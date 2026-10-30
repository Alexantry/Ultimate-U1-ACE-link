"""Two-stage U1 load integration, simulated serial/heartbeat/sensors only."""
import unittest

from test_protocol import frame, mod
from test_sensor_load import Rig, Gcmd, C


class StagedRig(Rig):
    def __init__(self):
        super().__init__()
        self.arrive_after = None
        self.fast_complete_after = 16.0
        self.arrive_phase = 'slow'
        self.head_after = 1.0
        self.feed_ack_delay = .01
        self.drop_feed_ack = False
        self.unwind_complete_after = 18.0
        self.phase_hook = None
        self.fast_ready_times = []

    def reply(self, request):
        response = super().reply(request)
        method = request['method']
        if method == 'feed_filament':
            phase = 'fast' if request['params']['speed'] == 200 else 'slow'
            if phase == 'fast' and self.fast_complete_after is not None:
                def finish_fast():
                    self.hardware_status = 'ready'
                    self.fast_ready_times.append(self.reactor.t)
                self.at(self.fast_complete_after, finish_fast)
            if phase == self.arrive_phase:
                self.at(self.head_after, lambda: setattr(self.sensor, 'present', True))
            if self.phase_hook is not None:
                self.phase_hook(phase)
            if self.drop_feed_ack:
                return None
            if self.feed_ack_delay != .01:
                self.at(self.feed_ack_delay,
                        lambda: self.ace._process_data(frame(self.ace, response)))
                return None
        elif method == 'unwind_filament':
            self.hardware_status = 'busy'
            self.at(self.unwind_complete_after, lambda: setattr(self, 'hardware_status', 'ready'))
        return response

    def known_insertion(self):
        """Earn eligibility using two real parsed heartbeat states, not a flag edit."""
        self.inlet = False
        self.reactor.pause(self.reactor.t + .4)
        self.inlet = True
        self.reactor.pause(self.reactor.t + .4)

    def feeds(self):
        return [event for event in self.events if event[0] == 'feed_filament']

    def params(self):
        return [event[2] for event in self.feeds()]


