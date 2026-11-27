# Full publication v3 wire and native provenance — exact design candidate review3

Status: A3/A4/A5/ROOT EXACT REVIEW PENDING. This is independent next-slice design,
not an implemented API or modification to frozen checkpoint/common-wire drafts.
Lifecycle PR264 at076f/431a is immutable pending audit and cannot authorize this
publication. Same Grid Consul/Raft leader and canonical commands/generation only.

## Typed inputs and outputs

Proposed `commit_publication(leader: ConsulLease, request: PublicationRequest,
context: AuthenticatedContext) -> PublicationOutcome`. Context is a real current
provider handle; raw actor/capability fields cannot authenticate it. No endpoint
is introduced. Builder performs consistent native reads itself; caller cannot
submit KV paths, arbitrary transaction verbs, indices as permissions or trust flags.

PublicationRequest is a closed object with schema=`unified.publication.v3-review3`,
cluster_id, cluster_generation, request_id, idempotency_key, actor_id,
job_id, assignment_id, assignment_revision, lease_id, lease_epoch, grant_revision,
owner_id, node_id, worker_incarnation_id, dataset_id, source_id, partition_id,
expected_dataset_revision, expected_checkpoint_revision, commit_id,
publication_content_sha256, manifest_content_sha256, outbox_content_sha256,
closure_attestation_id, resource_reservation_id, storage_reservation_id,
capacity_observation_id, resource_reservation_revision, capacity_observation_revision,
resource_units_schema_sha256, drain_id and drain_revision (both nullable only
for no-drain publication).

UUID fields: cluster_id/generation, assignment_id, logical lease_id, node_id,
worker_incarnation_id, dataset_id, commit_id and reservation/observation/attestation
IDs. request_id is canonical UUIDv4 and MUST equal commit_id exactly.
job_id/idempotency_key/actor_id/owner_id/source_id/partition_id are bounded
canonical IDs per common wire. All counters are canonical decimal u63 strings;
assignment_revision/lease_epoch/grant_revision positive, expected root revisions
may be0 only for genesis. Hashes are lowercase SHA256. Unknown fields, duplicate
JSON keys, numbers-as-counters, invalid nulls and excessive encoded bytes reject.
All immutable acquisition content must match the exact A3 new schema and full
lineage; content hash is verified against bytes, not just caller assertion.

PublicationOutcome closed tagged variants:

* COMMITTED: schema, status, effect_status=`DATA_PUBLICATION_COMMITTED`,
  request_id, idempotency_key, full_intent_sha256, commit_id, cluster_id,
  cluster_generation, publication_root_sha256, publication_content_sha256,
  manifest_content_sha256, outbox_content_sha256, dataset_revision,
  checkpoint_revision, receipt_ref and historical=true. Actual receipt
  `authority_modify_index` is attached by the authorized consistent READ result,
  never stored as a guess of its own future index. No exact UTC commit timestamp.
* UNKNOWN: schema, status, request_id, idempotency_key, full_intent_sha256,
  reason=`AUTHORITY_UNAVAILABLE|RECEIPT_UNVERIFIED`; no effect/permit/root success.
* REJECTED: same identity/digest plus exact reason from current verified
  generation/fence/state/closure/reservation/conflict predicates, only after
  consistent lookup reconciles any concurrent identical committed receipt.
  Idempotency key/digest mismatch is CONFLICT, never a new identity fallback.

`receipt_ref` is an opaque registry ID resolving to the authoritative publication
receipt in the same namespace. Authorized lookup verifies its immutable content,
root and identity bindings; it cannot resolve a lifecycle receipt as publication.
Current read disclosure authorization is mandatory even for expired historical
grants. A successor may reconcile original intent, never rekey it silently.

## Full composite fence and native binding

The full grant record contains EXACT cluster_id, cluster_generation, job_id,
dataset_id, source_id, partition_id, assignment_id,
assignment_revision, logical lease_id, lease_epoch, grant_revision, owner_id,
node_id, worker_incarnation_id, state and actual lease_session_id. Distinct counters:

* assignment_revision strictly increases on EVERY new assignment/initial grant,
  supersession or replacement within the authoritative scope, even for identical
  owner/node/incarnation and unchanged specification; renewal alone retains it;
