# Remove and restore

[简体中文](restore.zh-CN.md) · [Home](../README.md) · [Update and rollback](update-and-rollback.md)

This page tells you how to return the U1 and the ACE to a state without this project. The three tasks are independent. You can do only one.

| Task | What it does | Physical test |
| --- | --- | --- |
| **1. Remove this project** | The U1 uses the files shipped in the extended firmware again. It stays on `2.0.0-paxx12-24`. | Offline checks passed. No physical test. |
| **2. Return the ACE to vendor firmware** | The ACE goes from OpenCubic to Anycubic vendor `V1.3.863`. | **Never done on a device.** |
| **3. Return the U1 to official firmware** | The U1 goes to official Snapmaker `V2.0.0`. | No physical test. Uses the upstream method. |

For a complete return, use the order **2 → 1 → 3**. The ACE task needs this project on the U1. Removal needs the extended firmware.

> [!CAUTION]
> **Task 2 can damage the ACE. This project has no tested recovery method.**
> The vendor `V1.3.863` image is community-hosted. Only its size and SHA-256 are checked. It has no vendor signature, and it is not a backup of your ACE.
> Your ACE possibly left the factory with an earlier version, for example `V1.3.856`. This project cannot restore that version.

## With the wizard

1. End printing and filament operations. Turn off heating and drying. Wait until the nozzles and the bed are below 50°C.
2. Double-click **START-HERE.cmd**, select the language, then select **5. Restore**.
3. Select the task and follow the prompts.

| Restore menu | What the wizard does |
| --- | --- |
| **1. Remove this project** | Connects to the U1, runs a read-only check, and lists the files to restore and delete. It acts only after you confirm. |
| **2. Return ACE to vendor** | Asks three times: risk accepted, devices idle, final confirmation. Accepts only an ACE with `CV1.3.863` / boot `V1.0.1`. |
| **3. Official U1 firmware USB** | Downloads and verifies the official firmware and copies it to the FAT32 USB drive you select. It does not connect to the printer and does not format. |

## Task 1: remove this project

Removal does these things and changes no other file:

- Restores `filament_feed.py`, `filament_detect.py`, and `extruder.py` from the originals in the firmware image.
- Deletes `ace.py`, `ace.cfg`, and the `ace_vars.cfg` that `ace.cfg` declares.
- Sets filament detection from External back to the firmware default, Snapmaker. A different mode that you selected stays.
- Makes a backup first. If removal fails, it restores the state before removal.

After removal, the U1 cannot load or unload through the ACE. The ACE firmware and the U1 firmware version do not change.

**Before you start: all four print heads must be empty.** Use normal Unload on the U1 screen for each channel.

