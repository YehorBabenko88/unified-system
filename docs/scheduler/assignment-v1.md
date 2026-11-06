# Assignment v1 — proposed integration contract

Status: DESIGN_APPROVED_IN_PRINCIPLE / INTEGRATION_PENDING / NO-GO.
Date: 2026-11-06. Owner: Agent 5. Normative keywords MUST/MUST NOT describe the proposed contract, not deployed behavior.
Base: main @ b9b03a1ce9f887dbe113fd22d0bda8932f46ef80.
This branch changes design and isolated test fixtures only. Production API, consensus, storage implementation, ingestion and UI are unchanged.

## Intent and alternatives

Provide one durable assignment identity shared by placement, authority, storage and workers.
Independent expiry-check-then-write is rejected because supersession can race publication.
A shared serializable authority transaction is proposed. A prepared storage write followed by an authority-ordered publication command is acceptable only if Agent 2 and Agent 4 demonstrate equivalent atomicity, recovery and fencing.
The user approved the architecture and four added fields; the actual cross-service protocol is pending owner approval.

## Ownership

Agent 5 selects workers, reserves CPU/RAM/network/working-space resources, queues work and requests authority operations.
Agent 2 owns authority, epochs, verifiable fencing tokens, quorum and the total order of supersession/publication.
Agent 4 owns storage replica placement, capacity observations, storage reservations/budget revisions, verified checkpoint CAS and atomic publication receipts.
Worker incarnation is identity, never authority. Reservation is capacity entitlement, never lease, commit permission or integrity evidence.
Terminan consumes redacted events/state; tokens MUST NOT appear in events or decision logs.

## Schema and scope

See assignment-v1.schema.json (JSON Schema draft 2020-12). Unknown properties are rejected.
Positive counters are decimal strings (no floating point truncation); compare as arbitrary precision integers.
Scope is the exact tuple (job_id, dataset_id, source_id, partition_id).
Each component is a nonempty opaque case-sensitive identifier; no concatenation-based equality. IDs are allocated by their owner, not inferred from display names.
Instrument identity, if used, is exchange/category/symbol/instrument_version; it cannot substitute for partition scope.
A segment's unique commit key is (dataset_id, source_id, partition_id, segment_id); job_id is deliberately excluded to prevent overlapping jobs publishing duplicates.
Agent 4 must define segment boundaries and detect overlapping ranges with different segment IDs; key uniqueness alone does not establish nonoverlap.

assignment_revision increases on every new grant, supersession or replacement within the scope, even for the same worker.
Revision allocation and compare-and-swap are durable authority-ordered operations. Failed proposals may consume revisions; reuse is forbidden.
Revocation/expiry leaves a durable tombstone; job deletion, restart, compaction and rejoin MUST NOT reset counters.
lease_epoch is independently allocated by Agent 2; every replacement owner or incarnation requires a strictly greater epoch.
authority_term is diagnostic authority provenance, not an epoch or permission substitute.
Renewal retains assignment revision and epoch; authority increments grant_revision and issues a replacement token.
An old token MUST fail after renewal (including the old grant_revision); retries use idempotency receipts.
Changes to scope, worker, incarnation or storage reservation binding require a new assignment revision.
Storage budget changes invalidate the bound revision unless Agent 4 supplies an authority-ordered explicit preservation rule approved by all owners.
No implicit grandfathering is allowed.

## Assignment state machine

| From | Command / condition | To | Effect |
| --- | --- | --- | --- |
| QUEUED | fresh admitted placement + prepared reservations | PREPARING | no worker authority yet |
| PREPARING | quorum grant committed and reservations bound | ACTIVE | durable revision/epoch/token published |
| PREPARING | failure/timeout | QUEUED | reconcile/release provisional reservations |
| ACTIVE | schedule ends, operator drain, pressure | DRAINING | no new batches; bounded permitted in-flight work only |
| ACTIVE / DRAINING | authority revocation or supersession | REVOKED / SUPERSEDED | fence all future publications by old grant |
| ACTIVE / DRAINING | authority expiry | EXPIRED | cannot publish or renew expired grant |
| DRAINING | committed checkpoint + release | COMPLETED | assignment complete; unfinished job returns to QUEUED |
| ACTIVE | final segment/checkpoint committed | COMPLETED | release unused reservations |
| any nonterminal | quorum unavailable | same state, blocked overlay | cannot infer a committed transition |

Terminal assignment records are immutable. Publication and renewal require current state ACTIVE or DRAINING.
Completion atomically transitions the authority record and fences subsequent publication/renewal, even before lease expiry.
Job completion is separate from assignment completion.
Desired PAUSED/DISABLED states are policy intent: authority must record revocation before declaring worker fencing complete.
No-quorum UI can show DRAIN_REQUESTED/UNKNOWN_AUTHORITY; it MUST NOT assert a successful revocation.
State/event delivery may repeat or reorder; consumers reconcile by durable revision and event sequence.

