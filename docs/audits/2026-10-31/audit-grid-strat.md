# Grid and Strattester integration audit — 2026-10-31

## Scope and evidence

Read-only review of checked out Grid main `d537d525296ef34f727996e240ae6c60102c6082` and Strattester main `37ff7e9d12a4d2dccd788fc493c28557dbe8bcea`, their public entrypoints, historical pipeline and Windows deployment assets. Parent supplied test results: Grid 1082 passed / 12 skipped on local PG17; Strattester 518 passed / 1 skipped. Those results were not rerun in this audit and do not establish physical Windows or end-to-end historical readiness. No services were started and no live orders were attempted.

Remote inventories contain many relevant unmerged branches. The clones have only main objects; `cat-file` confirms key candidate history commits are absent. An explicitly escalated `git fetch origin '+refs/heads/*:refs/remotes/origin/*'` failed for both repositories with `could not read Username for https://github.com`. Consequently branch names/SHAs below are inventory facts, **not verified content, ancestry, mergeability or readiness**. Do not implement missing main behavior until these branches are inspected through authenticated fetch.

## What already exists and should be reused

* Grid already owns enrolled stable node identities, DB-less agent/control HTTP routing, fleet scheduling, leader/fencing components, collection/WAL/archive, PostgreSQL scientific state, historical-only import, scientific simulation and paper promotion gates. `grid/coordinator.py` exposes `/lifecycle`, `/lifecycle/phase/{target}`, `/scientific/history/import`, `/scientific/simulations`, ML claim/renew/data/artifact endpoints and a terminal read gateway. Do not build another six-module cluster scheduler or another enrollment mechanism in Strattester.
* Grid historical research implementation is substantial: `historical_signal_source.py`, `historical_levels.py`, `historical_experiment_runner.py`, `historical_variant_engine.py`, `barrier_simulator.py`, `historical_experiment_state.py`. It compares BASE/REGIME/MARKOV/REGIME_MARKOV/ML/ML_MARKOV over POC, BREAKOUT, FALSE_BREAK, VOLATILITY_CAPTURE; uses chronological folds, delayed Markov targets, fees/slippage, paired effects and bootstraps. Reuse kernels only behind corrected immutable dataset and claim contracts.
* Strattester already implements Bybit discovery/universe/history synchronization, coverage/readiness checks, node-local sharded SQLite stores, strategy requirement registration/execution, research metrics, scientific bootstrap exports and durable worker execution. `research/runner.py` synchronizes requirements before `engine/executor.py` executes a registered strategy through `StrategyContext`.
* Strattester `runtime/worker.py` has useful lease renewal, claim-token guarded transitions, worker generations, resource exhaustion holds, process/thread execution and cluster recovery. Reuse its executor semantics rather than replacing them with unguarded background work.
* Scientific handoff already exists: `research/scientific_bootstrap.py` exports schema-1 `HISTORICAL_BOOTSTRAP_ONLY` data; `runtime/grid_handoff.py` records file hashes; `runtime/bootstrap_completion.py` checks durable jobs before finalization; Grid `historical_science_import.py` checks the canonical JSON SHA and rejects claimed historical true L2/liquidations/absorption. Preserve the explicit separation between historical priors, live validation, simulation pass, paper and live authority.

## Confirmed gaps on inspected main

