# TargetAdapter v1 — independent acceptance preparation

Directive: 2026-11-09. This document is a checklist, not an implementation plan or product PASS. Exact source/PR/HEAD/tree/callable/package is unavailable; no adapter import, target invocation, fault injection or product tests executed. Existing audit history remains unchanged.

Level gates are cumulative prerequisites with independent evidence: PREPARATION → DIRECT_TARGET → SCHEDULER_INTEGRATION → AUTHENTICATED_GATEWAY → PHYSICAL. A higher-level case cannot borrow PASS from a lower level. The JSON matrix holds all requested report fields, currently null source/PR/evidence and explicit BLOCKED/NOT_RUN.

For every execution attach original command/environment, exact HEAD/tree/primary source and dependency digests, test ID/expected and actual outcome, original log/artifact URL or immutable receipt/hash, status, confirmed severity and required correction. Observer calibration must prove the measurement can detect a known positive effect. Historical/source-mixed RED is labelled as such; tests/skips/subtests/owner-vs-independent runs stay separate.

No new engine, scheduler or registry is authorized by this checklist. Actual fixed existing target/callable identity must be supplied by the source package. Prepared input, a broker read capture, an artifact hash, local staging or a rendered chart does not grant execution/publication or prove connected E2E.

## PREPARATION

Status: BLOCKED_SOURCE_NOT_AVAILABLE.

| Requirement ID | Test name | Expected result / decisive negative |
|---|---|---|
| A8-TAV1-P01 | Exact release candidate | Approved manifest identifies each involved repository/PR/exact HEAD/tree, dependency source/blob/SHA pins and original evidence index; no inferred current branch HEAD. |
| A8-TAV1-P02 | Source and callable ownership | Read complete allocated delta and exact fully qualified target/adapter/engine/verification callables. Owner ACKs identify exact source/API scope; no new engine/scheduler/registry or unapproved production edits. |
| A8-TAV1-P03 | Isolation and forbidden effects | Declare own processes, synthetic input, external scratch stores, loopback-only services if required, credentials-free environment and allowlisted IO. No office/process adoption/provider/real orders/Math rerun/security or network policy change. |
| A8-TAV1-P04 | Mandatory cases and environment | Freeze IDs, expected unique counts, OS/runtime/dependency versions, negative controls, cleanup and exact CI jobs/artifact requirements before execution; missing mandatory test/skip cannot become PASS. |
| A8-TAV1-P05 | Source/dependency evidence custody | Independently recompute primary Git BLOB OIDs/raw source and dependency pins; no shadow/untracked imports, replace refs, caches/reparse/hardlink surprises; pre/post source equality and exact source-to-process binding within declared trust boundary. |
| A8-TAV1-P06 | Contract and baseline separation | Pin prepared request/result schema, serialization, units, clocks, target identity, effect/idempotency/cancel/budget semantics and recovery plan. Existing phase81/98/99 evidence remains historical; no new target source supplied means execution BLOCKED. |

## DIRECT_TARGET

Status: NOT_RUN.

