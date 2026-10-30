#!/usr/bin/env python3
"""Experimental ACE Pro Gen1 IAP preparation tool. Default operations are offline.

SPDX-License-Identifier: GPL-3.0-only
Protocol derived from Godless50/ACE-PRO-v1.-NFC-UID ace_flash.py, pinned in ../../SOURCES.json.
Public packaging: 2026-10-30; runtime logic unchanged from the tested adapter.
No service control, motion, RFID rescan, or automatic firmware retry is implemented.
Serial access requires an explicit probe/flash subcommand. Shipped profile blocks flash.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import sys
import time

from protocol import (ProtocolError, RPCError, FrameParser, crc16,
                      encode_request, decode_response, decode_json_object, encode_chunk)

ROOT = Path(__file__).resolve().parent
MAX_IMAGE_BYTES = 114688
APP_BASE = 0x08008000
STAGING_BASE = 0x08024000


class PreparationError(Exception):
    pass


class LinkTimeout(PreparationError):
    pass


class IndeterminateFlash(PreparationError):
    """Some device state may have changed; never automatically retry."""


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_new_json(path, data):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


class Audit:
    def __init__(self, path):
        self.stream = Path(path).open('x', encoding='utf-8')

    def event(self, name, **fields):
        self.stream.write(json.dumps({'time_utc': utc_now(), 'event': name, **fields}) + '\n')
        self.stream.flush()
        os.fsync(self.stream.fileno())

    def close(self):
        self.stream.close()


def verify_image(manifest_path, image_id):
    manifest_path = Path(manifest_path).resolve()
    manifest = read_json(manifest_path)
    if manifest.get('schema') != 1 or manifest.get('max_image_bytes') != MAX_IMAGE_BYTES:
        raise PreparationError('Unsupported manifest schema or image limit')
    if manifest.get('target_generation') != 'ACE Pro Gen1 USB JSON':
        raise PreparationError('Manifest is not ACE Pro Gen1')
    record = manifest.get('images', {}).get(image_id)
    if not isinstance(record, dict):
        raise PreparationError('Unknown image id')
    path = (manifest_path.parent / record['file']).resolve()
    if not path.is_relative_to(manifest_path.parent):
        raise PreparationError('Image path escapes preparation package')
    size = path.stat().st_size
    if not 512 <= size <= MAX_IMAGE_BYTES or size != record.get('size'):
        raise PreparationError('Image size rejected before reading or serial access')
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != record.get('sha256'):
        raise PreparationError('Image SHA256 mismatch')
    if crc16(data) != record.get('crc16_mcrf4xx'):
        raise PreparationError('Image CRC16 mismatch')
    sp, reset = struct.unpack_from('<II', data)
    if not 0x20000000 <= sp <= 0x20020000 or sp % 8:
        raise PreparationError('Invalid ARM initial stack pointer')
    if not reset & 1 or not APP_BASE <= reset - 1 < APP_BASE + len(data):
        raise PreparationError('Invalid Thumb application reset vector')
    if not isinstance(record.get('expected_runtime_version'), str):
        raise PreparationError('Missing exact expected runtime version')
    if record.get('announced_version') != '1.3.863':
        raise PreparationError('Only the reviewed .863 image family is prepared')
    return data, record


def validate_write_profile(profile, record, device):
    # The shipped false gate is deliberate: each recipient must inspect their
    # own source firmware, bootloader and maintenance state before enabling writes.
    if profile.get('write_enabled') is not True:
        raise PreparationError('Writing locked: live probe and compatibility review are pending')
    required = ('idle_state_verified', 'heaters_and_dryer_off_verified',
                'klipper_stopped_and_port_released', 'source_version_reviewed',
                'rollback_path_reviewed')
    if any(profile.get('checks', {}).get(key) is not True for key in required):
        raise PreparationError('Incomplete live maintenance checks')
    if profile.get('device') != device:
        raise PreparationError('Profile device does not match requested serial path')
    if profile.get('image_sha256') != record['sha256']:
        raise PreparationError('Profile does not authorize this exact image')
    for key in ('source_firmware', 'boot_firmware', 'reviewed_at_utc', 'probe_sha256'):
        if not isinstance(profile.get(key), str) or not profile[key]:
            raise PreparationError('Missing live profile field: ' + key)
    stamp = dt.datetime.fromisoformat(profile['reviewed_at_utc'])
    if stamp.tzinfo is None:
        raise PreparationError('Review timestamp requires timezone')
    age = (dt.datetime.now(dt.timezone.utc) - stamp).total_seconds()
    if not 0 <= age <= 1800:
        raise PreparationError('Live review must be within the previous 30 minutes')
    if not isinstance(profile.get('device_info_id'), (str, int)) or isinstance(profile['device_info_id'], bool):
        raise PreparationError('Missing exact device info id')
    identity = profile.get('usb_identity')
    if not isinstance(identity, dict) or not all(identity.get(k) for k in ('sysfs_port', 'vid', 'pid')):
        raise PreparationError('Missing reviewed USB physical port identity')


def validate_probe_evidence(profile, probe_path):
    raw = Path(probe_path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != profile['probe_sha256']:
        raise PreparationError('Probe record digest mismatch')
    probe = json.loads(raw)
    if probe.get('device') != profile['device'] or probe.get('kind') != 'ACE_GEN1_READ_ONLY_PROBE':
        raise PreparationError('Probe device/kind mismatch')
    if probe.get('usb_identity') != profile['usb_identity']:
        raise PreparationError('Probe USB identity mismatch')
    info = probe.get('snapshot', {}).get('info', {})
    for field, key in [('firmware', 'source_firmware'), ('boot_firmware', 'boot_firmware'), ('id', 'device_info_id')]:
        if info.get(field) != profile[key]:
            raise PreparationError('Probe evidence mismatch: ' + field)
    if probe.get('snapshot', {}).get('status', {}).get('status') != 'ready':
        raise PreparationError('Probe does not establish normal application ready state')
    return probe


def serial_identity(device):
    target = Path(device).resolve(strict=True).stat()
    if not stat.S_ISCHR(target.st_mode):
        raise PreparationError('Serial target is not a character device')
    node = Path('/sys/dev/char/%d:%d/device' % (os.major(target.st_rdev), os.minor(target.st_rdev))).resolve(strict=True)
    for parent in (node, *node.parents):
        if (parent / 'idVendor').is_file() and (parent / 'idProduct').is_file():
            serial_file = parent / 'serial'
            return {'sysfs_port': str(parent), 'vid': (parent / 'idVendor').read_text().strip(),
                    'pid': (parent / 'idProduct').read_text().strip(),
                    'serial': serial_file.read_text().strip() if serial_file.exists() else None}
    raise PreparationError('Could not bind serial path to a USB physical port')


def require_unused_device(device):
    if not sys.platform.startswith('linux') or not hasattr(os, 'geteuid') or os.geteuid() != 0:
        raise PreparationError('Live operations require the Linux printer root context')
    resolved = Path(device).resolve(strict=True)
    target = resolved.stat()
    if not stat.S_ISCHR(target.st_mode):
        raise PreparationError('Serial target is not a character device')
    owners = set()
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid():
            continue
        try:
            fds = list((proc / 'fd').iterdir())
        except FileNotFoundError:
            continue
        except PermissionError as exc:
            raise PreparationError('Cannot inspect serial ownership: ' + proc.name) from exc
        for fd in fds:
            try:
                s = fd.stat()
                if stat.S_ISCHR(s.st_mode) and s.st_rdev == target.st_rdev:
                    owners.add(int(proc.name))
            except FileNotFoundError:
                pass
            except PermissionError as exc:
                raise PreparationError('Cannot inspect fd ownership') from exc
    if owners:
        raise PreparationError('Serial device is already open by PID(s): ' + ','.join(map(str, sorted(owners))))


class SerialSession:
    def __init__(self, device, audit, expected_identity=None):
        self.device, self.audit = device, audit
        self.serial = None
        self.request_id = 0
        self.parser = FrameParser()
        self.identity = expected_identity
        self._iap_started = False
        self._chunks_started = False
        self.reopen()

    def reopen(self):
        self.close()
        require_unused_device(self.device)
        identity = serial_identity(self.device)
        if self.identity is not None and identity != self.identity:
            raise PreparationError('USB device/physical port differs from the reviewed device')
        self.identity = identity
        import serial  # Never imported by inspect/plan/tests or a locked flash.
        self.serial = serial.Serial(self.device, 115200, timeout=0.1,
                                    write_timeout=2.0, rtscts=True, exclusive=True)
        try:
            require_unused_device(self.device)  # excludes this process, closes race window
            if serial_identity(self.device) != self.identity:
                raise PreparationError('USB identity changed while opening serial')
        except Exception:
            self.close()
            raise
        self.parser = FrameParser()
        self.audit.event('serial_open', device=self.device)

    def close(self):
        if self.serial is not None:
            self.serial.close()
            self.serial = None

    def _write(self, frame):
        count = self.serial.write(frame)
        if count != len(frame):
            raise IndeterminateFlash('Partial serial write; no retry performed')

    def _record_iap_reply(self, payload, context):
        # The bounded, validated frame payload is kept locally before semantic
        # validation, including rejected replies. Never log outgoing chunks.
        self.audit.event('iap_reply_received', context=context,
                         payload_bytes=len(payload), payload_hex=payload.hex())

    def rpc(self, method, params=None, timeout=1.5):
        if method not in ('get_info', 'iap_version', 'get_status', 'iap_upgrade', 'iap_upgrade_finish'):
            raise PreparationError('RPC method outside the reviewed maintenance allowlist')
        self.request_id += 1
        rid = self.request_id
        if method in ('iap_upgrade', 'iap_upgrade_finish'):
            # Retain this state across reconnect: a delayed transfer error must
            # not disappear as a stale ID during post-reboot verification.
            self._iap_started = True
        self._write(encode_request(rid, method, params))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            matched = None
            for payload in self.parser.feed(self.serial.read(4096)):
                response = None
                if getattr(self, '_iap_started', False):
                    self._record_iap_reply(payload, method)
                    decoded = decode_json_object(payload)
                    if (method != 'iap_upgrade' and getattr(self, '_chunks_started', False)
                            and is_chunk_write_success(decoded)):
                        # Gen1 uses id0 for write notifications, with no address.
                        # This is not the matching RPC/finish acknowledgment.
                        continue
                    if method == 'iap_upgrade_finish' and is_finish_success(decoded, rid):
                        response = decoded
                    # With one exclusive serial owner and one outstanding RPC,
                    # an error of unknown/stale ID during IAP is indeterminate,
                    # not safe to ignore. Ordinary read-only probes keep normal
                    # unmatched-ID filtering.
                    if response is None:
                        success_reply(decoded, 'IAP/late transfer response')
                if response is None:
                    response = decode_response(payload, rid)
                if response is not None:
                    if matched is not None:
                        raise ProtocolError('Duplicate matching RPC response in one read batch')
                    matched = response
            # FrameParser.feed consumes a whole batch. Returning inside its
            # loop would silently discard every frame after a matching reply,
            # including an explicit error in the same USB read.
            if matched is not None:
                return matched
        raise LinkTimeout('No validated matching response for ' + method)

    def send_chunk(self, address, data):
        self._write(encode_chunk(address, data))
        self._chunks_started = True
        self.drain_transfer_replies()

    def drain_transfer_replies(self, duration=0.0, clock=time.monotonic, sleep=time.sleep):
        # Per-chunk acknowledgement semantics are undocumented. Validate framing
        # of any replies, fail on explicit JSON error, but never claim receipt ACK.
        deadline = clock() + duration
        while True:
            count = self.serial.in_waiting
            if count > 8192:
                raise ProtocolError('Unbounded device reply backlog')
            if count:
                for payload in self.parser.feed(self.serial.read(min(count, 4096))):
                    self._record_iap_reply(payload, 'transfer')
                    stripped = payload.lstrip()
                    if stripped[:1] in [bytes([c]) for c in b'{["-0123456789tfn']:
                        decoded = decode_json_object(payload)
                        if not (getattr(self, '_chunks_started', False)
                                and is_chunk_write_success(decoded)):
                            success_reply(decoded, 'transfer response')
                    self.audit.event('chunk_reply_observed', payload_bytes=len(payload),
                                     meaning='not treated as an individual receipt acknowledgement')
            if duration == 0.0 or clock() >= deadline:
                if duration > 0.0 and self.parser.pending_bytes:
                    raise IndeterminateFlash('Incomplete transfer response before commit; finish not sent')
                return
            sleep(0.005)


def is_chunk_write_success(response):
    # Exact positive notification demonstrated in both reviewed .863 images.
    # There is no per-chunk address/sequence in this response; do not invent one.
    return (isinstance(response, dict) and type(response.get('id')) is int
            and response['id'] == 0 and type(response.get('code')) is int
            and response['code'] == 0 and response.get('msg') == 'write_success'
            and response.get('error') is None and response.get('result') == {})


def is_finish_success(response, request_id):
    # State3 full-image CRC/boot-marker success; accepted only for the exact
    # outstanding finish RPC, never start, transfer, or ordinary read-only RPCs.
    return (isinstance(response, dict) and type(response.get('id')) is int
            and response['id'] == request_id and type(response.get('code')) is int
            and response['code'] == 0 and response.get('msg') == 'Upgrade_success'
            and response.get('error') is None and response.get('result') == {})


def success_reply(response, method):
    if not isinstance(response, dict) or type(response.get('code')) is not int or response['code'] != 0:
        raise RPCError(method + ' not successful')
    if response.get('error') is not None:
        raise RPCError(method + ' contains an error object')
    msg = response.get('msg', '')
    if not isinstance(msg, str) or msg.strip().lower() not in ('', 'ok', 'success'):
        raise RPCError(method + ' contains an unsupported or negative message')
    return response


def result_object(response, method):
    success_reply(response, method)
    result = response.get('result')
    if not isinstance(result, dict):
        raise ProtocolError(method + ' missing result object')
    return result


def ready_state(status):
    if not isinstance(status, dict) or status.get('status') != 'ready':
        return False
    slots = status.get('slots')
    if not isinstance(slots, list) or len(slots) != 4 or any(not isinstance(s, dict) for s in slots):
        return False
    if any(type(s.get('index')) is not int for s in slots) or [s['index'] for s in slots] != [0, 1, 2, 3]:
        return False
    dryer = status.get('dryer_status')
    return isinstance(dryer, dict) and dryer.get('status') == 'stop' and dryer.get('target_temp') == 0


def snapshot(session):
    info = result_object(session.rpc('get_info'), 'get_info')
    version = success_reply(session.rpc('iap_version'), 'iap_version')
    status = result_object(session.rpc('get_status'), 'get_status')
    if info.get('model') != 'Anycubic Color Engine Pro' or info.get('slots') != 4:
        raise PreparationError('Device identity is not the prepared Gen1 four-slot model')
    return {'info': info, 'iap_version_response': version, 'status': status}


def check_live_source(observed, profile, image):
    info, status = observed['info'], observed['status']
    expected = {'firmware': profile['source_firmware'], 'boot_firmware': profile['boot_firmware'],
                'id': profile['device_info_id']}
    if any(info.get(key) != value for key, value in expected.items()):
        raise PreparationError('Live identity/firmware differs from reviewed probe')
    if info.get('firmware') == image['expected_runtime_version']:
        raise PreparationError('Target version already running; cannot verify transition, refusing redundant flash')
    if not ready_state(status):
        raise PreparationError('ACE is not in indexed four-slot ready state with dryer off')


def verify_target(session, image, before, audit, timeout=45.0, clock=time.monotonic, sleep=time.sleep):
    deadline = clock() + timeout
    consecutive = 0
    last_reason = 'No response'
    while clock() < deadline:
        try:
            info = result_object(session.rpc('get_info', timeout=1.0), 'get_info')
            status = result_object(session.rpc('get_status', timeout=1.0), 'get_status')
            identity_ok = (info.get('id') == before['info'].get('id') and
                           info.get('model') == before['info'].get('model') and info.get('slots') == 4 and
                           info.get('boot_firmware') == before['info'].get('boot_firmware'))
            ready = ready_state(status)
            changed = info.get('firmware') == image['expected_runtime_version']
            if identity_ok and ready and changed:
                consecutive += 1
                if consecutive >= 2:
                    audit.event('runtime_verified', firmware=info['firmware'], consecutive=consecutive)
                    return {'outcome': 'VERSION_CHANGED_AND_READY', 'info': info, 'status': status,
                            'flash_readback_verified': False, 'nfc_and_motion_tested': False}
            else:
                consecutive = 0
                last_reason = 'Observed version/state: ' + str(info.get('firmware')) + '/' + str(status.get('status'))
        except (RPCError, ProtocolError):
            raise  # An explicit device error/corrupt frame is not an ordinary reboot timeout.
        except Exception as exc:
            consecutive = 0
            last_reason = type(exc).__name__
            try:
                session.reopen()
            except Exception:
                pass
        sleep(0.25)
    raise IndeterminateFlash('Target runtime not verified: ' + last_reason + '; no retry or rollback performed')


def flash_once(session, data, image, profile, audit, sleep=time.sleep,
               verifier=verify_target):
    before = snapshot(session)
    check_live_source(before, profile, image)
    audit.event('source_verified', firmware=before['info']['firmware'], boot=before['info']['boot_firmware'])
    audit.event('iap_upgrade_request', bytes=len(data), crc16=crc16(data))
    # No automatic retry: even a timeout can mean the device entered IAP.
    response = success_reply(session.rpc('iap_upgrade', {'size': len(data), 'crc': crc16(data),
                                'version': image['announced_version']}, timeout=2.0), 'iap_upgrade')
    audit.event('iap_upgrade_acknowledged', response=response)
    for offset in range(0, len(data), 64):
        try:
            session.send_chunk(STAGING_BASE + offset, data[offset:offset+64])
        except Exception:
            audit.event('transfer_stopped', last_fully_completed_host_offset=offset,
                        failed_chunk_offset=offset, device_receipt_unknown=True)
            raise
        if offset % (64*256) == 0:
            audit.event('data_progress', sent=min(offset+64, len(data)), total=len(data))
        sleep(0.01)
    audit.event('data_sent', bytes=len(data), note='transmission is not proof of installation')
    sleep(0.3)
    session.drain_transfer_replies(duration=0.25)
    audit.event('iap_finish_request')
    try:
        response = session.rpc('iap_upgrade_finish', {}, timeout=1.5)
        # SerialSession verifies the special finish response against its own
        # request ID before returning. Other session implementations still need
        # strict success validation here; no generic message allowlist changes.
        if not (getattr(session, '_iap_started', False)
                and is_finish_success(response, session.request_id)):
            success_reply(response, 'iap_upgrade_finish')
        audit.event('iap_finish_acknowledged', response=response)
    except (RPCError, ProtocolError):
        raise
    except Exception as exc:
        audit.event('iap_finish_ack_missing', error=type(exc).__name__,
                    outcome='unknown until runtime verification')
    return verifier(session, image, before, audit)


def main(argv=None, session_factory=SerialSession):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('inspect', 'plan', 'flash'):
        p = sub.add_parser(name)
        p.add_argument('--manifest', default=str(ROOT / 'images.json'))
        p.add_argument('--image-id', default='opencubic-gen1')
        if name in ('plan', 'flash'):
            p.add_argument('--profile', default=str(ROOT / 'device-profile.json'))
        if name == 'flash':
            p.add_argument('--device', required=True)
            p.add_argument('--probe', required=True)
            p.add_argument('--log', required=True)
            p.add_argument('--result', required=True)
    probe = sub.add_parser('probe', help='LIVE read-only RPC; only after print complete and serial release')
    probe.add_argument('--device', required=True)
    probe.add_argument('--output', required=True)
    probe.add_argument('--log', required=True)
    args = parser.parse_args(argv)
    session = audit = None
    try:
        if args.command != 'probe':
            data, record = verify_image(args.manifest, args.image_id)
            summary = {'image_id': args.image_id, 'size': len(data), 'sha256': record['sha256'],
                       'crc16_mcrf4xx': hex(crc16(data)), 'hardware_access': False}
            if args.command == 'inspect':
                print(json.dumps(summary, indent=2))
                return 0
            profile = read_json(args.profile)
            if args.command == 'plan':
                summary.update(write_enabled=profile.get('write_enabled') is True,
                               pending=profile.get('pending', []), serial_port_opened=False)
                print(json.dumps(summary, indent=2))
                return 0
            validate_write_profile(profile, record, args.device)
            validate_probe_evidence(profile, args.probe)
        result_path = Path(args.output if args.command == 'probe' else args.result)
        if result_path.exists():
            raise PreparationError('Refusing to overwrite an existing evidence/result file')
        audit = Audit(args.log)
        audit.event('command', command=args.command)
        session = session_factory(args.device, audit,
                                  expected_identity=profile['usb_identity'] if args.command == 'flash' else None)
        if args.command == 'probe':
            result = {'schema': 1, 'kind': 'ACE_GEN1_READ_ONLY_PROBE', 'captured_at_utc': utc_now(),
                      'device': args.device, 'snapshot': snapshot(session),
                      'usb_identity': session.identity,
                      'warning': 'No firmware writes, but live serial ownership was required'}
        else:
            result = flash_once(session, data, record, profile, audit)
            result.update(image_sha256=record['sha256'], captured_at_utc=utc_now())
        write_new_json(result_path, result)
        print(json.dumps({'saved': str(result_path), 'outcome': result.get('outcome', 'PROBE_SAVED')}))
        return 0
    except Exception as exc:
        if audit:
            audit.event('failure', error=type(exc).__name__, message=str(exc),
                        no_automatic_retry=True, no_automatic_service_restart=True)
        print(type(exc).__name__ + ': ' + str(exc), file=sys.stderr)
        return 2
    finally:
        if session:
            session.close()
        if audit:
            audit.close()


if __name__ == '__main__':
    raise SystemExit(main())
