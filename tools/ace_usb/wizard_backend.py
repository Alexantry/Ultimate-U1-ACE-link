#!/usr/bin/env python3
"""Private, once-only ACE maintenance transactions for the bilingual wizard.

SPDX-License-Identifier: GPL-3.0-only
Copyright (C) 2026 Ultimate U1-ACE link contributors; developed with OpenAI Codex.
No firmware, service, or serial action runs on import. CLI workers require U1 root.
"""
import argparse
import base64
import contextlib
import copy
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import uuid

import ace_iap as iap
import fetch_firmware
import prepare_profile

BUNDLE = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('ace_wizard_installer', BUNDLE / 'installer.py')
I = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(I)
STATE = Path('/userdata/ultimate-u1-ace-link/ace-firmware')
BUSY = {'PREPARING', 'STARTING', 'RUNNING', 'RECOVERING'}
SAFE = {'PREPARED', 'ALREADY_TARGET', 'UNSUPPORTED', 'FAILED_SAFE', 'CANCELLED_SAFE', 'SUCCEEDED'}
TARGET = 'CV1.3.863'
STAGE_FILES = ('installer.py',) + tuple('tools/ace_usb/' + name for name in (
    'wizard_backend.py', 'ace_iap.py', 'protocol.py', 'prepare_profile.py',
    'fetch_firmware.py', 'images.json', 'device-profile.json'))
PUBLIC = ('schema', 'operation', 'state', 'code', 'progress', 'ready',
          'service_restored', 'flash_attempted', 'needs_material_review', 'material_changes',
          'source_firmware', 'boot_firmware', 'target_firmware', 'diagnostic_path')
PUBLIC += ('verified_installation_receipt',)


class WizardError(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require(value, code):
    if not value:
        raise WizardError(code)


def plain(path):
    path = Path(path)
    for item in (path, *path.parents):
        require(not item.is_symlink(), 'UNSAFE_PATH')
    return path


def write_json(path, value):
    path = plain(path)
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex)
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
        if sys.platform.startswith('linux'):
            fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try: os.fsync(fd)
            finally: os.close(fd)
    finally:
        if temporary.exists(): temporary.unlink()


def read_json(path, maximum=32 * 1024 * 1024):
    path = plain(path)
    require(path.is_file() and path.stat().st_size <= maximum, 'INVALID_RECORD')
    return json.loads(path.read_text(encoding='utf8'))


def process_stamp(pid):
    try:
        # starttime follows the parenthesized comm field, which may contain spaces.
        value = Path('/proc/%d/stat' % pid).read_text().rsplit(')', 1)[1].split()
        if value[0] == 'Z': return None
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        return boot + ':' + value[19]
    except (OSError, IndexError):
        return None


def worker_alive(record):
    pid = record.get('worker_pid')
    return (type(pid) is int and pid > 0 and record.get('worker_stamp') is not None
            and process_stamp(pid) == record['worker_stamp'])


def empty_material(value):
    return (value is None or (isinstance(value, str) and value.strip().upper() in ('', 'NONE'))
            or isinstance(value, (list, dict)) and len(value) == 0)


def material_preserved(before, after):
    """A black color (0) and false boolean are values, not missing material."""
    for key, old in before.items():
        if key not in after: return False
        new = after.get(key)
        if isinstance(old, (list, dict)) and type(new) is not type(old): return False
        if not empty_material(old) and empty_material(new): return False
        if not empty_material(old):
            if isinstance(old, (str, list, dict, bool)) and type(new) is not type(old): return False
            if isinstance(old, (int, float)) and not isinstance(old, bool):
                if isinstance(new, bool) or not isinstance(new, (int, float)): return False
        if isinstance(old, list) and isinstance(new, list):
            if len(new) != len(old): return False
            if not material_preserved(dict(enumerate(old)), dict(enumerate(new))): return False
        if isinstance(old, dict) and isinstance(new, dict):
            if not material_preserved(old, new): return False
    return True


