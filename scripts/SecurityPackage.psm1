Set-StrictMode -Version Latest

function Assert-LocalPath([string]$Path) {
    if ($Path -notmatch '^[A-Za-z]:\\' -or $Path.Substring(2).Contains(':') -or $Path.Contains('/') -or $Path.Contains('..')) { throw 'Absolute local drive path required' }
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    while ($null -ne $item) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Reparse point forbidden' }
        if ($item -is [IO.DirectoryInfo]) { $item = $item.Parent } else { $item = $item.Directory }
    }
}

function Assert-ProtectedAcl([string]$Path, [string]$IdentitySid) {
    $acl = Get-Acl -LiteralPath $Path -ErrorAction Stop
    $trusted = @($IdentitySid, 'S-1-5-18', 'S-1-5-32-544')
    if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin $trusted) { throw 'Untrusted owner' }
    # Reject any untrusted allow ACE capable of data, metadata, ACL or deletion changes.
    $writeMask = [int64]0x000D0156
    foreach ($ace in $acl.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier])) {
        if ($ace.AccessControlType -eq 'Allow' -and $ace.IdentityReference.Value -notin $trusted -and (([int64]$ace.FileSystemRights -band $writeMask) -ne 0)) {
            # InheritOnly cannot modify this object itself.
            if (($ace.PropagationFlags -band [Security.AccessControl.PropagationFlags]::InheritOnly) -eq 0) { throw 'Untrusted writable ACL' }
        }
    }
}

