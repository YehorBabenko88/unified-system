# Five-source disposable integration design

Source base: Unified `2fdd512bd06d3cb90b6c722e5f839f8ed159931f`.
Intent: exercise actual source APIs and disposable processes without confusing
source regression results with release admission or physical qualification.

## Source audit and approach

Latest open Grid #252 is `d2dcffb43e520db75936eb97389b66db2f3e1365`;
Strattester #69 is `702d285b5a5af28f0b2e1f4c9a52aeb49582cbef`.
Grid latest-release endpoint returns 404; Strattester release list is empty.
Neither is admitted. Existing five-boundary tests pin older #249/#43 and
manufacture synthetic admission bytes. Preserve those historical regression
tests, but label their scope separately from this exact-source suite.
Terminan #57 and Math #103 pins remain the requested source interfaces.

An all-pass simulation would not test consumer compatibility. A remote physical
test violates the task boundary. Choose actual local APIs with disposable SQLite
and Math worker threads, plus Chromium against snapshots produced by those APIs.
Fixture observations and caller votes remain synthetic and are never consensus.

## Interfaces

FleetControl.status_snapshot(now_ms) returns PLAN_ONLY nodes with unknown metrics
and database sizes null. Lifecycle.snapshot attaches a bounded fleet provider.
ReadOnlyLifecycleApp validates the core but currently trusts the nested fleet.
Terminan infrastructure.validate consumes lifecycle v1.0 and discards unqualified
links. Math runBoundedExperiment is a bounded, cancellable worker; its request
must reject execution_authority true. HistoricalBoundary and MarketBoundary
separately require owner receipt/release admission; source pins do not grant it.

## Deliverables and constraints

Add source pin manifest, independently runnable five-source tests and exact-head
CI evidence. Audit fail-closed nested fleet handling and fix only demonstrated
bugs with negative regressions. Test fleet sizes 0/1/5/6/7/10, resource pressure,
lease fencing/recovery, availability combinations, and actual Terminan consumer.
Run source-owned Math tests in a subprocess; add Chromium from real generated
snapshots without fabricating links, metrics or database sizes.

Every report says SOURCE_PROVENANCE BLOCKED, PHYSICAL NOT_RUN, PRODUCTION NO_GO.
No orders, host discovery, service mutation, remote inventory, deployment or merge.
Unimplemented acceptance cases must remain explicit blockers, never inferred PASS.
