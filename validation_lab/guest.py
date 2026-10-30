#!/usr/bin/env python3
"""Disposable GitHub VM fixture. Not printer software; never run on hardware.

SPDX-License-Identifier: GPL-3.0-only
"""
import argparse
import ast
import configparser
import contextlib
import errno
import hashlib
import http.server
import json
import os
from pathlib import Path
import re
import select
import shlex
import signal
import stat
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
LAB = Path('/run/ultimate-u1-ace-link-vm-lab')
STATE = LAB / 'state.json'
CONFIG = Path('/oem/printer_data/config')
CONFIG_ALIAS = Path('/home/lava/printer_data/config')
SERIAL = Path('/dev/serial/by-id/usb-ANYCUBIC_ACE_LAB-if00')
RFID_TWEAK = Path('/usr/local/share/firmware-config/tweaks/klipper/disable-rfid-reader.cfg')
RFID_LINK = CONFIG / 'extended/klipper/disable-rfid-reader.cfg'
RECEIPT = Path('/userdata/ultimate-u1-ace-link/install-state.json')
CANARY = CONFIG / 'extended/openrfid_user.cfg'
CANARY_BYTES = b'# Synthetic preservation canary. No credentials or NFC keys.\n[lab_canary]\nvalue = VM_ONLY\n'
REQUIRED = ['webhooks', 'print_stats', 'idle_timeout', 'machine_state_manager',
            'print_task_config', 'configfile', 'extruder', 'extruder1', 'extruder2',
            'extruder3', 'heater_bed'] + ['filament_motion_sensor e%d_filament' % i for i in range(4)]
PUBLIC_FIXTURES = {
    'home/lava/klipper/klippy/extras/filament_feed.py',
    'home/lava/klipper/klippy/extras/filament_detect.py',
    'home/lava/klipper/klippy/kinematics/extruder.py',
    'home/lava/klipper/klippy/extras/print_task_config.py',
    'etc/init.d/S59rfid-support', 'etc/init.d/S99openrfid',
    'usr/local/bin/extended-config.py',
    'usr/local/share/firmware-config/tweaks/klipper/disable-rfid-reader.cfg',
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def gate():
    """Fail before any filesystem, process, HTTP, or device setup mutation."""
    require(sys.platform.startswith('linux') and os.geteuid() == 0, 'Disposable Linux VM root required')
    require(os.environ.get('CI') == 'true' and os.environ.get('GITHUB_ACTIONS') == 'true', 'GitHub CI required')
    require(os.environ.get('GITHUB_REPOSITORY') == 'Alexantry/Ultimate-U1-ACE-link', 'Wrong repository')
    run_id = os.environ.get('GITHUB_RUN_ID', '')
    token = os.environ.get('U1_ACE_LAB_TOKEN', '')
    require(re.fullmatch(r'[0-9]+', run_id) is not None, 'Missing CI run identity')
    require(re.fullmatch(r'[a-f0-9]{32}', token) is not None, 'Missing disposable VM token')
    require(os.readlink('/proc/self/ns/mnt') != os.readlink('/proc/1/ns/mnt'), 'Private mount namespace required')
    marker = LAB / 'permission.json'
    require(not LAB.is_symlink() and not marker.is_symlink(), 'Unsafe VM marker path')
    info = marker.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o600,
            'VM marker must be a root-owned regular 0600 file')
    require(info.st_size < 4096, 'Invalid VM marker size')
    record = json.loads(marker.read_text())
    require(record == {'schema': 1, 'scope': 'vm-software-flow', 'run_id': run_id, 'token': token},
            'Disposable VM marker does not match this run')


def atomic_json(path, value):
    temporary = path.with_name(path.name + '.new-' + str(os.getpid()))
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, 'w') as stream:
            json.dump(value, stream, sort_keys=True)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists(): temporary.unlink()


