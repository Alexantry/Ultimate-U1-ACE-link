#!/usr/bin/env python3
"""Local, fail-closed installer for the reviewed U1 host integration.

Run on the printer as root. No downloads, firmware flashing, G-code, or physical
calibration are performed. check/status are read-only. Python standard library.
"""
import argparse
import configparser
import datetime
import errno
import glob
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

TARGET = '2.0.0-paxx12-24'
CONFIG_ROOT = '/home/lava/printer_data/config'
ACE_CONFIG = CONFIG_ROOT + '/extended/klipper/ace.cfg'
EXTENDED_CONFIG = CONFIG_ROOT + '/extended/extended2.cfg'
RFID_LINK = CONFIG_ROOT + '/extended/klipper/disable-rfid-reader.cfg'
RFID_TWEAK = '/usr/local/share/firmware-config/tweaks/klipper/disable-rfid-reader.cfg'
RFID_SERVICES = {
    '/etc/init.d/S59rfid-support': '60214bc1e0188774004e32fc2a1ae860c39d7a2c89c49da8b09a119a2b94eafd',
    '/etc/init.d/S99openrfid': '4eaf41a2c6e2c0cd72232c3f08723d3b2a3a058ae81a49d3738bdcb2b689f512',
    RFID_TWEAK: '80387430b72f73bcc459d6d5e895c2ab2c4bde58dcaf8967f871551a8dd585d3',
}
STATE_ROOT = '/userdata/ultimate-u1-ace-link'
RECEIPT = STATE_ROOT + '/install-state.json'
DEBUG = '/oem/.debug'
DESTINATIONS = {
    'ace.py': '/home/lava/klipper/klippy/extras/ace.py',
    'filament_feed.py': '/home/lava/klipper/klippy/extras/filament_feed.py',
    'filament_detect.py': '/home/lava/klipper/klippy/extras/filament_detect.py',
    'extruder.py': '/home/lava/klipper/klippy/kinematics/extruder.py',
}
DEFAULTS = {
    'serial': '/dev/serial/by-id/usb-ANYCUBIC_ACE_1-if00', 'baud': 115200,
    'feed_speed': 200, 'feed_length': 1250, 'retract_speed': 80,
    'retract_length': 1250, 'forward_takeup_length': 0, 'forward_takeup_speed': 50,
    'max_dryer_temperature': 55, 'fast_load_length': 1150, 'fast_load_speed': 200,
    'sensor_load_speed': 50, 'sensor_load_max_length': 2500,
    'calibrated_acknowledged': False, 'apply_existing_settings': False,
    'auto_detect_serial': True,
}
CONSTANTS = {'fast_load_length': ('FAST_LOAD_LENGTH', 1150),
             'fast_load_speed': ('FAST_LOAD_SPEED', 200),
             'sensor_load_speed': ('SENSOR_LOAD_SPEED', 50),
             'sensor_load_max_length': ('SENSOR_LOAD_MAX_LENGTH', 2500)}
CONFIG_KEYS = tuple(k for k in DEFAULTS if k not in CONSTANTS and
                    k not in ('calibrated_acknowledged', 'apply_existing_settings', 'auto_detect_serial'))


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def validate_settings(raw):
    require(isinstance(raw, dict) and not set(raw) - set(DEFAULTS), 'Unknown settings keys')
    s = dict(DEFAULTS, **raw)
    for key in ('calibrated_acknowledged', 'apply_existing_settings', 'auto_detect_serial'):
        require(type(s[key]) is bool, key + ' must be true or false')
    require(isinstance(s['serial'], str) and re.fullmatch(r'/dev/[A-Za-z0-9_./:+-]+', s['serial'])
            and '..' not in s['serial'].split('/'), 'serial must be a local /dev path')
    bounds = {'baud': (115200, 115200), 'feed_speed': (1, 200), 'feed_length': (1, 5000),
              'retract_speed': (1, 200), 'retract_length': (1, 5000),
              'forward_takeup_length': (0, 500), 'forward_takeup_speed': (1, 50),
              'max_dryer_temperature': (1, 70), 'fast_load_length': (1, 2500),
              'fast_load_speed': (1, 200), 'sensor_load_speed': (1, 50),
              'sensor_load_max_length': (2, 5000)}
    for key, (lo, hi) in bounds.items():
        require(type(s[key]) is int and lo <= s[key] <= hi,
                '%s must be an integer in %d..%d' % (key, lo, hi))
    require(s['forward_takeup_length'] < min(s['retract_length'], s['fast_load_length']),
            'Forward takeup must be shorter than retract and fast-load lengths')
    require(s['fast_load_length'] < s['sensor_load_max_length'], 'Fast load must be below seek limit')
    require(s['fast_load_length'] <= s['retract_length'], 'Fast load must not exceed calibrated retract')
    return s


def configured_payload(data, settings):
    text = data.decode('utf-8')
    for key, (constant, original) in CONSTANTS.items():
        pattern = r'(?m)^(    ' + constant + r' = )' + str(original) + r'$'
        text, count = re.subn(pattern, lambda m: m[1] + str(settings[key]), text)
        require(count == 1, 'Payload constant no longer matches reviewed source: ' + constant)
    result = text.encode('utf-8')
    compile(result, 'configured ace.py', 'exec')
    return result


