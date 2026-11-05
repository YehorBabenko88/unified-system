# Preparation only; native parser/execution NOT_RUN. Separate owner grant required.
# Local reads and JSON stdout only. No dependency binary is executed.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($args.Count -ne 0) { throw 'No arguments accepted; local inventory only' }
$drive = Get-CimInstance -ClassName Win32_LogicalDisk -Filter "DeviceID='C:'"
if ($null -eq $drive -or $drive.DriveType -ne 3) { throw 'Fixed local C drive required' }
function Get-LocalPathState([string]$Path) {
    if ($Path -notmatch '^C:\\' -or $Path.Contains('/') -or $Path.Substring(3).Contains(':')) { return 'BLOCKED' }
    $parts = @($Path.Substring(3).Split('\') | Where-Object { $_ -ne '' })
    if (@($parts | Where-Object { $_ -eq '.' -or $_ -eq '..' }).Count -ne 0) { return 'BLOCKED' }
    $current = 'C:\'
    # Check each parent before ever accessing a child. Missing/blocked parents
    # stop traversal. Reparse points are never followed intentionally.
    foreach ($part in @('') + $parts) {
        if ($part -ne '') { $current = Join-Path $current $part }
        try { $item = Get-Item -LiteralPath $current -Force -ErrorAction Stop }
        catch [System.Management.Automation.ItemNotFoundException] { return 'ABSENT' }
        catch { return 'BLOCKED' }
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { return 'BLOCKED' }
        if ($current -ne $Path -and -not $item.PSIsContainer) { return 'BLOCKED' }
    }
    return 'REGULAR'
}
function Get-LocalDependency([string]$Path) {
    $state = Get-LocalPathState $Path
    if ($state -ne 'REGULAR') { return $null }
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { return $null }
    $version = [string]$item.VersionInfo.FileVersion
    if ([string]::IsNullOrWhiteSpace($version)) { return $null }
    return [ordered]@{ path = $Path; file_version = $version }
}
$root = 'C:\UnifiedAdminitTest'
$rootState = Get-LocalPathState $root
$pgState = 'BLOCKED'
if ($rootState -eq 'ABSENT') { $pgState = 'ABSENT' }
elseif ($rootState -eq 'REGULAR') { $pgState = Get-LocalPathState (Join-Path $root 'postgres-data') }
$rootExists = $null
$pgExists = $null
if ($rootState -ne 'BLOCKED') { $rootExists = $rootState -eq 'REGULAR' }
if ($pgState -ne 'BLOCKED') { $pgExists = $pgState -eq 'REGULAR' }
$system = Get-CimInstance -ClassName Win32_ComputerSystem
$os = Get-CimInstance -ClassName Win32_OperatingSystem
[ordered]@{
    node = [string]$system.Name
    logical_processors = [long]$system.NumberOfLogicalProcessors
    memory_bytes = [long]$system.TotalPhysicalMemory
    free_bytes = [long]$drive.FreeSpace
    os = [ordered]@{ caption = [string]$os.Caption; edition = [string]$os.OperatingSystemSKU; build = [string]$os.BuildNumber; version = [string]$os.Version; architecture = [string]$os.OSArchitecture }
    service_names = @(Get-Service | Select-Object -ExpandProperty Name)
    root_exists = $rootExists
    postgres_data_exists = $pgExists
    linked_namespace = ($rootState -eq 'BLOCKED' -or $pgState -eq 'BLOCKED')
    dependencies = [ordered]@{
        python = Get-LocalDependency 'C:\Python313\python.exe'
        node = Get-LocalDependency 'C:\Program Files\nodejs\node.exe'
        postgres = Get-LocalDependency 'C:\Program Files\PostgreSQL\18\bin\postgres.exe'
        git = Get-LocalDependency 'C:\Program Files\Git\cmd\git.exe'
    }
} | ConvertTo-Json -Depth 5
