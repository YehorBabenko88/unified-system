# Issued scheduler records — NEW v1-c3 review1 proposal

PROPOSED / JOINT ACK PENDING / NOT AN ADMITTED PRODUCER. A2 owns the actual
`authority_runtime_v1` Consul implementation and all native keys/transactions.
This package supplies concrete record shapes for that review; it does not create
another authority. The old cd274d… request schema is NOT an issued grant schema.
Schema validity, hashes, fixtures and local SQLite never provide permission.

## Schemas and representation

schema-registry.json pins raw bytes of four closed draft2020-12 schemas:
assignment, worker-resource-reservation, capacity-observation, node-resource-ledger.
No schema embeds its own digest. Consumers pin registry+exact schema out of band.
All object fields required, explicit null where declared, no extra keys. Values
are canonical C3 printable ASCII, no numeric literals, no implicit conversion of
legacy domains. Numeric strings are exact0..9223372036854775807; revisions/epochs
and positive quantities exclude0. Overflow means UNAVAILABLE/new version, never
wrap, round or truncate. Native Consul operation Index remains an integer in its
native API, not a C3 domain scalar. Native ModifyIndex is verified read metadata;
it cannot be embedded as a record's self-index before that transaction commits.

The four scalar identity/units rules are shared. Opaque registry-issued IDs use
`[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}` with exact end; they are never IP/hostname
derivatives. Canonical lowercase UUIDv4 names assignment, request, lease, native
session, worker incarnation, resource reservation and observation. cluster_id is
globally issued. node/dataset/source IDs retain their registered meaning for the
entire cluster lifetime and are NEVER reused for different entities across any
generation. Partition identity within dataset+source is equally generation-stable;
job ID may be generation-scoped because it is not in the stable partition key.
Generation-local legacy dataset/source/partition aliases are UNAVAILABLE in this
profile until an explicitly approved stable registry mapping is supplied. A2 must
verify A3/A4's stable partition identity record; these fixture strings do not prove
registry provenance. No implicit string normalization, reuse or mapping is allowed. Instrument ID is Agent3-issued dataset lineage
reference, explicit null for jobs without instruments. A4 owns storage reservation
ID issuance and full-scope binding; it is opaque, not silently UUID-normalized.

Topology: one enrolled parent worker coordinator/daemon incarnation per node,
not one OS process for Grid/Math/Terminan. Concurrent job children require distinct
execution_attempt_id and current native process proof bound to node, parent worker
incarnation and full assignment scope. Serialized grant bytes never confer child
permission. Assignment/Reservation bind attempt UUID and process-proof reference;
PREPARING may have null proof. ACTIVE/DRAINING execution/publication requires an
actual admitted native attempt proof/session, not merely a non-null reference.
Reassignment uses a fresh attempt ID and revokes old delegation. A2/ROOT's native
NodeControl/attempt proof schema, attachment transition and identity provider remain
PENDING; this package does not claim multi-process runtime admission.

CPU entitlement uses cpu_millicores, exactly1000/logical processor. ram_bytes and
scratch_bytes are bytes; disk/network bytes_per_second are distinct throughput
dimensions. Unit profile is exact
LOGICAL_PROCESSOR_1000_MILLICORES_BYTES_BYTES_PER_SECOND. Scratch is worker space,
not storage replica capacity. CPU benchmark stores separate SHA256 byte-work,
elapsed_ns and explicitly floored byte/second score; it never becomes entitlement.
Capacity-observation CPU total must equal logical_processor_count*1000 and fit
u63; reservation totals must remain <= admitted ledger totals in every dimension.
Policies may cap measured capacity but never infer entitlement from benchmark.
The example benchmark profile matches the explicit opt-in measurement module;
it is not automatically promoted to authenticated observations.

## Scope, keys and monotonicity

Full assignment scope is cluster_id,cluster_generation,job_id,dataset_id,source_id,
partition_id. scope-key-vector.json pins the domain-separated C3 preimage and its
SHA256. ROOT selected stable partition keys excluding job_id AND generation,
while record values bind the complete six-field scope. Vector preimage contains
only cluster_id,dataset_id,source_id,partition_id with its own domain separator.
Proposed prefix P is `{A2_authority_namespace}/authority-v1/clusters/{cluster_id}/`.
Suffixes remain a review placeholder until A2 publishes its actual layout.

