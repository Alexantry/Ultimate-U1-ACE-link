# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Ultimate U1-ACE link contributors; developed with OpenAI Codex.
# Windows PowerShell 5.1. No local Python, stored passwords, or additional modules.
[CmdletBinding()]
param([switch]$LibraryOnly, [switch]$FromLauncher)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

$script:WizardLanguage = 'zh'
$script:WizardMessages = @{
    native_start = @('无法启动系统 SSH 工具。', 'Cannot start the Windows SSH tool.')
    bundle_regular = @('安装文件不是普通文件。请重新下载官方项目 ZIP 并完整解压。', 'An installation file is not a regular file. Download the project ZIP again. Extract all files.')
    bundle_incomplete = @('安装包清单不完整。请重新下载。', 'The package list is incomplete. Download the project ZIP again.')
    bundle_unknown = @('安装包清单包含未知文件。已停止。', 'The package list contains an unknown file. Installation has stopped.')
    bundle_hash = @('安装文件校验失败。请重新下载，勿混用不同版本文件。', 'A file checksum failed. Download the complete project again. Do not mix files from different releases.')
    bundle_duplicate = @('安装包清单包含重复文件。', 'The package list contains duplicate files.')
    lengths_invalid = @('长度超出本向导范围：退回长度 2 至 2499 mm，快速段必须大于 0 且小于退回长度。', 'A must be 2 to 2499 mm. B must be greater than zero and less than A.')
    continue = @('继续', 'Continue')
    exit = @('退出', 'Exit')
    choice_prompt = @('请输入 1 或 2', 'Enter 1 or 2')
    choice_invalid = @('请输入数字 1 或 2。', 'Enter the number 1 or 2.')
    length_range = @('请输入 {0} 至 {1} 的整数，单位毫米。输入 0 可退出。', 'Enter a whole number from {0} to {1}, in millimeters. Enter 0 to exit.')
    length_cancelled = @('用户取消：未提供已确认的管路长度。', 'Cancelled. Confirmed tube lengths were not supplied.')
    hint_firmware = @('固件版本或文件不匹配。请核对图文手册中的前置版本；不要强行覆盖现有改动。', 'The firmware version or files do not match. Check the required version in the guide. Do not overwrite unreviewed changes.')
    hint_idle = @('机器仍在工作或冷却。请在屏幕结束操作、关闭烘干和加热，等温度低于 50°C 后再试。', 'The printer is busy or hot. End the current operation on the screen. Stop heating and drying. Wait until temperatures are below 50 C.')
    hint_serial = @('未找到唯一可用的 ACE。请核对 ACE 电源、USB 转接线和图文手册的连接方法。', 'One usable ACE was not found. Check ACE power. Check the USB adapter and the wiring guide.')
    hint_ready = @('打印机后台尚未就绪。请查看屏幕报错，并确认 Advanced Mode 已开启、Root Access 为 Open。', 'The printer software is not ready. Check the printer screen. Enable Advanced Mode. Set Root Access to Open.')
    hint_dependency = @('打印机缺少前置组件。请按图文手册完成基础项目安装，不要在电脑上安装 Python。', 'A printer dependency is missing. Complete the prerequisite installation in the guide. Do not install Python on your computer.')
    hint_empty = @('首次安装要求四个 ACE 入口和四个打印头均无耗材。先在屏幕正常退料，再将耗材完全退出 ACE 入口；仅点退料不等于入口已清空。', 'First installation needs empty ACE inlets and print heads. Use normal Unload on the screen. Then remove filament fully from all ACE inlets. Unload alone does not clear the inlets.')
    hint_general = @('请保留此窗口和诊断文件，按 START-HERE.html 的故障处理说明继续。', 'Keep this window and the diagnostic file. Follow the recovery instructions in START-HERE.en.html.')
    unsafe_directory = @('不安全的远程目录。', 'The remote directory is not safe.')
    remote_error = @('{0}', '{0}')
    invalid_result = @('未收到完整的检查结果。不要重复点击安装；请保留诊断文件。', 'The complete result was not received. Do not repeat installation. Keep the diagnostic file.')
    settings_title = @('本次实际参数：', 'Settings for this installation:')
    settings_retract = @('  退回 ACE：{0} mm，速度 {1} mm/s', '  Return to ACE: {0} mm at {1} mm/s')
    settings_fast = @('  上料快速段：{0} mm，速度 {1} mm/s', '  Fast loading segment: {0} mm at {1} mm/s')
    settings_sensor = @('  接近打印头：传感器检测停止，速度 {0} mm/s', '  Approach to the print head: sensor stop at {0} mm/s')
    settings_takeup = @('  退料后向打印机送回：{0} mm', '  Forward feed after unloading: {0} mm')
    settings_external = @('  材料信息来源：ACE（自动设置 External）', '  Material source: ACE (External is set automatically)')
    stage_prepare = @('准备', 'Preparation')
    title = @('Ultimate U1-ACE link 安装向导', 'Ultimate U1-ACE link Setup Wizard')
    credit = @('由 OpenAI Codex 协助开发。U1 更新由屏幕确认；ACE 更新需检查通过并单独确认。', 'Developed with OpenAI Codex. U1 updates need screen confirmation. ACE updates need passed checks and separate confirmation.')
    warning_title = @('重要：不要复制旧版 SnapAce 软件文件！', 'IMPORTANT: Do not copy old SnapAce software files.')
    warning_replaces = @('本项目替代旧版 SnapAce 的软件安装步骤。', 'This project replaces the old SnapAce software installation steps.')
    warning_core = @('不要把旧版 filament_feed.py 或 extruder.py 覆盖到 U1 2.0。', 'Do not copy old filament_feed.py or extruder.py files onto U1 2.0.')
    warning_hardware = @('上游 SnapAce 指南仅用于参考硬件连接。', 'Use the upstream SnapAce guide only for hardware connections.')
    guide_first = @('先完成 U1 v24、Advanced Mode、Root Access 和接线准备。ACE 固件可在接下来的向导中完成。', 'Prepare U1 v24, Advanced Mode, Root Access, and wiring first. The following wizard can prepare ACE firmware.')
    prerequisites_question = @('U1 指定固件、访问开关及 ACE 第一代接线是否已准备好？', 'Are the required U1 firmware, access settings, and ACE Gen 1 wiring ready?')
    prerequisites_yes = @('已完成，开始检查', 'Yes, start the checks')
    prerequisites_no = @('尚未完成，退出看图文手册', 'No, exit and read the guide')
    cold_notice = @('安装期间不要打印、上下料或操作滚筒；请关闭烘干和加热并等温度低于 50°C。', 'Do not print or move filament during installation. Stop drying and heating. Wait until temperatures are below 50 C.')
    cold_question = @('机器现在是否空闲、冷却且烘干已停止？', 'Is the printer idle and cold, with drying stopped?')
    yes = @('是', 'Yes')
    no_exit = @('否，退出', 'No, exit')
    ssh_missing = @('Windows 缺少 OpenSSH 客户端。请在设置 > 应用 > 可选功能中添加 OpenSSH 客户端，再运行本向导。', 'The Windows OpenSSH Client is missing. Add it in Settings > Apps > Optional features. Then run this wizard again.')
    ip_prompt = @('请输入打印机 Wi-Fi 页面显示的 IP 地址', 'Enter the IP address shown on the printer Wi-Fi page')
    ip_invalid = @('只输入屏幕上的数字地址；不要加 http://、斜线或用户名。', 'Enter only the address from the screen. Do not add http://, a slash, or a username.')
    ssh_notice = @('连接时可能出现英文提示：', 'SSH connection prompts:')
    password_notice = @('  password: 输入打印机的 Root 密码后按回车；屏幕不显示字符或星号，这是正常的。', '  password: Enter the printer root password. Press Enter. No characters or asterisks appear. This is normal.')
    fingerprint_notice = @('  yes/no: 仅在自己的可信局域网中，逐字核对打印机屏幕 IP 后，才确认首次连接并输入 yes。这是首次信任，并非独立校验了指纹；不确定则按 Ctrl+C。', '  yes/no: On your own trusted local network, compare the IP with the printer screen. Enter yes only to trust this first connection. This does not independently verify the fingerprint. If unsure, press Ctrl+C.')
    fingerprint_changed = @('  若出现 REMOTE HOST IDENTIFICATION HAS CHANGED，请停止。不要删除已存指纹或关闭身份校验来继续；先按手动说明核实变化原因。', '  If REMOTE HOST IDENTIFICATION HAS CHANGED appears, stop. Do not delete the saved fingerprint or disable checks to continue. Follow the manual to investigate the change.')
    password_repeat = @('每次连接可能再次要求密码；向导不会保存密码，也不会跳过主机身份校验。', 'Each connection can request the password again. The wizard does not save passwords or bypass host identity checks.')
    stage_upload = @('上传安装文件', 'File transfer')
    step_upload = @('[1/4] 正在传送安装文件。此时尚未修改打印机配置。', '[1/4] Transferring installation files. Printer settings have not changed.')
    upload_failed = @('文件传送未完成。请核对 IP、Root Access、密码和网络；不要关闭主机身份校验。', 'File transfer failed. Check the IP, Root Access, password, and network. Do not disable host identity checks.')
    stage_read = @('读取现有设置', 'Reading existing settings')
    installer_mismatch = @('安装器版本不一致。请重新解压完整项目 ZIP。', 'Installer versions do not match. Extract the complete project ZIP again.')
    existing_found = @('已发现 ACE 配置。本次保留现有长度、速度、串口和补收参数。', 'Existing ACE settings were found. Your lengths, speeds, serial port, and slack-removal settings will be kept.')
    serial_ambiguous = @('未找到唯一 ACE 串口。请核对接线，并只连接一台 ACE 后重试。', 'One unique ACE serial port was not found. Check the wiring. Connect only one ACE before another attempt.')
    fresh_empty = @('这是首次安装。四个 ACE 入口和四个打印头必须均无耗材。先正常退料，再将耗材完全退出 ACE 入口。', 'This is the first installation. All four ACE inlets and all four print heads must be empty. Unload normally. Then remove filament fully from the ACE inlets.')
    empty_question = @('是否已完成正常退料，并清空上述八处位置？', 'Have you completed normal unloading and cleared all eight positions?')
    lengths_guide = @('请对照 START-HERE.html 的 A、B 长度图。没有量好时请输入 0 退出，切勿猜测。', 'Use the A/B diagram in START-HERE.en.html. Enter 0 to exit if measurements are not ready. Do not guess.')
    length_a = @('A：U1 完成热端释放后，ACE 的主回抽距离；耗材尖端须留在 ACE 后方管内。', 'A: The main ACE retract distance after U1 releases the filament from the hotend. The tip must remain inside the tube behind ACE.')
    length_a_prompt = @('A 退回距离（毫米；输入 0 退出）', 'A: Return distance in millimeters (0 exits)')
    length_b = @('B：基础快速送料长度，须在到达打印头前结束；退料后回送的长度由程序自动扣除。', 'B: The base fast-feed length. It must end before the print head. The software deducts any forward feed after unloading.')
    length_b_prompt = @('B 快速送料距离（毫米；输入 0 退出）', 'B: Fast feed distance in millimeters (0 exits)')
    speeds_notice = @('已预填速度：快送 200、接近打印头 50、退料 80 mm/s。退料后补送默认关闭。', 'Preset speeds: fast feed 200, head approach 50, and retract 80 mm/s. Forward feed after unloading is disabled by default.')
    calibration_question = @('是否已审查本次初始长度和速度，并准备在安装后按手册进行实机校准？已有安装将保留现有参数。', 'Have you reviewed the initial lengths and speeds? Will you do the supervised calibration after installation? Existing installations keep their current settings.')
    calibration_yes = @('已审查；安装后按手册校准', 'Reviewed; I will follow the calibration guide')
    calibration_no = @('不确定，退出', 'Unsure, exit')
    settings_upload_failed = @('参数传送失败。尚未开始安装，请检查网络后重新运行。', 'Settings transfer failed. Installation has not started. Check the network before another attempt.')
    stage_check = @('只读检查', 'Read-only checks')
    step_check = @('[2/4] 正在检查固件、耗材状态、温度、备份条件和文件兼容性。', '[2/4] Checking firmware, filament state, temperatures, backup conditions, and file compatibility.')
    state_changed = @('检查结果与起始状态不一致。已停止；请重新运行，勿继续操作耗材。', 'The state changed after the first check. Installation has stopped. Keep filament still before another attempt.')
    checks_passed = @('检查通过。下一步会备份原文件、安装适配，并重新启动打印服务。', 'Checks passed. The next step backs up the original files, installs the integration, and restarts the print service.')
    install_question = @('是否按以上参数开始安装？', 'Start installation with these settings?')
    install_yes = @('开始安装', 'Start installation')
    install_no = @('取消，保持当前配置', 'Cancel and keep the current configuration')
    stage_install = @('安装与验证', 'Installation and verification')
    step_install = @('[3/4] 正在安装和验证，可能需要数分钟。请勿关闭窗口或操作打印机。', '[3/4] Installing and verifying. This can take several minutes. Keep this window open. Do not operate the printer.')
    install_incomplete = @('尚未取得完整的安装成功结果。请勿重复安装。', 'A complete installation success result was not received. Do not repeat installation.')
    step_done = @('[4/4] 安装成功，后台已恢复就绪。', '[4/4] Installation succeeded. The printer software is ready.')
    backup_id = @('备份编号：{0}', 'Backup ID: {0}')
    protected_notice = @('原配置和材料识别所需的私人文件均由安装器保护。', 'The installer protects your existing configuration and private material-recognition files.')
    next_test = @('接下来请按 START-HERE.html 完成首次受控上料检查。向导不发送进退料命令；服务恢复时仍须让手远离运动部件。', 'Next, use START-HERE.en.html for the first supervised loading check. The wizard does not send load or unload commands. Keep hands away from moving parts when services restart.')
    log_local = @('诊断文件（仅保存在本机）：{0}', 'Diagnostic file (saved only on this computer): {0}')
    stopped = @('已停止：{0}', 'Stopped: {0}')
    uncertain_install = @('安装可能已经开始。不要重复运行安装或断电；先按图文手册的恢复说明检查状态。', 'Installation might have started. Do not repeat installation or switch off power. Follow the recovery instructions in START-HERE.en.html first.')
    backups_location = @('原文件备份在打印机 /userdata/ultimate-u1-ace-link/backups/。', 'Original-file backups are on the printer at /userdata/ultimate-u1-ace-link/backups/.')
    remote_location = @('本次打印机安装目录：{0}', 'Printer staging directory: {0}')
    log_failed = @('无法补写诊断文件，请保留窗口上的提示。', 'The diagnostic file could not be updated. Keep the messages in this window.')
    log_path = @('诊断文件：{0}', 'Diagnostic file: {0}')
    cleanup_failed = @('本机临时目录未清理：{0}', 'Local temporary directory was not removed: {0}')
    unexpected_error = @('向导遇到意外错误。请保留诊断文件，并查看 START-HERE.html 的故障处理说明。', 'The wizard encountered an unexpected error. Keep the diagnostic file. Read the recovery instructions in START-HERE.en.html.')
    startup_failed = @('向导未能继续。请保留此窗口，并查看 START-HERE.html 的故障处理说明。', 'The wizard could not continue. Keep this window. Read the recovery instructions in START-HERE.en.html.')
    close_prompt = @('按回车关闭窗口', 'Press Enter to close this window')
    task_title = @('请选择下一步：', 'Choose the next step:')
    task_ready = @('  1. U1 已准备好，安装或更新 ACE 适配', '  1. U1 is ready: install or update ACE integration')
    task_usb = @('  2. 准备 U1 固件 U 盘，并查看屏幕操作指引', '  2. Prepare U1 firmware USB and follow the screen instructions')
    task_manual = @('  3. 手动安装：打开本地说明并退出', '  3. Manual installation: open the local guide and exit')
    task_ace = @('  4. ACE 固件检查、更新或查看上次更新结果', '  4. Check or update ACE firmware; inspect the last update')
    task_prompt = @('请输入 1、2、3 或 4', 'Enter 1, 2, 3, or 4')
    task_invalid = @('请输入列表中的数字 1、2、3 或 4。', 'Enter 1, 2, 3, or 4 from the list.')
    manual_opened = @('已在浏览器打开手动安装说明；向导不会连接打印机。', 'The manual installation guide is open in your browser. The wizard will not contact the printer.')
    manual_missing = @('本地手动说明缺失。请重新下载并完整解压项目 ZIP，再选菜单 3。', 'The local manual is missing. Download and extract the complete project ZIP. Then select menu 3 again.')
    ace_maintenance_done = @('ACE 固件流程已结束。本次没有安装或更改 U1 适配。需要安装适配时，重新打开向导并选择菜单 1。', 'The ACE firmware workflow is complete. U1 integration was not installed or changed. To install the integration, open the wizard again and select menu 1.')
    stage_bootstrap = @('准备固件 U 盘', 'Preparing firmware USB')
    stage_ace = @('ACE 固件准备与结果检查', 'ACE firmware preparation and result checks')
    existing_firmware_kept = @('已有安装默认保留 ACE 固件；需要主动检查或查看上次更新时使用菜单 4。', 'Existing installations keep ACE firmware by default. Use menu 4 to check it or inspect the last update.')
}

