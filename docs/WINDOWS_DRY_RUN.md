# Offline Windows signed-manifest dry-run

Workstream D freezes integration PR #1 at `50e6e63cb183f6dcf1dee3c753f966717ee3b110`. This independent branch does not update that source branch.

`scripts/WindowsDryRun.psm1` exports `Test-UnifiedDryRun` for Windows PowerShell 5.1 and PowerShell 7. It reads local inputs only. It never downloads, executes, stages, installs, configures a service/DB/network/ACL or writes a result file. Its output always has `mode=DRY_RUN_ONLY`, `admission=NOT_GRANTED`, `physical_acceptance=NOT_AUTHORIZED`.

```powershell
Import-Module ./scripts/WindowsDryRun.psm1
Test-UnifiedDryRun -Root C:\ReviewedArtifacts `
  -Manifest C:\ReviewedArtifacts\manifest.json `
  -Signature C:\ReviewedArtifacts\manifest.p7s `
  -PublisherSha256 '<64 lowercase hex SHA256 of independently trusted signer certificate DER>' `
  -ExpectedIdentitySid '<explicit expected process SID>'
```

## Format and trust design

Detached CMS signs the exact strict UTF-8 JSON bytes. One SHA256 signer is required. The signer certificate must be current, and its DER SHA256 must match an explicit out-of-band trust anchor supplied by the caller. Signature validation uses `CheckSignature(true)` deliberately: no online chain building, revocation lookup, certificate-store trust or installation. A certificate bundled with the input is not independently trusted. Offline revocation and pin distribution remain operator/security-review responsibilities. No development or test key is shipped.

```json
{"schema":"unified.windows-dry-run.v1","identity_sid":"S-1-5-...","artifacts":[{"path":"module.bin","bytes":29,"sha256":"64 lowercase hex characters"}]}
```

The manifest is at most 1 MiB; CMS at most 256 KiB; 1–32 artifacts, each 1–512 MiB, aggregate at most 1 GiB. Sizes must be JSON integers, never booleans/floats. Hash and size are verified from the same read-only file handle. Artifact paths use forward-separated relative components, with no traversal, device names, ADS, trailing dot, UNC or absolute path. All input path ancestors must be free of reparse points. The root, manifest, signature, artifact and in-root artifact ancestors must have trusted ownership and no untrusted writable allow ACE (conservative rejection regardless of deny ACEs). Trusted SIDs are the explicit current identity, SYSTEM and builtin Administrators. Tests change ACLs only inside their disposable temp directory.

## Limits and acceptance

This is a bounded offline inspection, not a security admission or an installer. It does not establish API/source SHA compatibility, runtime health, physical acceptance, revocation status, least privilege or production publisher governance. It always reports `namespace_trust=UNVERIFIED`: ACLs above the selected input/root boundary are not qualified, and an untrusted writer on a parent can replace protected descendants. It does not hold directory handles against concurrent namespace changes; untrusted-parent, trusted-owner/admin races and changes after inspection invalidate the observation. A future installer requires handle-relative path resolution, independently protected staging ancestry, independent trust policy and authorization, security review and separate physical evidence. Do not reuse this observation as authorization to execute files.

Tests create an ephemeral self-signed certificate, synthetic artifact, signed manifest and path/ACL/identity/signature/digest negatives in a disposable test directory, then remove it. No persistent keys, certificate-store changes, services, DB or external requests. Local and hosted checks are SYNTHETIC; HOSTED is recorded by exact run/attempt/job, never inferred from local success. PHYSICAL G0 and G1 Execute/Cleanup remain NOT_AUTHORIZED.

Run `powershell -NoProfile -File tests/windows/Test-WindowsDryRun.ps1` and `pwsh -NoProfile -File tests/windows/Test-WindowsDryRun.ps1`. Existing Python contracts use `python -m unittest discover -s tests -v`.
