# CODEX — Mandatory Math platform-coverage remediation and five-module integration

**Source pins (verify current GitHub HEADs before starting):**
- Unified combined Draft PR #10: 4cd3c30c5120337fa72c1b431cc772817a55383d
- Terminan Draft PR #57: dbbc1c6c3b3982280af6f20b70980e4caf151b4c
- Math Draft PR #103: 0b75c0a3583f9823d2b554806468fa541f20b35c
- Grid and Strattester source revisions must be selected only after checking latest release/receipt pins. Do not assume older synthetic SHA is production qualified.

## Priority P1: Math mandatory CI portability conflict
1. Open an isolated Draft PR based on exact Math #103 source HEAD; preserve #99/#103 unchanged. Audit tests/*.test.mjs and identify all 22 Windows-only test identities with exact source locations and required Windows APIs.
2. Preserve every test and assertion. Design an explicit platform-aware **mandatory** CI matrix: Node22/24 x PG16/18 portable tests on Linux, plus Windows-only tests on Windows with their actual dependencies. Ensure Windows-only tests are not silently skipped or falsely counted on Linux.
3. Independently verify union-of-test-identities and absence of duplicate, omitted, skipped, todo, deselected, retried or substituted tests. Fail closed on inventory mismatch. Retain strict environment and disposable database guards, immutable action SHA pins, artifact/evidence checks.
4. If an existing policy requires literal zero-skips for the *unfiltered* Linux inventory, document and resolve the contradiction through an independently reviewed ADR and explicit policy change before altering the strict runner. Never simply filter tests to turn CI green.
5. Run hosted exact-head mandatory matrix, download actual ZIP artifacts, compute SHA256 and report run/attempt/job/HEAD/tree. Do not claim success for a queued, cancelled or unqualified cell.

## Parallel integration (separate Draft PR based on Unified #10)
1. Audit actual APIs: FleetControl.status_snapshot, Lifecycle.snapshot, release_boundary, Terminan infrastructure consumer and Math bounded worker. Validate schemas, module identity, version negotiation, bounded responses, fail-closed errors, stale/unknown telemetry and cancellation.
2. Add disposable source-owned integration tests for all five modules. Test 0/1/5/6/7/10 nodes, module availability combinations, resource pressure, missing quorum, leader loss, DB loss, lease expiry, drain/retire, restarts, recovery, stale observer, incomplete history, exchange gaps, and missing Math.
3. Prove independent autonomy: Terminan read-only remains usable if Strattester/Grid/Math are absent; Grid collection is not equivalent to trade permission; Math computations cannot issue Grid orders; Strattester history completion requires independently verified receipts.
4. Test actual Chromium UI buttons: refresh, node selection, search/filter, timeframe, stale request cancellation, network topology, DB size labels, and progress timeline. Never fabricate links or sizes.
5. Only after independent CI PASS, design an installer staging plan for six owned Windows PCs with future add/remove, managed SSH/Tailscale identities, least privilege, PostgreSQL schema ownership, backup/restore and HA. PLAN_ONLY only.

## Rules
No merges, deployment, Windows/SSH/Tailscale/ACL/firewall/service/production PostgreSQL mutations, physical G1 Execute/Cleanup, real or simulated exchange orders without separately approved gate. Source authenticity and physical admission remain BLOCKED. Preserve original PRs, publish minimal patches, independent source review and P0/P1/P2 report.
