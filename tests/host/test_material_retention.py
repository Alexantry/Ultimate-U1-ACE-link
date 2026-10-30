"""Metadata lifetime integration: real detector, ACE heartbeat and PTC methods.

No device or network access. Production classes are parsed locally; only MCU,
filesystem persistence and the gcode dispatcher are replaced by small fakes.
"""
import ast
import copy
import logging
from pathlib import Path
import shlex
import string
import types
import unittest

from test_protocol import new, frame


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EXTRAS = HERE / 'fixtures'


def extract(path, class_name=None, methods=None, namespace=None):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    nodes = []
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            nodes.append(node)
        elif isinstance(node, ast.ClassDef) and node.name == class_name:
            selected = [n for n in node.body if isinstance(n, ast.FunctionDef)
                        and (methods is None or n.name in methods)]
            nodes.append(ast.ClassDef(name=node.name, bases=[], keywords=[],
                                      body=selected, decorator_list=[]))
    ns = dict(namespace or {})
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])),
                 str(path), 'exec'), ns)
    return ns


protocol = extract(EXTRAS / 'filament_protocol.py')
detector_ns = extract(ROOT / 'payload/filament_detect.py', 'FilamentDetector', namespace={
    'logging': logging, 'os': __import__('os'),
    'filament_protocol': types.SimpleNamespace(**protocol),
})
Detector = detector_ns['FilamentDetector']
ptc_ns = extract(EXTRAS / 'print_task_config.py', 'PrintTaskConfig', methods={
    '_rfid_filament_info_update_cb', 'cmd_SET_PRINT_FILAMENT_CONFIG',
    'backup_filament_info', 'update_filament_edit_flag',
}, namespace={'copy': copy, 'logging': logging, 'string': string})
PTC = ptc_ns['PrintTaskConfig']


class Command:
    def __init__(self, **values):
        self.values = values
    def get(self, key, default=None):
        return self.values.get(key, default)
    def get_int(self, key, default=None, **kwargs):
        value = self.get(key, default)
        return int(value) if value is not None else None
    def get_raw_command_parameters(self):
        return str(self.values)
    def error(self, message):
        return ValueError(message)


