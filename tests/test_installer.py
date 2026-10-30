"""Installer transaction tests use only temporary files and virtual services."""
import copy
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('u1_installer', Path(__file__).resolve().parents[1] / 'installer.py')
I = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(I)

ACE = ('class BunnyAce:\n' + ''.join('    %s = %s\n' % (name, value)
                                    for name, value in I.CONSTANTS.values())).encode()


class FakeHost(I.Host):
    def __init__(self, root):
        super().__init__(root, self.snapshot, self.service_action)
        self.actions = []; self.active = False; self.ready_failure = False
        self.snapshot_override = None; self.fail_write = None
        self.initial = {
            'webhooks': {'state': 'ready'}, 'print_stats': {'state': 'standby'},
            'idle_timeout': {'state': 'Idle'},
            'machine_state_manager': {'main_state': 0, 'action_code': 0},
            'print_task_config': {'filament_vendor_0': 'Bambu', 'filament_type_0': 'PLA Matte'},
            'configfile': {'settings': {}}, '_config_file': I.CONFIG_ROOT + '/printer.cfg'}
        for name in ('extruder', 'extruder1', 'extruder2', 'extruder3', 'heater_bed'):
            self.initial[name] = {'target': 0, 'power': 0, 'temperature': 25}
        for i in range(4):
            self.initial['filament_motion_sensor e%d_filament' % i] = {'filament_detected': False}

    def persistence(self):
        # Real bind mounts cannot be created in a cross-platform unit test.
        I.require(self.path('/oem/.printer_data').is_file(), 'Missing test persistence marker')

    def snapshot(self):
        s = copy.deepcopy(self.initial)
        cfg = self.read(I.ACE_CONFIG)
        if cfg is not None:
            parser = I.configparser.RawConfigParser(inline_comment_prefixes=('#', ';'))
            parser.read_string(cfg.decode())
            values = {k: parser.get('ace', k) for k in I.CONFIG_KEYS if parser.has_option('ace', k)}
            for key in values:
                if key != 'serial': values[key] = int(values[key])
            s['configfile']['settings']['ace'] = values
            s['ace'] = {'connected': True, 'status_fresh': True, 'status': 'ready',
                'last_error': None, 'feed_assist_index': -1, 'preload_queue': [],
                'dryer_status': {'status': 'stop'}, 'rfid_sync': [None]*4,
                'gate_status': [0, 0, 0, 0], 'port_version': 'port7' if self.active else 'prior'}
        if self.snapshot_override:
            self.snapshot_override(s)
        return s

    def service_action(self, action):
        self.actions.append(action)
        if action == 'start':
            self.active = self.read(I.DESTINATIONS['ace.py']) is not None

    def write(self, name, data, metadata=None):
        if self.fail_write == name:
            self.fail_write = None
            raise OSError('simulated atomic-write failure')
        if metadata is not None:
            # The virtual printer's root-owned backup files belong to the test
            # account on the host. Keep actual chmod/fsync/replace operations;
            # ordinary Linux CI must not need permission to chown files to root.
            metadata = dict(metadata,
                            uid=os.getuid() if hasattr(os, 'getuid') else metadata['uid'],
                            gid=os.getgid() if hasattr(os, 'getgid') else metadata['gid'])
        super().write(name, data, metadata)