| Requirement ID | Test name | Expected result / decisive negative |
|---|---|---|
| A8-TAV1-D01 | Actual target positive control | Original prepared request invokes exact existing research target and actual computation, then independently verifies returned result. Record real callable/source/receipt identity and hand-calculated expected output; helper-only/fake engine/no-call path cannot pass. |
| A8-TAV1-D02 | Prepared bytes and no authority upgrade | Retain original request bytes/hash and typed joins; payload role/authorized/verified/native/publication flags, certificate/session JSON or prepared status cannot confer execution authority. |
| A8-TAV1-D03 | Independent result verification | Validate actual output schema/closed fields, byte counts, digest, original request binding, source pins and required dependency closure. Corrupt each binding independently; refuse whole result without cached/fabricated PASS or partial promotion. |
| A8-TAV1-D04 | Units precision and clocks | Declared units, scale, integer/decimal bounds, finite values, event/knowledge/decision/calculation clocks and synthetic/PIT/source limitations match contract. No silent float conversion, unit relabeling or invented financial profile/PnL. |
| A8-TAV1-D05 | No external IO or hidden effects | Observe actual target invocation with independently calibrated file/network/process/order effect monitors; only declared dependencies and own scratch allowed. Preserve positive observer calibration. Disable provider/order endpoints and prove no attempts, including error/cancel paths. |
| A8-TAV1-D06 | Injection and closed input | Reject unknown/duplicate fields, object subclasses/callback providers, command/module/path/URL/SQL selectors and schema/profile substitutions before unsafe protocol/import/IO. Data is never shell code or a dynamic authority/engine selector. |
| A8-TAV1-D07 | Determinism and direct retry boundary | Repeat identical original request and verify declared byte/result determinism; changed identity/request conflicts refuse where contract promises idempotency. Pure recomputation is not scheduler exactly-once or durable replay proof. |
| A8-TAV1-D08 | Crash and UNKNOWN outcome | Inject failure only in reviewed own test process at declared boundaries (before target, after computation, during verification/retention). Retain original error/partial evidence; uncertain effects remain UNKNOWN, no success, auto rerun, fabricated receipt or budget refund. |
| A8-TAV1-D09 | Input and output budgets | Exercise exact boundary and above-bound cases for all request/dependency/result sizes, rows/depth/counts and retained output; preflight before parsing/hashing where promised; actual target output tested, not stubbed. Reject whole output, no truncation disguised as valid. |
| A8-TAV1-D10 | Time CPU memory scope | Measure bounded own invocation and cleanup. Test contractual deadline/capacity behavior using reviewed isolated processes only; distinguish cooperative timeout from hard preemption, native CPU-rate from reserved millicores and committed memory from RSS. Unknown limits stay unqualified. |
| A8-TAV1-D11 | Cancel before execution | Cancellation before admission/computation produces no target effect/result/publication, with calibrated call/effect observations; exact cancellation type/ownership verified, no foreign awaitable/coroutine close/cancel. |
| A8-TAV1-D12 | Cancel during and after computation | Exercise actual computation cancellation/discard at declared checkpoints and before result retention/return; no late success or unauthorized cleanup/refund. Record cooperative vs native termination limits; do not invent a worker permit/provider. |
| A8-TAV1-D13 | Result staging and retention separation | If actual storage is in declared direct contract, verify exact staged bytes/reopen/collision/corruption behavior in own SQLite/ObjectStore and all publication prerequisites. Otherwise record storage NOT_RUN; local descriptor/hash stage is not published artifact or authenticated read. |
| A8-TAV1-D14 | Failure cleanup and evidence accuracy | Retain body error before cleanup, separate secondary cleanup failures, wait only own processes and close own handles/stores. No source mutation/extras; no tests silently deselected/skipped. Evidence includes executed command, environment, exact head/tree, unique IDs, stdout/stderr and checksums. |

## SCHEDULER_INTEGRATION

Status: NOT_RUN.

| Requirement ID | Test name | Expected result / decisive negative |
|---|---|---|
| A8-TAV1-S01 | Existing scheduler actual dispatch | Existing scheduler calls the independently pinned direct target through admitted existing path; no new parallel dispatcher/registry/engine. Actual dispatch and result verification observed; direct-only tests do not close this case. |
| A8-TAV1-S02 | Actual permit and same authority | Use actual admitted one-use dispatch permit, expected issuer/authority and owned attempt with original request/units/profile bindings. Fake providers/method-shaped objects/read captures/None returns cannot grant dispatch. |
| A8-TAV1-S03 | Native fencing at target commit | Current generation/leader/principal/policy/native session/assignment checks required by actual contract join SAME actual committing transaction. Stale worker, session loss, revocation, old generation and split authority refuse effects; local snapshot alone insufficient. |
| A8-TAV1-S04 | Idempotency and concurrent attempts | Actual same-intent duplicate/reconnect/restart does not create second admitted effect/launch; conflicting bytes and concurrent attempts refuse/fence. Retain actual durable outcome evidence, distinguish execution attempts from committed effects. |
| A8-TAV1-S05 | Crash recovery UNKNOWN | Reviewed own coordinator/worker loss at commit/return boundaries retains UNKNOWN until authoritative reconciliation; restart does not auto-launch or reclassify success. No quota release/refund or second publication on uncertain quiescence. |
| A8-TAV1-S06 | Budgets cancel and schedules | Actual admission/reservation/commit/cancel uses approved existing budget owner and node schedule; stale cancellation and resource overload fail closed. No unsupported CPU/RSS capacity assumption or unproven refund. |
| A8-TAV1-S07 | Existing registry and result recovery | Actual existing result store/publication receipt/registry agree on same request/revision/attempt; corruption, replica recovery and backup/restore use own synthetic stores if authorized. No new ledger or promotion of local unverified stage. |

## AUTHENTICATED_GATEWAY

Status: NOT_RUN.