class MaterialRig:
    def __init__(self, has_ace=True, startup_stay=False):
        self.ace = new()
        self.printer = self.ace.printer
        self.reactor = self.ace.reactor
        self.gcode = self.ace.gcode
        self.heads = [dict(filament_detected=False, enabled=True) for _ in range(4)]
        self.native_gates = [True] * 4
        self.slots = [dict(index=i, status='ready', rfid=1, sku='', type='',
                           color=[0, 0, 0]) for i in range(4)]
        self.saved = []
        self.read_requests = []
        self.clear_requests = []
        self.reader = types.SimpleNamespace(enabled=False)
        self.webhooks = types.SimpleNamespace(
            register_endpoint=lambda *a: None, has_remote_method=lambda *a: False)
        self.feeder = types.SimpleNamespace(get_status=lambda et: {
            'extruder%d' % i: {'module_exist': True, 'disable_auto': False,
                              'filament_detected': self.native_gates[i]}
            for i in range(4)})
        old_lookup = self.printer.lookup_object
        def lookup(name, default=None):
            if name == 'ace': return self.ace if has_ace else default
            if name == 'fm175xx_reader': return self.reader
            if name == 'webhooks': return self.webhooks
            if name == 'print_task_config': return self.ptc
            if name.startswith('filament_motion_sensor e'):
                index = int(name.split(' e')[1].split('_')[0])
                return types.SimpleNamespace(get_status=lambda et: self.heads[index].copy())
            return old_lookup(name, default)
        self.printer.lookup_object = lookup
        self.printer.lookup_objects = lambda name: [('filament_feed left', self.feeder)] if name == 'filament_feed' else []
        self.printer.get_snapmaker_config_dir = lambda: 'in-memory'
        self.printer.load_snapmaker_config_file = lambda path, default: dict(startup_stay=startup_stay)
        def save(path, value, default):
            self.saved.append(copy.deepcopy(value))
            return True
        self.printer.update_snapmaker_config_file = save
        self.ptc = PTC()
        self.ptc.printer = self.printer
        self.ptc.gcode = self.gcode
        self.ptc.config_path = 'in-memory/print_task.json'
        self.ptc.filament_param_obj = None
        self.ptc.print_task_config = copy.deepcopy(ptc_ns['DEFAULT_PRINT_TASK_CONFIG'])
        self.ptc.print_task_config['filament_exist'] = [True] * 4
        self.ptc.filament_info_backup = {}
        self.ptc.backup_filament_info()
        self.gcode.run_script = self.gcode.scripts.append
        def script(text):
            self.gcode.scripts.append(text)
            parts = shlex.split(text)
            if parts and parts[0] == 'SET_PRINT_FILAMENT_CONFIG':
                self.ptc.cmd_SET_PRINT_FILAMENT_CONFIG(Command(**dict(p.split('=', 1) for p in parts[1:])))
        self.gcode.run_script_from_command = script
        self.detector = Detector(types.SimpleNamespace(get_printer=lambda: self.printer))
        self.detector.register_cb_2_update_filament_info(self.ptc._rfid_filament_info_update_cb)
        update = self.detector.request_update_filament_info
        clear = self.detector.request_clear_filament_info
        def request_update(index):
            self.read_requests.append(index)
            return update(index)
        def request_clear(index):
            self.clear_requests.append(index)
            return clear(index)
        self.detector.request_update_filament_info = request_update
        self.detector.request_clear_filament_info = request_clear
        self.detector._ready()
        self.observe()

    def drain(self):
        while self.reactor.asyncs:
            self.reactor.asyncs.pop(0)(self.reactor.t)

    def observe(self, dispatch=True):
        self.ace._periodic_heartbeat_event(self.reactor.t)
        request_id = self.ace._heartbeat_request[0]
        self.ace._process_data(frame(self.ace, {'id': request_id, 'code': 0,
            'result': {'status': 'ready', 'slots': copy.deepcopy(self.slots)}}))
        if dispatch: self.drain()

    def set_material(self, index, vendor='Bambu', main='PLA', sub='Matte', color='B15533'):
        self.ptc.cmd_SET_PRINT_FILAMENT_CONFIG(Command(CONFIG_EXTRUDER=index,
            VENDOR=vendor, FILAMENT_TYPE=main, FILAMENT_SUBTYPE=sub, FILAMENT_COLOR_RGBA=color))

    def material(self, index):
        return {key: copy.deepcopy(value[index]) for key, value in self.ptc.print_task_config.items()
                if key.startswith('filament_') and isinstance(value, list)}

    def head_event(self, index, present):
        self.heads[index]['filament_detected'] = present
        self.printer.send_event('filament_switch_sensor:runout', index, present)
        self.drain()

    def native_event(self, index, present):
        self.printer.send_event('filament_feed:port', index, present)
        self.drain()

    def set_gate(self, index, present, dispatch=True):
        self.slots[index]['status'] = 'ready' if present else 'empty'
        if not present:
            self.slots[index].update(rfid=1, sku='', type='', color=[0, 0, 0])
        self.observe(dispatch)

    def sync_nfc(self, index, vendor='Bambu Lab', main='PETG HF', color=(1, 2, 3)):
        self.slots[index].update(status='ready', rfid=2, sku='NEW-SPOOL', type=main, color=list(color))
        self.observe()
        request_id = self.ace._filament_query['id']
        self.ace._process_data(frame(self.ace, {'id': request_id, 'code': 0,
            'result': dict(self.slots[index], brand=vendor)}))
        self.drain()