1. **Installed worker is liveness only.** `service/install_windows.ps1:31` installs `strattester.service_worker`; that module writes heartbeat and reads the phase file but never invokes the actual `WorkerRuntime`, `ResearchRunner` or completion coordinator. Repository search finds `build_worker` and completion coordinator only in definitions/tests; no production driver connects download -> durable strategy jobs -> results -> bootstrap -> Grid POST. The rich library plus green tests must not be described as an autonomous installed historical service.
2. **Grid run provenance is not actual input isolation.** `historical_experiment_state.create_run` requires a READY snapshot and stores dataset_id. But `historical_experiment_runner.run_symbol` uses dataset_id only for result writes. Signals query mutable global `poc_lifecycle`, `level_events`, `market_features_1m`; forward candles query global `candles_1m` by symbol/time. No dataset id is passed to these loaders. A repeated run can change after ingestion/retention despite identical stored dataset_id. Fix the reader contract to resolve an immutable export/snapshot with explicit cutoff, membership and hashes; label-only provenance is insufficient.
3. **Historical experiment worker is not wired into the application.** Search finds `run_experiment_worker` only at its definition. Existing state claims use SKIP LOCKED, but completion is keyed only by run_id/symbol, with no owner/token check or renewal. `recover_stale` can requeue after 30 minutes while the old worker still writes. Do not expose this directly to six nodes; reuse established fenced claim semantics and publish results through owner-token guarded completion.
4. **Some default signal variants cannot reach simulator with valid direction.** `barrier_simulator._direction` correctly requires explicit direction. POC loader and volatility loader do not select a direction; `_simulate` does not add one. Default POC/VOLATILITY_CAPTURE runs with actual selected rows can therefore raise instead of producing outcomes. Add causally known direction or explicitly mark these setups unavailable; never infer from future bars.
5. **Import is a prior import, not proof of completed research.** `/scientific/history/import` advances MARKET_HISTORY_SYNC -> HISTORICAL_STRATEGY_RESEARCH -> HISTORICAL_SCIENCE_BOOTSTRAP -> GRID_IMPORT using only the bundle. It does not consume/verify grid-handoff.json, result-store hash, required OOS outcomes or phase proof. Export capabilities are a constant support mask, not per-symbol/time observed coverage; a sparse/INSUFFICIENT symbol can accompany a bundle claiming support. Model observed coverage separately and require a run/dataset/results manifest for operational completion. Keep priors import permissible without falsely certifying research completion.
6. **Import transaction/representation cleanup needs branch review.** `import_historical_science` performs bundle and per-symbol writes separately without enclosing transaction. It constructs a capped scalp_events list but serializes the original `item.features`, so the local cap has no effect. The 20261030 handoff audit branch may already address this; inspect before coding.

## Ownership decision for six modules / five–six Windows nodes

Use Grid as the sole fleet authority: node identity/enrollment, heartbeats, availability, job ownership, retry, resource allocation, lifecycle intent, release rollout and recovery. Use Strattester as historical execution domain: history capabilities/coverage, registered strategies, causal backtest orchestration and result/manifest production. Math should be an explicit versioned numerical backend invoked by the research executor, not another scheduler. Other modules should consume versioned read contracts/artifacts instead of opening another module's live state file.

The current competing control surfaces are material: Strattester has independent PG/SQLite job/node membership, Brain/quorum research concepts, controller/guardian/Telegram lifecycle, Windows service installation and staged update logic; Grid already has corresponding fleet/control/Telegram/release ownership. Choose one owner per concern and adapt Strattester worker to Grid claims. Preserve Strattester research-specific state as domain state, not a second fleet registry. This is integration work, not a request to delete working recovery code.

SQLite remains node-local. Ship immutable checksummed exports or offer authenticated paged data access. Never share writable market SQLite across Windows hosts; use SQLite backup-consistent snapshots when WAL is active. A five–six-node fleet should use role/capability assignment and stable generated identities, not hard-coded PC names or addresses.

## Windows assets and physical readiness

Grid already supplies bootstrap/enrollment, Tailscale unattended setup, firewall/network preflight, PostgreSQL provisioning, worker packaging, immutable release staging/switch/recovery, release inventory and acceptance checks in `installer/`. `docs/PRODUCTION_LIFECYCLE.md` correctly says single CONTROL is not HA and standby promotion requires DB replication plus old-primary fencing. `WINDOWS_NETWORK_ONBOARDING.md` calls for tag-based node->control TCP 8765, with no agent-to-agent grant by default and no disabled ESET.

Strattester already has `install.ps1`, NSSM worker/controller/guardian, update/uninstall, `ops/bootstrap-node.ps1`, cluster commissioning/audit and recovery documentation. STOP persists durable intent, changes startup to manual and coordinates with Guardian through an OS-released SQLite lock. These are useful lifecycle invariants. However Strattester's commissioning SSH/22 + direct PostgreSQL model differs from Grid's DB-less node->control model; adopt one documented network/service topology. `install.ps1` requires Python, installs services only if NSSM is provided, and its smoke checks do not establish full production historical execution.

Before calling five–six physical Windows nodes ready, run existing commissioning stages in a dedicated root/DB: connectivity/reboot, identity/claims, storage/WAL, checksummed transfer, mini history, deterministic multi-node backtest parity, worker/network/DB interruption, lease loss/stale publication rejection, release canary failure/rollback and STOP persistence through guardian/host reboot. No VM/Linux pytest result substitutes for this evidence. Keep collection and simulation initially INFRA_ONLY / research-only. No live-order activation is required for this task.

## Exact branch recommendations, with verification boundary

