# Disposable source acceptance ledger

No physical admission. SOURCE_PROVENANCE BLOCKED; PHYSICAL NOT_RUN;
PRODUCTION NO_GO. Caller-supplied voter lists exercise the durable source model,
not real quorum consensus, network partition or multiple physical machines.

| Requirement | Executed source proof | Remaining boundary |
|---|---|---|
| 0/1/5/6/7/10 nodes | Real FleetControl -> Lifecycle -> Terminan.validate -> actual HTTP -> Chromium | Physical nodes not run |
| Add/disconnect/remove/drain/retire/restart/recovery | New integration expiry/drain/reassign and existing fleet/lifecycle regressions | Removal is retained identity tombstone, not host deletion |
| CPU/RAM/disk pressure | Each resource independently rejects unsafe placement; cumulative reservations distribute two medium jobs across two hosts; after lease expiry and reduced first-host capacity, first job reassigns to second host with old-token revocation/idempotence | SOURCE_MODEL backed by real SQLite, not physical load generation or live rebalance |
| Quorum/leader/DB loss | Real SQLite ledger, no-quorum denial, leader expiry, DB disappearance | No distributed network/production PG experiment |
| Fenced ownership | Old lease token rejected after expiry/reassignment, restart preserves valid token | Execution remains forbidden |
| Missing modules | All 32 inventories through actual lifecycle and consumer | Inventory is observation, no module launch |
| Missing Math/cancellation | Source-owned bounded worker tests: authority denial, capacity, deadline, abort | No Grid order capability passed to worker |
| History gap | Actual latest Strattester SQLite sync and gap failure | Fixture history is not exchange attestation |
| History receipt intake | Actual latest Grid export and handoff deny missing receipts | Positive five-source sealed handoff BLOCKED |
| Refresh/selection/search/filter/timeframe | Actual Chromium against actual Terminan HTTP reading real API-generated snapshots | Metrics/sizes remain null |
| Stale cancellation/error/recovery | Captured actual HTTP response delayed; newer source retained; missing file recovers | No external network used |
| Topology/DB/progress/resources | Actual source UI shows absent links, null sizes/resources, NOT_STARTED timeline | No fabricated links/sizes/progress |

## Confirmed defect and patch

Lifecycle.snapshot previously accepted any fleet dictionary with a bounded nodes
list; HTTP excluded fleet from validation. A provider could expose nested true
execution authority or invented telemetry despite PLAN_ONLY core. Negative tests
observed both original failures. The minimal patch shares strict fleet envelope
and node validation at both Unified read boundaries. This is a P1 display/integrity
defect; it is not evidence of an order-execution escalation.

## Current source interface gap

Strattester #43 ResearchRunner.run accepted `result_store` and `provenance` and
sealed `owned_runs` records. Latest #69 run signature instead accepts
`checkpoint`/`research_permission` and returns StrategyResult; it does not expose
that sealing path. Grid's accept_handoff and Unified HistoricalBoundary require
the v1.1 independently admitted owned-run receipt. A Unified adapter cannot
create authentic missing producer receipts. Positive chain completion remains a
P1 functionality blocker; denial is not successful handoff.

Grid #252 docs/integration/history-protocol-v1.1.md explicitly retains external
owner receipt provisioning. Latest Grid release lookup returned 404 and
Strattester releases were empty at audit. The new pins are source candidates,
not production qualified releases. Existing old synthetic five-boundary checks
remain separately scoped and are not promoted by this suite.

Local full suite includes one existing Windows symlink-unavailable skip; never
claim unfiltered local zero skips. New source and browser tests require zero skips.

## Exact source test mapping

Standalone command (all required roots verified before import):
`python integration/verify_sources.py --terminan .source/terminan --math .source/math --grid .source/grid --strattester .source/strattester --output five-source-evidence`.
Test identities in `integration/verify_sources.py`, class `FiveSourceTests`:

