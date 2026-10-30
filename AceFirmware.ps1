# SPDX-License-Identifier: GPL-3.0-only
# Developed with OpenAI Codex. Loaded by Install.ps1; import performs no device action.
$aceMessages = @{
    ace_title = @('ACE 第一代固件：检查、准备与更新', 'ACE Gen 1 firmware: check, prepare, and update')
    ace_scope = @('只支持已验证的 V1.3.856 / boot V1.0.1 → OpenCubic CFW 1.1.1。不会强制刷写未知版本。', 'Only V1.3.856 / boot V1.0.1 to OpenCubic CFW 1.1.1 is validated. Unknown versions cannot be forced.')
    ace_menu_check = @('  1. 自动检查 ACE，并从上游下载、校验所需固件', '  1. Check ACE; download and verify the required upstream files')
    ace_menu_keep = @('  2. 已安装指定 OpenCubic CFW 1.1.1，NFC 正常；保留现有固件', '  2. Keep known OpenCubic CFW 1.1.1 with working NFC')
    ace_menu_exit = @('  3. 退出，暂不改动', '  3. Exit without a change')
    ace_menu_prompt = @('请输入 1、2 或 3', 'Enter 1, 2, or 3')
    ace_menu_invalid = @('请输入列表中的数字 1、2 或 3。', 'Enter 1, 2, or 3 from the list.')
    ace_keep_warning = @('版本显示 CV1.3.863 不能单独证明具体构建。仅在你确认来源为指定 CFW 1.1.1 且 NFC 正常时保留。', 'CV1.3.863 alone does not identify the exact build. Keep it only when its CFW 1.1.1 source and NFC operation are known.')
    ace_keep_question = @('是否确认是指定 CFW 1.1.1，且这台 ACE 的 NFC 已正常工作？', 'Is this the specified CFW 1.1.1, with NFC already working on this ACE?')
    ace_keep_yes = @('已确认，保留现有固件', 'Confirmed; keep the current firmware')
    ace_keep_no = @('不能确认，退出', 'Cannot confirm; exit')
    ace_kept = @('按你的确认保留现有 ACE 固件。本次没有验证固件镜像，也没有刷写。', 'The ACE firmware is kept on your confirmation. This run has not verified the image or flashed ACE.')
    ace_prepare_notice = @('检查会暂时停止 Klipper 以独占 ACE 串口。向导不会发送进退料命令或写入固件；恢复服务时请保持手离开滚筒。', 'The check temporarily stops Klipper for exclusive ACE access. The wizard sends no filament movement or flash commands. Keep hands clear of the rollers when service resumes.')
    ace_retry_prepare = @('上次准备在确认就绪前结束。必须重新检查和准备；本轮不能跳过检查直接安装。', 'The previous preparation ended before ready checks passed. Run preparation again. This run cannot skip the checks and proceed directly to installation.')
    ace_maintenance_question = @('是否确认设备空闲、加热和烘干已关闭、温度低于 50°C，且 ACE 电源与 USB 连接稳定？', 'Are the devices idle, heating and drying off, temperatures below 50 C, and ACE power and USB stable?')
    ace_maintenance_yes = @('已确认，开始自动准备', 'Confirmed; start preparation')
    ace_maintenance_no = @('尚未完成，退出', 'Not ready; exit')
    ace_prepare_start = @('正在检查设备并准备两份上游固件。无需编辑配置或输入刷机命令。', 'Checking the device and preparing both upstream images. No profile editing or flash commands are needed.')
    ace_poll = @('ACE 操作状态：{0}；进度 {1}%。正在只读查询结果。', 'ACE operation state: {0}; progress {1}%. Reading the result only.')
    ace_poll_limit = @('操作尚未取得终态。不要重新刷写或断电。重新运行向导，选菜单 4 查看上次更新。', 'A final result is not available. Do not reflash or disconnect power. Run the wizard again and select menu 4 to inspect the last update.')
    ace_query_failed = @('未收到完整 ACE 结果。不要重发刷写或断电。重新运行向导，选菜单 4 只读查看上次更新。', 'The complete ACE result was not received. Do not resend the flash or disconnect power. Run the wizard again and select menu 4 to inspect the last update.')
    ace_attention = @('ACE 操作需要人工检查。向导不会重刷，也不会继续安装；Klipper 可能保持停止。保留诊断文件及操作编号。', 'The ACE operation needs inspection. The wizard will not reflash or continue installation. Klipper can remain stopped. Keep the diagnostic file and operation ID.')
    ace_recover_notice = @('记录表明尚未开始刷写。可以检查设备并恢复此前暂停的服务；此操作不会更新 ACE 固件，也不会重发刷写。', 'The record shows no flash attempt. You can check the device and restore the paused service. This does not update ACE firmware or resend a flash.')
    ace_recover_question = @('保持设备空闲、电源和 USB 稳定。是否检查并恢复这次尚未刷写的维护操作？', 'Keep the devices idle, with stable power and USB. Check and restore this maintenance operation before any flash?')
    ace_recover_yes = @('检查并恢复服务，不刷写', 'Check and restore the service without flashing')
    ace_recover_no = @('退出并保留现状', 'Exit and keep the current state')
    ace_recovered = @('刷写前维护已安全结束，后台已恢复。接下来可以重新检查或保留已知固件。', 'Maintenance ended safely before flashing. The service is restored. You can now check again or keep known firmware.')
    ace_invalid_result = @('ACE 返回结果格式或操作编号不匹配，已停止。请保留诊断记录。', 'The ACE result format or operation ID does not match. The workflow has stopped. Keep the diagnostics.')
    ace_unsupported = @('当前型号、来源版本或 boot 版本不在已验证范围。已停止，不提供强制继续选项。', 'The model, source version, or boot version is not validated. The workflow has stopped. There is no force option.')
    ace_safe_failure = @('本轮准备未完成；后台报告已安全恢复。请按诊断提示处理后再试，不会继续安装。', 'Preparation did not complete. The backend reports safe service restoration. Resolve the diagnostic issue before another attempt. Installation will not continue.')
    ace_error_download = @('下载或固件校验未通过。检查网络和诊断记录；不要使用未验证的文件。', 'Download or image verification failed. Check the network and diagnostics. Do not use an unverified file.')
    ace_error_idle = @('设备状态不满足维护条件。先正常结束打印、进退料和烘干，并等加热关闭、温度降低。', 'The device is not ready for maintenance. End printing, filament movement, and drying. Turn heaters off and allow cooling.')
    ace_error_port = @('ACE 接口或独占检查未通过。核对代际、接线和电源；不要关闭不明进程或随意选择串口。', 'The ACE interface or ownership check failed. Check the generation, wiring, and power. Do not stop unknown processes or guess a serial port.')
    ace_error_general = @('ACE 检查未通过。请保留诊断文件；不要修改探测记录或绕过检查。', 'The ACE check failed. Keep the diagnostic file. Do not edit probe evidence or bypass a check.')
    ace_code = @('诊断代码：{0}', 'Diagnostic code: {0}')
    ace_operation = @('ACE 操作编号：{0}', 'ACE operation ID: {0}')
    ace_versions = @('检测到：应用 {0}，boot {1}；目标 OpenCubic CFW 1.1.1（CV1.3.863）。', 'Detected: application {0}, boot {1}. Target: OpenCubic CFW 1.1.1 (CV1.3.863).')
    ace_downloads_verified = @('目标固件和原厂参考文件均已下载并校验，私人探测与逐设备配置由后台自动保存。', 'The target and stock reference files passed download and verification. The backend saved private device evidence and a device-specific profile.')
    ace_rollback_warning = @('注意：原厂 1.3.863 文件只是回退参考，不是此设备的备份；实机回退未验证，也不能保证救砖。', 'The stock 1.3.863 file is a rollback reference, not a device backup. Physical rollback is untested. Recovery is not guaranteed.')
    ace_final_question = @('是否确认保持供电、USB 和 U1 运行，并接受上述回退限制，执行这一次 ACE 固件更新？', 'Keep power, USB, and U1 running. Accept the stated rollback limits. Start this one ACE firmware update?')
    ace_final_yes = @('确认，刷写一次指定 ACE 固件', 'Confirm one flash of the specified ACE firmware')
    ace_final_no = @('取消，本次不刷写', 'Cancel without flashing')
    ace_starting = @('开始一次刷写。不要断电、拔线或重发；后续只有状态查询。', 'Starting one flash. Do not disconnect power or USB. Do not resend it. Only result queries follow.')
    ace_verified = @('已确认版本切换和连续就绪，后台已恢复。仍需完成后续 NFC 与进退料实机检查。', 'The version transition and consecutive ready states passed. The service is restored. NFC and filament operation still need physical checks.')
    ace_previous = @('已找到上次事务的成功记录。它只证明当时的结果；本次仍需检查当前 ACE 或确认保留已知固件。', 'A previous successful transaction was found. It records the earlier result. Check the current ACE or confirm keeping known firmware for this run.')
    ace_receipt = @('本次重新探测的 ACE 身份与已成功更新的记录匹配，保持该固件并继续。', 'The fresh ACE identity matches the successful update record. Keep that firmware and continue.')
    ace_material_title = @('材料信息发生非空变化，请核对当前料卷：', 'Nonempty material details changed. Compare these values with the current spools:')
    ace_material_line = @('  {0}：{1} → {2}', '  {0}: {1} -> {2}')
    ace_material_slot_line = @('  第 {0} 槽 · {1}：{2} → {3}', '  Slot {0} / {1}: {2} -> {3}')
    ace_material_brand = @('品牌', 'Brand')
    ace_material_type = @('材料类型', 'Material type')
    ace_material_subtype = @('材料系列', 'Material subtype')
    ace_material_color = @('颜色', 'Color')
    ace_material_question = @('这些品牌、类型和颜色是否与当前槽内料卷一致？不确认会退出，不会回刷固件。', 'Do these brand, type, and color values match the spools? If not, exit. The firmware will not be rolled back.')
    ace_material_yes = @('一致，继续', 'They match; continue')
    ace_material_no = @('不一致或不确定，退出', 'They differ or are uncertain; exit')
}
foreach ($entry in $aceMessages.GetEnumerator()) { $script:WizardMessages[$entry.Key] = $entry.Value }

