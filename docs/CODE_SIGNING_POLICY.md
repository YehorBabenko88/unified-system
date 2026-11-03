# Code Signing state and preparation boundary

Status on 2026-11-03: **BLOCKED_NO_TRUSTED_PUBLISHER**. The owner confirms no
current Unified Code Signing certificate, configured signing service, public
certificate SHA256 pin or provided private key. Another application's expired
certificate is not a candidate. No production key or trusted test certificate
is created by this workflow. Unsigned test builds are a separate scope and
never qualify release publisher trust or deployment admission.

Prefer a protected signing service/HSM with nonexportable keys outside source
repositories and workstations. Provision its public Code Signing certificate
and SHA256 pin independently; neither manifest contents nor a computed digest
can appoint its publisher. A local certificate-provider reference is retained
for explicitly provisioned providers, including external/HSM-backed providers;
no PFX/password import or private-key export is supported.

## Preparation before certificate access

`Build-UnifiedRelease.ps1` now requires an absolute pinned Python executable,
its SHA256, the preparation entrypoint SHA256, a source-pin file and its external
SHA256, the exact source root, and the security-module SHA256. The source-pin
JSON contains exactly `unified_system/__init__.py`, `module_catalog.py` and
`release_manifest.py` with their externally reviewed SHA256 values (all paths
have the `unified_system/` prefix). Use an isolated admitted interpreter before
connecting the signing provider.

The wrapper retains read handles denying writes/deletion to the Python binary,
preparer, source-pin file and security module through execution/signing. Python
runs with `-I -S -B`, checks fixed-drive ordinary paths, and compiles retained
verified project bytes into a closed module namespace. It never discovers
project code through site, .pth, bytecode or untracked package shadowing.
Six-module manifest and bounded artifact hashes must pass before the wrapper
accesses the certificate provider. It retains one bounded verified manifest
byte array, and CMS signs those same bytes rather than reopening a pathname.

`-PrepareOnly` performs no certificate-provider/private-key access and emits no
signature. A real release manifest still requires an independently provided
publisher pin; do not insert a placeholder to work around the blocked state.
Test fixtures containing dummy pins are unit-test inputs, not release artifacts.

## Verification

`Test-UnifiedCodeSigningPublisher` requires the external certificate SHA256,
explicit Code Signing EKU, current leaf validity, system chain trust and online
revocation checking with no permissive chain flags. The CMS builder applies it
before accessing the signing key. A detached CMS integrity/pin check alone does
not establish Windows Code Signing trust.

`Test-UnifiedAuthenticodeArtifact` holds the artifact against write/delete,
requires Windows Authenticode status `Valid`, applies the same publisher/chain
checks and reports the SHA256 of that retained artifact. Its public result
still grants no runtime or deployment authority. Normal release compatibility,
source provenance, enrollment, ACL, rollout and artifact-closure checks remain
mandatory. Do not disable TLS or signature checks when a provider is unavailable.

Unsigned artifacts are rejected in real native tests; malformed closure is
rejected before certificate access; retained-file replacement is tested under
PS5.1 and PS7. Positive production signing/chain/provider behavior remains
**NOT_RUN** until an admitted publisher is configured. The hosted-only security
test gates remain unchanged and are never impersonated on physical PCs.
