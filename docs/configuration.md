# Configuration and calibration

[中文说明](configuration.zh-CN.md) · [Guided installation](quick-start.md)

Tube length affects the settings. It is not the same as a transport command length.
Use three separate values:

| Letter | JSON setting | Function | Reference only |
| --- | --- | --- | --- |
| **A** | `retract_length` | Main ACE return distance, after the U1 releases filament from the hotend. | 1250 mm at speed 80 |
| **B** | `fast_load_length` | Base fast segment. Leave room for the slow approach to the head. | 1150 mm at speed 200 |
| **C** | `forward_takeup_length` | Forward movement after A, to draw loose filament into the PTFE tube. | Start at 0; tested reference 300 mm at speed 50 |

**All four slots share A, B, C, and the speed settings.**
This version has no separate length setting for each slot.
Check all four paths before you accept a common setting.
Distances use millimeters (mm). Speeds are protocol requests in millimeters per second (mm/s).
They are not measurements of actual motor or filament speed.

> [!CAUTION]
> **1250, 1150, and 300 are reference values for one tested arrangement.**
> **They are not universal values for every tube layout.**
> Loading stops at the U1 head sensor. It does not intentionally push until a mechanical stall.
> A travel limit and a timeout stop an unsuccessful attempt.

## Settings files

