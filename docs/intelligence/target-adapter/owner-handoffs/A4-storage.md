# TargetAdapter v1: current Storage source and contract boundary

2026-11-09, Europe/Berlin. Agent4. Read-only handoff, exact TargetAdapter draft
not yet received. Proposed LOCAL_UNATTESTED result direction is compatible in
principle; this is not an exact schema/API/source ACK or a new publication grant.

## Current published component heads

Remote branch heads independently queried on this date, no fetch/reset/mutation:

| Branch | HEAD |
| --- | --- |
| feature/storage-integrity-20261106 | 10157fed4d28606adf587be3494d2f6d42887ce9 |
| feature/storage-runtime-20261107 | cd0286dee5fc41cb7a35b0b6ac431a7ebfc25dfb |
| feature/storage-authority-fixtures-20261107 | 4c664983ca353f2996a133682b561e1883509c88 |
| feature/storage-manifest-codec-20261107 | f9f2d04595cf2360dab78980996ae6c34c9e26fc |
| feature/storage-gateway-disclosure-20261107 | ec5ee6feadc4977af8b0fbaee7f82927d777ab94 |
| feature/storage-result-publication-20261107 | 3e1b4c7c65174fe5775050449162153213e62a8f |

PR49 reader tree bf00f5ea964df6a243941cf3f3de2b2e7803bf89.
PR50 local-byte slice tree3354fe1f7e130dbaa19a8455b8f21b65f4ec067e.
These are component pins, not current ROOT integration or deployable global state.

## Reusable existing APIs

ObjectStore.create/open/put/read/verify: actual exclusive owned local immutable
bytes. Raw SHA256, length and readback are local observations; they are not replica
eligibility, authority, full dependency proof or physical durability qualification.
Primary object_store.py SHA193c4e68e48dcdda212412ed7bd00d23afa04fe36bffb84c074948602bb8f739.
Existing manifest codec SHA43f7eb6961248d7ec21e4f2ab0d4e2c0e70876590d590ccd7cf18b934c9605e1
parses an uncommitted claim, never promotes it.

PR50 result_publication.py SHA1693c5891f1e17913a24bca18430e8ab7bf5f248fdd06d45121822073488a199:
build_local_closure(entries), stage_local_closure(store,claim,entries),
copy_local_closure(source,destination,claim). Declared acyclic graph3..16objects,
mandatory artifact/descriptor/request, 1MiB TOTAL payload bytes,32KiB metadata.
All exact payload bytes are retained without JSON reencoding. Caller edges remain
untrusted; semantic_closure_verified/publication_confirmed areFalse.

replica_evidence.py SHA110da716e39abde25368975b95ac6b6bf81229b3a25a253cb01d8f52a1666d76:
LocalReplicaObservation is untrusted, replica_valid/failure_domain_verified/
publication_confirmed alwaysFalse. Two local directories are one failure domain.
ReplicaClosureInventory.capture_result_closure raises
NATIVE_CLOSURE_CAPTURE_UNAVAILABLE. commit_result/reconcile_result unconditionally
raise NATIVE_RESULT_PUBLICATION_UNAVAILABLE/NATIVE_RESULT_RECONCILIATION_UNAVAILABLE.
No current positive A4 native publication or reconciliation implementation exists.

PR49 get_dataset_manifest(request_bytes, *, owner_read_capability,
expected_identity_authority,pinned_owned_store)->bytes. Reader SHA
a374718b80456b916500956c294e2988af539dc8b02c1735d39a450d17e1b06e;
request schema SHAaf86efffc096b2412bc0f046360ca42eeb3206216858e21603f1ee87ccc99a89.
Exact admitted READ identity source is A2 module SHA
84093865e8477ef6562100d41137922785446c9cb4e024c9ba7105593a2b36c1,
owner commit2cb6b21eac5617ff39ad7a96b7e1c73118e0af00. It is a READ-only dependency
pin, not a claim that no newer A2 broker exists or a grant to dispatch/write.
GET uses fixed owner require_issued_read on independently expected actual issuer,
same commissioned store, exact original request/binding, before read and return.
Do not upgrade READ handles into TargetAdapter compute/publication permission.

## Proposed result semantics for exact draft review

LOCAL_UNATTESTED may describe actual retained isolated artifact bytes. Bind raw
SHA256 and length to those exact bytes, source HEAD/tree/hash, operation/input
digests, truthful producer/provenance and existing experiment identity/revision.
Do not invent an experiment registry, committed dataset identity/revision, replica
receipt, trusted provenance or a global filesystem existence claim.

publication remains UNPROVEN. Native commit, replica verification and runtime
admission are NOT_ESTABLISHED/false, with explicit scope rather than a claim that
all remote authorities contain no record. UNKNOWN outcomes/history remain UNKNOWN;
no local absence, file existence or hash match can establish global absence,
terminal rejection or authoritative commit. Preserve original request/idempotency
identity, bytes and uncertain holds until actual owner reconciliation.

Artifact production, byte storage, local hash readback, semantic validity,
publication, replication and access admission are independent dimensions. Null or
UNAVAILABLE finance/coverage stays that way; raw provenance is not authentication.
Schema boolean flags are assertions, not proof. Exact field names/closed schema,
bounds/error states and source capsule require review of ROOT's forthcoming draft.

## Concrete missing publication/reconciliation/access gates

1. A2 actual issued write/assignment/attempt/cancellation authority and exact
   current native record-to-CAS mapping; same native transaction must linearize
   supersession versus publication and bind original full intent/receipt.
2. Actual complete semantic dependency closure and same-authority current
   eligibility, holds/pins/reservation/accounting protection for two independently
   admitted domains. No two-domain lab has been established by A4 evidence.
3. Actual native commit sender and consistent reconciliation of the SAME original
   UUID/key/intent and immutable receipt, including UNKNOWN/crash histories.
   Local A4 commit/reconcile functions remain unavailable.
4. Existing ResultStore projection of a real consistently resolved receipt under
   current read rights. A7 last reviewed local SliceA887e3eeaf23ef8d9d1429435bc88bbac8099c6e6
   stages exact descriptors only; positive project/read remain denied, no receipt
   callback/JSON can unlock them. This is a reviewed pin, not a fresh remote query.
5. ROOT-owned access policy/source qualification, exact issuer/store/resource and
   original actor/consumer scope for each action. Filesystem paths, class labels,
   local artifact hashes and READ capabilities cannot authorize other effects.
   Network/public route/native job/production admission remains separate.

No implementation change, new tests/PASS, hosted rerun, merge, deployment, cleanup
or physical/network mutation was performed for this handoff. Prior exact-source
tests retain their original source/scope; no evidence transfer to TargetAdapter.
