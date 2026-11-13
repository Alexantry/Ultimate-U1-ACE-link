"""Runout continuation: the U1 head sensor pauses, the ACE refill resumes.

No printer, serial port or network is opened. Production ACE, feeder and
detector methods run against the same simulated serial link as the other
host checks.
"""
from types import SimpleNamespace
import unittest

from test_protocol import new, mod
from test_sensor_load import Rig, C
from test_material_retention import MaterialRig


class Gcmd:
    def __init__(self, **values):
        self.values = values
        self.messages = []

    def get_int(self, key, default=None, **_kw):
        return int(self.values.get(key, default))

    def respond_info(self, message):
        self.messages.append(message)

    def error(self, message):
        return ValueError(message)


def ace_with_replies(replies=None):
    """ACE whose device answers each method with a fixed (code, msg)."""
    ace = new()
    ace.gate_status = [1] * 4
    replies = replies or {}

    def reply(request):
        method = request['method']
        if method == 'get_status':
            return {'id': request['id'], 'code': 0, 'result': {
                'status': 'ready', 'slots': [
                    {'status': 'ready' if gate else 'empty', 'rfid': 0}
                    for gate in ace.gate_status]}}
        code, msg = replies.get(method, (0, 'success'))
        return {'id': request['id'], 'code': code, 'msg': msg}
    ace._serial.reply = reply

    def tick():
        if ace._connected:
            ace._periodic_heartbeat_event(ace.reactor.t)
        ace.reactor.pending.append((ace.reactor.t + .25, tick))
    ace.reactor.pending.append((ace.reactor.t + .25, tick))
    return ace


def sent(ace):
    return [r['method'] for r in ace._serial.sent if r['method'] != 'get_status']


class EmptySlotAssistChecks(unittest.TestCase):
    def test_start_is_skipped_for_an_empty_slot(self):
        ace = ace_with_replies()
        ace.gate_status[0] = 0
        self.assertIs(ace._enable_feed_assist(0), False)
        self.assertEqual(sent(ace), [])
        self.assertEqual(ace._feed_assist_index, -1)

    def test_start_rejected_as_empty_does_not_raise(self):
        # The incident: the slot emptied between two status reports.
        ace = ace_with_replies({'start_feed_assist': (1, 'empty')})
        self.assertIs(ace._enable_feed_assist(0), False)
        self.assertEqual(sent(ace), ['start_feed_assist'])
        self.assertEqual(ace._feed_assist_index, -1)

    def test_other_start_rejections_still_raise(self):
        ace = ace_with_replies({'start_feed_assist': (1, 'busy')})
        with self.assertRaises(mod.AceException):
            ace._enable_feed_assist(0)

    def test_skipped_start_stops_an_assist_left_on_another_slot(self):
        ace = ace_with_replies()
        ace._feed_assist_index = 2
        ace.gate_status[0] = 0
        self.assertIs(ace._enable_feed_assist(0), False)
        self.assertEqual(sent(ace), ['stop_feed_assist'])
        self.assertEqual(ace._feed_assist_index, -1)

    def test_toolchange_stop_on_an_empty_slot_does_not_unwind(self):
        ace = ace_with_replies()
        ace._feed_assist_index = 1
        ace.gate_status[1] = 0
        ace._disable_feed_assist(3)
        self.assertEqual(sent(ace), ['stop_feed_assist'])
        self.assertEqual(ace._feed_assist_index, -1)

    def test_toolchange_stop_rejected_as_empty_is_tolerated(self):
        ace = ace_with_replies({'stop_feed_assist': (1, 'empty'),
                                'unwind_filament': (1, 'empty')})
        ace._feed_assist_index = 1
        ace._disable_feed_assist(3)
        self.assertEqual(sent(ace), ['stop_feed_assist', 'unwind_filament'])
        self.assertEqual(ace._feed_assist_index, -1)

    def test_toolchange_stop_with_filament_still_unwinds(self):
        ace = ace_with_replies()
        ace._feed_assist_index = 1
        ace._disable_feed_assist(3)
        self.assertEqual(sent(ace), ['stop_feed_assist', 'unwind_filament'])

    def test_other_stop_rejections_still_raise(self):
        ace = ace_with_replies({'stop_feed_assist': (1, 'busy')})
        ace._feed_assist_index = 1
        with self.assertRaises(mod.AceException):
            ace._disable_feed_assist(3)


