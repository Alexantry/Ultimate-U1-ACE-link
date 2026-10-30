"""Exercise production feeder methods against simulated ACE serial and sensors.

No printer, serial port or network is opened. The AST extraction avoids loading
unrelated MCU drivers; the control flow and serial protocol under test are real.
"""
import ast
import logging
from pathlib import Path
from types import SimpleNamespace
import unittest

from test_protocol import new, mod


def production_methods():
    tree = ast.parse((Path(__file__).resolve().parents[2] / 'payload/filament_feed.py').read_text(encoding='utf-8'))
    constants = [n for n in tree.body if isinstance(n, ast.Assign)]
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'FilamentFeed')
    wanted = {'_ace_head_present', '_ace_check_load', '_ace_wait_load_ready',
              '_ace_claim_load', '_ace_feed_to_sensor', '_ace_gate_changed', '_do_feed',
              'cmd_FEED_AUTO', '_is_keep_raw_error_info'}
    methods = [n for n in cls.body if isinstance(n, ast.FunctionDef)
               and (n.name in wanted or n.name.startswith('_ace_'))]
    ns = {'logging': logging}
    exec(compile(ast.Module(body=constants + methods, type_ignores=[]), '<production feeder>', 'exec'), ns)
    return ns, type('ProductionFeeder', (), {n.name: ns[n.name] for n in methods})


C, Feeder = production_methods()


class Sensor:
    def __init__(self):
        self.present = False
        self.enabled = True
        self.error = None

    def get_status(self, _time):
        if self.error is not None:
            raise self.error
        return {'enabled': self.enabled, 'filament_detected': self.present}


class Gcmd:
    def __init__(self, **values):
        self.values = {'CHANNEL': 0, **values}
        self.messages = []

    def get_int(self, key, default=None, **_kw):
        return self.values.get(key, default)

    get_float = get_int
    get = get_int

    def get_raw_command_parameters(self):
        return repr(self.values)

    def respond_info(self, message):
        self.messages.append(message)

    def error(self, message='', **_kw):
        return ValueError(message)