def material_summary(before, after):
    result = []
    for key in sorted(set(before) | set(after), key=lambda name: (before.get(name) == after.get(name), name)):
        if not re.match(r'^filament_(vendor|brand|type|subtype|sub_type|color)(_|$)', key): continue
        def value(item):
            if isinstance(item, (str, int, float, bool)) or item is None:
                return item[:128] if isinstance(item, str) else item
            if isinstance(item, list): return [value(x) for x in item[:4]]
            return 'changed'
        result.append({'field': key, 'before': value(before.get(key)), 'after': value(after.get(key))})
    if not result and before != after:
        result.append({'field': 'other_material_fields', 'before': 'present', 'after': 'updated'})
    return result


class Store:
    def __init__(self, root=STATE):
        self.root = Path(root)

    def initialize(self):
        plain(self.root)
        self.root.mkdir(parents=True, mode=0o700, exist_ok=True)
        if sys.platform.startswith('linux'): os.chmod(self.root, 0o700)

    @contextlib.contextmanager
    def lock(self):
        self.initialize()
        # This is the host installer's lock too. A second backend cannot restart
        # Klipper while a firmware worker or host installation owns the machine.
        import fcntl
        path = plain(self.root.parent / 'installer.lock')
        fd = os.open(path, os.O_WRONLY | os.O_CREAT, 0o600)
        with os.fdopen(fd, 'a') as stream:
            try: fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError: raise WizardError('MAINTENANCE_BUSY')
            yield

    def directory(self, token):
        require(isinstance(token, str) and re.fullmatch(r'[a-f0-9]{32}', token), 'INVALID_OPERATION')
        return plain(self.root / token)

    def load(self, token=None):
        if token is None:
            pointer = plain(self.root / 'last.json')
            if not pointer.exists(): return None
            token = read_json(pointer, 1024)['operation']
        record = read_json(self.directory(token) / 'state.json', 65536)
        require(record.get('schema') == 1 and record.get('operation') == token, 'INVALID_RECORD')
        return record

    def save(self, record):
        record['updated_at_utc'] = iap.utc_now()
        write_json(self.directory(record['operation']) / 'state.json', record)

    def new(self):
        self.initialize()
        token = uuid.uuid4().hex
        directory = self.directory(token)
        directory.mkdir(mode=0o700)
        record = dict(schema=1, operation=token, state='PREPARING', code='PREPARING', progress=0,
                      ready=False, service_restored=False, flash_attempted=False,
                      needs_material_review=False, material_changes=[], stopped=False,
                      verified_installation_receipt=False,
                      target_firmware=TARGET, worker_pid=None, worker_stamp=None,
                      diagnostic_path=str(directory), created_at_utc=iap.utc_now())
        self.save(record)
        write_json(self.root / 'last.json', {'operation': token})
        return record


class GuardedSession:
    """Recheck indexed slot idleness and durably mark the one IAP start."""
    def __init__(self, session, before_iap, gates):
        self.session, self.before_iap, self.gates = session, before_iap, gates
        self.started = False

    def __getattr__(self, name): return getattr(self.session, name)

    def rpc(self, method, params=None, timeout=1.5):
        if method == 'iap_upgrade':
            require(not self.started, 'DUPLICATE_FLASH_REFUSED')
            observed = iap.result_object(self.session.rpc('get_status', timeout=1.5), 'get_status')
            require(slot_gates(observed) == self.gates, 'ACE_GATE_CHANGED')
            self.before_iap()  # fsync precedes the first state-changing request.
            self.started = True
        return self.session.rpc(method, params, timeout=timeout)


def check_slots(status):
    require(iap.ready_state(status) and all(s.get('status') in ('ready', 'empty')
                                          for s in status['slots']), 'ACE_NOT_IDLE')


def slot_gates(status):
    check_slots(status)
    return [slot['status'] for slot in sorted(status['slots'], key=lambda slot: slot['index'])]


