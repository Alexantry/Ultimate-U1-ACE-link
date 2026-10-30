"""Volatile fast-load qualification and interruptible feed; no device access."""
import unittest
from test_protocol import new, Serial, mod, serial


class OriginRig:
    def __init__(self):
        self.ace = new()
        self.loaded = set()
        self.status = 'ready'
        self.ace._serial.reply = self.reply

    def reply(self, request):
        if request['method'] == 'get_status':
            return {'id': request['id'], 'code': 0, 'result': {
                'status': self.status,
                'slots': [{'status': 'loaded' if i in self.loaded else 'empty', 'rfid': 0}
                          for i in range(4)]}}
        return {'id': request['id'], 'code': 0, 'msg': 'success'}

    def heartbeat(self):
        self.ace._periodic_heartbeat_event(self.ace.reactor.t)
        self.ace.reactor.pause(self.ace.reactor.t + .02)

    def insert(self, *indices):
        self.heartbeat()
        self.loaded.update(indices)
        self.heartbeat()
        return self.ace


class FastOriginTests(unittest.TestCase):
    def test_constants_and_explicit_origin_status(self):
        r = OriginRig(); a = r.insert(0, 2)
        self.assertEqual((a.FAST_LOAD_LENGTH, a.FAST_LOAD_SPEED, a.SENSOR_LOAD_SPEED),
                         (1150, 200, 50))
        self.assertEqual((a.SENSOR_LOAD_MAX_LENGTH, a.SENSOR_LOAD_WAIT_TIMEOUT,
                          a.SENSOR_LOAD_FINISH_TIMEOUT), (2500, 180, 10))
        self.assertEqual(a.get_status()['fast_origins'], ['inserted', None, 'inserted', None])

    def test_unknown_to_loaded_never_qualifies(self):
        r = OriginRig(); r.loaded = {0, 1, 2, 3}; r.heartbeat()
        self.assertEqual(r.ace.get_status()['fast_origins'], [None] * 4)

    def test_true_insert_qualifies_once_after_nfc_ready(self):
        r = OriginRig(); r.heartbeat(); r.status = 'busy'; r.loaded = {1}; r.heartbeat()
        self.assertEqual(r.ace._fast_origins[1]['reason'], 'inserted')
        r.status = 'ready'; r.heartbeat()
        self.assertTrue(r.ace.take_fast_origin(1))
        self.assertFalse(r.ace.take_fast_origin(1))

    def test_busy_take_consumes_unusable_origin(self):
        r = OriginRig(); a = r.insert(0); r.status = 'busy'; r.heartbeat()
        self.assertFalse(a.take_fast_origin(0)); self.assertIsNone(a._fast_origins[0])

    def test_gate_change_invalidates_and_advances_generation(self):
        r = OriginRig(); a = r.insert(0); epoch = a._gate_epochs[0]
        r.loaded.clear(); r.heartbeat()
        self.assertEqual(a._gate_epochs[0], epoch + 1)
        self.assertIsNone(a._fast_origins[0])
        r.loaded = {0}; r.heartbeat()
        self.assertEqual(a._gate_epochs[0], epoch + 2)
        self.assertTrue(a.take_fast_origin(0))

    def test_all_busy_host_guards_refuse_insertion_credit(self):
        for guard in ('load', 'unload', 'motion', 'assist', 'control'):
            with self.subTest(guard=guard):
                r = OriginRig(); r.heartbeat(); a = r.ace
                if guard == 'load': a._u1_load_owner = {'connection': a._connected_at}
                if guard == 'unload': a._u1_unload_depth = 1
                if guard == 'motion': a._motion_pending.add(2)
                if guard == 'assist': a._feed_assist_index = 2
                if guard == 'control': a._control_inflight = True
                r.loaded = {0}; r.heartbeat()
                self.assertIsNone(a._fast_origins[0])

    def test_motion_invalidates_only_target_before_send(self):
        methods = ('feed_filament', 'unwind_filament', 'start_feed_assist',
                   'stop_feed_assist', 'update_feeding_speed', 'stop_feed_filament')
        for method in methods:
            with self.subTest(method=method):
                r = OriginRig(); a = r.insert(0, 1)
                a._control_inflight = True
                with self.assertRaises(mod.AceException):
                    a._command({'method': method, 'params': {'index': 0}}, ready=False)
                self.assertIsNone(a._fast_origins[0])
                self.assertIsNotNone(a._fast_origins[1])
                self.assertEqual([x['method'] for x in a._serial.sent], ['get_status'] * 2)

    def test_stop_only_without_active_assist_preserves_origin(self):
        r = OriginRig(); a = r.insert(0)
        a._stop_feed_assist_only()
        self.assertTrue(a.take_fast_origin(0))

    def test_owned_selection_defers_before_old_five_mm_unwind(self):
        r = OriginRig(); a = r.insert(1)
        a._feed_assist_index = 0
        a._u1_load_owner = {'index': 1, 'connection': a._connected_at, 'allow_assist': False}
        a._enable_feed_assist(1)
        self.assertEqual(a._feed_assist_index, 0)
        self.assertEqual([x['method'] for x in a._serial.sent], ['get_status'] * 2)
        self.assertIsNotNone(a._fast_origins[1])

    def test_final_assist_is_allowed_and_invalidates(self):
        r = OriginRig(); a = r.insert(1)
        a._u1_load_owner = {'index': 1, 'connection': a._connected_at, 'allow_assist': True}
        a._enable_feed_assist(1)
        self.assertEqual(a._serial.sent[-1]['method'], 'start_feed_assist')
        self.assertEqual(a._feed_assist_index, 1)
        self.assertIsNone(a._fast_origins[1])

    def test_disconnect_and_reconnect_erase_all_credit(self):
        r = OriginRig(); a = r.insert(0, 1); epoch = a._gate_epochs[:]
        a._serial_disconnect()
        self.assertEqual(a._fast_origins, [None] * 4)
        self.assertTrue(all(x > y for x, y in zip(a._gate_epochs, epoch)))
        transport = Serial(a); transport.reply = r.reply
        serial.Serial = lambda **kw: transport
        a._connect(a.reactor.t); r.heartbeat()
        self.assertEqual(a._fast_origins, [None] * 4)

    def test_mark_unloaded_requires_current_connection_epoch_and_fresh_ready(self):
        r = OriginRig(); a = r.insert(0); conn = a._connected_at; epoch = a._gate_epochs[0]
        self.assertTrue(a.mark_unloaded(0, conn, epoch))
        self.assertEqual(a.get_status()['fast_origins'][0], 'unloaded')
        self.assertTrue(a.take_fast_origin(0))
        self.assertFalse(a.mark_unloaded(0, conn - 1, epoch))
        self.assertFalse(a.mark_unloaded(0, conn, epoch - 1))
        a._motion_pending.add(0)
        self.assertFalse(a.mark_unloaded(0, conn, epoch))
        a._motion_pending.clear(); a._last_status_time -= 10
        self.assertFalse(a.mark_unloaded(0, conn, epoch))

    def test_retract_guard_balances_on_failure(self):
        r = OriginRig(); a = r.insert(0)
        a._u1_unload_depth = 1
        a._serial.reply = lambda req: {'id': req['id'], 'code': 12, 'msg': 'blocked'}
        with self.assertRaises(mod.AceException): a.retract_fil(0)
        self.assertEqual(a._u1_unload_depth, 1)
        self.assertIsNone(a._fast_origins[0])

    def test_poll_interrupts_during_ack_or_point_one_dwell(self):
        for trigger_delay in (.01, .075):
            with self.subTest(delay=trigger_delay):
                a = new(); arrived = RuntimeError('head present'); hit = [False]
                a._serial.reply = lambda req: {'id': req['id'], 'code': 0}
                a.reactor.pending.append((a.reactor.t + trigger_delay,
                                          lambda: hit.__setitem__(0, True)))
                def poll():
                    if hit[0]: raise arrived
                try:
                    a._feed(0, 1150, 200, 0, _poll=poll)
                    self.fail('poll did not interrupt')
                except RuntimeError as exc:
                    self.assertIs(exc, arrived)
                    self.assertTrue(exc._ace_feed_stop_confirmed)
                self.assertFalse(a._control_inflight)
                self.assertEqual([x['method'] for x in a._serial.sent],
                                 ['feed_filament', 'stop_feed_filament'])
                self.assertLess(a.reactor.t, 100.2)

    def test_missing_ack_never_replays_feed(self):
        a = new()
        a._serial.reply = lambda req: (None if req['method'] == 'feed_filament'
                                      else {'id': req['id'], 'code': 0})
        with self.assertRaises(mod.AceException): a._feed(0, 1150, 200, 0, _poll=lambda: None)
        self.assertEqual([x['method'] for x in a._serial.sent],
                         ['feed_filament', 'stop_feed_filament'])
        self.assertFalse(a._control_inflight)

    def test_failed_stop_does_not_mark_arrival_cleanup_confirmed(self):
        a = new(); arrived = RuntimeError('head present')
        a._serial.reply = lambda req: {'id': req['id'], 'code': 12 if req['method'] == 'stop_feed_filament' else 0}
        def poll(): raise arrived
        with self.assertRaises(RuntimeError) as ctx: a._feed(0, 1150, 200, 0, _poll=poll)
        self.assertIs(ctx.exception, arrived)
        self.assertFalse(getattr(arrived, '_ace_feed_stop_confirmed', False))

    def test_connection_change_during_ack_never_stops_new_session(self):
        a = new(); old = a._serial; changed = RuntimeError('connection changed')
        def poll():
            a._serial_disconnect()
            a._serial = Serial(a); a._connected = True; a._connected_at += 1
            raise changed
        with self.assertRaises(RuntimeError) as ctx: a._feed(0, 1150, 200, 0, _poll=poll)
        self.assertIs(ctx.exception, changed)
        self.assertEqual([x['method'] for x in old.sent], ['feed_filament'])
        self.assertEqual(a._serial.sent, [])
        self.assertFalse(a._control_inflight)

    def test_assist_start_reconnect_during_ack_or_dwell_never_stops_new_session(self):
        for phase in ('ack', 'dwell'):
            with self.subTest(phase=phase):
                a = new(); old = a._serial; replacement = Serial(a)
                replacement.reply = lambda req: {'id': req['id'], 'code': 0}
                def reconnect():
                    a._serial_disconnect()
                    a._serial = replacement; a._connected = True; a._connected_at += 1
                    a._last_status_time = a.reactor.t; a._last_status_epoch = a._status_epoch
                    a._info['status'] = 'ready'; a._feed_assist_index = 3
                old.reply = lambda req: (None if phase == 'ack'
                                         else {'id': req['id'], 'code': 0})
                a.reactor.pending.append((a.reactor.t + (.01 if phase == 'ack' else .2), reconnect))
                with self.assertRaises(mod.AceException): a._enable_feed_assist(1)
                self.assertEqual([x['method'] for x in old.sent], ['start_feed_assist'])
                self.assertEqual(replacement.sent, [])
                self.assertEqual(a._feed_assist_index, 3)
                self.assertFalse(a._control_inflight)

    def test_assist_reconnect_while_waiting_never_retracts_or_starts_new_session(self):
        a = new(); a._info['status'] = 'busy'; a._feed_assist_index = 0
        old = a._serial; replacement = Serial(a)
        replacement.reply = lambda req: {'id': req['id'], 'code': 0}
        def reconnect():
            a._serial_disconnect()
            a._serial = replacement; a._connected = True; a._connected_at += 1
            a._last_status_time = a.reactor.t; a._last_status_epoch = a._status_epoch
            a._info['status'] = 'ready'; a._feed_assist_index = 3
        a.reactor.pending.append((a.reactor.t + .05, reconnect))
        with self.assertRaises(mod.AceException): a._enable_feed_assist(1)
        self.assertEqual(old.sent, [])
        self.assertEqual(replacement.sent, [])
        self.assertEqual(a._feed_assist_index, 3)

    def test_assist_cleanup_reconnect_does_not_clear_new_tracking(self):
        a = new(); old = a._serial; replacement = Serial(a)
        def reconnect():
            a._serial_disconnect()
            a._serial = replacement; a._connected = True; a._connected_at += 1
            a._feed_assist_index = 3
        def reply(req):
            if req['method'] == 'start_feed_assist':
                return {'id': req['id'], 'code': 12, 'msg': 'start rejected'}
            a.reactor.pending.append((a.reactor.t + .01, reconnect))
            return None
        old.reply = reply
        with self.assertRaises(mod.AceException): a._enable_feed_assist(1)
        self.assertEqual([x['method'] for x in old.sent],
                         ['start_feed_assist', 'stop_feed_assist'])
        self.assertEqual(replacement.sent, [])
        self.assertEqual(a._feed_assist_index, 3)


if __name__ == '__main__':
    unittest.main(verbosity=2)
