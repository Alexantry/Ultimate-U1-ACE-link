# Troubleshooting

Do not repeat a transport command when the filament position is uncertain.
Keep the printer idle while you identify the cause.

## Connection and installation

| Symptom | Check | Next action |
| --- | --- | --- |
| SSH refuses the connection | Root Access and the current Wi-Fi address | Open Root Access on the printer. |
| The printer disappeared after a firmware change | Wi-Fi connection on the touchscreen | Reconnect Wi-Fi before another installation attempt. |
| `/firmware-config/` is unavailable | Advanced Mode | Enable Advanced Mode. |
| The serial device is missing | USB connection and `/dev/serial/by-id/` | Correct the local `serial` setting. |
| The installer rejects a core file | A manual change or unsupported software version | Preserve the file for a compatible migration. |
| The installer rejects the firmware | The exact compatibility baseline | Use a supported project and firmware combination. |
| The installer rejects existing configuration | Duplicate or unexpected ACE sections | Review the reported config paths before any edit. |
| Changes disappear after reboot | Persistence and recent firmware changes | Check the installation status before reinstalling. |
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
| The fast distance is 850 mm after take-up | The previous advance was 300 mm. | Confirm the expected 1150 minus 300 calculation. |
| Loading stops with a travel or timeout error | The head sensor did not confirm arrival. | Inspect the path and sensor before another attempt. |
| Unloading leaves loose filament | The configured take-up distance might be insufficient. | Review the [take-up calibration](configuration.md#enable-forward-take-up). |
| No take-up follows an unload error | A valid retraction completion was not established. | Resolve the unload error first. |
| Filament remains in the PTFE tube after unloading | The design retains filament for later loading. | Check the inlet and head states. |
| A stop command was acknowledged but motion continued briefly | Some ACE selector states do not stop immediately. | Use the ACE power switch if motion becomes unsafe. |

The host does not provide an independent roller-speed parameter.
The forward take-up feature does not detect tension or pull filament back onto the spool.

## NFC and material display

| Symptom | Check | Next action |
| --- | --- | --- |
| Material type and color appear, but the brand is Generic | Whether ACE supplied a nonempty brand | Check the decoded ACE result before changing U1 mode. |
| Bambu does not appear in the slicer | The slicer's available brand profiles | Check the U1 slot details separately. |
| ACE does not recognize a tag | ACE firmware, tag format, and tag position | Follow the ACE firmware's supported recognition procedure. |
| U1 OpenRFID works, but ACE does not | These are different readers and decoders. | Check the ACE path instead of copying U1 keys. |
| Material disappears after true inlet removal | This is the intended clear event. | Reinsert the spool for a new read. |
| Material disappears during head-only unloading | The material-retention module might be missing. | Check the installed project version. |
| The dashboard has no material card | Klipper state, dashboard layout, and available components | Restore Klipper readiness before comparing layouts. |

External mode is appropriate for the ACE material path.
Changing back to internal OpenRFID does not upgrade the ACE reader.
See [NFC responsibilities](nfc.md) before changing detection settings.

## Read useful status without motion

1. Open the Windows PowerShell session used for installation.
2. Read the installation status.

```powershell
ssh $PrinterTarget "cd '$RemoteDir' && python3 installer.py status"
```

3. Read the ACE status through Moonraker.

```powershell
$AceStatus = Invoke-RestMethod "http://$PrinterAddress/printer/objects/query?ace"
$AceStatus.result.status.ace | Format-List
```

The useful fields include `connected`, `status_fresh`, `status`, `last_error`, and `gate_status`.
`fast_origins` and `fast_origin_advance_mm` explain the next fast-stage decision.
`rfid_sync` reports material-transfer progress.

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