class Rig:
    """Firmware movement is represented by busy/ready plus a head switch.

    Only explicit feed requests move the modeled filament. Heartbeats use the
    production parser and freshness epochs, so a stop ACK alone cannot satisfy
    a completion wait.
    """
    def __init__(self):
        self.ace = new()
        self.reactor = self.ace.reactor
        self.sensor = Sensor()
        self.inlet = True
        self.hardware_status = 'ready'
        self.arrive_after = 1.0
        self.exhaust_after = None
        self.stop_ready_delay = .4
        self.stop_code = 0
        self.drop_stop_ack = False
        self.fail_hotend = False
        self.events = []
        self.ace.gate_status = [1] * 4
        self.ace._serial.reply = self.reply
        self._schedule_heartbeat()
        self.feeder = self.make_feeder()

    def at(self, delay, callback):
        self.reactor.pending.append((self.reactor.t + delay, callback))

    def _schedule_heartbeat(self):
        def tick():
            if self.ace._connected:
                self.ace._periodic_heartbeat_event(self.reactor.t)
            self._schedule_heartbeat()
        self.at(.25, tick)

    def reply(self, request):
        method = request['method']
        if method != 'get_status':
            self.events.append((method, self.reactor.t, request.get('params')))
        if method == 'get_status':
            return {'id': request['id'], 'code': 0, 'result': {
                'status': self.hardware_status,
                'slots': [{'status': 'ready' if self.inlet else 'empty', 'rfid': 0}
                          for _ in range(4)]}}
        if method == 'feed_filament':
            self.hardware_status = 'busy'
            if self.arrive_after is not None:
                self.at(self.arrive_after, lambda: setattr(self.sensor, 'present', True))
            if self.exhaust_after is not None:
                self.at(self.exhaust_after, lambda: setattr(self, 'hardware_status', 'ready'))
        if method == 'stop_feed_filament':
            if self.stop_ready_delay is not None:
                self.at(self.stop_ready_delay, lambda: setattr(self, 'hardware_status', 'ready'))
            if self.drop_stop_ack:
                return None
            if self.stop_code:
                return {'id': request['id'], 'code': self.stop_code, 'msg': 'stop rejected'}
        return {'id': request['id'], 'code': 0, 'msg': 'success'}

    def make_feeder(self, index=0):
        obj = Feeder()
        obj.ace = self.ace
        obj.reactor = self.reactor
        obj.filament_ch = [index, index + 1]
        obj.runout_sensor = [self.sensor, self.sensor]
        obj._port = [SimpleNamespace(get_filament_detected=lambda: self.inlet)] * 2
        obj.channel_error = [C['FEED_OK']] * 2
        obj.exception_code = [0, 0]
        obj.channel_state = [C['FEED_STA_PRELOAD_FINISH']] * 2
        obj.channel_error_state = [C['FEED_STA_NONE']] * 2
        obj.channel_active = None
        obj.manual_feeding = [False, False]
        obj.module_exist = [True, True]
        obj.config = {'auto_mode': [True, True], 'load_finish': [False, False]}
        obj.toolhead = SimpleNamespace(wait_moves=lambda: None,
            get_extruder=lambda: SimpleNamespace(nozzle_diameter=.4))
        obj._check_homing_xy = lambda: True
        obj._get_filament_temp = lambda _ch: 220
        obj._get_filament_soft = lambda _ch: False
        obj.get_status = lambda: {'channel_state': obj.channel_state[:]}
        def set_state(ch, state, save=False):
            obj.channel_state[ch] = state
            if save:
                obj.config['load_finish'][ch] = state == C['FEED_STA_LOAD_FINISH']
        obj._set_channel_state = set_state
        def gcode(script):
            text = script.strip()
            self.events.append(('gcode', self.reactor.t, text))
            if text.startswith('INNER_FILAMENT_UNLOAD'):
                if self.fail_hotend:
                    raise ValueError('mock hotend unload failure')
                self.sensor.present = False
        obj.gcode = SimpleNamespace(run_script_from_command=gcode)
        obj.printer = SimpleNamespace(lookup_object=lambda _name, default=None: default,
                                     extract_coded_message_field=lambda text: text)
        return obj

    def claim(self, feeder=None):
        feeder = feeder or self.feeder
        return feeder._ace_claim_load(0)

    def seek(self):
        self.claim()
        return self.feeder._ace_feed_to_sensor(0)

    def motions(self):
        return [e[0] for e in self.events if e[0] in
                ('feed_filament', 'stop_feed_filament', 'unwind_filament')]

    def setup_unload(self):
        self.sensor.present = True
        self.feeder.channel_state[0] = C['FEED_STA_LOAD_FINISH']
        self.ace.retract_length = 1250
        self.ace.retract_speed = 80
        original = self.ace._serial.reply
        def reply(request):
            response = original(request)
            if request['method'] == 'unwind_filament':
                self.hardware_status = 'busy'
                self.at(18, lambda: setattr(self, 'hardware_status', 'ready'))
            return response
        self.ace._serial.reply = reply


