# Mission 3 implementation plan

> Workers execute incremental tested changes and retain independent review.

Goal: complete as much six-module operational and deployment preparation as can
be technically verified without physical deployment.
Spec: ../specs/2026-10-31-mission3-runtime-design.md

- [x] Verify six exact checkpoint heads and retained recovery bundles.
- [x] Inspect actual GitHub CI and open PR metadata; keep failed runs visible.
- [ ] Node-local runtime: ModuleSpec, persistent stop/recovery, dependency graph,
  release-aware readiness, bounded process ownership; RED/GREEN real child tests.
- [ ] Read-only v2 API and Terminan consumer/dashboard, preserving strict v1.
- [ ] Grid Consul Raft adapter and five-voter loss/partition tests; PG epochs kept.
- [ ] PG primary/standbys, synchronous loss tests, hard-fenced promotion, WAL/PITR
  and actual restore verification; no real database mutations.
- [ ] Signed release v3, existing rollout extension, agent staging/rollback and
  Prepare-default Windows installer with ephemeral-CI-only execution.
- [ ] Hot registration/unload, strategy activation and migration boundaries;
  protected history/release/backup retention and interruption recovery.
- [ ] Fix confirmed CI defects from actual logs, execute pinned browser and
  required native matrices; persist ZIP hashes and exact run/attempt/job state.
- [ ] Independent reviews, final verification, Draft PRs and PARTIALLY_READY /
  BLOCKED report with unmet mandatory criteria explicit. Never physical READY.
