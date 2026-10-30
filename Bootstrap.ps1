# SPDX-License-Identifier: GPL-3.0-only
# Developed with OpenAI Codex. Loaded by Install.ps1; no action runs on import.
$script:BootstrapImage = @{
    Name = 'U1_extended_2.0.0-paxx12-24_upgrade.bin'
    Url = 'https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware/releases/download/v2.0.0-paxx12-24/U1_extended_2.0.0-paxx12-24_upgrade.bin'
    Size = [long]253893376
    Sha256 = '42dcf59e06ef0f6fab20745883322f24ddd3c1a09da07449b356dd9dab943070'
}
$bootstrapMessages = @{
    boot_title = @('准备 U1 稳定固件 U 盘', 'Prepare the U1 stable-firmware USB drive')
    boot_scope = @('只准备未修改的上游原版扩展固件 v24；不会刷写 ACE，也不会远程刷写打印机。', 'This prepares the unchanged upstream v24 image. It does not flash ACE or update the printer remotely.')
    boot_no_format = @('不会格式化磁盘，不会删除其他文件。请选择已格式化为 FAT32 的可移动 U 盘。', 'No disk is formatted. Other files are not deleted. Select a removable USB drive that already uses FAT32.')
    boot_no_drives = @('未找到可移动 U 盘。请插入 FAT32 U 盘，再重新运行向导。', 'No removable USB drive was found. Insert a FAT32 USB drive before running the wizard again.')
    boot_drive_line = @('  {0}. {1}  卷标：{2}  容量：{3} GB  格式：{4}', '  {0}. {1}  Label: {2}  Size: {3} GB  Format: {4}')
    boot_drive_prompt = @('请输入目标 U 盘的编号；输入 0 退出', 'Enter the USB drive number; 0 exits')
    boot_drive_invalid = @('请输入列表中的编号，或输入 0 退出。', 'Enter a number from the list, or 0 to exit.')
    boot_target = @('即将复制到 {0}（卷标：{1}）。请确认这是目标 U 盘。', 'The file will be copied to {0} (label: {1}). Make sure this is the intended USB drive.')
    boot_target_question = @('是否只向这个 U 盘复制固件文件？', 'Copy the firmware file to this USB drive?')
    boot_target_yes = @('确认这个 U 盘，开始准备', 'Confirm this USB drive and continue')
    boot_cancel = @('取消，退出', 'Cancel and exit')
    boot_reparse = @('发现重解析点或链接路径。为避免写错位置，已停止。', 'A linked or redirected path was found. Preparation has stopped to avoid writing to the wrong location.')
    boot_invalid_drive = @('目标盘信息无效。请重新连接 U 盘。', 'The target drive information is invalid. Reconnect the USB drive.')
    boot_system_drive = @('不能选择 Windows 系统盘。', 'The Windows system drive cannot be selected.')
    boot_not_removable = @('目标不是可移动磁盘。只接受可移动 U 盘。', 'The target is not a removable disk. Only removable USB drives are accepted.')
    boot_not_fat32 = @('目标 U 盘不是 FAT32。本向导不会格式化；请另选已准备好的 FAT32 U 盘。', 'The USB drive is not FAT32. This wizard does not format disks. Use a prepared FAT32 USB drive.')
    boot_drive_changed = @('U 盘已断开或换成另一块盘。已停止，请重新开始。', 'The USB drive was disconnected or replaced. Preparation has stopped. Start again.')
    boot_space = @('U 盘空间不足，至少需要 253893376 字节可用空间。请另选 U 盘。', 'The USB drive needs at least 253893376 free bytes. Use another USB drive.')
    boot_cache_invalid = @('已缓存的固件未通过校验。请删除此文件后重试：{0}', 'The cached firmware failed verification. Delete this file before another attempt: {0}')
    boot_cached = @('已找到校验正确的缓存，无须重新下载。', 'The cached firmware passed verification. No new download is needed.')
    boot_downloading = @('正在下载约 254 MB 的稳定固件，请稍候。', 'Downloading approximately 254 MB of stable firmware. Please wait.')
    boot_download_failed = @('固件下载失败。请检查网络后重试；尚未写入 U 盘。', 'Firmware download failed. Check the network before another attempt. The USB drive has not been written.')
    boot_hash_failed = @('固件大小或 SHA-256 校验失败。已停止，未把该文件交给打印机。', 'The firmware size or SHA-256 check failed. Preparation has stopped. Do not use this file on the printer.')
    boot_conflict = @('U 盘存在同名但内容不同的文件，已停止且未覆盖：{0}', 'A different file already has this name on the USB drive. It was not overwritten: {0}')
    boot_copying = @('正在复制并校验 U 盘文件。请勿拔出 U 盘。', 'Copying and verifying the USB file. Do not remove the USB drive.')
    boot_usb_reuse = @('U 盘内已有校验正确的同名固件，无须重复复制。', 'The USB drive already contains the verified firmware. No new copy is needed.')
    boot_ready = @('U 盘已准备好，文件大小和 SHA-256 均正确。', 'The USB drive is ready. File size and SHA-256 checks passed.')
    boot_step1 = @('第 1 步：确认打印已结束，关闭加热和烘干。安全弹出 U 盘，再插入 U1。', 'Step 1: End printing. Stop heating and drying. Safely eject the USB drive. Insert it into U1.')
    boot_update_path = @('屏幕：Settings → About → Firmware Version → Local Update。', 'Screen: Settings > About > Firmware Version > Local Update.')
    boot_select_image = @('选择 {0}，确认升级，等待自动重启。升级时不要断电或拔 U 盘。', 'Select {0}. Confirm the update. Wait for the restart. Do not disconnect power or remove the USB drive during the update.')
    boot_updated_question = @('打印机是否已完成升级并自动重启？', 'Has the update completed and the printer restarted?')
    boot_step2 = @('第 2 步：屏幕 Settings → Maintenance → Advanced Mode，开启后重新启动打印机。', 'Step 2: Open Settings > Maintenance > Advanced Mode. Enable it. Restart the printer.')
    boot_advanced_question = @('Advanced Mode 是否已开启，并已完成重新启动？', 'Is Advanced Mode enabled, with the restart completed?')
    boot_step3 = @('第 3 步：屏幕 Settings → Maintenance → Root Access。阅读说明并向下滚动，同意后选择 Open。', 'Step 3: Open Settings > Maintenance > Root Access. Read the notice. Scroll down to agree. Select Open.')
    boot_root_question = @('Root Access 现在是否显示 Open？', 'Does Root Access now show Open?')
    boot_step4 = @('第 4 步：确认 Wi-Fi 已连接；升级后可能需要重新连接。记下屏幕上的当前 IP 地址。', 'Step 4: Check Wi-Fi. Reconnect if necessary. Note the current IP address shown on the screen.')
    boot_wifi_question = @('Wi-Fi 是否已连接，并已记下当前 IP 地址？', 'Is Wi-Fi connected, and have you noted the current IP address?')
    boot_done_yes = @('已完成，继续', 'Completed, continue')
    boot_pause_no = @('还未完成，退出后再继续', 'Not completed, exit for now')
}
foreach ($entry in $bootstrapMessages.GetEnumerator()) { $script:WizardMessages[$entry.Key] = $entry.Value }

