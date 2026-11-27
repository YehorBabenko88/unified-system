# Publication evidence producer — NEW owner-time V3 profile

Status: EXACT A3/A4/A5/ROOT REVIEW PENDING. Direct owner time decision relayed by
ROOT on2026-11-06 selects NEW checkpoint V3 option1 only. This does not approve
full Storage/LAN feature scope, shared wiring, runtime or physical action.
Checkpoint schema/spec/golden have ONE editor A3; this is the A2 producer contract,
not a competing checkpoint schema. Prior v1, event-v2-review1, publication wire
review1/2/3 and exact ACKs stay immutable and do not automatically transfer.

## Exact owner fields and two independent facts

NEW checkpoint content retains required `committed_at_utc` with literal JSON null
and uses EXACT field `commit_time_status` with EXACT string
`UNKNOWN_COMMIT_INSTANT`. Old proposed `commit_time_semantics` is NOT an alias,
fallback field or accepted input to this new profile. A3 must pin a new explicit
schema/version/identifier before any parser/producer accepts it. Unknown version
or old field in the NEW shape rejects; old formats retain their own semantics.

COMMIT confirmation and knowledge of COMMIT time are independent:

* Confirmed commit may have UNKNOWN_COMMIT_INSTANT. This is NOT an unknown outcome.
* Unconfirmed outcome is proposed exact status `COMMIT_UNCONFIRMED`, never a
  committed checkpoint envelope. No candidate/staging/lifecycle response can be
  promoted by adding audit timestamps or status labels.
* A2 proposes confirmation status `COMMIT_CONFIRMED` for positively verified
  publication evidence. Exact tag placement/version requires A3/ROOT ACK; do not
  silently reuse lifecycle COMMITTED or convert old checkpoint responses.

## Real publication evidence required before confirmed envelope

Producer must use current real disclosure authorization, a consistent read from
the SAME Grid Consul authority and the exact original request/commit UUID and
idempotency binding. It verifies ALL of:

1. Actual authoritative PUBLICATION receipt, not a lifecycle receipt or local
   SQL/outbox/caller object. Receipt operation/profile is the exact admitted
   publication version; its stored immutable identity/digest/root/debit result is
   valid and paired with original idempotency mapping.
2. Actual receipt KV ModifyIndex read from Consul, positive bounded decimal,
   and exact committed dataset/checkpoint revisions from that receipt. Revision
   and authority provenance establish order; no UTC value substitutes for them.
3. Same cluster/generation/request_id=commit_id, authorized actor/scope, immutable
   content SHA256, manifest/outbox/publication root and complete admitted composite
   fence/native session provenance as the original committed publication.
4. Retained immutable root/content and verifiable evidence referenced by that
   receipt; byte hashes and canonical structure match. Historical publication
   need not be today's dataset head, but its original root/closure/receipt lineage
   must be independently resolvable. Current head alone is not original evidence.

Unavailable read, malformed/conflicting evidence, missing or inconsistent pair,
unsupported profile or unresolved submission yields COMMIT_UNCONFIRMED with no
committed envelope. A consistent missing receipt is not by itself proof that an
inflight original request cannot later apply; preserve original identity/digest
and pending accounting until qualified reconciliation resolves it. Do not rekey,
retry effects or rehash changed leader/session provenance under the old key.

The current PR264 lifecycle module is EFFECT_UNWIRED and supplies NONE of the
above publication evidence. Its authority_modify_index cannot be reused here.
Actual atomic publication producer, full domain records and durable prepared
intent/receipt registry remain next allocated implementation, not asserted facts.

## Observation clock and hash DAG

Proposed exact external field `confirmed_observed_at_utc`: actual observation
AFTER verified consistent publication receipt/root lookup, with qualified
observer/provider identity, clock epoch/source evidence and uncertainty, or null
if no qualified clock exists. It is NEVER actual majority/apply/linearization time.
A delayed observation/restart cannot reconstruct original commit instant.

External observation binds original cluster/generation/commit identity, original
content/root hashes, actual publication receipt reference+ModifyIndex, committed
revisions and unique observation identity. Optional retained submitted observation
has its own qualified epoch/uncertainty; worker payload cannot fabricate it. No
cross-epoch interval or rollback ordering is inferred. No timestamp affects
authorization/fencing, civil-time/provider rules, quotas or UI freshness by itself.

Canonical encoding proposal to A3: complete immutable content uses exact required
null and status string; observation uses qualified canonical UTC
YYYY-MM-DDTHH:MM:SS.sssZ (valid Gregorian1970..9999) or literal null; no missing,
zero, empty string or string-null coercion. All revisions/indices/uncertainties
canonical bounded decimal strings, no JSON numbers. Duplicate/unknown keys reject.
Qualified non-null observed time requires matching clock source/epoch/uncertainty
evidence; null is not lack of commit confirmation. Final exact field placement,
schema constants, evidence IDs and semantic validators are A3's single candidate.

Content/root is hashed BEFORE publication. Receipt refers to that root; external
observation refers to receipt/root/content. Never insert observation time/index/
status/evidence into original content or mutate/recompute its hash after commit.
Repeated observations preserve identical original content and receipt identity;
new observations have independent IDs and truthful later samples or null.

## Required producer/adapter tests

* Confirmed receipt+valid immutable evidence+unqualified clock => confirmed commit,
  required content null/UNKNOWN_COMMIT_INSTANT and null external observed time.
* No verified commit => COMMIT_UNCONFIRMED, no committed envelope even with valid UTC.
* Delayed/repeated observation => same content/root/commit/receipt revisions,
  distinct observation identity; no original-instant fabrication/hash cycle.
* Crash before/after publication/reply/observation => original identity/receipt
  reconciliation, no duplicate debit or reconstructed time; restart reload hashes.
* Old incompatible version/commit_time_semantics alias => reject NEW parser.
* Stale worker/leader/session/grant => publication rejects after authoritative
  invalidation; historical receipt read still needs current disclosure auth.
* Wrong receipt kind/index/root/generation/request/idem/debit evidence => unconfirmed
  or explicit conflict, never confirmed by a lifecycle result or caller assertion.

These are NOT_RUN production-adapter tests. A3/A4 exact candidate ACK and ROOT
allocation precede shared wiring; independent lifecycle/harness work continues.
