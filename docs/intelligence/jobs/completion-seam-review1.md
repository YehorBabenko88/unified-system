# Completion observation and callsite — review1, exact joint ACK pending

ROOT allocated A2/A4/A7 Slice-A; that is not final API/native publication ACK.
This NEW schema is proposed observer DATA only, never input authority/proof.
It applies ONLY after actual publication COMMITTED is independently known.
Other lifecycle states/submission/cancel codecs remain separate owner proposals.

Closed oneOf: known COMMITTED + projection DURABLE => COMPLETED;
known COMMITTED + projection PENDING/UNKNOWN/FAILED => RESULT_PROJECTION_PENDING.
No branch rewrites a known commit to UNKNOWN or makes a projection failure a
new publication request. This schema imposes no new authority/status ledger.

identity binds cluster/job/execution_attempt/original publication request UUID,
exact original publication-intent SHA256, original compute input SHA256 and raw
artifact SHA256. All seven values compare to actual original intent/native issued
Assignment/child and actual A7 staged artifact; schema equality alone is not proof.
publication.receipt_bytes_sha256 hashes exact immutable approved A2 receipt bytes,
NOT its JSON reconstruction, self-hash or current mutable record. This field is
an OBSERVER digest; actual provider handle/index binding stays outside schema.
A2 must confirm its exact canonical receipt byte boundary before this field is
usable. No assumed receipt serialization/profile or native-index alias.

DURABLE projection_identity_sha256 proposal is SHA256(C3(identity)) using EXACT
seven schema fields and no schema discriminator inside this preimage. This is a
NEW projection logical-key candidate, not a replacement for frozen common-command
hash/index or a caller-selected SQLite key. A7 must coapprove or supply its exact
existing compatible idempotency key; no alias to rowid/experiment ID/hash of bytes
alone. Durable outcome only after actual SQLite commit and exact identity/receipt/
artifact bytes binding verified. Conflict never overwrites/adopts another record.

## Proposed internal callsite ordering; names below NOT approved methods

A5 gateway_jobs.py future completion callsite must invoke only exact actual
A2/A4/A7 owner bindings. A4 owns stage/closure/eligible replica verification and
A2 publication operation. Resolve SAME original native receipt and actual current
read rights, yielding actual process-local owner proof. Then A7's exact successor
project_gateway_artifact_commit (signature pending) projects SAME stage/receipt.
Only a verified durable A7 outcome can produce schema DURABLE branch. No public
caller raw JSON handle, callback, bool validator or None-return admission.

After restart reacquire actual A2 historical proof from SAME original durable
command/receipt. Process-local proof is never persisted or reconstructed from
these JSON fields. Current read rights required; historical projection does NOT
require expired worker lease to become current. Worker dispatch/current result
publication remain separate and require actual live grant. Recovery projection
never invokes publish again, releases uncertain physical charges or increments
native/domain revisions. Row missing/corrupt yields projection pending/failure,
not absent authority commit. Committed but artifact unavailable remains explicit
retrieval failure; durable metadata does not guarantee present physical bytes.

No current completion callsite exists: ResearchJobs remains unbound. Candidate
changes are docs ONLY in A5 allocated paths; no positive code/HTTP wiring. Exact
A2 receipt/proof and A7 projection return/error/idempotency schema, A4 actual
2-domain retention/closure and ROOT coACK required before code. Two same-disk
folders cannot qualify independent domains. Financial fields remain unavailable;
computed artifact is not automatically completed/verified financial evidence.