function Get-AceSafeDisplay {
    param($Value)
    $text = [string]$Value -replace '[\x00-\x1f\x7f-\x9f]', '?'
    if ($text.Length -gt 180) { return ($text.Substring(0, 180) + '...') }
    return $text
}

function Get-AceRemoteCommand {
    param([string]$RemoteDir, [ValidateSet('prepare', 'start', 'result', 'recover')][string]$Action,
          [string]$Operation = '', [int]$WaitSeconds = 0)
    if ($RemoteDir -notmatch '^/userdata/ultimate-u1-ace-stage-[0-9]{8}-[0-9]{6}-[a-f0-9]{8}$') { throw (New-WizardException 'unsafe_directory') }
    if ($Operation -and $Operation -notmatch '^[a-f0-9]{32}$') { throw (New-WizardException 'ace_invalid_result') }
    if ($WaitSeconds -notin @(0, 30) -or ($WaitSeconds -and $Action -ne 'result')) { throw (New-WizardException 'ace_invalid_result') }
    if ($Action -in @('start', 'recover') -and -not $Operation) { throw (New-WizardException 'ace_invalid_result') }
    $command = "cd '$RemoteDir' || exit 1; python3 tools/ace_usb/wizard_backend.py $Action"
    if ($Operation) { $command += ' --operation ' + $Operation }
    if ($Action -eq 'start') { $command += ' --confirm-flash --accept-untested-rollback' }
    if ($WaitSeconds) { $command += ' --wait-seconds 30' }
    $command += ' 2> wizard-ace-' + $Action + '.err'
    return $command
}

