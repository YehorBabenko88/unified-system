# Tailnet physical deployment and acceptance implementation plan

> For agentic workers: execute inline with superpowers:executing-plans and an independent final code review.

Goal: continue Missions 1–4 on every reachable authorized computer and qualify a
working research/paper system without real orders or exchange credentials.

Architecture: retain Grid as fleet/task/fencing owner and Unified as local
supervisor/release-policy owner. Reuse Strattester, Math, MetaAnalyse and Terminan;
do not introduce a competing controller. This plan extends the existing
2026-10-31 six-module physical design and the owner's 2026-11-03 acceptance spec.

Tech stack: isolated Windows CPython 3.12, pinned Node, PostgreSQL, existing SSH
profiles, Tailscale and signed externally admitted release manifests.

## Constraints and rulings

- No real orders/credentials, disabled firewalls/TLS/signature checks, unknown SSH
  host-key acceptance, foreign-data deletion, or hosted-runner impersonation.
- Keep existing branches/PRs; preserve work. No remote merge or branch deletion.
- Inventory confirms six accessible Windows hosts: LS5, PC1–PC4 and LS7.
  ADMINIT is offline, its Tailscale key expired, and TCP22 is unreachable.
- Ruling: use existing source branches in place, preserving clean checkpoints;
  deploy only fresh isolated capsules. Linked worktrees are incompatible with
  the current exact-source metadata policy and are unnecessary for these fixes.
- Candidate roles: LS5 control/history/UI; PC4 heavy research; PC3 Math/backup DB;
  PC1/PC2 collectors and bounded paper workers; LS7 lightweight monitoring/worker.
  Actual role activation must be admitted and resource bounded, not assumed.
- Signing is externally blocked: no valid owner-admitted Unified signing
  certificate/publisher pin was found on any accessible host. Do not repurpose
  another application's expired certificate or create a production signing key.
- Owner subsequently confirms `BLOCKED_NO_TRUSTED_PUBLISHER`, no signing service
  or public pin; explicitly permits separate unsigned test builds. Authenticode
  and system-chain verification support is required, not fake production trust.
- LS5 is UAC-filtered locally and SSH login is denied. Its service-install path
  needs an existing authorized elevated session; do not bypass UAC.

## Review focus

1. No relative/UNC/reparse source path can silently become trusted; resolve CLI
   spelling lexically and keep SourceFence checks mandatory.
2. No unpinned/interpreter/site startup may run before release preparation or
   signing-key access; preparation must be independently reviewable.
3. No passing tests from a different revision may qualify a release; retain
   current CI failures and external vendor HTTP failures.
4. Source/worker leases and instrument ownership belong to existing Grid;
   disconnected workers cannot continue an unfenced write authority.
5. UI staleness, missing data/costs, unsigned artifacts and untested HA remain
   explicit blockers, never synthetic success.

## Execution ledger

- [x] Read current owner authorization and enumerate Tailscale peers.
- [x] Strict-key SSH hostname/user verification of PC1, PC2, PC3, PC4 and LS7;
      local LS5 inventory; probe ADMINIT without accepting unknown keys.
- [x] Collect OS, CPU/RAM/GPU, disks, dependencies, ports, services and sleep policy.
- [x] Inspect all six clean working branches/current HEADs and PR/CI state.
- [x] Check public signing-certificate metadata without reading private keys.
- [x] Fix Chromium CLI-relative source roots, missing immutable Terminan sibling
      checkouts, and Windows overload socket-reset test handling with regressions.
      Grid vendor NSSM HTTP503 and Math hosted fixture failures remain open.
- [x] Fix release preparation so pinned isolated Python runs before signer access;
      retain verified files/manifest bytes; add Authenticode/Code Signing chain
      checks. Positive trusted signing remains externally blocked/NOT_RUN.
- [x] Run lightweight, externally hash-checked unsigned source probes on all six
      accessible PCs using portable CPython; no Torch/Qt on the light nodes.
      Existing Grid weighted assignment distributes ten live-discovered symbols;
      each obtains 1000 closed real minute candles, Math ACF and 28 legacy runs.
      These are short source-smoke probes, not training/OOS/live/HA acceptance.
- [x] Retain a six-by-six TCP22 matrix and failed probes; successful LS5 SSH does
      not prove that all peers can connect directly to each other.
- [ ] Stage role-specific dependency/source candidates on fresh per-host paths,
      verifying transport/source/archive hashes and resource budgets.
- [ ] Admit signed services and agent/runtime bridge only after external publisher
      identity and required elevation are available. Test rollback/uninstall.
- [ ] Qualify ten publicly discovered USDT perpetuals, bounded historical coverage,
      real Math/training/OOS with fees/funding/slippage and immutable provenance.
- [ ] Run simultaneous ten-instrument live/paper capture with existing Grid
      scheduling, leases/fencing, bounded queues and preserved failure evidence.
- [ ] Verify cross-host backup/restore, replication/failover, RPO/RTO and recovery
      using isolated data, not existing PostgreSQL databases.
- [ ] Provide protected Terminan access, stale/error states, linked logs and a
      user scenario; record Codex checks separately from owner manual acceptance.
- [ ] Record exact sources/artifacts, node roles, connectivity, results and
      remaining P0/P1/P2 blockers. Never mark whole-system acceptance prematurely.
