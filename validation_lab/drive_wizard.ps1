# SPDX-License-Identifier: GPL-3.0-only
# Lab input driver only. Production network, process, and install functions stay unchanged.
param(
    [Parameter(Mandatory=$true)][string]$BundleRoot,
    [Parameter(Mandatory=$true)][string]$LogRoot,
    [ValidateSet('fresh','update')][string]$Scenario = 'fresh',
    [ValidateSet('en','zh')][string]$Language = 'en'
)
$ErrorActionPreference = 'Stop'
if (-not $IsLinux -or $env:CI -ne 'true' -or $env:GITHUB_ACTIONS -ne 'true' -or
    $env:GITHUB_REPOSITORY -ne 'Alexantry/Ultimate-U1-ACE-link' -or
    $env:U1_ACE_LAB_TOKEN -notmatch '^[a-f0-9]{32}$') {
    throw 'VM lab requires its disposable GitHub Linux environment.'
}
$permissionPath = '/run/ultimate-u1-ace-link-vm-lab/permission.json'
$permission = Get-Content -LiteralPath $permissionPath -Raw | ConvertFrom-Json
if ($permission.scope -ne 'vm-software-flow' -or $permission.token -cne $env:U1_ACE_LAB_TOKEN -or
    [string]$permission.run_id -cne $env:GITHUB_RUN_ID) { throw 'VM lab permission mismatch.' }
# Reuse the real fixture gate for root, namespace, marker ownership/type/mode,
# and initialized guest state before loading any production UI code.
& /usr/bin/python3 (Join-Path $PSScriptRoot 'guest.py') snapshot | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'The isolated guest safety gate refused this run.' }
. (Join-Path $BundleRoot 'Install.ps1') -LibraryOnly
$languageNumber = '2'
if ($Language -eq 'zh') { $languageNumber = '1' }
$script:LabAnswers = New-Object 'System.Collections.Generic.Queue[string]'
$answers = @($languageNumber, '1', '1', '1', '127.0.0.1')
if ($Scenario -eq 'fresh') {
    # The test fixture assumes the exact ACE target firmware; no flash is attempted.
    $answers += @('2', '1', '1', '1370', '1210')
}
$answers += @('1', '1')
foreach ($answer in $answers) { $script:LabAnswers.Enqueue($answer) }
function Read-Host {
    param([string]$Prompt)
    if ($script:LabAnswers.Count -eq 0) { throw ('Unexpected input request: ' + $Prompt) }
    $answer = $script:LabAnswers.Dequeue()
    Write-Host ('LAB INPUT: ' + $Prompt + ' => ' + $answer)
    return $answer
}
$result = Start-U1Wizard -BundleRoot $BundleRoot -LocalLogRoot $LogRoot
if ($result -ne 0) { throw ('Production wizard returned ' + $result) }
if ($script:LabAnswers.Count -ne 0) { throw 'The production wizard did not consume the expected inputs.' }
[Console]::WriteLine('LAB_WIZARD_EXIT=0')