function Test-AceResultShape {
    param($Result, [string]$Operation = '')
    $states = @('NONE', 'PREPARING', 'PREPARED', 'ALREADY_TARGET', 'UNSUPPORTED', 'STARTING', 'RUNNING', 'RECOVERING', 'CANCELLED_SAFE', 'SUCCEEDED', 'FAILED_SAFE', 'NEEDS_ATTENTION', 'ERROR')
    if ($null -eq $Result -or $Result.schema -ne 1 -or $Result.state -notin $states) { throw (New-WizardException 'ace_invalid_result') }
    foreach ($name in @('ready', 'service_restored', 'flash_attempted', 'needs_material_review')) {
        if ($Result.$name -isnot [bool]) { throw (New-WizardException 'ace_invalid_result') }
    }
    if ($Result.state -notin @('NONE','ERROR') -and $Result.operation -notmatch '^[a-f0-9]{32}$') { throw (New-WizardException 'ace_invalid_result') }
    if ($Operation -and $Result.state -ne 'ERROR' -and $Result.operation -ne $Operation) { throw (New-WizardException 'ace_invalid_result') }
    if (($Result.progress -isnot [int] -and $Result.progress -isnot [long]) -or $Result.progress -lt 0 -or $Result.progress -gt 100) { throw (New-WizardException 'ace_invalid_result') }
    if ($Result.code -isnot [string]) { throw (New-WizardException 'ace_invalid_result') }
    if ($Result.PSObject.Properties.Name -contains 'verified_installation_receipt' -and $Result.verified_installation_receipt -isnot [bool]) { throw (New-WizardException 'ace_invalid_result') }
}

