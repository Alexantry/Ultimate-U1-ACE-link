"""Offline failure-path tests. FakeSession never imports serial or opens hardware."""
import contextlib
import copy
import datetime as dt
import hashlib
import io
import json
import struct
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import ace_iap as app
from protocol import RPCError, ProtocolError, STAGING_BASE, encode_frame, FrameParser

ROOT = Path(__file__).resolve().parent
USB = {'sysfs_port': '/sys/devices/test/usb1/1-1', 'vid': 'abcd', 'pid': '1234', 'serial': 'ACE_1'}


class Audit:
    def __init__(self): self.events = []
    def event(self, name, **fields): self.events.append((name, fields))


class Tick:
    def __init__(self): self.value = 0.0
    def clock(self): self.value += 0.1; return self.value


class FakeSession:
    def __init__(self, device='fake', audit=None, expected_identity=None):
        self.identity = USB.copy()
        self.methods = []
        self.chunks = []
        self.source = 'V1.3.856'
        self.target = 'CV1.3.863'
        self.after = False
        self.upgrade_response = {'code': 0, 'msg': 'success'}
        self.finish_response = {'code': 0, 'msg': 'success'}
        self.finish_error = None
        self.chunk_error_at = None
        self.info_override = {}
        self.status_override = {}
        self.closed = False
        self.reopens = 0
        self.late_chunk_error = None
    def info(self):
        result = {'id': 1, 'model': 'Anycubic Color Engine Pro', 'slots': 4,
                  'firmware': self.target if self.after else self.source, 'boot_firmware': 'V1.0.1'}
        result.update(self.info_override)
        return result
    def status(self):
        result = {'status': 'ready', 'slots': [{'index': i, 'status': 'ready', 'rfid': 0} for i in range(4)],
                  'dryer_status': {'status': 'stop', 'target_temp': 0}}
        result.update(self.status_override)
        return result
    def rpc(self, method, params=None, timeout=1.5):
        self.methods.append((method, params))
        if method == 'get_info': return {'code': 0, 'result': self.info()}
        if method == 'get_status': return {'code': 0, 'result': self.status()}
        if method == 'iap_version': return {'code': 0, 'result': {'boot': 'V1.0.1'}}
        if method == 'iap_upgrade':
            if isinstance(self.upgrade_response, Exception): raise self.upgrade_response
            return self.upgrade_response
        if method == 'iap_upgrade_finish':
            self.after = True
            if self.finish_error: raise self.finish_error
            return self.finish_response
        raise AssertionError('Unexpected hardware method: ' + method)
    def send_chunk(self, addr, data):
        if len(self.chunks) == self.chunk_error_at: raise OSError('simulated USB failure')
        self.chunks.append((addr, data))
    def drain_transfer_replies(self, duration=0.0):
        if self.late_chunk_error: raise self.late_chunk_error
    def reopen(self): self.reopens += 1
    def close(self): self.closed = True


def profile():
    return {'source_firmware': 'V1.3.856', 'boot_firmware': 'V1.0.1', 'device_info_id': 1}


def image():
    return {'expected_runtime_version': 'CV1.3.863', 'announced_version': '1.3.863'}


def fast_verify(session, record, before, audit):
    return app.verify_target(session, record, before, audit, timeout=2.0,
                             clock=Tick().clock, sleep=lambda _: None)


