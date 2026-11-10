# Atomic READ broker bridge: concrete before-edit implementation card

2026-11-10. SOURCE/DESIGN ONLY. No project import/compile, broker/Grid edit, test creation/execution, native fixture, Consul/session/job call, network, GPG or new branch was performed for this card. Direction ACKs from Root/A4/A5/A6 and A8's scoped review are not exact implementation approval. All shared code remains HELD until Root/A8/affected-owner agreement to the details below.

## Frozen sources, files and ownership

Unified base HEAD `96b17905a5be923857aa1e778085eaeec6f0f27f`, tree `e868213d3fd47739c05aa1fc9f70a8d7658a1333`; broker `unified_system/gateway_research_identity.py`, blob `e10519767bad164534f99e42e5b04eb69d823d9c`, raw SHA256 `481724cd2efca312773fa4152d1c223b46ced6529d96b2d74f452cdf57932d7f`.

Grid reference HEAD `fb177d14b1e6e399bd9b66ae7cb35d3838acbd81`, tree `2cba4b0a1ee7621ef213600d6334db8e9ac7dae1`; existing assignment raw SHA256 `5b972b6d81eeaf6f2283584c5b0482552fa9bf0717a4379838900a72da791491`, coordination `3dd73d3eb3dfb576f7174a94fab05a0f87fe248ffcacccfa19786ccc74f0776b`, runtime `cfb32db73f1859d9d78b03d886372cc08584c81abd64930b5409a91edc417b64`. This is an exact cross-repo source dependency proposal, not a global support1f6 replacement or adopted production authority assembly. SOURCE-EVIDENCE.json binds raw bytes/Git blobs/module imports/constructor and static calls; no import was used to inspect them.

Preferred implementation scope to allocate EXPLICITLY before edits:

| Repository/path | Owner and proposed change |
|---|---|
| Unified unified_system/gateway_research_identity.py | Root/Integration Owner; explicit scoped A2 edit lease required. Private bridge/decoder/capture refactor only; public ABI unchanged |
| Unified tests/test_research_identity_atomic_snapshot_unit.py | proposed NEW Root/A2 controlled-backend unit lane; exact test/dependency/runtime approval required, not native tests |
| Unified docs/analysis/research-identity/atomic-read-bridge-implementation-review1.md | proposed NEW explanatory source card; Root lease required; no hidden production/native qualification |
| Grid grid/authority_assignment_v1.py, coordination.py, authority_runtime_v1.py | A2 contract owner; NO EDIT preferred. Reuse existing helper exactly |
| Existing Grid/Unified consumer/fixture/workflow/storage/scheduler/Terminan files | NO EDIT; affected owners review compatibility only |

Future implementation branch/worktree, if allocated, starts from frozen96b; do not silently implement on model8ef or newer Root/source assembly. Existing model46c and relocated successor `8ef8d9eca6196e8d3aed0aa97ff665806f88c721` / tree `29bbc301ab76ba04009084c25587190d59c2f99b`, six DATA methods and all original evidence remain separate/immutable. No additional model run is proposed.

## Actual constructor and import decision: real wrapper, no fake capability

Preferred bridge creates ONE actual `AssignmentAuthority(self._authority, self._generation)` using its ordinary constructor, with native_provider OMITTED/defaultNone. Do not use object.__new__, fake/method-shaped instances, a supplied callback/provider, a caller boolean or a fabricated capability. This actual wrapper is not a new ConsulSessionAuthority/client/election/ledger: it retains the SAME authority/client/generation references and uses that authority's existing `_request`.

Actual inspected constructor is synchronous: it stores authority; validates generation with pure `_uuid`; stores native_provider (None); optional provider shape checks are skipped; derives prefix from existing config.namespace. It contains NO await/request, client/session/lease/broker/Journal construction, file/network/DB access or authority acquisition. It does not call execute/reconcile/_leader_fence, and none is proposed. No resource lifetime is transferred by constructing it.

Exact proposed import point: after successful EXISTING broker authority/IDs/TLS/certificate/profile initialization, locally import `AssignmentAuthority`, `CapturedRecord`, `AssignmentUnavailable` from `grid.authority_assignment_v1`; instantiate the actual wrapper and store it once as private `self._identity_snapshot_source`. No new constructor argument, public factory or import-path manipulation. Missing/incompatible module fails closed using the existing ResearchIdentityUnavailable class/code NATIVE_IDENTITY_SOURCE_UNAVAILABLE; no fallback to another Grid revision, private path, `_read` loop or ambient provider.

