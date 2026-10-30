# Ultimate U1-ACE link

Connect an Anycubic ACE Pro Gen 1 to a Snapmaker U1.
Load from the U1 screen, keep recognized material data, and reduce loose filament with optional forward take-up.

**Built with OpenAI Codex. You do not need Codex, programming knowledge, or an API key to install this project.**

[简体中文](README.zh-CN.md) · [Download v0.1.1 ZIP](https://github.com/Alexantry/Ultimate-U1-ACE-link/raw/refs/heads/main/downloads/Ultimate-U1-ACE-link-v0.1.1.zip) · [SHA-256](downloads/SHA256SUMS)

> [!CAUTION]
> **Do not copy old SnapAce `filament_feed.py` or `extruder.py` onto U1 firmware 2.0.**
>
> **This project replaces the original SnapAce software installation steps.**
> Use the upstream **hardware connection guide** for the cable arrangement.

## Choose your installation path

| I want prompts | I want to inspect each command |
| --- | --- |
| **[Bilingual guided installation](docs/quick-start.md)** | **[Manual source installation](docs/installation.md)** |
| Double-click `START-HERE.cmd`, then choose a language. | Review the source, then enter the documented commands. |

The **[original v0.1.0 package](docs/install-options.md#retained-v010)** remains available unchanged.

## Start with four steps

1. Complete the [machine preparation](docs/installation.md#1-prepare-the-prerequisite-projects).
2. Download the ZIP above.
3. Extract all files.
4. Double-click **START-HERE.cmd** and select **English** or **中文**.

The launcher enters commands and transfers files for you.
Open **START-HERE.html** or **START-HERE.en.html** for the illustrated offline guide.

Prefer to inspect the commands and source first?
The [manual source procedure](docs/installation.md) remains available and does not run the Windows launcher.
It still runs the open-source `installer.py` on the printer.
[Installation choices and the retained v0.1.0 package](docs/install-options.md) explain both paths.

![Download, extract, and start](docs/images/first-steps.en.svg)

## What is automatic?

| The installer does this | You supply or prepare this |
| --- | --- |
| Check firmware and device state | Install the supported prerequisite firmware and connect the hardware. |
| Find the ACE interface or preserve the existing one | Enter the printer address and SSH password. |
| Set **Filament Detection → External** | Review the physical distances for a new installation. |
| Save backups and configure persistence | Keep the machine idle and cold. |
| Install modules and verify the result | Check one slot after installation. |

The actual reader option is **External**, not a setting named extended.
The installer also disables the internal reader path and verifies the configuration.
Existing ACE parameters remain unchanged by default.
New installations start with forward take-up disabled.

## Prerequisites

> [!IMPORTANT]
> **Complete these prerequisites before installation.**
> **ACE Pro Gen 1 and the exact U1 version below are the tested baseline.**

| Component | Tested baseline |
| --- | --- |
| U1 extended firmware | `2.0.0-paxx12-24` |
| U1 access | Advanced Mode enabled; Root Access Open |
| ACE hardware | ACE Pro Gen 1, correct USB connection, four PTFE paths |
| ACE NFC firmware | `CV1.3.863` / OpenCubic `1.1.1` |

U1 firmware installation, ACE firmware changes, and cable preparation are separate prerequisite tasks.

## How it works

- Insertion performs a short bite and NFC recognition, then waits.
- The U1 Load button starts fast feed followed by a slower sensor-controlled approach.
- Unload retracts the configured distance while retaining filament in ACE.
- Material data stays until the ACE inlet becomes empty.
- Optional forward take-up reduces loose filament after retraction.

Reference values are 1150 mm at speed 200, then speed 50; unload is 1250 mm at speed 80.
The tested take-up value is 300 mm at speed 50.
**These distances are examples for the tested tube arrangement, not universal settings.**
Forward take-up has no tension feedback and does not independently drive the spool roller.
See [configuration](docs/configuration.md) and [validation limits](docs/validation.md).

## Project sources and development

| Project | Foundation |
| --- | --- |
| [SnapAce](https://github.com/BlackFrogKok/SnapAce) | ACE control and the original hardware integration. |
| [U1 Extended Firmware](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware) | The U1 firmware environment and configuration interface. |
| [Snapmaker U1 Klipper](https://github.com/Snapmaker/u1-klipper) | The native printer and filament workflow. |
| [OpenCubic](https://github.com/Jupsi/OpenCubic) | The tested ACE NFC firmware. |
| [OpenRFID](https://github.com/suchmememanyskill/OpenRFID) | Tag-format and material naming references. |
| [ACE Gen 1 protocol research](https://github.com/Godless50/ACE-PRO-v1.-NFC-UID) | The foundation for the separate optional USB updater. |

The user supplied requirements and performed physical tests.
**OpenAI Codex wrote and integrated this project's code, installation tools, and documentation.**
Upstream authors retain their credits and licenses. See [THIRD_PARTY.md](THIRD_PARTY.md) and [SOURCES.json](SOURCES.json).

This repository contains no NFC keys. Users must obtain required proprietary keys independently.
English procedures follow ASD-STE100 writing principles; this is not a certification claim.

[Beginner guide](docs/quick-start.md) · [NFC](docs/nfc.md) · [Update and rollback](docs/update-and-rollback.md) · [Troubleshooting](docs/troubleshooting.md)
