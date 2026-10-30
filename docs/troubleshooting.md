# Troubleshooting

[简体中文](troubleshooting.zh-CN.md) · [Installation guide](quick-start.md) · [Daily use](daily-use.md)

Do not repeat Load or Unload when the filament position is uncertain.
Keep the printer idle while you identify the cause. Save the complete error text.

> [!IMPORTANT]
> **Use the recovery path for the operation that failed.**
> **Do not repeat a firmware write because the computer disconnected.**

| Where the problem started | First action |
| --- | --- |
| U1 screen firmware update | Keep the screen error. Follow [U1 firmware recovery](u1-preparation.md). |
| ACE firmware update, or its result is unknown | Keep power and USB connected. Open the same package version, select menu **4**, and inspect the saved result. See [ACE recovery](ace-wizard.md#if-preparation-or-updating-stops). |
| U1 host integration installation | Read the success or restoration result. Use [host recovery](update-and-rollback.md#after-an-interrupted-installation) before reinstalling. |
| Normal loading, unloading, or NFC after installation | Use the checks below. Do not start another firmware update as the first response. |

`Automatic rollback VERIFIED` concerns host files and services. It does not restore ACE or U1 firmware.

## Connection and installation

| Symptom | Check | Next action |
| --- | --- | --- |
| SSH refuses the connection | Root Access, current Wi-Fi address, and the computer's network | Use the [connection steps](installation.md#confirm-the-connection). Keep the computer and U1 on the same local network. |
| Password entry shows no letters or stars | This is normal for SSH. | Enter the root SSH password and press Enter. It is not the Wi-Fi password. |
| Windows cannot find `ssh` or `scp` | OpenSSH Client is missing. | Use [the Windows component steps](quick-start.md#install-the-windows-openssh-client-if-needed). |
| The printer disappeared after a firmware change | Wi-Fi connection on the touchscreen | Reconnect Wi-Fi before another installation attempt. |
| `/firmware-config/` is unavailable | Advanced Mode | Enable Advanced Mode. |
| ACE is missing, or several serial devices are offered | ACE power, Gen 1 hardware, and the verified connection cable | Connect only one ACE. Recheck the hardware while powered off, then repeat the read-only check. Do not guess or edit a serial path. |
| The installer rejects a core file | A manual change or unsupported software version | Preserve the file for a compatible migration. |
| The installer rejects the firmware | The exact compatibility baseline | Keep the existing firmware. Compare the reported version with [the supported preparation path](u1-preparation.md). Do not force the check. |
| The installer rejects existing configuration | Duplicate or unexpected ACE sections | Review the reported config paths before any edit. |
| Changes disappear after reboot | Persistence and recent firmware changes | Read [installation status](update-and-rollback.md#read-installation-status) before reinstalling. |
| Klipper is disconnected | Startup error in `klippy.log` | Resolve that error before testing transport. |

The camera can remain available while Klipper is disconnected.
A visible camera image therefore does not prove that filament control is ready.

## Filament transport

| Symptom | Explanation or check | Next action |
| --- | --- | --- |
| Insertion stops after a short bite | This is the intended behavior. | Select Load on the U1 when you want full loading. |
| Loading waits during NFC recognition | Recognition has its own readiness wait. | Wait for recognition to finish. |
| The second slot waits | One operation owns ACE transport. | Wait for the active operation to finish. |
| Loading is slow after a restart | The origin is unknown. | Let the sensor-controlled slow load finish. |
| The next fast stage is shorter after take-up | The software subtracts the completed forward advance from fast-feed distance B. | Compare your own B and C values. Example only: 1150 minus 300 gives 850 mm. |
| Loading stops with a travel or timeout error | The head sensor did not confirm arrival. | Inspect the path and sensor before another attempt. |
| Unloading leaves loose filament | New installations start with take-up disabled. An existing distance can also be insufficient. | First verify normal loading and unloading. Then follow [take-up calibration](configuration.md#enable-forward-take-up). |
| No take-up follows an unload error | A valid retraction completion was not established. | Resolve the unload error first. |
| Filament remains in the PTFE tube after unloading | The design retains filament for later loading. | Check the inlet and head states. |
| A stop command was acknowledged but motion continued briefly | Some ACE selector states do not stop immediately. | During normal filament operations, use the ACE power switch if motion becomes unsafe. |

The host does not provide an independent roller-speed parameter.
Forward take-up advances filament into the rear PTFE tube to consume loose filament.
It does not detect tension, command independent roller rotation, or rewind loose filament onto the spool.
The example take-up distance is not suitable for every tube arrangement.

## NFC and material display

| Symptom | Check | Next action |
| --- | --- | --- |
| Material type and color appear, but the brand is Generic | Whether the displayed data is current | Reopen the slot details on U1. If it remains Generic, check the exact ACE build and supported tag list. Keep External selected. |
| Bambu does not appear in the slicer | The slicer's available brand profiles | Check the U1 slot details separately. |
| ACE does not recognize a tag | ACE firmware, tag format, original tag presence, and tag position | Compare [the NFC support table](nfc.md). Unsupported or untagged spools can use manual material data. |
| U1 OpenRFID works, but ACE does not | These are different readers and decoders. | Check the ACE path instead of copying U1 keys. |
| Material disappears after true inlet removal | This is the intended clear event. | Reinsert the spool for a new read. |
| Material disappears during head-only unloading | The material-retention module might be missing. | Check the installed project version. |
| The dashboard has no material card | Klipper state, dashboard layout, and available components | Restore Klipper readiness before comparing layouts. |

External mode is appropriate for the ACE material path.
Changing back to internal OpenRFID does not upgrade the ACE reader.
See [NFC responsibilities](nfc.md) before changing detection settings.
The supported OpenCubic tags do not require you to find or enter NFC keys.

## Read useful status without motion

For host installation status, use [the status and connection setup](update-and-rollback.md#read-installation-status).
That procedure identifies the correct printer staging directory. Do not assume an old PowerShell window still has the correct variables.

The optional steps below read the ACE status already available to the U1 web interface.
They do not send a motion command or open a second ACE serial connection.
Use them after the host integration is installed. During an unresolved ACE firmware update, use menu 4 instead.

1. Press **Windows + R**, type `powershell`, and press Enter.
2. Copy the line below into the window. Press Enter.
3. At the address prompt, enter the current IP from the U1 Wi-Fi screen. Do not add `http://` or a path. Press Enter.

```powershell
$PrinterAddress = (Read-Host "Current printer IP from the Wi-Fi screen").Trim()
```

4. Copy the next block into the window and press Enter.

```powershell
$AceStatus = Invoke-RestMethod "http://$PrinterAddress/printer/objects/query?ace"
$AceStatus.result.status.ace | Format-List
```

If the response is empty or reports an error, check Klipper readiness and save the exact message.
Do not change motion settings to make a failed status request succeed.

| Field | Meaning |
| --- | --- |
| `connected`, `status_fresh` | Whether ACE is connected and its state is current. Both must be true for normal operation. |
| `status`, `last_error` | Current ACE state and the last reported error. |
| `gate_status` | Four inlet states, in slot order: `0` empty, `1` occupied, `-1` unknown. Unknown does not mean empty. |
| `fast_origins`, `fast_origin_advance_mm` | The known loading origin and the distance already advanced after unloading. |
| `rfid_sync` | Material synchronization progress for each slot. |

## Prepare an issue report

1. Record the U1 firmware version.
2. Record the ACE generation and runtime version.
3. Record the installed project version.
4. Record the affected slot number.
5. Describe the last successful action.
6. Describe the visible filament and roller movement separately.
7. Remove private data from any attached log excerpt.

Do not attach private NFC keys, full configuration backups, credentials, or unreviewed device dumps.
Use [the project issue tracker](https://github.com/Alexantry/Ultimate-U1-ACE-link/issues) for reproducible host integration problems.
