# Local durable scheduler preparation journal

ROOT-approved independent slice on PR24. This is SQLite local preparation only,
not a consensus service, authority client, actual-capacity ledger or dispatcher.
No network, worker send, storage publication, factory hook or physical operation.
The existing authority boundary remains closed; event-v3 approval does not wire it.

## State and guarantees

An exact local scope binds cluster, generation, job, dataset, source and partition.
Opaque aliases are permitted internally; no alias is promoted to a verified UUID,
authenticated principal or authority key. Job demand/benchmark/data spec is immutable;
same enqueue is idempotent, changed spec under that scope conflicts.

QUEUED -> PREPARED creates one original request UUID and local_hold_id, selected
node/incarnation and provisional CPU/RAM/scratch/throughput accounting. This ID is
NOT a Storage reservation or Agent2 authority reservation/grant. No lease epoch,
fencing token or assignment revision is minted here. Local event sequence is only
this journal's event number.

New preparation requires caller-observed authority availability and active worker
schedule, then advisory health/role/mode/pressure/benchmark/fresh-capacity validation.
Those booleans/snapshots are input hints to local preparation, never trusted runtime
authorization. Defaults deny preparation. PREPARED retries return the original
intent, not current readiness or execution permission. Policy/authority must be
revalidated by a future admitted driver before any operation.

All views contain execution_authorized=false. record_handoff marks PREPARED as
SEALED BEFORE a future external boundary; it never performs that external action.
UNKNOWN can follow SEALED. A crash after sealing is conservatively uncertain even
if nothing was sent. SEALED/UNKNOWN holds remain charged across process restart,
incarnation/generation changes and elapsed time. They cannot be cancelled/refunded
or rekeyed here. There is intentionally no local committed-outcome/release API until
the exact admitted authority receipt/reconciliation contract exists.

Only QUEUED/PREPARED jobs can be locally CANCELLED. This releases only never-handed-
off local entitlement, not authority leases, Storage allocations or committed data.
Cancel racing handoff is serialized in the same database transaction.

BEGIN IMMEDIATE serializes this file's preparation/hold/event changes; synchronous
FULL requests SQLite durability. All write steps and the event commit together.
Two connections to this SAME file cannot both spend its provisional capacity.
It does not coordinate different files/nodes. Storage bytes and actual hardware
allocations remain external. Upstream reserved quantities plus all local uncertain
holds are counted conservatively; overlap may underutilize capacity and never
grants a credit. Observations still require later authoritative provenance/CAS.
An outstanding nonzero CPU hold in another benchmark scale blocks the node;
there is no implicit scale conversion or forgiveness after restart/UNKNOWN.
No TTL-based refunds, local reset of generation or cleanup of uncertain state.

## Typed dependencies before real dispatch

Agent2 must supply the exact event-v3 generation/session/leader index, immutable
assignment/lease/epoch/grant/worker registration and resource/capacity key/index tuple.
Agent4 owns storage reservation/budget/closure/allocation and publication receipt.
The future driver must durably seal the original complete canonical intent before
submitting, reconcile UNKNOWN by original request identity, and verify authorized
COMMITTED or authoritative REJECTED outcome before changing any external reservation.
Current request UUID is a local preparation identity, not a frozen common-wire
idempotency tuple. Binding/serialization must be jointly reviewed before submission.

Civil-time work windows and local drain intent remain independent; creating a
preparation never permits new work outside schedule or bypasses actual-capacity,
no-quorum, resource-side fencing or sender-containment requirements.

## Evidence

New tests exercise real file-backed SQLite restart, duplicate intent conflict,
two-connection admission, UNKNOWN retention/new incarnation, never-sent cancellation,
stale/pressured capacity, no-quorum/schedule denial, invalid raw observations,
SQL-trigger transaction abort and actual child-process exit before event commit.
These are local journal tests, not real Consul/fleet fault acceptance.

All original15 test method bodies/IDs are unchanged. Inventory v2 declares exact30
IDs (15 original +15 durable), zero skips; CI receipt is explicitly v2. Earlier
15-test source/receipts remain historical and do not qualify this new source.
Actual hosted artifacts/results and independent review are reported separately.