class Engine:
    def __init__(self, bundle=BUNDLE, store=None, host=None, session_factory=iap.SerialSession,
                 fetcher=fetch_firmware.fetch_image, alive=worker_alive, sleeper=time.sleep,
                 clock=time.monotonic):
        self.bundle = Path(bundle).resolve()
        self.store = store or Store()
        self.host = host or I.Host()
        self.installer = I.Installer(self.bundle, self.host)
        self.session_factory, self.fetcher, self.alive = session_factory, fetcher, alive
        self.sleep, self.clock = sleeper, clock

    def public(self, record):
        if record is None:
            return dict(schema=1, operation=None, state='NONE', code='NO_OPERATION', progress=0,
                        ready=False, service_restored=False, flash_attempted=False,
                        needs_material_review=False, material_changes=[], verified_installation_receipt=False)
        result = {key: record.get(key) for key in PUBLIC}
        if record['state'] in BUSY and not self.alive(record):
            age = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(record['updated_at_utc'])).total_seconds()
            if age > 10:
                result.update(state='NEEDS_ATTENTION', code='WORKER_STOPPED', ready=False,
                              service_restored=False)
        return result

    def result(self, token=None, wait_seconds=0):
        require(type(wait_seconds) is int and 0 <= wait_seconds <= 30, 'INVALID_WAIT')
        deadline = self.clock() + wait_seconds
        while True:
            result = self.public(self.store.load(token))
            if result['state'] not in BUSY or self.clock() >= deadline: return result
            self.sleep(min(2, max(0, deadline - self.clock())))

    def launch(self, record, action):
        directory = self.store.directory(record['operation'])
        logfile = plain(directory / (action + '-worker-' + uuid.uuid4().hex + '.log'))
        with logfile.open('xb') as output:
            process = subprocess.Popen([sys.executable, str(self.bundle / 'tools/ace_usb/wizard_backend.py'),
                         '_worker', '--operation', record['operation'], '--action', action],
                        stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                        close_fds=True, start_new_session=True, cwd=str(self.bundle))
        record['worker_pid'] = process.pid
        record['worker_stamp'] = process_stamp(process.pid)
        self.store.save(record)

    def prepare(self):
        with self.store.lock():
            previous = self.store.load()
            require(previous is None or previous['state'] in SAFE, 'ACTIVE_OPERATION')
            record = self.store.new()
            try:
                record['stage'] = self.stage()
                self.store.save(record)
                self.launch(record, 'prepare')
            except Exception:
                record.update(state='FAILED_SAFE', code='WORKER_START_FAILED', service_restored=True)
                self.store.save(record)
            return self.public(record)

    def start(self, token, confirmed=False, rollback_ack=False):
        require(confirmed and rollback_ack, 'CONFIRMATION_REQUIRED')
        with self.store.lock():
            record = self.store.load(token)
            require(self.store.load()['operation'] == token, 'NOT_LATEST_OPERATION')
            require(record['state'] == 'PREPARED' and not record['flash_attempted']
                    and record['ready'] and record['service_restored'], 'FLASH_NOT_PREPARED')
            self.stage_unchanged(record)
            require(0 <= (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(
                record['prepared_at_utc'])).total_seconds() <= 1800, 'PREPARATION_EXPIRED')
            record.update(state='STARTING', code='FLASH_STARTING', progress=0, ready=False,
                          service_restored=False, rollback_acknowledged=True)
            self.store.save(record)
            try: self.launch(record, 'flash')
            except Exception:
                # Never make this transaction startable again after reservation.
                record.update(state='NEEDS_ATTENTION', code='WORKER_START_FAILED')
                self.store.save(record)
            return self.public(record)

    def recover(self, token):
        with self.store.lock():
            record = self.store.load(token)
            require(self.store.load()['operation'] == token and not record['flash_attempted'], 'RECOVERY_REFUSED')
            require(not self.alive(record) and record['state'] not in SAFE, 'RECOVERY_REFUSED')
            record.update(state='RECOVERING', code='PROBE_ONLY_RECOVERY', ready=False,
                          service_restored=False, progress=0)
            self.store.save(record)
            self.launch(record, 'recover')
            return self.public(record)

    def maintenance(self):
        self.installer.firmware(); self.host.dependencies(); self.host.persistence()
        state = self.host.state(); self.host.idle(state)
        return state

    def stage(self):
        files = {}
        for name in STAGE_FILES:
            path = plain(self.bundle / name)
            require(path.is_file() and path.stat().st_size <= 2 * 1024 * 1024, 'INVALID_STAGE')
            files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        return {'directory': str(self.bundle), 'files': files}

    def stage_unchanged(self, record, same_directory=True):
        current = self.stage()
        previous = record.get('stage')
        require(isinstance(previous, dict) and previous.get('files') == current['files']
                and (not same_directory or previous.get('directory') == current['directory']), 'STAGE_CHANGED')

    def device(self, state):
        candidates = self.host.serial_candidates()
        require(len(candidates) == 1, 'ACE_INTERFACE_AMBIGUOUS')
        configured = state['configfile']['settings'].get('ace', {}).get('serial')
        if configured and configured != candidates[0]:
            require(Path(configured).resolve() == Path(candidates[0]).resolve(), 'ACE_INTERFACE_CHANGED')
        return candidates[0]

    def capture(self, state):
        files, total = {}, 0
        for path in sorted(self.host.path(I.CONFIG_ROOT).rglob('*.cfg')):
            name = '/' + path.relative_to(self.host.root).as_posix()
            data = self.host.read(name)
            if data is None: continue
            total += len(data); require(total <= 16 * 1024 * 1024, 'CONFIG_SNAPSHOT_TOO_LARGE')
            files[name] = base64.b64encode(data).decode('ascii')
        variable = state['configfile']['settings'].get('save_variables', {}).get('filename')
        if variable:
            require(isinstance(variable, str) and variable.startswith(I.CONFIG_ROOT + '/')
                    and Path(variable).name != 'print_task.json', 'UNSUPPORTED_VARIABLES_PATH')
            data = self.host.read(variable)
            require(data is not None and len(data) <= 1024 * 1024, 'VARIABLES_SNAPSHOT_FAILED')
            files[variable] = base64.b64encode(data).decode('ascii')
        for name in I.DESTINATIONS.values():
            data = self.host.read(name)
            files[name] = None if data is None else base64.b64encode(data).decode('ascii')
        return {'state': state, 'files': files}

    def protected(self, before):
        for name, encoded in before['files'].items():
            expected = None if encoded is None else base64.b64decode(encoded)
            require(self.host.read(name) == expected, 'CONFIG_CHANGED')

    def stop(self, record):
        record.update(stopped=True, service_restored=False, ready=False, probe_safe=False,
                      code='STOPPING_KLIPPER')
        self.store.save(record)
        self.host.service('stop')
        deadline = self.clock() + 15
        while True:
            server = self.host.get('/server/info')
            if server.get('klippy_connected') is False: break
            require(self.clock() < deadline, 'KLIPPER_STOP_FAILED')
            self.sleep(.5)
        iap.require_unused_device(record['device'])

    def probe(self, record, name, identity=None):
        directory = self.store.directory(record['operation'])
        audit = iap.Audit(directory / (name + '.jsonl'))
        session = None
        try:
            session = self.session_factory(record['device'], audit, expected_identity=identity)
            snap = iap.snapshot(session); check_slots(snap['status'])
            identity_value = snap['info'].get('id')
            require(type(identity_value) in (str, int) and str(identity_value).strip(), 'INVALID_ACE_ID')
            require(session.identity['vid'].lower() == '28e9' and session.identity['pid'].lower() == '018a',
                    'ACE_USB_IDENTITY_REJECTED')
            result = dict(schema=1, kind='ACE_GEN1_READ_ONLY_PROBE', captured_at_utc=iap.utc_now(),
                          device=record['device'], usb_identity=session.identity, snapshot=snap)
            iap.write_new_json(directory / (name + '.json'), result)
            return result
        finally:
            if session: session.close()
            audit.close()

    def restore(self, record, before):
        self.protected(before)
        self.host.service('start')
        deadline, stable, last = self.clock() + 110, 0, None
        while self.clock() < deadline:
            try:
                state = self.host.state(); self.host.idle(state)
                require(I.sensors(state) == I.sensors(before['state']), 'HEAD_SENSOR_CHANGED')
                original = before['state'].get('ace')
                if original:
                    require('ace' in state and state['ace']['gate_status'] == original['gate_status'], 'ACE_GATE_CHANGED')
                require(state['configfile']['settings'] == before['state']['configfile']['settings'], 'LOADED_CONFIG_CHANGED')
                self.protected(before)
                old, new = I.material(before['state']), I.material(state)
                require(material_preserved(old, new), 'MATERIAL_LOST')
                stable = stable + 1 if new == last else 1
                last = new
                if stable >= 3:
                    changes = material_summary(old, new) if old != new else []
                    record.update(service_restored=True, ready=True, stopped=False,
                                  needs_material_review=old != new, material_changes=changes)
                    return state
            except WizardError:
                raise
            except Exception:
                stable = 0
            self.sleep(1)
        raise WizardError('RESTORE_FAILED')

    def images(self, record, download=False):
        directory = self.store.directory(record['operation']) / 'images'
        if download:
            directory.mkdir(mode=0o700)
            source = (self.bundle / 'tools/ace_usb/images.json').read_bytes()
            descriptor = os.open(directory / 'images.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'wb') as stream: stream.write(source)
            for image in ('opencubic-gen1', 'stock-gen1-863'):
                self.fetcher(image, root=directory)
        require((directory / 'images.json').read_bytes() ==
                (self.bundle / 'tools/ace_usb/images.json').read_bytes(), 'IMAGE_MANIFEST_CHANGED')
        for image, (_, digest, size) in fetch_firmware.PINNED.items():
            data, item = iap.verify_image(directory / 'images.json', image)
            require(item['sha256'] == digest and len(data) == size, 'IMAGE_CHANGED')
        return iap.verify_image(directory / 'images.json', 'opencubic-gen1')

    def receipt_matches(self, probe):
        path = plain(self.store.root / 'last-success.json')
        if not path.exists(): return False
        receipt = read_json(path, 65536)
        age = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(receipt['captured_at_utc'])).total_seconds()
        return (0 <= age <= 86400 and receipt.get('image_sha256') == prepare_profile.TARGET_SHA256
                and receipt.get('usb_identity') == probe['usb_identity']
                and receipt.get('info') == probe['snapshot']['info'])

    def prepare_work(self, record):
        self.stage_unchanged(record)
        self.maintenance()
        record.update(code='DOWNLOADING_IMAGES', progress=5); self.store.save(record)
        self.images(record, download=True)
        state = self.maintenance()
        record['device'] = self.device(state)
        before = self.capture(state)
        write_json(self.store.directory(record['operation']) / 'before.json', before)
        record.update(progress=20); self.store.save(record)
        self.stop(record)
        probe = self.probe(record, 'probe')
        info = probe['snapshot']['info']
        record.update(source_firmware=info['firmware'], boot_firmware=info['boot_firmware'], progress=35,
                      usb_identity=probe['usb_identity'], device_info_id=info['id'],
                      inlet_status=slot_gates(probe['snapshot']['status']), probe_safe=True)
        self.store.save(record)
        self.restore(record, before)
        if info['firmware'] == TARGET:
            state, code = 'ALREADY_TARGET', 'EXISTING_TARGET_UNVERIFIED'
            record['verified_installation_receipt'] = self.receipt_matches(probe)
            if record['verified_installation_receipt']: code = 'EXISTING_TARGET_MATCHES_RECEIPT'
        elif (info['firmware'], info['boot_firmware']) == (prepare_profile.SOURCE_FIRMWARE, prepare_profile.BOOT_FIRMWARE):
            prepare_profile.build_draft(self.store.directory(record['operation']) / 'probe.json')
            state, code = 'PREPARED', 'READY_TO_FLASH'
        else:
            state, code = 'UNSUPPORTED', 'UNSUPPORTED_SOURCE'
        record.update(state=state, code=code, progress=100, prepared_at_utc=iap.utc_now())
        self.store.save(record)

    def flash_work(self, record):
        self.stage_unchanged(record)
        directory = self.store.directory(record['operation'])
        data, image = self.images(record)
        old = read_json(directory / 'before.json')
        self.protected(old)
        state = self.maintenance()
        require(self.device(state) == record['device'], 'ACE_INTERFACE_CHANGED')
        require(I.sensors(state) == I.sensors(old['state']), 'HEAD_SENSOR_CHANGED')
        require(state['configfile']['settings'] == old['state']['configfile']['settings'], 'LOADED_CONFIG_CHANGED')
        require(material_preserved(I.material(old['state']), I.material(state)), 'MATERIAL_LOST')
        if 'ace' in old['state']:
            require(state.get('ace', {}).get('gate_status') == old['state']['ace']['gate_status'], 'ACE_GATE_CHANGED')
        before = self.capture(state)
        write_json(directory / 'flash-before.json', before)
        self.stop(record)
        probe = self.probe(record, 'flash-probe', record['usb_identity'])
        info = probe['snapshot']['info']
        require(info['id'] == record['device_info_id'] and info['firmware'] == record['source_firmware']
                and info['boot_firmware'] == record['boot_firmware'], 'SOURCE_CHANGED')
        gates = slot_gates(probe['snapshot']['status'])
        require(gates == record['inlet_status'], 'ACE_GATE_CHANGED')
        record['probe_safe'] = True
        self.store.save(record)
        profile = prepare_profile.build_draft(directory / 'flash-probe.json')
        # Every gate has evidence above, or an explicit acknowledgement passed by
        # the UI to start(). No unmeasured maintenance fact is silently approved.
        profile['checks'] = dict(idle_state_verified=True, heaters_and_dryer_off_verified=True,
                                klipper_stopped_and_port_released=True, source_version_reviewed=True,
                                rollback_path_reviewed=record.get('rollback_acknowledged') is True)
        profile.update(write_enabled=True, reviewed_at_utc=iap.utc_now(), pending=[])
        iap.validate_write_profile(profile, image, record['device'])
        iap.validate_probe_evidence(profile, directory / 'flash-probe.json')
        prepare_profile.write_draft(directory / 'reviewed-profile.json', profile)
        # The low-level writer takes another live snapshot. A failure in that
        # final check invalidates the earlier safe probe; recovery must probe
        # again instead of restarting Klipper from stale inlet/identity evidence.
        record['probe_safe'] = False
        self.store.save(record)
        audit, session = iap.Audit(directory / 'flash.jsonl'), None
        def mark():
            self.stage_unchanged(record)
            record.update(flash_attempted=True, state='RUNNING', code='FLASH_RUNNING', progress=50)
            self.store.save(record)
        try:
            session = self.session_factory(record['device'], audit, expected_identity=record['usb_identity'])
            result = iap.flash_once(GuardedSession(session, mark, gates), data, image, profile, audit)
            require(result.get('outcome') == 'VERSION_CHANGED_AND_READY', 'TARGET_NOT_VERIFIED')
            require(slot_gates(result.get('status')) == gates, 'ACE_GATE_CHANGED')
            iap.write_new_json(directory / 'firmware-result.json', result)
        finally:
            if session: session.close()
            audit.close()
        record.update(progress=90, code='RESTORING_KLIPPER'); self.store.save(record)
        self.restore(record, before)
        write_json(self.store.root / 'last-success.json',
                   {'operation': record['operation'], 'captured_at_utc': iap.utc_now(),
                    'image_sha256': image['sha256'], 'usb_identity': record['usb_identity'],
                    'info': result['info']})
        record['verified_installation_receipt'] = True
        record.update(state='SUCCEEDED', code='FLASH_VERIFIED', progress=100)
        self.store.save(record)

    def recover_work(self, record):
        require(not record['flash_attempted'], 'RECOVERY_REFUSED')
        self.stage_unchanged(record, same_directory=False)
        path = self.store.directory(record['operation']) / 'before.json'
        if not record.get('stopped'):
            self.maintenance()
            record.update(ready=True, service_restored=True)
        else:
            before = read_json(path)
            self.installer.firmware(); self.protected(before)
            self.stop(record)
            probe = self.probe(record, 'recovery-' + uuid.uuid4().hex, record.get('usb_identity'))
            if 'device_info_id' in record:
                require(probe['snapshot']['info']['id'] == record['device_info_id'], 'SOURCE_CHANGED')
            if 'inlet_status' in record:
                require(slot_gates(probe['snapshot']['status']) == record['inlet_status'], 'ACE_GATE_CHANGED')
            self.restore(record, before)
        record.update(state='CANCELLED_SAFE', code='PROBE_ONLY_RECOVERED', progress=100)
        self.store.save(record)

    def work(self, token, action):
        # The parent releases its short creation lock before this worker obtains
        # the shared installer lock. Retry only lock acquisition, never an IAP.
        deadline = self.clock() + 15
        while True:
            try:
                with self.store.lock():
                    record = self.store.load(token)
                    expected = {'prepare': 'PREPARING', 'flash': 'STARTING', 'recover': 'RECOVERING'}[action]
                    require(self.store.load()['operation'] == token and record['state'] == expected, 'WORKER_STATE_CHANGED')
                    require(record.get('worker_pid') == os.getpid(), 'WORKER_IDENTITY_CHANGED')
                    try:
                        {'prepare': self.prepare_work, 'flash': self.flash_work, 'recover': self.recover_work}[action](record)
                    except Exception as exc:
                        # Details stay private. The public result contains a stable code only.
                        try:
                            write_json(self.store.directory(token) / ('failure-' + uuid.uuid4().hex + '.json'),
                                       {'type': type(exc).__name__, 'detail': str(exc)})
                        except Exception: pass  # Disk failure must not skip the hold/restore policy.
                        restored = False
                        if not record['flash_attempted']:
                            if not record.get('stopped'):
                                restored = True
                            elif record.get('probe_safe'):
                                try:
                                    path = self.store.directory(token) / ('flash-before.json' if action == 'flash' else 'before.json')
                                    self.restore(record, read_json(path)); restored = True
                                except Exception: pass
                        if not restored:
                            try: self.host.service('stop')
                            except Exception: pass
                            record.update(stopped=True, ready=False, service_restored=False)
                        record.update(state='FAILED_SAFE' if restored else 'NEEDS_ATTENTION',
                                      code=exc.code if isinstance(exc, WizardError) else 'MAINTENANCE_FAILED')
                        if restored: record['service_restored'] = True
                        self.store.save(record)
                    return
            except WizardError as exc:
                if exc.code != 'MAINTENANCE_BUSY' or self.clock() >= deadline: raise
                self.sleep(.2)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'start', 'result', 'recover', '_worker'))
    parser.add_argument('--operation')
    parser.add_argument('--wait-seconds', type=int, default=0)
    parser.add_argument('--confirm-flash', action='store_true')
    parser.add_argument('--accept-untested-rollback', action='store_true')
    parser.add_argument('--action', choices=('prepare', 'flash', 'recover'))
    args = parser.parse_args(argv)
    engine = Engine()
    try:
        require(sys.platform.startswith('linux') and hasattr(os, 'geteuid') and os.geteuid() == 0,
                'U1_ROOT_REQUIRED')
        os.umask(0o077)
        if args.command == 'result': result = engine.result(args.operation, args.wait_seconds)
        elif args.command == 'prepare': result = engine.prepare()
        elif args.command == 'start': result = engine.start(args.operation, args.confirm_flash, args.accept_untested_rollback)
        elif args.command == 'recover': result = engine.recover(args.operation)
        else:
            require(args.action is not None, 'INVALID_OPERATION')
            engine.work(args.operation, args.action)
            return 0
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        result = engine.public(None)
        result.update(state='ERROR', code=exc.code if isinstance(exc, WizardError) else 'MAINTENANCE_FAILED')
        print(json.dumps(result, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