@contextlib.contextmanager
def locked_state(write=False):
    import fcntl
    with (LAB / 'fixture.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        value = json.loads(STATE.read_text())
        yield value
        if write: atomic_json(STATE, value)


def event(kind, **values):
    data = json.dumps({'kind': kind, **values}, sort_keys=True) + '\n'
    descriptor = os.open(LAB / 'events.jsonl', os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try: os.write(descriptor, data.encode())
    finally: os.close(descriptor)


def identity(path):
    if path.is_symlink():
        return {'link': os.readlink(path)}
    if not path.exists(): return None
    info = path.stat()
    return {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'mode': stat.S_IMODE(info.st_mode), 'uid': info.st_uid, 'gid': info.st_gid}


def controlled_files():
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    paths = [Path(entry['destination']) for entry in manifest['files']]
    paths += [Path('/oem/.debug'), RECEIPT, CONFIG / 'ace_vars.cfg', CONFIG / 'extended/klipper/ace.cfg',
              CONFIG / 'extended/extended2.cfg', RFID_LINK, CANARY]
    return {str(path): identity(path) for path in paths}


def copy_new(destination, data, mode=0o644):
    require(not destination.exists() and not destination.is_symlink(), 'Refusing existing VM fixture path: ' + str(destination))
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode)
    with os.fdopen(descriptor, 'wb') as stream: stream.write(data)


def setup():
    require(not STATE.exists(), 'Fixture already initialized; use a new disposable VM')
    for path in ('/oem', '/userdata', '/home/lava'):
        require(not Path(path).exists() and not Path(path).is_symlink(), 'Target already exists: ' + path)
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    fixture_manifest = json.loads((ROOT / 'validation_lab/fixtures/manifest.json').read_text())
    fixture_root = ROOT / 'validation_lab/fixtures/root'
    expected = {entry['path']: entry['sha256'] for entry in fixture_manifest['files']}
    require(set(expected) == PUBLIC_FIXTURES and len(fixture_manifest['files']) == 8,
            'Unexpected public fixture scope')
    for relative, expected_hash in expected.items():
        data = (fixture_root / relative).read_bytes()
        require(hashlib.sha256(data).hexdigest() == expected_hash, 'Fixture hash mismatch: ' + relative)
    for check in manifest['firmware_checks']:
        require(expected[check['path'].lstrip('/')] == check['sha256'], 'Firmware guard fixture differs')
    for entry in manifest['files']:
        if entry['id'] == 'ace.py': continue
        require(expected[entry['destination'].lstrip('/')] in entry['accepted_source_sha256'],
                'Original module fixture is outside production acceptance')
    # Execute the exact production RFID services. Only Klipper itself is replaced.
    import importlib.util
    specification = importlib.util.spec_from_file_location('lab_installer_identity', ROOT / 'installer.py')
    installer = importlib.util.module_from_spec(specification); specification.loader.exec_module(installer)
    for path, digest in installer.RFID_SERVICES.items():
        require(expected[path.lstrip('/')] == digest, 'RFID service fixture differs')
    for relative in expected:
        destination = Path('/') / relative
        mode = 0o755 if relative.startswith(('etc/init.d/', 'usr/local/bin/')) else 0o644
        copy_new(destination, (fixture_root / relative).read_bytes(), mode)
    for marker in manifest['firmware_markers']:
        copy_new(Path(marker['path']), (marker['value'] + '\n').encode())
    CONFIG.mkdir(parents=True)
    (CONFIG / 'extended/klipper').mkdir(parents=True)
    Path('/userdata').mkdir()
    alias = Path('/home/lava/printer_data'); alias.mkdir(parents=True)
    subprocess.run(['mount', '--bind', '/oem/printer_data', str(alias)], check=True)
    require(CONFIG.samefile(CONFIG_ALIAS), 'Real printer-data bind mount failed')
    copy_new(Path('/oem/.printer_data'), b'')
    copy_new(CONFIG / 'printer.cfg', b'[printer]\nkinematics: corexy\n[include extended/klipper/*.cfg]\n')
    copy_new(CONFIG / 'extended/extended2.cfg', b'[components]\nrfid: snapmaker\n\n[web]\nfrontend: fluidd\n')
    copy_new(CANARY, CANARY_BYTES)
    service = '#!/bin/sh\n# LAB ONLY: does not start Klipper or any MCU.\nexec /usr/bin/python3 ' + shlex.quote(str(Path(__file__).resolve())) + ' service "$1"\n'
    copy_new(Path('/etc/init.d/S60klipper'), service.encode(), 0o755)
    synthetic_sysfs = LAB / 'sys-dev-char'; synthetic_sysfs.mkdir()
    subprocess.run(['mount', '--bind', str(synthetic_sysfs), '/sys/dev/char'], check=True)
    state = {'schema': 1, 'mode': 'idle', 'service_running': True, 'fail_starts': 0,
             'service_actions': [], 'serial_bytes': 0, 'http_write_attempts': 0, 'serial_target': None,
             'load_generation': 0, 'last_start_error': None,
             'material': {'filament_vendor_0': 'Bambu', 'filament_type_0': 'PLA',
                          'filament_subtype_0': 'Matte', 'filament_color_0': '102030FF'},
             'baseline': controlled_files(), 'guard_baseline': None, 'guard_service_count': 0}
    state.update(runtime_snapshot())
    atomic_json(STATE, state)
    event('setup', scope='synthetic-hardware-actual-installer')
    return snapshot()


def loaded_configuration():
    settings = {}
    ace_config = CONFIG / 'extended/klipper/ace.cfg'
    if ace_config.exists():
        parser = configparser.RawConfigParser(inline_comment_prefixes=('#', ';'))
        parser.read(ace_config)
        require(parser.has_section('ace'), 'Installed ACE configuration is malformed')
        settings['ace'] = {name: value if name == 'serial' else int(value)
                           for name, value in parser.items('ace')}
        if parser.has_section('save_variables'):
            settings['save_variables'] = dict(parser.items('save_variables'))
    if RFID_LINK.exists():
        reader = configparser.RawConfigParser(); reader.read(RFID_LINK)
        settings['fm175xx_reader'] = {'enabled': reader.getboolean('fm175xx_reader', 'enabled')}
    return settings


def port_version():
    source = Path('/home/lava/klipper/klippy/extras/ace.py')
    tree = ast.parse(source.read_bytes(), filename=str(source))
    values = [node.value.value for node in ast.walk(tree) if isinstance(node, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == 'PORT_VERSION' for target in node.targets)
              and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)]
    require(len(values) == 1, 'Installed integration version cannot be read')
    return values[0]


