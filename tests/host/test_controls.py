"""Mocked control/cleanup regression tests. No physical serial or network I/O."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from test_protocol import new, mod


def responding(ace, codes=None):
    codes = codes or {}
    def reply(request):
        def ready():
            ace._info['status'] = 'ready'
            ace._last_status_time = ace.reactor.t
            ace._last_status_epoch = ace._status_epoch
        ace.reactor.pending.append((ace.reactor.t + 0.02, ready))
        code = codes.get(request['method'], 0)
        return {'id': request['id'], 'code': code,
                'msg': 'success' if not code else request['method'] + ' rejected'}
    ace._serial.reply = reply


class ControlChecks(unittest.TestCase):
    def test_error_message_without_code_rejected(self):
        ace = new()
        ace._serial.reply = lambda r: {'id': r['id'], 'msg': 'failure'}
        with self.assertRaisesRegex(mod.AceException, 'failure'):
            ace._command({'method': 'drying_stop'}, ready=False)

    def test_unsent_nested_start_does_not_change_tracking(self):
        ace = new(); ace._control_inflight = True
        with self.assertRaisesRegex(mod.AceException, 'in progress'):
            ace._enable_feed_assist(2)
        self.assertEqual(ace._feed_assist_index, -1)
        self.assertEqual(ace._serial.sent, [])

    def test_precommand_heartbeat_cannot_mark_feed_finished(self):
        ace = new()
        ace._periodic_heartbeat_event(ace.reactor.t)
        heartbeat_id = ace._serial.sent[-1]['id']
        responding(ace)
        ace._command({'method': 'feed_filament', 'params': {'index': 1}}, ready=False)
        ace._info['status'] = 'busy'; ace._last_status_epoch = -1
        from test_protocol import frame
        ace._process_data(frame(ace, {'id': heartbeat_id, 'code': 0, 'result': {
            'status': 'ready', 'slots': [{'status': 'empty', 'rfid': 0}] * 4}}))
        self.assertFalse(ace.is_ace_ready())
        self.assertEqual(ace._info['status'], 'busy')

    def test_initial_disable_never_sends_negative_index(self):
        ace = new()
        ace._disable_feed_assist(2)
        self.assertEqual(ace._serial.sent, [])

    def test_disable_stops_and_retracts_tracked_channel(self):
        ace = new(); responding(ace); ace._feed_assist_index = 2
        ace._disable_feed_assist(0)
        self.assertEqual([(r['method'], r['params']['index']) for r in ace._serial.sent],
                         [('stop_feed_assist', 2), ('unwind_filament', 2)])
        self.assertEqual(ace._feed_assist_index, -1)

    def test_rejected_stop_does_not_retract(self):
        ace = new(); responding(ace, {'stop_feed_assist': 12}); ace._feed_assist_index = 2
        with self.assertRaisesRegex(mod.AceException, 'stop_feed_assist rejected'):
            ace._disable_feed_assist()
        self.assertEqual([r['method'] for r in ace._serial.sent], ['stop_feed_assist'])
        self.assertEqual(ace._feed_assist_index, 2)

    def test_rejected_start_cleans_up_without_retract(self):
        ace = new(); responding(ace, {'start_feed_assist': 12})
        with self.assertRaisesRegex(mod.AceException, 'start_feed_assist rejected'):
            ace._enable_feed_assist(1)
        self.assertEqual([r['method'] for r in ace._serial.sent], ['start_feed_assist', 'stop_feed_assist'])
        self.assertEqual(ace._feed_assist_index, -1)

    def test_cleanup_failure_does_not_mask_original_feed_rejection(self):
        ace = new(); responding(ace, {'feed_filament': 4, 'stop_feed_filament': 5})
        with self.assertRaisesRegex(mod.AceException, 'feed_filament rejected'):
            ace._feed(1, 100, 20, 0)
        self.assertTrue(any('cleanup also failed' in s for s in ace.gcode.messages))

    def test_cleanup_failure_does_not_mask_original_assist_rejection(self):
        ace = new(); responding(ace, {'start_feed_assist': 4, 'stop_feed_assist': 5})
        with self.assertRaisesRegex(mod.AceException, 'start_feed_assist rejected'):
            ace._enable_feed_assist(1)
        self.assertEqual(ace._feed_assist_index, 1)
        self.assertTrue(any('cleanup also failed' in s for s in ace.gcode.messages))

    def test_invalid_index_never_reaches_serial(self):
        ace = new()
        for index in (-1, 4, True, '1'):
            with self.assertRaises(mod.AceException): ace._retract(index, 5, 10)
            with self.assertRaises(mod.AceException): ace._feed(index, 5, 10)
        self.assertEqual(ace._serial.sent, [])

    def test_busy_ready_wait_is_bounded(self):
        ace = new(); ace._info['status'] = 'busy'
        with self.assertRaises(mod.AceException): ace.wait_ace_ready(timeout=0.3)
        self.assertLess(ace.reactor.t, 100.5)

    def test_serial_disconnect_during_ack_aborts(self):
        ace = new()
        ace.reactor.pending.append((100.1, lambda: ace._transport_failed('mock unplug')))
        with self.assertRaisesRegex(mod.AceException, 'disconnected'):
            ace._command({'method': 'start_feed_assist', 'params': {'index': 1}})
        self.assertLess(ace.reactor.t, 100.3)
        self.assertFalse(ace._control_inflight)

    def _reconnect(self, ace, at):
        from test_protocol import Serial
        def up():
            ace._serial = Serial(ace); ace._connected = True
            ace._connected_at = ace.reactor.t; ace._last_status_time = ace.reactor.t
            ace._last_status_epoch = ace._status_epoch; ace._info['status'] = 'ready'
            responding(ace)
        ace.reactor.pending.append((at, up))

    def test_toolchange_stop_retries_after_usb_drop(self):
        ace = new(); ace._feed_assist_index = 2
        ace.reactor.pending.append((100.02, lambda: ace._transport_failed('mock unplug')))
        self._reconnect(ace, 101.2)
        ace.toolchange_feed_assist(False, 0)
        self.assertEqual([(r['method'], r['params']['index']) for r in ace._serial.sent],
                         [('stop_feed_assist', 2), ('unwind_filament', 2)])
        self.assertEqual(ace._feed_assist_index, -1)
        self.assertLess(ace.reactor.t, 105)

    def test_toolchange_start_waits_when_already_disconnected(self):
        ace = new(); ace._transport_failed('mock unplug')
        self._reconnect(ace, 101.0)
        ace.toolchange_feed_assist(True, 1)
        self.assertEqual([r['method'] for r in ace._serial.sent], ['start_feed_assist'])
        self.assertEqual(ace._feed_assist_index, 1)

    def test_toolchange_gives_up_when_ace_stays_away(self):
        ace = new(); ace._feed_assist_index = 2; ace._transport_failed('mock unplug')
        with self.assertRaisesRegex(mod.AceException, 'did not reconnect'):
            ace.toolchange_feed_assist(False, 0)
        self.assertLess(ace.reactor.t, 100 + ace.RECONNECT_TIMEOUT + 1)

    def test_toolchange_rejection_on_live_link_is_not_retried(self):
        ace = new(); responding(ace, {'stop_feed_assist': 12}); ace._feed_assist_index = 2
        with self.assertRaisesRegex(mod.AceException, 'stop_feed_assist rejected'):
            ace.toolchange_feed_assist(False, 0)
        self.assertEqual([r['method'] for r in ace._serial.sent], ['stop_feed_assist'])

    def _drop_and_status(self, ace, state='printing', slot='ready'):
        from test_protocol import Serial, frame
        ace.printer.lookup_object = (lambda name, default=None, _o=ace.printer.lookup_object:
            SimpleNamespace(get_status=lambda t: {'state': state}) if name == 'print_stats' else _o(name, default))
        ace._transport_failed('mock ACE reset')
        ace._serial = Serial(ace); ace._connected = True; ace._connected_at = ace.reactor.t
        ace._periodic_heartbeat_event(ace.reactor.t)
        ace._process_data(frame(ace, {'id': ace._serial.sent[-1]['id'], 'code': 0, 'result': {
            'status': 'ready', 'slots': [{'status': slot, 'rfid': 0}] * 4}}))
        return [(r['method'], r.get('params', {}).get('index')) for r in ace._serial.sent]

    def test_assist_restored_after_reset_while_printing(self):
        from test_protocol import frame
        ace = new(); ace._feed_assist_index = 2
        self.assertEqual(self._drop_and_status(ace)[-1], ('start_feed_assist', 2))
        ace._process_data(frame(ace, {'id': ace._serial.sent[-1]['id'], 'code': 0, 'msg': 'success'}))
        self.assertIsNone(ace._assist_restore)
        self.assertEqual(ace._feed_assist_index, 2)
        self.assertTrue(any('restored after reconnect' in m for m in ace.gcode.messages))

    def test_assist_not_restored_when_not_printing_or_slot_empty(self):
        for kwargs in ({'state': 'paused'}, {'state': 'standby'}, {'slot': 'empty'}):
            ace = new(); ace._feed_assist_index = 2
            self.assertNotIn(('start_feed_assist', 2), self._drop_and_status(ace, **kwargs))
            self.assertIsNone(ace._assist_restore)

    def test_no_restore_without_tracked_assist(self):
        ace = new()
        self.assertEqual([m for m, i in self._drop_and_status(ace)], ['get_status'])

    def test_rejected_restore_retries_then_gives_up(self):
        from test_protocol import frame
        ace = new(); ace._feed_assist_index = 1
        self._drop_and_status(ace)
        for attempt in range(ace.ASSIST_RESTORE_ATTEMPTS):
            self.assertEqual(ace._serial.sent[-1]['method'], 'start_feed_assist')
            ace._process_data(frame(ace, {'id': ace._serial.sent[-1]['id'], 'code': 9, 'msg': 'busy'}))
            ace._heartbeat_request = None
            ace._periodic_heartbeat_event(ace.reactor.t)
            ace._process_data(frame(ace, {'id': ace._serial.sent[-1]['id'], 'code': 0, 'result': {
                'status': 'ready', 'slots': [{'status': 'ready', 'rfid': 0}] * 4}}))
        self.assertIsNone(ace._assist_restore)
        self.assertEqual([r['method'] for r in ace._serial.sent].count('start_feed_assist'),
                         ace.ASSIST_RESTORE_ATTEMPTS)

    def test_toolchange_owns_assist_across_reconnect(self):
        ace = new(); ace._feed_assist_index = 2
        ace.reactor.pending.append((100.02, lambda: ace._transport_failed('mock unplug')))
        self._reconnect(ace, 101.2)
        ace.toolchange_feed_assist(False, 0)
        self.assertIsNone(ace._assist_restore)
        self.assertFalse(ace._toolchange_assist)
        self.assertNotIn('start_feed_assist', [r['method'] for r in ace._serial.sent])

    def test_nested_control_rejected_before_serial_write(self):
        ace = new(); responding(ace); nested = []
        def overlap():
            try: ace._command({'method': 'feed_filament', 'params': {'index': 2}}, ready=False)
            except mod.AceException as exc: nested.append(str(exc))
        ace.reactor.pending.append((100.005, overlap))
        ace._command({'method': 'start_feed_assist', 'params': {'index': 1}})
        self.assertEqual(len(ace._serial.sent), 1)
        self.assertIn('in progress', nested[0])

    def test_read_only_status_identifies_port_and_freshness(self):
        ace = new()
        status = ace.get_status()
        self.assertTrue(status['connected']); self.assertTrue(status['status_fresh'])
        self.assertEqual(status['port_version'], 'u1-2.0.0-snapace-34a06e87-port8-runout-continue')
        self.assertEqual(status['load_policy'], 'u1_sensor')
        self.assertEqual(ace._serial.sent, [])

    def test_drying_stop_bypasses_busy_but_checks_ack(self):
        ace = new(); responding(ace); ace._info['status'] = 'busy'
        ace._command({'method': 'drying_stop'}, ready=False)
        self.assertEqual(ace._serial.sent[0]['method'], 'drying_stop')

    def test_final_feed_cleanup_preserves_primary_sensor_failure(self):
        # The sensor is checked before sending now: make it fail only after
        # motion starts, using the shared production-AST/serial fixture.
        from test_sensor_load import Rig
        rig = Rig(); rig.arrive_after = None; rig.stop_code = 12
        rig.at(.4, lambda: setattr(rig.sensor, 'error', ValueError('sensor failure')))
        with self.assertRaisesRegex(ValueError, 'sensor failure'):
            rig.seek()
        self.assertTrue(any('stop rejected' in text for text in rig.ace.gcode.messages))


if __name__ == '__main__': unittest.main(verbosity=2)
