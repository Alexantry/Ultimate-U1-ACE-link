# SPDX-License-Identifier: GPL-3.0-only
# Offline only. SSH results, user answers, and device records are synthetic.
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
. (Join-Path $repo 'Install.ps1') -LibraryOnly
. (Join-Path $repo 'AceFirmware.ps1')
$passed = 0
function Assert-True { param($Value, [string]$Message); if (-not $Value) { throw $Message } }
function Assert-Throws {
    param([scriptblock]$Body, [string]$Id = '')
    $caught = $null
    try { & $Body } catch { $caught = $_.Exception }
    Assert-True ($null -ne $caught) 'Expected refusal'
    if ($Id) { Assert-True ($caught.Data['WizardMessageId'] -eq $Id) ('Wrong refusal: ' + $caught.Message) }
}
function Test-Case { param([string]$Name, [scriptblock]$Body); & $Body; $script:passed++; [Console]::WriteLine('PASS ' + $Name) }
$script:answers = New-Object 'Collections.Generic.Queue[string]'
$script:results = New-Object 'Collections.Generic.Queue[object]'
$script:calls = New-Object 'Collections.Generic.List[string]'
$script:messages = New-Object 'Collections.Generic.List[string]'
$script:colors = New-Object 'Collections.Generic.List[object]'
$script:operation = '0123456789abcdef0123456789abcdef'
$remote = '/userdata/ultimate-u1-ace-stage-20261030-123456-abcdef12'
$testRoot = Join-Path ([IO.Path]::GetTempPath()) ('U1AceWizardTests-' + [guid]::NewGuid().ToString('N'))
[void](New-Item -ItemType Directory -Path $testRoot)
$log = Join-Path $testRoot 'test.log'
[IO.File]::WriteAllText($log, '')

function Read-Host {
    param([string]$Prompt)
    $script:messages.Add($Prompt)
    if (-not $script:answers.Count) { throw ('Unexpected prompt: ' + $Prompt) }
    return $script:answers.Dequeue()
}
function Write-Host {
    [CmdletBinding(PositionalBinding=$false)]
    param([Parameter(Position=0, ValueFromRemainingArguments=$true)]$Arguments, $ForegroundColor)
    $text = $Arguments -join ' '
    $script:messages.Add($text)
    $script:colors.Add([pscustomobject]@{Text=$text;Color=$ForegroundColor})
}
function Invoke-WizardNative {
    param([string]$Executable, [string[]]$Arguments)
    Assert-True (-not (($Arguments -join ' ') -match 'StrictHostKeyChecking=no|UserKnownHostsFile|BatchMode|sshpass')) 'Host verification bypass'
    $script:calls.Add($Arguments[-1])
    if (-not $script:results.Count) { throw 'Unexpected native call' }
    $next = $script:results.Dequeue()
    if ($next -is [string] -and $next -eq 'TRANSPORT_EXCEPTION') { throw 'synthetic process failure' }
    return $next
}
function New-Result {
    param([string]$State, [hashtable]$Extra=@{})
    $safe = $State -in @('PREPARED','ALREADY_TARGET','UNSUPPORTED','SUCCEEDED','FAILED_SAFE','CANCELLED_SAFE')
    $data = @{
        schema=1; state=$State; operation=$script:operation; code='SYNTHETIC'; progress=0;
        ready=$safe; service_restored=$safe; flash_attempted=($State -in @('RUNNING','SUCCEEDED'));
        needs_material_review=$false; material_changes=@(); source_firmware='V1.3.856';
        boot_firmware='V1.0.1'; target_firmware='CV1.3.863'
    }
    if ($State -eq 'NONE') { $data.operation=$null }
    foreach ($key in $Extra.Keys) { $data[$key]=$Extra[$key] }
    return [pscustomobject]$data
}
function Queue-Result {
    param($Data, [int]$ExitCode=0)
    $script:results.Enqueue([pscustomobject]@{ ExitCode=$ExitCode; Output=($Data | ConvertTo-Json -Depth 10) })
}
function Reset-Fakes {
    param([string[]]$Answers=@(), [string]$Language='en')
    $script:answers.Clear(); $script:results.Clear(); $script:calls.Clear(); $script:messages.Clear(); $script:colors.Clear()
    foreach ($answer in $Answers) { $script:answers.Enqueue($answer) }
    $script:WizardLanguage=$Language
}
function Run-Setup { param([bool]$ForcePrepare = $false); return (Start-AceFirmwareSetup 'ssh.exe' 'root@192.0.2.1' $remote $log $ForcePrepare) }
function Run-Gate { param([bool]$AllowRecovery = $false); return (Get-AceFirmwareGate 'ssh.exe' 'root@192.0.2.1' $remote $log $AllowRecovery) }
function Count-Starts { return @($script:calls | Where-Object { $_ -match 'wizard_backend.py start' }).Count }
function Assert-English { Assert-True (($script:messages -join ' ') -notmatch '[\u4e00-\u9fff]') 'Untranslated Chinese output' }

