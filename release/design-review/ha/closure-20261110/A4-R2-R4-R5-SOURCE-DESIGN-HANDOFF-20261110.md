# Storage source availability and writer-CAS / hold-release decisions

2026-11-10, Europe/Berlin. A4 response to A2/ROOT R2/R4/R5 design-closure
request. Read-only source/design review. No test, authority RPC, native write or
physical action performed. No new runtime or shared wire/API approval.

## Current ACTUAL source

Draft PR56: https://github.com/YehorBabenko88/unified-system/pull/56
Branch feature/storage-native-publication-20261109.
Remote and local HEAD independently checked:
743bfc7590a3d05eff3c42dc6dd4dc0be51e2ea6,
tree2823ec416656820f96836c4189c37e6b98bc7fca. Working source clean.
Its exact A4 imports were previously verified in ROOT source-only PR59
3af06455b601a328e94339327a0597eada802c38/treec5fa79b31a0f12b2db9e1b506edcaa3e48930293;
that is an integration source pin, not a current native/effect grant.

| Actual module | Raw SHA256 | Implemented boundary |
| --- | --- | --- |
| unified_system/storage/result_publication.py | f6c1833771546134f97c45a4c53aae7fe5c16bb3cb73fff182821f4a0be952ed | build_local_closure(entries); stage_local_closure(store,claim,entries); copy_local_closure(source,destination,claim); readback_local_closure(owned_store,claim). Local declared-byte facts only. |
| unified_system/storage/replica_evidence.py | 23ea42e433f70de35345030bce8fc0a8f30d7097dc022006249a7bd714af1c9d | LocalReplicaObservation / LocalInventoryReadback; native/domain/publication eligibility alwaysFalse. Legacy sync capture always unavailable. |
| unified_system/storage/publication_records.py | 65653bc442091bb935bd69d5873c33dc161083ceff51010f6805736ddbca8257 | RetainedPublicationIntent(publication_id,raw_bytes): opaque local custody, not approved native intent. PendingPublicationObservation.native_outcome=UNKNOWN; hold_release_authorized=False. |
| unified_system/storage/publication_recovery.py | 7a25a13533f66296d8626859374ebe850860cd825c5e094e6f2b2092ba0b3285 | PendingPublicationJournal(journal,owned_store): retain, mark_attempt_uncertain, recover_original, verify_staged_original, observation. Existing private Journal/ObjectStore only; no sender/receipt/retry/release. |
| unified_system/storage/publication.py | e9a92a2477c07ebbcf520d6e65a93237a723ed067f106bffcd605e3b4c7b4d12 | async PublicationAdapter.commit_storage(self,intent_bytes) / reconcile_storage(self,original_intent_bytes), both always raise ACTUAL_PUBLICATION_BACKEND_UNAVAILABLE. |

Additional explicit deny-only functions:
commit_result(original_intent_bytes) raises NATIVE_RESULT_PUBLICATION_UNAVAILABLE;
reconcile_result(original_intent_bytes) raises NATIVE_RESULT_RECONCILIATION_UNAVAILABLE;
ReplicaClosureInventory.capture_result_closure(self,original_intent_bytes,*,expected_authority)
is SYNCHRONOUS and raises NATIVE_CLOSURE_CAPTURE_UNAVAILABLE.

ACTUAL positive NativeClosurePlan, NativeSnapshot, NativeClosureCapture,
NativeReplicaClosureInventory, capture_storage_snapshot, PUBLISH/current scientific
READ grant, native commit/receipt validation and active-hold release API: NONE.
Their proposed names are not implementations. The legacy sync fixture is not an
async compatibility alias. A2's private data snapshot substrate, principal
captures and method-shaped providers are not publication proof.

Machine inventory A4-ACTUAL-PUBLICATION-API-INVENTORY-20261110.json binds primary
Git blob OIDs, raw lengths/SHA and AST signatures. No API was invoked by that scan.

## Selected writer-CAS design requirements, not an executable ABI

