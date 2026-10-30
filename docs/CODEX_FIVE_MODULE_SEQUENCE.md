# CODEX — Five-module infrastructure and lifecycle implementation order

Repository set: YehorBabenko88/unified-system, bybit-cluster-grid, strattester, Terminan, math.

## Mandatory operating scenario
First office PC starts Unified. Unified performs read-only inventory and prepares a signed/approved infrastructure plan for six initial PCs, scalable up/down. After separately authorized and verified provisioning, Terminan starts read-only and displays infrastructure progress and topology. Unified starts Strattester, which owns history download, dataset completeness, backtesting/training/research and immutable completion receipts. After successful independent handoff verification, Unified starts Grid for qualified current exchange market-data ingestion and sustained 24/7 operation. Terminan displays all stage progress, node loads, databases/sizes, Grid health, and historical/market data provenance. Math runs independent bounded experiments. Paper trading is optional, separately authorized, fully isolated from real orders.

## Parallel workstreams — independent Draft PR per stream
A: Unified Infrastructure. Inspect Grid/Strattester original infrastructure implementations; migrate owner-approved fleet registry, identity, node enrollment, resource telemetry, scheduler, lease fencing, quorum, failure-domain HA, Tailscale/SSH, dependency/DB/backup/release planning into Unified. First implement PLAN_ONLY and disposable CI. Do not delete upstream code until tested cutover. Verify existing Windows PS5.1/7 and PG18 requirements.
B: Unified Lifecycle. Durable idempotent orchestrator for INFRA -> STRAT_HISTORY_SYNC -> STRAT_RESULT_SEALED -> HANDOFF_VERIFY -> GRID_MARKET_READY -> STEADY_STATE; Terminan starts after INFRA_READY in parallel, Math independent. Explicit source-owned API contracts, epochs/sequences, retry/cancel, progress, completion and blocked states. No automatic paper/live execution. Verify recovery and partial module absence.
C: Strattester/Grid boundary. Inspect current exact PRs and owner receipts, historical coverage, source identity and Grid current-market data health. Implement read-only contract adapters with strict release pins and synthetic/disposable end-to-end tests. Grid data ingestion must not require live trading.
D: Terminan/Math. Build read-only infrastructure dashboard with verified topology, six-node cards, CPU/RAM/disk, DB sizes, alerts, stage timeline, progress counters, research and Grid health, Math experiment status. Test every visible control including refresh, search, filters, timeframes, node selection and stale request cancellation in real Chromium. Never fabricate network links or data. Math owns numerical compute API and cannot issue trading commands.
E: Windows installer/security. Audit installer/SSH/Tailscale/PG scripts from both legacy repos. Design signed offline package lock, dependency inventory, PlanOnly deltas, per-node operator-approved enrollment and rollback, least-privilege Windows service account and managed Tailscale device tags. Do not hide services, override admin controls, use reusable credentials, or change physical hosts.

## Delivery requirements
- Freeze exact HEAD/tree and source identity for each repo; report PR URLs and CI run/attempt/jobs.
- Test independent operation with 0, 1, 2, 3, 4 and 5 modules available, and fleet with 0, 1, 5, 6, 7+ nodes.
- Failover: stale heartbeat, lost leader/quorum, lost DB, split brain, resource pressure, duplicate jobs, expired leases, restart/recovery, disk full, backup restore and node drain.
- Real source provenance cannot be replaced with synthetic fixture attestation. Report SOFTWARE, SOURCE_PROVENANCE, PHYSICAL and PRODUCTION separately.
- Preserve original Draft PRs and source-owned semantics. No merges, installations, Tailscale/SSH enrollment, ACL/firewall/service/DB mutations, G1 Execute/Cleanup, live exchange orders or production deployment without separate authorization.

## Final output
Each stream must publish code/tests in its own Draft PR and a concise migration matrix with remaining P0/P1/P2 and exact blockers. Coordinator reviews integration contracts and accepts only exact-head CI SUCCESS.
