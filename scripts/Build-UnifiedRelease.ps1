[CmdletBinding()]
param(
 [Parameter(Mandatory=$true)][string]$Template,
 [Parameter(Mandatory=$true)][string]$ArtifactRoot,
 [Parameter(Mandatory=$true)][string]$OutputDirectory,
 [string]$CertificateThumbprint,
 [Parameter(Mandatory=$true)][string]$ExpectedPublisherSha256,
 [Parameter(Mandatory=$true)][string]$Python,
 [Parameter(Mandatory=$true)][string]$PythonSha256,
 [Parameter(Mandatory=$true)][string]$PreparationSha256,
 [Parameter(Mandatory=$true)][string]$SourceRoot,
 [Parameter(Mandatory=$true)][string]$SourcePinsPath,
 [Parameter(Mandatory=$true)][string]$SourcePinsSha256,
 [Parameter(Mandatory=$true)][string]$SecurityModuleSha256,
 [switch]$PrepareOnly
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
# Preparation/signing only; never fetch, publish, install or start a service.
if ($ExpectedPublisherSha256 -cnotmatch '^[0-9a-f]{64}$') { throw 'External publisher pin required' }
if (Test-Path -LiteralPath $OutputDirectory) { throw 'New output directory required' }
$preparer=Join-Path $PSScriptRoot 'prepare_unified_release.py'
$securityModule=Join-Path $PSScriptRoot 'SecurityPackage.psm1'
$locks=New-Object 'Collections.Generic.List[IDisposable]'
function Assert-ReleaseLocalPath([string]$Path){
 if($Path -notmatch '^[A-Za-z]:\\' -or $Path.Contains('..') -or $Path.Substring(2).Contains(':')){throw 'RELEASE_PREPARATION_REJECTED'}
 $anchor=[IO.Path]::GetPathRoot($Path)
 if([IO.DriveInfo]::new($anchor).DriveType -ne [IO.DriveType]::Fixed){throw 'RELEASE_PREPARATION_REJECTED'}
 $parts=New-Object 'Collections.Generic.List[string]';$cursor=[IO.Path]::GetFullPath($Path)
 while($cursor){$parts.Add($cursor);$next=[IO.Path]::GetDirectoryName($cursor.TrimEnd('\'));if($next -eq $cursor){break};$cursor=$next}
 for($i=$parts.Count-1;$i -ge 0;$i--){$item=Get-Item -LiteralPath $parts[$i] -Force;if(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'RELEASE_PREPARATION_REJECTED'}}
}
try {
 foreach($pair in @(@($Python,$PythonSha256),@($preparer,$PreparationSha256),@($SourcePinsPath,$SourcePinsSha256),@($securityModule,$SecurityModuleSha256))) {
  Assert-ReleaseLocalPath $pair[0]
  if($pair[1] -cnotmatch '^[0-9a-f]{64}$'){throw 'RELEASE_PREPARATION_REJECTED'}
  # Retain read handles denying writes/deletion until execution/signing finishes.
  $stream=[IO.File]::Open($pair[0],[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read);$locks.Add($stream)
  if($stream.Length -lt 1 -or $stream.Length -gt 67108864){throw 'RELEASE_PREPARATION_REJECTED'}
  $sha=[Security.Cryptography.SHA256]::Create()
  try{$actual=([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
  if($actual -cne $pair[1]){throw 'RELEASE_PREPARATION_REJECTED'}
 }
 $stage=New-Item -ItemType Directory -Path $OutputDirectory
 # No certificate-provider or private-key access before pinned isolated closure.
 Push-Location -LiteralPath $stage.FullName
 try {$prepared=& $Python -I -S -B $preparer --source-root $SourceRoot --source-pins $SourcePinsPath --source-pins-sha256 $SourcePinsSha256 --template $Template --artifact-root $ArtifactRoot --output $stage.FullName --publisher $ExpectedPublisherSha256; $result=$LASTEXITCODE} finally {Pop-Location}
 if ($result -ne 0) { throw 'RELEASE_PREPARATION_REJECTED' }
 $proof=$prepared|ConvertFrom-Json
 if($proof.schema -cne 'unified.release.preparation.v1' -or $proof.signed -ne $false -or $proof.modules -ne 6 -or $proof.release_sha256 -cnotmatch '^[0-9a-f]{64}$'){throw 'RELEASE_PREPARATION_REJECTED'}
 $manifestStream=[IO.File]::Open((Join-Path $stage.FullName 'release.json'),[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read);$locks.Add($manifestStream)
 if($manifestStream.Length -lt 1 -or $manifestStream.Length -gt 1048576){throw 'RELEASE_PREPARATION_REJECTED'}
 $bytes=New-Object byte[] ([int]$manifestStream.Length);$offset=0
 while($offset -lt $bytes.Length){$count=$manifestStream.Read($bytes,$offset,$bytes.Length-$offset);if($count -le 0){throw 'RELEASE_PREPARATION_REJECTED'};$offset+=$count}
 $sha=[Security.Cryptography.SHA256]::Create()
 try{$manifestHash=([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
 if($manifestHash -cne $proof.release_sha256){throw 'RELEASE_PREPARATION_REJECTED'}
 if($PrepareOnly){Write-Output 'PREPARED_UNSIGNED_RELEASE; signing=NOT_RUN; deployment=NOT_AUTHORIZED';return}
 if($CertificateThumbprint -cnotmatch '^[0-9a-fA-F]{40}$'){throw 'Separately provisioned signing key required'}
 Import-Module $securityModule -Force
 $cert=Get-Item -LiteralPath ("Cert:\CurrentUser\My\"+$CertificateThumbprint)
 [void](Test-UnifiedCodeSigningPublisher $cert $ExpectedPublisherSha256)
 if (!$cert.HasPrivateKey) { throw 'Separately provisioned signing key required' }
 $sha=[Security.Cryptography.SHA256]::Create()
 try { $pin=([BitConverter]::ToString($sha.ComputeHash($cert.RawData))).Replace('-','').ToLowerInvariant() } finally {$sha.Dispose()}
 if ($pin -cne $ExpectedPublisherSha256) { throw 'Signer is not independently pinned publisher' }
 Add-Type -AssemblyName System.Security
 if($PSVersionTable.PSEdition -eq 'Core'){Add-Type -AssemblyName System.Security.Cryptography.Pkcs}
 $cms=New-Object Security.Cryptography.Pkcs.SignedCms((New-Object Security.Cryptography.Pkcs.ContentInfo(,$bytes)),$true)
 $signer=New-Object Security.Cryptography.Pkcs.CmsSigner($cert)
 $signer.DigestAlgorithm=New-Object Security.Cryptography.Oid('2.16.840.1.101.3.4.2.1')
 $cms.ComputeSignature($signer)
 [IO.File]::WriteAllBytes((Join-Path $stage.FullName 'release.p7s'),$cms.Encode())
 Test-UnifiedPackageSignature -Bytes $bytes -SignatureBytes $cms.Encode() -PublisherSha256 $ExpectedPublisherSha256
 Write-Output 'PREPARED_SIGNED_RELEASE; deployment=NOT_AUTHORIZED; publisher_pin=EXTERNALLY_SUPPLIED'
} catch {
 # Preserve failed preparation for review; no recursive delete of user paths.
 throw
} finally {
 foreach($stream in $locks){$stream.Dispose()}
}
