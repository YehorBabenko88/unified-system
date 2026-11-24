# A8 fresh PR32 metadata hold and draining acceptance

Requirement ID: CONTROL_MUX_SUB_CLOSE_HOLD_ONLY.
Repository: unified-system; Draft PR https://github.com/YehorBabenko88/unified-system/pull/32.
Exact HEAD5fd0ccbd28c79fb5ff040ecb1030462ac4baef35; treeac734aade255b4b729e997239c215a2d936c4c70. Grid58cfe0f51bc05bb0ee2ed09368a9b64679358c63.
Environment: independent no-hardlink clone, Python3.12.10 hash-locked environment, pinned Consul1.22.2 binary and separate owned loopback three-voter/BoltDB processes, synthetic identities/data. Consul fixture and dependency lock raw unchanged from prior pin; results freshly executed, no prior ACK transfer.

Expected:18mandatory unit IDs,28real HTTP/Grid/Consul event IDs,8source negatives,0skip,665primary/672Grid raw before/after and owned cleanup. Actual: PASS all counts and cleanup. Original stdout/stderr, source-bound.json, real-consul.json/log and source-guard-controls.json/log retained. Supplemental GET24 automatically executed by runner is MODEL_MATCH_ONLY_NOT_ENDPOINT_OR_AUTHORITY, not a GET endpoint/schema/domain ACK.

Additional independent actual stand: original tracked test script compiled in memory with two extra A8 assertion blocks, product/test source files untouched. Fresh three Consul voters execute28original events plus2additional cases (30total, not58unique). Actual consistent reads verify subscription ledger/metadata/snapshot WAIT_SOURCE, body_sha256/cursor/view_ref all null; valid DATASET prepare returns UNAVAILABLE and entire private KV namespace retains exact original records/ModifyIndices. Both raw source sets unchanged and all owned processes stopped. Evidence actual-supplement.json, supplement-source-verification.json and original supplement logs; reproduction review_mux5_actual_supplement.py.

Observed boundaries: initial SUB201 durable actual Consul reservation is store-level; real HTTP SUB exercise replays historical201 without reactivation. CLOSE actual202 and HTTP replay retain DRAINING/original immutable receipt and connection/subscription obligations. Lost subscription preparation followed by close cannot reactivate; historical SUB201 is history only. New generation cannot reuse old parent; no-quorum UNKNOWN and real stale-leader txn denial preserved. ACK without admitted source returns503/no original intent; DATASET unavailable. No snapshot producer/barrier, actual LIVE delivery, containment/release/reuse or worker cancellation qualified.

Default composition remains503 without native provider. Native admission in stand is explicitly synthetic; no kernel identity/RBAC/session-expiration/fleet security qualification. Local Windows execution is not mandatory Windows CI matrix or Home qualification. No real orders, office probes/faults, service/OS/security policy/Firewall/ESET/Tailscale/provider changes.

CI run42350238072/attempt1 exact5fd independently read: queued/conclusion null (ci-run.original.json), NOT_PASS. No artifact acceptance claimed. Owner evidence file rawSHA8a001c2146845b59673cd6a710a5e70ea24ec88d93273278d23b95c713060ab3 recorded for correlation only; owner counts are not our execution evidence.

Status: PASS_ISOLATED_METADATA_HOLD_ONLY. Severity: existing P1 integrated native authentication/runtime/release acceptance gaps remain open, no new defect identified in bounded slice. Required correction: qualified actual native admission, producer/barrier/containment and coherent final composition plus independent CI artifacts before broader claims. Overall NO-GO;6P1/3P2 unchanged; PHYSICAL_ACCEPTANCE and TAILSCALE_REMOVAL_ACCEPTANCE BLOCKED.