For the manual procedure, first connect and set `$PrinterTarget` and `$RemoteDir` as in [update and rollback, section 1](update-and-rollback.md#read-installation-status). `$RemoteDir` must contain the `installer.py` of this version.

Run the read-only check first. It changes no file:
```powershell
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 installer.py remove-check"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Removal check failed; do not remove' }
```

Expect `read_only: true` and `removable: true`, with the lists `restore_from_firmware` and `delete`.
If the message is `Unknown modified core` or `Firmware original is not a reviewed file`, stop. Do not delete or overwrite files to pass the check.

After you review the lists, run this once:
```powershell
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 installer.py remove"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Removal failed; preserve the error' }
```

Expect `removed: true` and a backup ID. `Automatic rollback VERIFIED` means that removal failed and the state before removal was restored.
If the result is unknown, do not repeat the command. Read the status with [update and rollback](update-and-rollback.md).

## Task 2: return the ACE to vendor V1.3.863

| Item | Requirement |
| --- | --- |
| Current firmware | `CV1.3.863`, boot `V1.0.1` (the OpenCubic build that this project specifies) |
| Target firmware | `ACE_V1.3.863_20250518.bin`, 105652 bytes, reports `V1.3.863` |
| SHA-256 | `3f3676ba357749b3d0367922cb7f6b0dedc9b3d104c1c29e719ac3e563f5eb63` |
| Source | [Pinned community-hosted file](https://github.com/Jupsi/OpenCubic/blob/6a97e86eda2872e8f8046cefd9470d89906d9a36/originalFirmware/ACE_V1.3.863_20250518.bin) |

- This project must be installed on the U1. The tool uses it to confirm that the devices are idle and to restore Klipper afterwards.
- After the write, the multi-brand NFC recognition from OpenCubic is not available.
- Other versions are refused. Do not change the detected values to pass the check.
- Keep ACE power and USB connected, and keep the U1 on, for the full procedure.

For the manual procedure, set `$PrinterTarget` and `$RemoteDir` first. The first step downloads, verifies, and reads the version. It does not write:
```powershell
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 tools/ace_usb/wizard_backend.py prepare --route stock"
```

Read the result until the state is not `PREPARING`:
```powershell
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 tools/ace_usb/wizard_backend.py result --wait-seconds 30"
```

| Result | Meaning |
| --- | --- |
| `PREPARED`, `route: stock`, `target_firmware: V1.3.863` | You can continue. Record the `operation`. |
| `ALREADY_TARGET` | The ACE already has vendor `V1.3.863`. No write is necessary. |
| `UNSUPPORTED` | The current version is not supported. Stop. |
| `NEEDS_ATTENTION` or `ERROR` | Stop. Follow [update and rollback, section 2](update-and-rollback.md#ace-interruption). |

When `ready: true` and `service_restored: true` are shown, do this one write. All three confirmation flags are necessary:
```powershell
$AceOperation = (Read-Host 'Enter the operation from the prepare result').Trim()
if ($AceOperation -notmatch '^[a-f0-9]{32}$') { throw 'STOP: Invalid operation identifier' }
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 tools/ace_usb/wizard_backend.py start --operation $AceOperation --confirm-flash --accept-untested-rollback --accept-untested-stock-route"
```

After that, only read the result. **Do not send `start` again**:
```powershell
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 tools/ace_usb/wizard_backend.py result --wait-seconds 30"
```

Expect `SUCCEEDED`, `ready: true`, and `service_restored: true`. For all other results, stop and keep the records.
After success, check loading and unloading for each slot before normal use.

## Task 3: return the U1 to official Snapmaker firmware

The method is from the [extended firmware installation notes](https://snapmakeru1-extended-firmware.pages.dev/install): download the official `.bin` and install it with the same Local Update steps.

| Item | Value |
| --- | --- |
| File | `U1_2.0.0.205_20260914173503_upgrade.bin`, 216715726 bytes |
| Download | [Official Snapmaker address](https://public.resource.snapmaker.com/firmware/U1/U1_2.0.0.205_20260914173503_upgrade.bin), listed in the [official release notes](https://wiki.snapmaker.com/en/snapmaker_u1/firmware/release_notes) |
| SHA-256 | `e6269eb0f1d9e8da74173e9da6350a14b18dd2fe5c4e8f2cabc48b0cdaf2aad7` |

Snapmaker publishes no checksum. The value above is the one pinned by the upstream extended-firmware build. This project downloaded the official file and found the same value.

1. Do task 1 first and remove this project.
2. Recommended: clear the extended configuration. On the computer, open `http://PRINTER-ADDRESS/firmware-config/` and select **Reset Extended to Defaults** under Recovery. The official firmware does not delete this configuration.
3. Download the file from the table and verify it:
```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath ((Read-Host "Paste the file path").Trim('"'))
```
4. If the result is different from the table, do not use the file. If it is the same, copy the file to the top level of a FAT32 USB drive.
5. With the printer idle and cool, insert the USB drive. On the screen, select **Settings > About > Firmware Version > Local Update**, select the file, and confirm.
6. Wait for the update and the automatic restart. Do not remove power or the USB drive during the update.

After the return:

- Advanced Mode, Root Access, and the extended configuration page are removed with the extended firmware.
- If the printer offers `V2.1.0`, read the Snapmaker instructions first. Its wiki records a [black screen after the 2.1.0 update](https://wiki.snapmaker.com/en/snapmaker_u1/troubleshooting/touchscreen_malfunction).
- If the update reports an error, follow the [official update troubleshooting](https://wiki.snapmaker.com/en/snapmaker_u1/troubleshooting/firmware-update-failed).

## To install again later

Follow the [quick start](quick-start.md) from the beginning. The backups from removal and installation stay on the printer in `/userdata/ultimate-u1-ace-link/backups/`.
