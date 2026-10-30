"""Downloader failure boundaries; all responses and images are synthetic."""
import copy
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import Mock, patch

import ace_iap
import fetch_firmware as fetch


class FetchTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='ace-download-test-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.manifest = copy.deepcopy(json.loads((fetch.ROOT/'images.json').read_text()))
        data = bytearray(b'x' * 512)
        struct.pack_into('<II', data, 0, 0x20001000, ace_iap.APP_BASE + 0x101)
        self.data = bytes(data)
        self.record = self.manifest['images']['opencubic-gen1']
        self.record.update(size=len(data), sha256=hashlib.sha256(data).hexdigest(),
                           crc16_mcrf4xx=ace_iap.crc16(data))
        self.write_manifest()
        pins = patch.dict(fetch.PINNED, {'opencubic-gen1': (
            self.record['download_url'], self.record['sha256'], len(data))})
        pins.start(); self.addCleanup(pins.stop)
        self.destination = self.root/self.record['file']

    def write_manifest(self):
        (self.root/'images.json').write_text(json.dumps(self.manifest))

    def test_exact_response_saved_and_second_call_does_not_download(self):
        opener = Mock(return_value=io.BytesIO(self.data))
        self.assertEqual(fetch.fetch_image('opencubic-gen1', self.root, opener), self.destination)
        self.assertEqual(self.destination.read_bytes(), self.data)
        self.assertEqual(fetch.fetch_image('opencubic-gen1', self.root, opener), self.destination)
        self.assertEqual(opener.call_count, 1)

    def test_bad_response_does_not_create_an_image(self):
        with self.assertRaisesRegex(ValueError, 'nothing saved'):
            fetch.fetch_image('opencubic-gen1', self.root, Mock(return_value=io.BytesIO(b'bad')))
        self.assertFalse(self.destination.exists())

    def test_existing_invalid_file_is_never_overwritten(self):
        self.destination.parent.mkdir(); self.destination.write_bytes(b'existing')
        opener = Mock(side_effect=AssertionError('no download'))
        with self.assertRaises(ace_iap.PreparationError):
            fetch.fetch_image('opencubic-gen1', self.root, opener)
        self.assertEqual(self.destination.read_bytes(), b'existing')
        opener.assert_not_called()

    def test_changed_manifest_url_is_rejected_before_network(self):
        self.record['download_url'] = 'https://example.invalid/other.bin'
        self.write_manifest()
        opener = Mock(side_effect=AssertionError('no download'))
        with self.assertRaisesRegex(ValueError, 'pinned'):
            fetch.fetch_image('opencubic-gen1', self.root, opener)
        opener.assert_not_called()

    def test_destination_escape_is_rejected_before_network(self):
        self.record['file'] = '../outside.bin'; self.write_manifest()
        opener = Mock(side_effect=AssertionError('no download'))
        with self.assertRaisesRegex(ValueError, 'destination'):
            fetch.fetch_image('opencubic-gen1', self.root, opener)
        opener.assert_not_called()


if __name__ == '__main__':
    unittest.main()
