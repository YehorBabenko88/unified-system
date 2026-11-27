# Executed local prerequisites, not native publication

2026-11-09. This separate branch preserves PR50 source/evidence. Actual A2
publication/reconciliation API and physical two-domain commissioning are missing.
No committed scientific artifact or access permission is produced by this slice.

## Actual immutable inventory readback

readback_local_closure(owned_store, claim) verifies every declared object AND root
with actual ObjectStore.verify reads. The returned local inventory retains each
same-read byte length/hash/filesystem identity. Source corruption or missing bytes
fails without replacing them. The inventory is bounded by existing local declared
graph limits. Caller edges and payload schema/source/provenance are not validated
as semantic closure by this readback. LocalInventoryReadback is immutable and
nonserializable; private construction is provenance hygiene, NOT an authority
boundary against hostile Python. Native eligibility/domain/semantic closure/
publication properties remainFalse. Two copied roots on one host remain one model.

The existing ReplicaClosureInventory.capture_result_closure stub is synchronous
and unavailable. Its old local-fixture ABI is not silently replaced by an async
native proof. The future async native class/API/version/source and complete
same-authority record-to-CAS contract require explicit owner co-ACK.

## Actual original-byte custody and interruption recovery

RetainedPublicationIntent(publication_id, raw_bytes) is an untrusted opaque local
candidate: strict UUID4 and exact bytes1..16384, raw SHA256 computed locally. It
does not parse or approve a native publication intent, bind a native caller or
establish that an internal request UUID agrees with its custody identifier.
Actual native owner parsing/identity joins remain mandatory before any send.

PendingPublicationJournal(journal, owned_store) requires exact existing Journal
and ObjectStore types, an initialized private owned journal and trusted ROOT
directory custody. It reuses the existing transitions table, not a second registry
or native state authority. Files/ancestors/sidecars/link identity and2MiB/64record
bounds are checked. New-intent capacity is checked BEFORE staging effects. It is
not an adversarial filesystem race/ACL/physical durability qualification. ROOT
must provide exclusive journal lifecycle custody; local mutex is not a native
writer grant or distributed lock.

retain(original) writes actual immutable original bytes, reads them back, and
appends the exact base64/hash/length/original ID in an OBSERVING journal record.
Repeated identical ID/bytes is a local no-op; differing bytes conflict. The record
uses closed LOCAL schema unified.storage.pending-original.v1 and only RETAINED or
ATTEMPT_UNCERTAIN phases. No native receipt, revision, COMMITTED state or permission
field is accepted. Such records never serve as an A2 capture/receipt/projection
handle, even when their hash chain is valid.

mark_attempt_uncertain(id) persists BEFORE a future independently admitted send;
the marker does not claim that any send happened. recover_original(id) recovers
exact raw bytes from verified local custody after process exit without changing
ID, invoking a target, sending a native request or minting a receipt. UNKNOWN is
the only native outcome. No retry/refund/hold-release permission is returned.
Consistent actual A2 original-intent lookup is still needed for a native outcome.

Loss/corruption of the staged object is explicit through verify_staged_original;
the journal's retained exact raw original remains recoverable but does not repair
the store automatically. A lost append response may follow an actual SQLite
commit: the error remains uncertain and fresh recovery reads the same original.
No bytes, sidecars, records, holds or uncertainty are deleted or reset. An unrelated
journal/schema, bad hash chain, malformed base64 or corrupt SQLite fails closed.

## Evidence boundaries and current tests

TDD RED/GREEN for missing APIs, closed corrupt-SQLite errors and capacity-before-IO.
17 own local tests cover actual copies/readbacks, corruption, exact retained
original, identity conflict, actual child os._exit after durable attempt marker,
append-response loss after actual SQLite commit, malformed/foreign records and
budget denial before staging. Related retained62+11+new17 regression90PASS/0skip
was observed on CPython3.12.10. These are working-tree results until exact source
qualification. No native Consul/issuer/closure/replica-domain/receipt/access test
has passed in this slice; no A2/A5/A7/global counts transfer.

Dedicated workflow selects exact17 stdlib-only cases with primary Git byte guard
before project imports and after tests. It must not be labelled native or
two-domain E2E. Hosted execution is separate evidence and not yet claimed.