class IapTests(unittest.TestCase):
    def run_flash(self, session):
        audit = Audit()
        result = app.flash_once(session, bytes(range(145)), image(), profile(), audit,
                                sleep=lambda _: None, verifier=fast_verify)
        return result, audit
    def test_one_transfer_exact_chunks_and_runtime_transition(self):
        session = FakeSession()
        result, audit = self.run_flash(session)
        self.assertEqual(result['outcome'], 'VERSION_CHANGED_AND_READY')
        self.assertFalse(result['flash_readback_verified'])
        self.assertFalse(result['nfc_and_motion_tested'])
        self.assertEqual([a for a, _ in session.chunks], [STAGING_BASE, STAGING_BASE+64, STAGING_BASE+128])
        self.assertEqual([len(d) for _, d in session.chunks], [64, 64, 17])
        self.assertEqual(b''.join(d for _, d in session.chunks), bytes(range(145)))
        self.assertEqual([m for m, _ in session.methods].count('iap_upgrade'), 1)
        self.assertEqual([m for m, _ in session.methods].count('iap_upgrade_finish'), 1)
    def test_explicit_start_rejection_sends_no_chunks(self):
        for reply in ({'code': 1}, {'code': 0, 'msg': 'failed'}, {'code': False}, {}, {'code': 0, 'error': {}}):
            with self.subTest(reply=reply):
                session = FakeSession(); session.upgrade_response = reply
                with self.assertRaises(RPCError): self.run_flash(session)
                self.assertEqual(session.chunks, [])
                self.assertNotIn('iap_upgrade_finish', [m for m, _ in session.methods])
    def test_start_timeout_is_not_retried(self):
        session = FakeSession(); session.upgrade_response = app.LinkTimeout('lost')
        with self.assertRaises(app.LinkTimeout): self.run_flash(session)
        self.assertEqual([m for m, _ in session.methods].count('iap_upgrade'), 1)
        self.assertFalse(session.chunks)
    def test_mid_transfer_failure_never_finishes_or_retries(self):
        session = FakeSession(); session.chunk_error_at = 1
        audit = Audit()
        with self.assertRaises(OSError):
            app.flash_once(session, b'x'*200, image(), profile(), audit, sleep=lambda _: None)
        self.assertEqual(len(session.chunks), 1)
        self.assertNotIn('iap_upgrade_finish', [m for m, _ in session.methods])
        event = next(v for n, v in audit.events if n == 'transfer_stopped')
        self.assertEqual(event['last_fully_completed_host_offset'], 64)
        self.assertTrue(event['device_receipt_unknown'])
    def test_finish_disconnect_requires_independent_changed_runtime(self):
        session = FakeSession(); session.finish_error = app.LinkTimeout('reboot')
        result, audit = self.run_flash(session)
        self.assertEqual(result['outcome'], 'VERSION_CHANGED_AND_READY')
        self.assertIn('iap_finish_ack_missing', [n for n, _ in audit.events])
    def test_finish_error_is_not_treated_as_expected_disconnect(self):
        session = FakeSession(); session.finish_response = {'code': 0, 'msg': 'failure'}
        with self.assertRaises(RPCError): self.run_flash(session)
    def test_late_chunk_error_aborts_before_finish(self):
        session = FakeSession(); session.late_chunk_error = RPCError('delayed refusal')
        with self.assertRaises(RPCError): self.run_flash(session)
        self.assertNotIn('iap_upgrade_finish', [m for m, _ in session.methods])
    def test_old_runtime_after_sent_bytes_is_failure(self):
        session = FakeSession(); session.target = session.source
        with self.assertRaises(app.IndeterminateFlash): self.run_flash(session)
    def test_duplicate_flash_refused_before_iap(self):
        session = FakeSession(); session.source = 'CV1.3.863'
        p = profile(); p['source_firmware'] = session.source
        with self.assertRaises(app.PreparationError):
            app.flash_once(session, b'x'*64, image(), p, Audit(), sleep=lambda _: None)
        self.assertNotIn('iap_upgrade', [m for m, _ in session.methods])
    def test_live_source_drift_refused(self):
        session = FakeSession(); session.source = 'unexpected'
        with self.assertRaises(app.PreparationError): self.run_flash(session)
        self.assertFalse(session.chunks)
    def test_pretransfer_busy_or_drying_refused(self):
        for change in ({'status': 'busy'}, {'dryer_status': {'status': 'drying','target_temp': 70}},
                       {'slots': [{'index': 0}]*4}):
            with self.subTest(change=change):
                session = FakeSession(); session.status_override = change
                with self.assertRaises(app.PreparationError): self.run_flash(session)
                self.assertNotIn('iap_upgrade', [m for m, _ in session.methods])
    def test_target_bad_boot_identity_slots_or_dryer_never_pass(self):
        for info_change, status_change in [({'boot_firmware':'UNEXPECTED'}, {}), ({'id':2}, {}),
                ({'model':'ACE2'}, {}), ({}, {'slots':[{'index':0}]*4}),
                ({}, {'slots':{'a':1,'b':2,'c':3,'d':4}}),
                ({}, {'dryer_status':{'status':'drying','target_temp':70}}), ({}, {'status':'upgrading'})]:
            with self.subTest(info=info_change, status=status_change):
                session = FakeSession(); before = app.snapshot(session); session.after = True
                session.info_override = info_change; session.status_override = status_change
                with self.assertRaises(app.IndeterminateFlash): fast_verify(session, image(), before, Audit())
    def test_two_consecutive_target_samples_required(self):
        session = FakeSession(); before = app.snapshot(session); session.after = True
        result = fast_verify(session, image(), before, Audit())
        self.assertEqual([m for m,_ in session.methods].count('get_status'), 3)  # before + two fresh
        self.assertEqual(result['info']['firmware'], 'CV1.3.863')
    def test_probe_uses_read_only_allowlist(self):
        session = FakeSession(); app.snapshot(session)
        self.assertEqual([m for m,_ in session.methods], ['get_info','iap_version','get_status'])
    def test_strict_transfer_json_ack_validation(self):
        for bad in ({'code':True}, {'code':0, 'msg':'failed'}, {'code':0,'error':{}}, {}, []):
            with self.subTest(reply=bad):
                with self.assertRaises(RPCError): app.success_reply(bad, 'test')


