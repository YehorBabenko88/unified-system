$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot '../../scripts/WindowsDryRun.psm1') -Force
Add-Type -AssemblyName System.Security
if ($PSVersionTable.PSEdition -eq 'Core') { Add-Type -AssemblyName System.Security.Cryptography.Pkcs }
$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ('unified-dryrun-' + [Guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $tempRoot
try {
    $sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $privateAcl = New-Object Security.AccessControl.DirectorySecurity
    $privateAcl.SetOwner((New-Object Security.Principal.SecurityIdentifier($sid)))
    $privateAcl.SetAccessRuleProtection($true, $false)
    foreach ($trustedSid in @($sid, 'S-1-5-18', 'S-1-5-32-544')) {
        $privateAcl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule((New-Object Security.Principal.SecurityIdentifier($trustedSid)), 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')))
    }
    Set-Acl -LiteralPath $tempRoot -AclObject $privateAcl
    $rsa = [Security.Cryptography.RSA]::Create(2048)
    $request = New-Object Security.Cryptography.X509Certificates.CertificateRequest('CN=Disposable Test Only', $rsa, [Security.Cryptography.HashAlgorithmName]::SHA256, [Security.Cryptography.RSASignaturePadding]::Pkcs1)
    $cert = $request.CreateSelfSigned([DateTimeOffset]::UtcNow.AddDays(-1), [DateTimeOffset]::UtcNow.AddDays(1))
    $sha = [Security.Cryptography.SHA256]::Create()
    $pin = ([BitConverter]::ToString($sha.ComputeHash($cert.RawData))).Replace('-', '').ToLowerInvariant()
    $artifact = Join-Path $tempRoot 'module.bin'
    [IO.File]::WriteAllText($artifact, 'disposable synthetic artifact')
    $hash = (Get-FileHash -LiteralPath $artifact -Algorithm SHA256).Hash.ToLowerInvariant()
    $manifest = Join-Path $tempRoot 'manifest.json'
    $signature = Join-Path $tempRoot 'manifest.p7s'
    function Write-Fixture($path = 'module.bin', $digest = $hash, $size = 29, $manifestSid = $sid) {
        $json = @{schema='unified.windows-dry-run.v1'; identity_sid=$manifestSid; artifacts=@(@{path=$path;sha256=$digest;bytes=$size})} | ConvertTo-Json -Depth 5 -Compress
        $bytes = [Text.Encoding]::UTF8.GetBytes($json)
        [IO.File]::WriteAllBytes($manifest, $bytes)
        $cms = New-Object Security.Cryptography.Pkcs.SignedCms((New-Object Security.Cryptography.Pkcs.ContentInfo(,$bytes)), $true)
        $signer = New-Object Security.Cryptography.Pkcs.CmsSigner($cert)
        $signer.DigestAlgorithm = New-Object Security.Cryptography.Oid('2.16.840.1.101.3.4.2.1')
        $cms.ComputeSignature($signer)
        [IO.File]::WriteAllBytes($signature, $cms.Encode())
    }
    function Invoke-Check($publisher = $pin, $identity = $sid) {
        Test-UnifiedDryRun -Root $tempRoot -Manifest $manifest -Signature $signature -PublisherSha256 $publisher -ExpectedIdentitySid $identity
    }
    function Reject($name, [scriptblock]$action) {
        $rejected = $false
        try { $null = & $action } catch { $rejected = $true }
        if (!$rejected) { throw "Expected rejection: $name" }
        Write-Output "PASS rejection: $name"
    }
    Write-Fixture
    $before = (Get-ChildItem $tempRoot -File | Get-FileHash | Sort-Object Path | ConvertTo-Json -Compress)
    $result = Invoke-Check
    if ($result.mode -ne 'DRY_RUN_ONLY' -or $result.mutations_performed -ne $false -or $result.physical_acceptance -ne 'NOT_AUTHORIZED' -or $result.namespace_trust -ne 'UNVERIFIED' -or $result.admission -ne 'NOT_GRANTED') { throw 'Invalid plan' }
    $after = (Get-ChildItem $tempRoot -File | Get-FileHash | Sort-Object Path | ConvertTo-Json -Compress)
    if ($before -cne $after) { throw 'Verifier mutated input' }
    Reject 'publisher pin' { Invoke-Check ('0' * 64) }
    Reject 'process identity' { Invoke-Check $pin 'S-1-5-18' }
    Write-Fixture 'module.bin' $hash 29 'S-1-5-18'
    Reject 'signed manifest identity' { Invoke-Check }
    foreach ($size in @($true, 29.5, 0, 536870913)) {
        Write-Fixture 'module.bin' $hash $size
        Reject "invalid size $size" { Invoke-Check }
    }
    Write-Fixture
    [IO.File]::WriteAllBytes($signature, [byte[]]@(1,2,3))
    Reject 'invalid signature encoding' { Invoke-Check }
    Write-Fixture
    [IO.File]::AppendAllText($manifest, ' ')
    Reject 'tampered signed bytes' { Invoke-Check }
    foreach ($bad in @('../module.bin','C:\outside.bin','module.bin:stream','\\server\share\file','sub/../module.bin','CON','module.bin.')) {
        Write-Fixture $bad
        Reject "unsafe path $bad" { Invoke-Check }
    }
    Write-Fixture 'module.bin' ('0' * 64)
    Reject 'artifact digest' { Invoke-Check }
    Write-Fixture 'module.bin' $hash 28
    Reject 'artifact size mismatch' { Invoke-Check }
    Write-Fixture
    $link = Join-Path $tempRoot 'link'
    $null = New-Item -ItemType Junction -Path $link -Target $tempRoot
    Write-Fixture 'link/module.bin'
    Reject 'reparse ancestor' { Invoke-Check }
    [IO.Directory]::Delete($link)
    Write-Fixture
    $acl = Get-Acl -LiteralPath $artifact
    $originalAcl = $acl.GetSecurityDescriptorSddlForm('All')
    $rule = New-Object Security.AccessControl.FileSystemAccessRule((New-Object Security.Principal.SecurityIdentifier('S-1-1-0')), 'Write', 'Allow')
    $acl.AddAccessRule($rule)
    Set-Acl -LiteralPath $artifact -AclObject $acl
    Reject 'Everyone writable artifact' { Invoke-Check }
    $acl.SetSecurityDescriptorSddlForm($originalAcl)
    Set-Acl -LiteralPath $artifact -AclObject $acl
    $null = Invoke-Check
    Write-Output "PASS Windows dry-run synthetic checks ($($PSVersionTable.PSVersion))"
} finally {
    $resolvedTemp = [IO.Path]::GetFullPath($tempRoot)
    $allowedTemp = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    if (!$resolvedTemp.StartsWith($allowedTemp, [StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolvedTemp) -notmatch '^unified-dryrun-[0-9a-f]{32}$') { throw 'Refusing cleanup outside disposable fixture' }
    if (Test-Path -LiteralPath (Join-Path $tempRoot 'link')) { [IO.Directory]::Delete((Join-Path $tempRoot 'link')) }
    Remove-Item -LiteralPath $tempRoot -Recurse -Force
}
