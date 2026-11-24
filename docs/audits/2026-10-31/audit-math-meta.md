# Read-only branch audit: Math and Meta Analyse

Audited fetched refs with git log/show/ls-tree/diff only; no checkout, source edits, execution, deployment, or live exchange access. Exact commits below are source recommendations, not certified release heads. Remote inventories: math-remote-refs.txt and meta_analyse-remote-refs.txt.

## Exact bases

- Math consolidation: `12e688b339552ef2022e1b941780e6e1faadd0b1`, origin/codex/unified-history-scientific-20261030. This deliberately combines Scientific #102 `1f97e56701c0fce01dc8dd05952111fa8df3f2d1` and additive historical #100 `3a9c542841e160f8b1924f155aaa2d1a676dfd04`. docs/integration/history-scientific-v1.md explains composition. Do not choose grid-history-kernels alone: comparison lacks ~2,000 lines including joint worker, scientific engine, units, composition, APIs/tests. That branch and consolidation have shared merge-base b92cd96ab5a8cab048524b311f565f4fe1937b1f, so compare semantic changes rather than assuming identical ancestry.
- Math latest native diagnostic head `df10b815e406da0c59cb49bc6ef20b07f73e23b3`, origin/codex/math-native-console-fix-20261030, contains consolidation and adds 13 workflow/native harness/console/process-cleanup commits. Some are explicitly experiments, including inheriting hosted lab rights and isolating console initialization. Preserve for review; numerical base need not import experiments without validation. platform-matrix branch 135b437 is another relevant coverage donor. Existing numerical functions should not be recreated.
- Meta full source consolidation: `21af0a5c0a60c4be570052d0745c52cb8d40421c`, origin/fix/s1-ack-receipt-20261030. Contains origin/integration/final-ci-g0-20261026 plus 14 commits: benchmark evidence, native-loader provenance, G0 access, token drift/ABI cleanup, S0 isolated/filter hardening, bounded S1 precheck and nonce acknowledgement. S1 is read-only precheck, not runtime admission. Keep production target identity separate from this control packet source.

## Math reusable implementations and contracts

src/math-engine-server.mjs exports startMathEngine and evaluateMathRequest. Loopback-only port8788; GET /healthz and /v2/catalog; POST /v1/evaluate, /v1/graph/execute, /v1/graph/ports, /v1/formula, /v2/graph/execute, /v2/units/describe. Strict host/origin checks, JSON/body/time limits. src/scientific-engine.mjs executeScientificGraph/scientificCapabilities implements central graph execution; src/scientific-operations.mjs, scientific-units.mjs, scientific-data.mjs and scientific-unit-api.mjs own operations/time/units. Revision2.1 supports sum, rolling mean, derivative/integral, fixed affine/Landau/logistic maps, overlay/comparison named ports, exact time alignment, separate USD/USDT/BTC dimensions, propagated availability and bounded work. See docs/scientific-engine-v21.md. Fixed maps are not trained forecasts.

python/history_timed_worker.py is the isolated stdio entry: `python -I -S python/history_timed_worker.py`. Schema math.history.request.v1.1, exact model grid-frozen-analog-v1, max2000 causal-prefix rows/2MiB. Preserves event-end, watermark, first availability, decision and training cutoff separately; verifies rows/units/provenance shape; result includes dataset IDs/request digest/prefix digest and one-minute target. python/history_contract.py owns validation; history_nonlinear.py/history_sizing.py/history_statistics.py/history_stochastic.py/history_timeseries.py preserve Grid kernel ports.

Joint entry: `python -I -S python/history_scientific_worker.py /absolute/path/to/node`, evaluate_joint(q,node). Request exact {schema,history,graph}, math.history.scientific.request.v1. Reserved history.value source is injected; additional sources rejected. Math graph evaluates every formula/model/comparison. Eight-second Node subprocess limit and bounded result; scripts/history/scientific-stdio.mjs bridge. docs/integration/history-scientific-v1.md and history-protocol-v1.1.md are authoritative integration boundaries. Input availability <= decision is required; delayed observations after next event horizon cannot count as future forecasts.

Ownership already defined: Grid captures/authenticates dataset and source receipts; Math computes; Strattester owns costs/capital/funding/OOS/training lifecycle; Terminan renders receipts. Math explicitly does not authenticate source receipts or confer training/execution/trading authority. Authenticated historical admission remains blocked absent independent receipts. Do not turn offline synthetic parity into trusted-source admission.

## Useful Math checks (on isolated chosen checkout)

Runtime CI: Python3.12, Node22/24; npm package has Playwright1.56.1 and pg8.16.3. Pure scientific contracts do not need npm installation; browser/PG suites do.

```
node scripts/scientific/run-contracts.mjs
python -m unittest discover -s tests -p 'test_history*.py'
```

Full receipt gate `.github/workflows/history-integration.yml`: set EXPECTED_SOURCE_SHA to checkout HEAD, GRID_REFERENCE to exact Grid bf9f108b6777085d6725675eac778d61ec55f42b checkout, then `python scripts/history_ci.py tests 'test_history*.py'` and `python scripts/history/parity.py`. Original-source parity deliberately needs pinned original Grid blobs and a real Git checkout; archive-only temp copies may not satisfy source checks. Workflow runs Ubuntu/Windows, Python3.12/Node24. Scientific workflow runs Ubuntu/Windows × Node22/24 with `node scripts/scientific/run-contracts.mjs`. Tests include test_history_kernels.py, test_history_timed.py, test_history_scientific.py, test_history_ci_guard.py and scientific-{composition,engine,http,history-clocks,boundary-regressions,runner}.test.mjs. Hosted success not checked in this audit.

