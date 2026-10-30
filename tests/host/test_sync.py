"""Automatic metadata synchronization through the real fake-serial dispatcher."""
import copy
import shlex
import unittest
from test_protocol import new, frame, mod


LIVE = {'index': 1, 'sku': 'A01-R2', 'type': 'PLA Matte',
        'color': [177, 85, 51], 'rfid': 2, 'status': 'ready'}


def slots(spool=None):
    result = [{'index': i, 'status': 'ready', 'rfid': 1, 'sku': '',
               'type': '', 'color': [0, 0, 0]} for i in range(4)]
    if spool is not None: result[spool['index']] = copy.deepcopy(spool)
    return result


def drain(ace):
    while ace.reactor.asyncs:
        ace.reactor.asyncs.pop(0)(ace.reactor.t)


def observe(ace, spools, dispatch=True):
    ace._periodic_heartbeat_event(ace.reactor.t)
    rid = ace._heartbeat_request[0]
    ace._process_data(frame(ace, {'id': rid, 'code': 0, 'result': {
        'status': 'ready', 'slots': copy.deepcopy(spools)}}))
    if dispatch: drain(ace)


def detail(ace, data=None, dispatch=True):
    if data is None: data = dict(copy.deepcopy(LIVE), brand='Bambu Lab')
    rid = ace._filament_query['id']
    ace._process_data(frame(ace, {'id': rid, 'code': 0, 'result': data}))
    if dispatch: drain(ace)


def params(script):
    return dict(token.split('=', 1) for token in shlex.split(script)[1:])


