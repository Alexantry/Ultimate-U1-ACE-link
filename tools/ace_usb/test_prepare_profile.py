"""Draft-only profile generation with synthetic identities and no serial access."""
import contextlib
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import prepare_profile as prepare


class PrepareProfileTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='ace-draft-test-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.now = dt.datetime.now(dt.timezone.utc)
        self.probe = {
            'schema': 1, 'kind': 'ACE_GEN1_READ_ONLY_PROBE',
            'captured_at_utc': self.now.isoformat(), 'device': '/dev/test-ace',
            'usb_identity': {'sysfs_port': '/sys/test-port', 'vid': 'abcd', 'pid': '1234'},
            'snapshot': {
                'info': {'model': 'Anycubic Color Engine Pro', 'slots': 4, 'id': 'synthetic-id',
                         'firmware': 'V1.3.856', 'boot_firmware': 'V1.0.1'},
                'status': {'status': 'ready',
                           'slots': [{'index': i, 'status': 'empty'} for i in range(4)],
                           'dryer_status': {'status': 'stop', 'target_temp': 0}},
            },
        }

    def save(self):
        path = self.root/'probe.json'
        path.write_text(json.dumps(self.probe), encoding='utf-8')
        return path

    def test_draft_stays_locked_and_binds_exact_probe(self):
        path = self.save()
        draft = prepare.build_draft(path, self.now)
        self.assertFalse(draft['write_enabled'])
        self.assertTrue(all(value is False for value in draft['checks'].values()))
        self.assertIsNone(draft['reviewed_at_utc'])
        self.assertEqual(draft['probe_sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(draft['usb_identity'], self.probe['usb_identity'])
        self.assertEqual(draft['device_info_id'], 'synthetic-id')

    def test_other_source_or_boot_cannot_be_drafted(self):
        for key, value in (('firmware', 'V1.3.863'), ('firmware', 'CV1.3.863'),
                           ('boot_firmware', 'V1.0.2')):
            with self.subTest(key=key, value=value):
                original = self.probe['snapshot']['info'][key]
                self.probe['snapshot']['info'][key] = value
                with self.assertRaisesRegex(ValueError, 'Only the tested'):
                    prepare.build_draft(self.save(), self.now)
                self.probe['snapshot']['info'][key] = original

    def test_stale_future_or_naive_timestamp_rejected(self):
        for stamp in (self.now-dt.timedelta(minutes=31), self.now+dt.timedelta(seconds=1),
                      self.now.replace(tzinfo=None)):
            with self.subTest(stamp=stamp):
                self.probe['captured_at_utc'] = stamp.isoformat()
                with self.assertRaisesRegex(ValueError, '30 minutes'):
                    prepare.build_draft(self.save(), self.now)

    def test_missing_usb_or_invalid_device_identity_rejected(self):
        self.probe['usb_identity'] = {}
        with self.assertRaisesRegex(ValueError, 'USB'):
            prepare.build_draft(self.save(), self.now)
        self.probe['usb_identity'] = {'sysfs_port': '/sys/test', 'vid': 'abcd', 'pid': '1234'}
        self.probe['snapshot']['info']['id'] = True
        with self.assertRaisesRegex(ValueError, 'identity'):
            prepare.build_draft(self.save(), self.now)

    def test_busy_slot_or_drying_blocks_draft(self):
        self.probe['snapshot']['status']['slots'][0]['status'] = 'feeding'
        with self.assertRaisesRegex(ValueError, 'idle slots'):
            prepare.build_draft(self.save(), self.now)
        self.probe['snapshot']['status']['slots'][0]['status'] = 'ready'
        self.probe['snapshot']['status']['dryer_status']['status'] = 'drying'
        with self.assertRaisesRegex(ValueError, 'dryer'):
            prepare.build_draft(self.save(), self.now)

    def test_existing_output_is_never_overwritten(self):
        path = self.root/'draft.json'; path.write_text('existing')
        with self.assertRaises(FileExistsError):
            prepare.write_draft(path, {'write_enabled': False})
        self.assertEqual(path.read_text(), 'existing')

    def test_cli_has_no_serial_dependency_and_creates_only_locked_draft(self):
        probe = self.save(); output = self.root/'draft.json'
        with patch.dict('sys.modules', {'serial': None}), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(prepare.main(['--probe', str(probe), '--output', str(output)]), 0)
        self.assertFalse(json.loads(output.read_text())['write_enabled'])


if __name__ == '__main__':
    unittest.main()