function Read-BoundedBytes([string]$Path, [long]$Limit) {
    $stream = [IO.File]::Open($Path, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    try {
        if ($stream.Length -gt $Limit -or $stream.Length -lt 1) { throw 'Input size out of bounds' }
        $bytes = New-Object byte[] ([int]$stream.Length)
        $offset = 0
        while ($offset -lt $bytes.Length) {
            $count = $stream.Read($bytes, $offset, $bytes.Length - $offset)
            if ($count -eq 0) { throw 'Input truncated' }
            $offset += $count
        }
        return ,$bytes
    } finally { $stream.Dispose() }
}

function Test-UnifiedPackageSignature {
    param([byte[]]$Bytes, [byte[]]$SignatureBytes, [string]$PublisherSha256)
    if ($Bytes.Length -lt 1 -or $Bytes.Length -gt 1048576 -or $SignatureBytes.Length -lt 1 -or $SignatureBytes.Length -gt 262144 -or $PublisherSha256 -cnotmatch '^[0-9a-f]{64}$') { throw 'Signature input bounds/pin' }
    Add-Type -AssemblyName System.Security
    if ($PSVersionTable.PSEdition -eq 'Core') { Add-Type -AssemblyName System.Security.Cryptography.Pkcs }
    $cms = New-Object Security.Cryptography.Pkcs.SignedCms((New-Object Security.Cryptography.Pkcs.ContentInfo(,$bytes)), $true)
    $cms.Decode($SignatureBytes)
    if ($cms.SignerInfos.Count -ne 1) { throw 'Exactly one signer required' }
    $signer = $cms.SignerInfos[0]
    if ($signer.DigestAlgorithm.Value -ne '2.16.840.1.101.3.4.2.1') { throw 'SHA256 signature required' }
    $cms.CheckSignature($true) # Signature only: offline pin is the trust anchor, no chain/revocation network.
    $cert = $signer.Certificate
    if ($null -eq $cert -or [DateTime]::UtcNow -lt $cert.NotBefore.ToUniversalTime() -or [DateTime]::UtcNow -gt $cert.NotAfter.ToUniversalTime()) { throw 'Signer certificate missing or expired' }
    $sha = [Security.Cryptography.SHA256]::Create()
    try { $pin = ([BitConverter]::ToString($sha.ComputeHash($cert.RawData))).Replace('-', '').ToLowerInvariant() } finally { $sha.Dispose() }
    if ($pin -cne $PublisherSha256) { throw 'Publisher pin mismatch' }
}

function Test-UnifiedSecurityPackage {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)][string]$Manifest,
        [Parameter(Mandatory)][string]$Signature,
        [Parameter(Mandatory)][string]$PublisherSha256,
        [Parameter(Mandatory)][string]$ExpectedIdentitySid
    )
    $ErrorActionPreference = 'Stop'
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'Windows required' }
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    if ($ExpectedIdentitySid -cne $identity) { throw 'Process identity mismatch' }
    if ($PublisherSha256 -cnotmatch '^[0-9a-f]{64}$') { throw 'Explicit SHA256 publisher pin required' }
    foreach ($path in @($Root, $Manifest, $Signature)) { Assert-LocalPath $path
        $ancestor = Get-Item -LiteralPath $path -Force
        while ($null -ne $ancestor) {
            Assert-ProtectedAcl $ancestor.FullName $identity
            if ($ancestor -is [IO.DirectoryInfo]) { $ancestor = $ancestor.Parent } else { $ancestor = $ancestor.Directory }
        } }
    if (!(Get-Item -LiteralPath $Root).PSIsContainer) { throw 'Root must be a directory' }
    Add-Type -AssemblyName System.Security
    if ($PSVersionTable.PSEdition -eq 'Core') { Add-Type -AssemblyName System.Security.Cryptography.Pkcs }
    $bytes = Read-BoundedBytes $Manifest 1048576
    Test-UnifiedPackageSignature -Bytes $bytes -SignatureBytes (Read-BoundedBytes $Signature 262144) -PublisherSha256 $PublisherSha256
    $utf8 = New-Object Text.UTF8Encoding($false, $true)
    $data = $utf8.GetString($bytes) | ConvertFrom-Json
    if ($data.schema -cne 'unified.windows-package-lock.v1' -or $data.identity_sid -cne $identity) { throw 'Manifest schema or identity mismatch' }
    if ($data.requirements.powershell -cne '5.1,7' -or $data.requirements.postgresql_major -ne 18) { throw 'PS5.1/7 and PG18 contract required' }
    if ($data.artifacts -isnot [Array] -or $data.artifacts.Count -lt 1 -or $data.artifacts.Count -gt 32) { throw 'Artifact count out of bounds' }
    $seen = @{}
    $dependencies = @{}
    $total = [long]0
    $rootPath = [IO.Path]::GetFullPath($Root).TrimEnd('\') + '\'
    foreach ($artifact in $data.artifacts) {
        $relative = $artifact.path
        if ($artifact.dependency -notin @('python','postgresql','openssh','tailscale','service-wrapper') -or $dependencies.ContainsKey($artifact.dependency)) { throw 'Unknown or duplicate dependency' }
        $dependencies[$artifact.dependency] = $true
        if ($artifact.version -isnot [string] -or !$artifact.version -or $artifact.version.Length -gt 80 -or ($artifact.dependency -eq 'postgresql' -and $artifact.version.Split('.')[0] -cne '18')) { throw 'Invalid dependency version' }
        if ($artifact.publisher_sha256 -cnotmatch '^[0-9a-f]{64}$') { throw 'Package publisher pin required' }
        if ($relative -isnot [string] -or $relative.Length -gt 240 -or $relative -notmatch '^[A-Za-z0-9_-][A-Za-z0-9_./-]*$') { throw 'Invalid relative artifact path' }
        foreach ($part in $relative.Split('/')) {
            if (!$part -or $part -in @('.', '..') -or $part.EndsWith('.') -or $part -match '^(?i:CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(?:\.|$)') { throw 'Unsafe artifact component' }
        }
        if ($seen.ContainsKey($relative)) { throw 'Duplicate artifact path' }
        $seen[$relative] = $true
        if ($artifact.sha256 -isnot [string] -or $artifact.sha256 -cnotmatch '^[0-9a-f]{64}$') { throw 'Invalid digest' }
        if (($artifact.bytes -isnot [int] -and $artifact.bytes -isnot [long]) -or $artifact.bytes -lt 1 -or $artifact.bytes -gt 536870912) { throw 'Invalid artifact size' }
        $total += $artifact.bytes
        if ($total -gt 1073741824) { throw 'Aggregate artifact limit exceeded' }
        $path = [IO.Path]::GetFullPath((Join-Path $rootPath $relative.Replace('/', '\')))
        if (!$path.StartsWith($rootPath, [StringComparison]::OrdinalIgnoreCase)) { throw 'Artifact escapes root' }
        Assert-LocalPath $path
        $parent = Get-Item -LiteralPath $path
        while ($null -ne $parent -and $parent.FullName.Length -ge $rootPath.TrimEnd('\').Length) {
            Assert-ProtectedAcl $parent.FullName $identity
            if ($parent -is [IO.DirectoryInfo]) { $parent = $parent.Parent } else { $parent = $parent.Directory }
        }
        $stream = [IO.File]::Open($path, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
        try {
            if ($stream.Length -ne $artifact.bytes) { throw 'Artifact size mismatch' }
            $sha = [Security.Cryptography.SHA256]::Create()
            try { $actual = ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-', '').ToLowerInvariant() } finally { $sha.Dispose() }
            if ($actual -cne $artifact.sha256) { throw 'Artifact digest mismatch' }
        } finally { $stream.Dispose() }
    }
    if ($dependencies.Count -ne 5) { throw 'Dependency closure missing' }
    [pscustomobject]@{mode='DRY_RUN_ONLY'; signature='PINNED_SIGNATURE_VERIFIED'; source_provenance='NOT_EVALUATED'; production='NO_GO'; namespace_trust='UNVERIFIED'; artifacts=$data.artifacts.Count; mutations_performed=$false; physical_acceptance='NOT_AUTHORIZED'; admission='NOT_GRANTED'}
}
Export-ModuleMember -Function Test-UnifiedSecurityPackage, Test-UnifiedPackageSignature
