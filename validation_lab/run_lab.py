#!/usr/bin/env python3
"""Software installation E2E in a disposable GitHub Linux VM, never a printer.

Production installer, manifest, payload, SSH, SCP, and PowerShell process calls
are unchanged. The lab supplies virtual printer status and service substitutes.
It does not emulate the U1 board, ACE firmware, NFC, or filament movement.
SPDX-License-Identifier: GPL-3.0-only
"""
import argparse
import configparser
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import time
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LAB = Path(__file__).resolve().parent
STATE = Path('/run/ultimate-u1-ace-link-vm-lab')
SSH_CONFIG = STATE / 'ssh/config'
TARGET = 'root@127.0.0.1'
VERSION = '0.1.6'
ARCHIVE_SHA = '2c018540275022a9e821a19bbe78df622e34df6f9b2de07f675ab88150250bd3'
RECEIPT = Path('/userdata/ultimate-u1-ace-link/install-state.json')


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def guard():
    require(sys.platform == 'linux' and os.geteuid() == 0, 'Disposable Linux root VM required')
    for key, value in {'CI': 'true', 'GITHUB_ACTIONS': 'true',
                       'GITHUB_REPOSITORY': 'Alexantry/Ultimate-U1-ACE-link'}.items():
        require(os.environ.get(key) == value, 'Required lab environment is missing: ' + key)
    require(re.fullmatch(r'\d+', os.environ.get('GITHUB_RUN_ID', '')), 'Invalid run identity')
    require(re.fullmatch(r'[a-f0-9]{32}', os.environ.get('U1_ACE_LAB_TOKEN', '')), 'Invalid lab token')
    require(os.readlink('/proc/self/ns/mnt') != os.readlink('/proc/1/ns/mnt'),
            'Run in a private mount namespace')
    require(not STATE.exists(), 'Lab state already exists; do not reuse a guest')
    for command in ('ssh', 'scp', 'ssh-keygen', 'pwsh', 'mount', '/usr/sbin/sshd'):
        require(shutil.which(command), 'Missing VM dependency: ' + command)
    STATE.mkdir(mode=0o700)
    permission = {'schema': 1, 'scope': 'vm-software-flow',
                  'run_id': os.environ['GITHUB_RUN_ID'], 'token': os.environ['U1_ACE_LAB_TOKEN']}
    path = STATE / 'permission.json'
    path.write_text(json.dumps(permission), encoding='utf8')
    path.chmod(0o600)