* lease_epoch changes on ownership/incarnation replacement/supersession;
* grant_revision changes on renewal/state transitions;
* KV ModifyIndex changes on every checked record change and is separately captured.

Proposed grant lifecycle v3 must define initial values, monotonicity and recovery
with A5; current lifecycle internal revision does NOT supply this tuple. No
automatic mapping from worker_id to owner_id/node_id is admitted. Registration
must explicitly bind the actual stable worker principal, enrolled node and fresh
process incarnation in owner-managed records.

`authority_session_binding` in checkpoint content means:
leader_session_id = actual current `ConsulLease.session_id`;
lease_session_id = actual dedicated grant-session UUID;
lease_binding_revision = actual ModifyIndex of the CHECKED native lease lock.
leader_lock_index in composite fence = actual `ConsulLease.token`, independently
checked against the existing leader key. Both sessions require native canonical
UUID validation; generic schema ID-pattern acceptance alone is insufficient.

All provenance is reconstructed from trusted consistent native records before
building the publication intent; captured lease key/session/index is checked
atomically again at apply. It is included in the canonical full-intent digest and
immutable publication receipt provenance. If caller content contains a stale
session binding, reject/resnapshot; never rewrite content beneath its hash.
Native lease binding may survive renewal at same index; changed grant_revision
still invalidates old publication. Changed leader session may require preparing
a new content/intent ONLY after original UNKNOWN outcome reconciliation; a new
leader cannot erase a historical receipt or bypass idempotency by rehashing.

## Namespace and key ownership proposal

N is existing authority namespace. Recovery anchor is existing
`N/commands/generation`. Proposed new domain keys are
`N/publication-v3/<generation>/...`; suffixes below use approved canonical UUID
or SHA256 of complete canonical scope, never untrusted caller paths:

`grants/<assignment_id>`; `lease-locks/<lease_id>`;
`registrations/<node_id>/<worker_incarnation_id>`;
`principals/<actor-id-hash>`;
`resource-reservations/<id>`; `capacity-observations/<id>`;
`storage-reservations/<id>`; `storage-budgets/<volume-id>`;
`closure-attestations/<id>`; `eligibility-epochs/<volume-or-instance-id>`;
`allocation-roots/<volume-id>`; `hold-roots/<attestation-id>`;
`coverage/<lineage-scope-hash>`; `dataset-heads/<dataset_id>`;
`checkpoints/<lineage-scope-hash>`; `drains/<id>`;
`outbox/<commit_id>`; `receipts/<commit_id>`;
`idempotency/<SHA256([cluster,generation,actor,operation,scope,key])>`.

These keys are a concrete proposal requiring A4/A5/ROOT ownership/layout ACK;
they do not yet exist as production contracts. A4 may supply existing canonical
records instead of duplicating storage state, but the SAME checked serialization
domain is mandatory. No snapshot-ring/local SQL epoch, SQLite quota or separate
metadata store supplies distributed authority. The experimental lifecycle keys
are not automatically promoted to these full domain records.

## Atomic transaction recipe

1. Check generation anchor index/value; existing leader session+index; actual
   dedicated lease lock session+index; grant record index and ACTIVE/permitted
   DRAINING full composite fence; admitted registration and principal indices.
2. Check resource reservation and capacity observation provenance/revisions,
   storage reservation/budget/drain, immutable closure attestation, all current
   eligibility epochs, allocation/hold roots, lineage coverage conflict state,
   expected dataset/checkpoint roots and absent original outbox/receipt/dedupe.
3. In SAME transaction CAS root/checkpoint/outbox/receipt/idempotency binding,
   cumulative actual verified allocation/reservation/budget/drain debits, coverage
   and hold conversion. Full transitive holds/GC/eligibility mutators must obey
   the jointly approved A4 protocol; checking a historical manifest is insufficient.
4. No partial transaction on any failed predicate. Native response loss or409
   after retry triggers original consistent receipt reconciliation. No publication
   completion/receipt is inferred from staging, local database, callback success
   or lease estimate. Missing receipt under unavailable authority is UNKNOWN.

