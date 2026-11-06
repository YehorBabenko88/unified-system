# Independent scheduler components

Component base: mission/operator-control-plane at 2df6f5c2f77f4d883bad1a8623dd8375db529be0.
This package is additive and has no production activation/import hook.

## Placement

Resources.cpu is allocatable benchmark work units/second in the exact benchmark_id
scale; mismatched benchmark versions reject. RAM/scratch are bytes, disk/network
are bytes/second. Scratch is worker-local workspace, not Storage replica capacity.
Reserved quantities are subtracted in every dimension. Nonnegative integer vectors,
pressure in parts-per-million and caller-supplied policy thresholds/weights are
validated; malformed input fails closed. A snapshot from a prior incarnation,
future/stale observation, unhealthy or non-worker node, memory pressure above the
policy ceiling and STANDBY/DRAINING/MAINTENANCE nodes cannot receive new candidates.

Among eligible nodes, minimize weighted sum(request/remaining) minus weighted data
locality fraction. Exact rational arithmetic avoids float ordering and overflow;
node_id breaks ties deterministically. This is a proposed ranking heuristic,
not a hardware benchmark calibration. Decision.rejections supplies stable reasons.
No eligible node returns candidate=None: caller queues rather than overcommits.

Candidate identity is per-node aggregated worker capacity for this component.
No authoritative active-task counter, cluster reservation ledger, lease or worker
dispatch is implemented. The separate local preparation registry/holds are described
in durable.md and cannot grant execution. Snapshot admission alone cannot prevent concurrent
overcommit; authority-ordered reservation CAS and current observation validation
must occur in a future admitted backend. Capacity freshness here uses an exact
caller-provided time and is not a qualified distributed clock protocol.

## Worker schedule

Europe/Berlin conversion uses zoneinfo and aware instants. Windows review/CI uses
tzdata2026.6; missing IANA data raises rather than substituting a fixed offset.
Windows are half-open, crossing midnight associates early hours with the start
weekday. Both repeated autumn hours match; spring skipped local hours never occur.
Equal start/end is rejected; use an explicit future all-day policy, not ambiguity.
worker_mode returns ACTIVE when in schedule, otherwise DRAINING while assignments
remain, then STANDBY. This is local policy intent; no authority revocation/drain ACK
is inferred. Coordinator duties are outside this worker-policy function.

## Closed authority boundary

Pinned draft3 contract SHA256:
5cc8e6a3557a9d71b6d1ccdf9939be49133deee9219b19029ffd4cf3d3bfa278.
All nine mutations return SAFETY_GATE_CLOSED, including Cancel/Complete/Adopt/
Release. No client flags can open gates. ReadReceipt returns UNKNOWN because no
backend is admitted; Rejoin requires reconciliation and grants no authority.
The class has no network/Storage/Consul client and implements no publication.
This is an enforceable local denial boundary only, not runtime API integration.

Draft3 design resolves actor/target separation and resource-reservation/capacity
provenance CAS. Scoped design ACK does not qualify strict expiry, closure/allocation
protection, RBAC, real endpoints or load limits. All remain unqualified and gated.

## Verification

```powershell
python -m pip install tzdata==2026.6
python -m unittest discover -s tests -p test_agent5_scheduler_components.py -v
```

Windows CI runs only these isolated component tests. It does not claim fleet
acceptance, fault-injection on office PCs, production benchmarks or backend fencing.
Full repository results and any inherited failures are reported separately.

CI explicitly checks out the pull request head SHA (push SHA for push events).
The original suite had15 cases; inventory v2 adds15 durable cases and requires
the exact30 declared IDs with zero skips, failures or errors (no loose minimum).
The uploaded receipt includes run/attempt, workflow/event identity, expected SHA,
before/after source HEAD/tree and tracked status, and the test-log SHA256.
Source success additionally requires every protected source/test/inventory/workflow
regular file's raw bytes to equal its committed Git blob before and after tests,
independently of index flags. Per-file blob OID, expected/actual SHA256 and sizes
are recorded; LF checkout is configured before checkout, never normalized in the guard.
The upload action's artifact SHA256/ID/URL are published separately in the job
summary; a receipt cannot contain the digest of an archive containing itself.
Local execution of the same runner is labeled LOCAL and is not GitHub CI evidence.