class SensorLoadTests(unittest.TestCase):
    def test_present_head_sends_no_feed_or_stop(self):
        r = Rig(); r.sensor.present = True
        r.seek()
        self.assertEqual(r.motions(), [])

    def test_sixty_second_nfc_wait_does_not_consume_motion_budget(self):
        r = Rig(); r.hardware_status = 'busy'; r.ace._info['status'] = 'busy'
        r.arrive_after = 70
        r.at(60, lambda: setattr(r, 'hardware_status', 'ready'))
        r.seek()
        feed, stop = [e for e in r.events if e[0] in ('feed_filament', 'stop_feed_filament')]
        self.assertGreaterEqual(feed[1], 160)
        self.assertGreaterEqual(stop[1] - feed[1], 70)
        self.assertEqual(r.feeder.channel_error[0], C['FEED_OK'])
        self.assertEqual(r.motions(), ['feed_filament', 'stop_feed_filament'])

    def test_ui_load_waits_for_nfc_before_heating_or_moving(self):
        r = Rig(); r.hardware_status = 'busy'; r.ace._info['status'] = 'busy'
        r.at(60, lambda: setattr(r, 'hardware_status', 'ready'))
        record = r.feeder.gcode.run_script_from_command
        def stop_at_first_preparation(script):
            record(script)
            if script.strip().startswith('M104 S150 T0'):
                raise ValueError('fixture ends at first heat command')
        r.feeder.gcode.run_script_from_command = stop_at_first_preparation
        with self.assertRaisesRegex(ValueError, 'fixture ends'):
            r.feeder._do_feed(0, C['FEED_ACT_LOAD'])
        first_heat = next(e for e in r.events if e[0] == 'gcode'
                          and e[2].startswith('M104 S150 T0'))
        self.assertGreaterEqual(first_heat[1], 160)
        self.assertEqual(r.motions(), [])
        self.assertIsNone(r.ace._u1_load_owner)
        self.assertIsNone(r.feeder.channel_active)

    def test_sensor_success_requires_stop_ack_and_post_stop_ready(self):
        r = Rig(); r.stop_ready_delay = 1.3
        r.seek()
        stop = next(e for e in r.events if e[0] == 'stop_feed_filament')
        self.assertGreaterEqual(r.reactor.t, stop[1] + 1.3)
        self.assertTrue(r.ace.is_ace_ready())
        self.assertEqual(r.motions(), ['feed_filament', 'stop_feed_filament'])

    def test_head_lost_while_stopping_is_not_a_successful_handoff(self):
        r = Rig(); r.arrive_after = .4; r.stop_ready_delay = 1
        r.at(.7, lambda: setattr(r.sensor, 'present', False))
        failure = None
        try:
            r.seek()
        except (ValueError, mod.AceException) as exc:
            failure = exc
        self.assertTrue(failure is not None or r.feeder.channel_error[0] != C['FEED_OK'],
                        'Head became empty before stop completion, but handoff reported success')
        self.assertEqual(r.motions(), ['feed_filament', 'stop_feed_filament'])

    def test_distance_exhaustion_is_failure_not_another_feed(self):
        r = Rig(); r.arrive_after = None; r.exhaust_after = 1
        with self.assertRaisesRegex(ValueError, 'maximum seek distance'):
            r.seek()
        self.assertEqual(r.feeder.channel_error[0], C['FEED_ERR_TIMEOUT'])
        self.assertEqual(r.motions(), ['feed_filament', 'stop_feed_filament'])

    def test_timeout_stops_once_without_another_feed(self):
        r = Rig(); r.arrive_after = None
        r.ace.SENSOR_LOAD_MAX_LENGTH = 20; r.ace.READY_TIMEOUT = .5
        with self.assertRaisesRegex(ValueError, 'seek timed out'):
            r.seek()
        self.assertEqual(r.feeder.channel_error[0], C['FEED_ERR_TIMEOUT'])
        self.assertEqual(r.motions(), ['feed_filament', 'stop_feed_filament'])
        self.assertLess(r.reactor.t, 103)

    def test_disabled_sensor_never_starts(self):
        r = Rig(); r.sensor.enabled = False
        with self.assertRaisesRegex(ValueError, 'disabled'): r.seek()
        self.assertEqual(r.motions(), [])

    def test_disabled_sensor_during_motion_stops_and_raises(self):
        r = Rig(); r.arrive_after = None
        r.at(.4, lambda: setattr(r.sensor, 'enabled', False))
        with self.assertRaisesRegex(ValueError, 'disabled'): r.seek()
        self.assertEqual(r.motions(), ['feed_filament', 'stop_feed_filament'])

    def test_empty_inlet_never_starts(self):
        r = Rig(); r.inlet = False
        with self.assertRaisesRegex(ValueError, 'empty'): r.seek()
        self.assertEqual(r.motions(), [])

    def test_inlet_loss_during_seek_stops_once(self):
        r = Rig(); r.arrive_after = None
        r.at(.4, lambda: setattr(r, 'inlet', False))
        with self.assertRaisesRegex(ValueError, 'inlet became empty'):
            r.seek()
        self.assertEqual(r.feeder.channel_error[0], C['FEED_ERR_NO_FILAMENT'])
        self.assertEqual(r.motions(), ['feed_filament', 'stop_feed_filament'])

    def test_rejected_stop_ack_does_not_report_success(self):
        r = Rig(); r.stop_code = 12
        with self.assertRaisesRegex(mod.AceException, 'stop rejected'): r.seek()
        self.assertEqual(r.motions(), ['feed_filament', 'stop_feed_filament'])

    def test_missing_stop_ack_does_not_report_success_even_if_ready(self):
        r = Rig(); r.drop_stop_ack = True
        with self.assertRaisesRegex(mod.AceException, 'acknowledgement timed out'): r.seek()
        self.assertEqual(r.motions(), ['feed_filament', 'stop_feed_filament'])

    def test_ack_without_ready_does_not_report_success(self):
        r = Rig(); r.stop_ready_delay = None; r.ace.SENSOR_LOAD_FINISH_TIMEOUT = .7
        with self.assertRaisesRegex(mod.AceException, 'ready wait timed out'): r.seek()

    def test_reconnect_aborts_old_seek_without_stop_on_new_session(self):
        r = Rig(); r.arrive_after = None
        def reconnect():
            r.ace._connected_at += 1
        r.at(.4, reconnect)
        with self.assertRaisesRegex(ValueError, 'interrupted'): r.seek()
        self.assertEqual(r.motions(), ['feed_filament'])

    def test_shutdown_interrupt_stops_same_connection_without_resend(self):
        r = Rig(); r.arrive_after = None
        r.at(.4, lambda: setattr(r.ace, '_shutting_down', True))
        with self.assertRaisesRegex(ValueError, 'interrupted'): r.seek()
        self.assertEqual(r.motions(), ['feed_filament', 'stop_feed_filament'])

    def test_new_owner_is_not_stopped_by_old_seek_cleanup(self):
        r = Rig(); r.arrive_after = None
        replacement = {'owner': object(), 'channel': 1, 'connection': 101}
        def new_session():
            r.ace._connected_at = 101
            r.ace._u1_load_owner = replacement
        r.at(.4, new_session)
        with self.assertRaisesRegex(ValueError, 'interrupted'): r.seek()
        self.assertEqual(r.motions(), ['feed_filament'])
        self.assertIs(r.ace._u1_load_owner, replacement)

    def test_second_module_cannot_claim_shared_ace(self):
        r = Rig(); first = r.claim(); second = r.make_feeder(index=2)
        with self.assertRaisesRegex(ValueError, 'already using'): second._ace_claim_load(0)
        self.assertIs(r.ace._u1_load_owner, first)
        self.assertEqual(r.motions(), [])

    def test_sensor_failure_remains_primary_when_stop_also_fails(self):
        r = Rig(); r.arrive_after = None; r.stop_code = 12
        r.at(.4, lambda: setattr(r.sensor, 'error', ValueError('sensor failure')))
        with self.assertRaisesRegex(ValueError, 'sensor failure'): r.seek()
        self.assertTrue(any('stop rejected' in s for s in r.ace.gcode.messages))

    def test_load_finish_with_missing_head_reaches_load_action(self):
        r = Rig(); r.feeder.channel_state[0] = C['FEED_STA_LOAD_FINISH']
        calls = []
        def load(ch, action, **_kw):
            calls.append((ch, action))
            r.feeder.channel_state[ch] = C['FEED_STA_LOAD_FINISH']
        r.feeder._do_feed = load
        r.feeder.cmd_FEED_AUTO(Gcmd(LOAD=1))
        self.assertEqual(calls, [(0, C['FEED_ACT_LOAD'])])

    def test_repeated_load_with_present_head_is_noop(self):
        r = Rig(); r.sensor.present = True
        r.feeder.channel_state[0] = C['FEED_STA_LOAD_FINISH']
        r.feeder._do_feed = lambda *a, **k: self.fail('duplicate load action')
        r.feeder.cmd_FEED_AUTO(Gcmd(LOAD=1))
        self.assertEqual(r.motions(), [])


