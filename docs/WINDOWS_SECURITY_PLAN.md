# Windows installer/security E: source audit and PLAN_ONLY contract

Frozen Unified base: b8facc028e00493d8423d15280f87c2047c2b63b, tree 9ad0c3811711b8f243454b3d86302fa9093baa1a (PR4).
Existing independent PR2 is preserved: adaa1c850b7e10b9e79b178ab3511ccf66743de4.
Its scripts/WindowsDryRun.psm1 supplies the detached SignedCms/publisher-pin design copied into the new SecurityPackage.psm1; its branch and ACL-changing tests are never modified or run here.

Source audit snapshot, fetched 2026-10-30:

| Owner | Exact commit / tree | Inspected source | Finding and Unified plan |
|---|---|---|---|
| Grid | d537d525296ef34f727996e240ae6c60102c6082 / dc9e7e9bf20de3e1e4efc9c763062c45fb0572cf | installer/install.ps1, configure-tailscale.ps1, configure-postgres.ps1, harden-host.ps1, install-postgres.ps1 | Admin installer, winget/MSI, auth key, registry/UI task changes, service restart and SSH/firewall mutations. PG installer passes password in process arguments. Unified keeps these as separate owner-approved enrollment/rollback plans; no invocation. |
| Strattester | 37ff7e9d12a4d2dccd788fc493c28557dbe8bcea / 7f41758d353fe92a2e3d251cb7bd8901c364cc84 | install.ps1, ops/bootstrap-node.ps1, service/install_windows.ps1 | pip/network smoke; OpenSSH capability/service/firewall installation; administrators_authorized_keys ACL edits; NSSM LocalSystem service replacement. Unified plans dedicated non-admin accounts and per-node identity enrollment. No upstream deletion. |
| Unified PR2 | adaa1c850b7e10b9e79b178ab3511ccf66743de4 | scripts/WindowsDryRun.psm1, tests/windows/Test-WindowsDryRun.ps1 | Offline CMS pin check and artifact hash bounds already exist. Tests modify disposable ACLs; those tests are excluded here. New verifier also checks every namespace ancestor ACL, deliberately failing closed on ordinary permissive roots. |

Cutover is BLOCKED for every row. Static source audit establishes script behavior, not deployed state or independent authenticity of source ownership.

## New interfaces

`build_security_plan(lock, package_bytes, nodes)` in installer_security.py is a pure bounded model with at most 64 nodes, 32 artifacts, 512 MiB per artifact and 1 GiB total. It validates exact source commit/tree syntax, explicit PS5.1/7 + PostgreSQL18 requirements, immutable artifact SHA256/size/version/publisher-pin inventory and infrastructure dependency inventory closure (Python, PG18, OpenSSH, Tailscale, service wrapper). Windows relative paths exclude traversal, ADS, devices, trailing dots and case collisions. Input facts never grant admission. Missing/false/unknown identity, publisher, path, reparse, ACL or operator approval blocks the node. Deltas bind previous/desired package digest, with explicit rollback prerequisites.

The package contract is `unified.windows-package-lock.v1`: identity_sid, sources (grid/strattester/unified/terminan/math commit+tree), requirements {powershell:'5.1,7',postgresql_major:18}, artifacts [{dependency,path,version,publisher_sha256,sha256,bytes}]. This closure covers infrastructure package names only; it does not establish application release closure. Real Grid, Strattester, Unified, Terminan and Math release packages, transitive dependencies and independently authenticated release signing remain external blockers. Synthetic source pins in tests are not release inventories. Lock inventory does not provide the actual offline dependency artifacts or authenticated pins. Operator must obtain immutable packages and out-of-band approved signer/publisher/source pins. No package authenticity is inferred from hashes.

`Test-UnifiedSecurityPackage` in SecurityPackage.psm1 reads a bounded detached CMS signature, pins exactly one SHA256 signer certificate, checks certificate validity, process/signed identity, local path/reparse/ACL observations and package digests. It never installs or changes anything. Offline certificate pin verification intentionally performs no network chain/revocation lookup. Package publisher pins are inventory requirements, not independent Authenticode validation of every package. `Test-UnifiedPackageSignature` tests byte signatures only and grants no plan or host authority. Signed input is not a host attestation. Python planner and PowerShell verifier remain separate interfaces; no caller-provided verification Boolean promotes source trust.

PS5.1/7 compatibility is checked by hosted Windows CI running in-memory ephemeral signing keys and full Python tests. No ACL changes, service operations, DB, network configuration, Tailscale/SSH enrollment, external market operations or G1 occur. Existing Python loopback tests use disposable fixtures. No installer package is executed. The PG18 version requirement is a contract check; actual PG18 installation/runtime qualification is NOT_RUN.

## Enrollment and rollback design only

An operator separately approves each node identity, hardware/namespace evidence, exact lock digest and predecessor digest. Use single-use short-lived enrollment issued for that node, owner-managed Tailscale device tags with explicit tag-owner/ACL policy approval, dedicated non-admin service account with only required resource rights, no interactive logon, and no reusable secrets in plans/logs. Do not hide services or override administrator controls. No auth key, password or SSH private key is accepted by these APIs.

Rollback requires prior immutable release, owner-approved backup/restore validation, predecessor state, bounded drain and operator approval before any change. Missing prior version or database restore evidence blocks execution; planner does not promise reversibility of database migrations.

| Priority | Remaining blocker |
|---|---|
| P0 | Independent owner/source/publisher pins, authenticated package inventory, actual namespace/host attestation, per-node enrollment authorization and executor are unavailable. PHYSICAL NOT_RUN; PRODUCTION NO_GO. |
| P1 | Offline package Authenticode validation, revocation freshness, stable handle/hostile namespace TOCTOU qualification, effective ACL/token semantics, service-account rights and managed Tailscale policy require independent disposable Windows qualification. No security admission granted. |
| P2 | Real dependency closure/SBOM for bundled wheels and transitive native libraries, backup restore rehearsal, rollback/cutover operator UX remain planned. |

SOFTWARE: model/signature tests only. SOURCE_PROVENANCE: NOT_EVALUATED. PHYSICAL: NOT_RUN. PRODUCTION: NO_GO. Hosted JSON SHA evidence is integrity evidence for exact CI checkout only, not independent owner or physical attestation.
