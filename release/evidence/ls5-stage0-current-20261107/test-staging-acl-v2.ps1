$ErrorActionPreference='Stop'
$env:PSModulePath=[IO.Path]::Combine([Environment]::SystemDirectory,'WindowsPowerShell/v1.0/Modules')
$w=$PSScriptRoot
$r=Get-Content -LiteralPath (Join-Path $w 'test-directory-v2.json') -Raw|ConvertFrom-Json
$path=$r.directory;$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
Import-Module (Join-Path $w 'SecurityPackage.psm1') -Force
$m=Get-Module SecurityPackage
$o=[ordered]@{schema='unified.actual-staging-acl-observation.v1';path=$path;identity_sid=$sid;observed_at_utc=[DateTime]::UtcNow.ToString('o');powershell=$PSVersionTable.PSVersion.ToString();namespace='NOT_RUN';acl='NOT_RUN';acl_changed=$false;admission='NOT_GRANTED'}
try {&$m {param($p) Assert-LocalPath $p} $path;$o.namespace='OBSERVED_NO_REPARSE_FIXED_LOCAL_PATH'}catch{$o.namespace='REJECTED';$o.namespace_error=$_.Exception.Message}
try {&$m {param($p,$s) Assert-ProtectedAcl $p $s} $path $sid;$o.acl='CHECK_PASSED_NOT_INSTALLATION_ADMISSION'}catch{$o.acl='REJECTED';$o.acl_error=$_.Exception.Message}
$o.backup_access_services=@(Get-CimInstance Win32_Service|Where-Object {$_.Name -match '^(TeamViewer|sshd|WinRM|TermService)$'}|Select-Object Name,State,StartMode,StartName)
$o.backup_admin_access='NOT_DEMONSTRATED_END_TO_END'
[IO.File]::WriteAllText((Join-Path $w 'actual-staging-acl-v2.json'),($o|ConvertTo-Json -Depth 6),(New-Object Text.UTF8Encoding($false)))
$o|ConvertTo-Json -Depth 6