def run(command, *, check=True, timeout=180, input_text=None):
    result = subprocess.run([str(x) for x in command], input=input_text, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError('Command failed: ' + shlex.join([str(x) for x in command]) +
                           '\n' + result.stdout[-6000:] + '\n' + result.stderr[-6000:])
    return result


def guest(*arguments):
    result = run([sys.executable, LAB / 'guest.py', *arguments])
    return result


def ssh(command, *, check=True, timeout=180):
    # All remote commands target the in-VM loopback server. No LAN target exists.
    return run(['/usr/bin/ssh', '-F', SSH_CONFIG, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', TARGET, command],
               check=check, timeout=timeout)


def remote_json(stage, command, *, check=True):
    require(re.fullmatch(r'/userdata/ultimate-u1-ace-stage-\d{8}-\d{6}-[a-f0-9]{8}', stage),
            'Unexpected production staging directory')
    result = ssh('cd ' + shlex.quote(stage) + ' && python3 installer.py ' + command, check=check)
    if not check:
        return result
    return json.loads(result.stdout)


def spawn(command, log_path):
    stream = log_path.open('w', encoding='utf8')
    process = subprocess.Popen([str(x) for x in command], stdout=stream, stderr=subprocess.STDOUT,
                               start_new_session=True)
    return process, stream


def stop(process):
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)


def extract_release():
    archive = ROOT / 'downloads' / ('Ultimate-U1-ACE-link-v' + VERSION + '.zip')
    require(hashlib.sha256(archive.read_bytes()).hexdigest() == ARCHIVE_SHA, 'Release archive changed')
    destination = STATE / 'package with spaces'
    destination.mkdir()
    prefix = 'Ultimate-U1-ACE-link/'
    with zipfile.ZipFile(archive) as bundle:
        require(bundle.testzip() is None, 'Corrupt archive')
        hashes = {}
        for line in bundle.read(prefix + 'PACKAGE-SHA256SUMS').decode('ascii').splitlines():
            digest, name = line.split('  ', 1)
            require(re.fullmatch('[a-f0-9]{64}', digest), 'Invalid package checksum')
            hashes[name] = digest
        require(len(bundle.namelist()) == len(hashes) + 1, 'Unexpected archive entries')
        for item in bundle.infolist():
            require(item.filename.startswith(prefix) and '..' not in Path(item.filename).parts,
                    'Unsafe archive path')
            require(stat.S_ISREG(item.external_attr >> 16), 'Non-regular archive member')
            name = item.filename[len(prefix):]
            data = bundle.read(item)
            if name != 'PACKAGE-SHA256SUMS':
                require(name in hashes and hashlib.sha256(data).hexdigest() == hashes[name],
                        'Package member checksum mismatch')
            path = destination / item.filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    return destination / prefix, hashes


def configure_ssh():
    directory = STATE / 'ssh'
    directory.mkdir(mode=0o700)
    for name in ('client', 'host'):
        run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', directory / name])
    pub = (directory / 'host.pub').read_text().split()
    (directory / 'known_hosts').write_text('[127.0.0.1]:2222 ' + ' '.join(pub[:2]) + '\n')
    client_config = ('Host 127.0.0.1\n  HostName 127.0.0.1\n  Port 2222\n  User root\n'
                     '  IdentityFile ' + str(directory / 'client') + '\n  IdentitiesOnly yes\n'
                     '  UserKnownHostsFile ' + str(directory / 'known_hosts') + '\n'
                     '  StrictHostKeyChecking yes\n  BatchMode yes\n  ProxyCommand none\n'
                     'Host *\n  ProxyCommand /bin/false\n')
    (directory / 'config').write_text(client_config)
    (directory / 'config').chmod(0o600)
    Path('/run/sshd').mkdir(exist_ok=True)
    variables = ('CI', 'GITHUB_ACTIONS', 'GITHUB_REPOSITORY', 'GITHUB_RUN_ID', 'U1_ACE_LAB_TOKEN')
    values = ' '.join(key + '=' + os.environ[key] for key in variables)
    values += ' PATH=/usr/bin:/bin:/usr/local/bin'
    config = ('Port 2222\nListenAddress 127.0.0.1\nAddressFamily inet\n'
              'HostKey ' + str(directory / 'host') + '\n'
              'PidFile ' + str(directory / 'sshd.pid') + '\n'
              'AuthorizedKeysFile ' + str(directory / 'client.pub') + '\n'
              'PermitRootLogin yes\nPubkeyAuthentication yes\nPasswordAuthentication no\n'
              'KbdInteractiveAuthentication no\nAuthenticationMethods publickey\nUsePAM yes\n'
              'AllowUsers root\nAllowTcpForwarding no\nX11Forwarding no\n'
              'PermitTunnel no\nPermitUserEnvironment no\nPrintMotd no\n'
              'SetEnv ' + values + '\nSubsystem sftp internal-sftp\n')
    path = directory / 'sshd_config'
    path.write_text(config)
    path.chmod(0o600)
    run(['/usr/sbin/sshd', '-t', '-f', path])
    bins = STATE / 'client-bin'
    bins.mkdir()
    for name in ('ssh', 'scp'):
        # Production requests Windows executable names. This lab-only adapter
        # selects the isolated config, then execs the real OpenSSH client with
        # every production argument unchanged. It does not simulate results.
        executable = '/usr/bin/' + name
        require(Path(executable).is_file(), 'Missing real OpenSSH client: ' + executable)
        adapter = bins / (name + '.exe')
        adapter.write_text('#!/bin/sh\nexec ' + shlex.quote(executable) + ' -F ' +
                           shlex.quote(str(SSH_CONFIG)) + ' "$@"\n')
        adapter.chmod(0o700)
    os.environ['PATH'] = str(bins) + ':' + os.environ['PATH']
    return path


def tracked_files(bundle):
    manifest = json.loads((bundle / 'manifest.json').read_text())
    paths = [Path(entry['destination']) for entry in manifest['files']]
    paths += [Path('/oem/.debug'), Path('/usr/local/etc/extended.conf'), RECEIPT]
    config = Path('/oem/printer_data/config')
    paths += list(config.rglob('*.cfg'))
    # Include files that do not exist until first installation.
    paths += [config / 'extended/klipper/ace.cfg', config / 'ace_vars.cfg',
              config / 'extended/klipper/disable-rfid-reader.cfg']
    return sorted(set(paths))


def filesystem_snapshot(bundle):
    result = {}
    for path in tracked_files(bundle):
        if not path.exists() and not path.is_symlink():
            result[str(path)] = None
            continue
        info = path.lstat()
        result[str(path)] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                             'mode': stat.S_IMODE(info.st_mode), 'uid': info.st_uid, 'gid': info.st_gid,
                             'link': os.readlink(path) if path.is_symlink() else None}
    return result


