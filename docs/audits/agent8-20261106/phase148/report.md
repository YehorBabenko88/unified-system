# F35 successor: bounded exact source-only review

Unified Draft PR69 exact HEAD `e203c0bbeaa176a843a7d80b2eadfefe8fce7385`, tree `7ca3b471eb7ee2411eb83da68f8e068ee42c803c`. Independent original GitHub metadata, Git objects and all1668 raw primary files/no extras verified in an own clean clone. Only bootstrap.py, test_bootstrap_contract.py and source-review document differ from9f. No helper/project import, test/fixture, actual subprocess frame reproduction, native Job API, target, Node/SDK/browser execution by A8.

| Requirement ID | Repository / PR / exact HEAD | Test / Environment | Expected | Actual / Status | Evidence | Severity / Required correction |
|---|---|---|---|---|---|---|
| A8-HEAD-148 | unified-system / PR69 /e203 above | Exact metadata/tree/raw primary inventory / own clone | Immutable source binding | PASS_SOURCE_BYTES:1668/no extras/three changed paths | [metadata](GitHub-PR69.original-metadata.json), [AST and raw map](source-verification.json) | No mismatch |
| A8-F35 | Same | Wrapper/scope/audit composition versus reviewed CPython representation / static source only | Admit only exact native frame of currently prevalidated fixed source Git call | SOURCE_CORRECTION_ACK; runtime qualification NOT_RUN_BY_A8 | [exact diff](exact-source-diff.patch), same AST | P2 source corrected/runtime pending; no execution grant |
| A8-NEGATIVE-FRAMES | Same test source | Windows/POSIX positive and reject cases / inspected only | Canonical frame passes; wrong scope/extra arg/exe/platform shape denies | NOT_RUN_BY_A8; Root106/RED not accepted as own execution | Exact diff | No actual native subprocess/Job coverage claimed |
| A8-PACKAGE-E | New package not supplied | Bind actual new immutable assembly/invocation/isolation | Reviewed source incorporated with exact external manifest | BLOCKED_PENDING_PACKAGE | This report | No hotpatch d; no automatic retry |

The unchanged source_git_argv validator first requires the fixed six-argument Git show shape, admitted Stratt/Meta roots and bounded object/path pattern. A8 compared its AST to9f: unchanged. The actual pinned_source_popen wrapper rejects positional overrides/executable/shell, then calls that validator. It denies an already-active nested scope, sets the resulting selected argv as an immutable tuple in threading.local immediately around the original native_popen call, and clears it in finally on success or failure. No scope is shared with other Python threads. That original call is the point where CPython emits the audit event.

validate_source_git_audit requires an active selected list/tuple of length6 with fixed first executable and exact actual executable equality. On Windows it requires type(argv) is str and exact equality to subprocess.list2cmdline(selected); POSIX requires a vector exactly equal to selected, unsupported platforms reject. It never parses or executes a caller command string, broadens source roots, changes source algorithm, enables shell or admits arbitrary executable arguments. The composed wrapper establishes selected provenance; the helper alone is not an authority issuer and does not independently prove that an arbitrary supplied tuple was previously validated. This is a scoped restriction for trusted pinned Python code, not hostile in-process Python isolation or an OS capability boundary.

The audit callback retrieves only the current thread's scope and reports fixed SOURCE_GIT_AUDIT_DENIED on rejection. A fixed DIRECT_TARGET_COMPLETION_UNAVAILABLE marker precedes the existing strict completion failure. No runtime argv/environment/credential text is printed by these additions. Existing network/write restrictions, stand allocation after GO, identity/member/readback evidence, F32 elapsed/deadline and strict workload failure checks remain unchanged. launcher/supervisor/package/assembly/materialize/export and target adapter are byte-identical to9f.

The new regression source tests canonical Windows string and exact POSIX vector, then extra argument, foreign executable, no scope and platform-shape mismatch. A8 did not run it. It does not exercise an actual Windows launch, wrapper-thread reentry or finally cleanup; no such coverage is inferred from its name. Root106 local pure qualification/RED and exact follow-up artifacts were not independently authenticated here. No new high-confidence actionable defect was found in the bounded three-file diff.

Source correction matches the concrete F35 representation defect confirmed in phase147's pinned CPython source. It does not retroactively add a missing audit event/precise exception to d's generic RuntimeError/UNKNOWN journal. Original c/d remain failed evidence and unchanged; phase147 F33/F34 scoped fix qualification via actual Root originals is preserved without converting either workload to PASS. No new package e, invocation or fresh readiness is accepted from this source review.

Exact diff retains original Git context whitespace; only the raw patch is excluded from formatting checks if those literal blank context lines trigger them. Hash/raw-primary verification includes it.

RELEASE_MANIFEST_STATUS: e actual immutable manifest/externalSHA/invocation pending; no release-wide approval.
NODE_INVENTORY_STATUS: no new A8 host/ACL/token/Job query.
CONTRACT_STATUS: F35 SOURCE_CORRECTION_ACK at e203 only; independent runtime qualification pending.
OFFLINE_TESTS: independent static/source-byte checks only; no helper/frame/test/fixture replay.
WINDOWS_CI: Root106 not A8/mandatory hosted acceptance; F26 unchanged.
PHYSICAL_TESTS: no A8 application/native/SDK/browser calls; c/d FAIL preserved, full physical acceptance/fault injection BLOCKED.
P0_P1_P2:7 open P1 /8 P2 unchanged; F35 source corrected/runtime pending, F31/F32 pending; absence of P0 not proven.
EVIDENCE: exact original metadata, all1668 raw primary hashes, three-file diff/AST and own reproducible audit script.
NEXT_ACTIONS: owner retains qualification originals and supplies actual immutable e/externalmanifest/invocation/readiness for separate review; no automatic repeat or execution admission follows.
GO_NO_GO: overall NO-GO. TAILSCALE_REMOVAL_ACCEPTANCE: BLOCKED.