class FakeSerial:
    def __init__(self, incoming=b''): self.incoming = incoming; self.writes = []
    @property
    def in_waiting(self): return len(self.incoming)
    def read(self, count):
        result, self.incoming = self.incoming[:count], self.incoming[count:]
        return result
    def write(self, data): self.writes.append(data); return len(data)


class SerialReplyTests(unittest.TestCase):
    def session(self, payload):
        s = object.__new__(app.SerialSession)
        s.serial = FakeSerial(encode_frame(payload)); s.parser=FrameParser(); s.audit=Audit(); s.request_id=0
        return s
    def test_real_send_chunk_path_rejects_whitespace_error(self):
        s = self.session(b' \n {"code":1,"msg":"failed"}')
        with self.assertRaises(RPCError): s.send_chunk(STAGING_BASE,b'a')
        self.assertEqual(len(s.serial.writes),1)
    def test_transfer_replies_reject_duplicate_keys_and_nonobjects(self):
        for payload in (b'{"code":1,"code":0}', b'[ {"code":0} ]', b' null', b' true',
                        b'{"code":0,"error":{}}', b'{"code":0,"msg":"failed"}',b'{"code":false}'):
            with self.subTest(payload=payload):
                s=self.session(payload)
                with self.assertRaises(ProtocolError): s.drain_transfer_replies()
    def test_unknown_binary_is_framed_but_not_claimed_ack(self):
        s=self.session(b'\x55\x00\x40\x02\x08')
        s.drain_transfer_replies()
        observed = next(v for n, v in s.audit.events if n == 'chunk_reply_observed')
        self.assertIn('not treated',observed['meaning'])
    def test_finish_rpc_rejects_late_error_even_if_id_does_not_match(self):
        s=self.session(b'{"id":999,"code":1,"msg":"failed"}')
        with self.assertRaises(RPCError): s.rpc('iap_upgrade_finish',{})
    def test_transfer_frame_crc_failure(self):
        s=self.session(b'{"code":0}')
        b=bytearray(s.serial.incoming); b[-3]^=1; s.serial.incoming=bytes(b)
        with self.assertRaises(ProtocolError): s.drain_transfer_replies()
    def test_partial_transfer_frame_blocks_commit_boundary(self):
        s=self.session(b'{"code":1,"msg":"failed"}')
        s.serial.incoming=s.serial.incoming[:-2]
        with self.assertRaises(app.IndeterminateFlash):
            s.drain_transfer_replies(duration=0.25,clock=Tick().clock,sleep=lambda _:None)
        self.assertEqual(s.serial.writes,[])