function Get-WizardText {
    param([string]$Id, [object[]]$Values = @())
    if (-not $script:WizardMessages.ContainsKey($Id)) { throw ('Missing wizard message: ' + $Id) }
    $index = 0
    if ($script:WizardLanguage -eq 'en') { $index = 1 }
    $message = $script:WizardMessages[$Id][$index]
    if ($Values.Count) { return ($message -f $Values) }
    return $message
}

function New-WizardException {
    param([string]$Id, [object[]]$Values = @())
    $exception = New-Object System.InvalidOperationException (Get-WizardText $Id $Values)
    $exception.Data['WizardMessageId'] = $Id
    return $exception
}

function Get-WizardExceptionSummary {
    param([Exception]$Exception)
    if ($Exception.Data.Contains('WizardMessageId')) { return $Exception.Message }
    return (Get-WizardText 'unexpected_error')
}

function Select-WizardLanguage {
    Write-Host ''
    Write-Host 'Language / 语言' -ForegroundColor Cyan
    Write-Host '  1. 中文'
    Write-Host '  2. English'
    while ($true) {
        $choice = Read-Host '1 / 2'
        if ($choice -eq '1') { $script:WizardLanguage = 'zh'; return }
        if ($choice -eq '2') { $script:WizardLanguage = 'en'; return }
        Write-Host 'Enter 1 or 2 / 请输入 1 或 2。'
    }
}

