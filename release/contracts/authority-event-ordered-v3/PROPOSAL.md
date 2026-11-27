# Grid authority contract v3 event-ordered — normative proposal review1

Status: NEW_PROPOSAL_EXACT_ACK_PENDING / NO-GO. Supersedes no existing bytes or approvals. Proposed profile ID `unified.authority.event-ordered.v3`; existing strict drafts, checkpoint v1 and P0 stay frozen. No second authority, fabricated timestamp, code deployment or runtime PASS.

## Security contract

Only existing Grid Consul/Raft orders control mutations. Fixed voters LS5/PC4/PC3 require2/3. LS5 preference does not preempt a healthy leader. Every new mutation requires a committed atomic Consul transaction; cached status, node-count, heartbeat and SQLite grant no right. A client unable to establish authority returns UNKNOWN/AUTHORITY_UNAVAILABLE and performs no new effect; timeout alone is not proof of global NO_QUORUM. Actual minority cannot commit a new mutation.

Fencing binds cluster generation, actual leader-lock session+ModifyIndex, assignment_id/revision, lease_id/epoch, grant_revision, authenticated actor/target worker incarnation and affected resource revisions. None is a fabricated Raft term or a caller boolean. Disaster recovery uses a new owner-admitted generation after containment/reconciliation; ordinary leader failover does not reset domain counters or grants. Rejoin reconciles durable receipts/checkpoints before new work.

## Lease expiry: exact enforceable event

Lease authority is the current ACTIVE assignment/grant binding plus its authority-owned Consul lease session. A fenced transaction checks BOTH the actual leader lock session/index and the exact lease session binding/index, along with all domain predicates. A session's invalidation/release/destroy and an explicit committed grant revoke/terminal transition are authoritative invalidation events. Any later transaction relying on the old session or old checked revision MUST fail atomically, even with no successor. Supersession/renewal/terminal transitions change the same checked grant/assignment state; stale tokens cannot publish through a newer leader.

Lease acquisition must bind real session and grant atomically with assignment/registration/reservation state in the approved native transaction layout. Exact key schema/session lifecycle adapter remains A2/ROOT allocation work; no unimplemented API is asserted. Renewal is successful only after authority session renewal and the checked grant revision transition have both succeeded; partial/unknown renewal is UNKNOWN, not a new token. A session renewed without a matching accepted grant revision cannot bypass terminal/revoked state. Resource reservation invalidation is separately checked; capacity entitlement alone never authorizes work.

Two legal orders: publication before invalidation retains its immutable historical receipt and debit; invalidation before publication rejects all publication writes. Renew-before-publish invalidates the old grant_revision; publish-before-renew records one historical effect. No response time can retroactively change that order. Session expiry is eventually ordered by Consul; native TTL is NOT exact wall-clock not_after. A delayed expiry event may allow an otherwise valid transaction after a displayed expiry estimate; this is explicitly within THIS proposed event-ordered profile, unlike the strict draft. Workers conservatively stop at local execution deadlines, but local stopping is defense-in-depth, not distributed authorization proof.

Any product/domain policy requiring an actual civil-time cutoff (PC1 work window, credential expiry, externally imposed provider deadline, user confirmation expiration) retains its own explicitly reviewed enforcement and clock requirements. This profile does not relabel those deadlines as session events or open them. Source/network operation policy remains independently mandatory.

## Atomic publication and idempotency

One bounded native authority transaction checks generation, leader and lease session/index, exact assignment/grant/worker registration, reservation/budget/drain versions, closure holds and current committed eligibility epochs, coverage conflict state and expected manifest/checkpoint roots. It writes roots/checkpoint/outbox, all actual allocation/reservation/debit transitions and immutable receipt together. Every relied-on key carries check-index; semantic comparisons use captured records. Changed dependencies cause whole-transaction rejection. No Consul precheck followed by independent SQL commit is authoritative. Local databases are recoverable projections.

All mutators must participate in coupled eligibility/GC/holds/allocation; unknown bytes remain charged, IDs/paths are not reused and historical data is not deleted by view removal. Oversized closure is rejected, not split into partially authoritative commits. No adoption, release or checkpoint-only exemption bypasses equivalent dependencies.

Idempotency binds generation, authenticated actor, operation/scope, original request ID and canonical intent digest. Same committed intent returns original immutable receipt; changed digest conflicts. Lost response stays UNKNOWN until consistent receipt reconciliation. Missing/unavailable receipt is not automatic rejection or permission to rekey/re-execute. Successor may reconcile an authorized predecessor receipt, not impersonate predecessor or duplicate debit/effect.

## Truthful commit metadata and compatibility

Ordering keys are committed receipt/domain revision/authority index, not UTC. Proposed receipt separates `submitted_at_utc` (authority-observed audit before submit), `observed_committed_at_utc` (authority-observed audit after successful response/consistent receipt observation), `clock_uncertainty_ms` (nullable qualified bound) and `authority_modify_index`/domain revisions. Unknown clocks produce null audit time/bound as permitted by NEW schema; no caller time is labelled exact commit time. These observation timestamps do not bound original commit during long recovery unless actual retained observations establish it. Timestamp ordering validation requires same qualified clock epoch; rollback cannot invent an interval.

Checkpoint v1's committed_at_utc cannot silently become observed_committed_at_utc. A3/A4 must approve a NEW checkpoint schema/profile or explicitly define a reviewed audit-field semantic adapter. Current v1 data-success stays disabled until exact compatibility ACK. No exact majority-commit or FSM-apply UTC scalar is promised by this profile. Counterexamples to strict wall-clock expiry remain valid and are now explicit out-of-profile cases, never marked strict-test PASS.

## External effects and no-quorum

Resource-side fences or independently qualified containment remain mandatory where stale external writes/sockets are possible. Consul rejects stale authority transactions; it cannot stop a previously admitted paused process from writing to an unfenced external resource. No successor execution/reuse where old writer may still act, no release of unknown send debt by TTL alone. Majority loss prohibits new authority grants/renewals/publications/dispatch admissions; local read caches show stale/unknown only. Existing admitted external activity needs separately qualified stopping/containment, not an invented instantaneous partition detector.

## Required tests and review before code

Real3-voter tests: committed invalidation-first rejects old owner with no successor; publication-first preserves receipt; pause before RPC with invalidation ordered in between rejects; wall-time deadline passes without invalidation is accepted only in this NEW profile and explicitly documented; lease/grant renewal races; minority commits fail; successor higher fence rejects old worker; session/key rejoin/generation restore; same request lost response returns one receipt; all-node restart durable recovery; every-mutator closure/budget/GC concurrency; resource containment negative cases.

Peer review: ROOT validates requirement provenance, authority namespace/ownership and overall invariants; A5 reviews assignment/reservation/renewal semantics; A4 closure/allocation/receipt/checkpoint adapter; A3 exact checkpoint/source/civil-time policy; A1 dispatch/transport containment/budget; A6/A7 audit/projection/consumer semantics. Fresh exact ACKs required; no ACK inheritance from strict drafts or read-only envelopes. Then allocate feature files from agreed HEAD, RED/GREEN contract tests and real disposable Consul fault harness, isolated Linux/Windows CI, Draft PR and separate physical Windows acceptance. None run by this proposal.