def service_snapshot():
    return json.loads(guest('snapshot').stdout)


def verify_service_reload(before, bundle, status, expected_actions=('stop', 'start')):
    """Require an actual service cycle and a snapshot captured at successful start."""
    after = service_snapshot()
    prior_actions = before['service_actions']
    actions = after['service_actions']
    require(actions[:len(prior_actions)] == prior_actions, 'Service history was changed')
    delta = actions[len(prior_actions):]
    require(delta == list(expected_actions), 'Unexpected service sequence: ' + repr(delta))
    require(after['load_generation'] == before['load_generation'] + 1,
            'Service did not load a new configuration exactly once')
    require(after['service_running'] and after['last_start_error'] is None,
            'Service did not finish with a successful start')
    config = configparser.RawConfigParser(inline_comment_prefixes=('#', ';'))
    config.read('/oem/printer_data/config/extended/klipper/ace.cfg')
    expected_ace = {key: value if key == 'serial' else int(value)
                    for key, value in config.items('ace')} if config.has_section('ace') else {}
    require(after['loaded_settings'].get('ace', {}) == expected_ace,
            'Service retained a stale ACE configuration after file changes')
    require(all(expected_ace.get(key) == value for key, value in status['ace_settings'].items()),
            'Installer status differs from the configuration loaded at start')
    require(after['loaded_port_version'] == status['ace_version'],
            'Installer status differs from the integration version loaded at start')
    manifest = json.loads((bundle / 'manifest.json').read_text())
    expected_hashes = {entry['destination']:
                       hashlib.sha256(Path(entry['destination']).read_bytes()).hexdigest()
                       if Path(entry['destination']).exists() else None
                       for entry in manifest['files']}
    require(after['loaded_module_hashes'] == expected_hashes,
            'Service did not load the current installed module files')
    return {'actions': delta, 'load_generation_before': before['load_generation'],
            'load_generation_after': after['load_generation'],
            'loaded_port_version': after['loaded_port_version'],
            'configuration_and_module_hashes_match_disk': True}