PC1 ACTIVE 15:00–06:00 Europe/Berlin uses a half-open local wall-clock window.
At 06:00, effective node policy blocks new research assignments and batches; running assignments enter drain.
Outside the window node admission is STANDBY; DRAINING describes existing assignments until completion/deadline.
Coordinator duties follow an independent policy and are not disabled by the worker schedule.
Cross-midnight windows use the starting day's weekday. During fall-back both occurrences of a matching local time match;
spring-forward nonexistent times never occur. Evaluate actual UTC instants through Europe/Berlin, never subtract a fixed offset.
A locally observed drain deadline stops work, but only committed revocation/supersession or authority expiry fences publication.
Previously permitted in-flight batch identities and maximum bytes are bound in the ordered drain command.
Drain never permits a batch to publish after lease/reservation expiry.

## Proposed operation shapes (not production APIs)

Every mutation carries request_id, scope and expected assignment/grant revisions.
Requests authenticate the caller independently of the opaque fencing token.

- PreparePlacement(scope, worker_id, incarnation_id, resource_request, observation_revision) -> prepared local resource reservation.
- PrepareStorage(scope, byte_limit, expected_budget_revision, request_id) -> storage reservation with expiry and volume/node identities (Agent 4).
- GrantAssignment(prepared bindings, expected_assignment_revision, request_id) -> Assignment (Agent 2).
- RenewAssignment(scope, assignment_revision, lease_epoch, grant_revision, token, request_id) -> replacement grant with grant_revision + 1.
- SupersedeAssignment(scope, expected_assignment_revision, replacement bindings, request_id) -> new Assignment + old tombstone (Agent 2).
- PublishSegment(assignment identity, grant_revision, token, reservation binding, batch_id, segment_id, content_digest, byte_count, expected_checkpoint_revision, next_checkpoint, request_id) -> durable publication receipt (Agent 4 through Agent 2 ordered operation).
- AdoptCommittedSegment(assignment identity, grant_revision, token, existing_receipt_id, expected_checkpoint_revision, next_checkpoint, request_id) -> checkpoint receipt with zero byte debit; subject to current authority and verified segment coverage.
- ReadReceipt(commit_key or request_id) -> immutable committed receipt or NOT_FOUND/UNKNOWN; UNKNOWN is never proof of absence.
- ReleaseReservation(reservation_id, expected_reservation_revision, request_id) -> reconciled remaining entitlement, not deletion of committed data.

The signatures are design pseudocode. Transport, token format and cross-service transaction API require joint ACK.

## Resource and reservation lifecycle

Observations bind node_id, worker incarnation, volume_id, observed_at, freshness deadline, observation revision,
CPU benchmark/version, allocatable CPU/RAM, memory pressure, disk free/working bytes, storage throughput,
network bandwidth, locality, health and admission state. Unknown units or absent mandatory dimensions block placement.
Freshness is checked at authority grant time, not just at candidate ranking. Future-dated observations beyond
the approved clock bound, stale observations, changed incarnation or unavailable authority time block new assignments.
CPU/RAM/network admission reservations are Agent 5 owned; storage bytes/budget are Agent 4 owned.
The assignment ID resolves an immutable authority binding to the Agent 5 resource reservation ID/revision and quantities.
Grant cannot become ACTIVE until this binding is durable. Replacing it requires a new assignment revision;
release reconciles that binding, never an untrusted worker claim. The wire grant omits the quantities; the binding must be queryable by authorized owners.
No reservation may be issued twice against the same capacity; preparation and binding use durable CAS.
Storage lifecycle: PREPARED -> BOUND -> PARTIALLY_CONSUMED -> CONSUMED or RELEASED;
PREPARED/BOUND/PARTIALLY_CONSUMED may become EXPIRED or REVOKED.
Publication atomically debits actual bytes at most once, records receipt/checkpoint and updates remaining bytes.
Expiry/release frees only unused entitlement. Durable committed data remains accounted as used.
Orphan prepares are reconciled by request ID and authority binding before cleanup; lost responses never justify double allocation.
Storage budget revision is checked in the same ordered publication operation. Changed budget blocks publication and requires a new binding/assignment.
Agent 5 cannot manufacture reservations or extend storage expiry. Agent 4 does not choose a replacement worker.

## Renewal, expiry and clock skew