function Get-AceErrorHint {
    param([string]$Code)
    switch -Regex ($Code) {
        'DOWNLOAD|IMAGE|HASH|CRC' { return (Get-WizardText 'ace_error_download') }
        'IDLE|BUSY|HEAT|DRY|ACTIVE|TEMPERATURE' { return (Get-WizardText 'ace_error_idle') }
        'SERIAL|USB|PORT|DEVICE' { return (Get-WizardText 'ace_error_port') }
        'SOURCE|BOOT|MODEL|UNSUPPORTED' { return (Get-WizardText 'ace_unsupported') }
        default { return (Get-WizardText 'ace_error_general') }
    }
}

function Invoke-AceRemoteJson {
    param([string]$Ssh, [string]$Target, [string]$RemoteDir, [string]$Action,
          [string]$LogFile, [string]$Operation = '', [int]$WaitSeconds = 0)
    $command = Get-AceRemoteCommand $RemoteDir $Action $Operation $WaitSeconds
    try { $native = Invoke-WizardNative $Ssh @('-o', 'ConnectTimeout=15', '-o', 'ServerAliveInterval=10', '-o', 'ServerAliveCountMax=3', $Target, $command) }
    catch { throw (New-WizardException 'ace_query_failed') }
    Add-Content -LiteralPath $LogFile -Encoding UTF8 -Value ("`r`nACE action: $Action; exit: " + $native.ExitCode + "`r`n" + $native.Output)
    try { $result = $native.Output | ConvertFrom-Json; Test-AceResultShape $result $Operation }
    catch { throw (New-WizardException 'ace_query_failed') }
    if ($native.ExitCode -ne 0 -or $result.state -eq 'ERROR') {
        Write-Host (Get-WizardText 'ace_code' @((Get-AceSafeDisplay $result.code))) -ForegroundColor Yellow
        throw (New-WizardException 'remote_error' @((Get-AceErrorHint $result.code)))
    }
    return $result
}

