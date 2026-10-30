# Disposable source acceptance ledger

No physical admission. SOURCE_PROVENANCE BLOCKED; PHYSICAL NOT_RUN;
PRODUCTION NO_GO. Caller-supplied voter lists exercise the durable source model,
not real quorum consensus, network partition or multiple physical machines.

| Requirement | Executed source proof | Remaining boundary |
|---|---|---|
| 0/1/5/6/7/10 nodes | Real FleetControl -> Lifecycle -> Terminan.validate -> actual HTTP -> Chromium | Physical nodes not run |
| Add/disconnect/remove/drain/retire/restart/recovery | New integration expiry/drain/reassign and existing fleet/lifecycle regressions | Removal is retained identity tombstone, not host deletion |
| CPU/RAM/disk pressure | Each resource independently rejects unsafe placement | No physical load generation or live rebalance |
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
