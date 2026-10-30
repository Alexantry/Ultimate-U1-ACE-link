# Third-party sources and licensing

**[Sharing and use: license audit](docs/licensing.md) · [中文许可核查](docs/licensing.zh-CN.md)**

The source package can be used, modified, and shared under GPLv3, with its conditions.
That statement does not license separately downloaded U1 or ACE firmware, proprietary keys, or third-party trademarks.

## Development with OpenAI Codex

This integration was developed with **OpenAI Codex**.
The user supplied requirements, made physical observations, and performed machine tests.
Codex wrote and integrated the project code, installation tools, and documentation.
Installation and use do not require Codex, a ChatGPT subscription, or an API key.
This statement does not change upstream authorship or license obligations.

Ultimate U1-ACE link is a modified integration, not an official Snapmaker or Anycubic release. The source package is distributed under **GNU GPL version 3**; see [LICENSE](LICENSE). New project contributions are also GPL-3.0-only. Existing copyright notices remain in the source files.

**Modification notice — 2026-10-30:** the payload ports SnapAce to the exact U1 `2.0.0-paxx12-24` core. This project adds transport guards, explicit-load policy, staged loading, NFC metadata synchronization, material retention, and optional forward take-up. These changes were made for Ultimate U1-ACE link and must not be attributed to the upstream authors. [SOURCES.json](SOURCES.json) records the source identities and byte hashes; [manifest.json](manifest.json) records the installation allowlist.

## Included source