class MaterialRetentionChecks(unittest.TestCase):
    def test_head_unload_preserves_bambu_and_manual_generic_on_all_slots(self):
        for vendor, main, sub in [('Bambu', 'PLA', 'Matte'), ('Generic', 'PETG', 'HF')]:
            for index in range(4):
                with self.subTest(vendor=vendor, index=index):
                    r = MaterialRig(); r.set_material(index, vendor, main, sub)
                    before = r.material(index); saved = len(r.saved)
                    r.head_event(index, True); r.head_event(index, False)
                    self.assertEqual(r.material(index), before)
                    self.assertEqual(len(r.saved), saved)
                    self.assertEqual(r.read_requests, [])
                    self.assertEqual(r.clear_requests, [])

    def test_repeated_head_and_native_port_events_preserve_metadata(self):
        r = MaterialRig(); r.set_material(0); before = r.material(0)
        for _ in range(3):
            for present in (True, False):
                r.head_event(0, present); r.native_event(0, present)
        self.assertEqual(r.material(0), before)
        self.assertEqual(r.read_requests, [])
        self.assertEqual(r.clear_requests, [])

    def test_startup_with_head_present_does_not_request_native_rfid(self):
        r = MaterialRig(); r.set_material(0); before = r.material(0)
        r.heads[0]['filament_detected'] = True
        r.detector._ready(); r.drain()
        self.assertEqual(r.material(0), before)
        self.assertEqual(r.read_requests, [])

    def test_actual_ace_empty_clears_only_removed_slot_once(self):
        r = MaterialRig()
        for i in range(4): r.set_material(i, 'Bambu' if i % 2 else 'Generic')
        others = [r.material(i) for i in (0, 2, 3)]
        before_saves = len(r.saved)
        r.set_gate(1, False)
        self.assertEqual(r.material(1)['filament_vendor'], 'NONE')
        self.assertEqual(r.material(1)['filament_type'], 'NONE')
        self.assertEqual(r.material(1)['filament_color_rgba'], 'FFFFFFFF')
        self.assertEqual([r.material(i) for i in (0, 2, 3)], others)
        self.assertEqual(len(r.saved), before_saves + 1)
        count = len(r.saved)
        r.printer.send_event('ace:gate_changed', 1, False); r.drain()
        self.assertEqual(len(r.saved), count)
        self.assertEqual(r.clear_requests, [])  # no request to the native reader

    def test_empty_gate_clears_even_when_head_still_detects_filament(self):
        r = MaterialRig(); r.set_material(0); r.heads[0]['filament_detected'] = True
        r.set_gate(0, False)
        self.assertEqual(r.material(0)['filament_vendor'], 'NONE')

    def test_absent_gate_event_with_current_present_is_ignored(self):
        r = MaterialRig(); r.set_material(0); before = r.material(0)
        r.printer.send_event('ace:gate_changed', 0, False); r.drain()
        self.assertEqual(r.material(0), before)
        self.assertEqual(r.clear_requests, [])

    def test_unknown_stale_and_disconnected_status_never_clear_or_read(self):
        for state in ('unknown', 'stale', 'disconnected'):
            with self.subTest(state=state):
                r = MaterialRig(); r.set_material(0); before = r.material(0)
                if state == 'unknown': r.ace.gate_status[0] = -1
                elif state == 'stale':
                    r.ace.gate_status[0] = 0
                    r.ace._last_status_time = r.reactor.t - 60
                else: r.ace._serial_disconnect()
                r.head_event(0, False); r.native_event(0, False)
                r.printer.send_event('ace:gate_changed', 0, False); r.drain()
                self.assertEqual(r.material(0), before)
                self.assertEqual(r.read_requests, [])
                self.assertEqual(r.clear_requests, [])

    def test_removed_and_reinserted_spool_can_receive_new_nfc_metadata(self):
        r = MaterialRig(); r.set_material(0)
        r.set_gate(0, False)
        self.assertEqual(r.material(0)['filament_vendor'], 'NONE')
        r.sync_nfc(0, 'Bambu Lab', 'PETG HF', (1, 2, 3))
        m = r.material(0)
        self.assertEqual((m['filament_vendor'], m['filament_type'], m['filament_sub_type'],
                          m['filament_color_rgba']), ('Bambu', 'PETG', 'HF', '010203FF'))
        self.assertTrue(r.ace.get_status()['rfid_sync'][0]['complete'])
        self.assertTrue(all(q['method'] in ('get_status', 'get_filament_info') for q in r.ace._serial.sent))

    def test_deferred_old_clear_does_not_erase_reinserted_material(self):
        r = MaterialRig(); r.set_material(0)
        r.set_gate(0, False, dispatch=False)
        r.set_gate(0, True, dispatch=False)
        r.set_material(0, 'Generic', 'ABS', '', '112233')
        before = r.material(0); r.drain()
        self.assertEqual(r.material(0), before)

    def test_confirmed_removal_is_delivered_after_other_slot_changes_status_epoch(self):
        r = MaterialRig(); r.set_material(0)
        r.set_gate(0, False, dispatch=False)
        r.ace.send_request({'method': 'stop_feed_filament', 'params': {'index': 1}},
                           lambda *args: None)
        self.assertFalse(r.ace.get_status()['status_fresh'])
        self.assertEqual(r.material(0)['filament_vendor'], 'Bambu')
        r.drain()
        self.assertEqual(r.material(0)['filament_vendor'], 'NONE')

    def test_new_external_rfid_webhook_survives_deferred_previous_clear(self):
        r = MaterialRig(); r.set_material(0)
        r.set_gate(0, False, dispatch=False)
        r.set_gate(0, True, dispatch=False)
        responses = []; errors = []
        info = {'VENDOR': 'Creality', 'MAIN_TYPE': 'PETG', 'SUB_TYPE': '',
                'RGB_1': 0x225588, 'SKU': 123}
        request = types.SimpleNamespace(
            get_int=lambda key, default=None: 0 if key == 'channel' else default,
            get_dict=lambda key, default=None: dict(info),
            send=responses.append, set_error=errors.append, error=ValueError)
        r.detector._handle_filament_detect_set(request)
        r.drain()
        self.assertEqual(errors, [])
        self.assertEqual(responses, [{'state': 'success'}])
        material = r.material(0)
        self.assertEqual((material['filament_vendor'], material['filament_type'],
                          material['filament_color_rgba']), ('Creality', 'PETG', '225588FF'))
        self.assertTrue(material['filament_official'])

    def test_empty_gate_with_cached_rfid_does_not_restore_removed_material(self):
        r = MaterialRig(); r.sync_nfc(0)
        count = sum(q['method'] == 'get_filament_info' for q in r.ace._serial.sent)
        r.slots[0]['status'] = 'empty'  # ACE may retain the old RFID payload
        r.observe(); r.observe()
        self.assertEqual(r.material(0)['filament_vendor'], 'NONE')
        self.assertIsNone(r.ace.get_status()['rfid_sync'][0])
        self.assertEqual(sum(q['method'] == 'get_filament_info' for q in r.ace._serial.sent), count)

    def test_same_tag_reinserted_after_removal_is_synchronized_again(self):
        r = MaterialRig(); r.sync_nfc(0)
        before = r.material(0)
        r.slots[0]['status'] = 'empty'; r.observe()
        self.assertEqual(r.material(0)['filament_vendor'], 'NONE')
        r.sync_nfc(0)
        self.assertEqual(r.material(0), before)
        self.assertTrue(r.ace.get_status()['rfid_sync'][0]['complete'])
        self.assertEqual(sum(q['method'] == 'get_filament_info' for q in r.ace._serial.sent), 2)

    def test_late_nfc_response_after_cached_rfid_removal_cannot_restore_metadata(self):
        r = MaterialRig(); r.set_material(0)
        r.slots[0].update(rfid=2, sku='NEW-SPOOL', type='PETG HF', color=[1, 2, 3])
        r.observe()
        request_id = r.ace._filament_query['id']
        old_detail = dict(r.slots[0], brand='Bambu Lab')
        r.slots[0]['status'] = 'empty'; r.observe(dispatch=False)
        r.ace._process_data(frame(r.ace, {'id': request_id, 'code': 0, 'result': old_detail}))
        r.drain()
        self.assertEqual(r.material(0)['filament_vendor'], 'NONE')
        self.assertFalse(any(s.startswith('SET_PRINT_FILAMENT_CONFIG') for s in r.gcode.scripts))

    def test_non_ace_head_runout_keeps_original_clear_and_read_behavior(self):
        r = MaterialRig(has_ace=False); r.set_material(0)
        r.head_event(0, False)
        self.assertEqual(r.material(0)['filament_vendor'], 'NONE')
        self.assertEqual(r.clear_requests, [0])
        self.assertEqual(r.read_requests, [0])

    def test_non_ace_native_port_and_startup_keep_original_behavior(self):
        r = MaterialRig(has_ace=False); r.set_material(0)
        r.native_event(0, False)
        self.assertEqual(r.material(0)['filament_vendor'], 'NONE')
        r.heads[1]['filament_detected'] = True
        r.detector._ready()
        self.assertEqual(r.read_requests, [1])

    def test_explicit_clear_remains_effective_with_loaded_ace(self):
        r = MaterialRig(); r.set_material(0)
        r.detector.cmd_FILAMENT_DT_CLEAR(Command(CHANNEL=0)); r.drain()
        self.assertEqual(r.material(0)['filament_vendor'], 'NONE')
        self.assertEqual(r.clear_requests, [0])


if __name__ == '__main__':
    unittest.main()
