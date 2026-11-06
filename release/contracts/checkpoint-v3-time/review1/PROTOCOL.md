# Historical checkpoint V3 — OWNER Option1, review1

NEW major contract only. ROOT relayed direct owner decision2026-11-06 with raw
decision SHA256 aa84f7acbe7632f8d534c96f529c7a39b9b1b26c1a49cf7a69a9366e5c04670e
(immutable owner record publication pending). Event-ordered authority profile
design is published at Unified f3bde56c889ebd5e15665a05e113213f511f2b2a.
This approves time semantics only. Exact peer schema/wire ACK and allocated
implementation remain separate from runtime/physical/full lifecycle admission.

## Distinct result variants

schema.json defines two CLOSED results. COMMITTED contains immutable acquisition
publication_content plus external publication evidence and observation metadata.
COMMIT_UNCONFIRMED contains original identity/intent and reason ONLY, no content,
root success, receipt index, timestamps or fabricated committed evidence. A proven
producer REJECTED is a separate error/outcome, not converted to unknown or commit.
UNKNOWN in A2 publication wire maps to COMMIT_UNCONFIRMED, never to COMMITTED with
unknown time. Only independently confirmed publication maps to a committed result.

Both variants are UNTRUSTED INPUT CLAIMS when parsed from bytes. Structural validity,
a field saying COMMITTED, a proof reference/hash, a boolean or injected fake verifier
does NOT establish authority. The additive codec parses/encodes claims only. Its
production-promotion API must deny unconditionally until a separate explicitly
admitted actual A2/A4 publication proof adapter exists; no such adapter is enabled
by this contract. No authority, listener, factory, DB, provider or shared wiring.

## Mandatory owner fields and exact time spelling

All12 owner fields remain REQUIRED in publication_content: schema_version='3',
dataset_id, instrument_id, partition_id, source_cursor, committed_cursor,
segment_manifest_revision, assignment_revision, lease_epoch, fencing_token,
commit_id, committed_at_utc. Actual commit instant is unknown in this profile:

committed_at_utc = JSON null (required, not omitted)
commit_time_status = 'UNKNOWN_COMMIT_INSTANT' (exact owner field)

commit_time_semantics is NOT an alias and is rejected as unknown in V3. Neither
known observed time nor successful commit fills the actual-instant field.
Confirmed commit with unknown time is a legitimate distinct state, not a missing
receipt or unconfirmed commit. Commit status is based on independent publication
revision/identity/evidence, not any timestamp.

confirmed_observed_at_utc is separate EXTERNAL observation after successful current-
authorized consistent read of the actual original publication receipt/root. It is
qualified provider-observed UTC or null. observed_committed_at_utc is not an implicit
V3 alias. submitted_at_utc is a retained authority observation before original
submit or null, never reconstructed from worker payload. Post-read/submitted clocks
each have separate qualified epoch and uncertainty metadata. Missing/unqualified
clock makes corresponding time/epoch/uncertainty all null. These are claim fields
until real provider evidence is verified. Do not infer cross-epoch order/interval.
Within the same qualified epoch, supplied observations must be time-consistent.
Read observations do not bound original commit during delayed recovery.

## Actual publication evidence, not lifecycle success

publication_evidence has exact closed fields from schema, including provider,
opaque evidence/receipt refs, receipt bytes hash, actual post-read receipt
authority_modify_index, request_id=commit_id UUID, full_intent_sha256, cluster/
generation, dataset/source/partition, dataset/checkpoint revisions, exact content/
manifest/outbox/publication root hashes. Actual trusted producer lookup must bind
ALL of them to the SAME publication; a lifecycle receipt or EFFECT_UNWIRED cannot
supply them. Evidence includes job_id as grant authorization provenance ONLY,
not checkpoint lineage or job completion/adoption. New request identity refinement
uses A2 publication review3 SHA133d922df1edef3694120e204223049edae19b84a914bb528f2368fdb6f30d77,
not a claim that the API is implemented/admitted.

Envelope/content/evidence cluster and commit IDs equal; evidence request_id equals
commit_id; receipt/index/root/content refs match envelope; checkpoint revision
equals content revision; manifest hash equals content.segment_manifest_sha256;
dataset/source/partition equal. Distinct revision domains are never conflated:
segment manifest revision is checked against actual manifest, not dataset revision.
No hash/ref/positive revision alone proves the referenced bytes exist or are current.

