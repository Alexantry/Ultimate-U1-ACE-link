"""Finite forward tail and origin behavior against real ACE protocol code."""
import unittest
from test_protocol import new, mod


class Rig:
    def __init__(self, length=300):
        self.ace = a = new()
        a.retract_length, a.retract_speed = 1250, 80
        a.forward_takeup_length, a.forward_takeup_speed = length, 20
        self.hardware, self.phase = 'ready', 'ready'
        self.index = 0
        self.head = False
        self.drop_ack = False
        self.feed_behavior = 'normal'
        self.retract_behavior = 'normal'
        self.after_feed = None
        a._serial.reply = self.reply
        a._periodic_heartbeat_event(a.reactor.t)
        a.reactor.pause(a.reactor.t+.03)
        self.token = {'kind': 'unload', 'owner': self, 'channel': 0, 'index': 0,
                      'connection': a._connected_at, 'gate_epoch': a._gate_epochs[0], 'allow_assist': False}
        a._u1_load_owner = self.token
        self.heartbeat()

    def at(self, delay, callback):
        self.ace.reactor.pending.append((self.ace.reactor.t+delay, callback))

    def set_state(self, hardware, phase):
        self.hardware, self.phase = hardware, phase

    def heartbeat(self):
        a = self.ace
        a._periodic_heartbeat_event(a.reactor.t)
        self.at(.2, self.heartbeat)

    def reply(self, request):
        method = request['method']
        if method == 'get_status':
            return {'id': request['id'], 'code': 0, 'result': {
                'status': self.hardware,
                'slots': [{'index': i, 'status': self.phase if i == 0 else ('empty' if i == 2 else 'ready'),
                           'rfid': 0} for i in range(4)]}}
        if method == 'unwind_filament':
            self.set_state('busy', 'unwinding' if self.retract_behavior == 'normal' else 'shifting')
            self.at(1, lambda: self.set_state('ready', 'ready'))
        if method == 'feed_filament':
            self.set_state('busy', 'shifting')
            if self.feed_behavior == 'normal':
                self.at(.3, lambda: self.set_state('busy', 'feeding'))
                self.at(2, lambda: self.set_state('ready', 'ready'))
            elif self.feed_behavior == 'shifting_only':
                self.at(.3, lambda: self.set_state('ready', 'ready'))
            elif self.feed_behavior == 'error':
                self.at(.3, lambda: self.set_state('home_err', 'gear_err'))
            if self.after_feed is not None:
                self.after_feed()
            if self.drop_ack:
                return None
        if method == 'stop_feed_filament':
            self.set_state('ready', 'ready')
        return {'id': request['id'], 'code': 0, 'msg': 'success'}

    def guard(self):
        if self.head:
            raise RuntimeError('head unexpectedly detected')

    def retract(self):
        self.ace.retract_fil(0)

    def takeup(self, token=None):
        a = self.ace
        return a.forward_takeup(0, self.token['connection'], self.token['gate_epoch'],
                                _poll=self.guard, token=token or self.token)

    def motions(self):
        return [(r['method'], r.get('params')) for r in self.ace._serial.sent
                if r['method'] != 'get_status']


