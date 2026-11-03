# Release blockers and physical acceptance plan

> For agentic workers: use superpowers:executing-plans inline, then independent code review.

**Goal:** fix verified CI failures and prepare a secure, machine-checkable physical acceptance, retaining NO-GO until evidence satisfies every gate.
**Architecture:** preserve six Draft PR branches, Grid ownership and existing source fences. Diagnose downloaded artifacts before changing code; no runner impersonation on office PCs.
**Tech stack:** Python 3.12, Node/Playwright, PowerShell 5.1/7, GitHub Actions, PostgreSQL, Tailscale/SSH.
**Spec:** owner's 2026-11-03 release blockers and acceptance request in current chat.

## Constraints
Paper/simulation only; no merge/production deployment, security-policy weakening, office-initiated ADMINIT connections, foreign data/service deletion, private material publication or invented trust.
Signing remains BLOCKED_NO_TRUSTED_PUBLISHER. Work in existing source branches: linked-worktree metadata conflicts with the exact-source policy.

## Subsequent owner rulings and execution ledger

- LAB_SIMULATION is now the primary, explicitly authorized unsigned lab mode.
  TRUSTED_RELEASE alone retains BLOCKED_NO_TRUSTED_PUBLISHER; signing is not a
  blocker for admitted lab bytes. Design: ../specs/2026-11-03-lab-simulation.md.
- ADMINIT is removed entirely from processing, deployment and acceptance. The
  six-office-node route is LS5 -> PC1, PC2, PC3, PC4, LS7. No ADMINIT probes.
- Existing-source snapshot: six exact clean branch HEADs matched six Draft PRs.
- Terminan fixture strict-schema mismatch fixed in cbf7ce6; actual PR visual
  run41675129776 Windows and Ubuntu both pass. Full other workflows retained.
- Math full run41237484324 attempt3 passed all seven jobs after failed-only
  attempt2 correctly rejected mixed-attempt receipts. Original intermittent
  failure root unknown; add fixed diagnostic phases without deadline/guard changes.
- Meta exact-JUnit, PG mandatory-identity and platform receipt had three drifting
  skip policies for the one new Windows-impossible TAB filename test. Unified
  exact-identity policy in4963ccd; full run41678424661 passed. 72 focused tests
  include refusal of unknown/native/required skips and wrong platform/source/run.
- Current network refresh: all five remote strict-key SSH succeed; ESET and
  Firewall remain enabled, original ExecutionPolicy retained. LS5 still local
  UAC-filtered; no elevated service installation attempted.
- Lab feature: new canonical complete-file/directory manifest, external SHA256
  admission, new-only staging, fixed component launch profiles, source fences,
  private/minimal environment, isolated state and explicit physical lab entrypoint.
  Existing hosted-only entrypoint remains guarded. Raw source-pinned bootstrap
  dispatches lab only on explicit operation; no certificate access.
- Review findings fixed: external code/environment roots, mutable production
  paths, parsed/read hash mismatch, active dotenv, exited-child stdin cleanup,
  explicit office allowlist. Actual native child and six Git source-fence tests
  added. Full318 local tests passed before final small dotenv/timestamp tests;
  focused native signing tests PS5/PS7 pass. Complete physical capsule NOT_RUN.
- Trusted-release Authenticode verifier now requires native valid timestamp plus
  explicit TSA EKU/system chain/online revocation. Positive trusted signing NOT_RUN.
- Official www/non-www NSSM vendor endpoint still HTTP503; pin/checks unchanged.

## Review focus
- Exact JUnit identities and allowed skips must reject missing, extra, failed or unapproved skipped cases.
- Visual CI must test populated real UI and preserve error/stale paths, screenshots and browser zoom validation.
- Hosted fixture cannot become a local-host allowlist bypass or leak raw private diagnostics.
- Signing must fail closed without admitted publisher, timestamp and protected runtime/installer.
- Network checks must not initiate connections from office to ADMINIT or broaden peer access.

## Tasks
- [ ] Snapshot six HEADs, Draft status, complete workflow/job matrices and artifact hashes; retain baseline failures.
- [ ] Meta: compare actual JUnit identities/statuses to source manifest, add failing regression, fix cause, run focused tests and complete CI.
- [ ] Terminan: trace browser error to fixture/API/UI, add regression, preserve visual assertions, run both OS visual matrices and full required CI.
- [ ] Math: identify failing hosted case from retained receipt/source identities; add minimal regression and fix, repeat hosted matrix without spoofing environment.
- [ ] Diagnose any further required CI failures (including Grid vendor availability and Strattester financial acceptance); preserve external blockers rather than skip gates.
- [ ] Review signing verifier/installer trust boundary, add missing independent timestamp checks with tests; retain external signing blocker.
- [ ] Refresh six office nodes and ADMINIT status without office-to-ADMINIT probes; document owner-approved elevated LS5 deployment path, no UAC bypass.
- [ ] Produce machine-readable acceptance gates for ten instruments, history integrity, research/OOS costs, fenced paper execution, UI, backup/restore/failover/restart/update/rollback.
- [ ] Publish fixes/evidence in existing Draft PRs, obtain review, collect final exact-head CI evidence and report P0/P1 plus GO/NO-GO.
