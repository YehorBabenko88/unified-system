$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../../scripts/SecurityPackage.psm1') -Force
Add-Type -AssemblyName System.Security
if ($PSVersionTable.PSEdition -eq 'Core') { Add-Type -AssemblyName System.Security.Cryptography.Pkcs }
$rsa=[Security.Cryptography.RSA]::Create(2048)
$cert=$null
try {
  $request=New-Object Security.Cryptography.X509Certificates.CertificateRequest('CN=CI Disposable Only',$rsa,[Security.Cryptography.HashAlgorithmName]::SHA256,[Security.Cryptography.RSASignaturePadding]::Pkcs1)
  $cert=$request.CreateSelfSigned([DateTimeOffset]::UtcNow.AddDays(-1),[DateTimeOffset]::UtcNow.AddDays(1))
  $bytes=[Text.Encoding]::UTF8.GetBytes('{"synthetic":true}')
  $cms=New-Object Security.Cryptography.Pkcs.SignedCms((New-Object Security.Cryptography.Pkcs.ContentInfo(,$bytes)),$true)
  $signer=New-Object Security.Cryptography.Pkcs.CmsSigner($cert)
  $signer.DigestAlgorithm=New-Object Security.Cryptography.Oid('2.16.840.1.101.3.4.2.1')
  $cms.ComputeSignature($signer)
  $sha=[Security.Cryptography.SHA256]::Create()
  try {$pin=([BitConverter]::ToString($sha.ComputeHash($cert.RawData))).Replace('-','').ToLowerInvariant()} finally {$sha.Dispose()}
  $signature=$cms.Encode()
  Test-UnifiedPackageSignature $bytes $signature $pin
  function Reject([scriptblock]$action) {$rejected=$false; try {& $action} catch {$rejected=$true}; if (!$rejected) {throw 'Expected rejection'}}
  Reject {Test-UnifiedPackageSignature $bytes $signature ('0'*64)}
  Reject {Test-UnifiedPackageSignature ([Text.Encoding]::UTF8.GetBytes('tamper')) $signature $pin}
  Reject {Test-UnifiedPackageSignature $bytes ([byte[]]@(1,2,3)) $pin}
  Reject {Test-UnifiedPackageSignature ([byte[]]@()) $signature $pin}
  Reject {Test-UnifiedPackageSignature $bytes $signature 'latest'}
  $module=Get-Module SecurityPackage
  foreach ($path in @('../x','//server/share','C:/outside','C:\x:ads')) {Reject {& $module {param($p) Assert-LocalPath $p} $path}}
  Write-Output "PASS in-memory synthetic signatures ($($PSVersionTable.PSVersion)); physical NOT_RUN"
} finally {if ($null -ne $cert) {$cert.Dispose()}; $rsa.Dispose()}
