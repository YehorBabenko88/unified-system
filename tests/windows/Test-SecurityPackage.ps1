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
  # Real detached CMS signatures bind each schema and inventory before contract validation.
  foreach ($schema in @('unified.windows-package-lock.v1','unified.windows-package-lock.v2')) {
    $names = if ($schema.EndsWith('.v1')) { @('grid','strattester','unified','terminan','math') } else { @('unified-system','grid','strattester','math','meta_analyse','terminan') }
    $sources = [ordered]@{}
    foreach ($name in $names) { $sources[$name] = @{commit=('a'*40);tree=('b'*40)} }
    $manifest = @{schema=$schema;identity_sid='S-1-5-21-100';sources=$sources;requirements=@{powershell='5.1,7';postgresql_major=18}}
    $manifestBytes = [Text.Encoding]::UTF8.GetBytes(($manifest | ConvertTo-Json -Depth 8 -Compress))
    $manifestCms = New-Object Security.Cryptography.Pkcs.SignedCms((New-Object Security.Cryptography.Pkcs.ContentInfo(,$manifestBytes)),$true)
    $manifestCms.ComputeSignature($signer)
    Test-UnifiedPackageSignature $manifestBytes $manifestCms.Encode() $pin
    $parsed = [Text.Encoding]::UTF8.GetString($manifestBytes) | ConvertFrom-Json
    & $module {param($data) Assert-UnifiedManifestContract $data 'S-1-5-21-100'} $parsed
    Reject { Test-UnifiedPackageSignature ([Text.Encoding]::UTF8.GetBytes('{}')) $manifestCms.Encode() $pin }
    foreach ($name in $names) {
      $bad = [Text.Encoding]::UTF8.GetString($manifestBytes) | ConvertFrom-Json
      $bad.sources.PSObject.Properties.Remove($name)
      Reject { & $module {param($data) Assert-UnifiedManifestContract $data 'S-1-5-21-100'} $bad }
    }
    foreach ($mutation in @('extra','alias','schema','downgrade','source-type','pin','pg','ps','identity')) {
      $bad = [Text.Encoding]::UTF8.GetString($manifestBytes) | ConvertFrom-Json
      switch ($mutation) {
        'extra' { $bad.sources | Add-Member -NotePropertyName unknown -NotePropertyValue @{commit=('a'*40);tree=('b'*40)} }
        'alias' { $name = if ($schema.EndsWith('.v2')) {'unified-system'} else {'unified'}; $bad.sources.PSObject.Properties.Remove($name); $bad.sources | Add-Member -NotePropertyName UNIFIED -NotePropertyValue @{commit=('a'*40);tree=('b'*40)} }
        'schema' { $bad.schema = 'unified.windows-package-lock.v3' }
        'downgrade' { $bad.schema = if ($schema.EndsWith('.v2')) {'unified.windows-package-lock.v1'} else {'unified.windows-package-lock.v2'} }
        'source-type' { $bad.sources = @() }
        'pin' { $bad.sources.grid.commit = $true }
        'pg' { $bad.requirements.postgresql_major = '18' }
        'ps' { $bad.requirements.powershell = '7' }
        'identity' { $bad.identity_sid = 'admin' }
      }
      Reject { & $module {param($data) Assert-UnifiedManifestContract $data 'S-1-5-21-100'} $bad }
    }
  }
  foreach ($path in @('../x','//server/share','C:/outside','C:\x:ads')) {Reject {& $module {param($p) Assert-LocalPath $p} $path}}
  & $module { Assert-AclFacts 'S-1-5-21-100' 'S-1-5-21-100' @() }
  Reject { & $module { Assert-AclFacts 'S-1-1-0' 'S-1-5-21-100' @() } }
  foreach ($right in @([int64]2,[int64]4,[int64]16,[int64]64,[int64]256,[int64]65536,[int64]262144,[int64]524288)) {
    Reject { & $module { param($r) Assert-AclFacts 'S-1-5-21-100' 'S-1-5-21-100' @([pscustomobject]@{Type='Allow';Sid='S-1-1-0';Rights=$r;InheritOnly=$false}) } $right }
  }
  & $module { Assert-AclFacts 'S-1-5-21-100' 'S-1-5-21-100' @([pscustomobject]@{Type='Allow';Sid='S-1-1-0';Rights=[int64]2;InheritOnly=$true}) }
  Write-Output "PASS in-memory synthetic signatures ($($PSVersionTable.PSVersion)); physical NOT_RUN"
} finally {if ($null -ne $cert) {$cert.Dispose()}; $rsa.Dispose()}