New direct import graph: grid.authority_assignment_v1 -> stdlib base64/hashlib/json/os/re/stat/uuid/pathlib/dataclasses/urllib.parse, existing httpx, grid.authority_runtime_v1 and grid.coordination. Broker already imports httpx/runtime/coordination. Assignment module top level defines classes/functions/constants/frozensets/dataclass decorators; actual RootRegistrationCustody and its deferred Journal/OS routines are merely defined, NOT instantiated/called. Runtime and coordination module static imports/calls are retained in SOURCE-EVIDENCE.json. This inspection identifies no explicit module-top native request/file/Journal construction, but does NOT attest third-party import/DSO/installed-origin closure or guarantee all runtime import effects. Exact approved module roots/wheel/runtime origins remain an execution prerequisite. No new dependency installation is implied.

Before AND after snapshot await assert private source has exact AssignmentAuthority type, source.authority is broker._authority, source.generation equals broker._generation, source.prefix equals broker._namespace+'/runtime-v1/', source.native_provider is None. Source helper independently checks actual ConsulSessionAuthority/owned actual httpx client+AsyncHTTPTransport. No method-shaped type acceptance or callback substitution in production. Imports may use normal cached module resolution only from the qualified frozen source graph; no importlib.find_spec, sys.path insertion or environment override.

Lifetime: wrapper owns no client or session and needs no new close/finalizer. Existing Root owns the original authority/client; broker.close owns its previously issued principal sessions exactly as before. Do not close/release the authority via the wrapper, create Journal custody, auto-renew, generate a leader or recover a generation here. Closing broker latches `_closed` before lock wait as today; that latch must reject a returning read.

## Exact closed key plan and five-row conversion

For an already issued actual broker context, `_context(context)` returns existing state `(socket,fingerprint,service,session,deadline,actor,policy,quota,expiry)`. Derive keys ONLY from this issued state and existing immutable broker namespace/profile/realm:

1. self._namespace + '/commands/generation'
2. self._prefix + 'profile-registry/' + self._profile_sha
3. self._prefix + 'principals/' + state[5]
4. self._prefix + 'policies/' + state[6]
5. self._prefix + 'principal-sessions/' + state[3] + '/lock'

These are a tuple of five unique exact bounded keys. No request-selected realm/key/policy, prefix scan, hint GET, fallback lookup or extra session/info call. State IDs were issued/validated by the actual existing broker; retain explicit canonical session and UUID/key bound checks. Reject mismatched decoded actor/policy/profile/namespace, never chase a new key after snapshot.

New private proposed method: `async _read_identity_snapshot(self, state: tuple) -> tuple[ResearchNativeRecord, ...]`. It binds the actual wrapper, calls ONLY `await source._read_snapshot(keys)`, validates the same binding after await and converts its five results. Existing helper issues one get-or-empty per key in ONE consistent read-only txn and preserves exact result inventory/ACL/type checks. No second snapshot implementation/parser is copied. Actual HTTP uses PUT /v1/txn?consistent with get-or-empty verbs; require exact read-only endpoint-classifier evidence before native execution. HTTP PUT alone is not a job mutation.

Conversion contract: exact tuple length5 and actual CapturedRecord entries, key equals expected key in order, integer positive ModifyIndex<2**63 (bool invalid), raw exact bytes present and bounded by existing native codec; session string canonical when nonempty. Helper permits absence(index0/rawNone); bridge does NOT upgrade absence to an identity record: absent required row -> existing NATIVE_IDENTITY_RECORD_UNAVAILABLE. Do not fabricate an empty native record, normalize bytes or replace missing row from previous capture. Construct only existing frozen ResearchNativeRecord(key,index,raw,session) DATA, in existing order generation/profile/principal/policy/lock. A ResearchNativeRecord is not an issued capture/lease/worker permit.

Preserve helper KnownLeader true AND ResultsFilteredByACLs false; missing/extra/duplicate/reordered/ACL-omitted/ambiguous rows or malformed base64/canonical payload fail closed. Do not infer a shared index: unequal per-key ModifyIndex is valid. No max-index/client-time/ACK-as-Raft-index field added. Existing64ops/32768encoded plan bound remains; full response/timeout bound remains an independent runtime prerequisite.