class RunoutRig(Rig):
    """Feeder rig with the print state the stock pause macro leaves behind."""

    def __init__(self):
        super().__init__()
        self.print_state = 'paused'
        self.variables = {'is_runout': 1, 'last_extruder_index': 0, 'last_extruder_temp': 220}
        self.backup_type = 'PLA'
        self.current_type = 'PLA'
        self.scripts = []
        self.script_times = []
        self.info = []
        self.entangle = []
        feeder = self.feeder
        feeder.module_name = 'left'
        feeder.toolhead = SimpleNamespace(
            wait_moves=lambda: None,
            get_extruder=lambda: SimpleNamespace(extruder_index=0),
            get_status=lambda _t: {'homed_axes': 'xyz'})
        feeder._do_feed = lambda *a, **k: None

        def lookup(name, default=None):
            if name == 'print_stats':
                return SimpleNamespace(state=self.print_state)
            if name == 'gcode_macro INNER_RESUME':
                return SimpleNamespace(variables=self.variables)
            if name in ('extruder', 'extruder1', 'extruder2', 'extruder3'):
                return object()
            if name == 'filament_entangle_detect e0_filament':
                return SimpleNamespace(skip_entangle_check=self.entangle.append)
            if name == 'print_task_config':
                return SimpleNamespace(
                    filament_info_backup={'filament_type': [self.backup_type] * 4},
                    print_task_config={'filament_type': [self.current_type] * 4})
            return default
        feeder.printer = SimpleNamespace(lookup_object=lookup)

        def run_script(text):
            self.scripts.append(text)
            self.script_times.append(self.reactor.t)
            if text.startswith('FEED_RUNOUT_REFILL_RESUME'):
                feeder.cmd_FEED_RUNOUT_REFILL_RESUME(Gcmd(CHANNEL=text.split('CHANNEL=')[1]))
            if text == 'RESUME':
                self.print_state = 'printing'
                self.variables['is_runout'] = 0
        feeder.gcode = SimpleNamespace(run_script=run_script, run_script_from_command=run_script,
                                       respond_info=self.info.append)
        self.ace.printer.register_event_handler('ace:gate_changed', feeder._ace_gate_changed)

    def runout(self):
        self.feeder.cmd_FEED_RUNOUT_EVENT_HANDLE(Gcmd(CHANNEL=0))

    def run(self, seconds):
        """Advance simulated time and let queued background work run.

        The simulated reactor is not cooperative: a background worker that
        waits advances the clock itself. Schedule state changes with at().
        """
        end = self.reactor.t + seconds
        while self.reactor.t < end:
            self.reactor.pause(min(end, self.reactor.t + .25))
            while self.reactor.asyncs:
                self.reactor.asyncs.pop(0)(self.reactor.t)

    def heater_off(self):
        return [s for s in self.scripts if s.startswith('M104 S0')]

    def resumes(self):
        return self.scripts.count('RESUME')


class RunoutPauseChecks(unittest.TestCase):
    def empty_slot_rig(self):
        r = RunoutRig()
        r.inlet = False
        r.run(1)
        return r

    def test_head_runout_flushes_then_switches_all_nozzle_heaters_off(self):
        r = self.empty_slot_rig()
        r.runout()
        flush = r.scripts[0].split('\n')
        self.assertEqual(flush[:2], ['M109 S220 T0 A0', 'M83'])
        self.assertEqual(flush[2:-1], ['G1 E10.00 F150'] * 5)
        self.assertEqual(flush[-1], 'M400')
        self.assertEqual(r.entangle, [True, False])
        self.assertEqual(r.heater_off(), ['M104 S0 T%d A0' % i for i in range(4)])
        self.assertFalse(any('M140' in s for s in r.scripts))  # bed is untouched
        self.assertIn(0, r.feeder._ace_runout_wait)
        self.assertEqual(r.resumes(), 0)

    def test_flush_length_zero_skips_the_flush(self):
        r = self.empty_slot_rig()
        r.ace.runout_flush_length = 0
        r.runout()
        self.assertEqual(r.scripts, r.heater_off())

    def test_cold_nozzle_is_not_flushed(self):
        r = self.empty_slot_rig()
        r.variables['last_extruder_temp'] = 0
        r.runout()
        self.assertEqual(r.scripts, r.heater_off())

    def test_heaters_stay_on_when_disabled_in_settings(self):
        r = self.empty_slot_rig()
        r.ace.runout_heaters_off = False
        r.runout()
        self.assertEqual(r.heater_off(), [])

    def test_nothing_happens_outside_a_runout_pause(self):
        for state, runout in (('printing', 1), ('paused', 0), ('complete', 1)):
            r = self.empty_slot_rig()
            r.print_state = state
            r.variables['is_runout'] = runout
            r.runout()
            self.assertEqual(r.scripts, [])
            self.assertEqual(r.feeder._ace_runout_wait, {})

    def test_runout_on_another_head_is_ignored(self):
        r = self.empty_slot_rig()
        r.variables['last_extruder_index'] = 1
        r.runout()
        self.assertEqual(r.scripts, [])


