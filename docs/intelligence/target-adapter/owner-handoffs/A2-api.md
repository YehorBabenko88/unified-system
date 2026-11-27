# TargetAdapter v1 — actual A2 API inventory, 2026-11-09

Status: API_INVENTORY_ONLY / CO_ACK_REQUIRED / PUBLIC_SUBMIT_DENY.
No Root adapter/shared contract edits, execution, scheduler call, service changes or tests performed for this inventory. Remote branch refs were read and match local clean worktrees.

## Exact sources

- Grid substrate branch feature/agent2-assignment-native-20261107 HEAD 40e9c8dc274a2746018bc1aa08d103cd0187cecc, tree a67f969d95934fe39c4206021a9aabcde6b6ccab (PR270).
- Allocated Grid docs branch feature/authority-result-publication-20261107 HEAD f7ecdc1415e8a77f6c5cf709c3da71c0139859a4, tree e5aa9ed2ad813149dc8edccafcdd9bff2271885f. Runtime Assignment/Core files remain identical to substrate; later commits are candidate/design documents.
- Unified broker branch feature/gateway-research-identity-20261107 HEAD 65169396d550989b6b9fc78d4f3a64a1c906172b, tree f67c605fb7d5530029bd0ff28cecf4c18c18737d (Draft PR53).
- grid/coordination.py SHA256 86814ec2519c272740ac8fae6fb4eae73d14ba51ccec091053ab260c7c024f73.
- grid/authority_assignment_v1.py SHA256 7d9f7c8488407b6ed60e781f75748a89c5d77cfce5925a16df583468ebd1895c.
- grid/authority_runtime_v1.py SHA256 cfb32db73f1859d9d78b03d886372cc08584c81abd64930b5409a91edc417b64.
- unified_system/gateway_research_identity.py SHA256 1e9f4bb1c7a563b3cf5e19f432f5799941448df212a2ddb9a7de9df1d99cb543.

## Implemented APIs — source signatures, not implied target grants

Existing Grid core:

    ConsulSessionAuthority(config: ConsulConfig, *, client=None, clock=time.monotonic)
    async acquire(owner)                 # actual ConsulLease or None
    async validate(lease)                # boolean current check, NOT target permission
    async renew(lease)                   # boolean, actual native session renewal
    async release(lease)                 # destroys only owned native session
    async write_control(lease, name, payload)
    async read_control(name)
    async close()

ConsulLease fields: owner, session_id, token. Token is actual leader KV ModifyIndex, NOT Raft term, job revision, worker lease epoch, resource fence or dispatch permit. Core exposes no Raft-term API. write_control performs same-native-Txn leader session+index checks with state write, but supplies NO job-owner/quota/Assignment/idempotency/cancel contract. read_control is a consistent control record read, NOT authorized job status. Never expose the arbitrary payload path as submit/admission. Actual 2/3 quorum is a property of real three-voter Consul, not these dataclasses or a caller claim.

Assignment substrate:

    AssignmentAuthority(authority, generation, *, native_provider=None)
    async execute(original_request_bytes, *, context, leader)
    async reconcile(original_request_bytes, *, context)

Both public positive methods remain CLOSED. execute raises ACTUAL_NATIVE_PROVIDER_UNAVAILABLE for missing provider, otherwise ASSIGNMENT_DOMAIN_PROFILE_NOT_APPROVED; method-shaped provider acceptance in constructor DOES NOT open execution. reconcile raises ASSIGNMENT_RECEIPT_PROFILE_NOT_APPROVED. Private _read/_leader_fence/_transaction are native primitives, not an admission endpoint. Layout helpers/data schemas do not issue grants.

Broker (actual disposable research service identity only):

    ResearchIdentityBroker(*, authority, generation, realm_id, profile_sha256,
                           server_ssl_context, server_certificate_der, audit_sink)
    async open_session(server_ssl_socket, *, leader)
    async capture_current(context, *, scope, request_bytes)
    ResearchIdentityBroker.require_capture(expected_broker, capture, *,
        expected_authority, scope, request_bytes)
    async invalidate_context(context)
    async close()

open_session returns a nonconstructible, nonserializable issuer-owned ResearchPrincipalContext only after actual mTLS/native profile/principal/policy/session checks. capture_current returns issuer-owned ResearchIdentityCapture. Fixed require_capture returns ResearchIdentitySnapshot(actor_id, service_id, quota_owner_id, session_id, policy_id, profile_sha256, records). Each ResearchNativeRecord is key/index/raw/session. Snapshot/dataclass or JSON construction is NOT authentication. Context/capture membership and same actual broker/Consul instance, fixed scope and exact bounded original bytes are mandatory. Scope is SUBMIT_RESEARCH, READ_RESEARCH or CANCEL_OWN_JOB. Native principal session is not a worker/leader lease. Profile/constructor generation and realm are server-selected, never client role claims. No native-human identity implied.

Capture is READ OBSERVATION ONLY. The eventual mutation owner must derive/validate its exact expected key set, then check all captured generation/profile/principal/policy indices and principal-session index+Session in the SAME actual target transaction with current leader and all job/resource/worker checks. Local consume does not read Consul synchronously or prove capture remains native-current. No callback, None return, reported role or direct-stand opaque scope can substitute.

## Missing target admission contract — all BLOCKED