def runtime_snapshot():
    """Record the file view at a simulated start, without importing Klipper."""
    settings = loaded_configuration()
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    hashes = {}
    for entry in manifest['files']:
        source = Path(entry['destination'])
        hashes[str(source)] = hashlib.sha256(source.read_bytes()).hexdigest() if source.exists() else None
    return {'loaded_settings': settings,
            'loaded_port_version': port_version() if 'ace' in settings else None,
            'loaded_module_hashes': hashes}


def moonraker_state():
    with locked_state() as current: value = dict(current)
    settings = value['loaded_settings']
    busy = value['mode'] == 'busy'; hot = value['mode'] == 'hot'
    result = {'webhooks': {'state': 'ready' if value['service_running'] else 'shutdown'},
              'print_stats': {'state': 'printing' if busy else 'standby'},
              'idle_timeout': {'state': 'Printing' if busy else 'Idle'},
              'machine_state_manager': {'main_state': 1 if busy else 0, 'action_code': 0},
              'print_task_config': value['material'], 'configfile': {'settings': settings}}
    for name in ('extruder', 'extruder1', 'extruder2', 'extruder3', 'heater_bed'):
        result[name] = {'target': 100 if hot else 0, 'power': .5 if hot else 0,
                        'temperature': 100 if hot else 25}
    for index in range(4):
        result['filament_motion_sensor e%d_filament' % index] = {'filament_detected': False}
    if 'ace' in settings:
        result['ace'] = {'connected': True, 'status_fresh': True, 'status': 'ready',
                         'last_error': None, 'feed_assist_index': -1, 'preload_queue': [],
                         'dryer_status': {'status': 'stop'}, 'rfid_sync': [None] * 4,
                         'gate_status': [0, 0, 0, 0], 'port_version': value['loaded_port_version']}
    return result


