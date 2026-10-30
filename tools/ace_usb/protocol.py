"""Pure ACE Pro Gen1 wire primitives. No device, serial, or network access.

SPDX-License-Identifier: GPL-3.0-only
Public packaging: 2026-10-30; runtime logic unchanged from the tested adapter.

encode_request() and encode_chunk() return complete frames. FrameParser returns
payloads. Its failed state is permanent: create a new parser only after deciding
how to recover the transport. A parsed frame is not an IAP success indication.
"""

from __future__ import annotations

import json
import struct

MAX_PAYLOAD = 4096
STAGING_BASE = 0x08024000
MAX_IMAGE_BYTES = 114688
STAGING_END = STAGING_BASE + MAX_IMAGE_BYTES


class ProtocolError(ValueError):
    """Malformed data or an unsupported wire shape; fail closed."""


class RPCError(ProtocolError):
    """A matching, validly framed RPC response reports failure."""


def _bytes(value, label):
    if not isinstance(value, (bytes, bytearray, memoryview)):
        raise ProtocolError("%s must be bytes-like" % label)
    return bytes(value)


def _integer(value, label, minimum=None, maximum=None):
    if type(value) is not int:
        raise ProtocolError("%s must be an integer, not bool" % label)
    if minimum is not None and value < minimum:
        raise ProtocolError("%s is below its allowed range" % label)
    if maximum is not None and value > maximum:
        raise ProtocolError("%s exceeds its allowed range" % label)
    return value


def crc16(data: bytes) -> int:
    """CRC-16/MCRF4XX: reflected 0x8408, init FFFF, xorout 0000."""
    crc = 0xFFFF
    for byte in _bytes(data, "data"):
        # Byte-at-a-time algebraic implementation, independently tested against
        # the bitwise recurrence and its published standard check value.
        value = byte ^ (crc & 0xFF)
        value ^= (value & 0x0F) << 4
        crc = (((value << 8) | (crc >> 8)) ^ (value >> 4) ^ (value << 3)) & 0xFFFF
    return crc


def encode_frame(payload: bytes) -> bytes:
    payload = _bytes(payload, "payload")
    if len(payload) > MAX_PAYLOAD:
        raise ProtocolError("payload exceeds 4096 bytes")
    return b"\xff\xaa" + struct.pack("<H", len(payload)) + payload + struct.pack("<H", crc16(payload)) + b"\xfe"


class FrameParser:
    """Bounded incremental parser with strict candidate-frame validation.

    Noise before a header may be discarded, up to max_buffer bytes between
    valid frames. A trailing lone FF is retained across calls. Each feed's
    pending data must fit max_buffer; callers should use bounded read chunks.
    A bad length, CRC, or terminator poisons the parser instead of resyncing.
    """

    def __init__(self, max_payload=4096, max_buffer=8192):
        self.max_payload = _integer(max_payload, "max_payload", 0, 65535)
        self.max_buffer = _integer(max_buffer, "max_buffer", 7)
        self._buffer = bytearray()
        self._noise = 0
        self._failed = None

    @property
    def pending_bytes(self):
        """Bytes awaiting a complete frame; inspect before an IAP commit."""
        return len(self._buffer)

    def _fail(self, message):
        self._failed = message
        self._buffer.clear()
        raise ProtocolError(message)

    def _discard_noise(self, count):
        self._noise += count
        if self._noise > self.max_buffer:
            self._fail("noise limit exceeded")
        del self._buffer[:count]

    def feed(self, data: bytes) -> list[bytes]:
        if self._failed is not None:
            raise ProtocolError("parser already failed: " + self._failed)
        data = _bytes(data, "data")
        if len(self._buffer) + len(data) > self.max_buffer:
            self._fail("buffer limit exceeded")
        self._buffer.extend(data)
        result = []
        while self._buffer:
            start = self._buffer.find(b"\xff\xaa")
            if start < 0:
                keep = 1 if self._buffer[-1] == 0xFF else 0
                self._discard_noise(len(self._buffer) - keep)
                break
            if start:
                self._discard_noise(start)
            if len(self._buffer) < 4:
                break
            length = struct.unpack_from("<H", self._buffer, 2)[0]
            if length > self.max_payload:
                self._fail("declared payload length exceeds limit")
            total = length + 7
            if total > self.max_buffer:
                self._fail("declared frame exceeds buffer limit")
            if len(self._buffer) < total:
                break
            if self._buffer[total - 1] != 0xFE:
                self._fail("invalid frame terminator")
            payload = bytes(self._buffer[4:4 + length])
            expected = struct.unpack_from("<H", self._buffer, 4 + length)[0]
            if crc16(payload) != expected:
                self._fail("invalid frame CRC")
            del self._buffer[:total]
            self._noise = 0
            result.append(payload)
        return result