Current disclosure authorization is mandatory for historical evidence lookup even
after original grant expiry. Stored fence/session/index is provenance, never a new
write capability. Original UNKNOWN intent/request/key must reconcile before fresh
session-bound content or a successor attempt. No rekey/receipt-path bypass.

## Canonical encoding C3

Complete canonical UTF-8 bytes, no BOM/whitespace/terminal newline. Unique keys
sorted by ASCII bytes at every level. Printable ASCII strings, quote/backslash
escaped only; no optional slash or Unicode escapes. No case folding/normalization.
All counters, revisions, epochs and milliseconds are checked decimal STRINGS
0..9223372036854775807, no sign/leading zero except0, positive fields exclude0.
No JSON numeric literal, NaN/Infinity or bool-to-number coercion. UUIDv4 lowercase;
SHA256 lowercase64hex. Calendar timestamps1970..9999 exact UTC
YYYY-MM-DDTHH:MM:SS.sssZ, valid calendar, no leap seconds or offset normalization.
Null is literal JSON null only; no missing/empty/string-null substitute.
Statuses are exact enums; unsupported versions/old aliases/duplicate/unknown keys
reject. Input must already equal its canonical re-encoding; encode of a typed
untrusted value validates it and returns canonical CLAIM bytes, not authority.

Limits: <=32768 canonical input/output bytes; depth<=12 root depth1; <=48members
per object, no arbitrary extra fields. Current data objects contain no arrays.
Reject excess/deep input before recursive parsing; cap all input before decoding.
No environment variables, filesystem reads, network or dynamic schema loading in
codec. Goldens use synthetic IDs/hashes/clock refs, no real authority evidence.

## Immutable content, DAG and version boundary

publication_content_sha256 hashes COMPLETE canonical content only. External
observation/evidence times/index are not inserted into content/root/own receipt.
DAG is manifest-content->segments/coverage/gaps; checkpoint-content->manifest;
outbox-content->checkpoint/manifest/commit_id; publication-root->three content
objects; external final receipt->root; external authorized observation->receipt/
root/content. No reverse edge or self-index. Later observation may create new
audit object with new observation_id but original content/hash/commit identity
unchanged. Exact repeated observation is inert evidence, never a second commit.

V1 and earlier event-V2 schemas/goldens remain immutable. V3 parser rejects them
and old time field aliases; callers must select an explicit versioned adapter.
No automatic upgrade/downgrade or loss of old semantics. Old data may be read only
by its own admitted reader; this codec does not rewrite it. Owner decision does
not admit full ingestion, LAN, Storage wiring, provider traffic or physical work.

## Fencing, crash/reload and source semantics

Actual publication still requires atomic generation + real leader/lease sessions/
indices + distinct grant/assignment/owner/incarnation + reservation/closure/holds/
eligibility/coverage + actual debit + checkpoint/head/outbox/idempotency. Committed
invalidation first rejects old owner even without successor; publication first
retains historical receipt. Unknown outcome does not become COMMITTED because
its clock is unknown. Native session IDs are actual UUIDs, not logical lease_id;
captured lease_binding_revision is checked lease KV ModifyIndex, not grant revision.

Crash/restart must recover original durable prepared identity/receipt and verify
same content/manifest/evidence before projection/replay. Pure codec reload only
restores UNTRUSTED parsed claim; serializing a claim through disk does not promote
it to authority. Delayed observation changes external audit only. Stale internally
inconsistent fence rejects structurally; even a structurally consistent stale
fence cannot gain runtime authorization from this standalone module.

DATASET/source/partition lineage and fixed source UTC/range/1m reverse-cursor
rules remain: disposition frontier != completeness; gaps persist until supported
source evidence; same symbol different market/incarnation cannot mix. UI view
delete, retirement or codec reload never deletes history. Provider/civil-time
cutoffs and paused external sender containment remain separate gates.

## Required regression evidence classes

Independent codec/contract tests: confirmed+unknown time with bound evidence CLAIM;
unconfirmed has no committed envelope; malformed/absent/conflicting evidence;
qualified/delayed/repeated external observation leaves content constant; serialized
restart/reload stays untrusted; incompatible versions/old aliases reject; malformed
or inconsistent/stale fences never authorize; canonical null/status/timestamp/
evidence bytes exact. Real publication confirmation, renewal/revocation races,
crash durability, no-quorum and stale-writer rejection require actual A2/A4 proof
integration and real disposable authority tests separately. Structural/model
results must not be labelled actual authority, Windows HA or physical PASS.
