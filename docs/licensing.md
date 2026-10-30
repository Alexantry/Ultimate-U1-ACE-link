# Licensing and redistribution

[简体中文](licensing.zh-CN.md)

Reviewed on **2026-10-30** against the identified upstream sources and this project's public source package.
This review records available license evidence; it is not a guarantee for every jurisdiction or third-party asset.

> [!IMPORTANT]
> **The source package is GPLv3; external firmware images are not covered by that statement.**
> You can use, modify, and share the covered source, including commercially, subject to GPLv3 requirements.
> Public availability of a firmware download does not establish permission to redistribute or relicense that image.

## What you can do with this source package

The repository includes the full [GNU GPL version 3](../LICENSE).
The included source has no additional noncommercial-only or no-sharing restriction.
GPLv3 permits charging for copies; it does not require all use to be noncommercial.
Private use does not require publication of private modifications.
Distribution of modified source creates obligations under the license.

When sharing the source or a modified version:

1. Keep existing copyright, license, and warranty notices.
2. Include the GPLv3 license text.
3. Identify your changes with a prominent notice and relevant date.
4. License the covered combined work consistently with GPLv3.
5. Provide the corresponding source required for what you distribute.
6. Include required build and installation scripts with that source.
7. Preserve the recipients' GPL rights without additional restrictions.
8. Keep private credentials and printer backups outside the shared package.