class Moonraker(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args): pass

    def do_GET(self):
        try:
            endpoint = urlsplit(self.path).path
            event('http_get', path=endpoint)
            state = moonraker_state()
            if endpoint == '/server/info':
                result = {'klippy_connected': state['webhooks']['state'] == 'ready',
                          'klippy_state': state['webhooks']['state']}
            elif endpoint == '/printer/objects/list':
                result = {'objects': REQUIRED + (['ace'] if 'ace' in state else [])}
            elif endpoint == '/printer/objects/query': result = {'status': state}
            elif endpoint == '/printer/info': result = {'config_file': str(CONFIG_ALIAS / 'printer.cfg')}
            else:
                self.send_error(404); return
            self.reply(200, {'result': result})
        except Exception as exception:
            self.reply(500, {'error': str(exception)})

    def do_POST(self):
        with locked_state(True) as state: state['http_write_attempts'] += 1
        event('rejected_http_write', path=urlsplit(self.path).path)
        self.reply(405, {'error': 'Lab fixture never accepts motion or firmware API commands'})

    def reply(self, status, value):
        data = json.dumps(value).encode()
        self.send_response(status); self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)


def serve(ready_file):
    require(STATE.exists(), 'Run setup first')
    master, slave = os.openpty()
    target = os.ttyname(slave)
    device = os.fstat(slave)
    os.close(slave)  # No held slave descriptor: real exclusive-ownership checks remain meaningful.
    SERIAL.parent.mkdir(parents=True, exist_ok=True)
    require(not SERIAL.exists() and not SERIAL.is_symlink(), 'Synthetic serial link already exists')
    SERIAL.symlink_to(target)
    usb = LAB / 'synthetic-usb/1-1'; usb.mkdir(parents=True)
    (usb / 'idVendor').write_text('28e9\n'); (usb / 'idProduct').write_text('018a\n')
    (usb / 'serial').write_text('VM-LAB-SYNTHETIC-NOT-A-DEVICE\n')
    tty = usb / 'tty'; tty.mkdir()
    char = LAB / ('sys-dev-char/%d:%d' % (os.major(device.st_rdev), os.minor(device.st_rdev)))
    char.mkdir(); (char / 'device').symlink_to(tty)
    with locked_state(True) as state: state['serial_target'] = target
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 80), Moonraker)
    stopping = threading.Event()
    def stop(*_): stopping.set()
    signal.signal(signal.SIGTERM, stop); signal.signal(signal.SIGINT, stop)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    ready_file = Path(ready_file).resolve()
    require(ready_file.is_relative_to(LAB), 'Ready marker must stay inside the lab directory')
    atomic_json(ready_file, {'ready': True, 'pid': os.getpid(), 'serial': str(SERIAL), 'http': '127.0.0.1:80'})
    event('serve_ready')
    try:
        while not stopping.is_set():
            if not select.select([master], [], [], .2)[0]: continue
            try:
                data = os.read(master, 65536)
                if data:
                    with locked_state(True) as state: state['serial_bytes'] += len(data)
                    event('unexpected_serial_bytes', count=len(data))
            except OSError as exception:
                if exception.errno != errno.EIO: raise
                stopping.wait(.1)
    finally:
        server.shutdown(); server.server_close(); os.close(master)


def service(action):
    require(action in ('start', 'stop', 'restart'), 'Unsupported lab service action')
    if action == 'restart':
        service('stop'); return service('start')
    with locked_state(True) as state:
        state['service_actions'].append(action)
        fail = action == 'start' and state['fail_starts'] > 0
        if fail: state['fail_starts'] -= 1
        state['service_running'] = False
        if action == 'start':
            state['last_start_error'] = 'Injected one-shot lab Klipper start failure' if fail else None
            if not fail:
                try:
                    loaded = runtime_snapshot()
                except Exception as exception:
                    fail = True
                    state['last_start_error'] = 'Lab configuration load failed: ' + str(exception)
                else:
                    state.update(loaded)
                    state['load_generation'] += 1
                    state['service_running'] = True
        error = state['last_start_error'] if fail else None
    event('service', action=action, injected_failure=fail)
    require(not fail, error)
    return {'service': action, 'hardware': False}


