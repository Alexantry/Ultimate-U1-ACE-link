# Ultimate U1-ACE link

[简体中文](README.zh-CN.md) · [Installation](docs/installation.md) · [Configuration](docs/configuration.md) · [Troubleshooting](docs/troubleshooting.md)

[Download v0.1.0 ZIP](https://github.com/Alexantry/Ultimate-U1-ACE-link/raw/refs/heads/main/downloads/Ultimate-U1-ACE-link-v0.1.0.zip) · [Archive SHA-256](https://github.com/Alexantry/Ultimate-U1-ACE-link/blob/main/downloads/SHA256SUMS)

Use an Anycubic ACE Pro Gen 1 with a Snapmaker U1 through USB.
This project extends SnapAce for U1 firmware 2.0, NFC material transfer, controlled filament transport, and material retention.

The current implementation is `port7-forward-takeup`.
It contains the integrated work from October 28–30, 2026.
The installer does not run a filament transport test.

## Install the prerequisites first

| Order | Project or component | Required preparation |
| --- | --- | --- |
| 1 | [SnapmakerU1-Extended-Firmware](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware) | Install the tested stable release, `v2.0.0-paxx12-24`. |
| 2 | U1 access | Enable Advanced Mode and Root Access. Confirm Wi-Fi and SSH access. |
| 3 | ACE Pro Gen 1 firmware | Use the tested `CV1.3.863` / OpenCubic `1.1.1` combination for the NFC path. |
| 4 | [SnapAce hardware connection](https://github.com/BlackFrogKok/SnapAce#pinout-and-wiring) | Prepare the USB cable and four PTFE paths. |
| 5 | Ultimate U1-ACE link | Install this compatible software port with [the installation guide](docs/installation.md). |

This project replaces the **software installation steps** in the original SnapAce instructions.
Do not copy the old SnapAce `filament_feed.py` or `extruder.py` over U1 firmware 2.0 files.
Use the upstream hardware guide for the cable arrangement.

The tested versions form one compatibility baseline.
A newer U1 release, ACE revision, or tag format needs separate validation.
See [NFC prerequisites](docs/nfc.md) for ACE firmware and private-key boundaries.

## Current behavior

The following distances apply to the tested reference configuration.
The standard installation template disables the forward take-up movement until you calibrate your PTFE paths.

| Event | Result |
| --- | --- |
| Insert filament into an empty ACE inlet | ACE takes a short bite and reads NFC. It does not automatically send 1250 mm. |
| Select Load on the U1, with a known insertion position | Send 1150 mm at speed 200, then speed 50 until the head sensor detects filament. |
| Select Unload on the U1 | Complete the hotend unload, then retract 1250 mm at speed 80. |
| Complete the reference unload | Send 300 mm toward the U1 at speed 50 to reduce loose filament. |
| Select Load after that unload, without reinsertion | Send 850 mm at speed 200, then speed 50 until the head sensor detects filament. |
| Load after restart or an uncertain movement | Use speed 50 throughout. |
| Unload while filament remains in the ACE inlet | Retain the material brand, type, subtype, and color. |
| Remove filament from the ACE inlet | Clear that slot's material data after a confirmed empty state. |

Speeds are protocol requests in mm/s.
ACE firmware can limit the actual transport speed.
The head sensor determines the normal load endpoint.
The total 2500 mm load limit is a fault limit, not the normal travel distance.

## What changed

- U1 2.0 compatibility replaces the old feeder integration.
- One operation owns ACE transport across both U1 feeder modules.
- Insertion performs NFC recognition without automatic full loading.
- Loading waits for NFC before the separate movement timeout starts.
- Two-stage loading uses a short slow approach to the head sensor.
- Successful unloading records the forward movement for the next fast distance.
- Disconnects, cancellations, and uncertain positions remove permission for the fast stage.
- NFC transfer preserves recognized brands instead of forcing every brand to Generic.
- Material data remains available during normal load and unload cycles.
- The optional forward take-up movement reduces loose filament after retraction.

## Limits

The forward take-up movement pulls filament toward the U1.
It does not drive the spool roller independently.
It uses a fixed configured distance, without tension detection.
The implementation does not modify ACE gear ratios or ACE motor firmware.

Brand conversion does not prove support for every physical NFC tag.
Tag recognition depends on ACE firmware, tag format, antenna position, and any required authentication material.
This repository contains no NFC keys.
Users must obtain their own keys independently.

The U1 **External** detection setting disables its internal reader path.
It prevents conflicting material updates in this setup.
It does not define the NFC capabilities of ACE firmware.
See [NFC behavior](docs/nfc.md).

## Validation

The integrated candidate passed **194 offline tests** before installation on the test printer.
One complete **slot 4** unload and reload cycle passed the recorded physical check.
The user confirmed that the unload result was satisfactory.
The recorded reload used 850/200, then sensor-controlled speed 50, and reached `load_finish`.
Material data remained unchanged throughout that recorded cycle.

This result does not establish physical validation for all four slots or all spool types.
See [validation details](docs/validation.md) for the evidence boundary.

## Guides

- [Installation](docs/installation.md): prerequisites, Windows transfer, checks, and installation.
- [Configuration](docs/configuration.md): parameters and PTFE calibration.
- [NFC](docs/nfc.md): firmware responsibilities, material transfer, and key privacy.
- [Update and rollback](docs/update-and-rollback.md): backups and version changes.
- [Troubleshooting](docs/troubleshooting.md): connection, recognition, and transport faults.
- [Validation](docs/validation.md): software tests and physical checks.
- [Glossary](docs/glossary.md): consistent technical terms.

## Attribution

| Project | Contribution |
| --- | --- |
| [BlackFrogKok/SnapAce](https://github.com/BlackFrogKok/SnapAce) | The original ACE-to-U1 integration, serial transport, and hardware connection guide. |
| [paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware) | The tested U1 firmware environment, configuration interface, and external material interface. |
| [Snapmaker/U1-klipper](https://github.com/Snapmaker/U1-klipper) | The U1 Klipper implementation and native filament workflow. |
| [Jupsi/OpenCubic](https://github.com/Jupsi/OpenCubic) | The ACE firmware prerequisite for the tested external NFC path. |
| [OpenRFID](https://github.com/suchmememanyskill/OpenRFID) | The upstream tag-format ecosystem and material naming reference. |
| [Godless50/ACE-PRO-v1.-NFC-UID](https://github.com/Godless50/ACE-PRO-v1.-NFC-UID) | The Gen 1 USB/IAP protocol research used by the corrected optional updater. |

See [THIRD_PARTY.md](THIRD_PARTY.md) and [SOURCES.json](SOURCES.json) for pinned sources, changes, and distribution terms.
The host software license does not grant rights to third-party firmware or proprietary NFC keys.

The English procedures use short sentences and consistent terms, informed by [ASD-STE100 Issue 9](https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf).
This project does not claim certification or formal STE compliance.