class StagedLoadTests(unittest.TestCase):
    def test_known_insertion_fast_then_fresh_ready_then_slow(self):
        r = StagedRig(); r.known_insertion(); r.seek()
        self.assertEqual(r.params(), [
            {'index': 0, 'length': 1150, 'speed': 200},
            {'index': 0, 'length': 1350, 'speed': 50}])
        self.assertGreaterEqual(r.feeds()[1][1], r.fast_ready_times[0])
        self.assertEqual(r.motions().count('stop_feed_filament'), 1)
        self.assertEqual(r.feeder.channel_error[0], C['FEED_OK'])

    def test_firmware_cap_does_not_cause_early_slow_stage(self):
        r = StagedRig(); r.known_insertion(); r.fast_complete_after = 22
        r.seek()
        fast, slow = r.feeds()
        self.assertGreater(slow[1] - fast[1], 1150 / 200)
        self.assertGreaterEqual(slow[1] - fast[1], 22)

    def test_early_post_ack_ready_requires_later_busy_then_ready_before_slow(self):
        r = StagedRig(); r.known_insertion()
        def delayed_busy(phase):
            if phase == 'fast':
                r.hardware_status = 'ready'
                r.at(2, lambda: setattr(r, 'hardware_status', 'busy'))
        r.phase_hook = delayed_busy
        r.seek()
        self.assertEqual(len(r.feeds()), 2)
        self.assertGreaterEqual(r.feeds()[1][1], r.fast_ready_times[0])
        self.assertGreaterEqual(r.feeds()[1][1] - r.feeds()[0][1], 16)
        self.assertEqual(r.feeder.channel_error[0], C['FEED_OK'])

    def test_fast_always_ready_without_head_times_out_without_slow(self):
        r = StagedRig(); r.known_insertion()
        r.fast_complete_after = None; r.arrive_phase = None
        def never_busy(phase):
            if phase == 'fast':
                r.hardware_status = 'ready'
        r.phase_hook = never_busy
        start = r.reactor.t
        with self.assertRaisesRegex(ValueError, 'seek timed out'):
            r.seek()
        self.assertEqual(r.params(), [{'index': 0, 'length': 1150, 'speed': 200}])
        self.assertEqual(r.motions(), ['feed_filament', 'stop_feed_filament'])
        self.assertGreaterEqual(r.reactor.t - start, 80)
        self.assertLess(r.reactor.t - start, 82)

    def test_head_before_first_busy_is_stopped_successfully(self):
        r = StagedRig(); r.known_insertion()
        r.arrive_phase = 'fast'; r.head_after = .2
        def still_queued(phase):
            if phase == 'fast':
                r.hardware_status = 'ready'
        r.phase_hook = still_queued
        r.seek()
        self.assertEqual(r.motions(), ['feed_filament', 'stop_feed_filament'])
        self.assertEqual(r.feeder.channel_error[0], C['FEED_OK'])
        feed, stop = [e for e in r.events if e[0] in ('feed_filament', 'stop_feed_filament')]
        self.assertLess(stop[1] - feed[1], .5)

    def test_both_stages_exhaust_without_head_fails_without_third_feed(self):
        r = StagedRig(); r.known_insertion(); r.arrive_phase = None
        def finish_slow(phase):
            if phase == 'slow':
                r.at(27, lambda: setattr(r, 'hardware_status', 'ready'))
        r.phase_hook = finish_slow
        with self.assertRaisesRegex(ValueError, 'maximum seek distance'):
            r.seek()
        self.assertEqual(r.params(), [
            {'index': 0, 'length': 1150, 'speed': 200},
            {'index': 0, 'length': 1350, 'speed': 50}])
        self.assertEqual(sum(p['length'] for p in r.params()), 2500)
        self.assertEqual(r.motions(), ['feed_filament', 'feed_filament', 'stop_feed_filament'])
        self.assertEqual(r.feeder.channel_error[0], C['FEED_ERR_TIMEOUT'])
        self.assertFalse(r.ace.take_fast_origin(0))

    def test_head_trigger_in_fast_or_at_boundary_never_starts_slow(self):
        for arrival in (1.0, 16.0):
            with self.subTest(arrival=arrival):
                r = StagedRig(); r.known_insertion()
                r.arrive_phase = 'fast'; r.head_after = arrival
                r.seek()
                self.assertEqual(r.params(), [{'index': 0, 'length': 1150, 'speed': 200}])
                self.assertEqual(r.motions(), ['feed_filament', 'stop_feed_filament'])
                self.assertEqual(r.feeder.channel_error[0], C['FEED_OK'])

    def test_head_trigger_during_fast_ack_wait_stops_promptly_once(self):
        r = StagedRig(); r.known_insertion()
        r.arrive_phase = 'fast'; r.head_after = .2; r.feed_ack_delay = 3
        r.seek()
        self.assertEqual(r.motions(), ['feed_filament', 'stop_feed_filament'])
        feed, stop = [e for e in r.events if e[0] in ('feed_filament', 'stop_feed_filament')]
        self.assertLess(stop[1] - feed[1], .5)
        self.assertEqual(r.feeder.channel_error[0], C['FEED_OK'])

    def test_head_trigger_even_with_missing_feed_ack_does_not_replay(self):
        r = StagedRig(); r.known_insertion()
        r.arrive_phase = 'fast'; r.head_after = .2; r.drop_feed_ack = True
        r.seek()
        self.assertEqual(r.motions(), ['feed_filament', 'stop_feed_filament'])
        self.assertEqual(r.feeder.channel_error[0], C['FEED_OK'])

    def test_missing_fast_ack_without_head_aborts_without_slow(self):
        r = StagedRig(); r.known_insertion()
        r.arrive_phase = None; r.drop_feed_ack = True
        with self.assertRaisesRegex(mod.AceException, 'acknowledgement timed out'):
            r.seek()
        self.assertEqual(len(r.feeds()), 1)
        self.assertEqual(r.feeds()[0][2]['speed'], 200)
        self.assertFalse(r.ace.take_fast_origin(0))

    def test_unknown_and_reconnected_sources_use_only_slow(self):
        for reconnect in (False, True):
            with self.subTest(reconnect=reconnect):
                r = StagedRig()
                if reconnect:
                    r.known_insertion()
                    r.ace._connected_at += 1
                r.seek()
                self.assertEqual(r.params(), [{'index': 0, 'length': 2500, 'speed': 50}])

    def test_failed_partial_fast_consumes_qualification_and_retry_is_slow(self):
        r = StagedRig(); r.known_insertion(); r.arrive_phase = None
        r.at(.5, lambda: setattr(r.sensor, 'enabled', False))
        with self.assertRaisesRegex(ValueError, 'disabled'): r.seek()
        self.assertFalse(r.ace.take_fast_origin(0))
        # Equivalent to the U1 operation's finally release, followed by a new click.
        r.ace._u1_load_owner = None
        r.sensor.enabled = True; r.arrive_phase = 'slow'
        r.events.clear()
        r.seek()
        self.assertEqual(r.params(), [{'index': 0, 'length': 2500, 'speed': 50}])

    def test_reconnect_during_fast_never_starts_slow_or_stops_new_session(self):
        r = StagedRig(); r.known_insertion(); r.arrive_phase = None
        r.at(.5, lambda: setattr(r.ace, '_connected_at', r.ace._connected_at + 1))
        with self.assertRaisesRegex(ValueError, 'interrupted'): r.seek()
        self.assertEqual(r.motions(), ['feed_filament'])

    def test_inlet_remove_reinsert_during_fast_never_rearms_fast(self):
        r = StagedRig(); r.known_insertion(); r.arrive_phase = None
        r.at(.5, lambda: setattr(r, 'inlet', False))
        r.at(.9, lambda: setattr(r, 'inlet', True))
        try:
            r.seek()
        except (ValueError, mod.AceException):
            pass
        r.reactor.pause(r.reactor.t + 1)
        self.assertEqual(len(r.feeds()), 1)
        self.assertNotEqual(r.feeder.channel_error[0], C['FEED_OK'])
        self.assertFalse(r.ace.take_fast_origin(0))

    def test_nfc_150_seconds_does_not_spend_80_second_motion_budget(self):
        r = StagedRig(); r.known_insertion()
        r.hardware_status = 'busy'; r.ace._info['status'] = 'busy'
        wait_start = r.reactor.t
        r.at(150, lambda: setattr(r, 'hardware_status', 'ready'))
        r.fast_complete_after = 20; r.head_after = 50
        r.seek()
        self.assertGreaterEqual(r.feeds()[0][1] - wait_start, 150)
        self.assertGreaterEqual(r.reactor.t - r.feeds()[0][1], 70)
        self.assertEqual(r.feeder.channel_error[0], C['FEED_OK'])
        self.assertEqual(len(r.feeds()), 2)

    def test_tool_selection_cannot_start_assist_until_explicit_handoff(self):
        r = StagedRig(); token = r.claim()
        r.ace._enable_feed_assist(0)
        self.assertFalse(any(e[0] == 'start_feed_assist' for e in r.events))
        token['allow_assist'] = True
        r.sensor.present = True
        r.ace._enable_feed_assist(0)
        self.assertEqual(sum(e[0] == 'start_feed_assist' for e in r.events), 1)
        self.assertEqual(r.ace._feed_assist_index, 0)