def wizard(bundle, output, language, scenario):
    logs = output / (scenario + '-' + language)
    logs.mkdir()
    result = run(['pwsh', '-NoLogo', '-NoProfile', '-File', LAB / 'drive_wizard.ps1',
                  '-BundleRoot', bundle, '-LogRoot', logs, '-Scenario', scenario,
                  '-Language', language], timeout=300)
    (logs / 'console.txt').write_text(result.stdout + '\n' + result.stderr, encoding='utf8')
    require('LAB_WIZARD_EXIT=0' in result.stdout, 'Wizard success marker missing')
    stages = []
    for path in logs.glob('*.txt'):
        stages += re.findall(r'^Remote stage: (/userdata/ultimate-u1-ace-stage-\d{8}-\d{6}-[a-f0-9]{8})\s*$',
                             path.read_text(encoding='utf-8-sig'), flags=re.M)
    require(len(stages) == 1, 'Production wizard staging record missing')
    return stages[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    require(not output.exists(), 'Use a new evidence directory')
    guard()
    output.mkdir(parents=True)
    result = {'schema': 1, 'classification': 'virtual-machine software workflow validation',
              'release': VERSION, 'archive_sha256': ARCHIVE_SHA, 'passed': False, 'cases': [],
              'real_components': ['Linux filesystem, bind mounts and permissions',
                                  'OpenSSH SSH/SCP through a lab-only configuration selector',
                                  'unmodified published Install.ps1, installer.py, manifest and payload',
                                  'HTTP status requests, service subprocesses, backups and rollback',
                                  'Linux PowerShell process invocation and both prompt languages'],
              'simulated_components': ['Moonraker printer status', 'Klipper lifecycle', 'ACE USB identity and PTY',
                                       'preinstalled exact ACE firmware confirmation'],
              'not_validated': ['Windows PowerShell 5.1 against a remote Linux host', 'interactive SSH passwords',
                                'U1 ARM firmware boot or touchscreen update', 'real Klipper/MCU startup',
                                'ACE firmware flashing and real USB timing', 'NFC RF and physical filament transport']}
    processes = []
    streams = []
    try:
        bundle, original_hashes = extract_release()
        guest('setup')
        ready = STATE / 'guest-ready'
        process, stream = spawn([sys.executable, LAB / 'guest.py', 'serve', '--ready-file', ready], output / 'guest.txt')
        processes.append(process); streams.append(stream)
        for _ in range(100):
            if ready.exists(): break
            require(process.poll() is None, 'Guest service stopped before readiness')
            time.sleep(.1)
        require(ready.exists(), 'Guest did not become ready')
        config = configure_ssh()
        process, stream = spawn(['/usr/sbin/sshd', '-D', '-e', '-f', config], output / 'sshd.txt')
        processes.append(process); streams.append(stream)
        for _ in range(40):
            probe = ssh('id -u', check=False, timeout=10)
            if probe.returncode == 0: break
            require(process.poll() is None, 'Loopback sshd stopped')
            time.sleep(.1)
        require(probe.returncode == 0 and probe.stdout.strip() == '0', 'Strict loopback SSH authentication failed')
        ssh("python3 -c 'import serial; print(serial.__version__)'")
        baseline = filesystem_snapshot(bundle)
        result['cases'].append({'name': 'release_integrity_and_real_strict_ssh', 'passed': True})

        service_before = service_snapshot()
        stage = wizard(bundle, output, 'en', 'fresh')
        status = remote_json(stage, 'status')
        require(status['managed'] and status['filament_detection'] == 'external' and
                status['ace_settings']['retract_length'] == 1370, 'First installation did not become managed')
        guest('assert', 'installed')
        service_evidence = verify_service_reload(service_before, bundle, status)
        result['cases'].append({'name': 'english_fresh_wizard_real_transfer_and_install', 'passed': True,
                                'service': service_evidence})

        settings = json.loads((bundle / 'config/settings.example.json').read_text())
        settings.update(calibrated_acknowledged=True, apply_existing_settings=True,
                        retract_length=1370, feed_length=1370, fast_load_length=1210,
                        forward_takeup_length=210)
        settings_path = STATE / 'settings.lab.json'
        settings_path.write_text(json.dumps(settings))
        run(['/usr/bin/scp', '-F', SSH_CONFIG, '-O', settings_path, TARGET + ':' + stage + '/config/settings.lab.json'])
        service_before = service_snapshot()
        change = remote_json(stage, 'install --settings config/settings.lab.json')
        require(change['installed'] and change['settings']['forward_takeup_length'] == 210,
                'Custom parameters did not install')
        status = remote_json(stage, 'status')
        custom_state = status['ace_settings']
        service_evidence = verify_service_reload(service_before, bundle, status)
        manifest = json.loads((bundle / 'manifest.json').read_text())
        module_hashes = {entry['destination']: hashlib.sha256(Path(entry['destination']).read_bytes()).hexdigest()
                         for entry in manifest['files']}
        result['cases'].append({'name': 'explicit_parameter_update_through_real_cli', 'passed': True,
                                'service': service_evidence})

        service_before = service_snapshot()
        stage = wizard(bundle, output, 'zh', 'update')
        status = remote_json(stage, 'status')
        require(status['ace_settings'] == custom_state, 'Ordinary update changed custom parameters')
        require(all(hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
                    for path, digest in module_hashes.items()), 'Update changed staged-load module constants')
        service_evidence = verify_service_reload(service_before, bundle, status)
        result['cases'].append({'name': 'chinese_update_preserves_parameters', 'passed': True,
                                'service': service_evidence})

        for state, expected in (('busy', 'Printer must be idle'), ('hot', 'Heater or motion is active')):
            guest('set-state', state)
            before = filesystem_snapshot(bundle)
            refused = remote_json(stage, 'install --settings config/settings.local.json', check=False)
            require(refused.returncode != 0 and expected in refused.stderr, state + ' was not refused')
            require(filesystem_snapshot(bundle) == before, 'Refused state changed managed files')
            guest('assert', 'guarded')
            guest('set-state', 'idle')
            result['cases'].append({'name': state + '_guard_real_cli_no_changes', 'passed': True})

        before = filesystem_snapshot(bundle)
        lock_code = ("import fcntl,sys; f=open('/userdata/ultimate-u1-ace-link/installer.lock','a'); "
                     "fcntl.flock(f.fileno(),fcntl.LOCK_EX); print('LOCKED',flush=True); sys.stdin.readline()")
        holder = subprocess.Popen(['/usr/bin/ssh', '-F', str(SSH_CONFIG), '-o', 'BatchMode=yes', TARGET,
                                   'python3 -c ' + shlex.quote(lock_code)],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            require(holder.stdout.readline().strip() == 'LOCKED', 'Independent lock holder failed')
            refused = remote_json(stage, 'install --settings config/settings.local.json', check=False)
            require(refused.returncode != 0 and ('temporarily unavailable' in refused.stderr or
                    'would block' in refused.stderr), 'Concurrent installer was not blocked by flock')
            require(filesystem_snapshot(bundle) == before, 'Concurrent refusal changed managed files')
        finally:
            holder.communicate('\n', timeout=15)
        result['cases'].append({'name': 'independent_process_lock_blocks_second_install', 'passed': True})

        before = filesystem_snapshot(bundle)
        guest('set-state', 'service-failure')
        service_before = service_snapshot()
        failed = remote_json(stage, 'install --settings config/settings.local.json', check=False)
        require(failed.returncode != 0 and 'Automatic rollback VERIFIED' in failed.stderr,
                'One failed service start did not trigger verified rollback')
        require(filesystem_snapshot(bundle) == before, 'Automatic rollback did not restore exact managed files')
        status = remote_json(stage, 'status')
        require(status['ace_settings'] == custom_state, 'Failure changed loaded settings')
        guest('assert', 'service-recovered')
        guest('assert', 'unchanged')
        service_evidence = verify_service_reload(service_before, bundle, status,
                                                ('stop', 'start', 'stop', 'start'))
        result['cases'].append({'name': 'service_start_failure_restores_files_and_receipt', 'passed': True,
                                'service': service_evidence})

        rollback_service_evidence = []
        for _ in range(3):
            service_before = service_snapshot()
            restored = remote_json(stage, 'rollback')
            require(restored['rolled_back'], 'Rollback did not report success')
            rollback_service_evidence.append(verify_service_reload(service_before, bundle,
                                                                   remote_json(stage, 'status')))
        require(not remote_json(stage, 'status')['managed'], 'Rollback chain did not reach uninstalled state')
        require(filesystem_snapshot(bundle) == baseline, 'Rollback did not restore original bytes and metadata')
        guest('assert', 'rolled-back')
        result['cases'].append({'name': 'rollback_chain_restores_original_files_permissions_and_mode', 'passed': True,
                                'service_cycles': rollback_service_evidence})

        service_before = service_snapshot()
        stage = wizard(bundle, output, 'zh', 'fresh')
        guest('assert', 'installed')
        status = remote_json(stage, 'status')
        require(status['ace_settings']['forward_takeup_length'] == 0,
                'Fresh reinstall did not disable take-up')
        service_evidence = verify_service_reload(service_before, bundle, status)
        result['cases'].append({'name': 'chinese_fresh_reinstall_after_rollback', 'passed': True,
                                'service': service_evidence})
        for name, digest in original_hashes.items():
            require(hashlib.sha256((bundle / name).read_bytes()).hexdigest() == digest,
                    'Production package changed during validation: ' + name)
        guest_evidence = json.loads(guest('snapshot').stdout)
        require(guest_evidence['serial_bytes'] == 0, 'KEEP-only workflow unexpectedly wrote to the simulated serial port')
        require(guest_evidence['http_write_attempts'] == 0, 'Unexpected printer HTTP write request')
        result['ace_serial_bytes'] = 0
        result['printer_http_write_attempts'] = 0
        result['bind_mount_verified'] = guest_evidence['bind_mount_verified']
        result['service_lifecycle'] = {key: guest_evidence[key] for key in
                                      ('service_actions', 'load_generation', 'service_running',
                                       'loaded_settings', 'loaded_port_version', 'loaded_module_hashes',
                                       'last_start_error')}
        result['cases'].append({'name': 'published_production_package_remains_unmodified', 'passed': True})
        result['passed'] = True
    except Exception as exc:
        result['failure'] = str(exc)
        (output / 'failure.txt').write_text(traceback.format_exc(), encoding='utf8')
    finally:
        for process in reversed(processes):
            with contextlib.suppress(Exception): stop(process)
        for stream in streams: stream.close()
        result['case_count'] = len(result['cases'])
        (output / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
        print(json.dumps(result, ensure_ascii=False))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
