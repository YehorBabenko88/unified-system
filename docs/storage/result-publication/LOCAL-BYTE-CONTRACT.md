# Local declared byte graph v1

This isolated Slice A contract is not the proposed native closure/CAS ABI.

build_local_closure(entries) takes a tuple of (role, exact_bytes, dependency_hashes)
tuples. It returns LocalByteClosure with canonical ASCII C3 metadata schema
unified.storage.local-declared-byte-closure.v1. There are3..16 distinct roles and
content hashes, mandatory artifact/descriptor/request, no missing edges/cycles,
maximum1MiB total nonempty payload bytes and32KiB metadata. Payload JSON numbers,
encoding and source bytes are retained without parsing/reencoding. Empty or
duplicate-content entries are unsupported and rejected, never silently deduped.

The closed metadata root has schema and objects; each object has role, sha256,
bytes (canonical positive u63 string), dependencies (sorted unique hashes).
Objects are sorted by role. Root hash is SHA256 of exact canonical metadata.
Constructor revalidates and value returns a detached decoded dictionary.
The caller supplies dependencies: shape/acyclicity is checked, semantic completeness,
artifact schema, source/provenance, input coverage and producer truth are NOT verified.
No caller flag can change semantic_closure_verified/publication_confirmed fromFalse.

stage_local_closure(store, claim, entries) validates the entire declared input
before writing any object, writes immutable content-addressed payloads/root using
the existing ObjectStore, then re-reads them. copy_local_closure(source,destination,
claim) rejects same root/store identity; reads all bounded source bytes before
destination effects, copies and re-reads the full destination inventory including
root. Existing bytes are not replaced. Partial writes remain on failure; no rollback
or cleanup success is implied. The observation is point-in-time local bytes only,
not a hostile in-process sandbox or perpetual integrity/failure independence proof.

LocalReplicaObservation canonical schema unified.storage.local-copy-observation.v1
has exact closure_sha256, source_store_id, destination_store_id, object_count,
byte_count plus schema. Count includes the metadata root. Parsed observations are
untrusted; replica_valid/failure_domain_verified/publication_confirmed are always
False. No authoritative node/domain/receipt fields are admitted by this schema.

ReplicaClosureInventory.capture_result_closure, commit_result and reconcile_result
unconditionally raise StorageBlocked. They do not touch arbitrary supplied values,
accept callbacks, construct a grant or infer absence. Actual successor APIs and
native schemas require separate exact A2/ROOT co-ACK before a positive path exists.
