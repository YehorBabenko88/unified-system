# Independent Codex workstreams — source-owned, read-only

Baseline integration PR #1; freeze exact HEAD before any cherry-pick. Do not write to another contributor's branch. Every change requires tests and exact-head CI; no merge without explicit review.

## Codex A — Strattester read-only results
Repository: YehorBabenko88/strattester. Create independent Draft PR. Inspect actual current code and source-owned result store, add versioned GET /internal/v1/capabilities, /health, /runs, /runs/{id}/metrics only if compatible with existing architecture. No invented trades, no live execution. Bounded pagination, immutable run/dataset identity, no credentials in logs, strict UTC milliseconds, historical-only provenance. Unit/contract tests with fake SQLite fixture. Do not touch native G1 or AlphaFold PR #21 branch.

## Codex B — Grid read-only gateway
Repository: YehorBabenko88/bybit-cluster-grid. Independent Draft PR, no edits to #244/#247 branches. Inspect actual PG18 schema and existing read-only interfaces. Add capabilities/health and bounded candles/footprint adapter only where source provenance can be established. Never relabel aggregated footprint as live L2; no exchange subscriptions, writes, service/ACL changes, G1 or orders. Fail closed on unknown market type/epoch/freshness. Synthetic/PG disposable tests only.

## Codex C — Terminan consumer
Repository: YehorBabenko88/Terminan. Independent Draft PR based on compatible pinned integration stack; inspect PR #9 and #20 ancestry. Consume versioned read-only source contracts and supervisor status; render UNAVAILABLE/STALE/GAP and historical/synthetic labels. No direct exchange connectivity, no order API, no write credentials. Browser/DOM and Windows loopback regression tests.

## Codex D — Windows installer dry-run
Repository: YehorBabenko88/unified-system. Independent Draft PR from main or a documented frozen base, never push to integration/offline-contract-prototype. Build non-mutating signed-manifest verification design and a Windows PowerShell 5.1/7 dry-run with path/reparse/ACL/identity negatives, no service, DB, network or filesystem mutations beyond explicitly disposable test temp. No actual installer/deployment until authorized and security reviewed.

## Integration acceptance
Pinned source SHA, immutable release digest, API major/minor/capabilities, identity and provenance, UTC ms, bounded query/timeout, read-only, deterministic mock and disposable-source tests, offline absence matrix, exact-head CI run/attempt/job. Report SYNTHETIC, HOSTED and PHYSICAL separately. Real physical G0 requires explicit authorization. G1 Execute/Cleanup and live trading NOT_AUTHORIZED.