class SyncChecks(unittest.TestCase):
    def test_live_material_fetches_brand_and_updates_only_recognized_slot(self):
        ace = new(); observe(ace, slots(LIVE))
        self.assertEqual(ace._serial.sent[-1]['method'], 'get_filament_info')
        self.assertEqual(ace._serial.sent[-1]['params'], {'index': 1})
        self.assertEqual(ace.gcode.scripts, [])
        detail(ace, dispatch=False)
        self.assertEqual(ace.gcode.scripts, [])  # never execute SET inside the serial callback
        drain(ace)
        self.assertEqual(len(ace.gcode.scripts), 1)
        self.assertEqual(params(ace.gcode.scripts[0]), {'CONFIG_EXTRUDER':'1',
            'FILAMENT_TYPE':'PLA', 'FILAMENT_SUBTYPE':'Matte', 'VENDOR':'Bambu',
            'FILAMENT_COLOR_RGBA':'B15533'})
        self.assertTrue(ace.get_status()['rfid_sync'][1]['complete'])
        self.assertEqual(ace._info['slots'][1]['type'], 'PLA Matte')
        self.assertEqual([s for s in ace._rfid_sync if s is not None], [ace._rfid_sync[1]])
        self.assertTrue(all(r['method'] in ('get_status','get_filament_info') for r in ace._serial.sent))

    def test_all_supported_and_unknown_real_brands_are_preserved(self):
        for raw, expected in [('Bambu Lab','Bambu'),('BambuLab','Bambu'),('bambu','Bambu'),
            ('CREALITY','Creality'),('elegoo','Elegoo'),('qidi','QIDI'),('AC','AC'),
            ('Snapmaker','Snapmaker'),('Anycubic','Anycubic'),('Polymaker','Polymaker'),
            ('Prusa','Prusa'),('Jayo','Jayo'),('New Maker','New Maker')]:
            ace = new(); observe(ace, slots(LIVE)); detail(ace, dict(LIVE, brand=raw))
            self.assertEqual(params(ace.gcode.scripts[0])['VENDOR'], expected)

    def test_empty_brand_generic_without_guessing_from_bambu_sku_or_material(self):
        ace = new(); observe(ace, slots(LIVE)); detail(ace, dict(LIVE, brand='  '))
        self.assertEqual(params(ace.gcode.scripts[0])['VENDOR'], 'Generic')
        self.assertTrue(ace._rfid_sync[1]['complete'])

    def test_missing_detail_brand_is_incomplete_and_retried(self):
        ace = new(); observe(ace, slots(LIVE)); detail(ace, LIVE)
        self.assertEqual(ace.gcode.scripts, [])
        self.assertFalse(ace._rfid_sync[1]['complete'])
        ace.reactor.t += 2.1; observe(ace, slots(LIVE)); detail(ace)
        self.assertEqual(len(ace.gcode.scripts), 1)

    def test_empty_summary_brand_does_not_override_detailed_brand(self):
        for empty in ('', '   '):
            ace = new(); observe(ace, slots(dict(LIVE, brand=empty))); detail(ace)
            self.assertEqual(params(ace.gcode.scripts[0])['VENDOR'], 'Bambu')

    def test_conflicting_nonempty_summary_brand_is_rejected(self):
        ace = new(); observe(ace, slots(dict(LIVE, brand='Other Maker'))); detail(ace)
        self.assertEqual(ace.gcode.scripts, [])
        self.assertFalse(ace._rfid_sync[1]['complete'])

    def test_material_split_only_known_space_prefixes(self):
        for raw, main, sub in [('PLA Matte','PLA','Matte'),('PETG HF','PETG','HF'),
            ('PA6-CF','PA6-CF',''),('PA6-CF High Flow','PA6-CF','High Flow'),
            ('PETG-CF','PETG-CF',''),('New Resin Blend','New Resin Blend','')]:
            ace = new(); spool = dict(LIVE, type=raw)
            observe(ace, slots(spool)); detail(ace, dict(spool, brand='Actual Maker'))
            result = params(ace.gcode.scripts[0])
            self.assertEqual((result['FILAMENT_TYPE'], result['FILAMENT_SUBTYPE']), (main,sub))

    def test_unidentified_and_initial_empty_metadata_never_write(self):
        for spool in (dict(LIVE,rfid=1), dict(LIVE,rfid=3), dict(LIVE,type=''),
                      dict(LIVE,color=[999,0,0])):
            ace = new(); observe(ace, slots(spool))
            self.assertIsNone(ace._filament_query)
            self.assertEqual(ace.gcode.scripts, [])

    def test_initial_rfid2_and_reconnect_rfid2_both_sync(self):
        ace = new(); observe(ace, slots(LIVE)); detail(ace)
        ace._serial_disconnect()
        from test_protocol import Serial
        ace._serial = Serial(ace); ace._connected = True
        ace._connected_at = ace.reactor.t
        observe(ace, slots(LIVE)); detail(ace)
        self.assertEqual(len(ace.gcode.scripts), 2)
        self.assertEqual(ace._feed_assist_index, -1)
        self.assertFalse(any(r['method'].startswith('feed') for r in ace._serial.sent))

    def test_successful_unchanged_tag_does_not_rewrite_manual_settings(self):
        ace = new(); observe(ace, slots(LIVE)); detail(ace)
        for _ in range(5):
            ace.reactor.t += 1; observe(ace, slots(LIVE))
        self.assertEqual(len(ace.gcode.scripts), 1)
        self.assertIsNone(ace._filament_query)

    def test_same_rfid2_color_change_requests_new_details(self):
        ace = new(); observe(ace, slots(LIVE)); detail(ace)
        changed = dict(LIVE, color=[1,2,3])
        observe(ace, slots(changed)); detail(ace, dict(changed, brand='Bambu Lab'))
        self.assertEqual(len(ace.gcode.scripts), 2)
        self.assertEqual(params(ace.gcode.scripts[-1])['FILAMENT_COLOR_RGBA'], '010203')

    def test_stale_detail_after_slot_change_is_discarded(self):
        ace = new(); observe(ace, slots(LIVE))
        changed = dict(LIVE, sku='different', color=[1,2,3])
        observe(ace, slots(changed))
        detail(ace)
        self.assertEqual(ace.gcode.scripts, [])
        ace.reactor.t += 1.1; observe(ace, slots(changed))
        detail(ace, dict(changed,brand='Actual Maker'))
        self.assertEqual(len(ace.gcode.scripts), 1)

    def test_removed_tag_and_aba_reinsertion_invalidate_old_response(self):
        ace = new(); observe(ace, slots(LIVE)); old_state = ace._rfid_sync[1]
        observe(ace, slots(dict(LIVE, rfid=1)))
        observe(ace, slots(LIVE))
        self.assertIsNot(ace._rfid_sync[1], old_state)
        detail(ace)
        self.assertEqual(ace.gcode.scripts, [])

    def test_tag_changes_between_detail_and_deferred_write(self):
        ace = new(); observe(ace, slots(LIVE)); detail(ace, dispatch=False)
        observe(ace, slots(dict(LIVE, rfid=1)), dispatch=False)
        drain(ace)
        self.assertEqual(ace.gcode.scripts, [])

    def test_mismatched_detail_index_rfid_and_fingerprint_never_write(self):
        for changes in ({'index':0},{'rfid':1},{'sku':'other'},{'type':'PETG'},
                        {'color':[4,5,6]}):
            ace = new(); observe(ace, slots(LIVE)); detail(ace, dict(LIVE,brand='Bambu Lab',**changes))
            self.assertEqual(ace.gcode.scripts, [])
            self.assertFalse(ace._rfid_sync[1]['complete'])

    def test_query_timeouts_are_bounded_and_do_not_disconnect(self):
        ace = new(); observe(ace, slots(LIVE))
        for attempt in range(1,4):
            pending = ace._filament_query
            # Keep status fresh, as the real independent heartbeat would.
            ace.reactor.t += 4.9; observe(ace, slots(LIVE))
            pending['timer'](ace.reactor.t + .1)
            self.assertEqual(ace._rfid_sync[1]['attempts'], attempt)
            ace.reactor.t += 2.1; observe(ace, slots(LIVE))
        self.assertIsNone(ace._filament_query)
        self.assertTrue(ace._connected)
        self.assertEqual(ace.gcode.scripts, [])
        self.assertEqual(sum(r['method']=='get_filament_info' for r in ace._serial.sent), 3)

    def test_guard_failure_retries_without_force_and_marks_success_only_after_set(self):
        ace = new(); calls = []
        def protected(script):
            calls.append(script)
            raise RuntimeError('official filament, not configurable')
        ace.gcode.run_script_from_command = protected
        observe(ace, slots(LIVE)); detail(ace)
        self.assertFalse(ace._rfid_sync[1]['complete'])
        self.assertNotIn('FORCE', calls[0])
        ace.gcode.run_script_from_command = ace.gcode.scripts.append
        ace.reactor.t += 2.1; observe(ace, slots(LIVE)); detail(ace)
        self.assertTrue(ace._rfid_sync[1]['complete'])
        self.assertEqual(ace._rfid_sync[1]['attempts'], 2)

    def test_spoolman_or_official_rejection_stops_after_three_attempts(self):
        ace = new(); calls = []
        def protected(script):
            calls.append(script)
            raise RuntimeError('filament_spool_id is configured')
        ace.gcode.run_script_from_command = protected
        for _ in range(3):
            observe(ace, slots(LIVE)); detail(ace); ace.reactor.t += 2.1
        observe(ace, slots(LIVE))
        self.assertEqual(len(calls), 3)
        self.assertIsNone(ace._filament_query)
        self.assertFalse(ace._rfid_sync[1]['complete'])
        self.assertTrue(all('FORCE' not in command for command in calls))

    def test_control_and_manual_query_contention_does_not_consume_attempts(self):
        ace = new(); ace._control_inflight = True
        observe(ace, slots(LIVE))
        self.assertEqual(ace._rfid_sync[1]['attempts'], 0)
        ace._control_inflight = False
        from test_query import Command
        ace.cmd_ACE_QUERY_FILAMENT(Command(0))
        ace.reactor.t += 1.1; observe(ace, slots(LIVE))
        self.assertEqual(ace._rfid_sync[1]['attempts'], 0)

    def test_all_four_channels_serialize_details_without_motion(self):
        ace = new(); all_slots=[dict(LIVE,index=i) for i in range(4)]
        for i in range(4):
            observe(ace, all_slots)
            self.assertEqual(ace._filament_query['index'], i)
            detail(ace, dict(all_slots[i],brand='Maker '+str(i)))
            ace.reactor.t += 1.1
        self.assertEqual([params(s)['CONFIG_EXTRUDER'] for s in ace.gcode.scripts], ['0','1','2','3'])
        self.assertTrue(all(r['method'] in ('get_status','get_filament_info') for r in ace._serial.sent))

    def test_repeated_control_preemption_does_not_exhaust_failure_budget(self):
        for phase in ('reply', 'apply', 'control'):
            ace = new()
            for _ in range(3):
                observe(ace, slots(LIVE))
                if phase == 'reply':
                    ace._status_epoch += 1
                    detail(ace)
                else:
                    detail(ace, dispatch=False)
                    if phase == 'apply': ace._status_epoch += 1
                    else: ace._control_inflight = True
                    drain(ace)
                self.assertEqual(ace._rfid_sync[1]['attempts'], 0)
                self.assertEqual(ace.gcode.scripts, [])
                ace._control_inflight = False
                ace.reactor.t += 1.1
            observe(ace, slots(LIVE)); detail(ace)
            self.assertTrue(ace._rfid_sync[1]['complete'])
            self.assertEqual(ace._rfid_sync[1]['attempts'], 1)
            self.assertEqual(len(ace.gcode.scripts), 1)

    def test_actual_timeout_or_invalid_reply_is_not_refunded_during_control(self):
        for mode in ('timeout', 'invalid'):
            ace = new(); observe(ace, slots(LIVE)); ace._status_epoch += 1
            if mode == 'timeout':
                ace._filament_query['timer'](ace.reactor.t + 5)
            else:
                detail(ace, dict(LIVE,brand='Bambu Lab',rfid=1))
            self.assertEqual(ace._rfid_sync[1]['attempts'], 1)
            self.assertIsNotNone(ace._rfid_sync[1]['last_error'])
            self.assertEqual(ace.gcode.scripts, [])

    def test_disconnect_after_details_before_apply_cancels_write(self):
        ace = new(); observe(ace, slots(LIVE)); detail(ace, dispatch=False)
        ace._serial_disconnect(); drain(ace)
        self.assertEqual(ace.gcode.scripts, [])
        self.assertEqual(ace._rfid_sync, [None]*4)


if __name__ == '__main__': unittest.main(verbosity=2)