| Test name | Mechanism / qualification |
|---|---|
| test_node_sizes_actual_consumer_unknown_observations | REAL SQLite + APIs + direct consumer; fixture node observations |
| test_every_module_availability_combination_remains_read_only | REAL lifecycle/consumer, 32 inventories; no module launch |
| test_resource_pressure_rebalance_expiry_drain_and_restart | REAL transactional SQLite ledger; modeled caller votes/resources; no execution |
| test_each_resource_reservation_redistributes_and_expiry_rebalances | SOURCE_MODEL, REAL FleetControl/SQLite per CPU/RAM/disk: cumulative reservations force node-1, third job denies, expiry + changed heartbeat moves A to node-1 and fences old token/idempotence |
| test_quorum_leader_db_loss_and_stale_consumer | MODEL voter quorum/clock, REAL database unlink/backup/restore, old token denied |
| test_actual_research_sync_and_incomplete_history_denial | REAL SQLite/sync engine/research; offline history provider, no exchange |
| test_unattested_grid_export_and_handoff_denied | REAL latest Grid export and intake; missing receipt denies |
| test_latest_result_schema_cannot_substitute_for_sealed_receipt | REAL current ResultStore schema/write/read then intake denial, interface-gap artifact |
| test_consumer_version_negotiation_denies_bool_or_future | REAL current consumer rejects bool/future versions |
| test_actual_consumer_independently_rejects_forged_nested_observations | REAL independent Terminan candidate rejects nested forged fields |
| test_actual_grid_collection_is_not_exchange_completeness_or_order_permission | REAL footprint producer/minute encoder/oracle, partial/stale not trading authority |

Worker subprocess is exactly `node --test --test-reporter=tap .source/math/tests/bounded-experiment.test.mjs`:
actual isolated Node workers, cancellation/capacity/deadline and actual loopback
HTTP permission-denial tests. This is not Math's full mandatory matrix.

Browser command: `node integration/node_modules/@playwright/test/cli.js test --config integration/playwright.config.cjs`.
Four identities in `integration/actual-ui.spec.cjs`: all controls, delayed actual
response cancellation, missing snapshot file/recovery, actual socket disconnect/
recovery. The disconnect uses a disposable server transport wrapper that closes
the actual TCP socket; successful requests use the actual Terminan source Handler.
Control inventory fails if any new interactive tag/role is uncovered. No links,
node utilization, database sizes or completed progress are invented.

Terminan candidate consumer follow-up starts from #57, independently validates
nested schema, and projects a small safe display result. Source pins record the
candidate exact HEAD; source admission remains BLOCKED.

## Source consistency qualification

`integration/source_guard.py` verifies every HEAD tracked blob against actual
working files using immutable raw Git blob reads and recorded runtime SHA256,
before and after both API/worker and Chromium/server processes. It never invokes
clean filters: only explicitly declared non-NUL text CRLF/LF differences are accepted, and
tracked `-text` attributes require raw byte identity. Git replacement refs,
local filter/include config, external worktrees/object stores and repository
override environment variables are rejected; Git commands disable replacement
objects and inherit a sanitized configuration/environment.
It rejects tracked differences, staged changes, untracked executable source
shadows (including ignored Python files), symlinks/path escapes, wrong imported
package origins and source changes during execution. Source imports use a new
empty bytecode cache. All source module `__file__` paths and the invoked Math
test/runner origins must belong to their expected tracked trees.

Dirty local development runs write `qualification: UNQUALIFIED` without borrowing
the committed HEAD/tree identity, and exit nonzero before source API imports.
Earlier local pre-guard runs are candidate observations only, not exact-head
qualification. `tests/test_source_guard.py` uses disposable Git repositories to
prove dirty tracked source, ignored untracked shadow, post-run mutation and wrong
import origin rejection, plus a clean pre/post positive control. Hosted artifact
source consistency is still separate from owner release authenticity/admission.

Browser fenced command:
`python integration/verify_chromium.py --terminan .source/terminan --math .source/math --grid .source/grid --strattester .source/strattester --output five-source-evidence`.
It requires a qualified same-head API proof, rechecks all five trees before and
after the server/browser subprocesses, and requires exactly four Chromium passes,
zero skips, zero unexpected failures and zero flaky tests.
