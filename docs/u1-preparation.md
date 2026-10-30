# Prepare U1 firmware in the guided workflow

[简体中文](u1-preparation.zh-CN.md) · [Guided installation](quick-start.md) · **[Manual source installation](installation.md)**

The preparation stage handles the U1 firmware file and shows the required screen actions.
It uses the **original upstream file**, not a new combined firmware image.
This U1 preparation stage does not flash ACE.
The same installer provides a separate [bilingual ACE firmware stage](ace-wizard.md) after U1 preparation.

> [!IMPORTANT]
> **The first firmware update still requires confirmation on the U1 screen.**
> **Advanced Mode and Root Access must also be enabled before remote installation.**
> These steps are part of the guide. They are not silently performed over an unopened connection.

## What you need

- A Windows 10 or Windows 11 computer with internet access.
- A removable USB drive that already uses **FAT32**, with at least 300 MB free.
- The extracted project package.
- An idle, cold U1. Finish printing and all filament operations first.
- All heating and ACE drying off. Let the nozzles and bed cool below 50 °C.
- A private copy of any existing custom configuration, before a firmware update.

For a first installation, unload all four heads with the normal printer controls.
Then remove filament from all four ACE inlets. Let the heaters cool again after unloading.
An update of this project's existing installation does not require empty inlets.

The host installer's later backup does not protect changes from an earlier firmware update.
If you already have the exact supported firmware, choose the existing-preparation path instead.
Do not replace a customized or newer firmware merely to pass an installation check.

## Guided steps

1. Extract the complete project ZIP.
2. Double-click **START-HERE.cmd**.
3. Select **English** or **中文**.
4. Select **2. Prepare U1 firmware USB**.
5. Insert your FAT32 USB drive into the computer.
6. Select its drive from the displayed list. Check its letter, label, and capacity.
7. Confirm that destination.
8. Wait for download, SHA-256 verification, file copy, and destination verification.
9. Use Windows **Eject** after the copy has finished.
10. Insert the drive into U1.
11. Select **Settings → About → Firmware Version → Local Update** on the U1 screen.
12. Select `U1_extended_2.0.0-paxx12-24_upgrade.bin`. Confirm the update.
13. Wait for the update and restart to finish. Keep power connected.
14. Open **Settings → Maintenance → Advanced Mode**. Enable it and complete the requested restart.
15. Open **Settings → Maintenance → Root Access**. Read the notice, scroll to **Agree**, and select **Open**.
16. Check Wi-Fi. Reconnect if necessary. Read the current printer IP address.
17. Continue in the same computer wizard when these checks are complete.

The next stage asks for the current printer address and SSH password.
It checks or prepares ACE firmware before host integration.
For a first installation, it also asks you to review the initial tube-distance settings.
It then runs compatibility checks, backup, installation, and verification.
See [the main guide](quick-start.md) for these steps and the final four-slot tests.

The computer's USB-file preparation does not contact or move the printer.
The screen-confirmed firmware update and the later ACE stage are separate device operations.

If the U1 update fails, keep the displayed error text.
Use [Snapmaker's firmware-update recovery instructions](https://wiki.snapmaker.com/en/snapmaker_u1/troubleshooting/firmware-update-failed).
Do not try random firmware files. Host integration rollback does not reverse a U1 firmware update.

## What the preparation stage will not change

It does not format disks, use a fixed internal disk, or overwrite a different file with the same name.
It copies only the verified firmware file to the selected USB root.
Other USB files stay in place.
If a conflicting file exists, inspect it yourself before another attempt.
If no suitable drive appears, use a FAT32 removable drive; do not change the program to force another disk.

The download is cached under the Windows user's Local AppData project folder.
A complete matching file can be reused. A partial or incorrect download is not offered for installation.
No downloaded script is executed.

## Exact firmware identity

| Field | Required value |
| --- | --- |
| Upstream release | `v2.0.0-paxx12-24` |
| Filename | `U1_extended_2.0.0-paxx12-24_upgrade.bin` |
| Size | `253893376` bytes |
| SHA-256 | `42dcf59e06ef0f6fab20745883322f24ddd3c1a09da07449b356dd9dab943070` |

[Upstream release and checksum](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/releases/tag/v2.0.0-paxx12-24) · [Exact upstream download](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/releases/download/v2.0.0-paxx12-24/U1_extended_2.0.0-paxx12-24_upgrade.bin)

The checksum identifies the upstream asset; it is not a Snapmaker signature.
The project archive contains no U1 firmware binary.
See [third-party licensing](../THIRD_PARTY.md).

## Manual alternative

You can download that exact file from the release page yourself.
Check its SHA-256 before use:

1. In File Explorer, hold **Shift** and right-click the downloaded `.bin` file.
2. Select **Copy as path**.
3. Press **Windows + R**, type `powershell`, and press Enter.
4. Copy the following line into the window. Press Enter.
5. At `Paste the file path`, paste the copied path. Press Enter again.

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath ((Read-Host "Paste the file path").Trim('"'))
```

Compare the complete `Hash` value with the SHA-256 in the table above. Uppercase and lowercase letters are equivalent.
**If the values differ, do not use the file.** Download it again from the exact upstream link.
Copy the verified file to the FAT32 USB root, then perform screen steps 11–16 above.
Continue with **[manual source installation](installation.md)** if you do not want to run the wizard.
The full Chinese [machine preparation guide](before-you-start.zh-CN.md) includes file-explorer and USB instructions.

## Why not enable everything inside a new firmware image?

An image containing this project and changed startup defaults would be a different firmware build.
It would need its own identity, source obligations, recovery checks, and hardware validation.
It would still need the first screen-confirmed update.
This release instead retains the exact tested upstream baseline and automates its preparation.

Sources: [v24 installation](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/v2.0.0-paxx12-24/docs/install.md), [Advanced Mode requirement](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/v2.0.0-paxx12-24/docs/firmware_config.md), and [SSH access](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/v2.0.0-paxx12-24/docs/ssh_access.md).