| Requirement ID | Test name | Expected result / decisive negative |
|---|---|---|
| A8-TAV1-A01 | Actual peer and operator authentication | Real configured transport authenticates peer/operator under exact commissioned source and expected endpoint; negative wrong CA/SAN/EKU/pin/unregistered principal and expired session. Synthetic service certificate is not Windows human identity or operator RBAC proof. |
| A8-TAV1-A02 | Current RBAC and request binding | Actual current principal/policy/session/scope and exact bounded original bytes reach same admitted scheduler/target authority. Unauthorized commands and READ-to-SUBMIT upgrades deny; no JSON role or local broker capture as dispatch permission. |
| A8-TAV1-A03 | Expiry revocation and commit boundary | Real elapsed expiry, policy shortening/revocation, native session destroy, clock uncertainty and reconnect checked in required transport/target phases. Local UTC check is not UTC-at-Raft-commit; unimplemented strict commit expiry stays BLOCKED. |
| A8-TAV1-A04 | One request to verified actual result | Actual authenticated request -> existing scheduler/target -> computation -> independently verified retained result -> authorized response. Observe all real boundaries and exact joins; assembling offline receipts is not connected E2E. |
| A8-TAV1-A05 | Disclosure injection duplicate and stale response | Unauthorized metadata/artifact reads and changed context/URL/path/module/commands deny before protected IO; actual duplicate/reconnect/idempotency and concurrent UI sessions cannot expose stale or foreign result. Calibrate zero-IO observers with positive controls. |
| A8-TAV1-A06 | Audit and outage behavior | Actual required durable audit backpressure/corruption, native no-quorum/authority loss and coordinator restart fail closed without result leak or silent repair. Memory audit events alone do not prove durable consensus audit. |
| A8-TAV1-A07 | Hosted Windows and cross-platform CI | Exact HEAD mandatory jobs on all approved Windows/runtime and other required OS matrix finish terminal PASS with original jobs/logs/artifacts and skip inventory. Queued jobs, owner local PASS and alternative runtime are not hosted/pinned matrix PASS. |

## PHYSICAL

Status: BLOCKED_NOT_AUTHORIZED.

| Requirement ID | Test name | Expected result / decisive negative |
|---|---|---|
| A8-TAV1-H01 | Approved inventory and physical authorization | Approved exact release manifest/node inventory/dependencies and explicit physical test authorization for named nodes/cases; real deployment/merge and destructive fault injection require separate authorization. Current office fault injection remains BLOCKED. |
| A8-TAV1-H02 | LAN and node operation | After separate authorization, independently prove actual LAN transport/peer authentication/Terminan relocation and concurrent sessions/node schedules on all required nodes, with exact release and original evidence; loopback stand does not prove LAN. |
| A8-TAV1-H03 | Physical recovery and integrity | After separate authorization, actual failover/fencing/restart/worker loss/storage/replication/backup gaps/reconnect/update-rollback/safe uninstall acceptance on named nodes; synthetic offline models do not transfer PASS. |
| A8-TAV1-H04 | Tailscale removal gate and access recovery | Remain BLOCKED unless actual LAN/consensus/replication/Terminan-all-nodes/failover/restart recovery and tested independent access restoration all proved. Even GO does not authorize automatic Tailscale removal or network/security changes. |

## Evidence handoff and stop conditions

Integration Owner supplies one original index binding approved exact candidate(s), PR/head/tree/source blobs, fully qualified actual callable/ABI and dependencies, units/serialization/clocks, declared budgets/cancel/idempotency/recovery rules, owner ACKs and mandatory CI IDs. A8 first reviews sources for forbidden effects, then prepares independent probes in its owned paths. No execution while the source package is missing.

Any unclosed P0 is NO-GO. Missing source/contract/mandatory test/evidence is BLOCKED or NOT_RUN, never PASS. A required skip blocks that acceptance requirement. Findings severity is assigned only after evidence/reproduction; potential checklist risks do not create new confirmed P0/P1/P2 findings. No automatic merge, deployment, destructive cleanup, provider/order call, office fault, network/security/Tailscale change or protected Math rerun.

RELEASE_MANIFEST_STATUS: NEW_TARGET_PACKAGE_NOT_SUPPLIED.
NODE_INVENTORY_STATUS: NOT_NEWLY_ADMITTED.
CONTRACT_STATUS: NEW_TARGET_API_AND_EXACT_SOURCE_PENDING.
OFFLINE_TESTS: NOT_RUN_PREPARATION_ONLY.
WINDOWS_CI: NOT_RUN_NEW_TARGET_PACKAGE_UNAVAILABLE.
PHYSICAL_TESTS: BLOCKED.
P0_P1_P2: prior confirmed open6P1/3P2 preserved; not re-audited or closed by checklist.
EVIDENCE: this dated directive and preparation JSON; no product execution evidence.
NEXT_ACTIONS: Root supplies exact source and original index; A8 source-first review then independent level-specific execution.
GO_NO_GO: NO-GO. TAILSCALE_REMOVAL_ACCEPTANCE: BLOCKED/NO-GO.
