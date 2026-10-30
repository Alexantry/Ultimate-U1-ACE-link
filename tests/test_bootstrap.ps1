# SPDX-License-Identifier: GPL-3.0-only
# Offline tests: fake CIM, fake download, and temporary folders instead of USB.
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
. (Join-Path $repo 'Install.ps1') -LibraryOnly
. (Join-Path $repo 'Bootstrap.ps1')
$passed = 0
function Assert-True { param($Value, [string]$Message); if (-not $Value) { throw $Message } }
function Assert-Throws {
    param([scriptblock]$Body, [string]$Id)
    $caught = $null
    try { & $Body } catch { $caught = $_.Exception }
    Assert-True ($null -ne $caught) 'Expected refusal'
    if ($Id) { Assert-True ($caught.Data['WizardMessageId'] -eq $Id) ('Wrong refusal: ' + $caught.Message) }
}
function Test-Case { param([string]$Name, [scriptblock]$Body); & $Body; $script:passed += 1; [Console]::WriteLine('PASS ' + $Name) }

Test-Case 'pinned_upstream_release_metadata' {
    Assert-True ($script:BootstrapImage.Name -eq 'U1_extended_2.0.0-paxx12-24_upgrade.bin') 'Wrong name'
    Assert-True ($script:BootstrapImage.Size -eq 253893376) 'Wrong release size'
    Assert-True ($script:BootstrapImage.Sha256 -eq '42dcf59e06ef0f6fab20745883322f24ddd3c1a09da07449b356dd9dab943070') 'Wrong release hash'
    Assert-True ($script:BootstrapImage.Url -eq 'https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/releases/download/v2.0.0-paxx12-24/U1_extended_2.0.0-paxx12-24_upgrade.bin') 'Wrong URL'
    $bytes = [IO.File]::ReadAllBytes((Join-Path $repo 'Bootstrap.ps1'))
    Assert-True ($bytes[0] -eq 239 -and $bytes[1] -eq 187 -and $bytes[2] -eq 191) 'Missing UTF-8 BOM'
}

$script:testRoot = Join-Path ([IO.Path]::GetTempPath()) ('U1BootstrapTests-' + [guid]::NewGuid().ToString('N'))
[void](New-Item -ItemType Directory -Path $script:testRoot)
$script:usbRoot = Join-Path $script:testRoot 'usb'
[void](New-Item -ItemType Directory -Path $script:usbRoot)
$payload = [Text.Encoding]::UTF8.GetBytes('synthetic firmware, no device data')
$script:fixtureSource = Join-Path $script:testRoot 'source.bin'
[IO.File]::WriteAllBytes($script:fixtureSource, $payload)
$script:BootstrapImage.Size = [long]$payload.Length
$script:BootstrapImage.Sha256 = (Get-FileHash -LiteralPath $script:fixtureSource -Algorithm SHA256).Hash.ToLowerInvariant()
$script:drive = [pscustomobject]@{ DeviceID = 'Z:'; DriveType = 2; FileSystem = 'FAT32'; Size = [long]1GB; FreeSpace = [long]512MB; VolumeSerialNumber = 'ABCDEF12'; VolumeName = 'OFFLINE TEST' }
$script:downloadCount = 0
$script:badDownload = $false
function Get-BootstrapUsbRoot { param($Drive); return $script:usbRoot }
function Get-BootstrapDriveInfo { param([string]$DeviceId); return $script:drive }
function Get-BootstrapUsbCandidates { return @($script:drive) }
function Invoke-BootstrapDownload {
    param([string]$Destination)
    $script:downloadCount += 1
    if ($script:badDownload) {
        # Same size, different bytes: exercise SHA-256, not only the size check.
        [IO.File]::WriteAllBytes($Destination, (New-Object byte[] ([int]$script:BootstrapImage.Size)))
        return
    }
    [IO.File]::Copy($script:fixtureSource, $Destination, $false)
}
function New-FakeDrive {
    param([hashtable]$Changes = @{})
    $values = @{}
    foreach ($property in $script:drive.PSObject.Properties) { $values[$property.Name] = $property.Value }
    foreach ($key in $Changes.Keys) { $values[$key] = $Changes[$key] }
    return [pscustomobject]$values
}
function New-TestFolder {
    $path = Join-Path $script:testRoot ([guid]::NewGuid().ToString('N'))
    [void](New-Item -ItemType Directory -Path $path)
    return $path
}

