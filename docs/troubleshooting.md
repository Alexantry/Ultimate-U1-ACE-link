# Troubleshooting

[简体中文](troubleshooting.zh-CN.md) · [Installation guide](quick-start.md) · [Daily use](daily-use.md)

If the filament position is uncertain, do not repeat Load or Unload.
Keep the printer idle and save the complete error text.

> [!IMPORTANT]
> **Use the recovery path for the operation that failed.**
> **Do not repeat a firmware write because the computer disconnected.**

| Where the problem started | First action |
| --- | --- |
| U1 screen firmware update | Keep the screen error. Follow [U1 firmware recovery](u1-preparation.md). |
| ACE firmware update, or its result is unknown | Keep power and USB connected. Open the same package version, select menu **4**, and read the saved result. See [ACE recovery](ace-wizard.md). |
| U1 host integration installation | Read the success or restoration result. Use [host recovery](update-and-rollback.md#after-an-interrupted-installation) before reinstalling. |
| Normal loading, unloading, or NFC after installation | Use the checks below. Do not start with another firmware update. |

`Automatic rollback VERIFIED` covers host files and services. It does not restore ACE or U1 firmware.

## Connection and installation

| Symptom | Check | Next action |
| --- | --- | --- |
| SSH refuses the connection | Root Access, current U1 address, computer network | Follow the [connection steps](installation.md#confirm-the-connection). Keep the computer and U1 on the same local network. |
| Password entry shows no letters or stars | Normal for SSH | Type the root SSH password and press Enter. It is not the Wi-Fi password. |
| Windows cannot find `ssh` or `scp` | OpenSSH Client is missing | Follow the Windows component steps in the [quick start](quick-start.md). |
| Printer disappeared after a U1 firmware change | Wi-Fi on the touchscreen; whether the address changed | Reconnect Wi-Fi. Use the current address. |
| `/firmware-config/` is unavailable | Advanced Mode, current address | Enable Advanced Mode on the U1 and restart when asked. |
| ACE is missing, or several serial devices are offered | ACE power, Gen 1 hardware, verified connection cable | Connect only one ACE. Recheck the hardware with power off, then repeat the read-only check. Do not guess or edit a serial path. |
| Installer rejects a core file | A manual change or unsupported software version | Keep the file and the error for a compatible migration. Do not delete or overwrite it to bypass the check. |
| Installer rejects the firmware | The exact compatibility baseline | Keep the existing firmware. Compare the reported version with [U1 preparation](u1-preparation.md). Do not force the check. |
| Installer rejects existing configuration | Duplicate or unexpected ACE sections | Save and review the reported config paths before any edit. Do not delete other configuration. |
| Changes disappear after reboot | Persistence, recent firmware changes | Read the [installation status](update-and-rollback.md#read-installation-status) before reinstalling. |
| Klipper is disconnected | Startup error in `klippy.log` | Fix that error before testing transport. |

The camera can work while Klipper is disconnected. A camera image does not prove that filament control is ready.

## Filament transport

| Symptom | Explanation or check | Next action |
| --- | --- | --- |
| Insertion stops after a short bite | Intended behavior | Select Load for that slot on the U1 for full loading. |
| Loading waits during NFC recognition | Recognition has its own readiness wait. | Wait. Do not select Load repeatedly. |
| The second slot waits | One operation owns ACE transport. | Wait for the active operation to finish. |
| Loading is slow after a restart | The origin is unknown, so loading is slow and sensor-controlled. | Let it finish. On a jam or error, stop. Do not force the fast stage. |
| Next fast stage is shorter after take-up | The software subtracts the completed forward advance from fast-feed distance B. | Compare your own B and C values. Example only: 1150 minus 300 gives 850 mm. |
| Loading stops with a travel or timeout error | The head sensor did not confirm arrival. | Inspect the path and head sensor first. Do not repeat the long feed. |
| Unloading leaves loose filament | Take-up is disabled on new installations. An existing distance can also be too short. | Verify normal loading and unloading first. Then follow [take-up calibration](configuration.md#enable-forward-take-up). |
| No take-up follows an unload error | A valid retraction completion was not established. | Resolve the unload error first. |
| Filament remains in the rear PTFE tube after unloading | By design, it is kept for the next load. | Check that the ACE inlet has filament and the head has none. |
| Stop was acknowledged but motion continued briefly | Some ACE selector states do not stop immediately. | During normal filament operations, use the ACE power switch if motion becomes unsafe. |

Forward take-up advances filament into the rear PTFE tube to use up loose filament.
It does not detect tension, command independent roller rotation, or rewind loose filament onto the spool.
The host has no independent roller-speed parameter. The example take-up distance does not suit every tube arrangement.

## NFC and material display

| Symptom | Check | Next action |
| --- | --- | --- |
| Type and color appear, but the brand is Generic | Whether the displayed data is current | Reopen the slot details on the U1. If still Generic, check the exact ACE build and supported tag list. Keep External selected. |
| U1 shows Bambu, but the slicer does not | The slicer's own brand and material profiles | Check the slicer profiles and the U1 slot details separately. Do not change ACE firmware for this. |
| ACE does not recognize a tag | ACE firmware, tag format, original tag presence, tag position | Compare the [NFC support table](nfc.md). Unsupported or untagged spools can use manual material data. |
| U1 OpenRFID works, but ACE does not | Different readers and decoders | Check the ACE path. Do not copy U1 keys. |
| Material disappears after true inlet removal | Intended clear event | Reinsert and wait for a new read. |
| Material disappears during head-only unloading | The material-retention module might be missing. | Check the installed project version and status. |
| Dashboard has no material card | Klipper state, dashboard layout, available components | Restore Klipper readiness before comparing layouts. |

Use **External** mode for the ACE material path. Changing back to internal OpenRFID does not upgrade the ACE reader.
Read the [NFC notes](nfc.md) before changing detection settings.
Tags supported by the specified OpenCubic firmware need no NFC keys from you.

## Read status without motion

**Host installation status:** use [read installation status](update-and-rollback.md#read-installation-status). It identifies the correct printer staging directory. Do not assume an old PowerShell window still has the correct variables. Connection basics are in [confirm the connection](installation.md#confirm-the-connection).

**ACE status (optional):** the steps below read data already available to the U1 web interface.
They send no motion command and open no second ACE serial connection.
Use them only after the host integration is installed. During an unresolved ACE firmware update, use menu **4** instead.

1. Press **Windows + R**, type `powershell`, and press Enter.
2. Copy the line below into the window. Press Enter.
3. At the prompt, enter the current IP from the U1 Wi-Fi screen. Do not add `http://` or a path. Press Enter.

```powershell
$PrinterAddress = (Read-Host "Current printer IP from the Wi-Fi screen").Trim()
```

4. Copy the next block into the window and press Enter.

```powershell
$AceStatus = Invoke-RestMethod "http://$PrinterAddress/printer/objects/query?ace"
$AceStatus.result.status.ace | Format-List
```

Empty response or error: check Klipper readiness and save the exact message.
Do not change motion settings to make a failed status request succeed.

| Field | Meaning |
| --- | --- |
| `connected`, `status_fresh` | Whether ACE is connected and its state is current. Both must be true for normal operation. |
| `status`, `last_error` | Current ACE state and the last reported error. |
| `gate_status` | Inlet states for slots 1 to 4: `0` empty, `1` occupied, `-1` unknown. Unknown does not mean empty. |
| `fast_origins`, `fast_origin_advance_mm` | The known loading origin and the distance already advanced after unloading. |
| `rfid_sync` | Material synchronization progress for each slot. |

## Prepare an issue report

1. Full U1 firmware version.
2. ACE generation, runtime version, and known firmware source.
3. Installed project version.
4. Affected slot number.
5. Last successful action.
6. Filament movement and spool or roller movement, described separately: whether each moved and when it stopped.
7. Exact error text, plus only the needed log excerpts, reviewed and with private data removed.

Do not attach private NFC keys, full configuration backups, credentials, or unreviewed device dumps.
Use [the project issue tracker](https://github.com/Alexantry/Ultimate-U1-ACE-link/issues) for reproducible host integration problems.
