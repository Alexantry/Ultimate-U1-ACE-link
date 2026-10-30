"""Read-only diagnostic tests. Reuses the existing fake serial transport."""
import json
import unittest
from test_protocol import new, frame


class Command:
    def __init__(self, index): self.index = index
    def get_int(self, name):
        assert name == 'INDEX'
        return self.index
    def error(self, message): return RuntimeError(message)


class QueryChecks(unittest.TestCase):
    def start(self, ace, index=1):
        ace.cmd_ACE_QUERY_FILAMENT(Command(index))
        return ace._serial.sent[-1]['id']

    def reply(self, ace, request_id, result, **extra):
        response = {'id': request_id, 'code': 0, 'result': result}
        response.update(extra)
        ace._process_data(frame(ace, response))

    def test_all_channels_use_only_existing_read_request(self):
        for index in range(4):
            ace = new(); transport = ace._serial
            self.start(ace, index)
            self.assertIs(ace._serial, transport)
            self.assertEqual(transport.sent[0]['method'], 'get_filament_info')
            self.assertEqual(transport.sent[0]['params'], {'index': index})
            self.assertEqual(ace._info['status'], 'ready')
            self.assertEqual(ace._status_epoch, 0)
            self.assertFalse(ace._control_inflight)
            self.assertEqual(ace.gcode.scripts, [])

    def test_invalid_channels_never_write(self):
        for index in (-1, 4, True, '1', None):
            ace = new()
            with self.assertRaises(RuntimeError): self.start(ace, index)
            self.assertEqual(ace._serial.sent, [])

    def test_whitelist_preserves_real_brand_without_guessing(self):
        ace = new(); rid = self.start(ace)
        self.reply(ace, rid, {'index': 1, 'sku': 'A01-R2', 'brand': 'Bambu Lab',
                            'type': 'PLA Matte', 'rfid': 2, 'color': [177,85,51],
                            'key': 'DO_NOT_OUTPUT', 'uid': 'DO_NOT_OUTPUT'})
        result = json.loads(ace.gcode.messages[-1].split(' ', 1)[1])
        self.assertEqual(result, {'index': 1, 'sku': 'A01-R2', 'brand': 'Bambu Lab',
                                 'type': 'PLA Matte', 'rfid': 2, 'color': [177,85,51]})
        self.assertNotIn('DO_NOT_OUTPUT', ''.join(ace.gcode.messages))
        self.assertEqual(ace._callback_map, {})
        self.assertIsNone(ace._filament_query)
        self.assertEqual(ace.gcode.scripts, [])

    def test_missing_brand_stays_missing(self):
        ace = new(); rid = self.start(ace)
        self.reply(ace, rid, {'type': 'PLA Matte'})
        result = json.loads(ace.gcode.messages[-1].split(' ', 1)[1])
        self.assertNotIn('brand', result)
        self.assertEqual(ace.gcode.scripts, [])

    def test_reply_text_remains_json_data(self):
        ace = new(); rid = self.start(ace)
        text = 'Bambu\nG28 "test"'
        self.reply(ace, rid, {'brand': text})
        self.assertEqual(json.loads(ace.gcode.messages[-1].split(' ',1)[1])['brand'], text)
        self.assertNotIn('\n', ace.gcode.messages[-1])
        self.assertEqual(ace.gcode.scripts, [])

    def test_control_inflight_rejects_query_without_sending(self):
        ace = new(); ace._control_inflight = True
        with self.assertRaisesRegex(RuntimeError, 'control command'): self.start(ace)
        self.assertEqual(ace._serial.sent, [])
        self.assertTrue(ace._control_inflight)

    def test_duplicate_query_rejected_without_leaking_callback(self):
        ace = new(); rid = self.start(ace)
        with self.assertRaisesRegex(RuntimeError, 'already in progress'): self.start(ace, 2)
        self.assertEqual(list(ace._callback_map), [rid])
        self.assertEqual(len(ace._serial.sent), 1)

    def test_pending_query_does_not_block_control_or_consume_its_reply(self):
        ace = new(); rid = self.start(ace)
        ace._serial.reply = lambda r: {'id': r['id'], 'code': 0}
        ace._command({'method': 'drying_stop'}, ready=False)
        self.assertIn(rid, ace._callback_map)
        self.assertIsNotNone(ace._filament_query)
        self.assertEqual([r['method'] for r in ace._serial.sent], ['get_filament_info','drying_stop'])

    def test_timeout_removes_only_query_and_late_reply_is_ignored(self):
        ace = new(); rid = self.start(ace)
        timer = ace._filament_query['timer']
        ace._periodic_heartbeat_event(ace.reactor.t)
        heartbeat = ace._serial.sent[-1]['id']
        ace.reactor.t += ace.REQUEST_TIMEOUT
        self.assertEqual(timer(ace.reactor.t), ace.reactor.NEVER)
        self.assertNotIn(rid, ace._callback_map)
        self.assertIn(heartbeat, ace._callback_map)
        self.assertTrue(ace._connected)
        messages = ace.gcode.messages[:]
        self.reply(ace, rid, {'brand': 'late'})
        self.assertEqual(ace.gcode.messages, messages)

    def test_disconnect_clears_pending_query(self):
        ace = new(); self.start(ace)
        timer = ace._filament_query['timer']
        ace._serial_disconnect()
        self.assertIsNone(ace._filament_query)
        self.assertEqual(ace._callback_map, {})
        self.assertIn('disconnected', ace.gcode.messages[-1])
        messages = ace.gcode.messages[:]
        timer(ace.reactor.t + 10)
        self.assertEqual(ace.gcode.messages, messages)

    def test_rejection_does_not_echo_untrusted_response_fields(self):
        ace = new(); rid = self.start(ace)
        self.reply(ace, rid, {}, code=1, error={'key':'DO_NOT_OUTPUT'})
        self.assertIn('invalid or rejected', ace.gcode.messages[-1])
        self.assertNotIn('DO_NOT_OUTPUT', ''.join(ace.gcode.messages))
        self.assertIsNone(ace._filament_query)

    def test_wrong_channel_and_invalid_fields_are_rejected(self):
        for result in ({'index':2}, {'index':True}, {'color':[1,2,300]}, {'brand':{}}, {'rfid':True}, []):
            ace = new(); rid = self.start(ace)
            self.reply(ace, rid, result)
            self.assertIn('invalid or rejected', ace.gcode.messages[-1])
            self.assertEqual(ace._callback_map, {})

    def test_crc_renumber_is_cleaned_up_by_timeout(self):
        ace = new(); real = ace._calc_crc; count = [0]
        def crc(data):
            count[0] += 1
            return 0xaaff if count[0] == 1 else real(data)
        ace._calc_crc = crc
        rid = self.start(ace)
        self.assertEqual(rid, 2)
        ace._filament_query['timer'](ace.reactor.t + ace.REQUEST_TIMEOUT)
        self.assertEqual(ace._callback_map, {})

    def test_serial_failure_cleans_query_without_motion(self):
        ace = new(); transport = ace._serial; transport.short = True
        with self.assertRaises(RuntimeError): self.start(ace)
        self.assertIsNone(ace._filament_query)
        self.assertEqual(ace._callback_map, {})
        self.assertFalse(ace._connected)
        self.assertEqual([r['method'] for r in transport.sent], ['get_filament_info'])


if __name__ == '__main__': unittest.main(verbosity=2)