function Wait-AceFirmwareResult {
    param([string]$Ssh, [string]$Target, [string]$RemoteDir, [string]$LogFile, $Initial)
    $result = $Initial
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        if ($result.state -notin @('PREPARING', 'STARTING', 'RUNNING', 'RECOVERING')) { return $result }
        Write-Host (Get-WizardText 'ace_poll' @($result.state, $result.progress)) -ForegroundColor Cyan
        $result = Invoke-AceRemoteJson $Ssh $Target $RemoteDir 'result' $LogFile $result.operation 30
    }
    if ($result.state -in @('PREPARING', 'STARTING', 'RUNNING', 'RECOVERING')) { throw (New-WizardException 'ace_poll_limit') }
    return $result
}

function Assert-AceRestoredResult {
    param($Result)
    if ($Result.state -eq 'NEEDS_ATTENTION') { throw (New-WizardException 'ace_attention') }
    if ($Result.state -eq 'FAILED_SAFE' -and $Result.service_restored -and -not $Result.flash_attempted) {
        Write-Host (Get-WizardText 'ace_safe_failure') -ForegroundColor Yellow
        Write-Host (Get-WizardText 'ace_code' @((Get-AceSafeDisplay $Result.code)))
        throw (New-WizardException 'remote_error' @((Get-AceErrorHint $Result.code)))
    }
    if (-not $Result.ready -or -not $Result.service_restored -or $Result.state -eq 'FAILED_SAFE') { throw (New-WizardException 'ace_attention') }
}

function Confirm-AceMaterialChanges {
    param($Result)
    if (-not $Result.needs_material_review) { return $true }
    if (@($Result.material_changes).Count -eq 0 -or @($Result.material_changes).Count -gt 40) { throw (New-WizardException 'ace_invalid_result') }
    Write-Host (Get-WizardText 'ace_material_title') -ForegroundColor Yellow
    foreach ($change in $Result.material_changes) {
        $field = [string]$change.field
        $label = Get-AceSafeDisplay $field
        if ($field -match '^filament_(vendor|brand)(_|$)') { $label = Get-WizardText 'ace_material_brand' }
        elseif ($field -match '^filament_(subtype|sub_type)(_|$)') { $label = Get-WizardText 'ace_material_subtype' }
        elseif ($field -match '^filament_type(_|$)') { $label = Get-WizardText 'ace_material_type' }
        elseif ($field -match '^filament_color(_|$)') { $label = Get-WizardText 'ace_material_color' }
        if ($change.before -is [array] -and $change.after -is [array] -and $change.before.Count -eq 4 -and $change.after.Count -eq 4) {
            # Four-element U1 fields use zero-based storage and one-based slot labels.
            # Identical context is also displayed when the backend requests review
            # for private auxiliary metadata, without disclosing that metadata.
            $allEqual = (($change.before | ConvertTo-Json -Compress) -ceq ($change.after | ConvertTo-Json -Compress))
            for ($slot = 0; $slot -lt 4; $slot++) {
                $before = $change.before[$slot]; $after = $change.after[$slot]
                if (-not $allEqual -and ($before | ConvertTo-Json -Compress) -ceq ($after | ConvertTo-Json -Compress)) { continue }
                Write-Host (Get-WizardText 'ace_material_slot_line' @(($slot + 1), $label, (Get-AceSafeDisplay $before), (Get-AceSafeDisplay $after)))
            }
        } elseif ($field -match '^filament_.+_([0-3])$') {
            $slot = [int]$Matches[1] + 1
            Write-Host (Get-WizardText 'ace_material_slot_line' @($slot, $label, (Get-AceSafeDisplay $change.before), (Get-AceSafeDisplay $change.after)))
        } else {
            Write-Host (Get-WizardText 'ace_material_line' @($label, (Get-AceSafeDisplay $change.before), (Get-AceSafeDisplay $change.after)))
        }
    }
    return (Read-WizardChoice (Get-WizardText 'ace_material_question') (Get-WizardText 'ace_material_yes') (Get-WizardText 'ace_material_no'))
}

