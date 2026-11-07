# Research job composition contract — review1, PROPOSED

No supported runtime API or admission ACK. Owner directive8791d40c authorizes
isolated implementation after ownership ACK; this document requests exact joint
contract approval before implementation. Production/physical/trading prohibited.

Base6825964bf52375b134c6eb4487808963a0d128ed,
tree2b3988fa4cdd334b6ae63067fdb34987dd0e6840.
Branch feature/agent5-gateway-jobs-20261107. Owned NEW paths only:
unified_system/gateway_jobs.py, tests/gateway_jobs/**,
docs/intelligence/jobs/**, .github/workflows/gateway-jobs.yml.
ROOT owns composition/harness/report/ownership registry; no shared edits.

## Proposed Python composition surface, not registered endpoints

ResearchJobs(owner_bindings) is an async adapter over existing owner components.
Bindings MUST be actual source-qualified implementations, not caller capabilities,
boolean/None proof, structural protocols or synthetic provider substitutions.
No new scheduler, consensus, authority ledger or result registry is created.

- await submit(original_request_bytes, *, context) -> JobObservation
- await lookup(original_request_bytes, *, context) -> JobObservation
- await status(job_id, *, context) -> JobObservation
- await cancel(original_cancel_bytes, *, context) -> JobObservation
- await reconnect(original_request_bytes, *, context) -> JobObservation

These are NEW proposed names, not aliases for old synchronous SingleNodeScheduler
or frozen A2 methods. Wire ingress/result bytes and actual binding call signatures
must be co-approved; public Gateway route composition belongs to ROOT.

## Immutable submission identity and ownership

Closed versioned intent must bind original UUID4 request_id, cluster UUID4,
job UUID4, operation, idempotency key, exact plan digest and full plan,
immutable dataset/revision/manifest hash, exact instrument tuple, research adapter
profile/version/configuration, bounded resource demand, deadline policy and
separate original authenticated actor/quota owner. Final field schemas/types
await A2/A4/A7; these prose fields are not an approved byte codec.
Job ID is stable within cluster and independent of IP/hostname/process.
Gateway generates no authority/lease/reservation IDs. Assignment, lease epoch,
revision, incarnation, child attempt and storage reservation remain owner-issued.
Context is actual ROOT/A2 nonserializable authenticated authority; never from JSON.
Job owner is bound durably to actual registry identity, not hypothesis text.
Quota owner and actor are not inferred equal to worker/storage/coordinator nodes.
Same idempotency key plus different immutable intent conflicts; same original
intent resolves original durable receipt, without another dispatch/charge/job.

## Admission, status and execution

Validate bounded plan first; verification alone creates no job. Before effects,
require actual SUBMIT_RESEARCH authority, dataset disclosure/admission, owner
quota and resource reservations, current Assignment/lease/fencing/attempt,
storage/result publication eligibility and supported research adapter.
Missing actual contracts yields NOT_SUBMITTED, job_id=null, effects_authorized=false
only when no submit attempt was made. Once submission is attempted, timeout,
cancellation of coroutine or lost quorum yields UNKNOWN for SAME original UUID,
key and bytes; NEVER relabel as NOT_SUBMITTED, refund or generate replacement.
Capacity staleness/resource pressure/schedule constraints deny fresh dispatch;
coordinator policy stays independent of worker working schedule.

Proposed observation states: NOT_SUBMITTED (pre-attempt only), UNKNOWN,
QUEUED, RUNNING, CANCEL_REQUESTED, CANCELLED, COMPLETED, FAILED.
These lifecycle names need owner mapping and are not native result statuses.
Observation binds authoritative job/assignment/attempt identity, original request,
monotonic status revision/source and read authorization. Local journal state,
planning digest or adapter output alone cannot establish RUNNING/COMPLETED.
Completion requires actual committed result/experiment registry evidence and
immutable digest/provenance, no mock SUCCESS. A7 owns deterministic computation;
A4 owns publication; A2 owns atomic authorization and fencing.

## Cancellation, races and reconnect

Cancellation is a NEW immutable command with its own original UUID/idempotency
and exact target job/scope. Actual CANCEL_OWN_JOB policy verifies ownership and
linearizes cancellation against dispatch/publication through A2 authority.
Requested cancellation is not effective worker stop or quota refund. Preserve
committed results/events and historical receipts. Contain only verified owned
child; pause/drain are not authority revocation. UNKNOWN cancellation reconciles
its SAME command, independently of original submission uncertainty.

Reconnect is lookup of SAME submission intent/UUID/key, not resubmission.
Current READ_RESEARCH rights apply even to historical receipts. Restart requires
new worker incarnation and current owner-verified child attachment; old worker
fenced. Historical commit proof grants no current dispatch. No automatic takeover,
lease renewal, rekey, storage release or restart on client disconnect.

## Bounded disposable validation and next executable step

No arbitrary backend plugin, provider injection, external process startup or
physical controls. Independent executable closure step authorized by ROOT: focused tests
for no-binding NOT_SUBMITTED with zero owner effects and original UNKNOWN
identity preservation. After exact positive contract ACK, add actual admitted
disposable owner bindings plus A7 existing offline research adapter. Synthetic DATA allowed, fake admission is not.
Missing actual backend is dependency-unavailable, not skipped native PASS.
Test quota/resource exhaustion, stale generation/incarnation, no quorum, duplicate
UUID/changed intent, cancellation/publication order, unauthorized status/cancel,
restart reconciliation, completion digest and output limits. Versioned limits
require measured owner load/encoded transaction budgets; offline plan limits
are not approved distributed admission capacity. Windows/Ubuntu CI separate.

## ACK requests and implementation gates

ROOT: exact ownership registry, immutable base, provider composition and status
visibility. A2: auth/actor/quota, durable original command/results, actual async
Assignment/admission/cancel/reconciliation and same-order proof. A4: admitted
immutable dataset/result provenance, storage publication and retained charges.
A7 via ROOT: exact existing executable research adapter input/output/cancellation,
result/experiment registry reuse and deterministic synthetic vector. Silence is
not ACK. ROOT subsequently authorized the local-only closed module and independent tests.
Keep positive owner bindings, actual adapters and workflow admission absent until
exact contract decision; closure tests/docs install no backend.

## Implemented independent closure slice (not positive contract ACK)

ROOT explicitly authorized independent strictintent/no-binding/UNKNOWN tests and
closed module after this proposal. ResearchJobs has NO owner_bindings constructor
and cannot execute any owner operation. Its local preparation schema is deliberately
unified.gateway.job-local-preparation.v1: NOT the shared submission wire codec.
It reuses existing offline plan validation (including its Math label) without
importing/bootstrapping Math or any A7 engine; this is not the A7 execution codec.

submit validates canonical bounded local bytes, returns NOT_SUBMITTED with null
job_id and no effects. lookup/reconnect raise JobUnavailable carrying frozen
LocalOriginal bytes/UUID/key/digest; UNKNOWN is absence of authoritative knowledge,
not evidence a native operation occurred. status raises unavailable without an
invented registry record. cancel also raises unavailable and does NOT parse a
submission intent as a cancellation command. Context is ignored for authority:
no value, typed shape or claimed role can enable this unbound shell.

Seven local tests passed after an initial module-absent import RED. These cover
strict fields/canonical identity, no-binding closure, immutable original retry
identity, unavailable status/cancel, and rejected backend injection. They are not
native tests, admission, workload benchmarks or runtime milestone. Existing16
Gateway offline tests remain a separate baseline. Positive owner bindings,
shared request/result/cancel codecs, data disclosure, quotas, Assignment, A7
computation, publication and real registry remain unimplemented/dependencies.
