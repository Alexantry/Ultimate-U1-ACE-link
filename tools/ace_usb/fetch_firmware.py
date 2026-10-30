#!/usr/bin/env python3
"""Explicitly fetch one pinned upstream image; no serial or printer access.

SPDX-License-Identifier: GPL-3.0-only
Copyright (C) 2026 Ultimate U1-ACE link contributors
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from urllib.request import Request, urlopen

from ace_iap import MAX_IMAGE_BYTES, verify_image

ROOT = Path(__file__).resolve().parent
PINNED = {
    'opencubic-gen1': (
        'https://github.com/Jupsi/OpenCubic/releases/download/v1.0.2/ACE_V1.3.863_20260716.bin',
        '95e0b6ddb1e77d624d127ac91d9b3e21caf58adc5e1598faf2be3feacf9b4048', 113720),
    'stock-gen1-863': (
        'https://raw.githubusercontent.com/Jupsi/OpenCubic/6a97e86eda2872e8f8046cefd9470d89906d9a36/originalFirmware/ACE_V1.3.863_20250518.bin',
        '3f3676ba357749b3d0367922cb7f6b0dedc9b3d104c1c29e719ac3e563f5eb63', 105652),
}


def fetch_image(image_id, root=ROOT, opener=urlopen):
    root = Path(root).resolve()
    manifest_path = root / 'images.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    record = manifest['images'][image_id]
    url, digest, size = PINNED[image_id]
    if (record.get('download_url'), record.get('sha256'), record.get('size')) != (url, digest, size):
        raise ValueError('Manifest differs from the pinned upstream image')
    destination = (root / record['file']).resolve()
    if destination.parent != root / 'firmware':
        raise ValueError('Image destination must be inside the local firmware directory')
    if destination.exists():
        verify_image(manifest_path, image_id)
        return destination
    request = Request(url, headers={'User-Agent': 'Ultimate-U1-ACE-link/0.1.0'})
    with opener(request, timeout=60) as response:
        data = response.read(MAX_IMAGE_BYTES + 1)
    if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
        raise ValueError('Downloaded image size or SHA256 differs from upstream pin; nothing saved')
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Verification precedes creation; never overwrite an existing recipient file.
    with destination.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    verify_image(manifest_path, image_id)
    return destination


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image_id', choices=tuple(PINNED))
    args = parser.parse_args(argv)
    try:
        path = fetch_image(args.image_id)
        print(json.dumps({'verified_file': str(path), 'serial_access': False}))
        return 0
    except Exception as exc:
        print(type(exc).__name__ + ': ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