try {
    Test-Case 'ps51_parse_bom_and_bilingual_catalog' {
        $path=Join-Path $repo 'AceFirmware.ps1'
        $bytes=[IO.File]::ReadAllBytes($path)
        Assert-True ($bytes[0]-eq239 -and $bytes[1]-eq187 -and $bytes[2]-eq191) 'Missing BOM'
        $tokens=$null; $errors=$null
        [void][Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors)
        Assert-True (@($errors).Count-eq0) 'PS syntax errors'
        foreach ($entry in $aceMessages.GetEnumerator()) {
            Assert-True ($entry.Value.Count-eq2 -and $entry.Value[1] -notmatch '[\u4e00-\u9fff]') 'Missing translation'
        }
    }
    Test-Case 'remote_arguments_are_fixed_and_guarded' {
        $command=Get-AceRemoteCommand $remote 'start' $script:operation
        Assert-True ($command.Contains('--confirm-flash --accept-untested-rollback')) 'Confirmation flags missing'
        Assert-True (-not $command.Contains('curl') -and -not $command.Contains('wget')) 'Remote script download'
        Assert-Throws { Get-AceRemoteCommand ($remote+"'; id") 'result' }
        Assert-Throws { Get-AceRemoteCommand $remote 'start' 'x; id' }
        Assert-Throws { Get-AceRemoteCommand $remote 'start' }
        Assert-Throws { Get-AceRemoteCommand $remote 'recover' }
        Assert-Throws { Get-AceRemoteCommand $remote 'prepare' '' 30 }
        Assert-Throws { Get-AceRemoteCommand $remote 'result' '' 31 }
    }
    Test-Case 'result_identity_state_and_booleans_checked' {
        Test-AceResultShape (New-Result 'NONE')
        Assert-Throws { Test-AceResultShape (New-Result 'RUNNING') ('f'*32) }
        Assert-Throws { Test-AceResultShape (New-Result 'INVENTED') }
        Assert-Throws { Test-AceResultShape (New-Result 'PREPARED' @{ready='true'}) }
        Assert-Throws { Test-AceResultShape (New-Result 'PREPARED' @{progress=101}) }
        Test-AceResultShape (New-Result 'PREPARED' @{progress=[long]100})
        Assert-Throws { Test-AceResultShape (New-Result 'PREPARED' @{progress=[long]101}) }
        Assert-Throws { Test-AceResultShape (New-Result 'PREPARED' @{progress=12.5}) }
        Assert-Throws { Test-AceResultShape (New-Result 'ALREADY_TARGET' @{verified_installation_receipt='true'}) }
    }
    Test-Case 'fresh_async_update_has_one_start_and_status_only_polls' {
        foreach($language in @('en','zh')) {
            Reset-Fakes @('1','1','1') $language
            Queue-Result (New-Result 'PREPARING'); Queue-Result (New-Result 'PREPARED')
            Queue-Result (New-Result 'STARTING'); Queue-Result (New-Result 'RUNNING'); Queue-Result (New-Result 'SUCCEEDED')
            Assert-True (Run-Setup) 'Upgrade flow failed'
            Assert-True ((Count-Starts)-eq1 -and $script:results.Count-eq0 -and $script:answers.Count-eq0) 'Unexpected replay or prompt'
            Assert-True (@($script:calls | Where-Object {$_ -match 'result.*--wait-seconds 30'}).Count-eq3) 'Polling not read-only'
            $warnings=@($script:colors | Where-Object {$_.Text-eq(Get-WizardText 'ace_rollback_warning')})
            Assert-True ($warnings.Count-eq1 -and $warnings[0].Color-eq'Red') 'Rollback warning not red'
            if($language-eq'en'){Assert-English}
        }
    }
    Test-Case 'cancel_before_probe_makes_no_remote_call' {
        foreach($answers in @(@('3'),@('1','2'))) {
            Reset-Fakes $answers
            Assert-True (-not (Run-Setup) -and $script:calls.Count-eq0) 'Cancelled but contacted device'
        }
    }
    Test-Case 'known_build_skip_is_explicit_and_not_claimed_verified' {
        Reset-Fakes @('2','1')
        Assert-True (Run-Setup) 'Known-build skip failed'
        Assert-True ($script:calls.Count-eq0 -and ($script:messages-join' ').Contains('has not verified the image')) 'Skip misrepresented'
        Reset-Fakes @('2','2')
        Assert-True (-not (Run-Setup)) 'Unconfirmed skip passed'
    }
    Test-Case 'cancel_final_review_does_not_flash' {
        Reset-Fakes @('1','1','2'); Queue-Result (New-Result 'PREPARED')
        Assert-True (-not (Run-Setup) -and (Count-Starts)-eq0) 'Cancelled final review flashed'
    }
    Test-Case 'unsupported_source_has_no_force_path' {
        Reset-Fakes @('1','1'); Queue-Result (New-Result 'UNSUPPORTED' @{source_firmware='V9.9.9'})
        Assert-Throws { Run-Setup } 'ace_unsupported'
        Assert-True ((Count-Starts)-eq0) 'Unsupported source flashed'
        Reset-Fakes @('1','1'); Queue-Result (New-Result 'PREPARED' @{boot_firmware='V9.0.0'})
        Assert-Throws { Run-Setup } 'ace_unsupported'
        Assert-True ((Count-Starts)-eq0) 'Wrong boot flashed'
    }
    Test-Case 'already_target_requires_confirmation_and_never_reflashes' {
        Reset-Fakes @('1','1','1'); Queue-Result (New-Result 'ALREADY_TARGET' @{source_firmware='CV1.3.863'})
        Assert-True (Run-Setup) 'Confirmed existing firmware refused'
        Assert-True ((Count-Starts)-eq0) 'Existing target was reflashed'
        Reset-Fakes @('1','1','2'); Queue-Result (New-Result 'ALREADY_TARGET' @{source_firmware='CV1.3.863'})
        Assert-True (-not (Run-Setup)) 'Unconfirmed existing firmware passed'
    }
    Test-Case 'fresh_identity_receipt_allows_recovered_upgrade_without_reflash' {
        Reset-Fakes @('1','1'); Queue-Result (New-Result 'ALREADY_TARGET' @{source_firmware='CV1.3.863';verified_installation_receipt=$true})
        Assert-True (Run-Setup) 'Matching receipt refused'
        Assert-True ((Count-Starts)-eq0 -and $script:answers.Count-eq0) 'Receipt caused extra flash or acknowledgement'
    }
    Test-Case 'lost_start_response_is_not_replayed' {
        Reset-Fakes @('1','1','1'); Queue-Result (New-Result 'PREPARED')
        $script:results.Enqueue([pscustomobject]@{ExitCode=255;Output=''})
        Assert-Throws { Run-Setup } 'ace_query_failed'
        Assert-True ((Count-Starts)-eq1 -and $script:calls.Count-eq2) 'Lost start replayed'
    }
    Test-Case 'native_exception_requires_result_query_not_retry' {
        Reset-Fakes @('1','1','1'); Queue-Result (New-Result 'PREPARED'); $script:results.Enqueue('TRANSPORT_EXCEPTION')
        Assert-Throws { Run-Setup } 'ace_query_failed'
        Assert-True ((Count-Starts)-eq1) 'Process failure replayed start'
    }
    Test-Case 'uncertain_result_never_passes_to_host_install' {
        Reset-Fakes @('1','1','1'); Queue-Result (New-Result 'PREPARED'); Queue-Result (New-Result 'NEEDS_ATTENTION')
        Assert-Throws { Run-Setup } 'ace_attention'
        Assert-True ((Count-Starts)-eq1) 'Uncertain result replayed'
    }
    Test-Case 'success_without_restored_service_is_refused' {
        Reset-Fakes @('1','1','1'); Queue-Result (New-Result 'PREPARED'); Queue-Result (New-Result 'SUCCEEDED' @{service_restored=$false})
        Assert-Throws { Run-Setup } 'ace_attention'
    }
    Test-Case 'prepare_failure_stops_before_flash' {
        foreach($ready in @($true,$false)) {
            Reset-Fakes @('1','1'); Queue-Result (New-Result 'FAILED_SAFE' @{code='IMAGE_HASH_FAILED';ready=$ready})
            Assert-Throws { Run-Setup } 'remote_error'
            Assert-True ((Count-Starts)-eq0) 'Preparation failure flashed'
            Assert-True (($script:messages -join ' ').Contains('IMAGE_HASH_FAILED')) 'Pre-stop failure lost its diagnostic'
            Assert-English
        }
    }
    Test-Case 'backend_nonzero_json_is_not_success' {
        Reset-Fakes @('1','1'); Queue-Result (New-Result 'FAILED_SAFE' @{code='SOURCE_UNSUPPORTED'}) 1
        Assert-Throws { Run-Setup } 'remote_error'
        Assert-True ((Count-Starts)-eq0) 'Failed backend command continued'
    }
    Test-Case 'backend_error_with_null_operation_preserves_diagnostic' {
        Reset-Fakes @('1','1')
        Queue-Result (New-Result 'ERROR' @{operation=$null;code='IMAGE_HASH_FAILED'}) 2
        Assert-Throws { Run-Setup } 'remote_error'
        Assert-True (($script:messages -join ' ').Contains('IMAGE_HASH_FAILED')) 'Backend diagnostic was hidden as transport error'
    }
    Test-Case 'material_review_before_flash_can_cancel' {
        Reset-Fakes @('1','1','2')
        Queue-Result (New-Result 'PREPARED' @{needs_material_review=$true;material_changes=@(@{field='slot1.brand';before='Generic';after='Bambu'})})
        Assert-True (-not (Run-Setup) -and (Count-Starts)-eq0) 'Material mismatch ignored before flash'
    }
    Test-Case 'material_review_after_success_can_stop_host_without_reflash' {
        Reset-Fakes @('1','1','1','2'); Queue-Result (New-Result 'PREPARED')
        Queue-Result (New-Result 'SUCCEEDED' @{needs_material_review=$true;material_changes=@(@{field='slot1.brand';before='Generic';after='Bambu'})})
        Assert-True (-not (Run-Setup) -and (Count-Starts)-eq1) 'Material mismatch retried or ignored'
    }
    Test-Case 'no_previous_operation_leaves_gate_open_without_prepare' {
        Reset-Fakes; Queue-Result (New-Result 'NONE')
        $gate=Run-Gate
        Assert-True ($gate.Continue -and -not $gate.CompletedNow -and $script:calls.Count-eq1) 'Empty gate did maintenance'
    }
    Test-Case 'reconnect_to_active_operation_only_polls' {
        Reset-Fakes; Queue-Result (New-Result 'RUNNING'); Queue-Result (New-Result 'SUCCEEDED')
        $gate=Run-Gate
        Assert-True ($gate.Continue -and $gate.CompletedNow) 'Completed operation not recognized'
        Assert-True ((Count-Starts)-eq0 -and @($script:calls | Where-Object {$_ -notmatch 'wizard_backend.py result'}).Count-eq0) 'Reconnect started another operation'
    }
    Test-Case 'old_success_receipt_does_not_certify_current_device' {
        Reset-Fakes; Queue-Result (New-Result 'SUCCEEDED')
        $gate=Run-Gate
        Assert-True ($gate.Continue -and -not $gate.CompletedNow -and $gate.RequiresSetup) 'Old receipt treated as fresh proof'
        Assert-True (($script:messages-join' ').Contains('earlier result')) 'Old result warning missing'
    }
    Test-Case 'needs_attention_gate_blocks_all_host_commands' {
        Reset-Fakes; Queue-Result (New-Result 'NEEDS_ATTENTION')
        Assert-Throws { Run-Gate } 'ace_attention'
        Assert-True ($script:calls.Count-eq1) 'Uncertain gate did extra work'
    }
    Test-Case 'safe_previous_failure_requests_new_setup' {
        Reset-Fakes; Queue-Result (New-Result 'FAILED_SAFE')
        $gate=Run-Gate
        Assert-True ($gate.Continue -and $gate.RequiresSetup -and -not $gate.CompletedNow) 'Safe retry gate failed'
    }
    Test-Case 'failure_before_ready_requires_fresh_prepare_without_keep_shortcut' {
        Reset-Fakes; Queue-Result (New-Result 'FAILED_SAFE' @{ready=$false;service_restored=$true;flash_attempted=$false})
        $gate=Run-Gate
        Assert-True ($gate.Continue -and $gate.ForcePrepare -and $gate.RequiresSetup) 'Failure before ready cannot be retried'
        Reset-Fakes @('1','2'); Queue-Result (New-Result 'PREPARED')
        Assert-True (-not (Run-Setup $true)) 'Forced preparation cancellation ignored'
        Assert-True ($script:calls.Count-eq1 -and $script:calls[0] -match 'wizard_backend.py prepare' -and (Count-Starts)-eq0) 'Forced preparation skipped probe'
        Assert-True (-not ($script:messages -contains (Get-WizardText 'ace_menu_keep'))) 'Forced preparation offered keep shortcut'
        Reset-Fakes @('2')
        Assert-True (-not (Run-Setup $true) -and $script:calls.Count-eq0) 'Forced preparation initial cancellation did work'
    }
    Test-Case 'stored_material_review_cannot_be_bypassed_on_reopen' {
        foreach ($state in @('PREPARED', 'ALREADY_TARGET', 'SUCCEEDED', 'FAILED_SAFE', 'CANCELLED_SAFE')) {
            Reset-Fakes @('2')
            Queue-Result (New-Result $state @{needs_material_review=$true;material_changes=@(@{field='slot1.brand';before='Generic';after='Bambu'})})
            $gate=Run-Gate
            Assert-True (-not $gate.Continue -and (Count-Starts)-eq0) ('Stored material changes ignored: '+$state)
        }
    }
    Test-Case 'material_arrays_use_changed_one_based_slots_and_localized_labels' {
        foreach($language in @('en','zh')) {
            Reset-Fakes @('1') $language
            $result=New-Result 'PREPARED' @{needs_material_review=$true;material_changes=@(
                @{field='filament_vendor';before=@('NONE','Generic','Bambu','NONE');after=@('NONE','Bambu','Bambu','NONE')},
                @{field='filament_color';before=@(1,1,1,1);after=@(1,0,1,1)},
                @{field='filament_sub_type_0';before='Basic';after="Matte`n"}
            )}
            Assert-True (Confirm-AceMaterialChanges $result) 'Material review failed'
            $expected=Get-WizardText 'ace_material_slot_line' @(2,(Get-WizardText 'ace_material_brand'),'Generic','Bambu')
            Assert-True ($script:messages -contains $expected) 'Array change not labeled as slot 2'
            $black=Get-WizardText 'ace_material_slot_line' @(2,(Get-WizardText 'ace_material_color'),'1','0')
            Assert-True ($script:messages -contains $black) 'Black zero was lost'
            $subtype=Get-WizardText 'ace_material_slot_line' @(1,(Get-WizardText 'ace_material_subtype'),'Basic','Matte?')
            Assert-True ($script:messages -contains $subtype) 'Indexed subtype or terminal controls mishandled'
            Assert-True (@($script:messages | Where-Object { $_ -match '^  (Slot|\u7b2c)' }).Count-eq3) 'Unchanged slots displayed as changes'
            if($language-eq'en'){Assert-English}
        }
    }
    Test-Case 'auxiliary_metadata_context_remains_reviewable_without_private_fields' {
        Reset-Fakes @('1')
        $result=New-Result 'PREPARED' @{needs_material_review=$true;material_changes=@(
            @{field='filament_vendor';before=@('Bambu','NONE','NONE','NONE');after=@('Bambu','NONE','NONE','NONE')}
        )}
        Assert-True (Confirm-AceMaterialChanges $result) 'Context-only material review failed'
        Assert-True (@($script:messages | Where-Object { $_ -match '^  Slot' }).Count-eq4) 'Private-metadata context disappeared'
    }
    Test-Case 'menu_four_can_recover_before_flash_once_then_only_poll' {
        foreach ($language in @('en','zh')) {
            Reset-Fakes @('1') $language
            Queue-Result (New-Result 'NEEDS_ATTENTION' @{flash_attempted=$false})
            Queue-Result (New-Result 'RECOVERING')
            Queue-Result (New-Result 'CANCELLED_SAFE')
            $gate=Run-Gate $true
            Assert-True ($gate.Continue -and -not $gate.CompletedNow -and (Count-Starts)-eq0) 'Safe recovery outcome failed'
            Assert-True (@($script:calls | Where-Object { $_ -match 'wizard_backend.py recover' }).Count-eq1) 'Recovery was repeated or not sent'
            Assert-True ($script:calls[-1] -match 'wizard_backend.py result') 'Recovery did not finish with result-only query'
            if($language-eq'en'){Assert-English}
        }
    }
    Test-Case 'recovery_cancel_leaves_maintenance_state_unchanged' {
        Reset-Fakes @('2'); Queue-Result (New-Result 'NEEDS_ATTENTION' @{flash_attempted=$false})
        $gate=Run-Gate $true
        Assert-True (-not $gate.Continue -and $script:calls.Count-eq1) 'Recovery cancellation sent a command'
    }
    Test-Case 'any_flash_attempt_blocks_recovery_even_in_menu_four' {
        Reset-Fakes; Queue-Result (New-Result 'NEEDS_ATTENTION' @{flash_attempted=$true})
        Assert-Throws { Run-Gate $true } 'ace_attention'
        Assert-True ($script:calls.Count-eq1) 'Recovery offered after IAP attempt'
    }
    Test-Case 'lost_recovery_result_is_never_replayed' {
        Reset-Fakes @('1'); Queue-Result (New-Result 'NEEDS_ATTENTION' @{flash_attempted=$false})
        $script:results.Enqueue([pscustomobject]@{ExitCode=255;Output=''})
        Assert-Throws { Run-Gate $true } 'ace_query_failed'
        Assert-True (@($script:calls | Where-Object { $_ -match 'wizard_backend.py recover' }).Count-eq1 -and (Count-Starts)-eq0) 'Recovery result loss caused a replay'
    }
    Test-Case 'reconnect_during_recovery_only_reads_result' {
        Reset-Fakes; Queue-Result (New-Result 'RECOVERING'); Queue-Result (New-Result 'CANCELLED_SAFE')
        $gate=Run-Gate $true
        Assert-True ($gate.Continue -and @($script:calls | Where-Object {$_ -notmatch 'wizard_backend.py result'}).Count-eq0) 'Recovery reconnect sent another action'
    }
    Test-Case 'polling_is_bounded_and_never_restarts' {
        Reset-Fakes
        for($i=0;$i-lt20;$i++){Queue-Result (New-Result 'RUNNING')}
        Assert-Throws { Wait-AceFirmwareResult 'ssh.exe' 'root@192.0.2.1' $remote $log (New-Result 'RUNNING') } 'ace_poll_limit'
        Assert-True ($script:calls.Count-eq20 -and (Count-Starts)-eq0) 'Unbounded poll or restart'
    }
    Test-Case 'device_display_neutralizes_control_characters' {
        $safe=Get-AceSafeDisplay ("PLA`n" + [char]27 + '[31m')
        Assert-True ($safe -notmatch '[\x00-\x1f\x7f-\x9f]') 'Terminal controls retained'
        Assert-True ((Get-AceSafeDisplay ('x'*500)).Length-eq183) 'Unbounded device display'
    }
} finally {
    $resolved=[IO.Path]::GetFullPath($testRoot)
    $parent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if($resolved.StartsWith($parent,[StringComparison]::OrdinalIgnoreCase) -and (Split-Path $resolved -Leaf)-match'^U1AceWizardTests-[a-f0-9]{32}$') {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
[Console]::WriteLine('All ' + $passed + ' offline ACE firmware wizard tests passed.')