| Operation | Missing executable contract / required boundary |
|---|---|
| Submit | No ResearchLabAuthority implementation or positive submit issuer. Need approved fixed request codec/profile registry, actual current broker capture and native identity joins, complete atomic admission builder and original-command binding. Return COMMITTED only after actual durable native evidence; ambiguous send is UNCERTAIN, never fresh identity/retry grant. |
| Job owner | Actor/service/quota derived from same commissioned broker/native rows, joined to original command and immutable job/Assignment. Client owner_id, role, profile, stand scope and echoed equality are claims only. No implemented owner-only target job API. |
| Resource/quota | No qualified reservation/debit/release issuer. Need genuine worker capacity/headroom/containment, exact quota/native ledgers, captured predecessors+CAS, atomically created hold, counters and issued Assignment. Existing/uncertain debt survives restart; no seeded issued rows or reset-to-zero. |
| Assignment | Need actual server-issued assignment/attempt/worker incarnation and same-Txn immutable binding. Current schemas and 17 candidate write values are DATA, not issued Assignment. Public execute/reconcile fail closed. |
| Lease | Need genuine current worker session+native lock tied to exact assignment/attempt/lease_id/lease_epoch, actual freshness and ownership. Native SID strict canonical UUID has no imposed version; actor/job/realm/assignment IDs retain UUIDv4. Initial issuance only; reuse/adoption/renewal/transfer need separate approved contracts. Broker principal session or core leader lease cannot substitute. |
| Fence/dispatch | Need exact compound worker/resource fence, same-Txn leader/index/session+generation and worker lease/attempt/job-current CAS checks, plus actual one-use same-owner dispatch permit. No implemented require_dispatch or worker authorization. Leader token alone is insufficient; JSON fields/stand token cannot fence a real target. |
| Status | No implemented ResearchLabAuthority.lookup/reconcile job API. Need current READ_RESEARCH plus consistent exact original/common bindings/assignment/phase receipt resolution. Known committed history may be reported under current read rights without old worker lease; no-quorum/missing/corrupt/unknown is not NOT_FOUND or permission. COMPUTED metadata is not publication or COMPLETED. |
| Cancel | No implemented native job cancel. Need own separately bound original cancel command, actual CANCEL_OWN_JOB and original-owner/job joins, current job+phase CAS in same transaction, durable cancel receipt. Ordering against dispatch/computed is native job CAS. Cancellation request does not prove child exit, kill success, refund or released hold. invalidate_context revokes a principal context, NOT job cancel. |
| Restart/recovery | No implemented job recovery/adoption. Nonserializable broker handles must be reacquired via fresh mTLS/current native records; original command UUID/C3 bytes/common idem binding/holds/receipts persist. Consistent recovery of known native state required. RUNNING replay returns observation only, no new child permit; lost delivery is execution UNKNOWN. No automatic resume/regrant/refund or clearing uncertain debt. |

Existing CoordinationCommands.submit(lease, envelope, session_context), get_command(command_id, session_context), and EventAuthority.submit(leader, intent, context) are DIFFERENT bounded command/event profiles. Their presence does not implement the above research job/worker/resource contract. Old command profile records effect_status PENDING_UNWIRED and cannot be aliased to TargetAdapter admission or scheduler PASS.

## Candidate design — names only, NOT executable APIs

ResearchLabAuthority.submit / lookup / begin_dispatch / record_computed / cancel, ResearchDispatchAuthorization / ResearchDispatchPermit and async fixed require_dispatch(expected_authority, permit, *, owned_attempt) are review2 design proposals. They are NOT defined in current grid runtime. No implementation signature for submit/lookup/cancel is claimed here. Exact target adapter request/result/error and ownership ABI still requires Root/A2/A5 co-ACK before wiring.

Review2 protocol SHA9f72ae19ca0db03cf873102379c27ed42164c5573a9173827c3bc108ab77cd90 and closed record schemas remain design evidence. Successor native lease schema SHA9bdb1084004fcc6cfb76fa0f1bce0013b6a26a9b288cbb71c82db621feb4f4d0 is format-ACK only. Full candidate plans reencoded at f7ecdc: ADMIT43ops/20119B, DISPATCH34/9295, COMPUTED35/9909, CANCEL26/10658; zero Consul calls. Every actual complete target transaction must be remeasured <=64ops/32768 encoded bytes with ALL current dependencies, never omit/split checks to fit. These samples do not qualify native issuance, worker or storage publication.

## Root independent direct stand boundary

An opaque Root-owned stand scope may bind that stand's actual local objects and journal operations. It is NOT ResearchPrincipalContext/Capture, ConsulLease, ResearchDispatchPermit or native resource grant. Local crash/idempotency journal receipts can qualify only their measured direct-stand behavior, never distributed consensus/actual scheduler/job admission PASS. Root direct stand should remain a separate explicit capability type and scope; no broker/Assignment fallback or production/public route. Actual scheduler BLOCKED, public submit DENY until separate co-ACK and native qualification. No second election or authority service.

## Evidence and remaining gates

Owner exact651 full15PASS/0skip/raw1514Unified+695Grid prepost is disposable broker evidence only. A8 phase99 independently ran ONE modified actual native test at651, not full15; phase98 full15+2 applies onlyc02. Historical expiry RED/GREEN were WIP without pre-fix primary pins; P2 static finding has current GREEN, no source-pinned historical RED. Workflow/downloader/Linux lock source review is not hosted/Linux runtime PASS. No new run performed today. Strict UTC-at-Raft-commit, actual worker qualification, two real storage failure domains, physical Windows quorum/native-human/public admission remain unqualified. GO_NO_GO: NO_GO.