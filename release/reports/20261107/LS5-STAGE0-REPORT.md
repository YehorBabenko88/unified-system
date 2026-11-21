# LS5 Stage0 practical report

UTC observation: 2026-11-07T09:11:02.6152052Z. LS5, Microsoft Windows 11 Pro, build26300; current token unelevated. Free RAM 36.11GiB; disk 1492.49GiB.

**Stage0 observations completed; installation BLOCKED.** Five pinned LAN SSH connections succeeded. DNS and HTTPS200 observed on all six nodes. Network, firewall and ExecutionPolicy observations match before/after preparation. No ADMINIT contact, provider requests, security/network/OS policy or existing service/database modifications.

Prepared new directory: `C:\Users\LS-5\Documents\Codex\UnifiedPilot\LS5-20261107-4b4d98ef222b4f80af346e3c1975840a`. Only a preparation marker exists; code/state/backup targets absent. Actual PS5.1 installer ACL check rejects it with `Untrusted writable ACL`. The inherited additional write SIDs were not silently removed and no code/keys were installed. Path/reparse checks succeeded, but that is not hostile namespace or service admission.

Backup access: sshd and TeamViewer services are running. End-to-end authenticated administrative recovery was not demonstrated; do not count running services as backup access PASS.

Runtime observations: Python3.15.2 default, development Python3.12.10, Node24.22.1, Git2.55.0.windows.5, OpenSSH9.5p2. These are version/hash observations, not installed-release provenance or qualification. Existing ports/processes/services are retained; without a final port plan no conflict-free install claim is possible.

Installer PLAN_ONLY entrypoint was exercised with the actual provisional integration manifest and no fabricated package lock/bytes/publisher pin. It refused the input at schema validation: BLOCKED_NO_INSTALLABLE_PACKAGE_LOCK; no executable install plan or mutations. Nine separate pure security-planner regressions passed,0skips; they are model tests only. The legacy planner is not LAB unsigned-package or native host admission.

Original PS5 diagnostic module-autoload failure is retained. A read-only reproduction shows duplicate ACL type-data import under inherited module paths. Restricting only the child helper module path to normal Windows PowerShell modules lets the actual ACL check run; the real ACL still denies admission. No system setting or actual installer security check was weakened.

Backup/rollback planning covers only future owned targets after package admission. Existing production databases and foreign services remain outside the pilot. Before installation: exact artifacts/dependencies/source and installer security qualification, reviewed staging ACL/native identities/keys, alternate admin channel, affected-state backup plus actual isolated restore and version-compatible rollback rehearsal. No pilot rollback PASS claimed.

Next executable work: real GET reconciliation in isolated actual HTTP/Grid/Consul; native identity/app-mTLS contract and implementation; actual authority/assignment/storage producers; admitted immutable pilot artifact closure and safe staging helper. Continue the original Math run without retry.

Evidence: release/evidence/ls5-stage0-current-20261107; full fields and hashes in ls5-stage0.json. MASTER MISSION: IN_PROGRESS / NO-GO.