## Decoder refactor: one validation implementation, no weakened session issuance

Private pure decoder signatures proposed (not public ABI):

* `_decode_profile_records(self, generation: ResearchNativeRecord, profile: ResearchNativeRecord, fingerprint: str) -> tuple[dict, str]` returns profile body and actor.
* `_decode_principal_record(self, principal: ResearchNativeRecord, *, profile: dict, actor: str, service: str) -> dict` returns principal body.
* `_decode_policy_record(self, policy: ResearchNativeRecord, *, profile: dict, principal: dict, actor: str) -> tuple[dict, float]` returns policy body and parsed minimum profile/policy expiry.
* `_decode_policy_snapshot(self, records: tuple, fingerprint: str, service: str) -> tuple[tuple, dict, dict, float]` validates exactly four ordered rows with the shared helpers and returns the existing `_policy` result shape `(records, principal, policy, expiry)`.

Pure means no await/request/audit, clock sample, mutation, client creation or capability issuance. Helpers read existing broker configuration and validate canonical record data. Time-dependent checks remain outside decoders in the existing live operation. No copied alternative policy implementation: move current checks into these helpers and use them from BOTH paths.

Existing async `_policy(fingerprint,service)` remains the preliminary-read path for `_open_session`: read generation/profile, decode profile to derive actor; read/decode principal to derive canonical policy ID; read/decode policy; sample existing `_clock`, enforce `wall < expiry <= self._wall+900`, return same four records/result. This preserves dynamic key derivation and current failure checks before any unsafe hint/path use. Do not weaken its existing exact-index transaction by replacing it with a read-only snapshot alone. Public open_session/close signatures unchanged.

`_capture_current` instead reads the closed five-row snapshot once; feeds its first four rows through `_decode_policy_snapshot`; uses the fifth row for the EXISTING lock body/session equality validation. There are no native reads inside any decoder. Scope, exact v2 original bytes and actor/policy/quota context joins remain in capture as today. A decoded policy ID different from context state rejects; no further lookup.

Preservation checklist (all required, not partial fixtures):

| Existing check | Must remain in shared validation/capture |
|---|---|
| Native encoding | exact canonical ASCII dictionary, duplicate keys/number coercion/size failures; original raw bytes retained |
| Generation | exact expected record/key/body equal current broker generation |
| Profile | exact raw hash, allowed v1/v2 closed schema, cluster/realm, NATIVE_SESSION_INVALIDATION_NOT_UTC_AT_COMMIT, bounded fingerprint registry/SHA/UUID syntax, fixed producer/input/resources, existing expiry grammar |
| Target v2 | all current target20/binding field/schema/ID/hash/base64/original/resource numeric/type checks, quota/actor/generation/producer joins; no target computation/provider call |
| Principal | exact key/closed schema, actor/service/certificate/profile/quota/policy bindings and ACTIVE, canonical quota and policyID |
| Policy | exact key/closed schema/actor/profile/policy, ACTIVE, positive decimal revision<2**63, sorted unique bounded fixed scopes, canonical expiry and current deadline bounds |
| Scope/original | actual request bytes/scope type/size, existing `_profile_request` raw binding; READ input uses original submit-intent DATA without submitting |
| Principal session lock | exact derived key/session, exact existing canonical lock body joins; no fake session/TTL/clock proof |
| Local issuer | actual issued context/capture registry, same authority/broker/socket peer, hash/scope/original, invalidation/closed/clock/expiry bounds, capacity limits |

Public ResearchIdentitySnapshot fields and records tuple/order, ResearchPrincipalContext/Capture construction restrictions, broker constructor/capture/require/close/open ABI and native schemas/scopes remain unchanged. No public optional reader/backend parameter is added. Local require_capture remains local; do not silently add a network effect or promise future currentness.

## Await, cancellation, close and errors

Capture sequencing: existing lock/capacity/type checks -> `_context(context)` before await -> derive/bind private reader -> one snapshot await -> immediately `_context(context)` and reader binding recheck BEFORE consuming records -> pure decode + exact scope/original/lock joins -> current policy bound check with existing `_clock` -> existing final `_context`/audit/clock+deadline checks -> only then existing snapshot/capture registry insertion. There must be no await between final local checks and insertion. No new capture is retained on a failed read, expired/invalidated/closed peer, audit failure or cancellation. No principal session is created/renewed/destroyed by capture.