Authority uses an approved nondecreasing time source and durably preserves expiry semantics across leadership changes/restart.
Validity intervals are half-open: issued_at <= authority_now < expires_at. Equality with expiry is rejected.
UTC epoch milliseconds are integer wire timestamps; Europe/Berlin applies to scheduling only.
Worker wall time never authorizes commit. Authority rejects expired grants; renewal after expiry is a new assignment.
Deployment must supply positive lease TTL, renewal lead time, reservation TTL, observation max age and bounded clock uncertainty.
No guessed defaults are approved here. Missing bounds or clock uncertainty exceeding the bound stops new grants/renewals/publications.
Worker uses monotonic elapsed time to stop before min(lease expiry, reservation expiry, drain deadline)
minus uncertainty and transport/execution safety margin. Restart loses this estimate and requires online reconciliation.
A worker stop estimate only reduces work; it never extends authority validity.
Renewal checks quorum, current identity/grant, storage validity, admission/drain limits and policy.
It cannot silently extend drain deadlines or change a binding. Scheduler schedule alone is not authority revocation.

## Supersession, crash and rejoin

Supersession requires quorum and expected current revision. Exactly one racing proposal wins CAS.
The ordered replacement fences old revision/epoch/incarnation/token before a new owner can publish.
Worker crash is suspicion until authority expiry or committed revocation. Scheduler may queue a replacement proposal
but MUST NOT activate it locally during loss of quorum.
Rejoin creates a fresh unguessable incarnation ID. It cannot reuse the previous process's assignment or token.
Reconcile authority and storage receipts first, then obtain new revision, epoch and reservations.
Resume from the latest verified committed checkpoint with digest and revision; local/staged checkpoints are untrusted.
Preserve ingestion gaps; do not fabricate successful progress from staged data or ACK loss.

## Commit authorization and race ordering

Publication's linearization point is an Agent 2 authority-ordered command atomically coupled to Agent 4 root/checkpoint CAS.
All of the following predicates are checked at that point:
quorum/time valid; current scope/assignment ID/revision; matching worker and incarnation;
current lease epoch/grant revision and verifiable token; unexpired lease;
BOUND/PARTIALLY_CONSUMED reservation with matching scope, ID, budget revision, sufficient bytes and unexpired lifetime;
permitted batch under drain; valid segment identity/digest and checkpoint CAS.
batch_id is authenticated as part of the canonical publication payload and must resolve to the assignment's admitted batch/segment mapping.
During drain, cumulative remaining-byte allowance is atomically debited with publication; concurrent batches cannot each spend the full allowance.
Successful publication stores segment receipt, byte debit and checkpoint update exactly once as one recoverable effect.
An authorize RPC followed by an independent storage write is prohibited.
If authority and storage cannot implement this atomicity, integration remains NO-GO.

If publication precedes supersession, its receipt/checkpoint is visible to the successor.
If supersession precedes publication, the old publication fails without visible segment, checkpoint or debit.
A crash after the linearization point but before response is recovered by the durable receipt; no re-execution of the effect.
Staging immutable bytes is not publication and grants no visibility/ownership.

## Idempotency and no quorum

Idempotency key is (operation, scope, request_id), durably bound to a canonical payload digest.
Same key + same payload returns the original receipt; different payload returns IDEMPOTENCY_CONFLICT.
A committed duplicate segment with identical digest returns ALREADY_COMMITTED, no new debit/checkpoint mutation.
Different digest returns SEGMENT_CONFLICT. Checkpoints are job-scoped. A second job may advance over an identical existing segment
only through AdoptCommittedSegment: verify receipt digest and exact required coverage, validate current assignment authority,
then CAS that job's checkpoint in the same ordered operation. This creates no segment or storage byte debit.
An ordinary ALREADY_COMMITTED response never silently advances another job's checkpoint.
A stale caller may query an authorized receipt but cannot perform a new effect.
Receipt replay after expiry is a read of an existing effect, never a renewed commit permission.
Two owners racing a segment cannot produce two committed receipts.
Retention of deduplication records/tombstones must cover all supported retries; forgetting them requires a separate approved protocol.

Without quorum: no grants, renewal, supersession, commit or authority-dependent reservation binding/release.
Local stopping, read-only diagnostics and capacity-safe provisional holds may continue; holds have no authority.
Prepared/staged work cannot advance committed checkpoints. Reconnection reconciles committed order before retry.
Cached state is labeled stale; uncertain outcomes remain UNKNOWN until quorum/read consistency permits resolution.

## Negative fault-injection matrix

These are acceptance specifications, NOT claims of passing implementation tests.
Run each against the actual joint adapter after all three owners approve the protocol.
Inject loss/crash immediately before and after linearization and before response delivery.
In every rejected mutation assert unchanged root, checkpoint revision, used/reserved bytes and receipt count.

