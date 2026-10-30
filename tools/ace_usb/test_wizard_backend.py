"""Offline transaction checks. No printer, USB, firmware download, or worker spawn."""
import contextlib
import copy
import datetime as dt
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import wizard_backend as W


class TestStore(W.Store):
    def __init__(self, root):
        super().__init__(root); self.locked = False

    @contextlib.contextmanager
    def lock(self):
        self.initialize()
        if self.locked: raise W.WizardError('MAINTENANCE_BUSY')
        self.locked = True
        try: yield
        finally: self.locked = False


class FakeHost(W.I.Host):
    def __init__(self, root, existing=True):
        super().__init__(root)
        self.running = True; self.actions = []; self.start_hook = None
        self.fail_start = False
        self.initial = {
            'webhooks': {'state': 'ready'}, 'print_stats': {'state': 'standby'},
            'idle_timeout': {'state': 'Idle'},
            'machine_state_manager': {'main_state': 0, 'action_code': 0},
            'print_task_config': {'filament_vendor_0': 'Generic', 'filament_type_0': 'PLA', 'filament_color_0': 0},
            'configfile': {'settings': {}}, '_config_file': W.I.CONFIG_ROOT + '/printer.cfg'}
        for name in ('extruder', 'extruder1', 'extruder2', 'extruder3', 'heater_bed'):
            self.initial[name] = {'temperature': 25, 'target': 0, 'power': 0}
        for i in range(4):
            self.initial['filament_motion_sensor e%d_filament' % i] = {'filament_detected': False}
        if existing:
            self.initial['ace'] = dict(connected=True, status_fresh=True, status='ready',
                last_error=None, feed_assist_index=-1, preload_queue=[],
                dryer_status={'status': 'stop'}, rfid_sync=[None] * 4, gate_status=[1, 0, 0, 0])
            self.initial['configfile']['settings']['ace'] = {'serial': '/dev/serial/by-id/usb-ANYCUBIC_ACE_fixture-if00'}
        self.candidates = ['/dev/serial/by-id/usb-ANYCUBIC_ACE_fixture-if00']
        self.info = {'model': 'Anycubic Color Engine Pro', 'slots': 4, 'firmware': 'V1.3.856',
                     'boot_firmware': 'V1.0.1', 'id': 'synthetic-unit'}
        self.usb = {'sysfs_port': '/sys/synthetic/usb1/1-2', 'vid': '28e9', 'pid': '018a', 'serial': 'synthetic'}
        self.ace_status = dict(status='ready', slots=[{'index': i, 'status': 'ready' if i == 0 else 'empty'} for i in range(4)],
                               dryer_status={'status': 'stop', 'target_temp': 0})
        self.put(W.I.CONFIG_ROOT + '/printer.cfg', b'unchanged config\n')
        self.put(W.I.CONFIG_ROOT + '/extended/openrfid_user.cfg', b'PRIVATE_PLACEHOLDER_ONLY\n')

    def put(self, name, data):
        p = self.path(name); p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)

    def state(self):
        if not self.running: raise RuntimeError('Klipper stopped')
        return copy.deepcopy(self.initial)

    def get(self, path):
        assert path == '/server/info'
        return {'klippy_connected': self.running}

    def service(self, action):
        self.actions.append(action)
        if action == 'start' and self.fail_start: raise RuntimeError('simulated start failure')
        self.running = action == 'start'
        if self.running and self.start_hook: self.start_hook()

    def dependencies(self): pass
    def persistence(self): pass
    def serial_candidates(self): return self.candidates[:]


