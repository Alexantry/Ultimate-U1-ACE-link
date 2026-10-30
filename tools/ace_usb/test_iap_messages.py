"""Exact Gen1 IAP status semantics, using only in-memory serial transports."""
import json
import unittest

import ace_iap as app
from protocol import FrameParser, ProtocolError, RPCError, STAGING_BASE, encode_frame
from test_iap import Audit, FakeSerial, FakeSession, fast_verify, image, profile


def frame(reply):
    return encode_frame(json.dumps(reply).encode())


WRITE = {'id': 0, 'code': 0, 'msg': 'write_success', 'result': {}}
FINISH = {'id': 1, 'code': 0, 'msg': 'Upgrade_success', 'result': {}}


class IapMessageTests(unittest.TestCase):
    def session(self, replies=(), chunks=False):
        session = object.__new__(app.SerialSession)
        session.serial = FakeSerial(b''.join(frame(r) for r in replies))
        session.parser = FrameParser()
        session.audit = Audit()
        session.request_id = 0
        session._iap_started = True
        session._chunks_started = chunks
        return session

    def test_write_success_accepted_only_after_a_complete_chunk_write(self):
        session = self.session([WRITE])
        with self.assertRaises(RPCError):
            session.drain_transfer_replies()
        session = self.session([WRITE])
        session.send_chunk(STAGING_BASE, b'abc')
        self.assertTrue(session._chunks_started)
        self.assertEqual(len(session.serial.writes), 1)

    def test_write_success_exact_shape_rejects_errors_and_wrong_identity(self):
        changes = ({'id': 1}, {'id': False}, {'id': None}, {'code': False}, {'code': 1},
                   {'error': {}}, {'error': False}, {'msg': 'write_error1'},
                   {'msg': 'write_error2'}, {'msg': 'Write_success'}, {'msg': ' write_success'},
                   {'result': None}, {'result': {'error': 1}})
        for change in changes:
            with self.subTest(change=change):
                session = self.session([{**WRITE, **change}], chunks=True)
                with self.assertRaises(ProtocolError):
                    session.drain_transfer_replies()
        session = self.session([{**WRITE, 'error': None}], chunks=True)
        session.drain_transfer_replies()

    def test_delayed_write_notification_is_not_finish_ack(self):
        session = self.session([WRITE, FINISH, WRITE], chunks=True)
        self.assertEqual(session.rpc('iap_upgrade_finish', {}), FINISH)
        self.assertEqual(session.serial.in_waiting, 0)
        self.assertEqual(len(session.audit.events), 3)

    def test_only_write_notification_does_not_satisfy_finish_request(self):
        session = self.session([WRITE], chunks=True)
        with self.assertRaises(app.LinkTimeout):
            session.rpc('iap_upgrade_finish', {}, timeout=0.002)

    def test_delayed_write_notification_allowed_during_runtime_check(self):
        answer = {'id': 1, 'code': 0, 'result': {'firmware': 'CV1.3.863'}}
        session = self.session([WRITE, answer, WRITE], chunks=True)
        self.assertEqual(session.rpc('get_info'), answer)

    def test_start_never_accepts_write_success_or_upgrading(self):
        for chunks in (False, True):
            for reply in (WRITE, {**WRITE, 'id': 1}, {'id': 1, 'code': 0, 'msg': 'upgrading'}):
                with self.subTest(chunks=chunks, reply=reply):
                    session = self.session([reply], chunks=chunks)
                    with self.assertRaises(ProtocolError):
                        session.rpc('iap_upgrade', {})

    def test_upgrading_rejected_in_transfer_finish_and_verification(self):
        reply = {'id': 1, 'code': 0, 'msg': 'upgrading', 'result': {}}
        session = self.session([reply], chunks=True)
        with self.assertRaises(RPCError):
            session.drain_transfer_replies()
        for method in ('iap_upgrade_finish', 'get_info', 'get_status'):
            with self.subTest(method=method):
                session = self.session([reply], chunks=True)
                with self.assertRaises(RPCError):
                    session.rpc(method)

    def test_finish_accepts_only_exact_success_and_matching_request(self):
        for change in ({'id': 0}, {'id': False}, {'code': False}, {'code': 1},
                       {'error': {}}, {'error': False}, {'result': None}, {'result': {'error': 1}},
                       {'msg': 'upgrade_success'}, {'msg': 'Upgrade_error'}):
            with self.subTest(change=change):
                session = self.session([{**FINISH, **change}], chunks=True)
                with self.assertRaises(ProtocolError):
                    session.rpc('iap_upgrade_finish', {})
        session = self.session([{**FINISH, 'error': None}], chunks=True)
        self.assertEqual(session.rpc('iap_upgrade_finish', {})['msg'], 'Upgrade_success')

    def test_finish_success_rejected_outside_finish_rpc(self):
        session = self.session([FINISH], chunks=True)
        with self.assertRaises(RPCError):
            session.drain_transfer_replies()
        for method in ('iap_upgrade', 'get_info', 'get_status'):
            with self.subTest(method=method):
                session = self.session([FINISH], chunks=True)
                with self.assertRaises(RPCError):
                    session.rpc(method)

    def test_finish_success_does_not_hide_a_later_negative_frame(self):
        session = self.session([FINISH, {'id': 0, 'code': 2, 'msg': 'write_error2'}], chunks=True)
        with self.assertRaises(RPCError):
            session.rpc('iap_upgrade_finish', {})

    def test_raw_iap_reply_logged_before_semantic_or_json_rejection(self):
        bad = {'id': 1, 'code': 0, 'msg': 'upgrading'}
        session = self.session([bad])
        with self.assertRaises(RPCError):
            session.rpc('iap_upgrade', {})
        name, event = session.audit.events[0]
        self.assertEqual(name, 'iap_reply_received')
        self.assertEqual(bytes.fromhex(event['payload_hex']), json.dumps(bad).encode())
        session = self.session(chunks=True)
        raw = b'{"code":0,"code":1}'
        session.serial.incoming = encode_frame(raw)
        with self.assertRaises(ProtocolError):
            session.drain_transfer_replies()
        self.assertEqual(bytes.fromhex(session.audit.events[0][1]['payload_hex']), raw)

    def test_special_finish_reply_still_requires_target_runtime_verification(self):
        class Gen1Session(FakeSession):
            _iap_started = True
            request_id = 20
            def rpc(self, method, params=None, timeout=1.5):
                result = super().rpc(method, params, timeout)
                if method == 'iap_upgrade_finish':
                    return {**FINISH, 'id': self.request_id}
                return result
        session = Gen1Session()
        result = app.flash_once(session, b'x' * 65, image(), profile(), Audit(),
                                sleep=lambda _: None, verifier=fast_verify)
        self.assertEqual(result['outcome'], 'VERSION_CHANGED_AND_READY')
        session = Gen1Session()
        session.target = session.source
        with self.assertRaises(app.IndeterminateFlash):
            app.flash_once(session, b'x' * 65, image(), profile(), Audit(),
                           sleep=lambda _: None, verifier=fast_verify)


if __name__ == '__main__':
    unittest.main(verbosity=2)
