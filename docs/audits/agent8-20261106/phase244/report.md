# Phase244 compile7 SOURCE corrections and MODELED11 preparation review

Math PR110 fixture source5721987a15d20c3f9984d52eac4446704566d4b9/tree4dfced3be2ee08fa8a33cead814bb0b92bc5bdcd. External source packet only. No A8 owner-function execution/import/compile/test/model/compiler/Win32/Job/token/desktop/Node/native action. All hashing/AST inspection used A8 own stdlib DATA verifier. Actual old/candidate modeled results NOT_RUN by A8 and not predicted.

| Requirement ID | Repository | PR | Exact HEAD | Test name | Environment | Expected result | Actual result | Evidence | Status | Severity | Required correction |
|---|---|---|---|---|---|---|---|---|---|---|---|
| COMPILE7-CUSTODY | math/external controller |110 fixture|5721987 exact fixture; dff→444 external controller|Poll exception must not skip direct termination|SOURCE only|Independent poll/terminate/wait attempts|Candidate444 initializes needs_termination true; isolated poll failure retains sticky error, still direct terminate; caller wait independent|[diff](compiler-controller-correction.diff), controller-candidate.py|CLOSED scoped SOURCE|P2 proposal correction|Actual selected fault evidence separate; no whole Win32 runtime acceptance |
| COMPILE7-DIAGNOSTICS |Same|Same|Same|Expected plus unrelated compiler error|SOURCE only|Mixed/unparsed/error/warning/symbol sets denied|Candidate parses complete nonempty lines, closed S03 error code/symbol pairs, requires CS0246; mixed output UNKNOWN/DENY|Same files|CLOSED scoped SOURCE|P2 proposal correction|No compiler output observed; future expected diagnostic policy remains hypothesis |
| COMPILE7-LOG-COMPLETE |Same|Same|Same|Reliable raw stream completeness|SOURCE only|EOF/read/close/retire/write states required|Candidate requires both started/EOF/close/retire/log_written and no read/close failure/overflow/uncertainty; immutable captured bytes|Same files|CLOSED scoped SOURCE|P2 proposal correction|No actual read/write fault injection by A8 |
| A8-MODELED11-SOURCE |Same|Same|Bound olddff and new444 profiles|11 exact selected-function controls|Unexecuted SOURCE|Same controls and actual selected AST only|Full drivers/control/preflight/child/parent read; source/data hashes match; source ACK for preparation only|[verification](verification.json), [bindings](BINDINGS.json), driver sources|PASS SOURCE only; actual models NOT_RUN|Scope limitation|Root separate exact one-profile allocation; no predicted RED/GREEN or compiler permission |

Original review1 dff93058aa9c97e776c7febb3d354cbf5502da4995e92340aa383fdc65b40494 restored byte-exact; original509e source seal unchanged. Candidate444c32b8456fa1c42e1504a96e5a2882b29c3a832368671aba813b4f2d3477d2 retained at new review2 path; restoration receipt3b081 independently verified. Original source findings retained separately, not rewritten into behavioral PASS. The original seven C# input set is unchanged; no eighth definition/control or fixture fix is admitted.

Packet-index9b0ffc522bfc2426287427b15ceb5bcf6b2d6753dc004993a3d6c50e0bcd6f88, original source-sealbb7dd, BINDINGSc01e and all members independently hashed. Old modeled driver57ef8e39 and candidatea0c45a2b differ in entire raw source only by fixed PROFILE literal. Controls541991 raw unchanged,11 exact test method IDs independently extracted with AST; no discovery or altered assertions. Both actual owner source buffers are size/SHA checked and held before control source is compiled in the prospective path. Rebinding is only fixed PROFILE and HeldSource read wrappers over admitted bytes. Selected actual terminate/reader/retirement/policy AST executes only under inert Win/Kernel/Pipe doubles if separately authorized; full controller module/main, ctypes/WinDLL/compiler are not imported in that route.

Full parent and adaptations independently source-read. Seven helpers match19353016 reference LF source; parent matches after exactly two schema/scope literals. Source-segment SHA c44c54df independently confirmed (without trailing newline, same extraction convention); no owner bytes normalized or modified. Parent uses own child handle, separate sticky poll/kill/wait/readers cleanup, starts observed15s before Popen, separate5s observed cleanup with uncapped elapsed and late DENY. Backend creation/OS calls remain cooperative, not hard kernel/family/whole-wallclock proof. Unknown constructor publication remains an unqualified outcome; no hostwide process/kill claim.

Origin admission covers exact stdlib841 and fixed control module, builtin/frozen identities and fresh parent/child prefixes. Prospective child denies secondary subprocess/socket/ctypes/sqlite writes outside owned scratch and Thread.start during controls. Full transitive OS DLL/bootstrap containment is not established by raw hashes. Current841 runtime files independently size/SHA rehashed; both future old/candidate OUTs absent at capture. No modeled result or real compiler custody proof follows from source review. Original protected Math remains CONSUMED_NO_RETRY; this is not an authorization for its replay.

RELEASE_MANIFEST_STATUS: NOT_APPROVED.
NODE_INVENTORY_STATUS: NOT_ACCEPTED.
CONTRACT_STATUS: No new whole-system acceptance.
OFFLINE_TESTS: SOURCE preparation ACK only; actual MODELED11 NOT_RUN in this phase.
WINDOWS_CI: No new hosted result.
PHYSICAL_TESTS: BLOCKED.
P0_P1_P2: Three unexecuted compile-proposal P2 remarks source-corrected only; no production/native RCA closure or P0 absence assurance.
EVIDENCE: Full original/candidate controller, exact correction diff, packet/index/bindings/controls/drivers/reference and verification.json.
NEXT_ACTIONS: Root considers separate exact one-profile inert allocation; preserve all actual outcomes. Compiler would require a later distinct reviewed custody/effects decision; no automatic execution or extra input.
GO_NO_GO: NO-GO.
TAILSCALE_REMOVAL_ACCEPTANCE: BLOCKED / NO-GO.