## Meta reusable implementations

README is stale MVP description (claims nine tests and missing features despite extensive later implementation). Use source and integration reports over README for capability decisions.

src/meta_analyse contains public-market collection, REST/WS client, sequenced L2 book/reconnect/freshness, footprint/tape analytics, archive ingestion with bounded resumable downloads, locks/checksums/ETag/day-boundary validation, persistent checkpoints and cancellation-safe drain, PostgreSQL migrations/storage, level ownership/sync journals, and desktop integration. core.py owns deterministic Candle/Level/Trade/PaperEngine/PaperFill rules. This is paper-only, not exchange order routing.

Historical entry points: history.py collect_history(exchange,store,symbol,timeframe,...), validate_fixed_interval, yearly_from_daily; archive_ingestion.py acquire_archive and acquire_many; history_parallel.py bounded_map; flow_history_storage.py read_flow_history(store,symbol,start,end,...) and to_orderflow_records(snapshot). AnalysisCoordinator in analysis_coordinator.py composes FootprintEngine/TapeVelocity/MarketClock with gap-quality propagation. Desktop entry meta_analyse.desktop:main (`meta-analyse` installed command / `python -m meta_analyse.desktop`). These are acquisition/analytics/paper interfaces, not an existing direct implementation of Grid historical v1.1 or Strattester simulation protocol; explicit adapters still required if Meta data is admitted.

ORDERBOOK_AUTONOMOUS_RECOVERY.md documents reconnect on invalid delta/malformed snapshot/sequence regression, fresh-epoch snapshot requirement, inactivity watchdog and bounded backoff. Relevant tests: test_orderbook_autonomous_recovery.py, test_orderbook_recovery.py, archive fault/resume suites, test_flow_history_storage.py, test_analysis_coordinator.py, test_history_checkpoint.py, test_storage_ingestion_postgres.py, test_integration_contract_shutdown.py, test_desktop_lifecycle.py. This is feed/session recovery, not physical multi-node coordinator failover.

## Useful Meta checks (on isolated chosen checkout)

pyproject.toml supports Python>=3.11; installer/CI select3.12. Dependencies httpx, websockets, psycopg[binary], PySide6; archive aiohttp; tests pytest/pytest-asyncio/hypothesis. Pin constraints requirements.lock. pytest pythonpath=src and asyncio strict; offscreen Qt for CI.

```
python -m pip install -c requirements.lock -e '.[test,archive]'
QT_QPA_PLATFORM=offscreen PYTHONASYNCIODEBUG=1 python -m pytest -q tests/test_core.py tests/test_history_checkpoint.py tests/test_history_parallel.py tests/test_archive_http_server.py tests/test_archive_resumable_faults.py tests/test_orderbook_autonomous_recovery.py tests/test_flow_history_storage.py tests/test_analysis_coordinator.py
```

Full `python -m pytest -q` includes platform/DSN-dependent tests; skipped Windows/DB tests are not evidence. .github/workflows/ci.yml provides disposable PostgreSQL18 Windows provisioning via scripts/prepare-ci-postgres18.ps1 and scripts/test-windows.ps1; Linux service PostgreSQL18.1 with META_ANALYSE_TEST_ADMIN_DSN/META_ANALYSE_TEST_DSN; tests/conftest.py governs fixtures. Important: CI full Windows/Linux jobs are explicitly disabled by branch-name exclusion for fix/s1-ack-receipt-20261030 and control/s1-precheck; run full suites on new integration branch and inspect all relevant workflows, not only green control checks.

## Windows installer/deployment reuse and gaps

Math scripts/windows-bootstrap.ps1, windows-update.ps1 and windows-deployment.ps1 already implement checked candidate worktrees, exact-SHA trusted-workflow/current-attempt context gating, per-root exclusive lock, atomic active.txt activation, NSSM service restart, loopback health and rollback. docs/windows-local-deployment.md documents exact contexts including full PG16/18 × Node22/24, native PDF, browser, contract and PowerShell jobs. Gate refreshes immediately before activation. Requires reviewed tooling, Git, NSSM, Node22/24, independently prepared deps/disposable test DB and pinned Python PDF requirements. No unattended scheduling; tooling explicitly supervised. Health only proves HTTP reachability, not release identity/scientific readiness. Existing bootstrap/updater should be extended after review rather than recreated.

Meta install.ps1 is user-level Python3.12 venv + constrained editable installation/import check and quoted Unicode launcher, optional DSN only. No trusted release manifest, staged release directory, atomic switch, rollback, updater/autostart or service rollout. commissioning modules are diagnostic/admission tools: process identity, SCM/module/registry provenance, DPAPI private evidence, G0 preflight/PG attestation. They are not fleet deployment agents. S1_PRECHECK emits PASS_PRECHECK_ONLY with s1_complete=false and authorization NONE/G0 FAIL_CLOSED; does not start UI/Bybit/SCM/Postgres/G1. Source/physical proof must not be inferred from synthetic evidence.

Required 5–6 physical Windows node installation, enrollment/identity, trusted automatic release rollout, canary sequencing, signed provenance, release-aware health, interrupted-update recovery, durable ownership/fencing and actual host-loss failover are not demonstrated by either repository. Preserve existing lease/fencing/storage/feed-recovery primitives, integrate them through the owning Grid/orchestrator contracts, and separately execute physical multi-host acceptance. No real-order routing is needed or authorized. This audit ran no tests and makes no physical readiness claim.
