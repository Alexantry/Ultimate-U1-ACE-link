# Licensing and redistribution

[简体中文](licensing.zh-CN.md)

Reviewed on **2026-10-30**. This page records the license evidence that was found. It is not legal advice.

> [!IMPORTANT]
> **The source package is GPLv3; external firmware images are not covered by that statement.**
> You can use, modify, and share the covered source, including commercially, subject to GPLv3 requirements.
> Public availability of a firmware download does not establish permission to redistribute or relicense that image.

## This project's code

The source in this repository is released under [GNU GPL version 3](../LICENSE).
It has no additional noncommercial-only or no-sharing restriction.
Private use does not require you to publish your modifications.

OpenAI Codex assisted this project's development. That does not replace upstream copyright, license conditions, or attribution.
This project is not an official Snapmaker or Anycubic release.

## Upstream components

Code included in this package:

| Source | License | Pinned evidence | Used here for |
| --- | --- | --- | --- |
| SnapAce, commit `34a06e87bcd59ca3ebc845ed32a794627505437c` | GPLv3 | [LICENSE](https://github.com/BlackFrogKok/SnapAce/blob/34a06e87bcd59ca3ebc845ed32a794627505437c/LICENSE) | Adapted ACE control and integration changes. |
| Snapmaker U1 Klipper, commit `93cb12fa` | GPLv3 | [COPYING](https://github.com/Snapmaker/u1-klipper/blob/93cb12faebf6e74c51bbc5f0be66e95124af14c8/COPYING) | U1 core modules and test-only fixtures. |
| Paxx12 U1 Extended Firmware, commit `417e6394f62366e010a3f76f8e567f67db770165` | GPLv3 | [LICENSE](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/417e6394f62366e010a3f76f8e567f67db770165/LICENSE) | Firmware-baseline changes and published RFID patches. |
| ACE Gen 1 USB/IAP research, commit `ec8f37bf9928e7814efaafe6aaa794c69f8216d1` | GPLv3 | [LICENSE](https://github.com/Godless50/ACE-PRO-v1.-NFC-UID/blob/ec8f37bf9928e7814efaafe6aaa794c69f8216d1/LICENSE) and [NOTICE](https://github.com/Godless50/ACE-PRO-v1.-NFC-UID/blob/ec8f37bf9928e7814efaafe6aaa794c69f8216d1/NOTICE.md) | Adapted USB/IAP protocol and updater source. |
| New Ultimate U1-ACE link contributions | GPLv3 | [LICENSE](../LICENSE) and [modification notice](../THIRD_PARTY.md) | Host changes, installer, Windows tools, tests, diagrams, and documentation. |

Related material that is **not** included in this package:

| Material | License evidence | Pinned evidence |
| --- | --- | --- |
| OpenRFID | GPLv3. No OpenRFID decoder, authentication code, or user configuration is bundled. | [LICENSE](https://github.com/suchmememanyskill/OpenRFID/blob/f2608fa1a2d28abce80c7f1a8fbf7aa184f22bbd/LICENSE) |
| OpenCubic ACE firmware | Source is private. Binaries are provided as-is for users to download and flash. No redistribution or commercial grant was found. | [README](https://github.com/Jupsi/OpenCubic/blob/6a97e86eda2872e8f8046cefd9470d89906d9a36/README.md#firmware-source) and [flashing guide](https://github.com/Jupsi/OpenCubic/blob/6a97e86eda2872e8f8046cefd9470d89906d9a36/docs/how-to-flash.md) |
| OpenCubic Qt flash tool | Labelled MIT in the upstream README. That label does not apply to the firmware. | Same README |
| Complete U1 extended firmware image | The main project is GPLv3. The image also contains manufacturer components and dependencies with their own licenses. | [License statement](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/417e6394f62366e010a3f76f8e567f67db770165/README.md#license) |
| Anycubic stock ACE firmware | Third-party manufacturer material. A community copy does not create a new license. | [ACE research NOTICE](https://github.com/Godless50/ACE-PRO-v1.-NFC-UID/blob/ec8f37bf9928e7814efaafe6aaa794c69f8216d1/NOTICE.md) |

[SOURCES.json](../SOURCES.json) records the source identities and public-file hashes. [manifest.json](../manifest.json) records the installation allowlist.

## What you may and may not redistribute

You may:

- Use, modify, and share this project's source under GPLv3, including commercially. GPLv3 permits charging for copies.

This project found no license grant that lets you do the following. Get permission from the rights holder first:

- Redistribute, modify, relicense, or commercially bundle the OpenCubic ACE firmware images.
- Redistribute the complete U1 firmware image or the Anycubic stock firmware as if this project's GPL grant covered them. It does not.
- Treat an accessible URL, a successful download, a matching hash, or an as-is disclaimer as a license.
- Apply the Qt flash tool's MIT label to the firmware.
- Publish private NFC keys or hashes of private key files.

The optional downloader fetches a firmware image that you select, directly from upstream, and verifies its size and hash.
Those checks prove integrity, not copyright permission. The downloader's own license does not license what it downloads.

This package bundles no firmware `.bin` files, NFC keys, OpenRFID configuration, or OpenCubic Qt flash tool.
The retained `v0.1.0` and `v0.1.1` archives were inspected and contained none of these. Check every later package again.

## What to keep when you redistribute

1. Keep existing copyright, license, and warranty notices.
2. Include the GPLv3 license text.
3. Identify your changes with a prominent notice and relevant date.
4. License the covered combined work consistently with GPLv3.
5. Provide the corresponding source for what you distribute, with its build and installation scripts.
6. Preserve the recipients' GPL rights without additional restrictions.
7. Keep credentials, printer backups, device-specific write profiles, and private diagnostics out of the shared package.

GPLv3 sections 4 and 5 govern source distribution. Section 6 adds requirements for object code or binaries.
