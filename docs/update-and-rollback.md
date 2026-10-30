# Update, interrupted connections, and rollback

[简体中文](update-and-rollback.zh-CN.md) · [Manual installation](installation.md) · [Troubleshooting](troubleshooting.md)

**Distinguish ACE firmware maintenance from U1 host integration installation.** They are separate transactions.
A host backup cannot roll back ACE or U1 firmware.
For an unknown result, keep the devices idle. Do not print or resend an install or flash command.
Run this page's commands in **Windows PowerShell**. No AI or previous open window is required.

<a id="read-installation-status"></a>
## 1. Open a new window and initialize the connection

1. Open Start, search for **Windows PowerShell**, and open it.
2. Obtain the current U1 screen address and the recorded **RemoteDir**. Installation paths contain `stage`; manual parameter-change paths contain `tuning`. The wizard displays that directory on failure; its private computer log also records `Remote stage`.
3. Paste the block below. Enter the address and SSH password, then the exact recorded directory.
4. Use [the connection instructions](installation.md#confirm-the-connection) for first-contact identity checks and hidden password input.

**Do not guess a directory.** If the record is missing, preserve the error window, screen information, and files.
Do not select an apparently recent directory and run a write from it.
```powershell
$ErrorActionPreference = 'Stop'
Get-Command ssh.exe, scp.exe -CommandType Application | Out-Host
$PrinterAddress = (Read-Host 'Enter the IPv4 address shown on the U1 Wi-Fi screen').Trim()
if ($PrinterAddress -notmatch '^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$' -or
    @($PrinterAddress.Split('.') | Where-Object { [int]$_ -gt 255 }).Count -gt 0) {
    throw 'STOP: Invalid IPv4 address'
}
$PrinterTarget = 'root@' + $PrinterAddress
ssh.exe $PrinterTarget 'id'
if ($LASTEXITCODE -ne 0) { throw 'STOP: SSH connection failed' }
$RemoteDir = (Read-Host 'Paste the RemoteDir path saved from the previous operation').Trim()
if ($RemoteDir -notmatch '^/userdata/ultimate-u1-ace-(?:stage|tuning)-[0-9]{8}-[0-9]{6}(?:-[a-f0-9]{8})?$') {
    throw 'STOP: Use the exact recorded staging directory'
}
ssh.exe $PrinterTarget "ls '$RemoteDir/installer.py' '$RemoteDir/manifest.json' '$RemoteDir/tools/ace_usb/wizard_backend.py'"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Recorded package files are unavailable' }
```

**Expected:** `uid=0(root)` and all three file paths appear.
If files are missing, do not combine files from another release. Establish the original transaction result before transferring a replacement package or starting any new write.

### Read ACE state before host status

This query does not open serial, restore services, or start a flash:
```powershell
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 tools/ace_usb/wizard_backend.py result --wait-seconds 30"
if ($LASTEXITCODE -ne 0) { throw 'STOP: ACE result query failed' }
```

For `PREPARING`, `STARTING`, `RUNNING`, or `RECOVERING`, keep power connected and repeat the same `result` query later.
For `NEEDS_ATTENTION`, `ERROR`, or a failed query, use [ACE interruption handling](#ace-interruption).
Do not restart or roll back merely because Klipper is unavailable.
Safe terminal states also need `ready: true` and `service_restored: true`. `NONE` means no ACE transaction exists.

Only when no unresolved ACE transaction exists, read host status:
```powershell
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 installer.py status"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Host status is unavailable; do not start a write' }
```

Expect `klipper_state: ready`. After installation, `managed` is `true`.
`ace_version` is this project's module version, not the ACE firmware version.
`status` reads current state. **It does not prove that a disconnected installer process has finished or that the earlier installation succeeded.**
If the original process can still be active, wait and preserve its record. Do not roll back or install again.

<a id="ace-interruption"></a>
## 2. Interrupted ACE firmware operation

**Simplest path:** extract the same package version, run `START-HERE.cmd`, and select **menu 4: ACE firmware**.
It first reads the saved transaction. It does not automatically flash again.
Only a failure before any write can offer a check-and-restore operation.

| Result | Action |
| --- | --- |
| Operation active | Keep ACE, U1, and USB powered and connected. Continue result queries. |
| `SUCCEEDED` with restored service | Review material changes. ACE maintenance is complete; check host installation separately. |
| `FAILED_SAFE` | Resolve network, idle, or cooling conditions. Start fresh preparation through the same package version. |
| `NEEDS_ATTENTION`, `flash_attempted: false` | Menu 4 can offer probe-only restoration. Confirm once and wait. |
| `NEEDS_ATTENTION`, `flash_attempted: true` | **Do not reflash, attempt automatic stock rollback, or force Klipper to start.** Keep records and stop normal use. |
| Unsupported version or corrupt record | Stop. Do not edit JSON, remove transactions, or change reported versions. |

If you do not want the Windows wizard, continue using the read-only `result` query in section 1.
For probe-only recovery, first establish `NEEDS_ATTENTION`, `flash_attempted: false`, and a stopped worker.
The block below restores maintenance that has not started writing. It does not update firmware:
```powershell
$Raw = & ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 tools/ace_usb/wizard_backend.py result"
if ($LASTEXITCODE -ne 0) { throw 'STOP: ACE query failed' }
$SavedAce = ($Raw -join "`n") | ConvertFrom-Json
if ($SavedAce.state -ne 'NEEDS_ATTENTION' -or $SavedAce.flash_attempted -ne $false -or
    $SavedAce.operation -notmatch '^[a-f0-9]{32}$') { throw 'STOP: Probe-only recovery is not available' }
$OperationId = $SavedAce.operation
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 tools/ace_usb/wizard_backend.py recover --operation $OperationId"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Do not repeat recovery; query its result' }
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 tools/ace_usb/wizard_backend.py result --operation $OperationId --wait-seconds 30"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Read the saved result later; do not repeat recovery' }
```

**Expected final result:** `CANCELLED_SAFE`, `ready: true`, and `service_restored: true`.
For `RECOVERING`, repeat only the `result` query in section 1. Do not repeat `recover`.
The backend refuses recovery after a flash attempt. Do not change its record.
Other faults can need manual maintenance. Ordinary installation steps cannot guarantee recovery.
See [advanced ACE maintenance](ace-firmware.md#uncertain-results-and-recovery).

<a id="after-an-interrupted-installation"></a>
## 3. Interrupted host installation

Read the last result in the original window or private log:

| Result | Meaning and action |
| --- | --- |
| `installed: true`, `ready_samples: 3` | The installer reported success. Check current status and physical functions. |
| `Automatic rollback VERIFIED` | Installation failed, but restoration was verified. Resolve the original failure before trying again. |
| `automatic rollback FAILED` | Restoration is incomplete. Keep idle and save the `Backup ID` and error. |
| SSH disconnect without a final result | Success and failure are unknown. Do not resend. Read status and establish the original process result. |

ACE `SUCCEEDED` is not host installation success. Do not roll back while the original installation is still running.

## 4. Update this project

1. Finish printing and filament operations. Stop drying, set every heater target to zero, and cool below 50 °C.
2. If feed assist remains active, unload that channel normally. Wait for completion and cool again. Existing installations need not empty every slot.
3. Save private configuration and backups. Download the complete new archive and extract it into a new folder.
4. Guided users select menu 1 in the new package. Current parameters are preserved by default.
5. Manual users begin at [manual installation](installation.md) step 2 in a new window and directory. Check the plan, then install once.
6. Do not copy an old JSON file wholesale into the new template. Do not set `apply_existing_settings` to `true` merely to update. See [configuration](configuration.md) for an intentional parameter change.

Unknown edits to core files are refused, not merged automatically. Preserve those edits instead of overwriting them to bypass a check.

## 5. Save private backups

Managed backups are under `/userdata/ultimate-u1-ace-link/backups/`.
After section 1 connects, copy them into a new unique folder under your computer's Documents folder:
```powershell
$BackupDir = Join-Path ([Environment]::GetFolderPath('MyDocuments')) ('Ultimate-U1-ACE-private-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0,8))
New-Item -ItemType Directory -Path $BackupDir | Out-Null
scp.exe -O -r "${PrinterTarget}:/userdata/ultimate-u1-ace-link/backups" "$BackupDir"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Backup copy failed' }
Write-Host $BackupDir
```

Keep the displayed path. Backups can contain private configuration; do not publish them.
This is a host-file backup, not an ACE firmware, U1 firmware, or complete device image.

## 6. Roll back the latest host installation

Use only after the original installer has finished, with no unresolved ACE transaction and the machine idle and cold.
Initialize and query with section 1 first. Normal rollback requires ACE ready, drying off, and feed assist off.
Confirm that the latest backup is the intended target, then run once:
```powershell
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 installer.py rollback"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Rollback failed; preserve the error' }
```

Expect `rolled_back: true` and the backup identifier. Query status again using section 1.
After rollback to a pre-integration state, `managed: false` and `ace_version: null` can be normal.
Files changed manually after installation cause refusal to protect later edits. Do not delete them blindly.

## 7. Host recovery when Klipper cannot become ready

**This does not recover ACE firmware or bypass active printing or an unresolved ACE transaction.**
First establish that the original installer has finished, movement has stopped, drying/heating are off, and actual temperatures are below 50 °C.
If the screen or independent observation cannot establish cooling and no movement, stop.
An unreadable network state is not evidence of idle hardware.

If section 1 can reach SSH but normal `status` cannot become ready, this command bypasses the initial online-ready check.
It retains firmware, backup, file-hash, ACE-transaction, and post-restoration ready checks:
```powershell
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 installer.py rollback --offline-recovery --confirm-idle-and-cold"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Recovery failed; preserve the error' }
```

For `No managed installation; offline recovery requires an explicit backup ID`, use only the exact `Backup ID` from this failed operation:
```powershell
$BackupId = (Read-Host 'Enter the backup identifier from this failed installation').Trim()
if ($BackupId -notmatch '^[0-9]{8}T[0-9]{12}Z$') { throw 'STOP: Invalid backup identifier' }
ssh.exe $PrinterTarget "cd '$RemoteDir' && python3 installer.py rollback --backup '$BackupId' --offline-recovery --confirm-idle-and-cold"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Recovery failed; do not try another backup at random' }
```

Expect `rolled_back: true`. If restoration still fails, stop and preserve the error. Do not try different backup identifiers at random.
This page cannot guarantee automatic recovery from every firmware, file, or hardware fault. No AI guess is needed to decide whether to stop.

## U1 firmware updates are separate

Save private configuration and backups before updating U1. Confirm that the target firmware is supported by this project.
Follow [U1 preparation](u1-preparation.md), then check Wi-Fi, Advanced Mode, and Root Access after reboot.
Reinstall only if this project's check accepts the target. Host-file restoration cannot roll back U1 or ACE firmware.