class UnloadIntegrationTests(unittest.TestCase):
    def test_staged_unload_retracts_once_only_after_hotend_unload(self):
        r = Rig(); r.setup_unload()
        r.feeder.cmd_FEED_AUTO(Gcmd(UNLOAD=1, STAGE='prepare'))
        self.assertEqual(r.motions(), [])
        r.feeder.cmd_FEED_AUTO(Gcmd(UNLOAD=1, STAGE='doing'))
        events = [e for e in r.events if e[0] == 'unwind_filament' or
                  (e[0] == 'gcode' and e[2].startswith('INNER_FILAMENT_UNLOAD'))]
        self.assertEqual([e[0] for e in events], ['gcode', 'unwind_filament'])
        self.assertEqual(events[1][2], {'index': 0, 'length': 1250, 'speed': 80})
        r.feeder.cmd_FEED_AUTO(Gcmd(UNLOAD=1))
        self.assertEqual(r.motions(), ['unwind_filament'])

    def test_unstaged_unload_also_retracts_once_after_hotend(self):
        r = Rig(); r.setup_unload()
        r.feeder.cmd_FEED_AUTO(Gcmd(UNLOAD=1))
        events = [e for e in r.events if e[0] == 'unwind_filament' or
                  (e[0] == 'gcode' and e[2].startswith('INNER_FILAMENT_UNLOAD'))]
        self.assertEqual([e[0] for e in events], ['gcode', 'unwind_filament'])

    def test_hotend_failure_never_sends_retract_in_either_route(self):
        for stage in (None, 'doing'):
            with self.subTest(stage=stage):
                r = Rig(); r.setup_unload(); r.fail_hotend = True
                if stage == 'doing':
                    r.feeder.channel_state[0] = C['FEED_STA_UNLOAD_HEAT_FINISH']
                with self.assertRaises(ValueError):
                    r.feeder.cmd_FEED_AUTO(Gcmd(UNLOAD=1, STAGE=stage))
                self.assertEqual(r.motions(), [])

    def test_unload_hotend_failure_stops_existing_assist_and_cools(self):
        for stage in (None, 'doing'):
            with self.subTest(stage=stage):
                r = Rig(); r.setup_unload(); r.fail_hotend = True
                r.ace._feed_assist_index = 0
                if stage == 'doing':
                    r.feeder.channel_state[0] = C['FEED_STA_UNLOAD_HEAT_FINISH']
                with self.assertRaises(ValueError):
                    r.feeder.cmd_FEED_AUTO(Gcmd(UNLOAD=1, STAGE=stage))
                controls = [e[0] for e in r.events if e[0] != 'gcode']
                self.assertEqual(controls, ['stop_feed_assist'])
                self.assertEqual(r.ace._feed_assist_index, -1)
                self.assertIn('M104 S0', [e[2] for e in r.events if e[0] == 'gcode'])

    def test_unload_assist_stop_failure_is_reported_and_heater_is_turned_off(self):
        r = Rig(); r.setup_unload(); r.ace._feed_assist_index = 0
        r.feeder.channel_state[0] = C['FEED_STA_UNLOAD_HEAT_FINISH']
        reply = r.reply
        def reject_stop(request):
            response = reply(request)
            if request['method'] == 'stop_feed_assist':
                return {'id': request['id'], 'code': 12, 'msg': 'assist stop rejected'}
            return response
        r.ace._serial.reply = reject_stop
        failure = None
        try:
            r.feeder.cmd_FEED_AUTO(Gcmd(UNLOAD=1, STAGE='doing'))
        except (ValueError, mod.AceException) as exc:
            failure = exc
        self.assertTrue(failure is not None or r.feeder.channel_error[0] != C['FEED_OK'],
                        'Failed assist stop was swallowed as successful unload')
        self.assertIn('M104 S0', [e[2] for e in r.events if e[0] == 'gcode'])
        self.assertEqual(r.motions(), [])

    def test_empty_head_prepare_or_unstaged_does_not_retract(self):
        for stage in (None, 'prepare'):
            with self.subTest(stage=stage):
                r = Rig(); r.setup_unload(); r.sensor.present = False
                r.feeder.cmd_FEED_AUTO(Gcmd(UNLOAD=1, STAGE=stage))
                self.assertEqual(r.motions(), [])
                self.assertFalse(any(e[0] == 'gcode' and e[2].startswith('INNER_FILAMENT_UNLOAD')
                                     for e in r.events))

    def test_cancel_with_empty_head_still_turns_heater_off_without_retract(self):
        r = Rig(); r.setup_unload(); r.sensor.present = False
        r.feeder.channel_state[0] = C['FEED_STA_UNLOAD_HEAT_FINISH']
        r.feeder.cmd_FEED_AUTO(Gcmd(UNLOAD=1, STAGE='cancel'))
        self.assertIn('M104 S0', [e[2] for e in r.events if e[0] == 'gcode'])
        self.assertEqual(r.motions(), [])


