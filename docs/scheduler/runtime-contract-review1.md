# Scheduler runtime seams — NEW review1, not full API ACK

Status: implementation of local command handoff and synthetic subprocess control;
native authority, storage, endpoints and fleet acceptance remain UNAVAILABLE.
This is not a replacement for the approved Assignment v1 specification. The NEW
`unified.scheduler.command.v1-c3.review1` profile carries assignment *requests*,
not grants, lease proofs, assignment state or publication permission. Existing
numeric Assignment/model encodings are not converted or assigned this lineage.

## Identity and units

Revision scope is exactly `(cluster_id, cluster_generation, job_id, dataset_id,
source_id, partition_id)`. IDs are registry-issued opaque printable ASCII tokens,
1..128 characters `[A-Za-z0-9][A-Za-z0-9_.:-]*`, never derived from IP/hostname.
Uniqueness of node/job/dataset/source is within cluster+generation; partition is
within source+dataset. Cluster identity is globally issued; generation is a
separate registry-issued identity. No local process invents their provenance.
Request, assignment and worker incarnation are canonical lowercase UUIDv4; their
uniqueness is cluster-wide (request UUID reuse conflicts even across scopes).
Worker incarnation names exactly one process, never authority. Instrument ID is
Agent3-owned dataset lineage, not a substitute for source/partition identity.
Storage reservation IDs are Agent4-issued within cluster/generation, bound to
full job scope; Worker resource reservation IDs remain A2/A5 joint-grant binding.

All counters/resource quantities use canonical decimal STRINGs 0..2^63-1, no
leading zero, exponent, fraction, sign, whitespace or numeric/boolean aliases.
CPU entitlement is `cpu_millicores`: one logical processor = 1000 millicores.
RAM and worker scratch use bytes; disk and network use bytes/second. The unit
profile string pins all five dimensions. CPU benchmark score is separate from
entitlement, never renamed, rounded or converted to millicores. Storage replica
capacity/placement belongs to Agent4; worker scratch does not grant it.

## Executed local state machine

SQLite FULL synchronous transaction persists complete exact canonical request
bytes and original request/idempotency IDs. PREPARED -> SUBMITTED is committed
before external handoff. A crash/reply loss leaves SUBMITTED/UNKNOWN; another
submit with same bytes never repeats execute. Reconcile passes the *original*
bytes to authority. Same request or key with changed bytes conflicts. COMMITTED
and REJECTED terminal receipts are immutable only after adapter verification.
`COMMITTED` here means this assignment command committed, NOT data publication.

Before worker start, current authority dispatch admission is required; raw grant
receipt and original intent go to worker. Worker must verify again before work
and every externally visible effect. An earlier scheduler check cannot eliminate
the network/expiry race. Dispatch NONE -> SENDING is durable before call; an
uncertain call is queried by original request, never blindly restarted.

Drain intent is durable and excludes new dispatch claims atomically. Worker
control must retain a pause received before start under the same identity, and
pause must be idempotent. Failed pause is retried during reconciliation. Drain
does not publish/adopt checkpoints, release reservations, cancel authority grants
or mark job complete. The local subprocess is explicitly synthetic, bounded to
32 control identities and 1024-byte messages with <=2s response deadline. These
are test-harness safety bounds, not production admission limits.

## Native port contracts pending joint exact-byte freeze

`Authority.execute(raw_command)->(state, raw_receipt_or_none)` and
`reconcile(original_raw_command)` use the same immutable original IDs. UNKNOWN
has no success proof. `verify_outcome(raw,state,receipt)` must validate actual
committed records/effects and full intent binding. `require_dispatch(raw,receipt)`
must reject loss of quorum, stale capacity, invalid node/incarnation, superseded
assignment, lease/session loss, fencing mismatch, expired/revoked reservation,
budget revision mismatch and schedule closure. Python return types alone do not
prove authority. A missing port is closed. This draft's ASSIGN-only codec does not
claim to implement renewal, supersession, cancellation or rejoin APIs yet.

Worker: `start(original_request_id,raw_command,raw_grant_receipt)->raw_response`,
`inspect(original_request_id)->raw_response_or_none`, `pause(original_request_id)`.
Real adapter must bind target node+incarnation, verify authority at start/effect,
retain idempotency and durable pause intent, and authenticate query responses.
SyntheticWorker deliberately does none of the native authentication/publication;
its responses cannot qualify a checkpoint or an execution permission.

Storage reservation prepare/validate/reconcile/release and checkpoint
publication/adoption methods do not yet exist in Agent4's admitted source. They
will be wired only after exact signatures, receipt types and native indexes ACK.
There is no storage publication implementation in this Scheduler.

## One transaction order: matrix for A2/A4 approval

Both supersession and publication must check the same authoritative full-scope
assignment record and native ModifyIndex, leader/session and generation. Publish
also checks assignment revision, lease epoch, fencing token, worker incarnation,
worker resource grant/capacity revision, storage reservation/budget revision,
dataset closure and current checkpoint/root; atomically writes original immutable
request receipt, resulting checkpoint and actual storage debit. A2 owns native
transaction construction; A4 owns immutable object/manifest evidence and budgets.

Supersession-first invalidates old grant: publish rejects without checkpoint or
debit. Publish-first creates exactly one historical receipt/checkpoint/debit:
later supersession cannot erase that historical commit or turn it into current
worker authority. Two publishers of one expected checkpoint cannot both commit.
No expiry-check-then-unprotected-write path is permitted. Exact key names and
native record grammar/index tuple are A2-owned PENDING; invented scheduler keys
are not an alternative authority. Event-ordered v3 semantics follow ROOT's separate
decision; local wall clocks never synthesize quorum, session validity or expiry.

## Limits, evidence and release gates

No metadata or batch payload is admitted by this command profile. Decoder's
4096-byte preparse bound is parser safety, not a load-qualified Assignment limit.
Working-set/active-assignment counts, leases, observation maximum age, reservation
and renewal budgets remain PENDING actual workload tests and joint policy ACK.
Review4 carrier constraints remain conjunctive: no numeric literal domains, no
silent string conversion, no truncation beyond 32 carrier array entries, no old
schema hash/root/cursor reuse. Unsupported domains remain UNAVAILABLE. New domain
schema hashes do not grant authority or automatically authorize Control Mux data.

Fixture tests qualify local CODE only. Real Consul concurrent supersession versus
publication, real storage reservation expiry/budget changes, native checkpoint
recovery, Windows hosted acceptance and physical runtime are separate gates.

## Opt-in local measurement

ROOT additionally allocated benchmarks.py: explicit opt-in, single-process SHA256
loop <=2s requested duration, private TemporaryDirectory file <=8MiB, IPv4
127.0.0.1 ephemeral transfer <=1MiB with common 2s deadline, and read-only Windows
GlobalMemoryStatusEx. No import/service startup invokes it. Each result records
actual bytes, elapsed monotonic nanoseconds and explicitly floored byte/second
ratio. CPU benchmark units do not imply millicores; fsync includes OS/filesystem
behavior, not raw-device guarantees; loopback is explicitly not LAN bandwidth.
The one local sample cannot qualify production payload, concurrency, TTL or fleet
capacity limits. Zero, negative, boolean and oversized configuration reject before
any measurement. Only own scratch files are removed.