class OfflineEntryTests(unittest.TestCase):
    def setUp(self):
        # Public tests use synthetic ARM-vector fixtures, never third-party bins.
        package_root = ROOT
        self.public_manifest = json.loads((package_root/'images.json').read_text())
        temporary = tempfile.TemporaryDirectory(prefix='ace-public-test-')
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root/'firmware').mkdir()
        manifest = copy.deepcopy(self.public_manifest)
        for counter, record in enumerate(manifest['images'].values()):
            data = bytearray(bytes([counter + 1]) * 512)
            struct.pack_into('<II', data, 0, 0x20001000, app.APP_BASE + 0x101)
            record.update(size=len(data), sha256=hashlib.sha256(data).hexdigest(),
                          crc16_mcrf4xx=app.crc16(data))
            (root/record['file']).write_bytes(data)
        (root/'images.json').write_text(json.dumps(manifest))
        profile = json.loads((package_root/'device-profile.json').read_text())
        profile['image_sha256'] = manifest['images']['opencubic-gen1']['sha256']
        (root/'device-profile.json').write_text(json.dumps(profile))
        local_root = patch.dict(globals(), ROOT=root)
        local_root.start(); self.addCleanup(local_root.stop)
        app_root = patch.object(app, 'ROOT', root)
        app_root.start(); self.addCleanup(app_root.stop)

    def test_pinned_manifest_and_synthetic_images_verified(self):
        expected = {
            'opencubic-gen1': '95e0b6ddb1e77d624d127ac91d9b3e21caf58adc5e1598faf2be3feacf9b4048',
            'stock-gen1-863': '3f3676ba357749b3d0367922cb7f6b0dedc9b3d104c1c29e719ac3e563f5eb63',
        }
        self.assertEqual({k: v['sha256'] for k, v in self.public_manifest['images'].items()}, expected)
        for image_id in ('opencubic-gen1','stock-gen1-863'):
            data, record = app.verify_image(ROOT/'images.json', image_id)
            self.assertLessEqual(len(data), 114688)
            self.assertEqual(hashlib.sha256(data).hexdigest(), record['sha256'])
    def test_inspect_plan_no_session_or_serial(self):
        for command in ('inspect', 'plan'):
            with self.subTest(command=command):
                factory = Mock(side_effect=AssertionError('Must not open serial'))
                with contextlib.redirect_stdout(io.StringIO()), patch.dict('sys.modules', {'serial': None}):
                    self.assertEqual(app.main([command], session_factory=factory), 0)
                factory.assert_not_called()
    def test_default_flash_gate_precedes_every_hardware_action(self):
        factory = Mock(side_effect=AssertionError('Must not open serial'))
        args = ['flash','--device','/dev/serial/by-id/usb-ANYCUBIC_ACE_1-if00',
                '--probe','does-not-exist','--log','must-not-create.jsonl','--result','must-not-create.json']
        with contextlib.redirect_stderr(io.StringIO()), patch.dict('sys.modules', {'serial': None}):
            self.assertEqual(app.main(args, session_factory=factory), 2)
        factory.assert_not_called()
        self.assertFalse((Path.cwd()/'must-not-create.jsonl').exists())
    def test_rejects_bad_hash_and_oversize_locally(self):
        with tempfile.TemporaryDirectory(prefix='ace-offline-test-') as folder:
            root = Path(folder); (root/'firmware').mkdir()
            source = read_manifest = json.loads((ROOT/'images.json').read_text())
            rec = source['images']['opencubic-gen1']
            data = (ROOT/rec['file']).read_bytes()
            path = root/rec['file']; path.write_bytes(bytes([data[0]^1])+data[1:])
            manifest = root/'images.json'; manifest.write_text(json.dumps(source))
            with self.assertRaisesRegex(app.PreparationError,'SHA256'): app.verify_image(manifest,'opencubic-gen1')
            path.write_bytes(b'x'*114689); rec['size']=114689; manifest.write_text(json.dumps(source))
            with self.assertRaisesRegex(app.PreparationError,'size'): app.verify_image(manifest,'opencubic-gen1')
    def test_path_escape_refused(self):
        with tempfile.TemporaryDirectory(prefix='ace-offline-test-') as folder:
            manifest = json.loads((ROOT/'images.json').read_text())
            manifest['images']['opencubic-gen1']['file'] = '../outside.bin'
            path = Path(folder)/'images.json'; path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(app.PreparationError,'escapes'): app.verify_image(path,'opencubic-gen1')
    def test_profile_unreviewed_or_stale_refused(self):
        p = json.loads((ROOT/'device-profile.json').read_text())
        _, rec = app.verify_image(ROOT/'images.json','opencubic-gen1')
        with self.assertRaisesRegex(app.PreparationError,'locked'): app.validate_write_profile(p,rec,p['device'])
        p['write_enabled']=True
        with self.assertRaisesRegex(app.PreparationError,'Incomplete'): app.validate_write_profile(p,rec,p['device'])
    def test_entire_cli_flash_simulation_with_bound_fresh_probe(self):
        with tempfile.TemporaryDirectory(prefix='ace-offline-test-') as folder:
            temp=Path(folder); probe_path=temp/'probe.json'; profile_path=temp/'profile.json'
            session=FakeSession(); factory=Mock(return_value=session)
            with contextlib.redirect_stdout(io.StringIO()), patch.dict('sys.modules',{'serial':None}):
                code=app.main(['probe','--device','fake','--output',str(probe_path),
                               '--log',str(temp/'probe.jsonl')],session_factory=factory)
            self.assertEqual(code,0); self.assertTrue(session.closed)
            p=json.loads((ROOT/'device-profile.json').read_text())
            p.update(write_enabled=True,device='fake',source_firmware='V1.3.856',boot_firmware='V1.0.1',
                     device_info_id=1,usb_identity=USB,reviewed_at_utc=app.utc_now(),
                     probe_sha256=hashlib.sha256(probe_path.read_bytes()).hexdigest())
            p['checks']={key:True for key in p['checks']}
            profile_path.write_text(json.dumps(p))
            new_session=FakeSession(); factory=Mock(return_value=new_session)
            original=app.flash_once
            def fast(*args,**kwargs): return original(*args,**kwargs,sleep=lambda _:None,verifier=fast_verify)
            with contextlib.redirect_stdout(io.StringIO()), patch.dict('sys.modules',{'serial':None}), patch.object(app,'flash_once',side_effect=fast):
                code=app.main(['flash','--device','fake','--profile',str(profile_path),'--probe',str(probe_path),
                               '--log',str(temp/'flash.jsonl'),'--result',str(temp/'result.json')],session_factory=factory)
            self.assertEqual(code,0)
            self.assertTrue(new_session.closed)
            expected,_=app.verify_image(ROOT/'images.json','opencubic-gen1')
            self.assertEqual(b''.join(data for _,data in new_session.chunks),expected)
            self.assertEqual(len(new_session.chunks),(len(expected)+63)//64)
            self.assertEqual(json.loads((temp/'result.json').read_text())['outcome'],'VERSION_CHANGED_AND_READY')
            self.assertEqual(factory.call_args.kwargs['expected_identity'],USB)
            p['reviewed_at_utc']=(dt.datetime.now(dt.timezone.utc)-dt.timedelta(hours=1)).isoformat()
            with self.assertRaisesRegex(app.PreparationError,'30 minutes'):
                app.validate_write_profile(p,json.loads((ROOT/'images.json').read_text())['images']['opencubic-gen1'],'fake')


if __name__ == '__main__':
    unittest.main(verbosity=2)