function Get-AceFirmwareGate {
    param([string]$Ssh, [string]$Target, [string]$RemoteDir, [string]$LogFile, [bool]$AllowRecovery = $false)
    $result = Invoke-AceRemoteJson $Ssh $Target $RemoteDir 'result' $LogFile
    if ($result.state -eq 'NONE') { return [pscustomobject]@{ Continue = $true; CompletedNow = $false; RequiresSetup = $false; ForcePrepare = $false } }
    Write-Host (Get-WizardText 'ace_operation' @($result.operation))
    $active = $result.state -in @('PREPARING', 'STARTING', 'RUNNING', 'RECOVERING')
    $result = Wait-AceFirmwareResult $Ssh $Target $RemoteDir $LogFile $result
    if ($AllowRecovery -and $result.state -eq 'NEEDS_ATTENTION' -and -not $result.flash_attempted) {
        Write-Host (Get-WizardText 'ace_recover_notice') -ForegroundColor Yellow
        if (-not (Read-WizardChoice (Get-WizardText 'ace_recover_question') (Get-WizardText 'ace_recover_yes') (Get-WizardText 'ace_recover_no'))) {
            return [pscustomobject]@{ Continue = $false; CompletedNow = $false; RequiresSetup = $false; ForcePrepare = $false }
        }
        $result = Invoke-AceRemoteJson $Ssh $Target $RemoteDir 'recover' $LogFile $result.operation
        $result = Wait-AceFirmwareResult $Ssh $Target $RemoteDir $LogFile $result
        if ($result.state -ne 'CANCELLED_SAFE' -or $result.flash_attempted) { throw (New-WizardException 'ace_attention') }
        Assert-AceRestoredResult $result
        Write-Host (Get-WizardText 'ace_recovered') -ForegroundColor Green
    }
    if ($result.state -eq 'FAILED_SAFE' -and $result.service_restored -and -not $result.flash_attempted) {
        Write-Host (Get-WizardText 'ace_safe_failure') -ForegroundColor Yellow
        if (-not (Confirm-AceMaterialChanges $result)) { return [pscustomobject]@{ Continue = $false; CompletedNow = $false; RequiresSetup = $true; ForcePrepare = $true } }
        return [pscustomobject]@{ Continue = $true; CompletedNow = $false; RequiresSetup = $true; ForcePrepare = (-not $result.ready) }
    }
    Assert-AceRestoredResult $result
    if (-not (Confirm-AceMaterialChanges $result)) { return [pscustomobject]@{ Continue = $false; CompletedNow = $false; RequiresSetup = $false; ForcePrepare = $false } }
    if ($result.state -eq 'SUCCEEDED') {
        $message = 'ace_previous'
        if ($active) { $message = 'ace_verified' }
        Write-Host (Get-WizardText $message) -ForegroundColor Green
    }
    return [pscustomobject]@{ Continue = $true; CompletedNow = ($active -and $result.state -eq 'SUCCEEDED'); RequiresSetup = ($result.state -eq 'UNSUPPORTED' -or ($result.state -eq 'SUCCEEDED' -and -not $active)); ForcePrepare = $false }
}

