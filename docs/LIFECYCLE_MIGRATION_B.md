# Durable five-module lifecycle (B)

Frozen PR4 base: b8facc028e00493d8423d15280f87c2047c2b63b. This independent branch preserves the existing Supervisor/Coordinator and source branches.

`Lifecycle(path, available_modules, verifier=None, fleet_provider=None)` is opt-in, PLAN_ONLY and local. `initialize()` opens its own explicitly supplied state DB. `apply(operation_id, expected_epoch, expected_sequence, stage, status, evidence, completed=0, total=0)` verifies observations through an injected source-owned oracle, binds the oracle result to the exact stage/status/counters, and atomically commits its event, snapshot and idempotency receipt. Default oracle denies all progress. No method launches processes, connects to exchanges, provisions nodes, or issues trading commands.

Order: INFRA_PREFLIGHT -> INFRA_READY -> STRAT_HISTORY_SYNC -> STRAT_RESULT_SEALED -> HANDOFF_VERIFY -> GRID_MARKET_READY -> STEADY_STATE. Terminan must be observed RUNNING/COMPLETE after INFRA_READY before research can progress. Math is independent. Paper and real trading remain NOT_AUTHORIZED. Module availability is explicit for all inventories from zero to five modules; missing prerequisites deny progress. A blocked/cancelled/retried upstream stage invalidates dependent stages. Observer loss invalidates research/Grid progress.

On restart, progress is visible as last recorded observation but new writes require explicit `recover(epoch, sequence)`. Recovery creates a new epoch, clears all stage observations and requires new source verification; it never replays old launch commands. Old operation IDs cannot replay after epoch change. Concurrent callers use BEGIN IMMEDIATE and expected sequence fencing. Event and cached response corruption reject reads/replays. DB write failure rolls back the entire transition.

`ReadOnlyLifecycleApp(provider)` exports GET `/internal/v1/lifecycle` only. No listener is started. Its versioned JSON is consumed by Terminan's new infrastructure dashboard; a caller can serialize a snapshot into an operator-selected local file. Inject A's `FleetControl.status_snapshot(now_ms)` through fleet_provider after compatible stack validation. Missing fleet is an empty UNAVAILABLE roster; no six invented machines or network edges. Source observations, heartbeat freshness and independent release/receipt admission remain the oracle/adapter's responsibility. Stored RUNNING is last observation, not proof of continued liveness.

| Previous owner | Unified responsibility | Compatibility and cutover |
|---|---|---|
| Existing Unified Coordinator | durable five-module stage journal and observer barrier | additive only; legacy synthetic acceptance unchanged |
| Grid/Strattester execution and retry internals | source-owned status/receipts consumed through verifier | no deletion; release-pinned C adapter and disposable E2E required |
| Grid node/process service code | none executed by B | A/E control models and separately approved physical executor needed |
| Terminan | read-only monitoring | D infrastructure route retains unavailable source labels |
| Math | independent numerical compute | no trading/paper authority |

P0: no physical executor added. P1 external: authenticated infrastructure approval/producer receipts, fresh observer proof, module launch adapters and real Grid completeness evidence absent. P2: bounded 4096-event local journal; no distributed consensus claim or automatic schema migration. SOFTWARE: synthetic tests only; SOURCE_PROVENANCE UNVERIFIED; PHYSICAL NOT_RUN; PRODUCTION NO_GO. Exact-head hosted success is a separate delivery gate.
