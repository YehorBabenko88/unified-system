# TargetAdapter20 -> native lab13 — PURE contract proposal review1

2026-11-09. ROOT choice/coACK PENDING. No actual native profile/issuer, scheduler,
job mutation, worker, public endpoint or shared Root file changes. Existing direct
stand remains DIRECT_DISPOSABLE_SYNTHETIC with native fields null, unaltered.
Root baseline PR54 cf7dad91bf0d3a24073c91e0d3e326e6d9e7d2db; this proposal is
owned A5 docs/harness on base3e498de, not an integration base/admission ACK.

## What is impossible without an explicit binding

Frozen13 schema19357891 does not contain dataset/experiment/strategy/result-schema
or outer request SHA. Directly dropping20 into13 loses intent; putting outerSHA in
input_request_sha256 corrupts fixed A7input identity. A2/A5 prefer the single-job
profile successor below, but ROOT has not chosen it. A new13 command schema is NOT
necessary merely to change the server-selected commissioned_profile_sha256.
Existing13 field set/schema remain unchanged for representable inputs. Current
broker's closed profile-v1 rejects profile-v2; no silent parser/schema upgrade.

Exact20 mappings and13 mappings are in mapping.json. ALL20 fields remain in exact
original canonical outer bytes. Root current direct-request bytes are NEVER
rewritten/upgraded, including their nulls/LOCAL_TEST_ONLY principal/quota semantics.
A new explicit Root native outer schema/mode/service consent is required, for
example proposed unified.gateway.target-native-request.v1-review1 with
NATIVE_RESEARCH_ADMISSION_REQUEST_NOT_PERMISSION. These names are candidate labels, not new
registered Root API. Root owns final schema and result/consumer contract.
A separately explicit native operation is not a migration of an old direct Journal
receipt; no automatic new UUID/key/profile to escape UNKNOWN/conflict.

Native outer keeps20 FIELD NAMES. authority_generation is an untrusted asserted
UUID compared with real current generation; assignment_revision and fencing_token
remain null BEFORE issuance, as does result_artifact_ref. Issued values are returned
only in separate actual A2 grant/phase/opaque one-use dispatch authorization. Never
write them back into the retained original outer bytes. JobUUID != experiment label,
actorUUID != quota owner/service/node; leaderKVModifyIndex != Raft term or worker
fence. Strategy null means no strategy for this operation, not a default strategy.

## Option A: content-addressed SINGLE-original commissioned profile-v2

Use SAME existing Consul L/profile-registry/<P_SHA> family/authority. No second
profile/job registry, ledger or scheduler. Actual ROOT commissioner prepares full
profile-v2 with existing cluster/realm/peer->actor/input/producer/resources/expiry
policy fields plus closed the EXACT A2 proposed profile schema pinned in A2-REFERENCE.json target_binding. Binding
contains exact outer bytes(base64), outerSHA, approved native outer schema hash,
cluster/realm/server-bound jobUUID and fixed input/source joins. Full actual profile
schema+parser/version/API are A2/ROOT successors; nested schema here is DATA ONLY.
The harness's structural profile vector is intentionally not a genuine commissioned
profile/context/issued record. It is NEVER written to Consul or passed to a broker.

Canonical preimages, with no circular edge:

1. I = exact1126B A7original raw input, SHA256(I)=c548e2... . Its payload canonical
   SHA=33d5bf... (Root local manifest reference); Meta own dataset digest is distinct.
2. T = exact Root-native outer20 canonical ASCII JSON bytes. Codec is Root sorted
   compact JSON/ensure_ascii/finite values, preserving JSON integer/float byte
   distinction; it is NOT C3 because resource_budget contains JSON numbers.
   H_T=SHA256(T). T contains NO P_SHA/H_T/native13 digest/profile selector field.
3. B contains standard canonical Base64(T), H_T and independent source/input/schema/
   cluster/realm/job bindings. Decode strict/no whitespace; reencode equality;
   decoded bytes must equal T and hash H_T. Full20 typed joins still required.
4. P = C3(full actual commissioned profile-v2 including B). NO own P_SHA, native13
   digest/bytes, native receipt/fence or principal/policy ROW BYTES that reference
   P_SHA are embedded. Existing principal_registry peer fingerprints->actor UUIDs
   and independently chosen IDs are allowed. P metadata has no JSON numbers:
   original T numeric fields survive only inside exact base64 bytes. H_P=SHA256(P).
