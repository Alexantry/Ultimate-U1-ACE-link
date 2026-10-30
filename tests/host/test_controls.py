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
        self.assertEqual(status['port_version'], 'u1-2.0.0-snapace-34a06e87-port7-forward-takeup')
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
