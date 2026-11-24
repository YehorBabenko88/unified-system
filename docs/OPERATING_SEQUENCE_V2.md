# Five-module operating sequence v2 — infrastructure -> research -> market observation

**Design-only; no physical authorization.** The coordinator owns orchestration, not research, exchange connections or trading authority.

## Stages and durable gates
1. INFRA_PREFLIGHT: owner-approved six-node inventory, software dependencies, system services, Tailscale/SSH policy, storage/DB plan, capacity/failure domains. Existing packages are not overwritten. Progress visible in Terminan.
2. INFRA_READY: only after independent verification of installed infrastructure, authenticated node identity, connectivity, DB schema, backups, and quorum/fencing. The PlanOnly prototype must not claim this.
3. STRAT_PREPARE -> STRAT_HISTORY_SYNC -> STRAT_RESEARCH -> STRAT_RESULT_SEALED: start Strattester through an authenticated, idempotent module lifecycle API. Strattester owns historical exchange ingestion, coverage, backtests, training, scientific provenance, checkpoints and completion receipts. Progress reports use run_id, stage, epoch, sequence, UTC time, counters, errors and stale flag. A process exit 0 alone is not completion.
4. HANDOFF_VERIFY: independently verify immutable dataset fingerprint, coverage, exact source/release pins, receipt, market type/symbol/timeframe, historical window, schema and owner trust policy. Incomplete or incompatible -> BLOCKED, not Grid start.
5. GRID_MARKET_READY: start Grid read-only current-market data ingestion via its source-owned API only after independent capability, market-source, credential, subscription, integrity and risk gates. Grid owns market data lifecycle, live candles/footprint/book/tape and data quality. Distinguish historical aggregates from authenticated live L2. No simulated or live orders inferred from ingestion readiness.
6. TERMINAN_OBSERVING: Terminan may launch read-only earlier (after verified infrastructure) and continuously show installation, node status, Strattester progress, Grid market data health, math experiments, warnings and transitions. If a source is absent show UNAVAILABLE, never fabricated success.
7. PAPER_TRADING (separate optional gate): simulator consumes qualified market events and explicitly approved model/strategy; independently authorize paper mode, isolate paper orders/positions from real exchange, retain deterministic replay, accounting, fees, slippage, fills and limits. Never auto-enable because Grid is running.
8. MATH_EXPERIMENTS (independent optional workload): Math jobs can run before/after research as resource leases allow; bounded compute and provenance, no ability to issue Grid trade commands.
9. STEADY_STATE: 24/7 Grid market-data collection is the operational goal. Define continuity SLOs (freshness, completeness, backlog, recovery time, recovery point), heartbeats, spool limits, retention, backup/restore, alerting, failure-domain placement and independently tested failover. Exactly-once external exchange side effects cannot be assumed.

## Dependency DAG
Infrastructure -> Strattester historical preparation -> verified handoff -> Grid market observation.
Terminan read-only UI starts as soon as INFRA_READY and runs alongside all later stages. Math experiments are independent, gated by compute capacity and user approval. Paper trading is separately authorized, never a required prerequisite for Grid data collection.

## Autonomous operation
Strattester/Math can run local offline jobs when Unified is down; Terminan can show cached or independently available read-only status with freshness labels; Grid can preserve its existing independently safe collection behavior where previously authorized, but no new distributed leases, ownership transfers or trading operations without quorum/fencing. If a node is lost, reclaim work only after lease expiry and verified checkpoint; avoid duplicate side effects. No automatic restart loop across module failures.

## Terminan user-visible timeline
Show stages with source_id, status (NOT_STARTED, RUNNING, WAITING, BLOCKED, DEGRADED, COMPLETE), monotonic progress counters, total/unknown units, exact timestamps, run_id, provenance, errors and next gate. Percentage only when numerator and denominator are independently known. Controls: read-only refresh/filters, explicit owner-approved actions for install/start/pause/retry/drain with dry-run preview and separate authorization. No implicit trade authorization or admin privilege from UI.

## Release/acceptance
Synthetic software CI, disposable PostgreSQL/SQLite and HTTP integration, physical read-only G0, signed release trust, independently authorized installation, physical operational qualification, then separately approved paper mode. Existing Grid G1 Execute/Cleanup, production DB changes and live trading remain NOT_AUTHORIZED.
