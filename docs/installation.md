# Manual installation: copy one command block at a time

[简体中文](installation.zh-CN.md) · [Guided installation](quick-start.md) · [Recovery](update-and-rollback.md)

This route does not run the Windows wizard. It runs the readable `installer.py` and ACE maintenance tools on U1.
You need no programming knowledge, Windows Python, AI assistant, or NFC keys.
You must be able to copy complete blocks, enter the requested values, and check the printer screen.
Use `START-HERE.cmd` if you prefer the guided route.

> [!CAUTION]
> **Do not copy old SnapAce `filament_feed.py` or `extruder.py` onto U1 firmware 2.0.**
> **Use SnapAce for hardware instructions only. Do not mix installer, manifest, and payload versions.**

This procedure applies to the current complete package. Use [matching instructions for retained archives](install-options.md).
The offline manuals are `MANUAL-INSTALL.html` and `MANUAL-INSTALL.zh-CN.html`.

## 1. Prepare the machine before opening commands

1. Finish printing and all filament operations. Turn heating and drying off. Wait until each nozzle and the bed are below **50 °C**.
2. For a first installation, use normal device controls to remove filament from all four heads and ACE inlets. Unloading can heat the nozzles again. Turn heating and drying off afterward; cool below 50 °C again. For an existing integration update, keep the current filament positions.
3. Follow [U1 firmware and access setup](u1-preparation.md). Install **`2.0.0-paxx12-24`**, enable **Advanced Mode**, and set **Root Access** to **Open**.
4. **Turn off ACE and U1. Disconnect both power supplies.** Follow the [SnapAce hardware guide](https://github.com/BlackFrogKok/SnapAce#pinout-and-wiring) for the **ACE Pro Gen 1** cable and matching four PTFE paths.
5. After wiring, start the devices. Connect U1 and the computer to the same local network. Record the address on the U1 Wi-Fi page.
6. Keep power and USB stable. The steps below upload the public tools before U1 checks ACE firmware. **Do not complete a separate ACE flashing tutorial first.**

Stop if the U1 version, access settings, ACE generation, or wiring do not match. ACE 2 Pro is not supported.
The installer sets **External**, saves original files, and verifies services. No manual reader selection or U1 OpenRFID key setup is needed.
[OpenCubic](https://github.com/Jupsi/OpenCubic) supplies the supported NFC decoders. This project synchronizes the data with U1; see [the support table](nfc.md).

<a id="prepare-windows-powershell"></a>
## 2. Download, extract, and open PowerShell

1. Download the complete ZIP from [the current package entry](../README.md). Do not download individual `.py` files.
2. Right-click the ZIP and select **Extract All**. Open the `Ultimate-U1-ACE-link` folder containing `installer.py`.
3. Click the File Explorer address bar. Copy the full folder path for the prompt below.
4. Open Start, search for **Windows PowerShell**, and open a normal window. Administrator mode is not needed.
5. Paste every code block below into this **Windows PowerShell** window. Copy one complete block, press Enter, and wait. Do not copy the three backticks.
6. If a red `STOP` or error appears, **stop the later steps**. Read the corresponding instructions. Do not repeat a write merely because success was not shown.

To check the ZIP, run `Get-FileHash -LiteralPath 'full path to your ZIP' -Algorithm SHA256`.
Keep the quotes. Compare the result with the same archive in [SHA256SUMS](../downloads/SHA256SUMS).
Stop and download the complete package again if the values differ.
You can inspect the source in Notepad without changing it. Keep private backups outside the project folder.

Copy this complete block. At its prompt, paste the extracted folder path:
```powershell
$ErrorActionPreference = 'Stop'
$ProjectDir = (Read-Host 'Paste the full extracted folder path containing installer.py').Trim().Trim('"')
Set-Location -LiteralPath $ProjectDir
$ProjectDir = (Get-Location).Path
if (-not (Test-Path -LiteralPath (Join-Path $ProjectDir 'installer.py') -PathType Leaf)) {
    throw 'STOP: Select the folder containing installer.py'
}
$Manifest = Get-Content -LiteralPath (Join-Path $ProjectDir 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if (@($Manifest.files).Count -ne 4 -or @($Manifest.files.payload | Select-Object -Unique).Count -ne 4) {
    throw 'STOP: Expected four unique payload entries'
}
foreach ($Entry in $Manifest.files) {
    if ($Entry.payload -notin @('payload/ace.py','payload/filament_feed.py','payload/filament_detect.py','payload/extruder.py')) {
        throw 'STOP: Unexpected payload path'
    }
    if ((Get-FileHash -LiteralPath (Join-Path $ProjectDir $Entry.payload) -Algorithm SHA256).Hash -ne $Entry.sha256) {
        throw 'STOP: Payload checksum mismatch'
    }
}
Write-Host ('Package version: ' + $Manifest.release)
```

**Expected:** the package version appears without `STOP`. The four payload hashes match the manifest.

<a id="set-connection-variables"></a>
<a id="confirm-the-connection"></a>
## 3. Connect to U1

Windows needs **OpenSSH Client**. If `ssh.exe` or `scp.exe` is missing, open Windows Optional Features → View features / Add a feature → search for OpenSSH → install **OpenSSH Client**.
Then reopen PowerShell and begin at step 2. Do not install OpenSSH Server.

Copy the block. Enter only the numeric address from the screen, for example `192.0.2.10`.
Do not add `http://`, a port, or a web path. The example is not your printer address.
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
```

**Expected:** the output includes `uid=0(root)`.
On first connection, SSH can ask `Are you sure you want to continue connecting`.
This is first-contact trust. This procedure has not independently verified the fingerprint.
Use a trusted local network. Compare the address with the U1 screen, then type `yes` and press Enter.
Stop if a previously recorded host key changed unexpectedly. Do not remove that warning to bypass an identity check.
Password entry shows no characters or asterisks. Use your changed password, or see [the upstream factory SSH credentials](https://snapmakeru1-extended-firmware.pages.dev/ssh_access).
Do not put the password in a command or settings file.

<a id="4-transfer-the-project"></a>
## 4. Transfer only the required public files

This block copies a fixed file list into a temporary folder, then uploads it to a unique U1 directory.
It does not upload unrelated backups or a `.git` directory from your work folder.
```powershell
$TransferDir = Join-Path ([IO.Path]::GetTempPath()) ('UltimateU1Manual-' + [guid]::NewGuid().ToString('N'))
$PublicFiles = @('installer.py','manifest.json','LICENSE','THIRD_PARTY.md','SOURCES.json',
    'payload/ace.py','payload/filament_feed.py','payload/filament_detect.py','payload/extruder.py',
    'tools/ace_usb/wizard_backend.py','tools/ace_usb/ace_iap.py','tools/ace_usb/protocol.py',
    'tools/ace_usb/prepare_profile.py','tools/ace_usb/fetch_firmware.py',
    'tools/ace_usb/images.json','tools/ace_usb/device-profile.json','config/settings.example.json')
foreach ($Name in $PublicFiles) {
    $Source = Get-Item -LiteralPath (Join-Path $ProjectDir $Name)
    if ($Source.PSIsContainer -or ($Source.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw 'STOP: Expected a regular package file'
    }
    $Destination = Join-Path $TransferDir $Name
    New-Item -ItemType Directory -Force -Path (Split-Path $Destination -Parent) | Out-Null
    Copy-Item -LiteralPath $Source.FullName -Destination $Destination
}
$RemoteDir = '/userdata/ultimate-u1-ace-stage-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0,8)
scp.exe -O -r "$TransferDir" "${PrinterTarget}:$RemoteDir"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Upload failed' }
Write-Host ('Printer: ' + $PrinterAddress)
Write-Host ('RemoteDir: ' + $RemoteDir)
ssh.exe $PrinterTarget "ls '$RemoteDir/installer.py' '$RemoteDir/manifest.json' '$RemoteDir/tools/ace_usb/wizard_backend.py'"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Uploaded files are missing' }
```

**Expected:** three remote file paths appear without an error.
Copy the displayed **Printer** and **RemoteDir** lines into your private notes. Recovery after a closed window needs them.
**Keep this PowerShell window open.** Later blocks use its variables.
If you closed it, use [the independent status procedure](update-and-rollback.md#read-installation-status) before starting a new transfer or write.

<a id="ace-firmware"></a>
## 5. Check or prepare ACE firmware

This section uses the same controlled backend as the bilingual wizard.
**Do not edit a device profile, NFC key file, or firmware JSON.**
U1 downloads and checks the pinned upstream images. U1 needs internet access to GitHub. The package contains no firmware binary.
The check temporarily stops and restores Klipper. It sends no load or unload command, but initialization can trigger ACE behavior. Keep hands clear of the rollers.

Copy this block first. It defines later operations and reads the previous ACE transaction.
If that transaction is active, it only reads results; it does not repeat a flash:
```powershell
function Read-U1Json([string]$Command) {
    $Raw = & ssh.exe -o ConnectTimeout=15 $PrinterTarget "cd '$RemoteDir' && $Command"
    if ($LASTEXITCODE -ne 0) { throw 'STOP: Remote command failed. Do not repeat a write.' }
    return (($Raw -join "`n") | ConvertFrom-Json)
}
function Show-AceResult($Result) {
    $Result | Format-List state,code,operation,source_firmware,boot_firmware,target_firmware,ready,service_restored,flash_attempted,needs_material_review | Out-Host
}
function Wait-AceResult($Result) {
    for ($Attempt = 0; $Attempt -lt 60; $Attempt++) {
        Show-AceResult $Result
        if ($Result.state -notin @('PREPARING','STARTING','RUNNING','RECOVERING')) { return $Result }
        if ($Result.operation -notmatch '^[a-f0-9]{32}$') { throw 'STOP: Invalid operation identifier' }
        $Result = Read-U1Json ('python3 tools/ace_usb/wizard_backend.py result --operation ' + $Result.operation + ' --wait-seconds 30')
    }
    throw 'STOP: Still waiting. Read the saved result later; do not repeat a write.'
}
function Confirm-AceMaterial($Result) {
    if ($Result.needs_material_review) {
        $Result.material_changes | ConvertTo-Json -Depth 8 | Out-Host
        if ((Read-Host 'Compare material changes with the spools. Enter YES if correct, otherwise STOP') -cne 'YES') { throw 'STOP: Material review not accepted' }
    }
}
$AceFirmwareAccepted = $false
$AceResult = Wait-AceResult (Read-U1Json 'python3 tools/ace_usb/wizard_backend.py result')
if ($AceResult.state -eq 'UNSUPPORTED') { throw 'STOP: Unsupported ACE; do not change version evidence' }
if ($AceResult.state -notin @('NONE','PREPARED','ALREADY_TARGET','FAILED_SAFE','CANCELLED_SAFE','SUCCEEDED')) {
    throw 'STOP: An unresolved ACE transaction needs recovery'
}
Confirm-AceMaterial $AceResult
```

| Displayed `state` | Action |
| --- | --- |
| `NONE` | No prior transaction. Choose A or B below. |
| `SUCCEEDED`, `PREPARED`, `ALREADY_TARGET`, `CANCELLED_SAFE` | Still choose A or B for the current device. An old success does not identify the current ACE. |
| `FAILED_SAFE` | Resolve network, cooling, or device conditions. Use B for fresh preparation. |
| `UNSUPPORTED` | Stop. Do not change evidence or force an unsupported source. |
| `NEEDS_ATTENTION`, `ERROR`, or a failed query | Stop installation. Use [ACE interruption recovery](update-and-rollback.md#ace-interruption). |

For material changes, `field` names the item. `before` is the old value; `after` is the new value.
Suffixes `_0`, `_1`, `_2`, and `_3` refer to slots 1, 2, 3, and 4. Four-item arrays use the same slot order.
Enter `YES` only when the new data matches the spools. No change means no material confirmation prompt.

### A. The exact firmware is already installed and NFC works

Run this block only if you know this ACE has **OpenCubic CFW 1.1.1 / `CV1.3.863`**. Then continue to step 6.
The string `CV1.3.863` alone does not identify every community build. If unsure, choose B.
```powershell
if ($AceResult.state -notin @('NONE','ALREADY_TARGET','CANCELLED_SAFE','SUCCEEDED')) {
    throw 'STOP: Use fresh preparation for this ACE state; do not keep unverified firmware'
}
if ($AceResult.state -ne 'NONE' -and (-not $AceResult.ready -or -not $AceResult.service_restored)) {
    throw 'STOP: Complete preparation or recovery before keeping existing firmware'
}
if ((Read-Host 'Enter KEEP only for known OpenCubic CFW 1.1.1 with working NFC') -cne 'KEEP') { throw 'STOP: Existing build not confirmed' }
$AceFirmwareAccepted = $true
```

### B. The current firmware is unknown, or an update is needed

Confirm idle state, all heater targets at zero, all actual temperatures below 50 °C, drying off, and no NFC or filament operation.
If an existing integration still has feed assist active, use normal U1 Unload for that channel. Wait for completion and cooling.
Do not empty every slot merely to update an existing installation.
Copy this block and wait for download, probing, and restoration:
```powershell
$AceResult = Wait-AceResult (Read-U1Json 'python3 tools/ace_usb/wizard_backend.py prepare')
if ($AceResult.state -notin @('PREPARED','ALREADY_TARGET') -or -not $AceResult.ready -or -not $AceResult.service_restored) {
    throw 'STOP: ACE preparation did not pass. Read the state table before continuing.'
}
Confirm-AceMaterial $AceResult
```

For `ALREADY_TARGET`, **do not flash**. Confirm the exact CFW source and working NFC, then use block A. Stop if you cannot confirm them.
For `PREPARED`, confirm **`V1.3.856` / boot `V1.0.1` → `CV1.3.863`**, then use the next block.
Stop for every other result. No forced path is provided for other source versions.

> [!CAUTION]
> **The next block updates ACE firmware. Run it once.**
> **The checked stock `1.3.863` file is a reference, not your device backup. Physical stock rollback is untested.**
> Enter `UPDATE` only after accepting that limit. Keep power and USB connected. Do not repeat the command or use another control window.
```powershell
if ($AceResult.state -ne 'PREPARED' -or $AceResult.source_firmware -ne 'V1.3.856' -or
    $AceResult.boot_firmware -ne 'V1.0.1' -or $AceResult.target_firmware -ne 'CV1.3.863' -or
    $AceResult.operation -notmatch '^[a-f0-9]{32}$') { throw 'STOP: This update path is not prepared' }
if ((Read-Host 'Accept the untested stock rollback limit. Enter UPDATE for one firmware write') -cne 'UPDATE') { throw 'STOP: Update cancelled' }
$AceOperation = $AceResult.operation
$AceResult = Wait-AceResult (Read-U1Json ('python3 tools/ace_usb/wizard_backend.py start --operation ' + $AceOperation + ' --confirm-flash --accept-untested-rollback'))
if ($AceResult.state -ne 'SUCCEEDED' -or -not $AceResult.ready -or -not $AceResult.service_restored) {
    throw 'STOP: Update result is uncertain. Do not flash again or restart printing.'
}
Confirm-AceMaterial $AceResult
$AceFirmwareAccepted = $true
```

**Expected:** `state: SUCCEEDED`, `ready: true`, and `service_restored: true`. Review any changed material values against the spools.
Firmware success does not install the host integration. Continue to step 6.
If the connection fails or the result is uncertain, use [recovery](update-and-rollback.md#ace-interruption). Do not repeat the update block.

<a id="5-check-before-installation"></a>
## 6. Enter initial settings and check the plan

Read [the A/B/C path guide](configuration.md). **A is the main retract distance, B is the fast-feed distance, and C is forward take-up.**
For a first installation, enter reviewed initial A and B values for your four physical paths.
This review is not the later installed movement test. All slots share these settings. B must be less than A.
Stop if you have no reviewed path measurements or equivalent-layout record. Software or AI cannot guess a safe distance.
Initial C is 0. Fast feed is 200, final approach is 50, and retraction is 80. Test each slot after installation before enabling take-up.
For an existing integration, this procedure keeps its values, including C. It does not request new A/B values or overwrite them with the template.

First installation requires empty ACE inlets and empty heads. Existing installations keep their filament positions.
The machine must be idle and cold, with drying and feed assist off.
The block generates the settings JSON from your answers. **You do not edit JSON punctuation.**
```powershell
if (-not $AceFirmwareAccepted) { throw 'STOP: Complete the ACE firmware step first' }
$Status = Read-U1Json 'python3 installer.py status'
$Status | ConvertTo-Json -Depth 8 | Out-Host
if ($Status.existing_ace -isnot [bool]) { throw 'STOP: Invalid host status' }
$Settings = Get-Content -LiteralPath (Join-Path $TransferDir 'config/settings.example.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$Settings.apply_existing_settings = $false
$Settings.forward_takeup_length = 0
if (-not $Status.existing_ace) {
    if (@($Status.serial_candidates).Count -ne 1) { throw 'STOP: One unique ACE interface is required' }
    $A = 0; $B = 0
    if (-not [int]::TryParse((Read-Host 'Enter reviewed initial A retract distance in whole mm, 2 to 2499'), [ref]$A) -or $A -lt 2 -or $A -gt 2499) { throw 'STOP: Invalid A' }
    if (-not [int]::TryParse((Read-Host 'Enter reviewed initial B fast distance in whole mm, greater than 0 and less than A'), [ref]$B) -or $B -lt 1 -or $B -ge $A) { throw 'STOP: Invalid B' }
    $Settings.feed_length = $A
    $Settings.retract_length = $A
    $Settings.fast_load_length = $B
}
if ((Read-Host 'Enter YES after reviewing all four paths, speeds, and later per-slot tests') -cne 'YES') { throw 'STOP: Settings review not accepted' }
$Settings.calibrated_acknowledged = $true
$SettingsPath = Join-Path $TransferDir 'config/settings.local.json'
[IO.File]::WriteAllText($SettingsPath, ($Settings | ConvertTo-Json -Depth 8), (New-Object System.Text.UTF8Encoding($false)))
scp.exe -O "$SettingsPath" "${PrinterTarget}:$RemoteDir/config/settings.local.json"
if ($LASTEXITCODE -ne 0) { throw 'STOP: Settings upload failed' }
$Plan = Read-U1Json 'python3 installer.py check --settings config/settings.local.json'
if ($Plan.compatible -ne $true -or $Plan.read_only -ne $true -or $Plan.calibration_acknowledged -ne $true) {
    throw 'STOP: Host check did not pass'
}
$Plan.effective_settings | Format-List | Out-Host
```

**Expected:** no `STOP`, and `effective_settings` matches your intended values.
Before first installation, `managed: false` and `ace_version: null` are normal. Existing settings must match the prior configuration.
`filament_detection: external` is the plan; the read-only check has not applied it yet.
If unknown core edits or incompatible versions are refused, preserve the originals and stop. Do not overwrite files to bypass a refusal.

## 7. Install once and check the result

Check the summary and physical state, then copy this block. Enter `INSTALL` to confirm one installation.
Wait for completion. Do not repeat the command:
```powershell
if (-not $AceFirmwareAccepted -or $Plan.compatible -ne $true) { throw 'STOP: Complete the checks first' }
if ((Read-Host 'If the summary is correct and the device is idle and cold, enter INSTALL once') -cne 'INSTALL') { throw 'STOP: Installation cancelled' }
$InstallResult = Read-U1Json 'python3 installer.py install --settings config/settings.local.json'
$InstallResult | ConvertTo-Json -Depth 8 | Out-Host
if ($InstallResult.installed -ne $true -or $InstallResult.ready_samples -lt 3) {
    throw 'STOP: Installation success is not confirmed'
}
Write-Host ('Backup: ' + $InstallResult.backup)
$FinalStatus = Read-U1Json 'python3 installer.py status'
$FinalStatus | ConvertTo-Json -Depth 8 | Out-Host
```

**Expected:** `installed: true`, `ready_samples: 3`, and final status `klipper_state: ready`, `managed: true`, `filament_detection: external`.
Both `internal_rfid_enabled` and `openrfid_running` must be `false`. Save the displayed `Backup` identifier.
A temporary Klipper disconnected message during service restart is expected. Start testing only after confirmed success.

## 8. Test one slot at a time

Follow [daily operation and acceptance](daily-use.md) for each of the four slots: insert and wait for short intake/NFC → U1 Load → Unload → Load again without reinsertion.
Compare brand, type, and color. Confirm material remains after unloading. Keep hands clear. Stop for slipping, a jam, or an abnormal result.
Then use [configuration](configuration.md) to calibrate C. Do not treat 1250, 1150, or 300 as universal distances.
Do not schedule unattended printing before all slots pass.

**Failure or disconnection:** use [independent status and recovery](update-and-rollback.md). Do not immediately repeat the install block.
These procedures do not establish all-tag NFC coverage, ACE internal calibration, or stock rollback. See [validation limits](validation.md).