class Fixture:
    def __init__(self, directory):
        self.base = Path(directory)
        self.bundle = self.base / 'bundle'; self.bundle.mkdir()
        (self.bundle / 'payload').mkdir()
        self.host = FakeHost(self.base / 'root')
        self.put('/oem/.printer_data', b'')
        self.put('/identity', b'exact firmware')
        self.put(I.CONFIG_ROOT + '/printer.cfg', b'[printer]\n[include extended/klipper/*.cfg]\n')
        self.put(I.CONFIG_ROOT + '/extended/openrfid_user.cfg', b'private NFC settings\n')
        self.manifest = {'schema': 1, 'target_firmware': I.TARGET, 'version': 'port7',
            'firmware_checks': [{'path': '/identity', 'sha256': I.digest(b'exact firmware')}],
            'firmware_markers': [], 'files': []}
        for name, value in (('FULLVERSION', I.TARGET), ('BASE_VERSION', 'base'), ('BUILD_VERSION', 'build')):
            self.put('/etc/' + name, (value + '\n').encode())
            self.manifest['firmware_markers'].append({'path': '/etc/' + name, 'value': value})
        for name, destination in I.DESTINATIONS.items():
            new = ACE if name == 'ace.py' else ('# reviewed ' + name + '\n').encode()
            old = None if name == 'ace.py' else ('# original ' + name + '\n').encode()
            (self.bundle / 'payload' / name).write_bytes(new)
            if old is not None: self.put(destination, old)
            self.manifest['files'].append({'id': name, 'payload': 'payload/' + name,
                'destination': destination, 'sha256': I.digest(new),
                'accepted_source_sha256': [I.digest(old) if old is not None else None]})
        self.write_manifest()
        self.installer = I.Installer(self.bundle, self.host)
        self.settings = dict(I.DEFAULTS, calibrated_acknowledged=True)

    def put(self, name, data):
        p = self.host.path(name); p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)

    def write_manifest(self):
        (self.bundle / 'manifest.json').write_bytes(I.json_bytes(self.manifest))

    def bytes(self):
        return {str(p.relative_to(self.host.root)): p.read_bytes()
                for p in self.host.root.rglob('*') if p.is_file() and 'ultimate-u1-ace-link' not in str(p)}

    def install(self):
        with patch.object(I.time, 'sleep', return_value=None):
            return self.installer.install(self.settings)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.f = Fixture(self.temp.name)

    def test_virtual_root_ownership_maps_to_test_account_without_skipping_write(self):
        with patch.object(I.os, 'getuid', return_value=1234, create=True), \
                patch.object(I.os, 'getgid', return_value=5678, create=True), \
                patch.object(I.os, 'chown', create=True) as chown, \
                patch.object(I.os, 'chmod', wraps=I.os.chmod) as chmod:
            self.f.host.write('/ownership-test', b'atomic bytes',
                              {'mode': 0o600, 'uid': 0, 'gid': 0})
        self.assertEqual(self.f.host.read('/ownership-test'), b'atomic bytes')
        chown.assert_called_once()
        self.assertEqual(chown.call_args.args[1:], (1234, 5678))
        chmod.assert_called_once_with(chown.call_args.args[0], 0o600)

    def test_check_does_not_write_or_restart(self):
        before = self.f.bytes(); plan = self.f.installer.prepare(self.f.settings)
        self.assertEqual(before, self.f.bytes()); self.assertEqual(self.f.host.actions, [])
        self.assertEqual(plan['settings']['forward_takeup_length'], 0)
        self.assertEqual(plan['changes'][I.DESTINATIONS['ace.py']], ACE)

    def test_clean_install_and_explicit_rollback_restore_original_bytes(self):
        before = self.f.bytes(); outcome = self.f.install()
        self.assertTrue(outcome['installed'])
        self.assertEqual(self.f.host.actions, ['stop', 'start'])
        self.assertIn(b'[save_variables]', self.f.host.read(I.ACE_CONFIG))
        with patch.object(I.time, 'sleep', return_value=None):
            self.f.installer.rollback()
        self.assertEqual(before, self.f.bytes())
        self.assertIsNone(self.f.host.read(I.RECEIPT))

    def test_acknowledgement_is_required_before_mutation(self):
        self.f.settings['calibrated_acknowledged'] = False
        before = self.f.bytes()
        with self.assertRaisesRegex(RuntimeError, 'calibrated_acknowledged'):
            self.f.install()
        self.assertEqual(before, self.f.bytes()); self.assertEqual(self.f.host.actions, [])

    def test_unknown_core_and_wrong_firmware_fail_before_service(self):
        for path in (I.DESTINATIONS['extruder.py'], '/identity', '/etc/FULLVERSION'):
            with self.subTest(path=path):
                original = self.f.host.read(path); self.f.put(path, b'unreviewed')
                with self.assertRaises(RuntimeError): self.f.install()
                self.assertEqual(self.f.host.actions, []); self.f.put(path, original)

    def test_tampered_payload_is_not_installed(self):
        p = self.f.bundle / 'payload' / 'ace.py'; p.write_bytes(ACE + b'# changed\n')
        with self.assertRaisesRegex(RuntimeError, 'Payload hash'): self.f.install()
        self.assertEqual(self.f.host.actions, [])

    def test_active_print_or_heat_is_refused(self):
        for condition in ('printing', 'heating'):
            with self.subTest(condition=condition):
                def change(s):
                    if condition == 'printing': s['print_stats']['state'] = 'printing'
                    else: s['extruder']['target'] = 210
                self.f.host.snapshot_override = change
                with self.assertRaises(RuntimeError): self.f.install()
                self.assertEqual(self.f.host.actions, [])

    def test_partial_write_failure_rolls_back_all_files(self):
        before = self.f.bytes(); self.f.host.fail_write = I.DESTINATIONS['filament_detect.py']
        with patch.object(I.time, 'sleep', return_value=None):
            with self.assertRaisesRegex(OSError, 'simulated'):
                self.f.installer.install(self.f.settings)
        self.assertEqual(before, self.f.bytes())
        self.assertEqual(self.f.host.actions, ['stop', 'stop', 'start'])

    def test_ready_failure_restores_all_originals(self):
        before = self.f.bytes(); real_ready = self.f.installer.ready
        def reject_new(before, version=None, settings=None, timeout=110):
            if version: raise RuntimeError('simulated new startup failure')
            return real_ready(before, version, settings, timeout)
        self.f.installer.ready = reject_new
        with patch.object(I.time, 'sleep', return_value=None):
            with self.assertRaisesRegex(RuntimeError, 'new startup failure'):
                self.f.installer.install(self.f.settings)
        self.assertEqual(before, self.f.bytes())
        self.assertEqual(self.f.host.actions, ['stop', 'start', 'stop', 'start'])

    def test_new_values_only_replace_existing_when_explicitly_selected(self):
        original = I.patch_ace_config(None, {k: I.DEFAULTS[k] for k in I.CONFIG_KEYS}, True)
        original = original.replace(b'retract_length: 1250', b'retract_length: 1400 # measured')
        original += b'\n[gcode_macro USER_MACRO]\ngcode:\n    M118 retained\n'
        self.f.put(I.ACE_CONFIG, original)
        self.f.put(I.CONFIG_ROOT + '/ace_vars.cfg', b'[Variables]\nmy_value = 42\n')
        plan = self.f.installer.prepare(self.f.settings)
        self.assertEqual(plan['settings']['retract_length'], 1400)
        self.assertIn(b'# measured', plan['changes'][I.ACE_CONFIG])
        self.assertIn(b'USER_MACRO', plan['changes'][I.ACE_CONFIG])
        self.assertEqual(plan['changes'][I.ACE_CONFIG].count(b'[save_variables]'), 1)
        self.assertNotIn(I.CONFIG_ROOT + '/ace_vars.cfg', plan['changes'])
        self.f.settings.update(apply_existing_settings=True, forward_takeup_length=300)
        plan = self.f.installer.prepare(self.f.settings)
        self.assertEqual(plan['settings']['retract_length'], 1250)
        self.assertEqual(plan['settings']['forward_takeup_length'], 300)

    def test_existing_separate_save_variables_is_reused_without_duplicate(self):
        self.f.put(I.CONFIG_ROOT + '/extended/klipper/other.cfg',
                   b'[save_variables]\nfilename: ' + (I.CONFIG_ROOT + '/other-vars.cfg').encode() + b'\n')
        self.f.put(I.CONFIG_ROOT + '/other-vars.cfg', b'[Variables]\nuser_value = 7\n')
        plan = self.f.installer.prepare(self.f.settings)
        self.assertNotIn(b'[save_variables]', plan['changes'][I.ACE_CONFIG])
        self.assertIn(I.CONFIG_ROOT + '/other-vars.cfg', plan['protected'])

    def test_duplicate_save_variables_or_unexpected_ace_section_refused(self):
        self.f.put(I.CONFIG_ROOT + '/extended/klipper/other.cfg', b'[ace]\nserial: /dev/ttyACM0\n')
        with self.assertRaisesRegex(RuntimeError, 'unexpected or duplicate'):
            self.f.installer.prepare(self.f.settings)

    def test_configured_constants_are_exact_and_retained_on_managed_update(self):
        self.f.settings.update(fast_load_length=1000, fast_load_speed=150,
                               sensor_load_speed=40, sensor_load_max_length=2200)
        self.f.install()
        data = self.f.host.read(I.DESTINATIONS['ace.py'])
        self.assertIn(b'FAST_LOAD_LENGTH = 1000', data)
        plan = self.f.installer.prepare(dict(I.DEFAULTS, calibrated_acknowledged=True))
        self.assertEqual(plan['changes'][I.DESTINATIONS['ace.py']], data)

    def test_modified_managed_core_blocks_reinstall_and_rollback(self):
        self.f.install(); self.f.host.actions.clear()
        self.f.put(I.DESTINATIONS['ace.py'], b'# unknown local edit\n')
        with self.assertRaisesRegex(RuntimeError, 'Unknown modified core'): self.f.install()
        with self.assertRaisesRegex(RuntimeError, 'Installed files changed'): self.f.installer.rollback()
        self.assertEqual(self.f.host.actions, [])

    def test_settings_limits_and_injection_are_refused(self):
        for kwargs in ({'forward_takeup_length': 501}, {'fast_load_speed': 201},
                       {'sensor_load_speed': 51}, {'serial': '/dev/ttyACM0\n[gcode_macro BAD]'},
                       {'retract_length': 100}, {'fast_load_length': True},
                       {'calibrated_acknowledged': 'true'}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(RuntimeError): I.validate_settings(dict(I.DEFAULTS, **kwargs))

    def test_missing_include_and_duplicate_include_fail_closed(self):
        for data in (b'[printer]\n',
                     b'[include extended/klipper/*.cfg]\n[include extended/klipper/*.cfg]\n'):
            self.f.put(I.CONFIG_ROOT + '/printer.cfg', data)
            self.f.put(I.CONFIG_ROOT + '/extended/klipper/one.cfg', b'[test]\n')
            with self.assertRaises(RuntimeError): self.f.installer.prepare(self.f.settings)

    def test_only_official_printer_data_symlink_mapping_is_allowed(self):
        source = self.f.host.root / 'home/lava/printer_data'
        target = self.f.host.root / 'oem/printer_data'
        source.rename(target)
        try:
            source.symlink_to(target, target_is_directory=True)
        except OSError as exc:
            self.skipTest('Platform does not permit test symlinks: ' + str(exc))
        self.assertEqual(self.f.host.read(I.CONFIG_ROOT + '/printer.cfg'),
                         (target / 'config/printer.cfg').read_bytes())
        self.f.installer.prepare(self.f.settings)
        source.unlink()
        other = self.f.host.root / 'unexpected'; other.mkdir()
        source.symlink_to(other, target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, 'Unexpected symlink'):
            self.f.host.read(I.CONFIG_ROOT + '/printer.cfg')

    def test_offline_recovery_requires_local_ack_and_recovers_without_receipt(self):
        before = self.f.bytes(); result = self.f.install()
        self.f.host.path(I.RECEIPT).unlink()
        original_state = self.f.host.state_reader
        self.f.host.state_reader = lambda: (_ for _ in ()).throw(RuntimeError('API unavailable'))
        with self.assertRaisesRegex(RuntimeError, 'confirm-idle-and-cold'):
            self.f.installer.rollback(result['backup'], offline_recovery=True)
        previous_service = self.f.host.service_runner
        def service(action):
            previous_service(action)
            if action == 'start': self.f.host.state_reader = original_state
        self.f.host.service_runner = service
        with patch.object(I.time, 'sleep', return_value=None):
            self.f.installer.rollback(result['backup'], offline_recovery=True, confirm_idle_and_cold=True)
        self.assertEqual(before, self.f.bytes())

    def test_offline_flag_does_not_override_known_active_print(self):
        self.f.install(); self.f.host.actions.clear()
        self.f.host.snapshot_override = lambda s: s['print_stats'].update(state='printing')
        with self.assertRaisesRegex(RuntimeError, 'Printer must be idle'):
            self.f.installer.rollback(offline_recovery=True, confirm_idle_and_cold=True)
        self.assertEqual(self.f.host.actions, [])

    def test_corrupt_backup_is_rejected_before_stopping_service(self):
        result = self.f.install(); self.f.host.actions.clear()
        self.f.put(I.STATE_ROOT + '/backups/' + result['backup'] + '/1', b'bad backup')
        with self.assertRaisesRegex(RuntimeError, 'Backup content mismatch'):
            self.f.installer.rollback()
        self.assertEqual(self.f.host.actions, [])

    def test_fresh_install_requires_empty_heads_before_any_mutation(self):
        self.f.host.initial['filament_motion_sensor e0_filament']['filament_detected'] = True
        with self.assertRaisesRegex(RuntimeError, 'all four U1 heads empty'):
            self.f.install()
        self.assertEqual(self.f.host.actions, [])

    def test_fresh_empty_slot_metadata_initialization_is_reported(self):
        def update(s):
            if self.f.host.active:
                s['print_task_config']['filament_vendor_0'] = 'Generic'
        self.f.host.snapshot_override = update
        result = self.f.install()
        self.assertTrue(result['fresh_install'])
        self.assertTrue(result['empty_slot_metadata_initialized'])

    def test_existing_ace_metadata_change_is_not_accepted(self):
        self.f.install()
        before = self.f.host.state()
        self.f.host.snapshot_override = lambda s: s['print_task_config'].update(filament_vendor_0='Changed')
        with patch.object(I.time, 'monotonic', side_effect=[0, 0, 200]), patch.object(I.time, 'sleep'):
            with self.assertRaisesRegex(RuntimeError, 'Material metadata changed'):
                self.f.installer.ready(before, 'port7', self.f.settings)

    def test_failed_install_reports_backup_and_verified_restoration(self):
        before = self.f.bytes()
        self.f.host.fail_write = I.DESTINATIONS['filament_detect.py']
        output = io.StringIO()
        with contextlib.redirect_stderr(output), patch.object(I.time, 'sleep', return_value=None):
            with self.assertRaisesRegex(OSError, 'simulated atomic-write failure'):
                self.f.installer.install(self.f.settings)
        self.assertEqual(before, self.f.bytes())
        text = output.getvalue()
        self.assertRegex(text, r'Backup ID: \d{8}T\d{12}Z')
        self.assertIn('Backup directory: ' + I.STATE_ROOT + '/backups/', text)
        self.assertIn('Automatic rollback VERIFIED', text)
        self.assertIn('Original installation error: OSError: simulated atomic-write failure', text)

    def test_failed_restoration_reports_both_errors_and_backup_id(self):
        self.f.host.fail_write = I.DESTINATIONS['filament_detect.py']
        def failed_restore(*args, **kwargs):
            raise RuntimeError('simulated restoration failure')
        self.f.installer.restore = failed_restore
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            with self.assertRaisesRegex(RuntimeError, 'simulated atomic-write failure.*simulated restoration failure') as caught:
                self.f.installer.install(self.f.settings)
        self.assertIsInstance(caught.exception.__cause__, OSError)
        self.assertIn('automatic rollback FAILED', output.getvalue())
        self.assertRegex(output.getvalue(), r'Backup ID: \d{8}T\d{12}Z')


if __name__ == '__main__':
    unittest.main()
