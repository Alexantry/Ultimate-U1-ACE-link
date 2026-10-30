"""Offline transport regression tests; never open serial or contact hardware."""
import json
import types
import unittest
from unittest.mock import patch

import ace_iap as app
from protocol import FrameParser, ProtocolError, RPCError, encode_frame
from test_iap import Audit, FakeSerial, USB


def frame(value):
    return encode_frame(json.dumps(value).encode('utf-8'))


SUCCESS = {'id': 1, 'code': 0, 'msg': 'success'}
STALE_ERROR = {'id': 999, 'code': 1, 'msg': 'failed'}


class BatchedReplyTests(unittest.TestCase):
    def session(self, incoming=b''):
        session = object.__new__(app.SerialSession)
        session.serial = FakeSerial(incoming)
        session.parser = FrameParser()
        session.audit = Audit()
        session.request_id = 0
        session._iap_started = False
        return session

    def test_success_then_stale_error_same_batch_never_returns_success(self):
        for method in ('iap_upgrade', 'iap_upgrade_finish'):
            with self.subTest(method=method):
                session = self.session(frame(SUCCESS) + frame(STALE_ERROR))
                with self.assertRaises(RPCError):
                    session.rpc(method, {})
                self.assertEqual(len(session.serial.writes), 1)

    def test_stale_error_then_success_same_batch_is_rejected(self):
        for method in ('iap_upgrade', 'iap_upgrade_finish'):
            with self.subTest(method=method):
                session = self.session(frame(STALE_ERROR) + frame(SUCCESS))
                with self.assertRaises(RPCError):
                    session.rpc(method, {})

    def test_late_matching_error_is_not_hidden_by_success(self):
        for method in ('iap_upgrade', 'iap_upgrade_finish'):
            for failure in ({'id': 1, 'code': 1}, {'id': 1, 'code': 0, 'error': {}},
                            {'id': 1, 'code': 0, 'msg': 'failed'}):
                with self.subTest(method=method, failure=failure):
                    session = self.session(frame(SUCCESS) + frame(failure))
                    with self.assertRaises(RPCError):
                        session.rpc(method, {})

    def test_success_batch_consumed_without_losing_extra_successes(self):
        session = self.session(frame({'id': 0, 'code': 0}) + frame(SUCCESS)
                               + frame({'id': 7, 'code': 0}))
        self.assertEqual(session.rpc('iap_upgrade', {}), SUCCESS)
        self.assertEqual(session.parser.pending_bytes, 0)
        self.assertEqual(session.serial.in_waiting, 0)

    def test_duplicate_matching_success_is_ambiguous(self):
        session = self.session(frame(SUCCESS) * 2)
        with self.assertRaisesRegex(ProtocolError, 'Duplicate matching'):
            session.rpc('iap_upgrade', {})

    def test_read_only_preflight_still_filters_unmatched_errors(self):
        for batch in (frame(STALE_ERROR) + frame(SUCCESS), frame(SUCCESS) + frame(STALE_ERROR)):
            with self.subTest(batch=batch):
                session = self.session(batch)
                self.assertEqual(session.rpc('get_info'), SUCCESS)
                self.assertFalse(session._iap_started)

    def test_late_error_during_runtime_verification_is_rejected(self):
        session = self.session(frame(SUCCESS))
        self.assertEqual(session.rpc('iap_upgrade', {}), SUCCESS)
        session.serial.incoming = frame({'id': 2, 'code': 0}) + frame(STALE_ERROR)
        with self.assertRaises(RPCError):
            session.rpc('get_info')

    def test_reopen_preserves_strict_iap_state(self):
        session = self.session()
        session._iap_started = True
        session.identity = USB.copy()
        session.device = 'fake'
        session.serial = None
        fake = FakeSerial(frame(STALE_ERROR) + frame(SUCCESS))
        fake.close = lambda: None
        module = types.SimpleNamespace(Serial=lambda *args, **kwargs: fake)
        with patch.object(app, 'require_unused_device'), \
             patch.object(app, 'serial_identity', return_value=USB.copy()), \
             patch.dict('sys.modules', {'serial': module}):
            session.reopen()
        self.assertTrue(session._iap_started)
        with self.assertRaises(RPCError):
            session.rpc('get_status')

    def test_trailing_invalid_json_is_not_silently_dropped(self):
        session = self.session(frame(SUCCESS) + encode_frame(b'{"id":2,"code":0,"code":1}'))
        with self.assertRaises(ProtocolError):
            session.rpc('iap_upgrade', {})


if __name__ == '__main__':
    unittest.main(verbosity=2)
