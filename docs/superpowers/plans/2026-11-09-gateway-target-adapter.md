# Target Adapter v1 — authorized isolated implementation

Base: Unified PR46 exact1b205595479cf2b4998bf98209615bba14a91581. Existing immutable evidence unchanged.

ROOT owns NEW unified_system/gateway_target_adapter.py, tests/gateway_target_adapter/**, docs/intelligence/target-adapter/**, coordination/target-adapter-ownership.v1.json, .github/workflows/gateway-target-adapter.yml. A7 owns research implementation; A2/A5 native admission; A4 publication; A6 separate disposable renderer; A8 independent audit. No edits to shared runtime.

1. Capture current remote PR/head/tree/source snapshots; inventory existing target capabilities, mark unverified implementations UNAVAILABLE.
2. Write executable tests first for preparation/closed contracts and actual existing A7->Meta invocation. The fixed three-row immutable synthetic BTC input and A7/Meta source hashes are pinned. No callback can replace the target.
3. Implement direct-only stand over existing Journal, with exclusive OS local writer lock. Persist original request intent BEFORE invocation. Finished output is bound to raw content SHA/length. Duplicate request/key returns the same prior result; collision refuses; interrupted intent stays UNKNOWN and is never re-executed. No new scheduler/registry/ledger.
4. Direct invocation uses an opaque stand-local context, explicit LOCAL_TEST_SCOPE_NOT_AUTHENTICATED, bounded expiry and cancellation. This is NOT production identity/authority. Public submit always DENY; assignment/fence/generation claims must be null in this direct profile.
5. Negative tests cover unsupported principal/scope/expiry/target/dataset/units/resources, non-null stale native claims, duplicate/collision, cancel race, partial result and crash before/after target through disposable process fault harness. No office fault injection.
6. Publish exact request/result schemas and source-bound actual output, get A4/A6 scoped ACK, run focused Windows tests and CI workflow. A8 reviews exact source independently. Do not transfer DIRECT_TARGET_PASS to scheduler/authenticated/physical gates.

Review focus: exclusive lock across processes; crash intent not retried; bounded preparse; source replacement/hash mismatch; cancellation before publication; output/journal integrity; no provider/network/production IO. Native resource containment is not claimed by cooperative in-process direct execution.
