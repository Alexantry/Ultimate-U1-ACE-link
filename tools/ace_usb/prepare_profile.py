#!/usr/bin/env python3
"""Create a write-disabled draft from a fresh probe. No hardware/network access.

SPDX-License-Identifier: GPL-3.0-only
Copyright (C) 2026 Ultimate U1-ACE link contributors
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sys

SOURCE_FIRMWARE = 'V1.3.856'
BOOT_FIRMWARE = 'V1.0.1'
TARGET_SHA256 = '95e0b6ddb1e77d624d127ac91d9b3e21caf58adc5e1598faf2be3feacf9b4048'
CHECKS = ('idle_state_verified', 'heaters_and_dryer_off_verified',
          'klipper_stopped_and_port_released', 'source_version_reviewed',
          'rollback_path_reviewed')


def build_draft(probe_path, now=None):
    raw = Path(probe_path).read_bytes()
    if len(raw) > 65536:
        raise ValueError('Probe is unexpectedly large')
    probe = json.loads(raw)
    if probe.get('schema') != 1 or probe.get('kind') != 'ACE_GEN1_READ_ONLY_PROBE':
        raise ValueError('Expected an ACE Gen1 read-only probe')
    stamp = dt.datetime.fromisoformat(probe['captured_at_utc'])
    current = now or dt.datetime.now(dt.timezone.utc)
    if stamp.tzinfo is None or not 0 <= (current - stamp).total_seconds() <= 1800:
        raise ValueError('Probe must be timezone-aware and no more than 30 minutes old')
    info = probe.get('snapshot', {}).get('info', {})
    if info.get('model') != 'Anycubic Color Engine Pro' or info.get('slots') != 4:
        raise ValueError('Unsupported device model or slot count')
    if (info.get('firmware'), info.get('boot_firmware')) != (SOURCE_FIRMWARE, BOOT_FIRMWARE):
        raise ValueError('Only the tested V1.3.856 / boot V1.0.1 upgrade route is supported; do not alter probe values')
    identity = probe.get('usb_identity')
    if not isinstance(identity, dict) or not all(identity.get(k) for k in ('sysfs_port', 'vid', 'pid')):
        raise ValueError('Probe has no complete USB physical identity')
    device = probe.get('device')
    if not isinstance(device, str) or not device.startswith('/dev/'):
        raise ValueError('Probe has no Linux serial device path')
    device_id = info.get('id')
    if isinstance(device_id, bool) or not isinstance(device_id, (str, int)):
        raise ValueError('Probe has no exact device identity')
    status = probe.get('snapshot', {}).get('status', {})
    slots = status.get('slots', [])
    if (status.get('status') != 'ready' or len(slots) != 4
            or any(not isinstance(s, dict) or type(s.get('index')) is not int for s in slots)
            or [s['index'] for s in slots] != [0, 1, 2, 3]
            or any(s.get('status') not in ('ready', 'empty') for s in slots)):
        raise ValueError('Probe does not show four indexed idle slots')
    dryer = status.get('dryer_status', {})
    if dryer.get('status') != 'stop' or dryer.get('target_temp') != 0:
        raise ValueError('Probe does not show a stopped dryer')
    return {
        'schema': 1, 'write_enabled': False, 'device': device,
        'source_firmware': info['firmware'], 'boot_firmware': info['boot_firmware'],
        'device_info_id': device_id, 'usb_identity': identity,
        'reviewed_at_utc': None, 'probe_sha256': hashlib.sha256(raw).hexdigest(),
        'image_sha256': TARGET_SHA256, 'checks': {name: False for name in CHECKS},
        'pending': [
            'Draft only. Verify current U1/ACE idle state, zero heater targets, temperatures below 50 C, and stopped drying.',
            'Verify exclusive ownership of the selected serial device.',
            'Inspect both pinned images. Stock V1.3.863 rollback is prepared but has not been physically tested by this project.',
            'Record a fresh UTC review timestamp only after completing the documented review.',
            'Do not commit this device-specific draft or the probe. All checks and writing remain disabled.',
        ],
    }


def write_draft(output, draft):
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
        json.dump(draft, stream, indent=2)
        stream.write('\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        draft = build_draft(args.probe)
        write_draft(args.output, draft)
        print(json.dumps({'draft_saved': args.output, 'write_enabled': False,
                          'all_checks_false': True, 'hardware_access': False}))
        return 0
    except Exception as exc:
        print(type(exc).__name__ + ': ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