5. N = C3(existing13): original requestUUID/key copied EXACT; actual actor/quota/
   cluster/generation/job bound; commissioned_profile_sha256=H_P;
   input_request_sha256=SHA256(I), producer_head=Stratt aed8 (NOT Meta f3c);
   resources fixed trial strings. H_N=SHA256(N). N may reference H_P; P NEVER
   references N or H_N, so graph I/T -> B -> P -> N -> native receipt is acyclic.
6. Existing command/common UUID/idempotency bindings commit full N/H_N using native
   submit schema locator19357891, DISTINCT from commissioned profile body H_P.
   No common-key preimage/domain/schema alias or hidden field dropping is allowed.

The native13 idempotency grammar excludes dot while Root direct grammar allows it.
Copy original key ONLY if both accept; otherwise MAPPING_NOT_REPRESENTABLE. Never hash,
normalize, sanitize, truncate, casefold or generate another key. A broader key
requires a separately versioned A2 schema/common-locator decision, NOT this mapping.
All20 mutations alter T/H_T, hence B/P/H_P/N/H_N. Keeping same native originalUUID/key
with any such changed intent must conflict. That fact does not authorize creating
another profile automatically on replay. No raw-field semantic equality shortcut
(e.g.3.0==3) may substitute for byte identity.

## Profile lifecycle, bounds and ACL

Exactly ONE precommissioned outerSHA, ONE original requestUUID/key and ONE bound
jobUUID per lab profile. Actor/quota/source/input/schema/resources/generation and
expiry are fixed before actual submission. Root private commissioner may CAS-create
genuine immutable profile/registration/policy only, with actual ACL default-deny;
client/worker cannot write those keys or native issued records. Principal/policy
rows can reference H_P AFTER P is hashed, not inside its preimage. No caller-selected
commissioning/profile factory callback. Existing broker constructor is server-selected.
Profile selector must equal raw P hash; actual current profile/principal/policy/
principal-session generation checks occur again in SAME native admission transaction.
A new profile is a separate explicit commissioning decision, never UNKNOWN retry.

Current broker max commissioning15min/native sessionTTL10s is NOT a new policy grant:
new profile expiry/revocation/UTC-vs-native invalidation semantics need explicit
ROOT/A2 successor ACK. No renewal/adoption/reuse is implied. Expiry does not delete
old command/receipt/tombstone/profile/debt or reset quota/resources. Keep old P/T/N/I
while needed to resolve originals/history, under current actual read rights.

Bounds reuse Grid actual C3 max16384/depth12/string16384 and its native64ops/32768
encoded-byte limit. Base64 expansion and full profile overhead must fit actual
profile bound; excessive binding => PROFILE_BINDING_TOO_LARGE, not truncation or
out-of-band caller blob. Those are encoding bounds, not workload/resource benchmarks.
Actual complete issuer plan must be rebuilt/serialized/measured for new profile;
old43/20119/etc examples are NOT inherited budget/hash proof. Trial native CPU/RSS/
output reservations are separate from preserved Target IO/row/execution limits;
stricter actual output bound remains enforced, never inferred from a reservation.

## Option B tradeoff: new native command envelope

Alternative C3 envelope includes base64(T), H_T and unchanged13 nested N referring
to an independent base commissioned profile. Envelope digest binds both once;
N/profile cannot contain that envelope digest. This supports generic requests
without per-original profile commissioning, but changes actual command codec,
profile_schema_sha256/common binding locator and possibly RPC/result identity.
It MUST get a new explicit A2/ROOT version/domain integration; cannot call the
composite digest old13 or reuse old receipts. Larger complete write payload needs
fresh budget/limits. Both options use existing Consul only. No implementation or
final selection is made here; single-job OptionA minimizes command ABI changes.

## Capture/dispatch and positive gates

Capture CURRENT actual broker evidence for exact N bytes and fixed SUBMIT_RESEARCH,
with fixed expected broker/SAME authority. Its profile raw/hash must be EXACT P;
P's T/H_T/native outer/source/schema/actor/quota/gen/job joins must ALL be checked.
Capture is NOT permission: actual A2 target transaction checks all captured native
indices/session, leader/generation and job/Assignment/attempt/resource/hold/quota
preconditions. No READ_DATA context upgrade, JSON proof, fake permit or bool lease.