def patch_ace_config(data, values, add_save_variables):
    """Edit only named ACE options; preserve unrelated sections and comments."""
    text = data.decode('utf-8') if data else '# Ultimate U1-ACE link\n\n[ace]\n'
    sections = list(re.finditer(r'(?m)^\s*\[([^\]\r\n]+)\]\s*(?:[#;].*)?$', text))
    matches = [m for m in sections if m[1].strip().lower() == 'ace']
    require(len(matches) == 1, 'Expected exactly one [ace] section in ace.cfg')
    start = matches[0].end()
    end = next((m.start() for m in sections if m.start() > start), len(text))
    body = text[start:end]
    for key, value in values.items():
        pattern = r'(?m)^(\s*' + re.escape(key) + r'\s*[:=]\s*)[^\r\n#;]*(.*)$'
        body, count = re.subn(pattern, lambda m: m[1] + str(value) +
                            (' ' if m[2].startswith(('#', ';')) else '') + m[2], body)
        require(count <= 1, 'Duplicate ACE option: ' + key)
        if count == 0:
            body = body.rstrip('\r\n') + '\n' + key + ': ' + str(value) + '\n\n'
    text = text[:start] + body + text[end:]
    if add_save_variables:
        text += '\n[save_variables]\nfilename: ' + CONFIG_ROOT + '/ace_vars.cfg\n'
    return text.encode('utf-8')


def filament_detection(data):
    parser = configparser.RawConfigParser(strict=True)
    if data:
        parser.read_string(data.decode('utf-8'))
    mode = parser.get('components', 'rfid', fallback='snapmaker').strip()
    require(mode in ('snapmaker', 'external', 'openrfid', 'openrfid-generic'),
            'Unknown filament detection mode; manual review required')
    return mode


def external_config(data):
    """Change only [components] rfid, preserving other settings and key files."""
    filament_detection(data)  # Reject malformed/duplicate configuration first.
    text = data.decode('utf-8') if data else ''
    headers = list(re.finditer(r'(?m)^\s*\[([^\]\r\n]+)\][ \t]*(?:[#;].*)?\r?$', text))
    section = next((m for m in headers if m[1] == 'components'), None)
    if section is None:
        return (text.rstrip('\r\n') + '\n\n[components]\nrfid: external\n').encode('utf-8')
    start = section.end()
    end = next((m.start() for m in headers if m.start() > start), len(text))
    body, count = re.subn(r'(?mi)^([ \t]*rfid[ \t]*[:=][ \t]*)[^\r\n]*(\r?)$',
                          lambda m: m[1] + 'external' + m[2], text[start:end])
    require(count <= 1, 'Duplicate filament detection setting')
    if not count:
        body = body.rstrip('\r\n') + '\nrfid: external\n\n'
    result = (text[:start] + body + text[end:]).encode('utf-8')
    require(filament_detection(result) == 'external', 'External setting verification failed')
    return result


