"""Real feeder + ACE protocol integration; all movement is virtual."""
import unittest

from test_protocol import mod
from test_sensor_load import Rig, Gcmd, C
from test_staged_load import StagedRig


class TakeupRig(StagedRig):
    def __init__(self, length=300):
        super().__init__()
        self.ace.retract_length = 1250
        self.ace.retract_speed = 80
        self.ace.forward_takeup_length = length
        self.ace.forward_takeup_speed = 20
        self.sensor.present = True
        self.feeder.channel_state[0] = C['FEED_STA_LOAD_FINISH']
        self.arrive_phase = None
        self.slot_action = 'ready'
        self.tail_hook = None
        self.guard_samples = []
        self.tail_complete_after = 16.0
        record = self.feeder.gcode.run_script_from_command
        def gcode(script):
            record(script)
            if script.strip().startswith('T0 A0'):
                self.ace._enable_feed_assist(0)
        self.feeder.gcode.run_script_from_command = gcode

    def reply(self, request):
        response = super().reply(request)
        method = request['method']
        if method == 'get_status':
            status = self.slot_action if self.hardware_status == 'busy' else 'ready'
            response['result']['slots'] = [
                {'status': status if i == 0 and self.inlet else
                           ('ready' if self.inlet else 'empty'), 'rfid': 0}
                for i in range(4)]
        elif method == 'unwind_filament':
            self.slot_action = 'unwinding'
            self.guard_samples.append(('retract', self.ace._u1_unload_depth,
                                       self.ace._u1_load_owner))
        elif method == 'feed_filament':
            token = self.ace._u1_load_owner
            if token is not None and token.get('kind') == 'unload':
                self.slot_action = 'feeding'
                self.guard_samples.append(('tail', self.ace._u1_unload_depth, token))
                if self.tail_complete_after is not None:
                    self.at(self.tail_complete_after,
                            lambda: setattr(self, 'hardware_status', 'ready'))
                if self.tail_hook is not None:
                    self.tail_hook()
        return response

    def unload(self, staged=False):
        if staged:
            self.feeder.cmd_FEED_AUTO(Gcmd(UNLOAD=1, STAGE='prepare'))
        self.feeder.cmd_FEED_AUTO(Gcmd(UNLOAD=1, STAGE='doing' if staged else None))


class ForwardTakeupFeederTests(unittest.TestCase):
    def assert_clean(self, r):
        self.assertEqual(r.ace._u1_unload_depth, 0)
        self.assertIsNone(r.ace._u1_load_owner)
        self.assertIsNone(r.feeder.channel_active)

    def test_both_routes_retract_then_tail_once_before_finish(self):
        for staged in (False, True):
            with self.subTest(staged=staged):
                r = TakeupRig(); r.unload(staged)
                self.assertEqual(r.motions(), ['unwind_filament', 'feed_filament'])
                self.assertEqual(r.params(), [{'index': 0, 'length': 300, 'speed': 20}])
                self.assertTrue(all(depth > 0 and token['kind'] == 'unload'
                                    for _, depth, token in r.guard_samples))
                self.assertIs(r.guard_samples[0][2], r.guard_samples[1][2])
                self.assertFalse(any(e[0] == 'start_feed_assist' for e in r.events))
                self.assertEqual(r.feeder.channel_error[0], C['FEED_OK'])
                origin = r.ace.take_fast_origin(0)
                self.assertEqual(origin['advance_upper_mm'], 300)
                self.assertIsNone(r.ace.take_fast_origin(0))
                self.assert_clean(r)
                r.feeder.cmd_FEED_AUTO(Gcmd(UNLOAD=1))
                self.assertEqual(r.motions(), ['unwind_filament', 'feed_filament'])

    def test_300_advance_reduces_next_fast_to_850_total_limit_stays_2500(self):
        r = TakeupRig(); r.unload()
        r.arrive_phase = 'slow'; r.seek()
        self.assertEqual(r.params(), [
            {'index': 0, 'length': 300, 'speed': 20},
            {'index': 0, 'length': 850, 'speed': 200},
            {'index': 0, 'length': 1650, 'speed': 50}])
        self.assertEqual(sum(p['length'] for p in r.params()[1:]), 2500)

    def test_disabled_tail_preserves_single_retract_and_1150_fast(self):
        for staged in (False, True):
            with self.subTest(staged=staged):
                r = TakeupRig(length=0); r.unload(staged)
                self.assertEqual(r.motions(), ['unwind_filament'])
                self.assertIsNone(r.ace._takeup_ready)
                self.assert_clean(r)
                r.arrive_phase = 'slow'; r.seek()
                self.assertEqual(r.params(), [
                    {'index': 0, 'length': 1150, 'speed': 200},
                    {'index': 0, 'length': 1350, 'speed': 50}])

    def test_tail_failure_never_publishes_origin_and_cools_both_routes(self):
        for staged in (False, True):
            for failure in ('head', 'inlet', 'cancel'):
                with self.subTest(staged=staged, failure=failure):
                    r = TakeupRig()
                    def interrupt():
                        if failure == 'head': r.sensor.present = True
                        elif failure == 'inlet': r.inlet = False
                        else: r.ace._u1_load_owner['cancelled'] = True
                    r.tail_hook = lambda: r.at(.2, interrupt)
                    with self.assertRaises((ValueError, mod.AceException)):
                        r.unload(staged)
                    self.assertEqual(r.motions().count('feed_filament'), 1)
                    self.assertEqual(r.motions().count('stop_feed_filament'), 1)
                    self.assertIsNone(r.ace.take_fast_origin(0))
                    self.assertNotEqual(r.feeder.channel_error[0], C['FEED_OK'])
                    self.assertIn('M104 S0', [e[2] for e in r.events if e[0] == 'gcode'])
                    self.assert_clean(r)

    def test_missing_mark_confirmation_fails_instead_of_unload_finish(self):
        r = TakeupRig(); r.ace.mark_unloaded = lambda *a, **k: False
        with self.assertRaisesRegex(ValueError, 'completion could not be confirmed'):
            r.unload()
        self.assertIsNone(r.ace.take_fast_origin(0))
        self.assertNotEqual(r.feeder.channel_error[0], C['FEED_OK'])
        self.assert_clean(r)

    def test_other_module_owner_rejects_unload_without_cooling_or_stopping_owner(self):
        for stage in (None, 'cancel'):
            with self.subTest(stage=stage):
                r = TakeupRig(); other = r.make_feeder(index=2)
                owner = other._ace_claim_load(0)
                with self.assertRaisesRegex(ValueError, 'Another U1'):
                    r.feeder.cmd_FEED_AUTO(Gcmd(UNLOAD=1, STAGE=stage))
                self.assertEqual(r.events, [])
                self.assertIs(r.ace._u1_load_owner, owner)
                self.assertEqual(r.ace._u1_unload_depth, 0)

    def test_prepared_doing_inlet_failure_cools_and_releases_claim(self):
        r = TakeupRig(); r.feeder.cmd_FEED_AUTO(Gcmd(UNLOAD=1, STAGE='prepare'))
        r.inlet = False
        with self.assertRaisesRegex(ValueError, 'inlet became empty'):
            r.feeder.cmd_FEED_AUTO(Gcmd(UNLOAD=1, STAGE='doing'))
        self.assertEqual(r.motions(), [])
        self.assertIn('M104 S0', [e[2] for e in r.events if e[0] == 'gcode'])
        self.assertEqual(r.feeder.channel_state[0], C['FEED_STA_UNLOAD_FAIL'])
        self.assert_clean(r)


if __name__ == '__main__':
    unittest.main(verbosity=2)