| Record | Proposed suffix under P | Revision scope |
|---|---|---|
| Assignment | partitions/{partition_sha256}/assignment | stable partition across jobs/generations |
| Persistent counter | partitions/{partition_sha256}/revision-counter | stable partition, never deleted/reset |
| WorkerResourceReservation | reservations/{reservation_id} | cluster/generation/reservation_id |
| CapacityObservation | observations/{observation_id} | immutable admitted observation |
| Current observation head | nodes/{node_id}/observation-current | node+worker incarnation monotonic pointer |
| NodeResourceLedger | nodes/{node_id}/resource-ledger | cluster/node, survives restart/generation |
| Worker registration | nodes/{node_id}/registration | A2-issued process registration |
| Worker admission policy | nodes/{node_id}/policy | work schedule/drain/health policy |
| Freshness session anchor | nodes/{node_id}/freshness | actual A2 session-bound key |

A2 must finalize these native keys and other leader/generation/principal/lease/
global-request/idempotency keys. Client paths/indices never supply authority.
All trusted reads happen in A2. ROOT selected a COMMON global request UUID and
idempotency registry under existing N/authority-v1 with generation-independent
immutable tombstones. Existing frozen Mux digests/indexes remain separate bindings;
no digest alias or silent re-key. Exact A2 preimages/key suffixes still pending. Worker registration, policy and session-anchor
record schemas remain A2-owned dependencies, not covert aliases for these four.

Assignment creation and every supersession atomically advance persistent counter
and assignment_revision, even same owner/spec or a new job/generation for the same partition. Cancellation/revocation at least
invalidates current grant/state; if represented as supersession it also advances
assignment_revision. New assignment never reuses old ID/revision. Counter overflow
closes scope. grant_revision tracks changes to authority grant binding; lease_epoch
is the actual A2-issued epoch, never replaced by either revision. Lease epoch
comparisons are within the actual lease identity/authority contract; no ordering
is inferred between unrelated IDs. fencing_token is independently A2-issued.
Pure native session renewal need not change assignment_revision; any grant tuple
change must update grant_revision and every current dependent binding atomically.
Resource reservation revision changes on lifecycle/binding changes. Capacity
ledger revision changes on actual reservation debits/releases or capacity rebasing.

## State, lifecycle and recovery

Assignment PREPARING -> ACTIVE -> DRAINING -> terminal SUPERSEDED/CANCELLED/COMPLETED; A2 may
invalidate ACTIVE directly on worker loss or policy. New ownership is a new
monotonic revision, not revival. Reservation RESERVED -> DRAINING -> REVOKED/
RELEASED. No UNKNOWN timeout refunds. New reservation creation requires atomically
adding each requested resource to *previous* node reserved total, rejecting any
overflow/exhaustion. The ledger is necessary: CAS on each separate reservation
alone cannot prevent two concurrent callers spending the same capacity.

Worker restart/rejoin changes registration incarnation through A2. Publication
checks that shared registration key, fencing all old incarnations in one native
transaction even when their many old assignments cannot fit one transaction.
Old uncertain resource charges survive restart. Releases/rebases require verified
authority outcomes; they are not erased by resetting telemetry or creating a new
ledger. Old receipts remain historical evidence, not current dispatch permission.

Creation requires ACTIVE worker schedule, admitted health/resources/freshness,
current registration and storage reservation. STANDBY blocks new research work;
existing valid work may checkpoint under explicit DRAINING policy. Coordinator
duties use separate policy. Publication checks the same policy key but must not
blindly reject all DRAINING checkpoints or silently allow cancelled work. Exact
allowed operation/state pairs require joint A2/A4/ROOT policy ACK.

Source monotonic_ns belongs only to producer_clock_id and is never compared across
machines. freshness_session_id is an actual authority session anchor, not a claimed
expiry. New assignments check its session and current observation head/immutable record indexes. A2 must freeze
max-age measurement, clock uncertainty and committed invalidation semantics; this
proposal does NOT assume session TTL equals exact wall-clock age. Until that
freshness contract/policy is admitted, capacity success remains UNAVAILABLE.
Lease semantics are ROOT's separately approved event-ordered v3: actual session
invalidation/revoke/supersession order, not a display UTC deadline. No literal
wall-clock commit timestamp or trusted source clock is fabricated by these schemas.