**Safe integration base today:** new review branches from inspected Grid main `d537d525296ef34f727996e240ae6c60102c6082` and Strattester main `37ff7e9d12a4d2dccd788fc493c28557dbe8bcea`. Do not reset existing checkouts. Once authenticated history is available, inspect candidate diffs and ancestry and selectively integrate existing implementation. Inventory-only branch tips cannot yet be responsibly declared a better base.

Priority Grid candidates:

| Branch | Tip | Why inspect first |
|---|---|---|
| codex/history-snapshot-selection-20261030 | d2dcffb43e520db75936eb97389b66db2f3e1365 | Likely immutable dataset selection overlap |
| codex/history-math-export-20261030 | 28d4ae46c8ddbc0238b351e8d6b2bd29c6602ef2 | Likely Grid->Math history contract overlap |
| audit/grid-physical-maintenance-20261030 | 01c8fca14edc3d85e65ee74e8383320a1d46bf60 | Recent physical lifecycle overlap |
| integration/full-system-first-boot-20261024 | 0bcfab09a84aceb131a283785c17bfd095e1cb3a | Existing assembled first-boot integration |
| coordination/physical-g1-recursion-hardening-20261024 | 684f4c23826072d0813a5fd17898b530a2dab828 | Physical gate implementation overlap |

Priority Strattester candidates:

| Branch | Tip | Why inspect first |
|---|---|---|
| codex/unified-history-consumer-20261030 | c951b3f711780affc8e6936f75fe3796d8ef99eb | Unified history consumption overlap |
| codex/grid-math-replay-20261030 | f08d0175162074819d1ef5b1c204d110fc197c91 | Math replay adapter overlap |
| audit/history-scientific-handoff-20261030 | 092e7d576e1c181d68304dbb40e5b46adb5a90d8 | Handoff/import correctness overlap |
| codex/handoff-syntax-repair-20261030 | 2669c433333b811b0eaedf88ea13b0e955b0836b | Known handoff repair overlap |
| codex/unified-display-handoff-fixes-20261030 | 8a9f31fa7d07f9201edadc2d2ff94a5e3e1c75a5 | Cross-module display/handoff overlap |
| integration/math-external-kernel-contract-20261029 | 62fe967cf7b2358cf8dd7035218db566e566a603 | Explicit external kernel boundary |
| engineering/data-first-scheduler-20261028 | bceb60fbee478b03a73fdf68f85291cab3521d8a | Scheduler/data ownership overlap |
| research/ls5-history-batches-f1 | 702d285b5a5af28f0b2e1f4c9a52aeb49582cbef | Latest physical history batch integration |
| parallel/windows-physical-independent | 77517cf106803bbd44524cdb0c56e9fcc51b509e | Existing physical Windows checks |

Do not merge all branches by name/date. Check `merge-base --is-ancestor`, inspect contract tests and run composed integration before selecting a feature branch as base; older “final/”, “cycle2/” and “parallel/alphafold-*” branches contain overlapping research/sandbox/training work and may be superseded. The remote refs alone do not establish open PR state or merged status.

## Concrete next integration work

1. Obtain authenticated read access, fetch all heads, make a branch/contract containment matrix for candidates above and the unified-system contract branch selected by the parent audit. Preserve existing work; select one implementation per contract.
2. Freeze a shared historical request/artifact contract: schema version, run/task id, claim token/attempt, dataset/snapshot id/hash, symbol/timeframe/range, event_time/known_at/cutoff, observed capability/coverage, strategy/config/backend versions, numeric semantics, outputs/hashes and failure reasons. Distinguish empty data, unsupported features and completed research.
3. Wire a production historical executor into the installed service and Grid claim adapter, including durable request creation, coverage-first sync, resource-aware execution, checkpoint/renew, fenced result commit and completion callback. Connect existing BootstrapCompletionCoordinator only after verified required jobs/results complete.
4. Bind every signal and forward-bar read to the immutable dataset; correct direction availability; add focused integration verification for unchanged results after live ingestion and retention, plus stale owner rejection.
5. Make handoff atomic and reproducible; verify the actual artifact hashes and observed coverage end-to-end; keep historical priors separate from live and make lifecycle advancement depend on recorded prerequisite evidence.
6. Compose existing Windows installer/release/recovery components under one fleet owner and run the isolated physical acceptance sequence. Record exact release hashes, node roles, tests, failure injections and rollback evidence for each of five–six nodes.