| Positive phase | Required actual owner ACK/gate; today BLOCKED |
|---|---|
|Pure prepare/binding|ROOT native outer/result schema+consent decision; A2 full profile-v2/C3/locator coACK. Structural vectors alone create no profile/grant.|
|Input identity|A4/A7/ROOT approve exact engineering input/experiment label semantics. local-sha/LOCAL_FIXTURE_1 are not A4 committed manifest/registry identity. Actual registry-required mode denies without it.|
|Native admission|A2 implemented original issuer+jobowner/quota/resource/Assignment transaction; ROOT commissioned separate SUBMIT identity/profile/ACL/session/expiry. Currently actual issuer CLOSED.|
|Worker dispatch|Actual current worker session/incarnation/attempt, qualified capacity/headroom/CPU-RSS mapping/boundedIO/deadline and actual once-only A2 permit. PR51 limits/quiescence are not this qualification.|
|COMPUTED metadata|A7 exact producer I/source/descriptor/artifact schema+digest and A2 current phase CAS/fence. This is not durable artifact publication.|
|Publication|A4 actual two-independent-domain closure/protection/budgets, A2 sole native publication order/current grant and exact result intent/receipt. No same-disk shortcut.|
|COMPLETED/retrieval|A7 genuine idempotent durable existing ResultStore projection plus exact original native receipt/current read rights; Root/A6 native result schema consumer ACK. Current direct success schema must not be relabelled.|

## Closed errors and restart UNKNOWN

the EXACT A2 proposed admission-error schema pinned in A2-REFERENCE.json is NEW PROPOSED DATA, not a Root shared wire enum.
A2 closed error fields/code set are copied EXACTLY as proposed DATA; no competing
A5 wire enum is created. NOT_ATTEMPTED_THIS_CALL covers preattempt mapping/owner
gates but does NOT prove an earlier original absent. UNCERTAIN after attempted
native send keeps original T/H_T/P/H_P/N/H_N/I, request/key/job/actor/quota unchanged,
no dispatch/refund/rekey/recommission. Parsed native409 only THIS_ATTEMPT_ROLLED_BACK,
not terminal original REJECTED. execution/retry/hold-release permissions all false.
Known native commit/phase facts stay separate from error/qualification UNKNOWN;
projection pending cannot erase a known native publication commit.

Root may store exact originals in EXISTING local Journal for crash retrieval,
explicit LOCAL_ONLY, never distributed receipt. After restart reacquire actual
current READ_RESEARCH context and resolve SAME durable native original intent/common
bindings/receipts/issued identity through A2. Expired P/session must NOT be renewed
or rewritten just to read history. If no historical read ABI/current authorization
exists, remain unavailable/UNKNOWN; local Journal cannot fabricate completion.
RUNNING replay cannot mint another start permit. Disconnection is not cancel;
cancel is a separate immutable original command bound to same job/original N,
actual CANCEL_OWN_JOB owner policy and same native order. It cannot undo committed
computation/publication nor release holds without actual approved exit/release.

## Harness evidence category

Owned tests use pinned primary Root20 request/schema and A7 I bytes to check field
coverage, all20 byte binding mutations, hash domain distinctions, direct denial,
key representability, native preissue nulls, overflow and error/restart structure.
They generate untrusted structural profile/native13 vectors ONLY, no issuer/context,
Consul seed, job/worker/Meta computation, calls, permission or success receipt.
No Root production module/schema is edited. Passing these tests is PURE_CONTRACT
coverage, not TargetAdapter/native scheduler/Windows/publication acceptance.

## A2 primary proposal alignment (not shared coACK)

Reference Grid26e63a28b8cb04e986153f80369169d7e2f8854d/tree03b843222305c7d7eabb44be34b6b154da18d473.
Exact proposed native outer schema faf01152678c5b066145dcafebe92f593a641a54dac84da3ce1e1df94c0fb261,
full profile schema27b169eebb07980c729ca479cf4ab66efe8e8e99f4f0f04fda1b6878f03eb05c.
Own fixture copies are exact PRIMARY bytes; A2-REFERENCE.json pins all8. No own
alternative binding/error ABI is introduced. A2 target_binding duplicates exact
actor/generation/request/key/quota/job/input/producer joins plus full20 raw/hash/schema.
Schema validity alone cannot establish those joins or real commissioning. Base64
schema upperbound21848 is NOT the operational C3 string/profile bound16384;
actual C3 encoding must additionally refuse an oversized profile. Sample labels
NOT_COMMISSIONED/NOT_ISSUED and all fake-value STRUCTURAL DATA status remain intact.
Actual existing broker profile-v1 rejects the new profile; no issuer test runs.

Pure harness review found a missing content join: outer/binding/native actor must
also occur in full profile principal_registry. Regression first produced12pass/
1failure (ValueError not raised); added content check now refuses that vector.
This is an untrusted FORMAT-ONLY verifier correction, NOT an observed native
admission bypass or authenticated issuer. Actual peer fingerprint/current principal/
policy/session equality and immutable commissioned provenance remain native gates.
No native runtime code was changed. Tests explicitly distinguish13unique unit
cases from20 INVALID one-field sensitivity subcases; no owner counts are adopted.
