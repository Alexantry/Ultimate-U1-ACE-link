"""Port5 insertion/NFC/retract policy in virtual time; no hardware access."""
import unittest
from test_protocol import new, Serial, mod
from preload_replay_fixture import Replay


def advance(replay, until):
    while replay.ace.reactor.t < until:
        replay.ace.reactor.pause(min(until, replay.ace.reactor.t + .1))
        replay.drain()


def enable_bambu_metadata(replay):
    original = replay.reply

    def material(index):
        return {'index': index, 'status': 'ready', 'rfid': 2,
                'sku': 'A01-W2', 'type': 'PLA Matte', 'color': [255, 255, 255]}

    def reply(request):
        response = original(request)
        if request['method'] == 'get_status':
            for index in replay.loaded(replay.ace.reactor.t):
                response['result']['slots'][index] = material(index)
        elif request['method'] == 'get_filament_info':
            response['result'] = dict(material(request['params']['index']), brand='Bambu Lab')
        return response

    replay.ace._serial.reply = reply
    return reply


class ManualPolicyChecks(unittest.TestCase):
    def test_two_insertions_do_not_feed_even_after_long_nfc_busy(self):
        r = Replay(ready_at=161., inserted=(0, 1))
        a = r.start()
        advance(r, 170.)
        self.assertTrue(a.is_ace_ready())
        self.assertEqual(a.gate_status, [1, 1, 0, 0])
        self.assertEqual(r.feeds, [])
        self.assertEqual(a.get_status()['preload_queue'], [])
        self.assertIsNone(a._preload_worker)
        self.assertTrue(all(request['method'] == 'get_status' for _, request in r.commands))

    def test_two_bambu_brands_sync_while_nfc_busy_without_transport(self):
        r = Replay(ready_at=161., inserted=(0, 1))
        enable_bambu_metadata(r)
        a = r.start()
        advance(r, 145.)
        self.assertEqual(a._info['status'], 'busy')
        self.assertEqual(r.feeds, [])
        self.assertEqual(len(a.gcode.scripts), 2)
        for script in a.gcode.scripts:
            self.assertIn('VENDOR="Bambu"', script)
            self.assertIn('FILAMENT_TYPE="PLA"', script)
            self.assertIn('FILAMENT_SUBTYPE="Matte"', script)
        self.assertTrue(all(a._rfid_sync[i]['complete'] for i in (0, 1)))
        advance(r, 170.)
        self.assertEqual(r.feeds, [])
        self.assertEqual(len(a.gcode.scripts), 2)

    def test_remove_and_reinsert_stays_in_ace(self):
        r = Replay(ready_at=102., gate_fn=lambda t: (0,) if 101 <= t < 110 or t >= 115 else ())
        a = r.start()
        advance(r, 130.)
        self.assertEqual(a.gate_status[0], mod.GATE_AVAILABLE)
        self.assertEqual(r.feeds, [])
        self.assertEqual(sum('filament inserted INDEX=0' in msg for msg in a.gcode.messages), 2)
        self.assertEqual(a.get_status()['preload_queue'], [])

    def test_reconnect_relearns_brand_without_loading_or_assist(self):
        r = Replay(ready_at=102., inserted=(0,))
        reply = enable_bambu_metadata(r)
        a = r.start()
        advance(r, 105.)
        self.assertEqual(len(a.gcode.scripts), 1)
        a._serial_disconnect()
        a._serial = Serial(a)
        a._serial.reply = reply
        a._connected = True
        a._connected_at = a.reactor.t
        advance(r, 110.)
        self.assertEqual(len(a.gcode.scripts), 2)
        self.assertIn('VENDOR="Bambu"', a.gcode.scripts[-1])
        self.assertEqual(r.feeds, [])
        self.assertEqual(a._feed_assist_index, -1)
        self.assertFalse(any(request['method'] == 'start_feed_assist' for _, request in r.commands))

    def test_legacy_preload_entry_is_nonmoving(self):
        a = new()
        a._pre_load(0)
        a._pre_load(1)
        self.assertEqual(a._serial.sent, [])
        self.assertEqual(a.reactor.asyncs, [])
        self.assertEqual(a.get_status()['preload_queue'], [])

    def test_explicit_feed_entry_is_still_available(self):
        r = Replay(ready_at=100., inserted=(0,))
        a = r.start()
        a._feed(0, 25, 20, 0)
        self.assertEqual(r.feeds[0][1], {'index': 0, 'length': 25, 'speed': 20})

    def test_retract_waits_past_host_estimate_for_actual_fresh_ready(self):
        r = Replay(ready_at=100., inserted=(0,))
        a = r.start()
        a.retract_length, a.retract_speed = 1250, 80
        original = r.reply
        completion = []

        def reply(request):
            if request['method'] == 'unwind_filament':
                r.feed_end = a.reactor.t + 23.
                completion.append(r.feed_end)
            return original(request)

        a._serial.reply = reply
        started = a.reactor.t
        a.retract_fil(0)
        self.assertGreater(a.reactor.t - started, 1250 / 80 + .1)
        self.assertGreaterEqual(a.reactor.t, completion[0])
        self.assertTrue(a.is_ace_ready())
        motions = [request for _, request in r.commands if request['method'] == 'unwind_filament']
        self.assertEqual(len(motions), 1)
        self.assertEqual(motions[0]['params'], {'index': 0, 'length': 1250, 'speed': 80})

    def test_retract_never_finishes_fails_bounded_without_retry(self):
        r = Replay(ready_at=100., inserted=(0,))
        a = r.start()
        a.retract_length, a.retract_speed = 1250, 80
        original = r.reply

        def reply(request):
            if request['method'] == 'unwind_filament':
                r.feed_end = float('inf')
            return original(request)

        a._serial.reply = reply
        started = a.reactor.t
        with self.assertRaisesRegex(mod.AceException, 'ready wait timed out'):
            a.retract_fil(0)
        self.assertLess(a.reactor.t - started, 47.)
        self.assertEqual(sum(request['method'] == 'unwind_filament' for _, request in r.commands), 1)

    def test_retract_missing_ack_is_not_repeated(self):
        r = Replay(ready_at=100., inserted=(0,))
        a = r.start()
        a.retract_length, a.retract_speed = 1250, 80
        original = r.reply

        def reply(request):
            response = original(request)
            if request['method'] == 'unwind_filament':
                r.feed_end = a.reactor.t + 25.
                return None
            return response

        a._serial.reply = reply
        with self.assertRaisesRegex(mod.AceException, 'acknowledgement timed out'):
            a.retract_fil(0)
        self.assertEqual(sum(request['method'] == 'unwind_filament' for _, request in r.commands), 1)

    def test_stop_only_inactive_does_not_send_any_motion(self):
        a = new()
        a._stop_feed_assist_only()
        self.assertEqual(a._serial.sent, [])
        self.assertEqual(a._feed_assist_index, -1)

    def test_stop_only_waits_for_completion_without_unwind(self):
        r = Replay(ready_at=100., inserted=(0, 1, 2))
        a = r.start()
        a._feed_assist_index = 2
        original = r.reply
        completed = []

        def reply(request):
            if request['method'] == 'stop_feed_assist':
                r.feed_end = a.reactor.t + 2.
                completed.append(r.feed_end)
            return original(request)

        a._serial.reply = reply
        a._stop_feed_assist_only()
        control = [req for _, req in r.commands if req['method'] != 'get_status']
        self.assertEqual([(req['method'], req['params']) for req in control],
                         [('stop_feed_assist', {'index': 2})])
        self.assertGreaterEqual(a.reactor.t, completed[0])
        self.assertTrue(a.is_ace_ready())
        self.assertEqual(a._feed_assist_index, -1)

    def test_stop_only_ack_rejection_and_loss_retain_tracking_no_unwind(self):
        for result, error in [('reject', 'rejected'), ('lost', 'acknowledgement timed out')]:
            r = Replay(ready_at=100., inserted=(0,))
            a = r.start()
            a._feed_assist_index = 0
            original = r.reply

            def reply(request):
                response = original(request)
                if request['method'] == 'stop_feed_assist':
                    if result == 'lost':
                        return None
                    return {'id': request['id'], 'code': 12, 'msg': 'rejected'}
                return response

            a._serial.reply = reply
            with self.assertRaisesRegex(mod.AceException, error):
                a._stop_feed_assist_only()
            self.assertEqual(a._feed_assist_index, 0)
            control = [req['method'] for _, req in r.commands if req['method'] != 'get_status']
            self.assertEqual(control, ['stop_feed_assist'])

    def test_stop_only_completion_timeout_retains_tracking(self):
        r = Replay(ready_at=100., inserted=(0,))
        a = r.start()
        a._feed_assist_index = 0
        original = r.reply

        def reply(request):
            if request['method'] == 'stop_feed_assist':
                r.feed_end = float('inf')
            return original(request)

        a._serial.reply = reply
        with self.assertRaisesRegex(mod.AceException, 'ready wait timed out'):
            a._stop_feed_assist_only()
        self.assertEqual(a._feed_assist_index, 0)
        self.assertFalse(any(req['method'] == 'unwind_filament' for _, req in r.commands))

    def test_retract_new_connection_during_dwell_or_ready_wait_is_unknown(self):
        for after in (8., 20.):
            r = Replay(ready_at=100., inserted=(0,))
            a = r.start()
            a.retract_length, a.retract_speed = 1250, 80
            original = r.reply

            def replace_connection():
                a._serial_disconnect()
                a._serial = Serial(a)
                a._serial.reply = reply
                a._connected = True
                a._connected_at = a.reactor.t
                r.feed_end = 0.

            def reply(request):
                if request['method'] == 'unwind_filament':
                    r.feed_end = a.reactor.t + 28.
                    a.reactor.pending.append((a.reactor.t + after, replace_connection))
                return original(request)

            a._serial.reply = reply
            with self.assertRaisesRegex(mod.AceException, 'connection changed during retract'):
                a.retract_fil(0)
            self.assertEqual(sum(req['method'] == 'unwind_filament' for _, req in r.commands), 1)

    def test_old_stop_cannot_clear_new_connection_assist_tracking(self):
        r = Replay(ready_at=100., inserted=(0, 3))
        a = r.start()
        a._feed_assist_index = 0
        original = r.reply

        def replace_connection():
            a._serial_disconnect()
            a._serial = Serial(a)
            a._serial.reply = reply
            a._connected = True
            a._connected_at = a.reactor.t
            a._feed_assist_index = 3
            r.feed_end = 0.

        def reply(request):
            if request['method'] == 'stop_feed_assist':
                r.feed_end = a.reactor.t + 28.
                a.reactor.pending.append((a.reactor.t + 1., replace_connection))
            return original(request)

        a._serial.reply = reply
        with self.assertRaisesRegex(mod.AceException, 'connection changed while stopping assist'):
            a._stop_feed_assist_only()
        self.assertEqual(a._feed_assist_index, 3)
        self.assertFalse(any(req['method'] == 'unwind_filament' for _, req in r.commands))

    def test_retract_reconnect_before_send_never_moves_new_connection(self):
        r = Replay(ready_at=130., inserted=(0,))
        a = r.start()
        a.retract_length, a.retract_speed = 1250, 80

        def replace_connection():
            a._serial_disconnect()
            a._serial = Serial(a)
            a._serial.reply = r.reply
            a._connected = True
            a._connected_at = a.reactor.t
            r.ready_at = 100.

        a.reactor.pending.append((a.reactor.t + 2., replace_connection))
        with self.assertRaisesRegex(mod.AceException, 'connection changed before retract'):
            a.retract_fil(0)
        self.assertFalse(any(req['method'] == 'unwind_filament' for _, req in r.commands))


if __name__ == '__main__':
    unittest.main(verbosity=2)
