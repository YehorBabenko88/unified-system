[CmdletBinding()]
param(
 [Parameter(Mandatory=$true)][string]$Template,
 [Parameter(Mandatory=$true)][string]$ArtifactRoot,
 [Parameter(Mandatory=$true)][string]$OutputDirectory,
 [Parameter(Mandatory=$true)][string]$CertificateThumbprint,
 [Parameter(Mandatory=$true)][string]$ExpectedPublisherSha256,
 [string]$Python = 'python'
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
# Preparation/signing only; never fetch, publish, install or start a service.
if ($ExpectedPublisherSha256 -cnotmatch '^[0-9a-f]{64}$') { throw 'External publisher pin required' }
if (Test-Path -LiteralPath $OutputDirectory) { throw 'New output directory required' }
$cert=Get-Item -LiteralPath ("Cert:\CurrentUser\My\"+$CertificateThumbprint)
if (!$cert.HasPrivateKey) { throw 'Separately provisioned signing key required' }
$sha=[Security.Cryptography.SHA256]::Create()
try { $pin=([BitConverter]::ToString($sha.ComputeHash($cert.RawData))).Replace('-','').ToLowerInvariant() } finally {$sha.Dispose()}
if ($pin -cne $ExpectedPublisherSha256) { throw 'Signer is not independently pinned publisher' }
$stage=New-Item -ItemType Directory -Path $OutputDirectory
$modules=New-Item -ItemType Directory -Path (Join-Path $stage.FullName 'modules')
try {
 foreach($name in @('unified-system','grid','strattester','math','meta_analyse','terminan')) {
  Copy-Item -LiteralPath (Join-Path $ArtifactRoot ("modules/"+$name+'.zip')) -Destination (Join-Path $modules.FullName ($name+'.zip')) -ErrorAction Stop
 }
 # Python owns canonical bytes and closure validation; avoid PS5.1 JSON ordering/encoding differences.
 $code=@'
import hashlib,sys,pathlib,json
from unified_system.release_manifest import canonical,validate_manifest
m=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))
validate_manifest(m,expected_publisher=sys.argv[3])
root=pathlib.Path(sys.argv[2])
for module in m['modules'].values():
 p=root/module['artifact']['path'];a=module['artifact']
 if p.stat().st_size!=a['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=a['sha256']:raise ValueError('artifact mismatch')
(root/'release.json').write_bytes(canonical(m))
'@
 & $Python -c $code $Template $stage.FullName $ExpectedPublisherSha256
 if ($LASTEXITCODE -ne 0) { throw 'Release closure/artifacts rejected' }
 Import-Module (Join-Path $PSScriptRoot 'SecurityPackage.psm1') -Force
 Add-Type -AssemblyName System.Security
 if($PSVersionTable.PSEdition -eq 'Core'){Add-Type -AssemblyName System.Security.Cryptography.Pkcs}
 $bytes=[IO.File]::ReadAllBytes((Join-Path $stage.FullName 'release.json'))
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
}