## Required cross-record checks and single linearization point

Assignment/reservation must match full scope, assignment ID/revision, node/process,
lease ID/epoch/session/fencing, grant revision, execution attempt/process-proof
reference, units and resource vector. Their
reservation ID/revision and ISSUED capacity-ledger revision must agree with each
other. issued_capacity_record_revision, issued_observation and issued policy/
schedule revisions are immutable issuance provenance, NOT mandatory equality with
latest mutable ledger/telemetry/policy. Creating or releasing unrelated reservation
B, or refreshing telemetry, must leave unchanged A valid without grant fanout.
Current observation head/immutable record must agree with current ledger and
registration for new admission. Current native ledger index is checked independently
when needed for publication; historical issued revisions need not equal it. Reservation storage is not held here: assignment's storage ID/budget
must match A4's actual full-scope issued reservation and current budget record.

Publication checks current assignment, worker registration, actual execution
attempt proof/session, lease session+binding,
worker resource reservation, current capacity observation head/record, freshness session/ledger and
worker policy native indexes. It also checks A4's reservation, current budget and
ALL relied-on closure/allocation/hold/coverage/eligibility records, dataset and
checkpoint heads, global request identity and idempotency bindings. Same transaction
writes actual checkpoint/head/outbox/debit and immutable receipt. No claimed root
can replace unreviewed closure dependencies. A2 builds it, A4 supplies storage
evidence/debits. Scheduler never performs storage publication.

Supersession MUST CAS the exact current assignment key publication checks; atomically
advance counter, revoke old reservation/attempt delegation, prepare new attempt
and reconcile old/new node ledgers with
new grant/reservation creation and request/receipt bindings. New node fresh
registration/policy/observation/session and A4 reservation/budget are checked too.
Same-node ledger changes must coalesce into ONE correctly computed CAS, not two
writes to the same expected index. Old lease may already be invalid: supersession
does not require its old session still alive. Renewal/cancel/rejoin must invalidate
or mutate every current authority key relied on by their affected old grant.

Publication-first preserves exactly one historical checkpoint/debit/receipt;
supersession-first rejects stale publication even if no successor is dispatched.
Two publishers with the same expected head cannot both commit. Request UUID is
cluster-wide across operation types; publication request_id=commit_id, separate
owner-scoped idempotency key. UNKNOWN reconciles full ORIGINAL intent/IDs, never
new key/reservation. No quorum: no grants/supersession/cancel/authority mutation;
local pause/containment may continue, but provides no release/commit proof.

## Measured encoding ledger and unresolved gates

atomic-operation-ledger.json counts actual serialized *synthetic* native operation
arrays and bytes, not native execution or load. Publication baseline18checks+8CAS
writes =26ops/4035bytes; cross-node supersession15checks+12CAS =27ops/11171bytes.
Each enumerated closure dependency adds one check. At32 dependencies this fixture
uses58/59ops; at64 it uses90/91 and must reject atomically, never split/truncate.
HashiCorp documents64 operations and512kB/value for the txn API:
https://developer.hashicorp.com/consul/api-docs/txn . Actual deployed version/config,
payload/response bounds and real closure/value sizes still require A2 measurement.
Attaching/verifying a new child native proof before PREPARING -> ACTIVE requires
a separate A2-frozen bounded transition; this fixture ledger does not qualify it.
Fixture CAS indices/record payloads are deliberately non-admitted placeholders;
they do NOT implement actual resource release, session-lock creation or storage
debit. No production max-closure count, lease, batch or payload limit is inferred.

P0: A2 exact keys/session binding/proof schemas, A4 complete closure/debit record
layout, freshness/drain policies and full issued-domain ACK. P1: actual native
same-transaction race/UNKNOWN/no-quorum/exhaustion/expiry/rejoin tests, measured
operation/byte ledger for real builder. Endpoint/Windows/fleet acceptance separate.
validate_proposal.py proves4 record examples,25 negative schema/binding cases,
two A-survives-B/telemetry cases, two job/generation-stable partition key cases
and one policy-capped capacity case
only; it cannot prove record provenance, freshness, storage validity or authority.