class Fixture:
    def __init__(self, root, existing=True):
        self.host = FakeHost(root / 'root', existing)
        self.store = TestStore(root / 'state' / 'ace-firmware')
        self.sessions = []; self.rpc_calls = []; self.spawns = []
        self.clock_value = 0
        fixture = self
        class Session:
            def __init__(self, device, audit, expected_identity=None):
                self.identity = copy.deepcopy(fixture.host.usb)
                if expected_identity is not None and expected_identity != self.identity:
                    raise W.iap.PreparationError('wrong USB')
                self.closed = False; fixture.sessions.append(self)
            def close(self): self.closed = True
            def rpc(self, method, params=None, timeout=1.5):
                fixture.rpc_calls.append(method)
                result = {'get_info': fixture.host.info, 'get_status': fixture.host.ace_status}.get(method, {})
                return {'code': 0, 'result': copy.deepcopy(result)}
        self.engine = W.Engine(store=self.store, host=self.host, session_factory=Session,
                               sleeper=self.sleep, clock=lambda: self.clock_value,
                               alive=lambda record: record.get('worker_stamp') == 'alive')
        self.engine.installer.firmware = Mock()
        self.engine.launch = self.launch
        self.engine.images = Mock(return_value=(b'synthetic image', {
            'sha256': W.prepare_profile.TARGET_SHA256, 'expected_runtime_version': W.TARGET,
            'announced_version': '1.3.863'}))

    def sleep(self, seconds): self.clock_value += max(seconds, .01)

    def launch(self, record, action):
        self.spawns.append(action)
        record.update(worker_pid=os.getpid(), worker_stamp='alive')
        self.store.save(record)

    def prepare(self):
        result = self.engine.prepare(); token = result['operation']
        self.engine.work(token, 'prepare')
        return self.store.load(token)

    def flash(self, record, callback=None):
        def flash_once(session, *args):
            if callback: callback(session)
            else: session.rpc('iap_upgrade', {})
            self.host.info['firmware'] = W.TARGET
            return {'outcome': 'VERSION_CHANGED_AND_READY', 'info': copy.deepcopy(self.host.info),
                    'status': copy.deepcopy(self.host.ace_status), 'flash_readback_verified': False}
        self.engine.start(record['operation'], True, True)
        with patch.object(W.iap, 'flash_once', side_effect=flash_once):
            self.engine.work(record['operation'], 'flash')
        return self.store.load(record['operation'])


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.f = Fixture(self.root)
        self.port_patch = patch.object(W.iap, 'require_unused_device')
        self.port = self.port_patch.start()

    def tearDown(self):
        self.port_patch.stop(); self.temp.cleanup()

    def assert_code(self, code, fn, *args):
        with self.assertRaises(W.WizardError) as caught: fn(*args)
        self.assertEqual(caught.exception.code, code)

    def test_none_result_has_no_side_effect(self):
        self.assertEqual(self.f.engine.result()['state'], 'NONE')
        self.assertFalse(self.f.store.root.exists())
        self.assertFalse(self.f.host.actions)

    def test_prepare_is_detached_then_restores_known_source(self):
        record = self.f.prepare()
        self.assertEqual(record['state'], 'PREPARED')
        self.assertTrue(record['ready'] and record['service_restored'])
        self.assertEqual(self.f.host.actions, ['stop', 'start'])
        self.assertEqual(self.f.spawns, ['prepare'])
        self.assertNotIn('iap_upgrade', self.f.rpc_calls)
        self.assertTrue(all(s.closed for s in self.f.sessions))

    def test_fresh_u1_without_host_integration_supported(self):
        self.f = Fixture(self.root / 'fresh', existing=False)
        self.assertEqual(self.f.prepare()['state'], 'PREPARED')

    def test_unknown_source_is_reported_and_restored(self):
        self.f.host.info['firmware'] = 'V1.3.900'
        result = self.f.prepare()
        self.assertEqual(result['state'], 'UNSUPPORTED')
        self.assertTrue(result['ready'])
        self.assert_code('FLASH_NOT_PREPARED', self.f.engine.start, result['operation'], True, True)

    def test_wrong_boot_source_refuses(self):
        self.f.host.info['boot_firmware'] = 'V2.0.0'
        self.assertEqual(self.f.prepare()['state'], 'UNSUPPORTED')

    def test_target_version_alone_is_not_image_proof(self):
        self.f.host.info['firmware'] = W.TARGET
        result = self.f.prepare()
        self.assertEqual(result['state'], 'ALREADY_TARGET')
        self.assertFalse(result['verified_installation_receipt'])
        self.assert_code('FLASH_NOT_PREPARED', self.f.engine.start, result['operation'], True, True)

    def test_source_busy_or_heated_never_stops_or_probes(self):
        for kind in ('heated', 'printing', 'assist'):
            f = Fixture(self.root / kind)
            if kind == 'heated': f.host.initial['extruder']['target'] = 200
            elif kind == 'printing': f.host.initial['print_stats']['state'] = 'printing'
            else: f.host.initial['ace']['feed_assist_index'] = 0
            result = f.prepare()
            self.assertEqual(result['state'], 'FAILED_SAFE')
            self.assertFalse(f.host.actions); self.assertFalse(f.sessions)

    def test_download_failure_never_stops_service(self):
        self.f.engine.images.side_effect = ValueError('bad download hash')
        result = self.f.prepare()
        self.assertEqual(result['state'], 'FAILED_SAFE')
        self.assertFalse(self.f.host.actions)

    def test_multiple_devices_no_guess(self):
        self.f.host.candidates.append('/dev/another')
        result = self.f.prepare()
        self.assertEqual(result['code'], 'ACE_INTERFACE_AMBIGUOUS')
        self.assertFalse(self.f.sessions)

    def test_dryer_or_nfc_busy_probe_leaves_control_stopped(self):
        self.f.host.ace_status['slots'][0]['status'] = 'identifying'
        result = self.f.prepare()
        self.assertEqual(result['state'], 'NEEDS_ATTENTION')
        self.assertFalse(self.f.host.running)
        self.assertFalse(result['probe_safe'])

    def test_wrong_usb_vendor_refuses(self):
        self.f.host.usb['vid'] = 'ffff'
        result = self.f.prepare()
        self.assertEqual(result['code'], 'ACE_USB_IDENTITY_REJECTED')
        self.assertFalse(self.f.host.running)

    def test_closed_prepare_does_not_allow_new_transaction(self):
        result = self.f.engine.prepare()
        self.assert_code('ACTIVE_OPERATION', self.f.engine.prepare)
        self.assertEqual(self.f.store.load()['operation'], result['operation'])

    def test_start_requires_both_explicit_confirmations(self):
        result = self.f.prepare()
        self.assert_code('CONFIRMATION_REQUIRED', self.f.engine.start, result['operation'], True, False)
        self.assertEqual(self.f.spawns, ['prepare'])

    def test_duplicate_start_cannot_replay(self):
        result = self.f.prepare()
        self.f.engine.start(result['operation'], True, True)
        self.assert_code('FLASH_NOT_PREPARED', self.f.engine.start, result['operation'], True, True)
        self.assertEqual(self.f.spawns.count('flash'), 1)
        self.assert_code('ACTIVE_OPERATION', self.f.engine.prepare)

    def test_stale_confirmation_refused_before_stopping(self):
        result = self.f.prepare()
        result['prepared_at_utc'] = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)).isoformat()
        self.f.store.save(result)
        self.assert_code('PREPARATION_EXPIRED', self.f.engine.start, result['operation'], True, True)
        self.assertEqual(self.f.host.actions, ['stop', 'start'])

    def test_public_result_never_exposes_private_state(self):
        record = self.f.prepare()
        result = self.f.engine.result(record['operation'])
        encoded = json.dumps(result)
        self.assertNotIn('PRIVATE_PLACEHOLDER', encoded)
        self.assertNotIn('synthetic-unit', encoded)
        self.assertNotIn('usb_identity', encoded)
        self.assertNotIn('files', result)

    def test_valid_flash_once_then_restore(self):
        record = self.f.prepare()
        result = self.f.flash(record)
        self.assertEqual(result['state'], 'SUCCEEDED')
        self.assertTrue(result['flash_attempted'] and result['ready'])
        self.assertEqual(self.f.rpc_calls.count('iap_upgrade'), 1)
        self.assertTrue((self.f.store.root / 'last-success.json').is_file())
        profile = W.read_json(self.f.store.directory(record['operation']) / 'reviewed-profile.json')
        self.assertTrue(all(profile['checks'].values()))

    def test_durable_marker_precedes_first_iap(self):
        record = self.f.prepare()
        def callback(session):
            original = session.session.rpc
            def rpc(method, params=None, timeout=1.5):
                if method == 'iap_upgrade':
                    self.assertTrue(self.f.store.load()['flash_attempted'])
                return original(method, params, timeout)
            session.session.rpc = rpc
            session.rpc('iap_upgrade', {})
        self.assertEqual(self.f.flash(record, callback)['state'], 'SUCCEEDED')

    def test_iap_failure_never_restarts_or_rolls_back(self):
        record = self.f.prepare()
        def callback(session):
            session.rpc('iap_upgrade', {})
            raise OSError('lost IAP response')
        result = self.f.flash(record, callback)
        self.assertEqual(result['state'], 'NEEDS_ATTENTION')
        self.assertTrue(result['flash_attempted'])
        self.assertFalse(self.f.host.running)
        self.assertEqual(self.f.host.actions.count('start'), 1)
        self.assert_code('RECOVERY_REFUSED', self.f.engine.recover, record['operation'])

    def test_slot_activity_after_fresh_probe_blocks_iap(self):
        record = self.f.prepare()
        def callback(session):
            self.f.host.ace_status['slots'][1]['status'] = 'identifying'
            session.rpc('iap_upgrade', {})
        result = self.f.flash(record, callback)
        self.assertNotIn('iap_upgrade', self.f.rpc_calls)
        self.assertFalse(result['flash_attempted'])

    def test_configuration_modified_between_prepare_and_start_refused(self):
        record = self.f.prepare()
        self.f.host.put(W.I.CONFIG_ROOT + '/printer.cfg', b'changed config')
        result = self.f.flash(record)
        self.assertEqual(result['code'], 'CONFIG_CHANGED')
        self.assertNotIn('iap_upgrade', self.f.rpc_calls)

    def test_source_changed_after_confirmation_never_flashes(self):
        record = self.f.prepare(); self.f.host.info['firmware'] = 'V1.3.999'
        result = self.f.flash(record)
        self.assertEqual(result['code'], 'SOURCE_CHANGED')
        self.assertNotIn('iap_upgrade', self.f.rpc_calls)

    def test_changed_identity_refuses(self):
        record = self.f.prepare(); self.f.host.usb['serial'] = 'different-unit'
        result = self.f.flash(record)
        self.assertEqual(result['state'], 'NEEDS_ATTENTION')
        self.assertNotIn('iap_upgrade', self.f.rpc_calls)
        self.assertFalse(self.f.host.running)

    def test_fresh_u1_readiness_rechecked_before_flash_stop(self):
        record = self.f.prepare(); self.f.host.initial['heater_bed']['temperature'] = 80
        result = self.f.flash(record)
        self.assertEqual(result['state'], 'FAILED_SAFE')
        self.assertEqual(self.f.host.actions, ['stop', 'start'])

    def test_nfc_nonempty_upgrade_needs_review(self):
        self.f.host.start_hook = lambda: self.f.host.initial['print_task_config'].update(filament_vendor_0='Bambu')
        result = self.f.prepare()
        self.assertEqual(result['state'], 'PREPARED')
        self.assertTrue(result['needs_material_review'])
        self.assertEqual(result['material_changes'][0]['after'], 'Bambu')

    def test_empty_or_none_material_loss_never_accepts(self):
        for index, value in enumerate(('', 'NONE', None)):
            f = Fixture(self.root / ('loss' + str(index)))
            f.host.start_hook = lambda f=f, value=value: f.host.initial['print_task_config'].update(filament_type_0=value)
            result = f.prepare()
            self.assertEqual(result['state'], 'NEEDS_ATTENTION')
            self.assertEqual(result['code'], 'MATERIAL_LOST')
            self.assertFalse(f.host.running)

    def test_black_color_and_false_are_not_empty(self):
        self.assertTrue(W.material_preserved({'color': 0, 'flag': False}, {'color': 0, 'flag': False}))
        self.assertFalse(W.material_preserved({'color': 0}, {}))

    def test_nested_material_loss_refused(self):
        self.assertFalse(W.material_preserved({'types': ['PLA', 'PETG']}, {'types': ['PLA', 'NONE']}))
        self.assertFalse(W.material_preserved({'types': {'a': 'PLA'}}, {'types': {}}))
        self.assertFalse(W.material_preserved({'type': 'PLA'}, {'type': False}))
        self.assertFalse(W.material_preserved({'type': 'PLA'}, {'type': 0}))
        self.assertFalse(W.material_preserved({'types': ['PLA']}, {'types': 'PLA'}))
        self.assertFalse(W.material_preserved({'types': {'a': 'PLA'}}, {'types': 'PLA'}))
        self.assertFalse(W.material_preserved({'types': ['PLA']}, {'types': ['PLA', 'PETG']}))
        self.assertFalse(W.material_preserved({'types': []}, {'types': {}}))
        self.assertFalse(W.material_preserved({'types': {}}, {'types': []}))
        self.assertFalse(W.material_preserved({'type': None}, {}))

    def test_sub_type_and_nonvisual_material_updates_are_reviewable(self):
        before = {'filament_sub_type': ['PLA Basic'] * 4, 'filament_vendor': ['Bambu'] * 4}
        after = copy.deepcopy(before); after['filament_sub_type'][0] = 'PLA Matte'
        self.assertEqual(W.material_summary(before, after)[0]['field'], 'filament_sub_type')
        after = copy.deepcopy(before); after['filament_spool_id'] = ['private-id'] * 4
        summary = W.material_summary(before, after)
        self.assertTrue(summary)
        self.assertNotIn('private-id', json.dumps(summary))

    def test_stage_path_or_code_change_cannot_start_prepared_flash(self):
        record = self.f.prepare()
        altered = copy.deepcopy(record['stage'])
        altered['directory'] += '-another-stage'
        with patch.object(self.f.engine, 'stage', return_value=altered):
            self.assert_code('STAGE_CHANGED', self.f.engine.start, record['operation'], True, True)
        altered = copy.deepcopy(record['stage'])
        altered['files']['tools/ace_usb/protocol.py'] = '0' * 64
        with patch.object(self.f.engine, 'stage', return_value=altered):
            self.assert_code('STAGE_CHANGED', self.f.engine.start, record['operation'], True, True)
        self.assertEqual(self.f.spawns, ['prepare'])

    def test_stage_changed_after_confirmation_refuses_before_iap(self):
        record = self.f.prepare()
        altered = copy.deepcopy(record['stage'])
        altered['files']['tools/ace_usb/protocol.py'] = '0' * 64
        def callback(session):
            with patch.object(self.f.engine, 'stage', return_value=altered):
                session.rpc('iap_upgrade', {})
        result = self.f.flash(record, callback)
        self.assertEqual(result['code'], 'STAGE_CHANGED')
        self.assertFalse(result['flash_attempted'])
        self.assertNotIn('iap_upgrade', self.f.rpc_calls)

    def test_empty_or_boolean_ace_id_refused(self):
        for index, value in enumerate(('', None, False)):
            f = Fixture(self.root / ('identity' + str(index))); f.host.info['id'] = value
            self.assertEqual(f.prepare()['code'], 'INVALID_ACE_ID')
            self.assertFalse(f.host.running)

    def test_fresh_without_host_still_binds_inlet_status(self):
        self.f = Fixture(self.root / 'nohost', existing=False)
        record = self.f.prepare()
        self.f.host.ace_status['slots'][0]['status'] = 'empty'
        result = self.f.flash(record)
        self.assertEqual(result['code'], 'ACE_GATE_CHANGED')
        self.assertFalse(result['flash_attempted'])
        self.assertFalse(self.f.host.running)

    def test_final_pre_iap_inlet_change_cannot_start(self):
        record = self.f.prepare()
        def callback(session):
            self.f.host.ace_status['slots'][0]['status'] = 'empty'
            session.rpc('iap_upgrade', {})
        result = self.f.flash(record, callback)
        self.assertEqual(result['code'], 'ACE_GATE_CHANGED')
        self.assertFalse(result['flash_attempted'])
        self.assertEqual(result['state'], 'NEEDS_ATTENTION')
        self.assertFalse(self.f.host.running)

    def test_target_inlet_change_after_write_keeps_service_stopped(self):
        record = self.f.prepare()
        def callback(session):
            session.rpc('iap_upgrade', {})
            self.f.host.ace_status['slots'][0]['status'] = 'empty'
        result = self.f.flash(record, callback)
        self.assertEqual(result['code'], 'ACE_GATE_CHANGED')
        self.assertTrue(result['flash_attempted'])
        self.assertFalse(self.f.host.running)

    def test_target_busy_slot_after_write_keeps_service_stopped(self):
        record = self.f.prepare()
        def callback(session):
            session.rpc('iap_upgrade', {})
            self.f.host.ace_status['slots'][0]['status'] = 'identifying'
        result = self.f.flash(record, callback)
        self.assertEqual(result['code'], 'ACE_NOT_IDLE')
        self.assertTrue(result['flash_attempted'])
        self.assertFalse(self.f.host.running)

    def test_restore_failure_after_write_does_not_replay(self):
        record = self.f.prepare(); self.f.host.fail_start = True
        result = self.f.flash(record)
        self.assertEqual(result['state'], 'NEEDS_ATTENTION')
        self.assertTrue(result['flash_attempted'])
        self.assertFalse(self.f.host.running)
        self.assertEqual(self.f.rpc_calls.count('iap_upgrade'), 1)

    def test_diagnostic_disk_error_does_not_skip_stop_after_iap_failure(self):
        record = self.f.prepare()
        original = W.write_json
        def write(path, value):
            if Path(path).name.startswith('failure-'): raise OSError('disk full')
            return original(path, value)
        def callback(session):
            session.rpc('iap_upgrade', {})
            raise OSError('lost IAP response')
        with patch.object(W, 'write_json', side_effect=write):
            result = self.f.flash(record, callback)
        self.assertEqual(result['state'], 'NEEDS_ATTENTION')
        self.assertFalse(self.f.host.running)

    def test_non_cfg_save_variables_are_protected(self):
        path = W.I.CONFIG_ROOT + '/transport-state.txt'
        self.f.host.initial['configfile']['settings']['save_variables'] = {'filename': path}
        self.f.host.put(path, b'[Variables]\nparking = 0\n')
        record = self.f.prepare()
        self.f.host.put(path, b'[Variables]\nparking = 999\n')
        result = self.f.flash(record)
        self.assertEqual(result['code'], 'CONFIG_CHANGED')
        self.assertFalse(result['flash_attempted'])

    def test_prior_success_receipt_requires_fresh_matching_probe(self):
        success = self.f.flash(self.f.prepare())
        self.assertEqual(success['state'], 'SUCCEEDED')
        record = self.f.prepare()
        self.assertEqual(record['state'], 'ALREADY_TARGET')
        self.assertTrue(record['verified_installation_receipt'])
        self.f.host.usb['serial'] = 'another-unit'
        self.assertFalse(self.f.prepare()['verified_installation_receipt'])

    def test_old_success_receipt_not_current_proof(self):
        self.f.flash(self.f.prepare())
        path = self.f.store.root / 'last-success.json'
        receipt = W.read_json(path)
        receipt['captured_at_utc'] = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=2)).isoformat()
        W.write_json(path, receipt)
        self.assertFalse(self.f.prepare()['verified_installation_receipt'])

    def test_dead_worker_result_is_readonly_and_unknown(self):
        record = self.f.engine.prepare()
        stored = self.f.store.load()
        stored.update(worker_stamp='dead', updated_at_utc=(dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=20)).isoformat())
        # save() would refresh the timestamp; emulate a crashed durable record.
        W.write_json(self.f.store.directory(record['operation']) / 'state.json', stored)
        before = (self.f.store.directory(record['operation']) / 'state.json').read_bytes()
        result = self.f.engine.result()
        self.assertEqual(result['state'], 'NEEDS_ATTENTION')
        self.assertEqual(before, (self.f.store.directory(record['operation']) / 'state.json').read_bytes())
        self.assert_code('ACTIVE_OPERATION', self.f.engine.prepare)

    def test_result_wait_is_bounded_and_never_opens_serial(self):
        self.f.engine.prepare()
        result = self.f.engine.result(wait_seconds=30)
        self.assertEqual(result['state'], 'PREPARING')
        self.assertEqual(self.f.clock_value, 30)
        self.assertFalse(self.f.sessions)
        self.assert_code('INVALID_WAIT', self.f.engine.result, None, 31)

    def test_probe_only_recovery_after_prepare_crash(self):
        record = self.f.engine.prepare(); stored = self.f.store.load()
        before = self.f.engine.capture(self.f.host.state())
        W.write_json(self.f.store.directory(record['operation']) / 'before.json', before)
        stored.update(stopped=True, device=self.f.host.candidates[0], worker_stamp='dead')
        self.f.store.save(stored); self.f.host.running = False
        self.f.engine.recover(stored['operation'])
        self.f.engine.work(stored['operation'], 'recover')
        result = self.f.store.load()
        self.assertEqual(result['state'], 'CANCELLED_SAFE')
        self.assertTrue(result['ready'])
        self.assertNotIn('iap_upgrade', self.f.rpc_calls)

    def test_private_files_are_not_returned_in_error_json(self):
        self.f.host.put(W.I.CONFIG_ROOT + '/extended/openrfid_user.cfg', b'not-a-real-key')
        result = self.f.prepare()
        self.assertNotIn('not-a-real-key', json.dumps(self.f.engine.result(result['operation'])))

    def test_transaction_paths_reject_traversal(self):
        for token in ('../bad', 'x' * 32, '/tmp/anything', ''):
            self.assert_code('INVALID_OPERATION', self.f.store.directory, token)

    def test_launch_uses_detached_session_and_no_inherited_streams(self):
        self.f.engine.launch = W.Engine.launch.__get__(self.f.engine, W.Engine)
        with patch.object(W.subprocess, 'Popen', return_value=Mock(pid=1234)) as spawn, patch.object(W, 'process_stamp', return_value='42'):
            self.f.engine.prepare()
        args, kwargs = spawn.call_args
        self.assertTrue(kwargs['start_new_session'] and kwargs['close_fds'])
        self.assertEqual(kwargs['stdin'], W.subprocess.DEVNULL)
        self.assertNotIn('shell', kwargs)
        self.assertIn('_worker', args[0])

    def test_process_stamp_changes_across_boot_with_reused_pid(self):
        # Linux stat fields from process state through starttime; same PID/ticks.
        stat_text = '123 (test worker) ' + ' '.join(['S'] + ['0'] * 18 + ['456'])
        def reader(boot):
            return lambda path, *a, **kw: boot if path.name == 'boot_id' else stat_text
        with patch.object(Path, 'read_text', reader('boot-one')):
            first = W.process_stamp(123)
        with patch.object(Path, 'read_text', reader('boot-two')):
            second = W.process_stamp(123)
        self.assertEqual(first, 'boot-one:456')
        self.assertNotEqual(first, second)

    @unittest.skipUnless(W.sys.platform.startswith('linux'), 'Linux flock integration')
    def test_real_store_lock_excludes_host_installer_inode(self):
        import fcntl
        store = W.Store(self.root / 'linux' / 'ace-firmware')
        with store.lock():
            with (store.root.parent / 'installer.lock').open('a') as other:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with (store.root.parent / 'installer.lock').open('a') as other:
            fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)


if __name__ == '__main__':
    unittest.main()