class GateUiIntegrationTests(unittest.TestCase):
    def connect_ui(self, rig):
        rig.ace.printer.register_event_handler('ace:gate_changed', rig.feeder._ace_gate_changed)
        rig.feeder._do_feed = lambda *a, **k: self.fail('Gate UI event invoked native feeding')

    def test_insertion_removal_changes_ui_only_once_per_edge(self):
        r = Rig(); self.connect_ui(r); r.inlet = False
        r.reactor.pause(100.4)
        self.assertEqual(r.feeder.channel_state, [C['FEED_STA_WAIT_INSERT']] * 2)
        r.inlet = True
        r.reactor.pause(100.8)
        self.assertEqual(r.feeder.channel_state, [C['FEED_STA_PRELOAD_FINISH']] * 2)
        event_count = len(r.ace.printer.events)
        r.reactor.pause(102)
        self.assertEqual(len(r.ace.printer.events), event_count)
        r.inlet = False
        r.reactor.pause(102.4)
        self.assertEqual(r.feeder.channel_state, [C['FEED_STA_WAIT_INSERT']] * 2)
        self.assertTrue(all(event[0] == 'ace:gate_changed' for event in r.ace.printer.events))
        self.assertEqual(r.motions(), [])
        self.assertEqual(r.reactor.asyncs, [])

    def test_gate_event_preserves_active_or_already_loaded_channel(self):
        for active in (True, False):
            with self.subTest(active=active):
                r = Rig(); self.connect_ui(r)
                r.ace.gate_status = [mod.GATE_UNKNOWN] * 4
                r.sensor.present = True
                original = C['FEED_STA_LOAD_FEEDING'] if active else C['FEED_STA_LOAD_FINISH']
                r.feeder.channel_state[0] = original
                r.feeder.channel_active = 0 if active else None
                r.reactor.pause(100.4)
                self.assertEqual(r.feeder.channel_state[0], original)
                self.assertEqual(r.motions(), [])
                self.assertEqual(r.reactor.asyncs, [])

    def test_gate_events_preserve_prepared_unload_and_failed_states(self):
        for state in (C['FEED_STA_UNLOAD_HEAT_FINISH'], C['FEED_STA_LOAD_FAIL'],
                      C['FEED_STA_UNLOAD_FAIL']):
            with self.subTest(state=state):
                r = Rig(); self.connect_ui(r)
                r.ace.gate_status = [mod.GATE_UNKNOWN] * 4
                r.feeder.channel_state[0] = state
                r.reactor.pause(100.4)
                r.inlet = False
                r.reactor.pause(100.8)
                self.assertEqual(r.feeder.channel_state[0], state)
                self.assertEqual(r.motions(), [])

    def test_ui_callback_failure_does_not_block_two_slot_nfc_sync(self):
        from preload_replay_fixture import Replay
        from test_manual_policy import advance, enable_bambu_metadata
        replay = Replay(ready_at=161., inserted=(0, 1))
        enable_bambu_metadata(replay)
        def broken_ui(index, present):
            if index == 0:
                raise ValueError('mock UI display failure')
        replay.ace.printer.register_event_handler('ace:gate_changed', broken_ui)
        ace = replay.start()
        advance(replay, 170.)
        self.assertEqual(len(ace.gcode.scripts), 2)
        self.assertTrue(all('VENDOR="Bambu"' in script for script in ace.gcode.scripts))
        self.assertEqual(replay.feeds, [])
        self.assertTrue(all(ace._rfid_sync[i]['complete'] for i in (0, 1)))

    def test_empty_nfc_polling_never_feeds_or_emits_stock_port_event(self):
        r = Rig(); self.connect_ui(r); r.inlet = False
        r.hardware_status = 'busy'
        r.reactor.pause(165)
        self.assertEqual(r.feeder.channel_state, [C['FEED_STA_WAIT_INSERT']] * 2)
        self.assertEqual(r.motions(), [])
        self.assertTrue(all(req['method'] == 'get_status' for req in r.ace._serial.sent))
        self.assertFalse(any(event[0] == 'filament_feed:port' for event in r.ace.printer.events))
        self.assertEqual(r.reactor.asyncs, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