Publication-specific proposed native ceiling<=64KV operations and<=32768encoded
request bytes (distinct from lifecycle module32/16384). No silent change to its
limits. A4 must produce measured bounded closure/epoch/allocation/hold roots and
an operation-count ledger for accepted publication classes. If the complete
predicate+write set does not fit, reject before effects; no batching partially
authoritative publication. No numeric ceiling is load-qualified here.

## Checkpoint audit boundary and remaining decisions

Exact A3 candidate schema141d1842/protocol4f1acf74 is the content/audit shape under
review: required committed_at_utc:null +UNKNOWN_COMMIT_INSTANT, external observed
audit only. Audit observation uses ACTUAL publication receipt ModifyIndex and
same immutable root/content/commit identity after current authorized consistent
lookup. No hash cycle or v1 reinterpretation. Producer clock may be unqualified:
null stays unknown, never a synthetic commit instant or display freshness proof.

Needed before code: A5 full-grant/session lifecycle and reservation/capacity key
bindings; A4 exact closure/eligibility/holds/coverage/allocation root protocol and
record ownership; ROOT namespace/provider/ACL and new source allocation; A3 exact
new checkpoint mapping plus owner null/audit representation decision. Prepared
immutable bytes stay under A4 holds until committed or safely reconciled. External
socket/filesystem fencing and civil-time policies remain independently qualified.
This wire candidate is not an excuse to stop independent module/harness tests.

## Review2 identity/idempotency and checkpoint scope corrections

A3 current new checkpoint mapping is retained explicitly: request_id and commit_id are the SAME canonical lowercase UUIDv4 identity. Reject inequality before preparing or submitting authority effects. Do not derive commit_id from an arbitrary bounded string or silently assign a new UUID during retry. idempotency_key is a distinct bounded canonical client key, not an alias for request_id; both are immutable across retry/reconciliation. UUID-format references elsewhere do not alter this equality.

Before any receipt-path choice, consistent lookup checks BOTH original receipt key (commit_id) and idempotency key binding. The idempotency record stores exact request_id=commit_id, authenticated actor, generation, operation, complete dataset/source/partition scope, full_intent_sha256 and original receipt_ref. In one publication transaction, check-index/CAS both original receipt and idempotency records; they are either created together with the domain effects or neither. Same key+same full intent resolves ORIGINAL receipt; any changed request/commit identity, scope or digest conflicts. A receipt without its exact matching idempotency record (or converse) is inconsistent/UNKNOWN, never absence or permission to publish anew. Reusing a commit_id with a different key also conflicts; check the original receipt's stored key binding. Concurrent identical callers reconcile before rejecting. A later leader must query original mappings before preparing altered session-bound content.

UNKNOWN preserves the original request_id/commit_id/idempotency_key/full intent and pending reservations. Client cannot generate a different receipt path/key to bypass reconciliation. The actual durable prepared-intent/outbox registry MUST bind the logical publication attempt to these identities before any ambiguous submission; the adapter must recover that binding after restart, not rely on caller memory. A changed key for the same unresolved prepared publication is rejected using this registry. Exact prepared-intent owner/key/schema and atomic preparation/adoption rules are next A2/A4/A5 protocol work and remain an implementation gate; current lifecycle module does not implement them. Absence of a final receipt alone is not proof the old request cannot still apply. Only qualified reconciliation/fencing establishes rejection/resolution before a genuinely new attempt. Logical coverage/global-segment dedup also remain mandatory; neither identity binding nor a new UUID permits duplicate publication/debit.

This candidate covers DATASET-PARTITION checkpoint publication only. Dataset root and the exact dataset/source/partition lineage checkpoint are atomically checked/updated. No job_id, job checkpoint CAS, cross-job adoption, ownership transfer or extra checkpoint scope is implied. Job-level checkpoints/adoption need a separately reviewed request/schema/transaction extension with equivalent fencing, closure, pin and accounting predicates. A Sync view delete is unrelated to either checkpoint scope.