def set_state(mode):
    with locked_state(True) as state:
        state['guard_baseline'] = controlled_files()
        state['guard_service_count'] = len(state['service_actions'])
        if mode in ('service-failure', 'fail-next-start'):
            state['mode'] = 'idle'; state['fail_starts'] = 1
        else:
            state['mode'] = mode; state['fail_starts'] = 0
    event('state', mode=mode)
    return snapshot()


def snapshot():
    with locked_state() as state:
        result = {name: state[name] for name in ('mode', 'service_running', 'fail_starts', 'service_actions',
                  'serial_bytes', 'http_write_attempts', 'serial_target', 'material', 'load_generation',
                  'loaded_settings', 'loaded_port_version', 'loaded_module_hashes', 'last_start_error')}
    result.update(files=controlled_files(), ace_config_exists=(CONFIG / 'extended/klipper/ace.cfg').exists(),
                  receipt_exists=RECEIPT.exists(), bind_mount_verified=CONFIG.samefile(CONFIG_ALIAS))
    return result


def assert_state(kind):
    with locked_state() as state: value = dict(state)
    current = controlled_files()
    require(CANARY.read_bytes() == CANARY_BYTES, 'Synthetic private-file canary changed')
    require(value['serial_bytes'] == 0, 'Unexpected serial writes in the KEEP-only host scenario')
    require(value['http_write_attempts'] == 0, 'Unexpected HTTP mutation attempted in the host scenario')
    require(CONFIG.samefile(CONFIG_ALIAS), 'Printer-data binding changed')
    if kind in ('baseline', 'rolled-back'):
        require(current == value['baseline'], 'Original file bytes or metadata were not restored')
    elif kind in ('guarded', 'unchanged'):
        require(value['guard_baseline'] is not None and current == value['guard_baseline'], 'Guarded files changed')
        if kind == 'guarded':
            require(len(value['service_actions']) == value['guard_service_count'], 'Rejected operation changed service state')
    elif kind == 'installed':
        require(RECEIPT.exists(), 'Installation receipt is missing')
        receipt = json.loads(RECEIPT.read_text())
        for path, digest in receipt['installed_hashes'].items():
            require(hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, 'Installed hash differs: ' + path)
        parser = configparser.RawConfigParser(); parser.read(CONFIG / 'extended/extended2.cfg')
        require(parser.get('components', 'rfid') == 'external', 'External mode was not installed')
        require(RFID_LINK.is_symlink() and os.readlink(RFID_LINK) == str(RFID_TWEAK), 'Actual RFID symlink differs')
        require(port_version() == json.loads((ROOT / 'manifest.json').read_text())['version'], 'Wrong installed version')
        require(value['load_generation'] > 0, 'No simulated service load occurred')
        for field, expected in runtime_snapshot().items():
            require(value[field] == expected, 'Disk files differ from the last simulated start: ' + field)
    elif kind == 'service-recovered':
        require(value['service_running'] and value['fail_starts'] == 0, 'Service did not recover')
    require(value['service_running'], 'Fixture service is not running')
    event('assert', check=kind, passed=True)
    return {'assertion': kind, 'passed': True, 'synthetic_hardware': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('setup'); sub.add_parser('snapshot')
    server = sub.add_parser('serve'); server.add_argument('--ready-file', default=str(LAB / 'ready.json'))
    setting = sub.add_parser('set-state'); setting.add_argument('mode', choices=('idle', 'busy', 'hot', 'service-failure', 'fail-next-start'))
    check = sub.add_parser('assert'); check.add_argument('kind', choices=('baseline', 'installed', 'rolled-back', 'guarded', 'unchanged', 'service-recovered'))
    operation = sub.add_parser('service'); operation.add_argument('action', choices=('start', 'stop', 'restart'))
    args = parser.parse_args()
    gate()
    if args.command == 'serve': serve(args.ready_file); return
    result = {'setup': setup, 'snapshot': snapshot,
              'set-state': lambda: set_state(args.mode),
              'assert': lambda: assert_state(args.kind),
              'service': lambda: service(args.action)}[args.command]()
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    try: main()
    except Exception as error:
        print('LAB REFUSED OR FAILED: ' + str(error), file=sys.stderr)
        sys.exit(1)