class StagedUnloadOriginTests(unittest.TestCase):
    def prepare_loaded(self):
        r = StagedRig()
        r.ace.retract_length = 1250; r.ace.retract_speed = 80
        r.sensor.present = True
        r.feeder.channel_state[0] = C['FEED_STA_LOAD_FINISH']
        return r

    def test_successful_staged_and_unstaged_unload_grant_once_after_ready(self):
        for staged in (False, True):
            with self.subTest(staged=staged):
                r = self.prepare_loaded()
                if staged:
                    r.feeder.cmd_FEED_AUTO(Gcmd(UNLOAD=1, STAGE='prepare'))
                    self.assertFalse(r.ace.take_fast_origin(0))
                r.feeder.cmd_FEED_AUTO(Gcmd(UNLOAD=1, STAGE='doing' if staged else None))
                unwind = [e for e in r.events if e[0] == 'unwind_filament']
                self.assertEqual(len(unwind), 1)
                self.assertEqual(unwind[0][2], {'index': 0, 'length': 1250, 'speed': 80})
                self.assertGreaterEqual(r.reactor.t, unwind[0][1] + 18)
                self.assertFalse(r.sensor.present)
                self.assertTrue(r.ace.take_fast_origin(0))
                self.assertFalse(r.ace.take_fast_origin(0))

    def test_cancel_and_hotend_failure_never_grant_unloaded_origin(self):
        for outcome in ('cancel', 'fail'):
            with self.subTest(outcome=outcome):
                r = self.prepare_loaded()
                r.feeder.cmd_FEED_AUTO(Gcmd(UNLOAD=1, STAGE='prepare'))
                if outcome == 'fail':
                    r.fail_hotend = True
                    with self.assertRaises(ValueError):
                        r.feeder.cmd_FEED_AUTO(Gcmd(UNLOAD=1, STAGE='doing'))
                else:
                    r.feeder.cmd_FEED_AUTO(Gcmd(UNLOAD=1, STAGE='cancel'))
                self.assertFalse(r.ace.take_fast_origin(0))
                self.assertEqual(r.motions(), [])

    def test_head_still_present_after_unload_never_grants_fast_origin(self):
        r = self.prepare_loaded()
        record = r.feeder.gcode.run_script_from_command
        def unchanged_head(script):
            record(script)
            if script.strip().startswith('INNER_FILAMENT_UNLOAD'):
                r.sensor.present = True
        r.feeder.gcode.run_script_from_command = unchanged_head
        failure = None
        try:
            r.feeder.cmd_FEED_AUTO(Gcmd(UNLOAD=1))
        except (ValueError, mod.AceException) as exc:
            failure = exc
        self.assertFalse(r.ace.take_fast_origin(0))
        self.assertTrue(failure is not None or r.feeder.channel_error[0] != C['FEED_OK'])
        self.assertIn('M104 S0', [e[2] for e in r.events if e[0] == 'gcode'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