The [guided launcher](quick-start.md) asks for A and B during a first installation.
It starts with C disabled and uses the reference speeds below.
For an existing installation, the launcher keeps the current settings.
**Running the launcher again does not apply new A, B, or C values.**
Use [Apply changed settings](#apply-changed-settings) for an intentional change.

| File | Use |
| --- | --- |
| `config/settings.example.json` | Conservative template. C is 0. Existing settings are preserved. |
| `config/settings.tested-reference.json` | Tested reference. C is 300. It requests replacement of existing settings. |
| `config/settings.local.json` | Your working file for the manual procedure below. |

Both templates have `calibrated_acknowledged: false`.
Review your physical lengths and speeds before changing it to `true`.
The acknowledgement does not measure or test your tubes.
For a first installation, it confirms review of the initial settings.
Complete the physical checks after installation, before normal printing.

| Setting | Reference value | Meaning |
| --- | --- | --- |
| `serial` | Your ACE USB path | Preserves an existing choice or identifies one matching ACE. |
| `auto_detect_serial` | `true` by default | Automatic selection requires one matching device. |
| `baud` | `115200` | Serial connection speed. Keep this value. |
| `feed_speed` | `200` | Default speed for direct `ACE_FEED`, not the staged-load speed setting. |
| `feed_length` | `1250` | Retained legacy preload option. Automatic long preload is disabled. This is **not B**. |
| `retract_speed` | `80` | Main ACE return speed. |
| `retract_length` | `1250` | A: main ACE return distance. |
| `forward_takeup_length` | `0` initially | C: forward take-up distance. Zero disables this movement. |
| `forward_takeup_speed` | `50` | Speed of C when enabled. |
| `fast_load_length` | `1150` | B: fast distance before the recorded advance deduction. |
| `fast_load_speed` | `200` | Fast-stage speed. |
| `sensor_load_speed` | `50` | Final approach speed. |
| `sensor_load_max_length` | `2500` | Total load travel allowance across both stages. A fault limit, not the target. |
| `max_dryer_temperature` | `55` | Dryer ceiling. Keep your existing value during length calibration. |
| `calibrated_acknowledged` | `false` in templates | Set `true` after reviewing the physical lengths and speeds. |
| `apply_existing_settings` | `false` normally | Set `true` to apply intentional changes to an existing installation. |

`ACE_FEED` requires its own `LENGTH` argument. It does not use `feed_length` as its default length.
For the U1 screen's Load action, change `fast_load_length`, not `feed_length`.
For Unload, change `retract_length` and, if required, `forward_takeup_length`.

The installer writes ACE options to `/home/lava/printer_data/config/extended/klipper/ace.cfg`.
It applies staged-load constants to the installed module.
It also configures External detection and the internal-reader service.
**Use the installer for parameter changes. Do not edit `ace.py` yourself.**

The installer accepts these relationships:

- C is 0–500 mm, and is smaller than both A and B.
- B does not exceed A, and is smaller than the total load allowance.
- Fast speed does not exceed 200. Slow and take-up speeds do not exceed 50.

These checks reject invalid inputs. They do not prove mechanical suitability.
Keep the 2500 mm fault limit during this procedure. Do not increase it to hide a feed failure.

## How the distances interact

Insertion starts the ACE's short bite and NFC recognition.
It does not start long transport to the U1 head.
Select **Load** on the U1 when you want to load that slot.

With a valid starting-position record, the controller uses:

```text
fast request = max(0, B - recorded forward advance)
slow allowance = 2500 - fast request
```

The head sensor can stop either stage early.
The slow allowance is a maximum request, not a distance that must be completed.
After detection, the U1 completes its normal extruder loading sequence.

| Starting state | Example fast request | Final approach |
| --- | --- | --- |
| Verified new insertion; B = 1150 | 1150 mm at speed 200 | Speed 50; maximum remaining allowance 1350 mm |
| Successful unload; B = 1150 and C = 300 | **850 mm at speed 200** | Speed 50; maximum remaining allowance 1650 mm |
| Restart, interrupted operation, or uncertain position | No fast stage | Speed 50; total allowance 2500 mm |

**Do not enter 850 as B to compensate for C = 300.**
Keep B = 1150 in that reference example. The controller subtracts the recorded 300 itself.
Entering B = 850 would produce a 550 mm fast request after that unload.

![Conceptual transport distances](images/feed-cycle.svg)

The picture shows control stages, not tube dimensions.
The recorded advance is a conservative allowance, not a measured tip position.
The controller consumes the starting-position record once. A restart clears it.
A slow first load after installation can therefore be normal.

During Unload, the sequence is:

1. The U1 performs its normal hotend release.
2. ACE retracts A at speed 80.
3. The controller checks the head and ACE inlet states.
4. If enabled, ACE feeds C toward the U1 at speed 50.
5. The controller confirms completion and records C for the next load.

Filament must remain in the ACE inlet and rear PTFE path, with the U1 head sensor empty.
Material data remains while filament remains in the ACE inlet.
An uncertain completion does not authorize an automatic retry.

## Calibrate the PTFE paths

### Measure and record all four paths

**Measure the installed tube along its bends, not the straight distance between the machines.**
The ACE internal path, initial bite, head path, and hotend release also affect transport.
A tape measure does not measure these movements. This project does not measure tube length automatically.

1. Finish printing and any filament operation.
2. Let the printer cool before inspecting the paths.
3. Remove power before disconnecting tubing or hardware.
4. Label both ends of each tube with its ACE slot and U1 head.
5. Measure each installed PTFE route along its bends.
6. Record inaccessible sections as unknown. Do not guess them as zero.
7. Record the intended tip position after unloading.
8. Reconnect every tube securely before a powered test.

Use a parking point inside the ACE-side PTFE tube.
The tip must not reach the head or leave the ACE inlet after unloading.
A starts after the U1's hotend release, not at one end of the tape measure.
**Do not copy the measured tube length directly into A, B, and C.**

| Slot / U1 head | Measured PTFE route (mm) | Internal sections or unknowns | Tip position after unload | A / B / C tested | Load → unload → reload result |
| --- | --- | --- | --- | --- | --- |
| ACE 1 → head ___ | ___ | ___ | ___ | ___ / ___ / ___ | ___ |
| ACE 2 → head ___ | ___ | ___ | ___ | ___ / ___ / ___ | ___ |
| ACE 3 → head ___ | ___ | ___ | ___ | ___ / ___ / ___ | ___ |
| ACE 4 → head ___ | ___ | ___ | ___ | ___ / ___ / ___ | ___ |

Use one common set that works on every row.
Check B against the shortest effective path to a head.
It must end before the head, leaving a slow approach.
Check both a new insertion and a reload after unloading.

The reference difference between A = 1250 and B = 1150 is 100 mm.
**That difference does not establish a 100 mm physical clearance on your printer.**
Do not assume that another layout needs the same margin.
If the four paths have no safe common setting, correct the tube arrangement before proceeding.

### Choose and check the first values

**You do not need to complete an ACE transport test before installing the integration.**
There are two separate stages:

| Stage | What you do | When you can continue |
| --- | --- | --- |
| Before installation | Record the four routes and the intended ACE-side parking point. Review initial A and B; keep C = 0. | You can explain where the tip will remain and where fast travel must end. Unknown dimensions are resolved. |
| After installation | Use the U1 screen to test Load, Unload, then Load on one slot. Inspect the stopped tip and record the result. | The first slot passes; then repeat on the other three slots before normal printing. |

Start from recorded, working values for your arrangement, when available.
Measurements help assess clearance. They do not establish an exact A by themselves.
If the path or parking point is unknown, resolve it before entering an unverified long return.
You can exit the first-installation wizard without installing.

1. Set C to `0` for the initial checks.
2. Keep fast speed `200`, approach speed `50`, and return speed `80`.
3. Choose B short enough to leave a slow approach before the head.
4. Choose A to return the tip to the recorded ACE-side parking point.
5. Enter the reviewed A and B during first installation. For later changes, use the procedure below.
6. Test one slot with the U1's normal Load, Unload, and Load actions.
7. Wait for each action to finish before selecting the next action.
8. Record the final tip position, head state, inlet state, and loose filament.
9. Test the other three slots with the same settings.
10. Keep the record with your installed settings.

Keep hands away from moving rollers. Inspect the final tip only after motion stops.
Remove power before disconnecting a tube to inspect it.
Use the [acceptance checklist](validation.md#repeat-the-acceptance-check) to record the full cycle.

### What to change after an observation

| Observation | Next action |
| --- | --- |
| Fast travel reaches the head before a slow approach. | Reduce B. A sensor stop does not prove sufficient fast-stage clearance. |
| The slow approach is long, but loading succeeds. | You can keep B. Increase it only after verifying the remaining clearance on all four paths. |
| After unloading, the tip is too far toward U1; the head is empty and no fault occurred. | Consider a small increase in A, within the measured ACE retention margin. Retest with C = 0. |
| The tip leaves the ACE inlet, or the inlet becomes empty. | Reduce A after correcting the physical state. Do not repeat Unload to recover it. |
| Unload fails, the head still detects filament, or filament slips or jams. | Inspect hotend release and the tube path. Do not increase A blindly. |
| Unload succeeds, but loose loops remain at the spool. | Keep A and B. Evaluate C separately in the next section. |
| A changed B seems unused on the first load after restart. | An unknown position uses the slow stage. Check a reload after a successful unload. |

Change one distance at a time, within the clearance you can verify.
No universal increment or tube-length ratio guarantees a correct result.

### After changing or rerouting a tube

1. Save the last working settings and four-slot record.
2. Measure the changed route and update the record.
3. Recheck the shortest path across all four slots.
4. Disable C during the new calibration.
5. Review A and B before the next load or unload.
6. Repeat the four-slot checks.
7. Re-enable C only after the new A and B pass.

A change to one tube can invalidate the common B setting.
Do not use old values merely to discover whether a new tube is too short.

## Enable forward take-up

C draws loose filament into the PTFE tube after the main return.
It does not independently turn spool rollers. It has no tension-sensor endpoint.

1. Confirm successful loading, unloading, and reloading with C = `0`.
2. Inspect the loose filament after unloading.
3. Select a limited C for the observed slack and available head clearance.
4. Keep `forward_takeup_speed` at or below `50`.
5. Apply the change and test one normal unload.
6. Check that the head remains empty and the ACE inlet remains occupied.
7. Check the next load without removing the filament.
8. Repeat the checks on all four slots.

**The tested C = 300 is not an automatic recommendation for your setup.**
See the [recorded slot-4 test](validation.md) for its scope.
More C consumes more of the parked distance toward the head.
If slack remains, first confirm that filament moves freely.
Increase C only within verified clearance and the accepted limits.
If filament becomes tight, snags, or reaches the head, stop and reduce or disable C.
Do not increase A merely to compensate for excessive C.

## Apply changed settings

This procedure changes an **existing installation**.
For a first installation, use the [guided launcher](quick-start.md). It asks for A and B and starts with C = 0.
The procedure exports effective current settings before editing them.
This preserves your serial path, dryer ceiling, and other values.
**Do not replace your full settings file with a generic example.**

### 1. Prepare the printer and project folder

1. Finish printing and all filament operations.
2. Complete the [idle preparation](installation.md#5-check-before-installation).
3. Keep heater targets at zero and actual temperatures below 50 °C.
4. Stop the ACE dryer and feed assist.
5. Open an extracted project version that supports your installed version.
6. Enter the folder containing `installer.py` and `manifest.json`.
7. Type `powershell` in File Explorer's address bar, then press Enter.

Use the same PowerShell window for every block.
Copy commands inside each block, without the surrounding backticks.
If any command reports an error, stop before the next block.

```powershell
$ProjectDir = (Get-Location).Path
if (-not (Test-Path -LiteralPath .\installer.py)) { throw "Open the folder containing installer.py first." }
$PrinterAddress = Read-Host "Printer IP from the Wi-Fi page"
$PrinterTarget = "root@$PrinterAddress"
$RemoteDir = "/userdata/ultimate-u1-ace-tuning-" + (Get-Date -Format "yyyyMMdd-HHmmss")
Get-Command ssh, scp
$UploadDir = Join-Path ([IO.Path]::GetTempPath()) ("U1AceSettings-" + [guid]::NewGuid().ToString('N'))
$PublicFiles = @('installer.py', 'manifest.json', 'LICENSE', 'THIRD_PARTY.md', 'SOURCES.json',
    'payload/ace.py', 'payload/filament_feed.py', 'payload/filament_detect.py', 'payload/extruder.py',
    'tools/ace_usb/wizard_backend.py', 'tools/ace_usb/ace_iap.py', 'tools/ace_usb/protocol.py',
    'tools/ace_usb/prepare_profile.py', 'tools/ace_usb/fetch_firmware.py',
    'tools/ace_usb/images.json', 'tools/ace_usb/device-profile.json', 'config/settings.example.json')
foreach ($Name in $PublicFiles) {
    $Destination = Join-Path $UploadDir $Name
    New-Item -ItemType Directory -Force -Path (Split-Path $Destination -Parent) | Out-Null
    Copy-Item -LiteralPath (Join-Path $ProjectDir $Name) -Destination $Destination -ErrorAction Stop
}
scp -O -r "$UploadDir" "${PrinterTarget}:$RemoteDir"
if ($LASTEXITCODE -ne 0) { throw "Upload failed. Stop here." }
```

Enter the root password when requested. SSH does not display password characters.
Verify new host-key prompts with the [connection instructions](installation.md#confirm-the-connection).
The temporary upload folder contains only the listed public files, not your backups or local configuration.

### 2. Export the current settings

The read-only check uses the conservative template to retain current settings. It does not install that template.
These commands preserve any previous local working file before writing the export.

```powershell
$PlanText = ssh $PrinterTarget "cd '$RemoteDir' && python3 installer.py check --settings config/settings.example.json"
if ($LASTEXITCODE -ne 0) { throw "Check failed. Stop here." }
$Plan = ($PlanText -join "`n") | ConvertFrom-Json
if ($Plan.compatible -ne $true -or $Plan.fresh_install -ne $false) { throw "This procedure requires a supported existing installation." }
if (Test-Path -LiteralPath .\config\settings.local.json) {
    Copy-Item -LiteralPath .\config\settings.local.json -Destination (".\config\settings.local.before-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".json")
}
$Plan.effective_settings | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath .\config\settings.local.json -Encoding UTF8
notepad .\config\settings.local.json
```

### 3. Edit the three distances

Find these entries in Notepad.
This is a **partial example**, not a replacement for the complete file.
The distances are references. Use your calibration record.

```json
{
  "retract_length": 1250,
  "fast_load_length": 1150,
  "forward_takeup_length": 0,
  "apply_existing_settings": true,
  "calibrated_acknowledged": true
}
```

1. Change `retract_length` to your A.
2. Change `fast_load_length` to your B.
3. Change `forward_takeup_length` to your C. Use 0 during initial calibration.
4. Set `apply_existing_settings` to `true`.
5. Set `calibrated_acknowledged` to `true` after reviewing the physical values.
6. Keep every other entry from the exported file.
7. Save the file and close Notepad.

Use whole numbers without quotation marks or units. Use lowercase `true` and `false`.
Keep commas, quotation marks, and braces in place.
Leave `feed_length` unchanged. It is not the current U1 loading distance.
Reference speeds are `retract_speed: 80`, `fast_load_speed: 200`, and `sensor_load_speed: 50`.
Review custom speeds separately instead of silently replacing them.

### 4. Check, apply, and verify

1. Upload the edited file and run the read-only check.

```powershell
scp -O .\config\settings.local.json "${PrinterTarget}:$RemoteDir/config/settings.local.json"
if ($LASTEXITCODE -ne 0) { throw "Settings upload failed. Stop here." }
ssh $PrinterTarget "cd '$RemoteDir' && python3 installer.py check --settings config/settings.local.json"
if ($LASTEXITCODE -ne 0) { throw "Check failed. Do not install." }
```

2. Read `effective_settings` in the output.
3. Confirm A, B, C, speeds, serial path, and dryer ceiling.
4. Confirm that `apply_existing_settings` and the check's `calibration_acknowledged` are `true`.
5. Keep the printer idle and cold, then apply the settings.

```powershell
ssh $PrinterTarget "cd '$RemoteDir' && python3 installer.py install --settings config/settings.local.json"
if ($LASTEXITCODE -ne 0) { throw "Install failed. Read the rollback result and backup ID. Stop here." }
```

6. Save the reported backup ID.
7. Run the read-only check again.

```powershell
ssh $PrinterTarget "cd '$RemoteDir' && python3 installer.py check --settings config/settings.local.json"
if ($LASTEXITCODE -ne 0) { throw "Verification failed. Do not start a transport test." }
```

8. Confirm effective values, then perform the four-slot checks above.

The installer restarts Klipper and verifies the loaded configuration.
It preserves NFC secrets and checks existing material data.
If installation fails, read the automatic rollback result before proceeding.
Use [Update and rollback](update-and-rollback.md) when recovery is needed.