| Component | Origin and attribution | License evidence | What is included |
| --- | --- | --- | --- |
| SnapAce integration | [BlackFrogKok/SnapAce](https://github.com/BlackFrogKok/SnapAce/tree/34a06e87bcd59ca3ebc845ed32a794627505437c), commit `34a06e87bcd59ca3ebc845ed32a794627505437c` | [GPLv3 LICENSE at that commit](https://github.com/BlackFrogKok/SnapAce/blob/34a06e87bcd59ca3ebc845ed32a794627505437c/LICENSE) | Adapted `ace.py`, integration changes in `filament_feed.py` and `extruder.py` |
| Snapmaker U1 Klipper | [Snapmaker/u1-klipper](https://github.com/Snapmaker/u1-klipper); also incorporates Klipper work by Kevin O'Connor and other contributors | [Official COPYING](https://github.com/Snapmaker/u1-klipper/blob/93cb12faebf6e74c51bbc5f0be66e95124af14c8/COPYING); original GPL notice retained in `extruder.py` | Exact-release core files adapted for the integration; two test-only source fixtures |
| Paxx12 extended firmware | [paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/tree/v2.0.0-paxx12-24), tag `v2.0.0-paxx12-24`, commit `417e6394f62366e010a3f76f8e567f67db770165` | [GPLv3 LICENSE](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/417e6394f62366e010a3f76f8e567f67db770165/LICENSE) and [published RFID patches](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/tree/417e6394f62366e010a3f76f8e567f67db770165/overlays/firmware-extended/13-patch-rfid/patches) | Baseline U1 core changes, including the detector being extended by this project |
| Gen1 USB/IAP protocol research | [Godless50/ACE-PRO-v1.-NFC-UID](https://github.com/Godless50/ACE-PRO-v1.-NFC-UID/tree/ec8f37bf9928e7814efaafe6aaa794c69f8216d1), commit `ec8f37bf9928e7814efaafe6aaa794c69f8216d1` | [GPLv3 LICENSE](https://github.com/Godless50/ACE-PRO-v1.-NFC-UID/blob/ec8f37bf9928e7814efaafe6aaa794c69f8216d1/LICENSE); [README distinguishes own source from third-party firmware](https://github.com/Godless50/ACE-PRO-v1.-NFC-UID/blob/ec8f37bf9928e7814efaafe6aaa794c69f8216d1/README.md#licence) | Optional rewritten/adapted `ace_iap.py` and `protocol.py`, with strict reply validation and failure-path tests; no upstream firmware patches or binaries |

The payload core baseline is extracted from the identified extended-firmware release. The official Snapmaker source revision above is license/provenance evidence, not a claim that every extracted file equals that revision. The baseline `extruder.py` does match official git blob `6978d8a1b33c4b767e0f0cd783a2b50b6ed115dd` exactly. Paxx12's published patches account for additional reader and metadata behavior. Full source files, rather than opaque binary patches, are provided for review and modification.

## External prerequisites, not relicensed here

- **Paxx12 extended firmware and SnapAce hardware setup:** install the exact supported U1 firmware and follow the original SnapAce wiring and configuration guidance. On U1 2.0.0, this project's migrated payload replaces the old upstream core-copy steps. Do not first overwrite the new core with older SnapAce `filament_feed.py` or `extruder.py`.
- **OpenCubic Gen1 firmware:** multi-brand NFC decoding on the ACE is supplied by [OpenCubic](https://github.com/Jupsi/OpenCubic), not by this host project's brand mapping. Its [README](https://github.com/Jupsi/OpenCubic/blob/6a97e86eda2872e8f8046cefd9470d89906d9a36/README.md#firmware-source) says firmware source is private and release binaries are supplied as-is. This package includes **no firmware images** and makes no GPL grant over those images. Optional downloads point to exact upstream files and verify their hashes. The separate upstream Qt flash tool is described as MIT; it is not copied into this repository.
- **Anycubic stock firmware:** the optional `V1.3.863` reference remains Anycubic's material. Its community-hosted download is identified as such; it is not a backup of any recipient's printer or ACE.
- **OpenRFID:** the U1's internal-reader option is a separate upstream component, not the ACE USB decoding path. This package does not bundle or replace its tag processors, keys, or user configuration. Existing credentials must remain private. Users needing proprietary-tag keys must obtain them independently.
- **Runtime dependencies:** Klipper, Moonraker, the U1 Python runtime, and pyserial are prerequisites from their respective projects. They are not bundled or automatically installed by the USB tooling.

## Preserved boundaries

The [unchanged Godless50 upstream notice](docs/licenses/Godless50-NOTICE.md) retains its source-versus-firmware distinction.
Its references to included binaries describe that upstream repository; those binaries are **not** in this package.
Source: [NOTICE.md at the recorded commit](https://github.com/Godless50/ACE-PRO-v1.-NFC-UID/blob/ec8f37bf9928e7814efaafe6aaa794c69f8216d1/NOTICE.md).

The U1 preparation wizard obtains the unchanged upstream image only when a user selects that step.
It does not rehost the image or assert a GPL grant over all original-vendor components inside it.
OpenCubic's published download/use instructions do not establish unrestricted rights to redistribute or sell its firmware binaries.

Only source payloads and synthetic offline tests are distributed. This repository excludes printer backups, personal filesystem paths, private network addresses, NFC keys, and hashes of private key files. It also excludes per-device write profiles, firmware binaries, and raw hardware logs. The shipped USB profile is a generic, write-disabled template; recipients create any reviewed device profile locally and never commit it.

The existing USB IAP and protocol modules retain the tested adapter's runtime logic. Packaging changes update attribution/comments, replace the old preparation profile with a generic locked template, and replace binary-dependent test inputs with synthetic images. The additional fetch helper only downloads explicitly selected, pinned upstream images; it does not open serial devices.

The optional draft-profile helper copies a fresh, supported probe into a private draft. It leaves writing and all maintenance checks disabled. Only the physically tested V1.3.856 / boot V1.0.1 upgrade route is accepted. It does not open hardware or authorize a transfer.

The guided ACE backend is new project source under GPLv3.
It uses the existing protocol tools to perform measured preflight checks and the explicitly confirmed, supported update transaction.
It obtains pinned binaries from their upstream locations when requested; those binaries and private transaction records remain outside the distributed source archive.
No additional firmware redistribution rights are asserted by this automation.