All other review1 dependencies remain: A4 coupled closure/eligibility/holds/coverage/allocation records and COMPLETE operation/byte ledger; A5 full grant/session/reservation lifecycle; ROOT namespace/provider/source allocation; exact A3 new content/audit representation.64operations/32768bytes are proposed upper bounds only, not proof the complete transaction fits or is qualified. Fresh exact review2 ACK required; no review1 ACK inheritance or runtime admission.

## Review3 scheduler scope, counters and typed resources

Full authoritative assignment scope is EXACT tuple (cluster_id,cluster_generation,job_id,dataset_id,source_id,partition_id), not concatenated IDs and not inferred from assignment_id or a local queue. Grant and assignment-counter records both carry this immutable scope. A durable scope-counter key is SHA256 of its complete canonical tuple. Every new assignment/initial grant/supersession/replacement CAS allocates a strictly greater assignment_revision from that counter, including same owner/incarnation; it never resets on restart, leader failover, terminal/job deletion, compaction or rejoin. Failed consumed allocations are never reused. Overflow rejects before effects. Disaster recovery uses explicitly new generation; old generation tombstones/evidence remain and are never numerically compared as current grants. Renewal preserves assignment_revision and lease_epoch but advances grant_revision; lifecycle's internal revision is not reused as this counter.

Grant record immutably binds full scope plus assignment_id, assignment_revision, logical lease_id, lease_epoch, grant_revision, owner_id, node_id, worker_incarnation_id, resource_reservation_id/revision, storage_reservation_id/budget binding, capacity_observation_id/revision and resource_units_schema_sha256. Scope/worker/incarnation/storage-binding changes require new assignment revision. Publication request fields must equal this checked grant and authoritative resource/storage records exactly. A mismatching job_id cannot borrow another job's assignment. Job identity binds authorization/provenance, not dataset segment uniqueness: global content/coverage/segment identity still excludes job_id so overlapping jobs cannot double-publish.

Resource reservation key /resource-reservations/<id> is an authority-owned record, not A5's provisional SQLite hold. Required semantic fields: full assignment scope; resource_reservation_id and revision; state BOUND or permitted DRAINING; owner/node/incarnation; bound assignment/lease/grant identities; capacity_observation_id/revision; units_schema_sha256; reserved CPU/RAM/scratch/storage-throughput/network-throughput quantities. Publication captures/checks its actual ModifyIndex and exact requested resource_reservation_revision. Capacity key /capacity-observations/<id> binds actual provider/enrollment/registration node/incarnation, observation revision, measurement provenance/schema hash, units schema hash and COMMITTED eligibility state. Changed or revoked observation/policy index rejects; a caller observation timestamp or local scalar does not confer eligibility. Atomic resource-capacity ledger/hold creation and release remain A5/A2 next protocol work, not an existing authority API.

Concrete unit proposal for A5 review (not an accepted conversion): cpu_millicores is integer units of1/1000 enrolled logical processor, with explicit cpu_basis=LOGICAL_PROCESSOR_1000_MILLICORES; RAM and scratch are integer bytes; storage/network throughput are integer bytes/second. Benchmark-normalized CPU scores are separate typed measurements and MUST NOT be added to millicores. Logical/physical core identity or SMT ratios cannot silently change the basis. Full units schema hash+provider version are pinned; unknown/mismatched units/basis block binding. A5 may propose a different exact scale before ACK; current local scores/holds never automatically become authoritative quantities. No floating-point conversion, caller estimate or unqualified capacity freshness assumption is admitted.

Drain key /drains/<drain_id> has exact revision, assignment full scope/fence, allowed immutable batch IDs, cumulative remaining byte/operation allowance and state. Request drain_id/drain_revision are both null or both non-null; if non-null, capture/check actual record ModifyIndex plus exact semantic revision and debit same transaction. A local event sequence or remaining counter is not this authority drain ledger. Resource/storage records need respective owner-approved schemas, CPU/byte/throughput bounds, provenance and complete operation-count ledger before implementation.

This remains DATASET-PARTITION checkpoint publication. job_id scope binding adds NO job-checkpoint write, job completion, assignment terminal transition, capacity release, adoption or transfer effect. Those require separate explicit versioned operations. Durable prepared identity binding/UNKNOWN rules from review2 remain mandatory. Fresh review3 ACK required; review1/2 remain immutable; code PR264 unchanged.