function Start-AceFirmwareSetup {
    param([string]$Ssh, [string]$Target, [string]$RemoteDir, [string]$LogFile, [bool]$ForcePrepare = $false)
    Write-Host ''
    Write-Host (Get-WizardText 'ace_title') -ForegroundColor Cyan
    Write-Host (Get-WizardText 'ace_scope')
    $choice = '1'
    if ($ForcePrepare) { Write-Host (Get-WizardText 'ace_retry_prepare') -ForegroundColor Yellow }
    else {
        foreach ($id in @('ace_menu_check', 'ace_menu_keep', 'ace_menu_exit')) { Write-Host (Get-WizardText $id) }
        do {
            $choice = Read-Host (Get-WizardText 'ace_menu_prompt')
            if ($choice -notin @('1', '2', '3')) { Write-Host (Get-WizardText 'ace_menu_invalid') }
        } until ($choice -in @('1', '2', '3'))
    }
    if ($choice -eq '3') { return $false }
    if ($choice -eq '2') {
        Write-Host (Get-WizardText 'ace_keep_warning') -ForegroundColor Yellow
        if (-not (Read-WizardChoice (Get-WizardText 'ace_keep_question') (Get-WizardText 'ace_keep_yes') (Get-WizardText 'ace_keep_no'))) { return $false }
        Write-Host (Get-WizardText 'ace_kept') -ForegroundColor Yellow
        return $true
    }
    Write-Host (Get-WizardText 'ace_prepare_notice') -ForegroundColor Yellow
    if (-not (Read-WizardChoice (Get-WizardText 'ace_maintenance_question') (Get-WizardText 'ace_maintenance_yes') (Get-WizardText 'ace_maintenance_no'))) { return $false }
    Write-Host (Get-WizardText 'ace_prepare_start') -ForegroundColor Cyan
    $prepared = Invoke-AceRemoteJson $Ssh $Target $RemoteDir 'prepare' $LogFile
    $prepared = Wait-AceFirmwareResult $Ssh $Target $RemoteDir $LogFile $prepared
    Write-Host (Get-WizardText 'ace_operation' @($prepared.operation))
    Assert-AceRestoredResult $prepared
    if ($prepared.state -notin @('PREPARED', 'ALREADY_TARGET')) { throw (New-WizardException 'ace_unsupported') }
    Write-Host (Get-WizardText 'ace_versions' @((Get-AceSafeDisplay $prepared.source_firmware), (Get-AceSafeDisplay $prepared.boot_firmware)))
    if (-not (Confirm-AceMaterialChanges $prepared)) { return $false }
    if ($prepared.state -eq 'ALREADY_TARGET') {
        if ($prepared.source_firmware -ne 'CV1.3.863') { throw (New-WizardException 'ace_unsupported') }
        if ($prepared.PSObject.Properties.Name -contains 'verified_installation_receipt' -and $prepared.verified_installation_receipt -eq $true) {
            Write-Host (Get-WizardText 'ace_receipt') -ForegroundColor Green
            return $true
        }
        Write-Host (Get-WizardText 'ace_keep_warning') -ForegroundColor Yellow
        if (-not (Read-WizardChoice (Get-WizardText 'ace_keep_question') (Get-WizardText 'ace_keep_yes') (Get-WizardText 'ace_keep_no'))) { return $false }
        Write-Host (Get-WizardText 'ace_kept') -ForegroundColor Yellow
        return $true
    }
    if ($prepared.source_firmware -ne 'V1.3.856' -or $prepared.boot_firmware -ne 'V1.0.1' -or $prepared.target_firmware -ne 'CV1.3.863') { throw (New-WizardException 'ace_unsupported') }
    Write-Host (Get-WizardText 'ace_downloads_verified')
    Write-Host (Get-WizardText 'ace_rollback_warning') -ForegroundColor Red
    if (-not (Read-WizardChoice (Get-WizardText 'ace_final_question') (Get-WizardText 'ace_final_yes') (Get-WizardText 'ace_final_no'))) { return $false }
    Write-Host (Get-WizardText 'ace_starting') -ForegroundColor Red
    $started = Invoke-AceRemoteJson $Ssh $Target $RemoteDir 'start' $LogFile $prepared.operation
    $finished = Wait-AceFirmwareResult $Ssh $Target $RemoteDir $LogFile $started
    if ($finished.state -ne 'SUCCEEDED') { throw (New-WizardException 'ace_attention') }
    Assert-AceRestoredResult $finished
    Write-Host (Get-WizardText 'ace_verified') -ForegroundColor Green
    return (Confirm-AceMaterialChanges $finished)
}