class ForwardTakeupTests(unittest.TestCase):
    def test_default_is_disabled_and_zero_advance_remains_truthy_once(self):
        a = new()
        self.assertEqual((a.forward_takeup_length, a.forward_takeup_speed), (0, 20))
        r = Rig(0); r.retract(); self.assertEqual(r.takeup(), 0)
        self.assertEqual([m for m, _ in r.motions()], ['unwind_filament'])
        a = r.ace
        self.assertTrue(a.mark_unloaded(0, a._connected_at, a._gate_epochs[0], 0))
        origin = a.take_fast_origin(0)
        self.assertTrue(origin); self.assertEqual(origin['advance_upper_mm'], 0)
        self.assertIsNone(a.take_fast_origin(0))

    def test_one_1250_retract_then_single_300_feed_and_explicit_new_origin(self):
        r = Rig(); r.retract(); self.assertEqual(r.takeup(), 300)
        self.assertEqual(r.motions(), [
            ('unwind_filament', {'index': 0, 'length': 1250, 'speed': 80}),
            ('feed_filament', {'index': 0, 'length': 300, 'speed': 20})])
        self.assertIsNone(r.ace._fast_origins[0])
        self.assertTrue(r.ace.mark_unloaded(0, r.token['connection'], r.token['gate_epoch'], 300))
        self.assertEqual(r.ace.take_fast_origin(0)['advance_upper_mm'], 300)
        with self.assertRaisesRegex(mod.AceException, 'no replay'): r.takeup()
        self.assertEqual(len(r.motions()), 2)

    def test_no_receipt_or_different_owner_never_sends_tail(self):
        r = Rig()
        with self.assertRaises(mod.AceException): r.takeup()
        r.retract(); old = r.token; r.token = dict(old); r.ace._u1_load_owner = r.token
        with self.assertRaises(mod.AceException): r.takeup()
        self.assertEqual([m for m, _ in r.motions()], ['unwind_filament'])

    def test_enabled_tail_requires_real_unwinding_before_ready(self):
        r = Rig(); r.retract_behavior = 'shifting_only'
        with self.assertRaisesRegex(mod.AceException, 'did not prove unwinding'):
            r.retract()
        self.assertIsNone(r.ace._takeup_ready)
        with self.assertRaises(mod.AceException): r.takeup()
        self.assertEqual([m for m, _ in r.motions()], ['unwind_filament'])

    def test_enabled_retract_rechecks_cancellation_owner_and_gate_after_ready_wait(self):
        for change in ('cancel', 'owner', 'gate'):
            with self.subTest(change=change):
                r = Rig()
                r.ace.reactor.pause(r.ace.reactor.t + .05)  # Drain the initial ready response first.
                r.set_state('busy', 'shifting'); r.ace._info['status'] = 'busy'
                def invalidate():
                    if change == 'cancel': r.token['cancelled'] = True
                    elif change == 'owner': r.ace._u1_load_owner = dict(r.token)
                    else: r.ace._gate_epochs[0] += 2
                r.at(.15, invalidate)
                r.at(.3, lambda: r.set_state('ready', 'ready'))
                with self.assertRaisesRegex(mod.AceException, 'retract interrupted'):
                    r.retract()
                self.assertEqual(r.motions(), [])
                self.assertIsNone(r.ace._takeup_ready)

    def test_disabled_tail_keeps_previous_retract_behavior(self):
        r = Rig(0); r.retract_behavior = 'shifting_only'; r.retract()
        self.assertEqual(r.takeup(), 0)
        self.assertEqual([m for m, _ in r.motions()], ['unwind_filament'])

    def test_manual_motion_invalidates_retract_receipt(self):
        r = Rig(); r.retract()
        r.ace._invalidate_motion_origin({'method': 'feed_filament', 'params': {'index': 1}})
        with self.assertRaises(mod.AceException): r.takeup()
        self.assertEqual([m for m, _ in r.motions()], ['unwind_filament'])

    def test_head_already_present_or_cancelled_before_send_has_no_tail(self):
        for reason in ('head', 'cancel'):
            with self.subTest(reason=reason):
                r = Rig(); r.retract()
                if reason == 'head': r.head = True
                else: r.token['cancelled'] = True
                with self.assertRaises(Exception): r.takeup()
                self.assertEqual([m for m, _ in r.motions()], ['unwind_filament'])

    def test_head_or_cancel_during_motion_stops_once_without_replay(self):
        for reason in ('head', 'cancel'):
            with self.subTest(reason=reason):
                r = Rig(); r.retract()
                def changed():
                    if reason == 'head': r.head = True
                    else: r.token['cancelled'] = True
                r.after_feed = lambda: r.at(.5, changed)
                with self.assertRaises(Exception): r.takeup()
                self.assertEqual([m for m, _ in r.motions()],
                                 ['unwind_filament', 'feed_filament', 'stop_feed_filament'])
                self.assertIsNone(r.ace._fast_origins[0])
                with self.assertRaises(mod.AceException): r.takeup()
                self.assertEqual(len(r.motions()), 3)

    def test_missing_ack_is_not_retried_and_single_cleanup_stop(self):
        r = Rig(); r.retract(); r.drop_ack = True
        with self.assertRaises(mod.AceException): r.takeup()
        self.assertEqual([m for m, _ in r.motions()],
                         ['unwind_filament', 'feed_filament', 'stop_feed_filament'])
        self.assertIsNone(r.ace._fast_origins[0])

    def test_shifting_only_or_real_error_never_reports_completed_tail(self):
        for behavior in ('shifting_only', 'error'):
            with self.subTest(behavior=behavior):
                r = Rig(); r.retract(); r.feed_behavior = behavior
                with self.assertRaises(mod.AceException): r.takeup()
                self.assertIsNone(r.ace._fast_origins[0])
                self.assertEqual([m for m, _ in r.motions()].count('feed_filament'), 1)

    def test_reconnection_or_owner_replacement_never_stops_or_erases_new_operation(self):
        for change in ('connection', 'owner', 'gate'):
            with self.subTest(change=change):
                r = Rig(); r.retract(); new_origin = {'reason': 'new-session'}
                def changed():
                    a = r.ace
                    if change == 'connection': a._connected_at += 1
                    elif change == 'owner': a._u1_load_owner = dict(r.token)
                    else: a._gate_epochs[0] += 2
                    a._fast_origins[0] = new_origin
                r.after_feed = lambda: r.at(.005, changed)
                with self.assertRaises(Exception): r.takeup()
                self.assertEqual([m for m, _ in r.motions()], ['unwind_filament', 'feed_filament'])
                self.assertIs(r.ace._fast_origins[0], new_origin)

    def test_invalid_lengths_speed_and_origin_are_rejected(self):
        for key, bad in [('forward_takeup_length', 501), ('forward_takeup_length', -1),
                         ('forward_takeup_length', True), ('forward_takeup_speed', 51)]:
            with self.subTest(key=key, bad=bad):
                r = Rig(); r.retract(); setattr(r.ace, key, bad)
                with self.assertRaises(mod.AceException): r.takeup()
                self.assertEqual([m for m, _ in r.motions()], ['unwind_filament'])
        r = Rig(); r.retract()
        with self.assertRaises(mod.AceException): r.ace.mark_unloaded(0, r.token['connection'], r.token['gate_epoch'], 501)

    def test_unload_owner_defers_assist_for_all_channels(self):
        r = Rig()
        for index in range(4): r.ace._enable_feed_assist(index)
        self.assertEqual(r.motions(), [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