function Assert-BootstrapPlainPath {
    param([string]$Path)
    $current = [IO.Path]::GetFullPath($Path)
    while ($current) {
        $item = Get-Item -LiteralPath $current -Force -ErrorAction SilentlyContinue
        if ($null -ne $item) {
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw (New-WizardException 'boot_reparse') }
        }
        $parent = Split-Path $current -Parent
        if ($parent -eq $current) { break }
        $current = $parent
    }
}

function Get-BootstrapUsbCandidates {
    return @(Get-CimInstance -ClassName Win32_LogicalDisk -Filter 'DriveType=2' | Sort-Object DeviceID)
}

function Get-BootstrapDriveInfo {
    param([string]$DeviceId)
    return @(Get-CimInstance -ClassName Win32_LogicalDisk | Where-Object { $_.DeviceID -eq $DeviceId })
}

function Get-BootstrapUsbRoot {
    param($Drive)
    return ($Drive.DeviceID + '\')
}

function Test-BootstrapUsbTarget {
    param($Drive, [string]$SystemDrive = $env:SystemDrive)
    if (-not $Drive -or $Drive.DeviceID -notmatch '^[A-Za-z]:$' -or [long]$Drive.Size -le 0 -or
        $Drive.VolumeSerialNumber -notmatch '^[A-Fa-f0-9]{8}$') { throw (New-WizardException 'boot_invalid_drive') }
    if ($Drive.DeviceID -eq $SystemDrive) { throw (New-WizardException 'boot_system_drive') }
    if ([int]$Drive.DriveType -ne 2) { throw (New-WizardException 'boot_not_removable') }
    if ($Drive.FileSystem -ne 'FAT32') { throw (New-WizardException 'boot_not_fat32') }
    Assert-BootstrapPlainPath (Get-BootstrapUsbRoot $Drive)
}

function Get-BootstrapFreshDrive {
    param($Selected)
    $found = @(Get-BootstrapDriveInfo $Selected.DeviceID)
    if ($found.Count -ne 1) { throw (New-WizardException 'boot_drive_changed') }
    $fresh = $found[0]
    Test-BootstrapUsbTarget $fresh
    if ($fresh.VolumeSerialNumber -ne $Selected.VolumeSerialNumber -or [long]$fresh.Size -ne [long]$Selected.Size) {
        throw (New-WizardException 'boot_drive_changed')
    }
    return $fresh
}

function Test-BootstrapImageFile {
    param([string]$Path)
    Assert-BootstrapPlainPath $Path
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }
    if ((Get-Item -LiteralPath $Path).Length -ne $script:BootstrapImage.Size) { return $false }
    return ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -eq $script:BootstrapImage.Sha256)
}