class Host:
    """root/state_reader/service_runner are injection points for offline tests only."""
    def __init__(self, root=Path('/'), state_reader=None, service_runner=None):
        self.root = Path(root)
        self.state_reader = state_reader
        self.service_runner = service_runner
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def path(self, absolute):
        require(isinstance(absolute, str) and absolute.startswith('/') and
                '..' not in absolute.split('/'), 'Unsafe absolute path')
        p = self.root / absolute.lstrip('/')
        relative = p.relative_to(self.root)
        current = self.root
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                # This is the firmware's exact, pre-existing printer-data link.
                # Follow no other links, including links below its destination.
                if current == self.root / 'home/lava/printer_data':
                    expected = self.path('/oem/printer_data')
                elif current in (self.root / RFID_LINK.lstrip('/'),
                                 self.root / 'oem/printer_data/config/extended/klipper/disable-rfid-reader.cfg'):
                    expected = self.path(RFID_TWEAK)
                else:
                    raise RuntimeError('Unexpected symlink: ' + absolute)
                require(os.readlink(current) == str(expected)
                        and current.resolve() == expected,
                        'Unexpected symlink: ' + absolute)
        return p

    def read(self, path):
        p = self.path(path)
        return p.read_bytes() if p.exists() else None

    def get(self, path):
        with self.opener.open('http://127.0.0.1' + path, timeout=5) as response:
            return json.load(response)['result']

    def state(self):
        if self.state_reader:
            return self.state_reader()
        backend = self.get('/server/info')
        require(backend['klippy_connected'] and backend['klippy_state'] == 'ready', 'Klipper is not ready')
        names = set(self.get('/printer/objects/list')['objects'])
        required = ['webhooks', 'print_stats', 'idle_timeout', 'machine_state_manager',
                    'print_task_config', 'configfile', 'extruder', 'extruder1', 'extruder2',
                    'extruder3', 'heater_bed']
        required += ['filament_motion_sensor e%d_filament' % i for i in range(4)]
        require(set(required) <= names, 'Required U1 objects are missing')
        query = required + (['ace'] if 'ace' in names else [])
        result = self.get('/printer/objects/query?' + '&'.join(urllib.parse.quote(x) for x in query))['status']
        result['_config_file'] = self.get('/printer/info')['config_file']
        return result

    def idle(self, s, require_ace=False):
        require(s['webhooks']['state'] == 'ready' and
                s['print_stats']['state'] in ('standby', 'complete', 'cancelled') and
                s['idle_timeout']['state'] in ('Idle', 'Ready'), 'Printer must be idle')
        require(s['machine_state_manager']['main_state'] == 0 and
                s['machine_state_manager']['action_code'] == 0, 'U1 operation is active')
        for name in ('extruder', 'extruder1', 'extruder2', 'extruder3', 'heater_bed'):
            h = s[name]
            require(h['target'] == 0 and h['power'] == 0 and h['temperature'] < 50 and
                    not h.get('activating_move', False), 'Heater or motion is active: ' + name)
        a = s.get('ace')
        require(a is not None or not require_ace, 'ACE object is missing')
        if a is not None:
            require(a['connected'] and a['status_fresh'] and a['status'] == 'ready' and
                    not a['last_error'] and a['feed_assist_index'] == -1 and
                    not a['preload_queue'] and a['dryer_status']['status'] == 'stop', 'ACE must be idle and ready')
            require(not any(x and x.get('pending') for x in a['rfid_sync']), 'NFC synchronization is pending')

    def persistence(self):
        # The firmware supplies this bind mount. Never replace it with a symlink
        # or mount over arbitrary user paths from an installer.
        require(self.path(CONFIG_ROOT).samefile(self.path('/oem/printer_data/config')),
                'Expected /oem printer-data bind mount is missing')
        require(self.path('/oem/.printer_data').is_file(), 'Printer-data initialization marker is missing')

    def dependencies(self):
        if self.root == Path('/'):
            require(importlib.util.find_spec('serial') is not None,
                    'The printer Python lacks pyserial; install the documented dependency before continuing')

    def serial_candidates(self):
        """Identify unique ACE Gen 1 USB paths without opening a serial port."""
        found = {}
        for link in sorted((self.root / 'dev/serial/by-id').glob('usb-ANYCUBIC_ACE_*-if00')):
            try:
                target = link.resolve(strict=True)
                info = target.stat()
                if not stat.S_ISCHR(info.st_mode):
                    continue
                node = (self.root / ('sys/dev/char/%d:%d/device' %
                                    (os.major(info.st_rdev), os.minor(info.st_rdev)))).resolve(strict=True)
                for parent in (node, *node.parents):
                    vid, pid = parent / 'idVendor', parent / 'idProduct'
                    if vid.is_file() and pid.is_file():
                        if (vid.read_text().strip().lower(), pid.read_text().strip().lower()) == ('28e9', '018a'):
                            found.setdefault(str(target), '/' + link.relative_to(self.root).as_posix())
                        break
            except (OSError, ValueError):
                continue
        return sorted(found.values())

    def rfid_files(self):
        for path, expected in RFID_SERVICES.items():
            data = self.read(path)
            require(data is not None and digest(data) == expected,
                    'Unreviewed firmware RFID support file: ' + path)

    def _rfid_process_state(self):
        """Read actual daemon processes, independently of the removable PID file."""
        script = b'/usr/local/bin/openrfid.py'

        def daemon(command, native=False):
            argv = command.rstrip(b'\0').split(b'\0')
            # The native service puts the script at argv[1]. A manually
            # launched Python with extra flags is still a competing candidate,
            # but is never treated as owned by the native PID file.
            return (len(argv) >= 2 and (argv[1] == script if native else script in argv[1:]) and
                    re.fullmatch(rb'(?:.*/)?python(?:3(?:\.\d+)?)?', argv[0]) is not None)

        def command_at(path):
            try:
                return path.read_bytes()
            except OSError as exc:
                if exc.errno in (errno.ENOENT, errno.ESRCH):
                    return b''  # The process exited while /proc was enumerated.
                raise

        # /var/run can itself be a system symlink. This read-only runtime path
        # is separate from the strict managed-file mutation path policy.
        pidfile = self.root / 'var/run/openrfid.pid'
        registered = None
        if pidfile.exists():
            value = pidfile.read_text().strip()
            require(value.isdigit() and int(value) > 1, 'Invalid OpenRFID PID file')
            registered = int(value)
            command = command_at(self.root / ('proc/%d/cmdline' % registered))
            require(not command or daemon(command, native=True),
                    'OpenRFID PID belongs to another process; refusing to signal it')
        pids = set()
        for process in (self.root / 'proc').glob('[0-9]*'):
            if process.name.isdigit() and daemon(command_at(process / 'cmdline')):
                pids.add(int(process.name))
        require(len(pids) <= 1, 'Multiple OpenRFID processes found; refusing automatic service control')
        return registered, pids

    def rfid_running(self):
        registered, pids = self._rfid_process_state()
        require(not pids or pids == {registered},
                'Orphan OpenRFID process has no matching PID file; manual review required')
        return bool(pids)

    def rfid_service(self, action):
        require(action in ('start', 'stop'), 'Invalid OpenRFID service action')
        registered, original_pids = self._rfid_process_state()
        require(not original_pids or original_pids == {registered},
                'Orphan OpenRFID process has no matching PID file; refusing to signal it')
        subprocess.run(['/etc/init.d/S99openrfid', action], check=True, timeout=30,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            registered, remaining = self._rfid_process_state()
            if action == 'stop':
                require(remaining <= original_pids,
                        'A new OpenRFID process appeared during stop; refusing further signals')
                if not remaining:
                    return
            elif remaining and remaining == {registered}:
                return
            time.sleep(.1)
        raise RuntimeError('OpenRFID service state did not settle')

    def apply_rfid_support(self):
        subprocess.run(['/etc/init.d/S59rfid-support', 'restart'], check=True, timeout=30,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.external_ready()

    def external_ready(self):
        link = self.path(RFID_LINK)
        require(filament_detection(self.read(EXTENDED_CONFIG)) == 'external'
                and link.is_symlink() and os.readlink(link) == str(self.path(RFID_TWEAK))
                and not self.rfid_running(), 'External filament detection is not fully active')

    def restore_rfid_link(self, target):
        require(target == str(self.path(RFID_TWEAK)), 'Unexpected backed-up RFID link')
        path = self.path(RFID_LINK)
        temporary = path.with_name('.' + path.name + '.u1-ace-link')
        require(not temporary.exists() and not temporary.is_symlink(), 'Unexpected leftover RFID link stage')
        try:
            temporary.symlink_to(target)
            os.replace(temporary, path)
        finally:
            if temporary.is_symlink():
                temporary.unlink()

    def service(self, action):
        if self.service_runner:
            self.service_runner(action)
        else:
            subprocess.run(['/etc/init.d/S60klipper', action], check=True, timeout=90,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def write(self, path, data, metadata=None):
        p = self.path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if metadata is None:
            st = p.stat() if p.exists() else self.path(CONFIG_ROOT).stat()
            metadata = {'mode': stat.S_IMODE(st.st_mode) if p.exists() else 0o644,
                        'uid': st.st_uid, 'gid': st.st_gid}
        fd, name = tempfile.mkstemp(prefix='.' + p.name + '.u1-ace-', dir=str(p.parent))
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data); stream.flush(); os.fsync(stream.fileno())
            os.chmod(name, metadata['mode'])
            if hasattr(os, 'chown'):
                os.chown(name, metadata['uid'], metadata['gid'])
            os.replace(name, p)
        finally:
            if os.path.exists(name):
                os.unlink(name)


def material(s):
    return {k: v for k, v in s['print_task_config'].items() if k.startswith('filament_')}


def sensors(s):
    return [s['filament_motion_sensor e%d_filament' % i]['filament_detected'] for i in range(4)]


class Installer:
    def __init__(self, bundle, host=None):
        self.bundle = Path(bundle).resolve()
        self.host = host or Host()
        self.manifest = json.loads((self.bundle / 'manifest.json').read_text(encoding='utf-8'))

    def firmware(self):
        m = self.manifest
        require(m['schema'] == 1 and m['target_firmware'] == TARGET, 'Unsupported manifest or firmware target')
        checks = m.get('firmware_checks', [])
        require(bool(checks), 'Manifest lacks exact firmware evidence')
        for item in checks:
            data = self.host.read(item['path'])
            require(data is not None and digest(data) == item['sha256'], 'Unsupported firmware identity: ' + item['path'])
        markers = m.get('firmware_markers', [])
        require({x['path'] for x in markers} == {'/etc/FULLVERSION', '/etc/BASE_VERSION', '/etc/BUILD_VERSION'},
                'Manifest must identify the exact three U1 version markers')
        for marker in markers:
            raw = self.host.read(marker['path'])
            require(raw is not None and raw.decode().strip() == marker['value'], 'Wrong installed firmware version')

    def receipt(self):
        raw = self.host.read(RECEIPT)
        return json.loads(raw) if raw else None

    def config_files(self, entry):
        seen, stack, result = set(), set(), []
        def visit(name):
            require(name.startswith(CONFIG_ROOT + '/'), 'Config include outside printer config root')
            require(name not in stack, 'Cyclic Klipper config include')
            require(name not in seen, 'Duplicate Klipper config include: ' + name)
            stack.add(name); seen.add(name)
            data = self.host.read(name)
            require(data is not None, 'Missing config include: ' + name)
            text = data.decode('utf-8'); result.append((name, text))
            for pattern in re.findall(r'(?m)^\s*\[include\s+([^\]\r\n]+)\]', text):
                rel = str(PurePosixPath(name).parent / pattern.strip()) if not pattern.startswith('/') else pattern.strip()
                require('..' not in PurePosixPath(rel).parts, 'Parent config include requires manual review')
                paths = sorted(glob.glob(str(self.host.path(rel))))
                require(paths or any(c in rel for c in '*?['), 'Missing explicit config include')
                for path in paths:
                    visit('/' + Path(path).relative_to(self.host.root).as_posix())
            stack.remove(name)
        visit(entry)
        return result

    def prepare(self, raw_settings):
        self.firmware()
        s = validate_settings(raw_settings)
        requested_serial = s['serial']
        before = self.host.state(); self.host.idle(before); self.host.persistence(); self.host.dependencies()
        require(('ace' in before) == ('ace' in before['configfile']['settings']),
                'ACE object and loaded configuration disagree; resolve printer state before installation')
        self.host.rfid_files()
        rfid_before = {'mode': filament_detection(self.host.read(EXTENDED_CONFIG)),
                       'running': self.host.rfid_running()}
        require(not rfid_before['running'] or rfid_before['mode'] in ('openrfid', 'openrfid-generic'),
                'OpenRFID is running with an inconsistent configured mode; manual review required')
        if 'ace' not in before:
            require(not any(sensors(before)), 'First install requires all four U1 heads empty; also empty all ACE slots before continuing')
        entries = self.manifest['files']
        require(len(entries) == 4 and {x['id'] for x in entries} == set(DESTINATIONS), 'Payload scope is not exactly four modules')
        receipt = self.receipt()
        known = receipt.get('installed_hashes', {}) if receipt else {}
        changes, expected = {}, {}
        for item in entries:
            dest = DESTINATIONS[item['id']]
            require(item['destination'] == dest, 'Wrong module destination')
            source = (self.bundle / item['payload']).resolve()
            require(source.parent == self.bundle / 'payload' and source.name == item['id'], 'Unexpected payload path')
            new = source.read_bytes()
            require(digest(new) == item['sha256'], 'Payload hash mismatch: ' + item['id'])
            compile(new, str(source), 'exec')
            old = self.host.read(dest); old_hash = digest(old) if old is not None else None
            allowed = list(item['accepted_source_sha256']) + [item['sha256']]
            if dest in known:
                allowed.append(known[dest])
            require(old_hash in allowed, 'Unknown modified core; back up and review manually: ' + item['id'])
            changes[dest] = new
        files = self.config_files(before['_config_file'])
        ace_sections = [name for name, text in files if re.search(r'(?mi)^\s*\[ace\]\s*$', text)]
        require(not ace_sections or ace_sections == [ACE_CONFIG], 'Existing [ace] is in an unexpected or duplicate config')
        save_sections = [(name, text) for name, text in files if re.search(r'(?mi)^\s*\[save_variables\]\s*$', text)]
        require(len(save_sections) <= 1, 'Duplicate [save_variables] sections')
        require(any(re.search(r'(?m)^\s*\[include\s+extended/klipper/\*\.cfg\]', text)
                    for name, text in files if name == before['_config_file']),
                'Required stock extended/klipper/*.cfg include is missing; restore supported firmware config')
        loaded = before['configfile']['settings'].get('ace', {})
        if loaded and not s['apply_existing_settings']:
            for key in CONFIG_KEYS:
                if key in loaded:
                    s[key] = loaded[key]
            s = validate_settings(s)
        # Existing custom fast constants from this install are retained unless
        # the user explicitly chooses replacement settings.
        if receipt and not s['apply_existing_settings']:
            for key in CONSTANTS:
                s[key] = receipt['settings'][key]
            s = validate_settings(s)
        if loaded.get('serial') and (not s['apply_existing_settings'] or
                                     (requested_serial == DEFAULTS['serial'] and s['auto_detect_serial'])):
            s['serial'] = loaded['serial']
            serial_selection = 'existing_config'
        elif requested_serial != DEFAULTS['serial'] or not s['auto_detect_serial']:
            s['serial'] = requested_serial
            serial_selection = 'explicit_setting'
        else:
            candidates = self.host.serial_candidates()
            require(len(candidates) == 1,
                    'Automatic ACE serial selection requires exactly one verified device; found %d. '
                    'Use status to inspect candidates and choose an explicit serial path.' % len(candidates))
            s['serial'] = candidates[0]
            serial_selection = 'auto_discovered'
        s = validate_settings(s)
        require(self.host.root != Path('/') or Path(s['serial']).exists(), 'ACE serial device was not found')
        changes[DESTINATIONS['ace.py']] = configured_payload(changes[DESTINATIONS['ace.py']], s)
        old_cfg = self.host.read(ACE_CONFIG)
        require(old_cfg is None or ace_sections, 'Unloaded ace.cfg exists; refusing ambiguous configuration')
        changes[ACE_CONFIG] = patch_ace_config(old_cfg, {k: s[k] for k in CONFIG_KEYS}, not save_sections)
        changes[EXTENDED_CONFIG] = external_config(self.host.read(EXTENDED_CONFIG))
        tweak = self.host.read(RFID_TWEAK)
        current_reader = self.host.read(RFID_LINK)
        require(current_reader is None or current_reader == tweak,
                'Custom disable-rfid-reader.cfg requires manual review')
        changes[RFID_LINK] = tweak
        if not save_sections:
            variable_path = CONFIG_ROOT + '/ace_vars.cfg'
            if self.host.read(variable_path) is None:
                changes[variable_path] = b'[Variables]\nace__revision = 0\n'
        if self.host.read(DEBUG) is None:
            changes[DEBUG] = b''
        # Preserve all existing config files outside the exact ACE file, plus
        # save_variables contents. Only hashes enter the receipt, never keys.
        protected = {}
        for path in self.host.path(CONFIG_ROOT).rglob('*.cfg'):
            if path.is_symlink():
                continue
            name = '/' + path.relative_to(self.host.root).as_posix()
            if name not in changes:
                protected[name] = digest(path.read_bytes())
        for name, text in save_sections:
            parser = configparser.RawConfigParser(strict=True, inline_comment_prefixes=('#', ';'))
            parser.read_string(text)
            variable_path = parser.get('save_variables', 'filename')
            require(variable_path.startswith(CONFIG_ROOT + '/'), 'Existing save_variables file requires manual review')
            data = self.host.read(variable_path)
            if data is not None:
                protected[variable_path] = digest(data)
        for dest, data in changes.items():
            expected[dest] = digest(data)
        return {'changes': changes, 'expected': expected, 'protected': protected,
                'settings': s, 'before': before, 'rfid_before': rfid_before,
                'serial_selection': serial_selection, 'filament_detection': 'external'}

    def protected_ok(self, hashes):
        for name, expected in hashes.items():
            data = self.host.read(name)
            require(data is not None and digest(data) == expected, 'Protected user file changed: ' + name)

    def ready(self, before, version=None, settings=None, timeout=110):
        deadline, stable, error = time.monotonic() + timeout, 0, ''
        fresh_install = version is not None and 'ace' not in before
        last_material = None
        while time.monotonic() < deadline:
            try:
                s = self.host.state(); self.host.idle(s, require_ace=version is not None)
                require(sensors(s) == sensors(before), 'Head sensor changed')
                if fresh_install:
                    require(not any(sensors(s)) and s['ace']['gate_status'] == [0, 0, 0, 0],
                            'First install verification requires all ACE slots and U1 heads empty')
                    current_material = material(s)
                    if last_material is not None and current_material != last_material:
                        stable = 0
                    last_material = current_material
                else:
                    require(material(s) == material(before), 'Material metadata changed')
                if 'ace' in before and 'ace' in s:
                    require(s['ace']['gate_status'] == before['ace']['gate_status'], 'ACE gate changed')
                if version:
                    self.host.external_ready()
                    require(s['ace']['port_version'] == version, 'Unexpected active integration version')
                    loaded = s['configfile']['settings']['ace']
                    require(all(loaded.get(k) == settings[k] for k in CONFIG_KEYS), 'Loaded ACE settings mismatch')
                    require(s['configfile']['settings'].get('fm175xx_reader', {}).get('enabled') is False,
                            'Klipper internal RFID reader is not disabled')
                stable += 1
                if stable >= 3:
                    return s
            except Exception as exc:
                error = str(exc); stable = 0; last_material = None
            time.sleep(1)
        raise RuntimeError('Ready verification failed: ' + error)

    def ace_maintenance_clear(self):
        """A dead firmware worker must not grant permission to change services.

        The CLI holds installer.lock before this check. Check the durable record
        too: a crashed worker releases its lock while its ACE state is uncertain.
        This only inspects records; it never repairs or clears a transaction.
        """
        message = 'ACE firmware operation is not safely complete; inspect its saved result before host installation or rollback'
        base = STATE_ROOT + '/ace-firmware'

        def record(name, limit):
            path = self.host.path(name)  # Reject unexpected links in every component.
            require(path.is_file() and stat.S_ISREG(path.stat().st_mode)
                    and path.stat().st_size <= limit, message)
            with path.open('rb') as stream:
                content = stream.read(limit + 1)
            require(len(content) <= limit, message)
            try:
                value = json.loads(content)
            except (ValueError, UnicodeError) as exc:
                raise RuntimeError(message) from exc
            require(isinstance(value, dict), message)
            return value

        directory = self.host.path(base)
        require(not directory.exists() or directory.is_dir(), message)
        pointer = self.host.path(base + '/last.json')
        if not pointer.exists():
            return  # Older installations have no ACE wizard transaction.
        last = record(base + '/last.json', 1024)
        token = last.get('operation')
        require(isinstance(token, str) and re.fullmatch(r'[a-f0-9]{32}', token), message)
        state = record(base + '/' + token + '/state.json', 65536)
        require(type(state.get('schema')) is int and state['schema'] == 1
                and state.get('operation') == token, message)
        safe = {'PREPARED', 'ALREADY_TARGET', 'UNSUPPORTED', 'FAILED_SAFE',
                'CANCELLED_SAFE', 'SUCCEEDED'}
        require(isinstance(state.get('state'), str) and state['state'] in safe, message)
        require(state.get('ready') is True and state.get('service_restored') is True
                and state.get('stopped') is False, message)
        require(state.get('flash_attempted') is (state['state'] == 'SUCCEEDED'), message)

    def install(self, settings):
        self.ace_maintenance_clear()
        plan = self.prepare(settings)
        require(plan['settings']['calibrated_acknowledged'], 'Set calibrated_acknowledged=true only after reviewing your physical lengths and speeds')
        ident = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup = STATE_ROOT + '/backups/' + ident
        self.host.path(backup).mkdir(parents=True, mode=0o700, exist_ok=False)
        metadata = {'schema': 1, 'id': ident, 'target_firmware': TARGET, 'files': [],
                    'protected': plan['protected'], 'before': plan['before'],
                    'previous_receipt': self.receipt(), 'installed_hashes': plan['expected'],
                    'rfid_before': plan['rfid_before']}
        for i, (name, data) in enumerate(plan['changes'].items()):
            old = self.host.read(name); p = self.host.path(name)
            entry = {'path': name, 'existed': old is not None, 'backup': str(i),
                     'before_sha256': digest(old) if old is not None else None}
            if old is not None:
                st = p.stat(); entry.update(mode=stat.S_IMODE(st.st_mode), uid=st.st_uid, gid=st.st_gid)
                if p.is_symlink():
                    require(name == RFID_LINK, 'Unexpected managed symlink')
                    entry['symlink_target'] = os.readlink(p)
                self.host.write(backup + '/' + str(i), old, {'mode': 0o600, 'uid': 0, 'gid': 0})
            metadata['files'].append(entry)
        self.host.write(backup + '/backup.json', json_bytes(metadata), {'mode': 0o600, 'uid': 0, 'gid': 0})
        print('Backup ID: ' + ident + '\nBackup directory: ' + backup,
              file=sys.stderr, flush=True)
        stopped = False
        try:
            latest = self.host.state(); self.host.idle(latest)
            require(material(latest) == material(plan['before']) and sensors(latest) == sensors(plan['before']), 'State changed before installation')
            for entry in metadata['files']:
                old = self.host.read(entry['path'])
                require((digest(old) if old is not None else None) == entry['before_sha256'], 'File changed during preflight')
            self.protected_ok(plan['protected'])
            require(self.host.rfid_running() == plan['rfid_before']['running'], 'OpenRFID service changed during preflight')
            stopped = True; self.host.service('stop')
            self.host.rfid_service('stop')
            for name, data in plan['changes'].items():
                self.host.write(name, data)
            self.host.apply_rfid_support()
            self.host.service('start')
            after = self.ready(plan['before'], self.manifest['version'], plan['settings'])
            self.protected_ok(plan['protected'])
            require(all(digest(self.host.read(n)) == h for n, h in plan['expected'].items()), 'Installed file verification failed')
            receipt = {'schema': 1, 'backup': ident, 'version': self.manifest['version'],
                       'settings': plan['settings'], 'installed_hashes': plan['expected'],
                       'filament_detection': 'external', 'serial_selection': plan['serial_selection']}
            self.host.write(RECEIPT, json_bytes(receipt), {'mode': 0o600, 'uid': 0, 'gid': 0})
            return {'installed': True, 'backup': ident, 'ready_samples': 3, 'settings': plan['settings'],
                    'fresh_install': 'ace' not in plan['before'],
                    'empty_slot_metadata_initialized': material(after) != material(plan['before']),
                    'filament_detection': 'external', 'serial_selection': plan['serial_selection']}
        except BaseException as original:
            if stopped:
                try:
                    self.restore(metadata, backup, verify=True)
                except BaseException as recovery:
                    message = ('Installation failed: %s: %s; automatic rollback FAILED: %s: %s; '
                               'Backup ID: %s' % (type(original).__name__, original,
                                                 type(recovery).__name__, recovery, ident))
                    print(message, file=sys.stderr, flush=True)
                    raise RuntimeError(message) from original
                print('Automatic rollback VERIFIED. Backup ID: %s. Original installation error: %s: %s'
                      % (ident, type(original).__name__, original), file=sys.stderr, flush=True)
            else:
                print('Installation stopped before service/file changes. Backup ID: %s. Original error: %s: %s'
                      % (ident, type(original).__name__, original), file=sys.stderr, flush=True)
            raise

    def restore(self, metadata, backup, verify=True):
        allowed = set(DESTINATIONS.values()) | {ACE_CONFIG, CONFIG_ROOT + '/ace_vars.cfg', DEBUG,
                                              EXTENDED_CONFIG, RFID_LINK}
        require(len({e['path'] for e in metadata['files']}) == len(metadata['files']), 'Duplicate backup destinations')
        if 'rfid_before' in metadata:
            self.host.rfid_files()
        prepared = []
        for entry in metadata['files']:
            name = entry['path']; require(name in allowed, 'Backup contains an unexpected destination')
            if entry['existed']:
                require(re.fullmatch(r'\d+', entry['backup']), 'Invalid backup member')
                data = self.host.read(backup + '/' + entry['backup'])
                require(data is not None and digest(data) == entry['before_sha256'], 'Backup content mismatch')
                if entry.get('symlink_target') is not None:
                    require(name == RFID_LINK and entry['symlink_target'] == str(self.host.path(RFID_TWEAK)),
                            'Unexpected backed-up symlink')
            else:
                data = None
            prepared.append((entry, data))
        self.host.service('stop')
        if 'rfid_before' in metadata:
            self.host.rfid_service('stop')
        for entry, data in reversed(prepared):
            name = entry['path']
            if entry['existed']:
                if entry.get('symlink_target') is not None:
                    self.host.restore_rfid_link(entry['symlink_target'])
                else:
                    self.host.write(name, data, entry)
            elif self.host.path(name).exists():
                self.host.path(name).unlink()
        for entry, data in prepared:
            actual = self.host.read(entry['path'])
            require(actual == data, 'Restored file verification failed: ' + entry['path'])
        self.host.service('start')
        if metadata.get('rfid_before', {}).get('running'):
            self.host.rfid_service('start')
        if verify:
            prior = metadata['before'].get('ace', {}).get('port_version')
            # Older releases may not expose every newly added config key.
            self.ready(metadata['before'])
            if prior:
                require(self.host.state()['ace']['port_version'] == prior, 'Rollback version mismatch')
            self.protected_ok(metadata['protected'])
            if 'rfid_before' in metadata:
                original = metadata['rfid_before']
                require(filament_detection(self.host.read(EXTENDED_CONFIG)) == original['mode']
                        and self.host.rfid_running() == original['running'], 'Rollback RFID state mismatch')
        previous = metadata.get('previous_receipt')
        if previous is None:
            if self.host.path(RECEIPT).exists():
                self.host.path(RECEIPT).unlink()
        else:
            self.host.write(RECEIPT, json_bytes(previous), {'mode': 0o600, 'uid': 0, 'gid': 0})

    def rollback(self, ident=None, offline_recovery=False, confirm_idle_and_cold=False):
        self.ace_maintenance_clear()
        self.firmware()
        receipt = self.receipt()
        require(receipt is not None or (offline_recovery and ident),
                'No managed installation; offline recovery requires an explicit backup ID')
        ident = ident or receipt['backup']
        require(re.fullmatch(r'\d{8}T\d{12}Z', ident), 'Invalid backup ID')
        if offline_recovery:
            require(confirm_idle_and_cold, 'Offline recovery requires --confirm-idle-and-cold after a local physical check')
            try:
                live = self.host.state()
            except Exception:
                live = None
            if live is not None:
                live = dict(live); live.pop('ace', None)
                self.host.idle(live)
        else:
            require(ident == receipt['backup'], 'Only the latest managed installation can be rolled back')
            self.host.idle(self.host.state(), require_ace=True)
        backup = STATE_ROOT + '/backups/' + ident
        metadata = json.loads(self.host.read(backup + '/backup.json'))
        require(metadata['id'] == ident and metadata['target_firmware'] == TARGET, 'Backup identity mismatch')
        for entry in metadata['files']:
            name = entry['path']; data = self.host.read(name)
            actual = digest(data) if data is not None else None
            permitted = {metadata['installed_hashes'][name]}
            if offline_recovery:
                permitted.add(entry['before_sha256'])
            require(actual in permitted, 'Installed files changed; manual rollback review required')
        self.restore(metadata, backup)
        return {'rolled_back': True, 'backup': ident}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('check', 'status', 'install', 'rollback'))
    parser.add_argument('--settings', type=Path, help='Local JSON settings; required for check/install')
    parser.add_argument('--backup', help='Latest backup ID; optional for rollback')
    parser.add_argument('--offline-recovery', action='store_true', help='Recover when the API cannot become ready')
    parser.add_argument('--confirm-idle-and-cold', action='store_true', help='Confirm a local physical idle/cold check for offline recovery')
    args = parser.parse_args()
    installer = Installer(Path(__file__).resolve().parent)
    if args.command in ('install', 'rollback'):
        require(hasattr(os, 'geteuid') and os.geteuid() == 0, 'Run on the U1 as root')
        import fcntl
        lock_dir = installer.host.path(STATE_ROOT)
        lock_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
        # Held until process exit, including rollback and ready verification.
        lock = open(installer.host.path(STATE_ROOT + '/installer.lock'), 'a')
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    if args.command == 'status':
        installer.firmware()
        s = installer.host.state()
        result = {'firmware': TARGET, 'klipper_state': s['webhooks']['state'],
                  'ace_version': s.get('ace', {}).get('port_version'),
                  'managed': installer.receipt() is not None,
                  'existing_ace': 'ace' in s or 'ace' in s['configfile']['settings'],
                  'ace_settings': {k: v for k, v in s['configfile']['settings'].get('ace', {}).items()
                                   if k in CONFIG_KEYS},
                  'serial_candidates': installer.host.serial_candidates(),
                  'filament_detection': filament_detection(installer.host.read(EXTENDED_CONFIG)),
                  'internal_rfid_enabled': s['configfile']['settings'].get('fm175xx_reader', {}).get('enabled'),
                  'openrfid_running': installer.host.rfid_running()}
    elif args.command == 'rollback':
        result = installer.rollback(args.backup, args.offline_recovery, args.confirm_idle_and_cold)
    else:
        require(args.settings is not None, '--settings is required')
        settings = json.loads(args.settings.read_text(encoding='utf-8-sig'))
        if args.command == 'install':
            result = installer.install(settings)
        else:
            plan = installer.prepare(settings)
            result = {'compatible': True, 'read_only': True, 'destinations': list(plan['changes']),
                      'effective_settings': plan['settings'],
                      'calibration_acknowledged': plan['settings']['calibrated_acknowledged'],
                      'serial_selection': plan['serial_selection'],
                      'fresh_install': 'ace' not in plan['before'],
                      'filament_detection': plan['filament_detection'],
                      'previous_filament_detection': plan['rfid_before']['mode']}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        sys.exit(1)