class RefillResumeChecks(unittest.TestCase):
    def waiting_rig(self):
        r = RunoutRig()
        r.inlet = False
        r.run(1)
        r.runout()
        del r.scripts[:], r.script_times[:]
        return r

    def test_refill_of_the_same_slot_resumes_after_the_settle_time(self):
        r = self.waiting_rig()
        inserted = r.reactor.t
        r.inlet = True
        r.run(12)
        self.assertEqual(r.resumes(), 1)
        # The ACE bite / NFC read gets the full settle time first.
        self.assertGreaterEqual(r.script_times[r.scripts.index('RESUME')] - inserted, 8)
        self.assertEqual(r.feeder._ace_runout_wait, {})
        r.run(30)
        self.assertEqual(r.resumes(), 1)

    def test_no_resume_while_the_slot_stays_empty(self):
        r = self.waiting_rig()
        r.run(60)
        self.assertEqual(r.scripts, [])

    def test_filament_pulled_out_again_waits_for_the_next_insertion(self):
        r = self.waiting_rig()
        r.inlet = True
        r.at(3, lambda: setattr(r, 'inlet', False))
        r.run(20)
        self.assertEqual(r.resumes(), 0)
        self.assertIn(0, r.feeder._ace_runout_wait)
        r.inlet = True
        r.run(12)
        self.assertEqual(r.resumes(), 1)

    def test_refill_waits_while_the_ace_is_busy(self):
        r = self.waiting_rig()
        r.inlet = True
        r.hardware_status = 'busy'
        started = r.reactor.t
        r.at(30, lambda: setattr(r, 'hardware_status', 'ready'))
        r.run(40)
        self.assertEqual(r.resumes(), 1)
        self.assertGreaterEqual(r.script_times[r.scripts.index('RESUME')] - started, 30)

    def test_refill_that_never_becomes_ready_gives_up_without_resuming(self):
        r = self.waiting_rig()
        r.inlet = True
        r.hardware_status = 'busy'
        r.run(400)
        self.assertEqual(r.resumes(), 0)
        self.assertIn(0, r.feeder._ace_runout_wait)  # manual Resume still possible

    def test_manual_resume_before_refill_cancels_the_automatic_one(self):
        r = self.waiting_rig()
        r.print_state = 'printing'
        r.variables['is_runout'] = 0
        r.inlet = True
        r.run(30)
        self.assertEqual(r.scripts, [])
        self.assertEqual(r.feeder._ace_runout_wait, {})

    def test_cancelled_print_is_not_resumed(self):
        r = self.waiting_rig()
        r.inlet = True
        r.at(3, lambda: setattr(r, 'print_state', 'cancelled'))
        r.run(30)
        self.assertEqual(r.resumes(), 0)
        self.assertEqual(r.feeder._ace_runout_wait, {})

    def test_different_material_type_keeps_the_print_paused(self):
        r = self.waiting_rig()
        r.current_type = 'PETG'
        r.inlet = True
        r.run(15)
        self.assertEqual(r.resumes(), 0)
        self.assertEqual(r.feeder._ace_runout_wait, {})

    def test_auto_resume_can_be_disabled(self):
        r = self.waiting_rig()
        r.ace.runout_auto_resume = False
        r.inlet = True
        r.run(30)
        self.assertEqual(r.scripts, [])

    def test_slot_refilled_before_the_head_ran_out_keeps_heat_and_resumes(self):
        r = RunoutRig()  # new filament already waits behind the old tail
        r.runout()
        self.assertEqual(r.heater_off(), [])
        r.run(12)
        self.assertEqual(r.resumes(), 1)

    def test_refill_resume_command_alone_does_nothing(self):
        r = self.waiting_rig()
        r.ace.gate_status[0] = 1  # typed by hand before the settle check passed
        r.feeder.cmd_FEED_RUNOUT_REFILL_RESUME(Gcmd(CHANNEL=0))
        self.assertEqual(r.resumes(), 0)
        self.assertIn(0, r.feeder._ace_runout_wait)


class MaterialDuringRunoutChecks(unittest.TestCase):
    def rig(self, state):
        r = MaterialRig()
        r.set_material(0)
        lookup = r.printer.lookup_object
        r.print_state = state
        r.printer.lookup_object = lambda name, default=None: (
            SimpleNamespace(state=r.print_state) if name == 'print_stats' else lookup(name, default))
        return r

    def test_tail_feeding_the_head_keeps_material_during_a_print(self):
        r = self.rig('printing')
        before = r.material(0)
        r.heads[0]['filament_detected'] = True
        r.set_gate(0, False)
        self.assertEqual(r.material(0), before)

    def test_material_survives_the_head_runout_pause(self):
        r = self.rig('printing')
        before = r.material(0)
        r.heads[0]['filament_detected'] = True
        r.set_gate(0, False)
        r.heads[0]['filament_detected'] = False
        r.print_state = 'paused'
        r.detector._runout_evt_handle(0, False); r.drain()
        self.assertEqual(r.material(0), before)

    def test_tail_removed_after_the_print_clears_material(self):
        r = self.rig('printing')
        r.heads[0]['filament_detected'] = True
        r.set_gate(0, False)
        r.print_state = 'complete'
        r.heads[0]['filament_detected'] = False
        r.detector._runout_evt_handle(0, False); r.drain()
        self.assertEqual(r.material(0)['filament_vendor'], 'NONE')

    def test_spool_removed_during_a_print_with_empty_head_still_clears(self):
        r = self.rig('printing')
        r.set_gate(0, False)
        self.assertEqual(r.material(0)['filament_vendor'], 'NONE')

    def test_head_unload_with_filament_left_in_ace_keeps_material(self):
        r = self.rig('complete')
        before = r.material(0)
        r.detector._runout_evt_handle(0, False); r.drain()
        self.assertEqual(r.material(0), before)


if __name__ == '__main__':
    unittest.main()