function Invoke-BootstrapDownload {
    param([string]$Destination)
    $oldTls = [Net.ServicePointManager]::SecurityProtocol
    try {
        [Net.ServicePointManager]::SecurityProtocol = $oldTls -bor [Net.SecurityProtocolType]::Tls12
        $ProgressPreference = 'SilentlyContinue'
        Invoke-WebRequest -UseBasicParsing -Uri $script:BootstrapImage.Url -OutFile $Destination
    } catch { throw (New-WizardException 'boot_download_failed') }
    finally { [Net.ServicePointManager]::SecurityProtocol = $oldTls }
}

function Get-BootstrapFirmware {
    param([string]$CacheRoot)
    if (-not $CacheRoot) { $CacheRoot = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'Ultimate-U1-ACE-link/firmware' }
    Assert-BootstrapPlainPath $CacheRoot
    [void](New-Item -ItemType Directory -Force -Path $CacheRoot)
    $destination = Join-Path $CacheRoot $script:BootstrapImage.Name
    if (Test-Path -LiteralPath $destination) {
        if (-not (Test-BootstrapImageFile $destination)) { throw (New-WizardException 'boot_cache_invalid' @($destination)) }
        Write-Host (Get-WizardText 'boot_cached') -ForegroundColor Cyan
        return $destination
    }
    $partial = Join-Path $CacheRoot ($script:BootstrapImage.Name + '.' + [guid]::NewGuid().ToString('N') + '.part')
    try {
        Assert-BootstrapPlainPath $partial
        if (Test-Path -LiteralPath $partial) { throw (New-WizardException 'boot_conflict' @($partial)) }
        Write-Host (Get-WizardText 'boot_downloading') -ForegroundColor Cyan
        Invoke-BootstrapDownload $partial
        if (-not (Test-BootstrapImageFile $partial)) { throw (New-WizardException 'boot_hash_failed') }
        Assert-BootstrapPlainPath $destination
        [IO.File]::Move($partial, $destination)
        return $destination
    } finally {
        if (Test-Path -LiteralPath $partial) { Remove-Item -LiteralPath $partial -Force }
    }
}

