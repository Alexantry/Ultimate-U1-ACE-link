"""Offline-only protocol tests. No serial module or device transport."""

import ast
import json
from pathlib import Path
import random
import struct
import unittest

from protocol import (MAX_IMAGE_BYTES, STAGING_BASE, STAGING_END, FrameParser,
                      ProtocolError, RPCError, crc16, decode_response,
                      decode_json_object, encode_chunk, encode_frame, encode_request)


def bitwise_crc(data):
    value = 0xFFFF
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = ((value >> 1) ^ 0x8408) if value & 1 else (value >> 1)
    return value & 0xFFFF


class ProtocolTests(unittest.TestCase):
    def test_crc_known_answers(self):
        self.assertEqual(crc16(b"123456789"), 0x6F91)
        self.assertEqual(crc16(b""), 0xFFFF)

    def test_crc_independent_oracle(self):
        rng = random.Random(804)
        for length in (0, 1, 2, 3, 63, 64, 65, 255, 1024, 4096):
            data = bytes(rng.randrange(256) for _ in range(length))
            with self.subTest(length=length):
                self.assertEqual(crc16(data), bitwise_crc(data))

    def test_exact_frame_bytes(self):
        self.assertEqual(encode_frame(b"123456789"), b"\xff\xaa\x09\x00123456789\x91\x6f\xfe")

    def test_fragmented_every_byte(self):
        parser = FrameParser()
        got = []
        for byte in encode_frame(b"one") + encode_frame(b"\xff\xaa\xfe\x00"):
            got += parser.feed(bytes([byte]))
        self.assertEqual(got, [b"one", b"\xff\xaa\xfe\x00"])

    def test_concatenated_and_empty_payload(self):
        self.assertEqual(FrameParser().feed(encode_frame(b"a") + encode_frame(b"") + encode_frame(b"b")), [b"a", b"", b"b"])

    def test_pending_bytes_exposes_incomplete_frame_read_only(self):
        parser = FrameParser()
        frame = encode_frame(b'{"code":1}')
        self.assertEqual(parser.pending_bytes, 0)
        self.assertEqual(parser.feed(frame[:-1]), [])
        self.assertEqual(parser.pending_bytes, len(frame) - 1)
        with self.assertRaises(AttributeError):
            parser.pending_bytes = 0
        self.assertEqual(parser.feed(frame[-1:]), [b'{"code":1}'])
        self.assertEqual(parser.pending_bytes, 0)

    def test_lone_ff_survives_noise(self):
        parser = FrameParser()
        self.assertEqual(parser.feed(b"noise\xff"), [])
        self.assertEqual(parser.feed(encode_frame(b"ok")[1:]), [b"ok"])

    def test_ff_ff_aa_resync(self):
        parser = FrameParser()
        self.assertEqual(parser.feed(b"\xff"), [])
        self.assertEqual(parser.feed(encode_frame(b"ok")), [b"ok"])

    def test_payload_limit_and_boundary(self):
        frame = encode_frame(b"a" * 4096)
        self.assertEqual(FrameParser().feed(frame), [b"a" * 4096])
        with self.assertRaises(ProtocolError):
            encode_frame(b"a" * 4097)

    def test_bad_crc_poisoned(self):
        parser = FrameParser()
        bad = bytearray(encode_frame(b"payload"))
        bad[-2] ^= 1
        with self.assertRaisesRegex(ProtocolError, "CRC"):
            parser.feed(bad)
        with self.assertRaisesRegex(ProtocolError, "already failed"):
            parser.feed(encode_frame(b"later"))

    def test_bad_tail_no_resync(self):
        bad = encode_frame(b"first")[:-1] + b"\x00" + encode_frame(b"later")
        with self.assertRaisesRegex(ProtocolError, "terminator"):
            FrameParser().feed(bad)

    def test_announced_length_rejected_early(self):
        with self.assertRaisesRegex(ProtocolError, "length"):
            FrameParser().feed(b"\xff\xaa\x01\x10")

    def test_declared_frame_exceeds_custom_buffer(self):
        with self.assertRaisesRegex(ProtocolError, "buffer"):
            FrameParser(max_buffer=8).feed(b"\xff\xaa\x02\x00")

    def test_buffer_overflow(self):
        with self.assertRaisesRegex(ProtocolError, "buffer"):
            FrameParser().feed(b"n" * 8193)

    def test_accumulated_noise_limit(self):
        parser = FrameParser(max_payload=16, max_buffer=32)
        parser.feed(b"n" * 32)
        with self.assertRaisesRegex(ProtocolError, "noise"):
            parser.feed(b"n")

    def test_valid_frame_resets_noise_budget(self):
        parser = FrameParser(max_payload=16, max_buffer=32)
        parser.feed(b"n" * 32)
        self.assertEqual(parser.feed(encode_frame(b"ok")), [b"ok"])
        self.assertEqual(parser.feed(b"n" * 32), [])

    def test_request_is_complete_frame(self):
        payload, = FrameParser().feed(encode_request(7, "get_info"))
        self.assertEqual(json.loads(payload), {"id": 7, "method": "get_info"})
        payload, = FrameParser().feed(encode_request(8, "iap_upgrade", {"size": 64}))
        self.assertEqual(json.loads(payload)["params"], {"size": 64})

    def test_invalid_request(self):
        cases = [(True, "get_info", None), (-1, "get_info", None), (2**31, "get_info", None),
                 (1, "", None), (1, "get_info", []), (1, "get_info", {"a": float("nan")})]
        for args in cases:
            with self.subTest(args=args), self.assertRaises(ProtocolError):
                encode_request(*args)

    def test_success_response(self):
        response = {"id": 7, "code": 0, "msg": "success", "result": {"firmware": "V1.3.863"}}
        self.assertEqual(decode_response(json.dumps(response).encode(), 7), response)

    def test_success_message_variants(self):
        for msg in ("success", "ok", ""):
            self.assertEqual(decode_response(json.dumps({"id": 1, "code": 0, "msg": msg}).encode(), 1)["code"], 0)

    def test_stale_id_ignored(self):
        self.assertIsNone(decode_response(b'{"id":8,"code":12,"msg":"failure"}', 7))

    def test_nonzero_code(self):
        with self.assertRaises(RPCError):
            decode_response(b'{"id":1,"code":2,"msg":"success"}', 1)

    def test_non_success_message(self):
        with self.assertRaises(RPCError):
            decode_response(b'{"id":1,"code":0,"msg":"upgrade rejected"}', 1)

    def test_explicit_error(self):
        with self.assertRaises(RPCError):
            decode_response(b'{"id":1,"code":0,"error":{"reason":"bad CRC"}}', 1)

    def test_invalid_code_types(self):
        for code in (False, True, None, "0", 0.0):
            with self.subTest(code=code), self.assertRaises(ProtocolError):
                decode_response(json.dumps({"id": 1, "code": code}).encode(), 1)
        with self.assertRaises(ProtocolError):
            decode_response(b'{"id":1}', 1)

    def test_invalid_id_types(self):
        for rid in (False, True, None, "1", 1.0):
            with self.subTest(rid=rid), self.assertRaises(ProtocolError):
                decode_response(json.dumps({"id": rid, "code": 0}).encode(), 1)

    def test_malformed_json(self):
        for payload in (b'[]', b'null', b'not json', b'\xff', b'{"id":1,"code":0}x',
                        b'{"id":1,"id":2,"code":0}', b'{"id":1,"code":0,"result":{"a":1,"a":2}}',
                        b'{"id":1,"code":0,"result":NaN}'):
            with self.subTest(payload=payload), self.assertRaises(ProtocolError):
                decode_response(payload, 1)

    def test_json_object_accepts_whitespace_without_assigning_ack_meaning(self):
        self.assertEqual(decode_json_object(b' \r\n {"code":1,"msg":"failed"} \t'),
                         {"code": 1, "msg": "failed"})

    def test_json_duplicate_id_or_code_never_last_wins(self):
        for payload in (b'{"id":1,"id":2,"code":0}',
                        b'{"id":1,"code":2,"code":0}',
                        b'{"result":{"code":2,"code":0}}'):
            with self.subTest(payload=payload), self.assertRaises(ProtocolError):
                decode_json_object(payload)
        with self.assertRaises(ProtocolError):
            decode_response(b'{"id":1,"code":2,"code":0}', 1)

    def test_json_nonfinite_numbers_refused_at_any_depth(self):
        for constant in (b'NaN', b'Infinity', b'-Infinity', b'1e999', b'-1e999'):
            for prefix, suffix in ((b'{"value":', b'}'), (b'{"values":[', b']}')):
                with self.subTest(constant=constant, prefix=prefix), self.assertRaises(ProtocolError):
                    decode_json_object(prefix + constant + suffix)

    def test_json_top_level_nonobjects_and_invalid_utf8_refused(self):
        for payload in (b'[]', b'"success"', b'0', b'-1', b'true', b'false', b'null',
                        b'{"msg":"\xff"}', b'{} trailing'):
            with self.subTest(payload=payload), self.assertRaises(ProtocolError):
                decode_json_object(payload)

    def test_chunk_exact_wire(self):
        payload, = FrameParser().feed(encode_chunk(STAGING_BASE, b"abc"))
        self.assertEqual(payload, b"\x55" + struct.pack("<I", STAGING_BASE) + b"\x03abc")

    def test_chunk_first_and_last_boundaries(self):
        self.assertEqual(MAX_IMAGE_BYTES, 114688)
        for addr, data in ((STAGING_BASE, b"a"), (STAGING_END - 64, b"a" * 64), (STAGING_END - 1, b"z")):
            self.assertTrue(encode_chunk(addr, data))

    def test_chunk_invalid_boundaries(self):
        cases = [(STAGING_BASE - 1, b"a"), (STAGING_END, b"a"),
                 (STAGING_END - 1, b"aa"), (STAGING_BASE, b""),
                 (STAGING_BASE, b"a" * 65), (True, b"a"), (-1, b"a"), (2**32, b"a")]
        for args in cases:
            with self.subTest(args=args), self.assertRaises(ProtocolError):
                encode_chunk(*args)

    def test_module_imports_are_offline_only(self):
        tree = ast.parse(Path(__file__).with_name("protocol.py").read_text())
        imports = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        self.assertEqual(imports, {"json", "struct"})
        from_imports = {(node.module, tuple(alias.name for alias in node.names))
                        for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        self.assertEqual(from_imports, {("__future__", ("annotations",))})


if __name__ == "__main__":
    unittest.main(verbosity=2)