GPLv3 sections 4 and 5 govern source distribution.
Section 6 adds requirements when distributing object code or binaries.
Applicable installation information can also be required under section 6.
The present package supplies readable source and its build/install tools, not compiled printer firmware.
See the [upstream GPLv3 text](https://github.com/BlackFrogKok/SnapAce/blob/34a06e87bcd59ca3ebc845ed32a794627505437c/LICENSE).

## Included code and its license evidence

| Source | Evidence checked | Material in this project |
| --- | --- | --- |
| SnapAce, commit `34a06e87bcd59ca3ebc845ed32a794627505437c` | [GPLv3 LICENSE](https://github.com/BlackFrogKok/SnapAce/blob/34a06e87bcd59ca3ebc845ed32a794627505437c/LICENSE) | Adapted ACE control and integration changes. |
| Snapmaker U1 Klipper | [GPLv3 COPYING at `93cb12fa`](https://github.com/Snapmaker/u1-klipper/blob/93cb12faebf6e74c51bbc5f0be66e95124af14c8/COPYING) | U1 core modules and test-only fixtures from the identified firmware baseline. |
| Paxx12 U1 Extended Firmware, commit `417e6394f62366e010a3f76f8e567f67db770165` | [GPLv3 LICENSE](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/417e6394f62366e010a3f76f8e567f67db770165/LICENSE) | Firmware-baseline changes and published RFID patches used by the host integration. |
| ACE Gen 1 USB/IAP research, commit `ec8f37bf9928e7814efaafe6aaa794c69f8216d1` | [GPLv3 LICENSE](https://github.com/Godless50/ACE-PRO-v1.-NFC-UID/blob/ec8f37bf9928e7814efaafe6aaa794c69f8216d1/LICENSE) and [licensing-scope NOTICE](https://github.com/Godless50/ACE-PRO-v1.-NFC-UID/blob/ec8f37bf9928e7814efaafe6aaa794c69f8216d1/NOTICE.md) | Adapted USB/IAP protocol and updater source, with synthetic offline tests. |
| New Ultimate U1-ACE link contributions | [Project LICENSE](../LICENSE) and [modification notice](../THIRD_PARTY.md) | Host changes, installer, Windows tools, tests, diagrams, and documentation. |

The checked upstream GPL files contain the same GPLv3 text.
No separate commercial-use prohibition was found for these included source components.
The source identities and public-file hashes are recorded in [SOURCES.json](../SOURCES.json).
The installation allowlist is recorded separately in [manifest.json](../manifest.json).

The U1 core baseline comes from the exact extended-firmware release.
The cited official Klipper revision establishes license provenance; it does not assert byte equality for every extracted file.
The original Kevin O'Connor copyright and GPL notice remain in `payload/extruder.py`.
The print-task fixture retains its GPL notice.
The protocol fixture identifies its origin, extraction date, and limited test-only contents.
The package's modification notice identifies this project's changes and their date.

## OpenRFID: separate runtime component and references

OpenRFID publishes [GPLv3](https://github.com/suchmememanyskill/OpenRFID/blob/f2608fa1a2d28abce80c7f1a8fbf7aa184f22bbd/LICENSE).
The current license was checked on 2026-10-30 and matched that fixed license revision.

This package does not bundle OpenRFID tag decoders, authentication implementations, or its user configuration.
The reviewed payload and fixtures contain no OpenRFID decoder imports or implementation files.
Comparison with the extracted upstream reference found no substantial identical implementation block in those reviewed files.
That comparison supports the recorded scope; it does not prove every historical source relationship.

OpenRFID is an existing U1 component and a documentation/reference source.
The ACE path receives decoded information from ACE firmware instead.
The [NFC guide](nfc.md) describes ACE recognition and its support limits. It contains no key-entry procedure or proprietary keys.
Future copied OpenRFID code would need its applicable notices, attribution, and license treatment.

## OpenCubic: firmware and Qt flash tool differ

The pinned [OpenCubic README](https://github.com/Jupsi/OpenCubic/blob/6a97e86eda2872e8f8046cefd9470d89906d9a36/README.md#firmware-source) states that firmware source remains private.
Its license section identifies the Qt flash tool as MIT and describes firmware binaries as provided as-is.
A standalone license file was not present in the checked repository root or flash-tool directory.
The MIT description for the tool must not be applied to the firmware.

| Material | Available permission evidence | Project treatment |
| --- | --- | --- |
| OpenCubic ACE firmware | Official instructions invite users to download and flash it. No clear blanket redistribution or commercial firmware grant was found. | Not bundled, modified, or relicensed here. |
| OpenCubic Qt flash tool | Upstream README labels the tool MIT. | No Qt flash-tool source or executable is included here. |
| Our USB tool | Adapted from the separately GPLv3-licensed ACE research source. | Included as source under the project's GPLv3 terms. |

The official [flashing guide](https://github.com/Jupsi/OpenCubic/blob/6a97e86eda2872e8f8046cefd9470d89906d9a36/docs/how-to-flash.md) supports the intended download-and-use workflow.
It does not supply an unrestricted firmware redistribution, modification, or commercial-use license.
The research project's [NOTICE](https://github.com/Godless50/ACE-PRO-v1.-NFC-UID/blob/ec8f37bf9928e7814efaafe6aaa794c69f8216d1/NOTICE.md) explicitly excludes third-party firmware images from its GPL grant.

The optional downloader fetches a user-selected image directly from the identified upstream location.
It verifies public size and hash values; those checks establish integrity, not copyright permission.
The downloader's own source license does not license its downloaded output.
No separate automation permission was found in the reviewed firmware terms.
Do not infer additional rights from an accessible URL, a successful download, or an as-is disclaimer.
Obtain suitable permission before redistributing or commercially bundling those firmware images.

## U1 and Anycubic complete firmware images

Paxx12 licenses its main project under GPLv3 and directs users to individual dependencies for their licenses.
Its [license statement](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/417e6394f62366e010a3f76f8e567f67db770165/README.md#license) does not establish one license for every original-firmware component.
A complete U1 image includes original manufacturer components and other dependencies.
This review does not establish redistribution rights for every component in that image.

The Anycubic stock image remains third-party manufacturer material.
A community repository's copy does not create a new license for that image.
The [ACE research NOTICE](https://github.com/Godless50/ACE-PRO-v1.-NFC-UID/blob/ec8f37bf9928e7814efaafe6aaa794c69f8216d1/NOTICE.md) expressly makes that distinction.
Neither firmware family is covered by this source package's GPL grant.

A helper can direct users to a pinned upstream download and verify its hash.
That workflow keeps the upstream asset separate; it is not a claim of unrestricted firmware rights.
A modified first-boot U1 image would require a separate component-license and distribution review.

## Retained archive findings

The review inspected the locally retained `v0.1.0` and `v0.1.1` archives.
Both contained the project LICENSE and THIRD_PARTY notice.
Neither contained firmware `.bin` files, NFC key files, OpenRFID user configuration, or the OpenCubic Qt flash tool.
The source hashes listed in SOURCES.json matched the reviewed files.

These findings concern those inspected archives.
A later package must be checked again; the earlier result does not automatically cover added files.
Keep [the retained-version policy](install-options.md) separate from any new package's audit result.

## Private data and attribution

Private NFC keys and hashes of private key files must not be published.
Public source-file and firmware checksums serve integrity checks; they do not contain a private-key-file audit record.
Printer backups, device-specific write profiles, credentials, and raw private diagnostics remain excluded from public distribution.

OpenAI Codex assisted this project's development.
That fact does not replace upstream copyright, license conditions, or required attribution.
The project does not claim to be an official Snapmaker or Anycubic release.

This audit found a compatible GPLv3 basis for the identified included source.
It does not guarantee all legal rights for external firmware, trademarks, private keys, or future additions.