function Copy-BootstrapFirmware {
    param([string]$Source, $Drive)
    if (-not (Test-BootstrapImageFile $Source)) { throw (New-WizardException 'boot_hash_failed') }
    $fresh = Get-BootstrapFreshDrive $Drive
    $root = Get-BootstrapUsbRoot $fresh
    $destination = Join-Path $root $script:BootstrapImage.Name
    Assert-BootstrapPlainPath $destination
    if (Test-Path -LiteralPath $destination) {
        if (-not (Test-BootstrapImageFile $destination)) { throw (New-WizardException 'boot_conflict' @($destination)) }
        Write-Host (Get-WizardText 'boot_usb_reuse') -ForegroundColor Cyan
        return $destination
    }
    if ([long]$fresh.FreeSpace -lt $script:BootstrapImage.Size) { throw (New-WizardException 'boot_space') }
    $partial = Join-Path $root ('.ultimate-u1-' + [guid]::NewGuid().ToString('N') + '.part')
    try {
        Assert-BootstrapPlainPath $partial
        Write-Host (Get-WizardText 'boot_copying') -ForegroundColor Cyan
        [IO.File]::Copy($Source, $partial, $false)
        if (-not (Test-BootstrapImageFile $partial)) { throw (New-WizardException 'boot_hash_failed') }
        [void](Get-BootstrapFreshDrive $Drive)
        Assert-BootstrapPlainPath $destination
        [IO.File]::Move($partial, $destination)
        if (-not (Test-BootstrapImageFile $destination)) { throw (New-WizardException 'boot_hash_failed') }
        return $destination
    } finally {
        if (Test-Path -LiteralPath $partial) { Remove-Item -LiteralPath $partial -Force }
    }
}

function Start-U1Bootstrap {
    param([string]$BundleRoot)
    Write-Host ''
    Write-Host (Get-WizardText 'boot_title') -ForegroundColor Cyan
    Write-Host (Get-WizardText 'boot_scope')
    Write-Host (Get-WizardText 'boot_no_format') -ForegroundColor Yellow
    $drives = @(Get-BootstrapUsbCandidates)
    if (-not $drives.Count) { throw (New-WizardException 'boot_no_drives') }
    for ($i = 0; $i -lt $drives.Count; $i++) {
        $drive = $drives[$i]
        $label = [string]$drive.VolumeName -replace '[\x00-\x1f\x7f]', '?'
        Write-Host (Get-WizardText 'boot_drive_line' @(($i + 1), $drive.DeviceID, $label, [Math]::Round($drive.Size / 1GB, 1), $drive.FileSystem))
    }
    while ($true) {
        $answer = Read-Host (Get-WizardText 'boot_drive_prompt')
        if ($answer -eq '0') { return $false }
        $selected = 0
        if ([int]::TryParse($answer, [ref]$selected) -and $selected -ge 1 -and $selected -le $drives.Count) { break }
        Write-Host (Get-WizardText 'boot_drive_invalid') -ForegroundColor Yellow
    }
    $drive = $drives[$selected - 1]
    Test-BootstrapUsbTarget $drive
    Write-Host (Get-WizardText 'boot_target' @($drive.DeviceID, $drive.VolumeName)) -ForegroundColor Yellow
    if (-not (Read-WizardChoice (Get-WizardText 'boot_target_question') (Get-WizardText 'boot_target_yes') (Get-WizardText 'boot_cancel'))) { return $false }
    $source = Get-BootstrapFirmware
    [void](Copy-BootstrapFirmware $source $drive)
    Write-Host (Get-WizardText 'boot_ready') -ForegroundColor Green
    Write-Host ''
    Write-Host (Get-WizardText 'boot_step1') -ForegroundColor Yellow
    Write-Host (Get-WizardText 'boot_update_path') -ForegroundColor Cyan
    Write-Host (Get-WizardText 'boot_select_image' @($script:BootstrapImage.Name)) -ForegroundColor Red
    if (-not (Read-WizardChoice (Get-WizardText 'boot_updated_question') (Get-WizardText 'boot_done_yes') (Get-WizardText 'boot_pause_no'))) { return $false }
    foreach ($pair in @(@('boot_step2', 'boot_advanced_question'), @('boot_step3', 'boot_root_question'), @('boot_step4', 'boot_wifi_question'))) {
        Write-Host ''
        Write-Host (Get-WizardText $pair[0]) -ForegroundColor Cyan
        if (-not (Read-WizardChoice (Get-WizardText $pair[1]) (Get-WizardText 'boot_done_yes') (Get-WizardText 'boot_pause_no'))) { return $false }
    }
    return $true
}
