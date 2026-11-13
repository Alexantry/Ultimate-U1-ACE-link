# Prepare the U1 firmware

[简体中文](u1-preparation.zh-CN.md) · [Guided installation](quick-start.md) · **[Manual source installation](installation.md)**

The wizard downloads the exact U1 extended firmware (the **original upstream file**), verifies it, and copies it to a USB drive. You then update on the U1 screen and enable Advanced Mode and Root Access.
This stage does not flash the ACE. The [ACE firmware stage](ace-wizard.md) follows in the same wizard.

> [!IMPORTANT]
> **You must confirm the first firmware update on the U1 screen.**
> **You must also enable Advanced Mode and Root Access before remote installation.**

## What you need

- A Windows 10 or Windows 11 computer with internet access, and the extracted project package.
- A removable USB drive that already uses **FAT32**, with at least 300 MB free. The wizard does not format disks.
- An idle, cold U1: printing and all filament operations finished, heating and ACE drying off, nozzles and bed below 50 °C.
- For a first installation: unload all four heads with the normal printer controls, remove the filament from all four ACE inlets, then let the heaters cool again. An update of this project does not require empty inlets.
- Your own copy of any custom configuration, made before the firmware update. The project's later backup does not protect it.

If the U1 already runs the exact supported firmware, select menu **1. U1 is ready** instead. Do not replace a customized or newer firmware merely to pass an installation check.

## Guided steps

1. Extract the complete project ZIP. Double-click **START-HERE.cmd**, select your language, then select **2. Prepare U1 firmware USB**.
2. Insert the FAT32 USB drive into the computer. Select it from the list, check its letter, label, and capacity, then confirm.
3. Wait for download, SHA-256 verification, file copy, and destination verification. Then use Windows **Eject**.
4. Insert the drive into the U1. Select **Settings → About → Firmware Version → Local Update** on the U1 screen.
5. Select `U1_extended_2.0.0-paxx12-24_upgrade.bin`. Confirm the update. Wait for the update and restart to finish. Keep power connected.
6. Open **Settings → Maintenance → Advanced Mode**. Enable it and complete the requested restart.
7. Open **Settings → Maintenance → Root Access**. Read the notice, scroll to **Agree**, and select **Open**.
8. Check Wi-Fi. Reconnect if necessary. Read the current printer IP address.
9. Continue in the same computer wizard. It asks for the printer address and SSH password.

The wizard does not overwrite a file that has the same name but different content. Inspect that file yourself before another attempt. If no suitable drive appears, use a FAT32 removable drive. Do not change the program to force another disk.

If the U1 update fails, keep the displayed error text and use [Snapmaker's firmware-update recovery instructions](https://wiki.snapmaker.com/en/snapmaker_u1/troubleshooting/firmware-update-failed). Do not try random firmware files. Host integration rollback does not reverse a U1 firmware update.

## Exact firmware identity

| Field | Required value |
| --- | --- |
| Upstream release | `v2.0.0-paxx12-24` |
| Filename | `U1_extended_2.0.0-paxx12-24_upgrade.bin` |
| Size | `253893376` bytes |
| SHA-256 | `42dcf59e06ef0f6fab20745883322f24ddd3c1a09da07449b356dd9dab943070` |

[Upstream release and checksum](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/releases/tag/v2.0.0-paxx12-24) · [Exact upstream download](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/releases/download/v2.0.0-paxx12-24/U1_extended_2.0.0-paxx12-24_upgrade.bin)

The checksum identifies the upstream asset. It is not a Snapmaker signature. The project archive contains no U1 firmware binary; see [third-party licensing](../THIRD_PARTY.md).

## Manual alternative

Download that exact file from the release page yourself. Check its SHA-256 before use:

1. In File Explorer, hold **Shift** and right-click the downloaded `.bin` file. Select **Copy as path**.
2. Press **Windows + R**, type `powershell`, and press Enter.
3. Copy the following line into the window and press Enter. At `Paste the file path`, paste the copied path. Press Enter again.

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath ((Read-Host "Paste the file path").Trim('"'))
```

Compare the complete `Hash` value with the SHA-256 in the table above. Uppercase and lowercase letters are equivalent. **If the values differ, do not use the file.** Download it again from the exact upstream link.
Copy the verified file to the root of the FAT32 USB drive and do guided steps 4–8. Then continue with **[manual source installation](installation.md)**.

Sources: [v24 installation](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/v2.0.0-paxx12-24/docs/install.md), [Advanced Mode requirement](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/v2.0.0-paxx12-24/docs/firmware_config.md), and [SSH access](https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/blob/v2.0.0-paxx12-24/docs/ssh_access.md).