asyncio.CancelledError/BaseException must propagate through the awaited read; no broad BaseException catch, automatic retry, second endpoint mode/fallback read or manufactured UNKNOWN success. Existing source helper/authority request failover semantics remain; no change to transport implementation. Close can latch while capture holds `_operations_lock`; post-await local check observes `_closed`. Snapshot-only cancellation has no native write outcome to reconcile; do not create Journal debt or session destroy from it. Original broker.close still handles preexisting owned sessions independently.

Exception mapping proposal, using EXISTING public classes/codes only:

| Condition | Result |
|---|---|
| Missing/incompatible bridge import/binding, coordination unavailable/no quorum, AssignmentUnavailable inventory/ACL/shape failure | ResearchIdentityUnavailable('NATIVE_IDENTITY_SOURCE_UNAVAILABLE'), fromNone; no raw native error/keys/token disclosure |
| Required record absent index0/rawNone | ResearchIdentityUnavailable('NATIVE_IDENTITY_RECORD_UNAVAILABLE'), fromNone |
| Present decoded generation/profile/principal/policy/lock/scope/original/context fails existing `_require` checks | ResearchIdentityDenied('RESEARCH_IDENTITY_DENIED') as existing policy path |
| Audit backpressure / poisoned or closed/expired local source | existing specific ResearchIdentityUnavailable/Denied behavior retained; no capture inserted |
| Unexpected noncancellation exception | existing capture wrapper ResearchIdentityUnavailable('CURRENT_IDENTITY_UNAVAILABLE'), fromNone |
| Cancellation | propagate; no capture, retry or write |

Helper decoding can reject malformed inventory before broker field validation, so some previously malformed-field denials may now become SOURCE_UNAVAILABLE. This is an explicit fail-closed classification decision for Root/A8/owners to ACK; no promise of byte-for-byte malformed-error classification equivalence. No missing/revoked/filtered identity becomes positive. No new exception enum or public structured response fields proposed.

## Targeted actual-unit proposal: controlled backend, explicitly NOT native proof

Proposed NEW test module `tests/test_research_identity_atomic_snapshot_unit.py` imports actual frozen broker + actual existing Grid wrapper/helper only in a separately approved qualified unit environment. It must NOT import native fixture modules, run broad discovery, use object.__new__ to fabricate broker/context/capture, construct a fake positive provider or bypass production type guards. No test-only path is added to production.

Concrete harness proposal requiring explicit dependency/runtime approval: create an actual ConsulSessionAuthority with isolated test config and its actual httpx AsyncClient/AsyncHTTPTransport; intercept ONLY its `_request` boundary with a closed in-memory recording backend. No socket/DNS/HTTP request is sent. Construct the actual broker normally using an in-memory test CA/server public certificate and real SSLContext (crypto/ssl CPU only, no certificate files/socket/handshake); scoped unittest patches for peer observation and virtual `_utc` DATA avoid real network and clock mutation. For monotonic DATA, replace ONLY the broker module's `time` binding with a test namespace exposing monotonic, never patch the global stdlib time.monotonic function used by asyncio/timers. Restore all patches per case. This deliberately does NOT qualify peer/TLS/clock/native identity. Existing cryptography/httpx/CPython module/DSO origins must be approved before such imports; no new download/install or ambient fallback.

Obtain any needed test context by executing actual open_session over that explicit simulated backend with bounded modeled leader/session responses and existing transaction checks; do not forge a context/capture externally. These simulated PUT/session responses are UNIT DATA, not actual native writes/grants. Reset operation log before capture, and assert actual capture builds ONE exact read-only five-key txn, no GET-loop/hint/session/job operation. The real helper decodes the backend's native-shaped rows. Dispose actual in-process client via its existing close; fake backend handles any simulated session retirement. No process, persistent Journal, worker, GPG, host clock/security policy, provider, protected Math or real Consul contact. Tests carry MOCK_BACKEND_UNIT_ONLY labels/receipts; never count as actual native principal/session acceptance.

Freeze proposed ten method IDs under `ControlledBackendBrokerUnitTests` before execution:

1. `test_mock_backend_same_authority_constructor_creates_no_native_call` — normal wrapper type/identity/generation/providerNone; zero requests/client/session/Journal creation by bridge constructor.
2. `test_mock_backend_stable_read_uses_one_five_key_snapshot_and_preserves_order` — actual capture/require succeed over explicit fake records, exact row bytes/order/unequal indices, actual request builder uses closed5 get-or-empty ops/consistent and no writes.
3. `test_mock_backend_generation_or_principal_policy_interleaving_cannot_issue_mixed_capture` — backend timeline from audited recipe; stable pre-change snapshot allowed or changed generation/revocation denied; no impossible mixed capture or fallback GETs.
4. `test_mock_backend_snapshot_inventory_acl_and_transport_fail_closed` — bounded table for absent/extra/reordered/duplicate/filtered/unknown leader/unavailable/malformed index/base64 rows; no capture registry growth.
5. `test_mock_backend_context_loss_during_snapshot_prevents_capture` — pause fake snapshot and apply existing local invalidation/close/peer-loss/virtual expiry flags; after-await rejection and no capture, without changing host clocks or native state.
6. `test_mock_backend_cancelled_snapshot_propagates_without_capture_or_retry` — cancel paused await; one attempt, cancellation propagates, no new capture/session/job requests.
7. `test_mock_backend_policy_decoder_keeps_original_schema_target_scope_and_expiry_rejections` — bounded explicit schema/hash/actor/policy/revision/scope/original/v2 numeric/expiry cases against actual refactored decoder, not source-text assertions.
8. `test_mock_backend_open_session_retains_atomic_record_and_leader_fences` — actual operation construction retains all4 check-index + leader check-session/index + check-not-exists/lock; simulated changed index rejects issuance and original simulated cleanup remains.
9. `test_mock_backend_existing_reobserve_guard_remains_required` — actual existing ResearchLabAuthority._observe over same authority/broker still performs its larger identity+leader+job snapshot and exact compare; a later changed record rejects.
10. `test_mock_backend_cached_capture_is_historical_until_explicit_reobserve` — actual local require does not native-refresh; later simulated revocation fails fresh observation; no future-grant/finalvisibility promise.

These tests are NOT written/run now, and ten is a proposed method manifest, not a passing count. TDD and exact actual-unit originals/IDs/source pre-post proof are required only after explicit implementation/unit import approval. Existing six stdlib models are independent evidence and remain untouched; no extra rerun or sum of counts implied. If this harness cannot preserve constructor/type guards without unreviewed effects, stop and amend the card; do not weaken guards or substitute a forged instance to claim acceptance.

## Compatibility, publication and alternate refactor gate

Keep existing `_open_session` commit-time exact-index/session fences and `_observe` larger snapshot/reobservation. No accepted end-to-end bypass was demonstrated by prior model. A4 publication/current scientific READ, A5 worker/resource/lease/start, A6 Control/final visibility and Agent1 LAN transport APIs/placement/storage/UI stay unchanged. One snapshot establishes native lock association/current-at-read only, never TTL UTC-at-commit, continuous revocation freshness, durable command permit or scientific payload authority. Any future mutation must fence indexes/session/generation in the SAME committing transaction; strictD4 remains DISABLED.

Production broker edit necessarily matches the native gateway workflow even if this card/test are in analysis/top-level paths. The model relocation authorization does NOT apply to a production patch. Root's prepublication exact CI/cohort/native artifact+runner prerequisite review is mandatory before any push/PR; no YAML edit/skip/mandatory test removal or bootstrap-failure containment. GPG metadata/signature verification/Windows family custody and physical lanes remain separately blocked.

Preferred reuse needs NO Grid edit. If Root/A8 reject importing/holding the actual AssignmentAuthority wrapper for dependency/ownership reasons, alternate design is a separately allocated shared primitive in existing Grid coordination.py plus a delegating existing assignment helper and Unified broker adoption. That would require explicit Grid+Unified path ownership, exact return type/exception/import contract and preserved tests before edits. Do not copy a second atomic read implementation or secretly promote a private method. No alternate signature or implementation is authorized by this card.

Decision now: CONCRETE_SOURCE_CARD_PENDING_ROOT_A8_EXACT_ACK; unit import/execution and shared broker edits HELD. Direction ACKs do not auto-approve this import bridge, error classification or mocked harness. Model8ef sixPASS remains MODEL ONLY; native READ/fullfixture/Windows physical/strictD4 remain NO-GO.