Use the sole existing A2 Consul authority. Publication must be one native
transaction over the actual current grant/assignment/attempt/lease/cancel state,
original intent/idempotency, dataset expected revision, actual current eligible
replicas/incarnations/domain policy, issued budget/reservation/accounting and
active protection/hold/pin revisions. A2 derives all keys and operations; A4
supplies only fixed-owner validated capture/readback facts. No raw caller ops,
remote precheck plus local commit, unchecked aggregate root or proof DTO success.

Writer reassignment/supersession and hold release must change records checked by
that SAME transaction, in the same serialization domain. If supersession/release
commits first, the old publication cannot succeed. If publication commits first,
its immutable root/revision/receipt/history remain committed. A later release
must resolve that committed effect and preserve/transfer its retained protection;
it cannot erase history or change the old outcome to uncommitted.

Actual native ModifyIndex/session checks are distinct from domain counters,
dataset revisions and worker fence/epoch. Capture reads alone do not authorize a
write. Session invalidation/policy CAS is not strict UTC-at-Raft-commit proof.
Full actual plan is serialized/measured with every relevant check/effect under
native64op/32768 limits; oversize denies, never omits checks or splits atomicity.

## Selected active-hold release requirements

No release is currently executable. Holds/debt remain conservatively charged on
UNKNOWN, response loss, process crash, lease/context expiry, reassignment,
COMPUTED or CANCEL_REQUESTED. None proves an original operation absent, a child
quiescent, retained bytes safe, or a refund authorized. Local file absence/PID
absence/hash equality/JSON flags are not authority evidence.

Distinguish execution/resource holds, pending storage reservations, and retained
dataset/research/dependency protections. These are PURPOSE distinctions, not new
frozen schema enums. Releasing a worker's CPU/RSS hold must not release storage
pins or infer that artifact retention is complete. A5 must supply actual owned
child/attempt/incarnation/quiescence evidence; A2 verifies it against actual
current same-job native state and release authority in the target transaction.

On a known native publication, conversion of pending reservation/debt to retained
dataset accounting/protection must be atomic and idempotent. It must not drop
the bytes' protection before the successor charge/hold exists. A known commit
with projection pending/failed remains committed; publication is not reissued
and debited twice. A7 projection retry resolves the SAME immutable receipt under
current historical-read rights, not the expired worker's old write lease.

A release command needs its own exact original identity/digest/idempotency and
captured current versions; it binds the prior publication/job/attempt/hold. The
actual A2/A5/A4 record names, wire codec and source API must be jointly co-ACKed
before wiring. Concurrent pin/repair/publication/deletion reservations must see
the changed hold version; no interval may count a removed protection as active.

No release authorizes cleanup/deletion. Last confirmed copy, active research pins,
dependency/recovery/backup holds and retired-instrument history remain protected.
No cleanup executor is admitted by current source, no profile/counter/hold reset
on restart or time expiry, no silent garbage collection or policy weakening.

## Interruption, receipt and access boundary

Persist exact original bytes/UUID/key and uncertain holds. Recover through actual
same-authority consistent original bindings plus immutable decoded KV Value
receipt bytes, external native ModifyIndex, dataset root/revision and access
scope. An opaque handle is reacquired from the real issuer, never reconstructed
from a serializable record or local Journal. Missing/incomplete/no-quorum history
stays UNKNOWN, not NOT_FOUND/REJECTED/automatic retry.

Actual current reader rights are required before disclosure/projection payload
readback. Historical committed facts do not make their old worker lease current
or give a new reader access. A6 needs actual scientific bytes and descriptor,
not metadata/golden hashes. Current local readback and principal captures grant
neither payload access nor publication. Independent-domain commissioning and
eligible two-copy protected closure remain unqualified.

HA operator gate remains closed. These are concrete design requirements for
joint R2/R4/R5 closure, not claims that those runtime gates are implemented or
passed. No tests/RPC/native/physical writes or broader source/evidence adoption
are requested by this response.