try {
    Test-Case 'reject_system_drive' { Assert-Throws { Test-BootstrapUsbTarget (New-FakeDrive @{ DeviceID = 'C:' }) 'C:' } 'boot_system_drive' }
    Test-Case 'reject_nonremovable_drive' { Assert-Throws { Test-BootstrapUsbTarget (New-FakeDrive @{ DriveType = 3 }) 'C:' } 'boot_not_removable' }
    Test-Case 'reject_nonfat32_drive' { Assert-Throws { Test-BootstrapUsbTarget (New-FakeDrive @{ FileSystem = 'NTFS' }) 'C:' } 'boot_not_fat32' }
    Test-Case 'reject_missing_volume_identity' { Assert-Throws { Test-BootstrapUsbTarget (New-FakeDrive @{ VolumeSerialNumber = '' }) 'C:' } 'boot_invalid_drive' }
    Test-Case 'accept_identified_removable_fat32_drive' { Test-BootstrapUsbTarget $script:drive 'C:' }
    Test-Case 'download_verified_before_atomic_cache_name' {
        $cache = New-TestFolder
        $before = $script:downloadCount
        $file = Get-BootstrapFirmware $cache
        Assert-True (Test-BootstrapImageFile $file) 'Cache verification failed'
        Assert-True ($script:downloadCount -eq $before + 1) 'Wrong download count'
        Assert-True (@(Get-ChildItem -LiteralPath $cache -Filter '*.part').Count -eq 0) 'Partial remained'
        [void](Get-BootstrapFirmware $cache)
        Assert-True ($script:downloadCount -eq $before + 1) 'Valid cache downloaded again'
    }
    Test-Case 'bad_download_never_becomes_final_firmware' {
        $cache = New-TestFolder
        $script:badDownload = $true
        try { Assert-Throws { Get-BootstrapFirmware $cache } 'boot_hash_failed' }
        finally { $script:badDownload = $false }
        Assert-True (@(Get-ChildItem -LiteralPath $cache -Force).Count -eq 0) 'Bad download left a usable file'
    }
    Test-Case 'invalid_existing_cache_is_not_overwritten' {
        $cache = New-TestFolder
        $file = Join-Path $cache $script:BootstrapImage.Name
        [IO.File]::WriteAllText($file, 'keep this different file')
        $before = $script:downloadCount
        Assert-Throws { Get-BootstrapFirmware $cache } 'boot_cache_invalid'
        Assert-True ([IO.File]::ReadAllText($file) -eq 'keep this different file' -and $script:downloadCount -eq $before) 'Bad cache was overwritten'
    }
    Test-Case 'copy_verifies_and_keeps_unrelated_files' {
        $script:usbRoot = New-TestFolder
        $other = Join-Path $script:usbRoot 'unrelated.txt'
        [IO.File]::WriteAllText($other, 'untouched')
        $copied = Copy-BootstrapFirmware $script:fixtureSource $script:drive
        Assert-True (Test-BootstrapImageFile $copied) 'USB checksum failed'
        Assert-True ([IO.File]::ReadAllText($other) -eq 'untouched') 'Unrelated file changed'
        [void](Copy-BootstrapFirmware $script:fixtureSource $script:drive)
        Assert-True (@(Get-ChildItem -LiteralPath $script:usbRoot -Force).Count -eq 2) 'Unexpected files created'
    }
    Test-Case 'same_name_different_file_is_not_overwritten' {
        $script:usbRoot = New-TestFolder
        $file = Join-Path $script:usbRoot $script:BootstrapImage.Name
        [IO.File]::WriteAllText($file, 'existing different firmware')
        Assert-Throws { Copy-BootstrapFirmware $script:fixtureSource $script:drive } 'boot_conflict'
        Assert-True ([IO.File]::ReadAllText($file) -eq 'existing different firmware') 'Conflict overwritten'
    }
    Test-Case 'insufficient_space_fails_before_copy' {
        $script:usbRoot = New-TestFolder
        $free = $script:drive.FreeSpace
        $script:drive.FreeSpace = 1
        try { Assert-Throws { Copy-BootstrapFirmware $script:fixtureSource $script:drive } 'boot_space' }
        finally { $script:drive.FreeSpace = $free }
        Assert-True (@(Get-ChildItem -LiteralPath $script:usbRoot -Force).Count -eq 0) 'Copied onto full target'
    }
    Test-Case 'changed_volume_rejected_before_copy' {
        $script:usbRoot = New-TestFolder
        $selected = New-FakeDrive @{ VolumeSerialNumber = '11111111' }
        Assert-Throws { Copy-BootstrapFirmware $script:fixtureSource $selected } 'boot_drive_changed'
        Assert-True (@(Get-ChildItem -LiteralPath $script:usbRoot -Force).Count -eq 0) 'Changed volume was written'
    }
    Test-Case 'bad_source_rejected_before_usb_write' {
        $script:usbRoot = New-TestFolder
        $bad = Join-Path $script:testRoot 'bad.bin'
        [IO.File]::WriteAllText($bad, 'wrong')
        Assert-Throws { Copy-BootstrapFirmware $bad $script:drive } 'boot_hash_failed'
        Assert-True (@(Get-ChildItem -LiteralPath $script:usbRoot -Force).Count -eq 0) 'Invalid source written'
    }
    Test-Case 'real_local_junction_rejected' {
        $target = New-TestFolder
        $junction = Join-Path $script:testRoot 'junction'
        [void](New-Item -ItemType Junction -Path $junction -Target $target)
        try {
            Assert-Throws { Assert-BootstrapPlainPath (Join-Path $junction 'firmware.bin') } 'boot_reparse'
        } finally { [IO.Directory]::Delete($junction) }
        Assert-True (Test-Path -LiteralPath $target) 'Junction target changed'
    }
    Test-Case 'broken_local_junction_is_also_rejected' {
        $target = New-TestFolder
        $junction = Join-Path $script:testRoot 'broken-junction'
        [void](New-Item -ItemType Junction -Path $junction -Target $target)
        [IO.Directory]::Delete($target)
        try { Assert-Throws { Assert-BootstrapPlainPath (Join-Path $junction 'firmware.bin') } 'boot_reparse' }
        finally { [IO.Directory]::Delete($junction) }
    }

    $script:answers = New-Object 'Collections.Generic.Queue[string]'
    $script:messages = New-Object 'Collections.Generic.List[string]'
    function Read-Host { param([string]$Prompt); if (-not $script:answers.Count) { throw 'Unexpected prompt' }; return $script:answers.Dequeue() }
    function Write-Host {
        [CmdletBinding(PositionalBinding=$false)]
        param([Parameter(Position=0, ValueFromRemainingArguments=$true)]$Arguments, $ForegroundColor)
        $script:messages.Add(($Arguments -join ' '))
    }
    $originalGetFirmware = (Get-Command Get-BootstrapFirmware).ScriptBlock
    $script:prepareCount = 0
    function Get-BootstrapFirmware { param([string]$CacheRoot); $script:prepareCount += 1; return $script:fixtureSource }
    Test-Case 'drive_selection_cancel_does_not_download_or_write' {
        $script:usbRoot = New-TestFolder
        $script:answers.Enqueue('0')
        Assert-True (-not (Start-U1Bootstrap $repo)) 'Cancel ignored'
        Assert-True ($script:prepareCount -eq 0 -and @(Get-ChildItem -LiteralPath $script:usbRoot -Force).Count -eq 0) 'Cancelled preparation wrote files'
    }
    Test-Case 'target_confirmation_cancel_does_not_download_or_write' {
        $script:usbRoot = New-TestFolder
        foreach ($answer in @('1', '2')) { $script:answers.Enqueue($answer) }
        Assert-True (-not (Start-U1Bootstrap $repo)) 'Target cancellation ignored'
        Assert-True ($script:prepareCount -eq 0 -and @(Get-ChildItem -LiteralPath $script:usbRoot -Force).Count -eq 0) 'Unconfirmed target written'
    }
    Test-Case 'english_usb_and_all_screen_confirmations_complete' {
        $script:usbRoot = New-TestFolder
        $script:WizardLanguage = 'en'; $script:messages.Clear()
        foreach ($answer in @('1', '1', '1', '1', '1', '1')) { $script:answers.Enqueue($answer) }
        Assert-True (Start-U1Bootstrap $repo) 'Completed bootstrap failed'
        Assert-True ($script:prepareCount -eq 1 -and $script:answers.Count -eq 0) 'Wrong number of bootstrap prompts'
        Assert-True (($script:messages -join ' ') -notmatch '[\u4e00-\u9fff]') 'English bootstrap contains Chinese'
        Assert-True (Test-BootstrapImageFile (Join-Path $script:usbRoot $script:BootstrapImage.Name)) 'Final USB file invalid'
    }
    Test-Case 'screen_step_can_exit_after_safe_usb_copy' {
        $script:usbRoot = New-TestFolder
        foreach ($answer in @('1', '1', '2')) { $script:answers.Enqueue($answer) }
        Assert-True (-not (Start-U1Bootstrap $repo)) 'Screen cancellation ignored'
        Assert-True (Test-BootstrapImageFile (Join-Path $script:usbRoot $script:BootstrapImage.Name)) 'Prepared file lost on cancellation'
    }
    Set-Item -Path Function:Get-BootstrapFirmware -Value $originalGetFirmware
} finally {
    $resolved = [IO.Path]::GetFullPath($script:testRoot)
    $tempBase = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    if ($resolved.StartsWith($tempBase, [StringComparison]::OrdinalIgnoreCase) -and (Split-Path $resolved -Leaf) -match '^U1BootstrapTests-[a-f0-9]{32}$') {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
[Console]::WriteLine('All ' + $passed + ' offline bootstrap tests passed.')
