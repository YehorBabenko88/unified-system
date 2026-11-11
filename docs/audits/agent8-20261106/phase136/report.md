# PR280 source/preparation safety review: two blockers

Exact Grid Draft PR280 HEAD `49406ab9b2349abcf9524a7bc4aa4dc0e0cf0213`, tree `03439c7a0ef4ace77d0f10364f34da488af4cefd`; module `c606b70a4cbe71011659b522eb5ac7f06e149990573533361017c6d12fcde386`, Core3dd unchanged. Current Draft HEAD independently confirmed by GitHub connector. A8 performed SOURCE/PREPARATION review only, with zero product imports, runtime tests, Consul fixtures or native RPCs. Owner18 is not accepted as A8 execution.

| Requirement ID | Repository / PR / exact HEAD | Verification | Environment | Expected | Actual / status | Evidence | Severity / correction |
|---|---|---|---|---|---|---|---|
| A8-F29 | Grid PR280 /49406ab above | Prepared transaction result count versus pinned Consul1.22.2 server source | Static client AST/source plus official pinned server code | Operation-aware successful result shape | FAIL_SOURCE: prepared sender requires7 Results; actual server semantics yield5 for this7-op plan | [Static review](static-review.json), [upstream/source index](pinned-upstream-source-index.json) | P2 pre-activation blocker, correct native result grammar before opening gate |
| A8-F30 | Same source | Exact native session LockDelay type check | Static source and Python boolean equality semantics | Only integer0 satisfies policy | FAIL_SOURCE: false passes ==0; JSON parser preserves bool | Same static review/source line785 | P2 pre-activation blocker, require exact int plus0 and typed policy negative regression |
| A8-PREPARATION-GATE | Same source | Both public execution method ASTs and private sender/call sites | No project code imported/executed | Public APIs always stop before append/RPC | SOURCE_GATE_CONFIRMED_CLOSED; both raise fixed preparation error after read-only local validation | [Static review](static-review.json), [primary maps](static-primary-binding.json), [original PR metadata](GitHub-PR280.original-metadata.json) | Does not authorize private routines or prepared native harness execution |

F29: the plan includes generation/leader checks, two check-not-exists operations, CAS and lock. In [pinned Consul1.22.2 state source](https://github.com/hashicorp/consul/blob/v1.22.2/agent/consul/state/txn.go#L97), successful absence checks produce no result and the dispatcher concatenates results without placeholders. Thus this plan yields five entries. The client's equality-to-seven rejects a valid200 before _known_commit becomes true; a real commit would be classified UNKNOWN. This is a source-derived consequence, not an observed native commit or response. The [official transaction response description](https://developer.hashicorp.com/consul/api-docs/txn#sample-response) also describes per-operation result variability. Do not fix by inventing seven placeholder results or weakening all checks to any list; require operation-aware typed result validation.

F30 independently corroborates Root's preliminary typing concern. The parser rejects float/constants but preserves JSON booleans. _session_policy_matches compares LockDelay with0 without an exact int guard; false therefore satisfies that comparison if the other fields match. This has not been exercised against a real server or by invoking the private method. It is a future response-classification defect, not actual issuance, unsafe worker permission or historical malformed Consul evidence.

Six paths changed. All41 existing top-level/method definitions remain AST-equal to2f; Core and frozen intent/record/custody schemas are not changed in the diff.824 Grid+1519 support primary files matched Git raw bytes, with no extras. One private stream call site and durable begin_rpc before it were reviewed, along with fixed endpoint/path selection, raw-body bounds, typed original/SID joins and no mutation retry/rollback after UNKNOWN. Their actual network/custody/ACL/quorum behavior remains unqualified. Public methods have no environment/boolean/JSON gate switch and cannot reach that prepared sender in this exact source. Private routines remain prohibited from execution under this request.

No native harness, local18 suite, constructor, private parser/predicate, sender or public API was executed by A8. No session/registration/job writes or office/provider/network changes occurred. Owner18/partialRED/other component25/26/21/145/Direct22 claims were not independently authenticated or transferred. Root's separately reported physical development preparation is outside this source review; A8 has not inspected that attachment or granted physical execution. Previous physical/production/native-positive gates are unchanged.

RELEASE_MANIFEST_STATUS: gated preparation candidate only; no source adoption into RootPR68.
NODE_INVENTORY_STATUS: not requalified.
CONTRACT_STATUS: two source blockers; final sender/API/Root-A5 commissioning ACK and execution release remain required.
OFFLINE_TESTS: static source review only, runtime NOT_RUN.
WINDOWS_CI: hosted NOT_RUN here; F26 remains open.
PHYSICAL_TESTS: BLOCKED in A8 acceptance.
P0_P1_P2: 7 open P1 /5 P2. F29/F30 are preparation blockers, not deployed vulnerabilities or runtime failures. Absence of P0 not proven.
EVIDENCE: exact source/AST maps, original PR metadata and pinned upstream references above.
NEXT_ACTIONS: A2 separate explicit correction; keep both public gates closed. Review corrected exact source and response grammar before any separately authorized native acceptance.
GO_NO_GO: NO-GO; TAILSCALE_REMOVAL BLOCKED.