function Select-WizardTask {
    Write-Host ''
    Write-Host (Get-WizardText 'task_title') -ForegroundColor Cyan
    foreach ($id in @('task_ready', 'task_usb', 'task_manual', 'task_ace')) { Write-Host (Get-WizardText $id) }
    while ($true) {
        $choice = Read-Host (Get-WizardText 'task_prompt')
        if ($choice -in @('1', '2', '3', '4')) { return $choice }
        Write-Host (Get-WizardText 'task_invalid') -ForegroundColor Yellow
    }
}

function Open-WizardManual {
    param([string]$BundleRoot)
    $name = 'MANUAL-INSTALL.zh-CN.html'
    if ($script:WizardLanguage -eq 'en') { $name = 'MANUAL-INSTALL.html' }
    $path = Join-Path $BundleRoot $name
    if (-not (Test-Path -LiteralPath $path)) { throw (New-WizardException 'manual_missing') }
    $file = Get-Item -LiteralPath $path -Force
    if ($file.PSIsContainer -or ($file.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw (New-WizardException 'bundle_regular')
    }
    Start-Process -FilePath $file.FullName
    Write-Host (Get-WizardText 'manual_opened') -ForegroundColor Cyan
}

function Invoke-WizardBootstrap {
    param([string]$BundleRoot)
    $bootstrapPath = Join-Path $BundleRoot 'Bootstrap.ps1'
    $bootstrapFile = Get-Item -LiteralPath $bootstrapPath -Force
    if ($bootstrapFile.PSIsContainer -or ($bootstrapFile.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw (New-WizardException 'bundle_regular')
    }
    . $bootstrapPath
    return (Start-U1Bootstrap -BundleRoot $BundleRoot)
}

function Invoke-WizardAceGate {
    param([string]$BundleRoot, [string]$Ssh, [string]$Target, [string]$RemoteDir, [string]$LogFile, [bool]$AllowRecovery = $false)
    $source = Get-Item -LiteralPath (Join-Path $BundleRoot 'AceFirmware.ps1') -Force
    if ($source.PSIsContainer -or ($source.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw (New-WizardException 'bundle_regular') }
    . $source.FullName
    return (Get-AceFirmwareGate $Ssh $Target $RemoteDir $LogFile $AllowRecovery)
}

function Invoke-WizardAceSetup {
    param([string]$BundleRoot, [string]$Ssh, [string]$Target, [string]$RemoteDir, [string]$LogFile, [bool]$ForcePrepare = $false)
    $source = Get-Item -LiteralPath (Join-Path $BundleRoot 'AceFirmware.ps1') -Force
    if ($source.PSIsContainer -or ($source.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw (New-WizardException 'bundle_regular') }
    . $source.FullName
    return (Start-AceFirmwareSetup $Ssh $Target $RemoteDir $LogFile $ForcePrepare)
}

function Test-PrinterAddress {
    param([string]$Address)
    if ([string]::IsNullOrWhiteSpace($Address) -or $Address.Length -gt 253) { return $false }
    if ($Address -match '^[0-9.]+$') {
        $parts = $Address.Split('.')
        if ($parts.Count -ne 4) { return $false }
        foreach ($part in $parts) {
            if ($part -notmatch '^(0|[1-9][0-9]{0,2})$' -or [int]$part -gt 255) { return $false }
        }
        return $true
    }
    if ($Address -notmatch '^[A-Za-z0-9.-]+$') { return $false }
    foreach ($label in $Address.Split('.')) {
        if ($label.Length -gt 63 -or $label -notmatch '^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$') { return $false }
    }
    return $true
}

function ConvertTo-NativeArgument {
    param([AllowEmptyString()][string]$Value)
    # Windows command-line quoting; no cmd.exe or PowerShell evaluation.
    if ($Value -and $Value -notmatch '[\s"]') { return $Value }
    $escaped = [regex]::Replace($Value, '(\\*)"', '$1$1\"')
    $escaped = [regex]::Replace($escaped, '(\\+)$', '$1$1')
    return '"' + $escaped + '"'
}

function Invoke-WizardNative {
    param([string]$Executable, [string[]]$Arguments)
    $info = New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName = $Executable
    $info.Arguments = (($Arguments | ForEach-Object { ConvertTo-NativeArgument $_ }) -join ' ')
    $info.UseShellExecute = $false
    $info.RedirectStandardOutput = $true
    $info.StandardOutputEncoding = New-Object System.Text.UTF8Encoding($false)
    # Inherit the console for SSH fingerprint and password prompts.
    $info.RedirectStandardError = $false
    $info.RedirectStandardInput = $false
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $info
    try {
        if (-not $process.Start()) { throw (New-WizardException 'native_start') }
        $output = $process.StandardOutput.ReadToEnd()
        $process.WaitForExit()
        return [pscustomobject]@{ ExitCode = $process.ExitCode; Output = $output }
    } finally { $process.Dispose() }
}

function Get-WizardBundleFiles {
    param([string]$Root)
    $names = @('installer.py', 'manifest.json', 'LICENSE', 'THIRD_PARTY.md', 'SOURCES.json',
        'payload/ace.py', 'payload/filament_feed.py', 'payload/filament_detect.py', 'payload/extruder.py',
        'tools/ace_usb/wizard_backend.py', 'tools/ace_usb/ace_iap.py', 'tools/ace_usb/protocol.py',
        'tools/ace_usb/prepare_profile.py', 'tools/ace_usb/fetch_firmware.py',
        'tools/ace_usb/images.json', 'tools/ace_usb/device-profile.json')
    foreach ($name in $names + @('config/settings.example.json')) {
        $file = Get-Item -LiteralPath (Join-Path $Root $name)
        if ($file.PSIsContainer -or ($file.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw (New-WizardException 'bundle_regular')
        }
    }
    $manifest = Get-Content -LiteralPath (Join-Path $Root 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $expected = @('ace.py', 'filament_feed.py', 'filament_detect.py', 'extruder.py')
    if (@($manifest.files).Count -ne 4) { throw (New-WizardException 'bundle_incomplete') }
    foreach ($entry in $manifest.files) {
        if ($entry.id -notin $expected -or $entry.payload -ne ('payload/' + $entry.id)) {
            throw (New-WizardException 'bundle_unknown')
        }
        $actual = (Get-FileHash -LiteralPath (Join-Path $Root $entry.payload) -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $entry.sha256) { throw (New-WizardException 'bundle_hash') }
    }
    if (@($manifest.files.id | Select-Object -Unique).Count -ne 4) { throw (New-WizardException 'bundle_duplicate') }
    return $names
}

function New-WizardSettings {
    param([string]$Root)
    $template = Get-Content -LiteralPath (Join-Path $Root 'config/settings.example.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $settings = [ordered]@{}
    foreach ($property in $template.PSObject.Properties) { $settings[$property.Name] = $property.Value }
    $settings['apply_existing_settings'] = $false
    $settings['calibrated_acknowledged'] = $false
    $settings['forward_takeup_length'] = 0
    return $settings
}

function Set-WizardLengths {
    param($Settings, [int]$Retract, [int]$Fast)
    if ($Retract -lt 2 -or $Retract -ge 2500 -or $Fast -lt 1 -or $Fast -ge $Retract -or $Fast -ge 2500) {
        throw (New-WizardException 'lengths_invalid')
    }
    $Settings['feed_length'] = $Retract
    $Settings['retract_length'] = $Retract
    $Settings['fast_load_length'] = $Fast
    $Settings['forward_takeup_length'] = 0
}

function Write-WizardJson {
    param([string]$Path, $Value)
    [IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth 8), (New-Object System.Text.UTF8Encoding($false)))
}

function Read-WizardChoice {
    param([string]$Question, [string]$Yes = (Get-WizardText 'continue'), [string]$No = (Get-WizardText 'exit'))
    Write-Host ''
    Write-Host $Question -ForegroundColor Cyan
    Write-Host ('  1. ' + $Yes)
    Write-Host ('  2. ' + $No)
    while ($true) {
        $answer = Read-Host (Get-WizardText 'choice_prompt')
        if ($answer -eq '1') { return $true }
        if ($answer -eq '2') { return $false }
        Write-Host (Get-WizardText 'choice_invalid')
    }
}

function Read-WizardLength {
    param([string]$Question, [int]$Minimum, [int]$Maximum)
    while ($true) {
        $answer = Read-Host $Question
        $value = 0
        if ([int]::TryParse($answer, [ref]$value) -and $value -ge $Minimum -and $value -le $Maximum) { return $value }
        Write-Host (Get-WizardText 'length_range' @($Minimum, $Maximum)) -ForegroundColor Yellow
        if ($answer -eq '0') { throw (New-WizardException 'length_cancelled') }
    }
}

function Get-WizardErrorHint {
    param([string]$Detail)
    switch -Regex ($Detail) {
        'firmware|version|Firmware|hash mismatch|Unknown modified core' { return (Get-WizardText 'hint_firmware') }
        'idle|active|Heater|NFC synchronization' { return (Get-WizardText 'hint_idle') }
        'pyserial|serial.*module|dependency' { return (Get-WizardText 'hint_dependency') }
        'serial|USB|ACE.*found|ACE.*device' { return (Get-WizardText 'hint_serial') }
        'not ready|objects are missing|urlopen|Connection refused' { return (Get-WizardText 'hint_ready') }
        'empty|sensor' { return (Get-WizardText 'hint_empty') }
        default { return (Get-WizardText 'hint_general') }
    }
}

function Get-RemoteWizardCommand {
    param([string]$RemoteDir, [ValidateSet('status', 'check', 'install')][string]$Action)
    if ($RemoteDir -notmatch '^/userdata/ultimate-u1-ace-stage-[0-9]{8}-[0-9]{6}-[a-f0-9]{8}$') { throw (New-WizardException 'unsafe_directory') }
    $command = "cd '$RemoteDir' || exit 1; python3 installer.py $Action"
    if ($Action -ne 'status') { $command += ' --settings config/settings.local.json' }
    # Keep installer diagnostics in its stage directory. Never hide SSH prompts.
    $command += ' 2> wizard-' + $Action + '.err; result=$?; if [ "$result" -ne 0 ]; then cat wizard-' + $Action + '.err; fi; exit "$result"'
    return $command
}

function Invoke-WizardRemoteJson {
    param([string]$Ssh, [string]$Target, [string]$RemoteDir, [string]$Action, [string]$LogFile)
    $remoteCommand = Get-RemoteWizardCommand $RemoteDir $Action
    $result = Invoke-WizardNative $Ssh @('-o', 'ConnectTimeout=15', '-o', 'ServerAliveInterval=10', '-o', 'ServerAliveCountMax=3', $Target, $remoteCommand)
    Add-Content -LiteralPath $LogFile -Encoding UTF8 -Value ("`r`nAction: $Action; exit: " + $result.ExitCode + "`r`n" + $result.Output)
    if ($result.ExitCode -ne 0) { throw (New-WizardException 'remote_error' @((Get-WizardErrorHint $result.Output))) }
    try { return ($result.Output | ConvertFrom-Json) }
    catch { throw (New-WizardException 'invalid_result') }
}

function Show-WizardSettings {
    param($Settings)
    Write-Host ''
    Write-Host (Get-WizardText 'settings_title') -ForegroundColor Cyan
    Write-Host (Get-WizardText 'settings_retract' @($Settings.retract_length, $Settings.retract_speed))
    Write-Host (Get-WizardText 'settings_fast' @($Settings.fast_load_length, $Settings.fast_load_speed))
    Write-Host (Get-WizardText 'settings_sensor' @($Settings.sensor_load_speed))
    Write-Host (Get-WizardText 'settings_takeup' @($Settings.forward_takeup_length))
    Write-Host (Get-WizardText 'settings_external')
}

function Start-U1Wizard {
    param([string]$BundleRoot, [string]$LocalLogRoot)
    $temporary = $null
    $remoteDir = $null
    $logFile = $null
    $installStarted = $false
    $stage = (Get-WizardText 'stage_prepare')
    try {
        Select-WizardLanguage
        $stage = Get-WizardText 'stage_prepare'
        Write-Host ''
        Write-Host (Get-WizardText 'title') -ForegroundColor Cyan
        Write-Host (Get-WizardText 'credit')
        Write-Host ''
        Write-Host (Get-WizardText 'warning_title') -ForegroundColor Red
        Write-Host (Get-WizardText 'warning_replaces') -ForegroundColor Red
        Write-Host (Get-WizardText 'warning_core') -ForegroundColor Red
        Write-Host (Get-WizardText 'warning_hardware') -ForegroundColor Red
        Write-Host ''
        $task = Select-WizardTask
        if ($task -eq '3') { Open-WizardManual $BundleRoot; return 2 }
        if ($task -eq '2') {
            $stage = Get-WizardText 'stage_bootstrap'
            if (-not (Invoke-WizardBootstrap -BundleRoot $BundleRoot)) { return 2 }
            $stage = Get-WizardText 'stage_prepare'
        }
        Write-Host (Get-WizardText 'guide_first')
        if (-not (Read-WizardChoice (Get-WizardText 'prerequisites_question') (Get-WizardText 'prerequisites_yes') (Get-WizardText 'prerequisites_no'))) { return 2 }
        Write-Host (Get-WizardText 'cold_notice')
        if (-not (Read-WizardChoice (Get-WizardText 'cold_question') (Get-WizardText 'yes') (Get-WizardText 'no_exit'))) { return 2 }
        $files = @(Get-WizardBundleFiles $BundleRoot)
        $sshCommand = Get-Command ssh.exe -CommandType Application -ErrorAction SilentlyContinue
        $scpCommand = Get-Command scp.exe -CommandType Application -ErrorAction SilentlyContinue
        if (-not $sshCommand -or -not $scpCommand) { throw (New-WizardException 'ssh_missing') }
        $ssh = $sshCommand.Source; $scp = $scpCommand.Source
        do {
            $address = (Read-Host (Get-WizardText 'ip_prompt')).Trim()
            $valid = Test-PrinterAddress $address
            if (-not $valid) { Write-Host (Get-WizardText 'ip_invalid') -ForegroundColor Yellow }
        } until ($valid)
        $target = 'root@' + $address
        $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
        $nonce = [guid]::NewGuid().ToString('N').Substring(0, 8)
        $remoteDir = '/userdata/ultimate-u1-ace-stage-' + $stamp + '-' + $nonce
        $temporary = Join-Path ([IO.Path]::GetTempPath()) ('UltimateU1ACE-' + [guid]::NewGuid().ToString('N'))
        $bundle = Join-Path $temporary 'bundle'
        [void](New-Item -ItemType Directory -Path $bundle)
        foreach ($relative in $files) {
            $destination = Join-Path $bundle $relative
            [void](New-Item -ItemType Directory -Force -Path (Split-Path $destination -Parent))
            Copy-Item -LiteralPath (Join-Path $BundleRoot $relative) -Destination $destination
        }
        [void](New-Item -ItemType Directory -Path (Join-Path $bundle 'config'))
        $settingsPath = Join-Path $bundle 'config/settings.local.json'
        $settings = New-WizardSettings $BundleRoot
        Write-WizardJson $settingsPath $settings
        $logRoot = $LocalLogRoot
        if (-not $logRoot) { $logRoot = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'Ultimate-U1-ACE-link/logs' }
        [void](New-Item -ItemType Directory -Force -Path $logRoot)
        $logFile = Join-Path $logRoot ($stamp + '-' + $nonce + '.txt')
        [IO.File]::WriteAllText($logFile, "Printer: $address`r`nRemote stage: $remoteDir`r`n", (New-Object System.Text.UTF8Encoding($true)))
        Write-Host ''
        Write-Host (Get-WizardText 'ssh_notice') -ForegroundColor Cyan
        Write-Host (Get-WizardText 'password_notice')
        Write-Host (Get-WizardText 'fingerprint_notice')
        Write-Host (Get-WizardText 'fingerprint_changed') -ForegroundColor Yellow
        Write-Host (Get-WizardText 'password_repeat')
        $stage = (Get-WizardText 'stage_upload')
        Write-Host ''
        Write-Host (Get-WizardText 'step_upload') -ForegroundColor Cyan
        $copy = Invoke-WizardNative $scp @('-O', '-o', 'ConnectTimeout=15', '-r', $bundle, ($target + ':' + $remoteDir))
        if ($copy.ExitCode -ne 0) { throw (New-WizardException 'upload_failed') }
        # A previous firmware worker can still own the port while Klipper is stopped.
        # Inspect that durable result before the normal printer status check.
        $stage = Get-WizardText 'stage_ace'
        $aceGate = Invoke-WizardAceGate $BundleRoot $ssh $target $remoteDir $logFile ($task -eq '4')
        if (-not $aceGate.Continue) { return 2 }
        $aceSetupDone = $false
        if ($aceGate.ForcePrepare) {
            if (-not (Invoke-WizardAceSetup $BundleRoot $ssh $target $remoteDir $logFile $true)) { return 2 }
            $aceSetupDone = $true
        }
        # Menu 4 is ACE maintenance only. Do not enter host installation after it.
        if ($task -eq '4') {
            if (-not $aceSetupDone -and -not $aceGate.CompletedNow) {
                if (-not (Invoke-WizardAceSetup $BundleRoot $ssh $target $remoteDir $logFile)) { return 2 }
            }
            Write-Host (Get-WizardText 'ace_maintenance_done') -ForegroundColor Green
            Write-Host (Get-WizardText 'log_local' @($logFile))
            return 0
        }
        $stage = (Get-WizardText 'stage_read')
        $status = Invoke-WizardRemoteJson $ssh $target $remoteDir 'status' $logFile
        if ($status.existing_ace -isnot [bool]) { throw (New-WizardException 'installer_mismatch') }
        $existing = $status.existing_ace
        if (-not $existing -and @($status.serial_candidates).Count -ne 1) { throw (New-WizardException 'serial_ambiguous') }
        if (-not $aceSetupDone -and -not $aceGate.CompletedNow -and (-not $existing -or $aceGate.RequiresSetup)) {
            $stage = Get-WizardText 'stage_ace'
            if (-not (Invoke-WizardAceSetup $BundleRoot $ssh $target $remoteDir $logFile)) { return 2 }
            $stage = Get-WizardText 'stage_read'
            $status = Invoke-WizardRemoteJson $ssh $target $remoteDir 'status' $logFile
            if ($status.existing_ace -isnot [bool] -or $status.existing_ace -ne $existing) { throw (New-WizardException 'state_changed') }
        } elseif ($existing -and -not $aceGate.CompletedNow -and -not $aceSetupDone) {
            Write-Host (Get-WizardText 'existing_firmware_kept')
        }
        if ($existing) {
            Write-Host (Get-WizardText 'existing_found') -ForegroundColor Green
        } else {
            if (@($status.serial_candidates).Count -ne 1) { throw (New-WizardException 'serial_ambiguous') }
            Write-Host (Get-WizardText 'fresh_empty')
            if (-not (Read-WizardChoice (Get-WizardText 'empty_question') (Get-WizardText 'yes') (Get-WizardText 'no_exit'))) { return 2 }
            Write-Host (Get-WizardText 'lengths_guide')
            Write-Host (Get-WizardText 'length_a')
            $retract = Read-WizardLength (Get-WizardText 'length_a_prompt') 2 2499
            Write-Host (Get-WizardText 'length_b')
            $fast = Read-WizardLength (Get-WizardText 'length_b_prompt') 1 ($retract - 1)
            Set-WizardLengths $settings $retract $fast
            Write-Host (Get-WizardText 'speeds_notice')
        }
        if (-not (Read-WizardChoice (Get-WizardText 'calibration_question') (Get-WizardText 'calibration_yes') (Get-WizardText 'calibration_no'))) { return 2 }
        $settings['calibrated_acknowledged'] = $true
        Write-WizardJson $settingsPath $settings
        $copy = Invoke-WizardNative $scp @('-O', '-o', 'ConnectTimeout=15', $settingsPath, ($target + ':' + $remoteDir + '/config/settings.local.json'))
        if ($copy.ExitCode -ne 0) { throw (New-WizardException 'settings_upload_failed') }
        $stage = (Get-WizardText 'stage_check')
        Write-Host ''
        Write-Host (Get-WizardText 'step_check') -ForegroundColor Cyan
        $check = Invoke-WizardRemoteJson $ssh $target $remoteDir 'check' $logFile
        if ($check.compatible -ne $true -or $check.read_only -ne $true -or $check.fresh_install -isnot [bool] -or $check.fresh_install -eq $existing) {
            throw (New-WizardException 'state_changed')
        }
        Show-WizardSettings $check.effective_settings
        Write-Host (Get-WizardText 'checks_passed')
        if (-not (Read-WizardChoice (Get-WizardText 'install_question') (Get-WizardText 'install_yes') (Get-WizardText 'install_no'))) { return 2 }
        $stage = (Get-WizardText 'stage_install')
        $installStarted = $true
        Write-Host ''
        Write-Host (Get-WizardText 'step_install') -ForegroundColor Cyan
        $result = Invoke-WizardRemoteJson $ssh $target $remoteDir 'install' $logFile
        if ($result.installed -ne $true -or $result.ready_samples -lt 3) { throw (New-WizardException 'install_incomplete') }
        Write-Host ''
        Write-Host (Get-WizardText 'step_done') -ForegroundColor Green
        Write-Host (Get-WizardText 'backup_id' @($result.backup))
        Write-Host (Get-WizardText 'protected_notice')
        Write-Host (Get-WizardText 'next_test')
        Write-Host (Get-WizardText 'log_local' @($logFile))
        return 0
    } catch {
        if ($_.Exception.Data['WizardMessageId'] -eq 'length_cancelled') {
            Write-Host (Get-WizardExceptionSummary $_.Exception) -ForegroundColor Yellow
            return 2
        }
        Write-Host ''
        Write-Host (Get-WizardText 'stopped' @($stage)) -ForegroundColor Red
        Write-Host (Get-WizardExceptionSummary $_.Exception) -ForegroundColor Yellow
        if ($installStarted) {
            Write-Host (Get-WizardText 'uncertain_install') -ForegroundColor Red
            Write-Host (Get-WizardText 'backups_location')
        }
        if ($remoteDir) { Write-Host (Get-WizardText 'remote_location' @($remoteDir)) }
        if ($logFile) {
            try { Add-Content -LiteralPath $logFile -Encoding UTF8 -Value ("`r`nWizard stage: $stage`r`n" + $_.Exception.Message) }
            catch { Write-Host (Get-WizardText 'log_failed') -ForegroundColor Yellow }
            Write-Host (Get-WizardText 'log_path' @($logFile))
        }
        return 1
    } finally {
        if ($temporary -and (Test-Path -LiteralPath $temporary)) {
            $actual = [IO.Path]::GetFullPath($temporary)
            $tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
            if ($actual.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase) -and
                (Split-Path $actual -Leaf) -match '^UltimateU1ACE-[a-f0-9]{32}$') {
                try { Remove-Item -LiteralPath $actual -Recurse -Force }
                catch { Write-Host (Get-WizardText 'cleanup_failed' @($actual)) -ForegroundColor Yellow }
            }
        }
    }
}

if (-not $LibraryOnly) {
    $exitCode = 1
    try {
        [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
        $exitCode = Start-U1Wizard -BundleRoot $PSScriptRoot
    } catch {
        Write-Host (Get-WizardText 'startup_failed') -ForegroundColor Red
        Write-Host (Get-WizardExceptionSummary $_.Exception)
    }
    Write-Host ''
    [void](Read-Host (Get-WizardText 'close_prompt'))
    # 20..22 tells the launcher that the localized close prompt was displayed.
    if ($FromLauncher) { exit (20 + $exitCode) }
    exit $exitCode
}
