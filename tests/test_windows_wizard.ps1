# SPDX-License-Identifier: GPL-3.0-only
# Offline only. Windows PowerShell 5.1; no Pester and no device access.
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
. (Join-Path $repo 'Install.ps1') -LibraryOnly
$passed = 0

function Assert-True {
    param($Value, [string]$Message)
    if (-not $Value) { throw $Message }
}
function Test-Case {
    param([string]$Name, [scriptblock]$Body)
    & $Body
    $script:passed += 1
    [Console]::WriteLine('PASS ' + $Name)
}
function Assert-Throws {
    param([scriptblock]$Body)
    $thrown = $false
    try { & $Body } catch { $thrown = $true }
    Assert-True $thrown 'Expected an exception'
}

Test-Case 'powershell_51_parse_and_utf8_bom' {
    $bytes = [IO.File]::ReadAllBytes((Join-Path $repo 'Install.ps1'))
    Assert-True ($bytes[0] -eq 239 -and $bytes[1] -eq 187 -and $bytes[2] -eq 191) 'Chinese script needs a UTF-8 BOM'
    $parseErrors = $null; $tokens = $null
    [void][Management.Automation.Language.Parser]::ParseFile((Join-Path $repo 'Install.ps1'), [ref]$tokens, [ref]$parseErrors)
    Assert-True (@($parseErrors).Count -eq 0) 'Parse errors'
}
Test-Case 'ipv4_and_dns_addresses' {
    foreach ($value in @('192.0.2.1', '10.0.0.2', 'u1.local', 'my-printer', 'Printer-01.example')) {
        Assert-True (Test-PrinterAddress $value) ('Valid address rejected: ' + $value)
    }
}
Test-Case 'address_shell_injection_and_bad_ip_rejected' {
    foreach ($value in @('', ' ', '192.0.2.999', '192.0.2', '0192.0.2.1', '-oProxyCommand=x',
            'root@192.0.2.1', 'http://192.0.2.1/', 'a;id', 'a&whoami', 'a$(whoami)', 'a`id',
            'a b', 'a..b', '-a.local', 'a-.local', 'a.local.', '::1', "a`nb", "a'b")) {
        Assert-True (-not (Test-PrinterAddress $value)) ('Unsafe address accepted: ' + $value)
    }
}
Test-Case 'windows_argument_quoting' {
    Assert-True ((ConvertTo-NativeArgument '') -eq '""') 'Empty argument'
    Assert-True ((ConvertTo-NativeArgument 'safe') -eq 'safe') 'Simple argument'
    Assert-True ((ConvertTo-NativeArgument 'a b') -eq '"a b"') 'Space'
    Assert-True ((ConvertTo-NativeArgument 'a"b') -eq '"a\"b"') 'Embedded quote'
    Assert-True ((ConvertTo-NativeArgument 'C:\a b\') -eq '"C:\a b\\"') 'Trailing backslash'
}
Test-Case 'native_process_exit_and_stdout' {
    $binary = Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe'
    $result = Invoke-WizardNative $binary @('-NoProfile', '-Command', '[Console]::Write("offline"); exit 7')
    Assert-True ($result.ExitCode -eq 7 -and $result.Output -eq 'offline') 'Native process handling'
}
Test-Case 'bundle_exact_allowlist_and_hashes' {
    $files = @(Get-WizardBundleFiles $repo)
    Assert-True ($files.Count -eq 16) 'Wrong upload scope'
    Assert-True (-not ($files -match 'private|settings.local|key|firmware/')) 'Private or firmware upload'
}
Test-Case 'template_cannot_enable_takeup_or_overwrite_existing' {
    $settings = New-WizardSettings $repo
    Assert-True ($settings.forward_takeup_length -eq 0) 'Takeup enabled'
    Assert-True ($settings.calibrated_acknowledged -eq $false) 'Unreviewed calibration'
    Assert-True ($settings.apply_existing_settings -eq $false) 'Existing settings overwrite'
}
Test-Case 'measured_lengths_are_used' {
    $settings = New-WizardSettings $repo
    Set-WizardLengths $settings 1400 1200
    Assert-True ($settings.retract_length -eq 1400 -and $settings.feed_length -eq 1400 -and $settings.fast_load_length -eq 1200) 'Measurements ignored'
    Assert-True ($settings.retract_speed -eq 80 -and $settings.sensor_load_speed -eq 50 -and $settings.fast_load_speed -eq 200) 'Common speed changed'
}
Test-Case 'invalid_lengths_rejected' {
    foreach ($pair in @(@(0, 100), @(1250, 0), @(1000, 1100), @(1000, 1000), @(2500, 1000), @(1250, 3000))) {
        Assert-Throws { Set-WizardLengths (New-WizardSettings $repo) $pair[0] $pair[1] }
    }
}
Test-Case 'remote_commands_fixed_and_quoted' {
    $remote = '/userdata/ultimate-u1-ace-stage-20261030-123456-abcdef12'
    $command = Get-RemoteWizardCommand $remote 'install'
    Assert-True ($command.Contains("cd '$remote' || exit 1;")) 'Missing protected directory'
    Assert-True ($command.Contains('installer.py install --settings config/settings.local.json')) 'Wrong install invocation'
    Assert-True (-not $command.Contains('StrictHostKeyChecking')) 'Host key bypass'
    Assert-Throws { Get-RemoteWizardCommand ($remote + "'; id") 'status' }
}
Test-Case 'launcher_is_ascii_and_uses_bundled_script' {
    $bytes = [IO.File]::ReadAllBytes((Join-Path $repo 'START-HERE.cmd'))
    Assert-True (@($bytes | Where-Object { $_ -gt 127 }).Count -eq 0) 'Non-ASCII launcher'
    $content = [Text.Encoding]::ASCII.GetString($bytes)
    Assert-True ($content.Contains('-NoProfile -ExecutionPolicy Bypass -File "%~dp0Install.ps1"')) 'Wrong launcher'
    Assert-True ($content.Contains('set "WIZARD_EXIT=%ERRORLEVEL%"') -and $content.Contains('exit /b %WIZARD_EXIT%')) 'Launcher must preserve outcome'
    foreach ($mapping in @('"20" exit /b 0', '"21" exit /b 1', '"22" exit /b 2')) {
        Assert-True ($content.Contains($mapping)) 'Launcher must handle localized close prompts'
    }
}

Test-Case 'message_catalog_has_both_languages' {
    foreach ($entry in $script:WizardMessages.GetEnumerator()) {
        Assert-True ($entry.Value.Count -eq 2) ('Incomplete translation: ' + $entry.Key)
        Assert-True ($entry.Value[0].Length -gt 0 -and $entry.Value[1].Length -gt 0) ('Empty translation: ' + $entry.Key)
        Assert-True ($entry.Value[1] -notmatch '[\u4e00-\u9fff]') ('Chinese in English translation: ' + $entry.Key)
    }
}
Test-Case 'shared_flow_has_no_hardcoded_chinese_messages' {
    $parseErrors = $null; $tokens = $null
    $ast = [Management.Automation.Language.Parser]::ParseFile((Join-Path $repo 'Install.ps1'), [ref]$tokens, [ref]$parseErrors)
    $functions = $ast.FindAll({ param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] }, $true)
    foreach ($function in $functions) {
        if ($function.Name -eq 'Select-WizardLanguage') { continue }
        $literals = $function.FindAll({ param($node)
            $node -is [Management.Automation.Language.StringConstantExpressionAst] -or
            $node -is [Management.Automation.Language.ExpandableStringExpressionAst]
        }, $true)
        foreach ($literal in $literals) {
            Assert-True ($literal.Value -notmatch '[\u4e00-\u9fff]') ('Hardcoded Chinese in ' + $function.Name)
        }
    }
}
Test-Case 'unexpected_errors_have_localized_summaries' {
    $script:WizardLanguage = 'en'
    $errorObject = New-Object System.InvalidOperationException 'OS error detail'
    $summary = Get-WizardExceptionSummary $errorObject
    Assert-True ($summary.Contains('unexpected error') -and -not $summary.Contains('OS error detail')) 'Untranslated system error exposed'
    $localized = New-WizardException 'lengths_invalid'
    Assert-True ((Get-WizardExceptionSummary $localized).Contains('A must be 2 to 2499 mm')) 'Localized exception lost'
    Assert-True ((Get-WizardErrorHint 'The printer Python lacks pyserial').Contains('dependency is missing')) 'Dependency error misidentified as a USB fault'
    $script:WizardLanguage = 'zh'
    Assert-True ((Get-WizardExceptionSummary $errorObject) -match '[\u4e00-\u9fff]') 'Chinese summary missing'
}

# The full wizard is driven by answers and fake native commands below.
# No SSH/SCP process can start after this definition.
$script:answers = New-Object 'Collections.Generic.Queue[string]'
$script:calls = New-Object 'Collections.Generic.List[object]'
$script:scenario = 'fresh'
$script:uploadedSettings = $null
$script:messages = New-Object 'Collections.Generic.List[string]'
$script:coloredMessages = New-Object 'Collections.Generic.List[object]'
$script:languageChosen = $false
$script:manualUrls = New-Object 'Collections.Generic.List[string]'
$script:events = New-Object 'Collections.Generic.List[string]'
$script:aceSetupCalls = 0
$script:aceRecoveryAllowed = $false
function Start-Process {
    param([string]$FilePath)
    $script:manualUrls.Add($FilePath)
}
function Invoke-WizardBootstrap {
    param([string]$BundleRoot)
    if ($script:scenario -eq 'bootstrap-failed') { throw (New-WizardException 'bundle_hash') }
    return ($script:scenario -ne 'bootstrap-cancelled')
}
function Invoke-WizardAceGate {
    param([string]$BundleRoot, [string]$Ssh, [string]$Target, [string]$RemoteDir, [string]$LogFile, [bool]$AllowRecovery = $false)
    $script:events.Add('ace-gate')
    $script:aceRecoveryAllowed = $AllowRecovery
    if ($script:scenario -eq 'ace-gate-attention') { throw (New-WizardException 'invalid_result') }
    return [pscustomobject]@{
        Continue = ($script:scenario -ne 'ace-gate-cancel')
        CompletedNow = ($script:scenario -eq 'ace-completed-now')
        RequiresSetup = ($script:scenario -eq 'existing-requires-ace')
        ForcePrepare = ($script:scenario -like 'ace-forced-*')
    }
}
function Invoke-WizardAceSetup {
    param([string]$BundleRoot, [string]$Ssh, [string]$Target, [string]$RemoteDir, [string]$LogFile, [bool]$ForcePrepare = $false)
    $script:events.Add('ace-setup')
    $script:aceSetupCalls++
    if ($script:scenario -like 'ace-forced-*') { Assert-True $ForcePrepare 'Unsafe preparation retry offered keep shortcut' }
    if ($script:scenario -eq 'ace-setup-failed') { throw (New-WizardException 'invalid_result') }
    return ($script:scenario -notin @('ace-setup-cancel', 'ace-forced-cancel'))
}
function Read-Host {
    param([string]$Prompt)
    if ($script:answers.Count -eq 0) { throw ('Unexpected prompt: ' + $Prompt) }
    if ($script:languageChosen) { $script:messages.Add($Prompt) }
    $answer = $script:answers.Dequeue()
    if ($Prompt -eq '1 / 2' -and $answer -in @('1', '2')) { $script:languageChosen = $true }
    return $answer
}
function Write-Host {
    [CmdletBinding(PositionalBinding=$false)]
    param([Parameter(Position=0, ValueFromRemainingArguments=$true)]$Arguments, $ForegroundColor)
    if ($script:languageChosen) {
        $script:messages.Add(($Arguments -join ' '))
        $script:coloredMessages.Add([pscustomobject]@{ Text = ($Arguments -join ' '); Color = $ForegroundColor })
    }
}
function Invoke-WizardNative {
    param([string]$Executable, [string[]]$Arguments)
    $script:calls.Add([pscustomobject]@{ Executable = $Executable; Arguments = $Arguments })
    Assert-True (-not (($Arguments -join ' ') -match 'StrictHostKeyChecking=no|UserKnownHostsFile|BatchMode|sshpass')) 'Unsafe SSH options'
    if ([IO.Path]::GetFileName($Executable) -eq 'scp.exe') {
        Assert-True ($Arguments[0] -eq '-O') 'Legacy SCP is required'
        if ($script:scenario -eq 'upload-failed') { return [pscustomobject]@{ ExitCode = 1; Output = '' } }
        if ($Arguments -contains '-r') {
            $source = $Arguments[$Arguments.Count - 2]
            $paths = @(Get-ChildItem -LiteralPath $source -Recurse -File)
            Assert-True ($paths.Count -eq 17) 'Unexpected copied files'
            Assert-True (-not ($paths.Name -match 'openrfid|user.cfg|credentials|\.bin$')) 'Private file copied'
        } else {
            $script:uploadedSettings = Get-Content -LiteralPath $Arguments[$Arguments.Count - 2] -Raw -Encoding UTF8 | ConvertFrom-Json
        }
        return [pscustomobject]@{ ExitCode = 0; Output = '' }
    }
    $command = $Arguments[-1]
    if ($command -match 'installer.py status') {
        $script:events.Add('host-status')
        $existing = $script:scenario -in @('existing', 'existing-requires-ace')
        $ports = @('/dev/serial/by-id/usb-ANYCUBIC_ACE_TEST-if00')
        if ($script:scenario -eq 'multiple-ace') { $ports += '/dev/serial/by-id/usb-ANYCUBIC_ACE_OTHER-if00' }
        $data = @{ existing_ace = $existing; serial_candidates = $ports; ace_settings = @{} }
    } elseif ($command -match 'installer.py check') {
        if ($script:scenario -eq 'check-failed') { return [pscustomobject]@{ ExitCode = 1; Output = 'ERROR: Printer must be idle' } }
        $fresh = $script:scenario -notin @('existing', 'existing-requires-ace')
        if ($script:scenario -eq 'state-changed') { $fresh = -not $fresh }
        $settings = $script:uploadedSettings
        if ($script:scenario -in @('existing', 'existing-requires-ace')) { $settings.retract_length = 1500; $settings.forward_takeup_length = 250 }
        $data = @{ compatible = $true; read_only = $true; fresh_install = $fresh; effective_settings = $settings }
    } elseif ($command -match 'installer.py install') {
        if ($script:scenario -eq 'install-lost') { return [pscustomobject]@{ ExitCode = 255; Output = '' } }
        $data = @{ installed = $true; backup = 'synthetic-backup'; ready_samples = 3 }
    } else { throw 'Unexpected remote command' }
    return [pscustomobject]@{ ExitCode = 0; Output = ($data | ConvertTo-Json -Depth 8) }
}

$testTemp = Join-Path ([IO.Path]::GetTempPath()) ('U1WizardTests-' + [guid]::NewGuid().ToString('N'))
[void](New-Item -ItemType Directory -Path $testTemp)
function Invoke-FakeWizard {
    param([string]$Scenario, [string[]]$Answers, [ValidateSet('zh', 'en')][string]$Language = 'zh', [string]$Task = '1', [string]$BundleRoot = $repo)
    $script:scenario = $Scenario
    $script:calls.Clear()
    $script:answers.Clear()
    $script:messages.Clear()
    $script:coloredMessages.Clear()
    $script:manualUrls.Clear()
    $script:events.Clear()
    $script:aceSetupCalls = 0
    $script:aceRecoveryAllowed = $false
    $script:languageChosen = $false
    if ($Language -eq 'en') { $script:answers.Enqueue('2') }
    else { $script:answers.Enqueue('1') }
    $script:answers.Enqueue($Task)
    foreach ($answer in $Answers) { $script:answers.Enqueue($answer) }
    $script:uploadedSettings = $null
    return Start-U1Wizard -BundleRoot $BundleRoot -LocalLogRoot $testTemp
}
function Count-InstallCalls {
    return @($script:calls | Where-Object { $_.Arguments[-1] -match 'installer.py install' }).Count
}
function Assert-EnglishOutput {
    $text = $script:messages -join "`n"
    Assert-True ($text -notmatch '[\u4e00-\u9fff]') 'Chinese appeared after English selection'
    Assert-True ($text.Contains('Setup Wizard')) 'English wizard title missing'
}
function Assert-ImportantWarning {
    foreach ($id in @('warning_title', 'warning_replaces', 'warning_core', 'warning_hardware')) {
        $text = Get-WizardText $id
        $lines = @($script:coloredMessages | Where-Object { $_.Text -eq $text })
        Assert-True ($lines.Count -eq 1 -and $lines[0].Color -eq 'Red') ('Important warning is not red: ' + $id)
        Assert-True ($script:messages.IndexOf($text) -lt $script:messages.IndexOf((Get-WizardText 'prerequisites_question'))) 'Warning appeared too late'
    }
}
try {
    Test-Case 'fresh_install_complete_without_json_edit' {
        $code = Invoke-FakeWizard 'fresh' @('1', '1', '192.0.2.1', '1', '1400', '1200', '1', '1')
        Assert-True ($code -eq 0) 'Fresh wizard failed'
        Assert-True ((Count-InstallCalls) -eq 1) 'Install count'
        Assert-True ($script:uploadedSettings.retract_length -eq 1400 -and $script:uploadedSettings.fast_load_length -eq 1200) 'Measured lengths not sent'
        Assert-True ($script:uploadedSettings.forward_takeup_length -eq 0) 'Unsafe initial takeup'
        Assert-True ($script:aceSetupCalls -eq 1 -and $script:events[0] -eq 'ace-gate') 'Fresh flow missed ACE stage or checked host status first'
        Assert-True (-not $script:aceRecoveryAllowed) 'Normal setup offered recovery'
        Assert-ImportantWarning
    }
    Test-Case 'existing_settings_preserved_without_length_prompt' {
        $code = Invoke-FakeWizard 'existing' @('1', '1', '192.0.2.1', '1', '1')
        Assert-True ($code -eq 0 -and (Count-InstallCalls) -eq 1) 'Existing update failed'
        Assert-True ($script:uploadedSettings.apply_existing_settings -eq $false) 'Existing settings replaced'
        Assert-True ($script:answers.Count -eq 0) 'Wrong existing prompts'
        Assert-True ($script:aceSetupCalls -eq 0) 'Existing firmware was prepared without a request'
    }
    Test-Case 'cancel_before_network' {
        $code = Invoke-FakeWizard 'fresh' @('2')
        Assert-True ($code -eq 2 -and $script:calls.Count -eq 0) 'Cancelled yet contacted device'
    }
    Test-Case 'uncalibrated_exit_without_install' {
        foreach ($language in @('zh', 'en')) {
            $code = Invoke-FakeWizard 'fresh' @('1', '1', '192.0.2.1', '1', '0') $language
            Assert-True ($code -eq 2 -and (Count-InstallCalls) -eq 0) 'Length cancellation was treated as failure or allowed install'
        }
    }
    Test-Case 'calibration_not_acknowledged_stops' {
        $code = Invoke-FakeWizard 'fresh' @('1', '1', '192.0.2.1', '1', '1400', '1200', '2')
        Assert-True ($code -eq 2 -and (Count-InstallCalls) -eq 0) 'Calibration bypass'
    }
    Test-Case 'final_review_cancel_does_not_install' {
        $code = Invoke-FakeWizard 'fresh' @('1', '1', '192.0.2.1', '1', '1400', '1200', '1', '2')
        Assert-True ($code -eq 2 -and (Count-InstallCalls) -eq 0) 'Review cancellation ignored'
    }
    Test-Case 'check_failure_does_not_install' {
        $code = Invoke-FakeWizard 'check-failed' @('1', '1', '192.0.2.1', '1', '1400', '1200', '1')
        Assert-True ($code -eq 1 -and (Count-InstallCalls) -eq 0) 'Failed check bypass'
    }
    Test-Case 'state_change_does_not_install' {
        $code = Invoke-FakeWizard 'state-changed' @('1', '1', '192.0.2.1', '1', '1400', '1200', '1')
        Assert-True ($code -eq 1 -and (Count-InstallCalls) -eq 0) 'Configuration race ignored'
    }
    Test-Case 'multiple_ace_not_guessed' {
        $code = Invoke-FakeWizard 'multiple-ace' @('1', '1', '192.0.2.1')
        Assert-True ($code -eq 1 -and (Count-InstallCalls) -eq 0) 'Ambiguous device guessed'
    }
    Test-Case 'upload_failure_stops' {
        $code = Invoke-FakeWizard 'upload-failed' @('1', '1', '192.0.2.1')
        Assert-True ($code -eq 1 -and $script:calls.Count -eq 1) 'Failed upload retried'
    }
    Test-Case 'lost_install_result_is_not_retried' {
        $code = Invoke-FakeWizard 'install-lost' @('1', '1', '192.0.2.1', '1', '1400', '1200', '1', '1')
        Assert-True ($code -eq 1 -and (Count-InstallCalls) -eq 1) 'Uncertain install repeated'
    }
    Test-Case 'english_fresh_install_complete' {
        $code = Invoke-FakeWizard 'fresh' @('1', '1', '192.0.2.1', '1', '1400', '1200', '1', '1') 'en'
        Assert-True ($code -eq 0 -and (Count-InstallCalls) -eq 1) 'English fresh install failed'
        Assert-True ($script:uploadedSettings.retract_length -eq 1400 -and $script:uploadedSettings.fast_load_length -eq 1200) 'English measurements ignored'
        Assert-True ($script:uploadedSettings.forward_takeup_length -eq 0) 'English initial takeup enabled'
        Assert-EnglishOutput
        Assert-ImportantWarning
        Assert-True (($script:messages -join ' ').Contains('Installation succeeded')) 'English success missing'
    }
    Test-Case 'english_existing_settings_preserved' {
        $code = Invoke-FakeWizard 'existing' @('1', '1', '192.0.2.1', '1', '1') 'en'
        Assert-True ($code -eq 0 -and (Count-InstallCalls) -eq 1) 'English existing update failed'
        Assert-True ($script:uploadedSettings.apply_existing_settings -eq $false) 'English overwrite enabled'
        Assert-True ($script:answers.Count -eq 0) 'English existing user was asked for lengths'
        Assert-EnglishOutput
        Assert-True (($script:messages -join ' ').Contains('1500 mm')) 'Effective existing settings were not displayed'
    }
    Test-Case 'english_cancel_before_network' {
        $code = Invoke-FakeWizard 'fresh' @('2') 'en'
        Assert-True ($code -eq 2 -and $script:calls.Count -eq 0) 'English cancellation ignored'
        Assert-EnglishOutput
    }
    Test-Case 'english_failure_help_is_localized' {
        $code = Invoke-FakeWizard 'check-failed' @('1', '1', '192.0.2.1', '1', '1400', '1200', '1') 'en'
        Assert-True ($code -eq 1 -and (Count-InstallCalls) -eq 0) 'English failed check bypassed'
        Assert-EnglishOutput
        $text = $script:messages -join ' '
        Assert-True ($text.Contains('printer is busy or hot') -and $text.Contains('below 50 C')) 'Actionable English failure help missing'
    }
    Test-Case 'english_uncertain_install_not_retried' {
        $code = Invoke-FakeWizard 'install-lost' @('1', '1', '192.0.2.1', '1', '1400', '1200', '1', '1') 'en'
        Assert-True ($code -eq 1 -and (Count-InstallCalls) -eq 1) 'English uncertain install repeated'
        Assert-EnglishOutput
        Assert-True (($script:messages -join ' ').Contains('Do not repeat installation')) 'English recovery instruction missing'
        $warning = @($script:coloredMessages | Where-Object { $_.Text -eq (Get-WizardText 'uncertain_install') })
        Assert-True ($warning.Count -eq 1 -and $warning[0].Color -eq 'Red') 'Uncertain-install warning must be red'
    }
    Test-Case 'english_upload_failure_stops' {
        $code = Invoke-FakeWizard 'upload-failed' @('1', '1', '192.0.2.1') 'en'
        Assert-True ($code -eq 1 -and $script:calls.Count -eq 1) 'English upload failure retried'
        Assert-EnglishOutput
        Assert-True (($script:messages -join ' ').Contains('File transfer failed')) 'English transfer failure missing'
    }
    Test-Case 'language_selection_is_first_and_retries_invalid_choice' {
        $script:answers.Clear(); $script:messages.Clear(); $script:languageChosen = $false
        foreach ($answer in @('bad', '2')) { $script:answers.Enqueue($answer) }
        Select-WizardLanguage
        Assert-True ($script:WizardLanguage -eq 'en' -and $script:answers.Count -eq 0) 'Language selection failed'
    }
    Test-Case 'manual_menu_opens_local_language_guide_without_printer_access' {
        $manualFixture = Join-Path $testTemp 'local-manuals'
        [void](New-Item -ItemType Directory -Path $manualFixture)
        foreach ($name in @('MANUAL-INSTALL.zh-CN.html', 'MANUAL-INSTALL.html')) {
            [IO.File]::WriteAllText((Join-Path $manualFixture $name), '<html>Offline manual fixture</html>')
        }
        foreach ($language in @('zh', 'en')) {
            $code = Invoke-FakeWizard 'fresh' @() $language '3' $manualFixture
            Assert-True ($code -eq 2 -and $script:calls.Count -eq 0) 'Manual menu contacted printer'
            $name = 'MANUAL-INSTALL.zh-CN.html'
            if ($language -eq 'en') { $name = 'MANUAL-INSTALL.html' }
            $expectedPath = [IO.Path]::GetFullPath((Join-Path $manualFixture $name))
            Assert-True ($script:manualUrls.Count -eq 1 -and $script:manualUrls[0] -eq $expectedPath) 'Wrong local manual destination'
            if ($language -eq 'en') { Assert-EnglishOutput }
        }
    }
    Test-Case 'missing_or_directory_manual_stops_without_browser_or_network' {
        $manualFixture = Join-Path $testTemp 'manual-fixture'
        [void](New-Item -ItemType Directory -Path $manualFixture)
        $script:WizardLanguage = 'en'
        $script:manualUrls.Clear()
        $script:calls.Clear()
        $failureId = $null
        try { Open-WizardManual $manualFixture } catch { $failureId = $_.Exception.Data['WizardMessageId'] }
        Assert-True ($failureId -eq 'manual_missing') 'Missing manual did not explain how to recover'
        [void](New-Item -ItemType Directory -Path (Join-Path $manualFixture 'MANUAL-INSTALL.html'))
        $failureId = $null
        try { Open-WizardManual $manualFixture } catch { $failureId = $_.Exception.Data['WizardMessageId'] }
        Assert-True ($failureId -eq 'bundle_regular') 'Directory was opened as a guide'
        Assert-True ($script:manualUrls.Count -eq 0 -and $script:calls.Count -eq 0) 'Invalid manual started a browser or network operation'
    }
    Test-Case 'usb_menu_cancel_does_not_start_ssh' {
        $code = Invoke-FakeWizard 'bootstrap-cancelled' @() 'en' '2'
        Assert-True ($code -eq 2 -and $script:calls.Count -eq 0) 'USB cancellation reached SSH'
    }
    Test-Case 'usb_menu_failure_does_not_start_ssh' {
        $code = Invoke-FakeWizard 'bootstrap-failed' @() 'en' '2'
        Assert-True ($code -eq 1 -and $script:calls.Count -eq 0) 'USB failure reached SSH'
    }
    Test-Case 'usb_menu_completion_continues_existing_install_flow' {
        $code = Invoke-FakeWizard 'fresh' @('1', '1', '192.0.2.1', '1', '1400', '1200', '1', '1') 'en' '2'
        Assert-True ($code -eq 0 -and (Count-InstallCalls) -eq 1) 'Completed USB setup did not continue'
        Assert-EnglishOutput
    }
    Test-Case 'ace_menu_is_maintenance_only_for_new_and_existing_host' {
        foreach ($language in @('zh', 'en')) {
            foreach ($scenario in @('fresh', 'existing')) {
                $code = Invoke-FakeWizard $scenario @('1', '1', '192.0.2.1') $language '4'
                Assert-True ($code -eq 0 -and (Count-InstallCalls) -eq 0 -and $script:aceSetupCalls -eq 1) 'ACE menu started host installation or missed firmware setup'
                Assert-True ($script:aceRecoveryAllowed -and $script:events[0] -eq 'ace-gate') 'ACE menu did not inspect durable status first'
                Assert-True (-not ($script:events -contains 'host-status') -and $null -eq $script:uploadedSettings) 'ACE maintenance entered the host configuration flow'
                Assert-True ($script:answers.Count -eq 0 -and $script:messages.Contains((Get-WizardText 'ace_maintenance_done'))) 'Maintenance exit or next-step instruction missing'
                if ($language -eq 'en') { Assert-EnglishOutput }
            }
        }
    }
    Test-Case 'ace_menu_newly_completed_update_exits_without_second_setup' {
        $code = Invoke-FakeWizard 'ace-completed-now' @('1', '1', '192.0.2.1') 'en' '4'
        Assert-True ($code -eq 0 -and $script:aceSetupCalls -eq 0 -and (Count-InstallCalls) -eq 0) 'Completed ACE update was repeated or installed host'
        Assert-True ($script:events.Count -eq 1 -and $script:events[0] -eq 'ace-gate') 'Result inspection reached host status'
    }
    Test-Case 'ace_menu_forced_prepare_is_not_bypassed_and_never_installs_host' {
        $code = Invoke-FakeWizard 'ace-forced-retry' @('1', '1', '192.0.2.1') 'en' '4'
        Assert-True ($code -eq 0 -and $script:aceSetupCalls -eq 1 -and (Count-InstallCalls) -eq 0) 'Maintenance forced preparation was bypassed or repeated'
        Assert-True ($script:events.Count -eq 2 -and $script:events[1] -eq 'ace-setup') 'Maintenance recovery entered the host flow'
        $code = Invoke-FakeWizard 'ace-forced-cancel' @('1', '1', '192.0.2.1') 'en' '4'
        Assert-True ($code -eq 2 -and $script:aceSetupCalls -eq 1 -and -not ($script:events -contains 'host-status')) 'Forced preparation cancellation was ignored'
    }
    Test-Case 'ace_menu_cancel_and_failure_do_not_report_completion' {
        foreach ($scenario in @('ace-setup-cancel', 'ace-setup-failed')) {
            $code = Invoke-FakeWizard $scenario @('1', '1', '192.0.2.1') 'en' '4'
            Assert-True ($code -ne 0 -and $script:aceSetupCalls -eq 1 -and (Count-InstallCalls) -eq 0) 'ACE failure reached host installation'
            Assert-True (-not $script:messages.Contains((Get-WizardText 'ace_maintenance_done'))) 'Failed or cancelled maintenance was reported as complete'
            Assert-True (-not ($script:events -contains 'host-status')) 'ACE failure reached host status'
        }
    }
    Test-Case 'ace_uncertain_or_cancelled_gate_blocks_host_status' {
        foreach ($scenario in @('ace-gate-attention', 'ace-gate-cancel')) {
            $code = Invoke-FakeWizard $scenario @('1', '1', '192.0.2.1') 'en' '4'
            Assert-True ($code -ne 0 -and (Count-InstallCalls) -eq 0 -and $script:aceSetupCalls -eq 0) 'Blocked gate reached installation'
            Assert-True (-not ($script:events -contains 'host-status')) 'Stopped service was queried before durable recovery'
        }
    }
    Test-Case 'ace_setup_cancel_or_failure_blocks_host_install' {
        foreach ($scenario in @('ace-setup-cancel', 'ace-setup-failed')) {
            $code = Invoke-FakeWizard $scenario @('1', '1', '192.0.2.1') 'en'
            Assert-True ($code -ne 0 -and (Count-InstallCalls) -eq 0 -and $script:aceSetupCalls -eq 1) 'ACE stage failure continued host install'
        }
    }
    Test-Case 'active_update_finished_now_does_not_start_second_setup' {
        $code = Invoke-FakeWizard 'ace-completed-now' @('1', '1', '192.0.2.1', '1', '1400', '1200', '1', '1') 'en'
        Assert-True ($code -eq 0 -and (Count-InstallCalls) -eq 1 -and $script:aceSetupCalls -eq 0) 'Finished ACE transaction was repeated'
    }
    Test-Case 'safe_failed_ace_gate_requires_setup_even_for_existing_host' {
        $code = Invoke-FakeWizard 'existing-requires-ace' @('1', '1', '192.0.2.1', '1', '1') 'en'
        Assert-True ($code -eq 0 -and $script:aceSetupCalls -eq 1) 'Existing host bypassed required ACE retry'
    }
    Test-Case 'failed_before_ready_forces_preparation_before_host_status' {
        $code = Invoke-FakeWizard 'ace-forced-retry' @('1', '1', '192.0.2.1', '1', '1400', '1200', '1', '1') 'en'
        Assert-True ($code -eq 0 -and $script:aceSetupCalls -eq 1 -and $script:events[1] -eq 'ace-setup' -and $script:events[2] -eq 'host-status') 'Required preparation was blocked by or skipped for host status'
        $code = Invoke-FakeWizard 'ace-forced-cancel' @('1', '1', '192.0.2.1') 'en'
        Assert-True ($code -eq 2 -and -not ($script:events -contains 'host-status')) 'Forced preparation cancellation reached host status'
    }
} finally {
    $resolved = [IO.Path]::GetFullPath($testTemp)
    $parent = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    if ($resolved.StartsWith($parent, [StringComparison]::OrdinalIgnoreCase) -and (Split-Path $resolved -Leaf) -match '^U1WizardTests-[a-f0-9]{32}$') {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
[Console]::WriteLine('All ' + $passed + ' offline Windows wizard tests passed.')