def encode_request(id, method, params=None) -> bytes:
    """Encode a full JSON-RPC frame. Does not select or execute a method."""
    _integer(id, "request id", 0, 0x7FFFFFFF)
    if not isinstance(method, str) or not method or "\x00" in method:
        raise ProtocolError("method must be a nonempty string without NUL")
    request = {"id": id, "method": method}
    if params is not None:
        if not isinstance(params, dict):
            raise ProtocolError("params must be an object")
        request["params"] = params
    try:
        payload = json.dumps(request, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ProtocolError("request is not valid JSON") from exc
    return encode_frame(payload)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolError("duplicate JSON key: " + key)
        result[key] = value
    return result


def _invalid_constant(value):
    raise ProtocolError("nonfinite JSON number: " + value)


def _finite_float(value):
    number = float(value)
    if not -float("inf") < number < float("inf"):
        raise ProtocolError("JSON floating-point overflow")
    return number


def decode_json_object(payload: bytes) -> dict:
    """Strict UTF-8 JSON object, independent of RPC/unknown IAP reply meaning."""
    payload = _bytes(payload, "payload")
    if len(payload) > MAX_PAYLOAD:
        raise ProtocolError("JSON payload exceeds 4096 bytes")
    try:
        response = json.loads(payload.decode("utf-8"), object_pairs_hook=_unique_object,
                              parse_constant=_invalid_constant, parse_float=_finite_float)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ProtocolError("malformed JSON object: " + str(exc)) from exc
    if not isinstance(response, dict):
        raise ProtocolError("JSON value must be an object")
    return response


def decode_response(payload: bytes, request_id) -> dict | None:
    """Return a successful matching response; None for another integer ID.

    Missing/boolean/non-integer success codes are malformed. Explicit failure
    messages cannot override code 0. Unknown response shapes require review.
    """
    _integer(request_id, "request id", 0, 0x7FFFFFFF)
    response = decode_json_object(payload)
    response_id = _integer(response.get("id"), "response id", 0, 0x7FFFFFFF)
    if response_id != request_id:
        return None
    code = _integer(response.get("code"), "response code")
    if code != 0:
        raise RPCError("RPC failure code %d" % code)
    if response.get("error") is not None:
        raise RPCError("RPC returned an explicit error")
    if "msg" in response:
        message = response["msg"]
        if not isinstance(message, str):
            raise ProtocolError("response msg must be a string")
        if message.strip().lower() not in ("", "success", "ok"):
            raise RPCError("RPC returned a non-success message: " + message)
    return response


def encode_chunk(address, data: bytes) -> bytes:
    """Encode one Gen1 binary IAP frame; no device or write operations."""
    _integer(address, "chunk address", STAGING_BASE, STAGING_END - 1)
    data = _bytes(data, "chunk data")
    if not 1 <= len(data) <= 64:
        raise ProtocolError("chunk data length must be 1..64")
    if address + len(data) > STAGING_END:
        raise ProtocolError("chunk crosses staging boundary")
    return encode_frame(b"\x55" + struct.pack("<I", address) + bytes([len(data)]) + data)