| ID | Injection | Required oracle |
| --- | --- | --- |
| F01 | Old worker publishes after reassignment | STALE_ASSIGNMENT; zero new effects |
| F02 | Restart worker with fresh incarnation and old token | INCARNATION_MISMATCH; reconciliation + new revision/epoch required |
| F03 | Reservation expires at t=100; lease expires at t=200; publish at t=100 | RESERVATION_EXPIRED, no debit |
| F04 | Lease expires at t=100; reservation expires at t=200; publish at t=100 | LEASE_EXPIRED, reservation cannot authorize |
| F05 | Capacity observation past freshness deadline at grant | CAPACITY_STALE; no active assignment/reservation double spend |
| F06a | Publish linearizes before supersession, response lost | one receipt; successor resumes its verified checkpoint |
| F06b | Supersession linearizes before old publish | STALE_ASSIGNMENT; no old effect |
| F07 | Coordinator loses quorum before each grant/renew/supersede/publish | NO_QUORUM/UNKNOWN; no new committed authority/effect |
| F08 | Two workers publish same segment, then conflicting digest | one receipt/debit; stale owner rejected, conflict never overwrites |
| F09 | PC1 reaches 06:00 Berlin while batch active | no new batch; bounded drain; permitted batch only before both expiries; coordinator policy unchanged |
| F10 | Storage budget revision changes after assignment | STORAGE_BUDGET_CHANGED; no publish; rebind through new assignment |
| F11 | Renew succeeds then old grant token is replayed | STALE_GRANT; new grant succeeds once |
| F12 | Retry same request after ACK loss; then change payload | original receipt; IDEMPOTENCY_CONFLICT on changed payload |
| F13 | Crash after prepare before grant; lost release ACK | reconcile orphan once, no double capacity credit |
| F14 | Clock rollback/uncertainty above bound | fail closed; no validity extension |
| F15 | Concurrent supersession proposals + authority restart | one CAS winner; durable monotonic counters |
| F16 | Spring DST skip / fall repeated hour / cross-midnight weekday | actual UTC-to-Berlin membership; no duplicate grant from repeated wall time |
| F17 | Checkpoint CAS conflict or bad digest | CHECKPOINT_CONFLICT/INTEGRITY_FAILURE; zero publication |
| F18 | Same dataset partition/segment via two different job IDs | one global segment receipt, no duplicate committed result |
| F19 | Node rejoin with stale capacity and previous volume identity | no new placement until fresh admitted observation |
| F20 | Expiry/revoke races publication | both legal orders tested; no check-then-write interleaving |
| F21 | Completion followed by publication/renewal before expiry | TERMINAL_ASSIGNMENT; zero new effects |
| F22 | Concurrent permitted batches exceed drain remaining bytes | atomic cumulative debit; excess rejected |
| F23 | Second job adopts committed segment with mismatched coverage | reject; valid coverage advances only its checkpoint once, zero byte debit |

## Approval gates and implementation boundary

### Agent 4 contract review, 2026-11-06

Reviewed STORAGE-CONTRACT.json SHA256 fb82ee72c66defa7e88fc7f502ed3778314e9733d4bbb7baf360e77509d7c6d5.
Agent 5 ACKs the ownership and single atomic transaction direction, not the final wire API.
Outstanding mappings that prevent full contract ACK:
- Storage requires cluster_generation, owner_id, lease_id/current_epoch while this proposal uses worker_id/lease_epoch.
  Agent 2 must supply the authoritative generation and lease identity; generation mismatch must fence all old grants.
  Final schema must bind generation into scope, token, receipts and deduplication, without resetting revision safety during restore.
- Storage does not list grant_revision, batch_id or the drain allowance binding in request_fields; these must be explicit
  or resolved from the same immutable authority binding inside the transaction. Independent prechecks are forbidden.
- Storage idempotency scope includes owner_id; cross-owner retries must still deduplicate by global segment identity.
  Canonical payload encoding and same-segment checkpoint adoption require joint agreement.
- Reservation expiry, budget revision changes, cumulative debit and terminal-assignment fencing must be checked in the atomic boundary.
These are proposed refinements, not permission for scheduler to modify Agent 4 or Agent 2 APIs.

Integration Owner: PENDING (must choose runtime base branch and joint protocol).
Agent 2: PENDING (scope counters, ordered command/root CAS coupling, renew token invalidation, clock policy).
Agent 4: PENDING (atomic debit/receipt/checkpoint, budget revision invalidation, segment overlap/dedupe).
Agent 5 architecture: approved in principle by user; wire schema and pseudocode remain PROPOSED.
No production adapter or production contract tests are implemented on this branch.
P0: joint linearization/recovery protocol and base runtime selection.
P1: TTL/skew/freshness values, segment overlap identity, capacity admission interface and dedupe retention.
P2: redacted placement/event reason-code vocabulary.
Windows acceptance: NOT RUN for scheduler runtime. Local schema/document checks are not fleet acceptance.
Benchmarks: NOT RUN; no runtime or representative hardware admitted for benchmarking.
GO/NO-GO: NO-GO for integration/deployment until contracts ACKed and matrix passes against real adapters.
