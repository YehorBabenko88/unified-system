# Qualifies collection on a disposable hosted runner, never ADMINIT acceptance.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -cne 'true' -or $env:RUNNER_ENVIRONMENT -cne 'github-hosted' -or $env:RUNNER_OS -cne 'Windows' -or !$env:RUNNER_TEMP -or $env:COMPUTERNAME -match '^(?i:ADMINIT|LS5|PC4)$') { throw 'Disposable hosted Windows CI required' }
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
foreach ($name in @('scripts/Collect-AdminitInventory.ps1','scripts/Build-UnifiedRelease.ps1')) {
    $tokens=$null; $errors=$null
    [Management.Automation.Language.Parser]::ParseFile((Join-Path $root $name),[ref]$tokens,[ref]$errors) | Out-Null
    if ($errors.Count -ne 0) { throw ('Native parser rejected '+$name) }
}
# This collector reads the current ephemeral runner only; no remote parameter.
$raw = & (Join-Path $root 'scripts/Collect-AdminitInventory.ps1')
$inventory = $raw | ConvertFrom-Json
if ($inventory.node -eq 'ADMINIT') { throw 'Physical target forbidden' }
$file = Join-Path $env:RUNNER_TEMP ('inventory-check-'+[Guid]::NewGuid().ToString('N')+'.json')
try {
    [IO.File]::WriteAllText($file,($inventory | ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
    $code=@'
import json,sys
from unified_system.adminit_acceptance import check_inventory
with open(sys.argv[1],encoding='utf-8') as f: inventory=json.load(f)
r=check_inventory(inventory)
assert r['status']=='BLOCKED' and 'WRONG_LOCAL_HOST' in r['issues']
assert r['physical_execution'] is False and r['deployment_authorized'] is False
'@
    & python -c $code $file
    if ($LASTEXITCODE -ne 0) { throw 'Native inventory contract rejected' }
} finally {
    if ([IO.File]::Exists($file)) { [IO.File]::Delete($file) }
}
Write-Output ('PASS EPHEMERAL_RUNNER_INVENTORY_CONTRACT PS'+$PSVersionTable.PSVersion+'; ADMINIT=NOT_RUN; physical=NOT_AUTHORIZED')
