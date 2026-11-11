# Native output-cap assertion: source-only test preparation

Base bfa3b24d8f209d5e91acfa64819d3ebed4967af7, tree
0145968d0492f0a87d3e1a7e1eecc0b34a0c4a98. Branch
feature/native-output-cap-assertion-20261110 uses a separate managed worktree.
Only this new document and tests/test_native_output_cap_assertion.py are added.
No helper, existing cap catch, production executor, environment, workflow,
component inventory, timeout or skip rule changes in this preparation.

## Confirmed defect and chosen approach

At exact96 tests/test_installation_service.py:247, catch {$limited=$true}
accepts ANY exception from the large-output Run call. A child/decode/launch/
drain/deadline failure can claim UNICODE_AND_OUTPUT_BOUND_VERIFIED. This is a
confirmed static false-positive defect, not the cause of the earlier Windows
FIRST_MEMBER_BEGIN/COMPILE_BEGIN/SAFE_LOOKUP_BEGIN stalls. No phase RCA fix is
claimed, and no previous failure is relabeled.

Use stock exception inputs against the eventual actual shared PowerShell
classifier. A Python mirror/source-string assertion would not exercise that
classifier. Extracting and executing the old catch with AST surgery could
demonstrate its behavior, but adds an unneeded execution seam; it is not part of
this proposal. Initial missing-helper RED is explicitly a NEW FEATURE RED.
It is not an observed old-catch behavior RED and cannot be reported as one.

## Frozen eventual helper contract (not implemented)

File: tests/native_output_cap_assertion.ps1, test-only, no top-level output/effect.
API: Test-NativeOutputCapException -ExceptionObject <object>.
Return exactly ONE System.Boolean on the success stream, with no other output.
The existing test catch will eventually call this same function on $_.Exception
and rethrow on false; that edit remains HELD until Root reviews actual RED.

Closed accepted graph:

- Exact System.InvalidOperationException leaf, ordinal Message equal to
  CHILD_OUTPUT_LIMIT, InnerException null.
- Exact System.AggregateException wrapper, nonempty InnerExceptions; inspect
  that collection rather than counting its aliasing InnerException twice.
- Exact System.Management.Automation.MethodInvocationException and exact
  System.Reflection.TargetInvocationException wrappers, one non-null inner.
- Every terminal leaf must be the exact cap leaf. At most 8 levels including
  root/leaf, 16 total nodes, and 1024 message characters per node. No repeated
  object identity or cycle. Unknown types/shapes, empty aggregate, non-leaf cap,
  mixed leaves, deadline/drain/launch errors, oversized messages and excess
  depth/width return false. No truthy arrays, strings or object records qualify.

These wrapper shapes are a deliberately closed proposed test contract, not a
claim that every hosted PowerShell/.NET wrapper graph has been sampled. If the
actual later exception shape differs, fail closed and review the contract.

## Frozen regression inventory and effects

One explicit Python unittest method, with stable module/class identity:
native_output_cap_assertion_controls.NativeOutputCapAssertionControls.test_actual_shared_classifier_stock_exception_matrix.
It checks all 24 fixed subcase IDs below, with seven accepts and seventeen rejects:

1. accept_leaf
2. accept_aggregate_single
3. accept_aggregate_all_cap
4. accept_method_aggregate
5. accept_target_method_aggregate
6. accept_max_depth
7. accept_max_nodes
8. reject_null
9. reject_truthy_nonexception
10. reject_deadline
11. reject_drain_deadline
12. reject_launch_failure
13. reject_unrelated
14. reject_wrong_case
15. reject_cap_prefix
16. reject_unknown_wrapper
17. reject_nonleaf_cap
18. reject_empty_aggregate
19. reject_mixed_aggregate
20. reject_nested_mixed
21. reject_cycle
22. reject_depth
23. reject_nodes
24. reject_oversized_message

make_suite defines the TestCase locally only for the explicit entrypoint. Plain
unittest discovery imports no project module and discovers zero NEW cases here;
it does not skip or remove any old case. These separate Windows-only controls
are not silently added to Linux full discovery. No workflow/discovery mask is
edited. Root must accept this explicit-control placement before execution.

If the helper is missing, the one Python test fails its first assertion
NATIVE_OUTPUT_CAP_HELPER_MISSING before tool qualification or any child launch.
No 24-case behavior result is claimed. Once separately implemented, the same
test runs ONE fixed Windows PowerShell process for the entire actual classifier
matrix; Python parses its 24 ordered unique records and requires actual bool
results. No Python classifier logic or copied production cap algorithm exists.

The fixed PowerShell command constructs managed stock Exceptions only. One
owned TargetInvocationException has its private Exception._innerException field
rewired by narrow managed reflection to make a genuine cycle. A missing field
or constructor is SETUP failure, never intended product RED. This seam is
explicitly proposed for review, not yet approved/executed. No Add-Type/C# compile,
Run method, service, ACL, registry, socket, project import or grandchild exists
in the command. The helper will be dot-sourced from its sealed absolute path.
Only static case IDs and TRUE/FALSE/NOT_BOOL are emitted; raw exceptions,
messages, source, environment values and child stderr are not relayed.

## Bounded runner proposal: not approved or executed

Root first seals exact source/tree/full raw inventories and the test/doc bytes,
checks a clean source clone, actual runtime dependency closure, and fixed tool
identities. Python is the already reviewed CPython3.12.10 -I -S -B. PowerShell is
explicitly C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe, no PATH,
fallback/version probe. Ordinary ancestors/reparse checks and a bounded raw hash
precede launch; servicing links on this OS leaf retain existing nlink>=1 policy.
Root's external receipt must pin actual tool bytes; the test alone is not tool
or source admission. No source code is installed or downloaded.

Proposed single invocation AFTER Root approval:

    <fixed-reviewed-python> -I -S -B tests/test_native_output_cap_assertion.py --allocated-pure-powershell

Outer Root watchdog: 15 seconds WHOLE including setup/cleanup, bounded output
256KiB, fixed minimal Python environment, all evidence outside source. Missing
helper stage launches zero PowerShell children. Later classifier stage allows
one direct fixed PowerShell child with -NoProfile -NonInteractive -EncodedCommand,
no shell, inherited module paths or arbitrary cwd. Test uses its explicit
minimal environment/system module path and project-root cwd. It owns file-backed
stdout/stderr, polls 8 seconds, caps stdout32768/stderr8192 bytes, kills and waits
up to2 seconds on error. Root must qualify direct-child custody and ensure no
remaining processes/threads before accepting results. This is cooperative unit
ownership, not an OS security sandbox. Any uncertainty fails; no automatic retry.

Keep the existing native fixture's 15/30-second fatal bounds and no-skip rules.
No full native test, actual C# child-output workload or Windows phase RCA
qualification follows from this stock-exception classification unit.

## Separate approval stages

- [x] Read exact old defect and prepare only the two allocated new sources.
- [ ] Root source/effects/API/inventory review, then ONE missing-helper RED.
- [ ] Preserve original RED; review that it is missing feature, not setup noise.
- [ ] New lease for shared helper and existing cap catch, no production changes.
- [ ] Review exact helper/catch and separately allocate ONE 24-subcase GREEN.
- [ ] Later separately allocated actual cap workload validates real wrapper
  classification; retain any unrecognized graph as failure, never broaden silently.

No imports, tests, PowerShell, C# compilation, subprocess fixture, native calls,
socket, source check/compile, helper implementation or cap-catch edit was run by
the source author. No RED, GREEN, Windows fixture PASS, runtime/native admission,
protected Math single-use or production authorization is claimed.

## Source review correction: unconditional held-child retirement

Root identified a runner defect before execution: the first monotonic call after
Popen preceded try/finally, and a poll exception in finally could bypass kill and
wait. Original test SHA25659dac2ed9518048eed74177a30470ebf22802230a06311e4224f8bae9e17ba75
and document SHA2562a34af28912741be816f8e67abd8610148f0a4f0015530390e5d3dba6aa103c2
are retained byte-for-byte outside source in
C:/Users/LS-5/.codex/native-output-cap-source-review2-20261110.

The revised proposal starts try immediately after Popen. Monotonic/output/poll
failures therefore enter unconditional retirement. Cleanup records poll failure
as uncertain, still attempts kill using the owned Popen handle when exit is
unconfirmed, and attempts wait even if poll or kill raises. A failed/invalid wait
or any cleanup uncertainty raises the fixed PURE_PS_CLEANUP_UNCERTAIN assertion;
it cannot produce GREEN. Existing8s/2s/outer15s bounds and case inventory remain.
This correction is source-reviewed only, not a process-double or actual child
result. No imports, tests, PowerShell, helper or existing catch edits occurred.

## Implementation source successor — no classifier or native execution

Root MCI118 consumed a separate, fresh prerequisite packet and observed the one
expected missing-helper assertion: original receipt SHA256
f90bd7e082c3a8f1a1d455c3e32040305cb07852e8889c7d6de7711452eaac67,
6.016s, six source-inspection Git roles plus one Python exit1, zero PowerShell
children/classifier subcases, all readers/children retired, source1872/runtime841
unchanged. This is NEW_FEATURE_PREREQUISITE_RED, not an execution of the former
catch or proof of its native failure cause. Both earlier DENY packets and all
model evidence retain their original classifications and are not rerun here.

The separately authorized source implementation adds only the shared test helper
and changes this document plus the existing installation test's helper load/env
and cap catch. Original LF test/document bytes were archived first outside source
in C:/Users/LS-5/.codex/native-output-cap-implementation-source-20261111. The exact
24-case matrix source remains SHA256
b822f4ec0d89240c1733b546eef3b00967c524da653ad802830c68b2b5f5191e.

The helper declares Test-NativeOutputCapException and has no top-level output.
It emits only a single System.Boolean; list Add/RemoveAt results are suppressed.
Pass one iteratively validates the entire exact-type, bounded, reference-acyclic
exception graph WITHOUT any Message getter. Aggregate InnerExceptions is traversed
without also following its aliasing InnerException. Unknown types, null/empty
wrappers, repeated identities, more than16 nodes or depth beyond8 reject before
message checks. No Flatten/GetBaseException/recursive walker is used.

Pass two visits the validated nodes in reverse traversal order: descendants
before parents. Every message must be a string of at most1024 characters; exact
InvalidOperationException leaves require ordinal CHILD_OUTPUT_LIMIT and null
inner. Checking descendants first bounds their messages before Aggregate.Message
can format them; structural cycles have already been refused. This is a closed,
stock-exception test contract, not arbitrary hostile-object containment or an
atomic concurrent graph-mutation guarantee. No source invokes native/IO/network
APIs, Add-Type or PowerShell autoload/module operations inside the classifier.

The existing native test validates unresolved helper ancestry and a regular
single-link helper leaf before supplying its absolute path via its existing safe
environment. Its PowerShell command refuses an already-defined function, dot-loads
the escaped fixed helper path and refuses any load output. The cap catch calls
that actual shared function on $_.Exception and rethrows unless the result is
exactly a true bool. The existing native module, C# workload, Unicode sample,
70000-character cap workload, phase markers and timeout30 remain unchanged.

Only source editing, byte/diff inspection and a source commit are authorized in
this phase. No helper parsing/import/execution, Python compilation/test, PowerShell
matrix, native workload, CI, push or new operational action was performed by the
implementer. This source is NOT classifier GREEN or Windows/hosted/runtime proof.
Root must independently review exact helper/catch bytes, then separately allocate
ONE actual shared-classifier matrix (1 method /24 subcases) and the mandatory
Windows CI/native workload qualification. No automatic retry or contract broadening
follows from an unfamiliar real exception graph. Logical mutation remains
disabled, public submit DENY and overall runtime/physical admission NO-GO.

## Separately observed local STOCK24 and proposed hosted source

Root's separately allocated MCI133→134 observed the exact shared classifier in
one Python unit method /24 distinct stock exception subcases, actual RETURN
7 TRUE /17 FALSE, and one normally retired owned PowerShell child exit0. Original
receipt SHA256 031ec79862874c7483fc9326316b3a506c16bc71c4e2a1a9f4339112b1f5db04;
profile 82f80a3e293fe5e19b38ac76cfd7716a609a77ab751a8ce522019c8215eee2a7.
That scope does not include independently retained raw nested PS streams, native
C# Run, compilation, installation/service behavior, Math or hosted Windows.

The next SOURCE-ONLY lease adds native-output-cap-assertion.yml and its dedicated
qualify_native_output_cap_assertion.py, updating only this review document.
Helper7181, matrixb822 and installation-test7f55 remain byte-identical. All old
workflows/triggers remain unchanged. The new mandatory stock24 job targets
windows-latest; it qualifies hosted Windows Server stock exceptions only, not
Win11 Home/Pro or the native workload. No skip, continue-on-error, dependency
installation, old-workflow filter change or broader timeout is introduced.

The pinned checkout/setup/upload actions use existing full revisions, least
contents:read and persist-credentials:false. Exact event HEAD is checked out with
autocrlf=false configured before checkout. Job eligibility binds repository name
YehorBabenko88/unified-system AND numeric ID1434933263, plus both PR head/base
repository names/IDs (or push repository identity) before checkout/setup. The
bootstrap repeats those bindings from the event file and binds the event SHA.
No same-name repository fallback, pull_request_target or workflow_dispatch exists.

Before any qualifier source compile/import, a stdlib-only isolated bootstrap
checks fixed C:/Program Files/Git/bin/git.exe with root-first ordinary ancestry,
single-link/external executable gates BEFORE reading its bytes or spawning it.
No cmd Git/PATH fallback exists. All Git roles disable replacements, optional
locks, fsmonitor and hooks. Bounded owned file capture verifies exact HEAD/tree/
parent, full primary ls-tree/cat-file batch bytes, all1875 tracked raw files,
ordinary single-link physical files, exact directories, no extras and clean Git.
The raw source ledger and verified qualifier copy are external, exclusive and
SHA-bound; a second same-buffer bounded read verifies the copy before execution.
The fresh external pycache prefix is passed with -I -S -B -X to the qualifier and
its sole Python unit child. No project import or unittest discovery occurs.

The qualifier reuses the reviewed3bba/9d383 capture core and narrow720b observer
patterns, with only hosted-path/origin binding adaptations. Its embedded child
source is written exclusive outside checkout and digest-checked pre/post. Actual
make_suite() must contain exactly the frozen one method; Result records actual
start/success/subTest identities, and the wrapper observes actual _run_matrix
RETURN rather than a copied classifier. It requires one exact fixed System32
PowerShell NoProfile/NonInteractive/encoded frozen command; the actual returned
Popen object is held immediately. Original PS8s/retirement2s, Python15s observed
completion, combined output256KiB and whole120s observations remain. A fallback
kill, missing profile, unknown handle or cleanup error denies. These are measured
local completion bounds, not kernel/family hardwall or hostwide containment.

Hosted Python3.12.10/setup origins and selected runtime tree are inventoried and
hashed pre/post, with a retained bounded runtime ledger. Selection excludes only
Lib/site-packages, all __pycache__ and pyc/pyo; no dependency is installed. Limits
are20k runtime files/directories and1GiB aggregate,8MiB runtime ledger,128MiB source
batch,64MiB individual tool/raw source and bounded per-role evidence. Fixed bin
Git, setup Python and fixed System32 PowerShell paths/identity/stat/raw digests
are independently observed pre/post; LS5 tool hashes are NOT reused as hosted
pins. Only System32 PowerShell permits ordinary OS-servicing hardlinks, as in
the unchanged matrix's _ordinary_tool role. Hashes/origin/resource observations
are not publisher verification, loaded-DLL closure, native or runtime authority.

Always-uploaded evidence contains original source/bootstrap failures, role
stdout/stderr, source/runtime/tool pre/post observations, exact24 RETURN/subtest
profile and artifact ID/digest. Raw nested PS stdout/stderr are consumed and
closed by the unchanged matrix and are explicitly NOT independently preserved.
No execution/import/compile/test/PowerShell/CI/push was authorized or performed
by the implementer for this source preparation. Root/A8 must review the exact
committed source and full prospective workflow cohort before any separate push
allocation. Public submit remains DENY; native/physical/runtime admission NO-GO.

## D5 source-review corrections (SOURCE ONLY)

The original D5 workflow f33d1b2b /qualifier347c2b6b /documentc7213c31 are
archived unchanged outside source before these corrections. Three concrete P2
findings are addressed without changing helper7181, matrixb822 or installation
test7f55: bootstrap poll failure must not bypass kill; candidate selection must
not precede artifact-completion gates; and a runtime file map alone does not
establish actual imported-module origins. None of these corrections has been
executed, imported, compiled or tested under this lease.

Bootstrap Git cleanup now observes poll, attempts kill on unknown status, and
attempts the held handle's wait independently. Cleanup and evidence errors are
recorded separately. The original body exception remains primary, with a fixed
cleanup-uncertainty note where relevant; unknown custody cannot return PASS.
An external unexecuted inert regression source extracts the actual workflow git
FunctionDef and supplies only BytesIO/fake owned-handle objects. Its poll-throws
case requires kill and wait. Any D5 RED for that control is predicted, NOT RUN.

Parent and unit child now observe actual sys.modules objects before/after the
unit boundary. One sealed origin-admission source definition is shared with
the embedded driver. Actual file-backed stdlib/extension origins must belong to
this run's raw runtime map and pass its held-descriptor hash guard; pyc/pyo
origins are refused. Builtin/frozen cases require their actual standard loader
identity and _imp builtin/frozen name checks. Only exact verified qualifier,
driver and explicit non-main matrix source roles are admitted outside that map.
The workflow registers the verified qualifier as its actual __main__ module.
Only the specific typing.io/typing.re identities held by admitted typing, with
its exact _DeprecatedType metaclass, may be pseudo-module classes; there is no
general fileless-module allowance. This CP312 shape was read from local typing
source without importing it. Row count/path/profile sizes are bounded. Cached
paths must point into the empty fresh external prefix; existing cache content
and other project imports deny. Origin rows are observations, not a proof of
executed byte identity, publisher provenance or transitive loaded-DLL closure.

The producer now records only candidate facts. Artifact hashing occurs before
the post-artifact measured-time gate; any artifact failure or over-budget
observation is sticky DENY. The closed candidate receipt is hash/readback-checked
before a separate completion observation. Late final write/print causes nonzero
producer return. Receipt/completion explicitly disclaim terminal self-attestation.
A subsequent workflow step requires GitHub's actual successful producer-step
outcome, independently reads closed receipt/completion/artifacts/profile with
bounded same-buffer metadata/hash checks, and records its observed elapsed time.
It cannot certify its own terminal publication; final job/producer exit and
downloaded closed-artifact verification remain necessary. No strict whole120s
kernel, family or terminal-write guarantee is claimed.

Publication additionally remains HOLD until Root reviews every automatically
eligible native/Consul route and A2 integration compatibility. The unfiltered
existing native cohort is not authorized to execute an unqualified tool. This
change does not skip, bypass, disable or modify any existing workflow to evade
that gate. Root/A8 source/cohort review and a separate execution/push allocation
are still required. Hosted STOCK24 is not Win11/native-workload acceptance.

## Original PR86 validation RED and static-shell successor (SOURCE ONLY)

The original exact5fc Draft PR86/push cohort remains preserved, never rerun. Run
43064999840 failed before any job: public original GitHub validation annotation
reports Line192/Col16, Unrecognized named-value env, in env.QUALIFICATION_BASE.
It is workflow configuration RED, not a PowerShell classifier failure:0 jobs,
no stock24 profile/cases. Source5fc, original annotation/receipts and prior4 model
bodies are retained unchanged outside this successor. The existing34 original
runs continue independently; no replacement or cancellation is authorized here.

Primary actions/runner workflow-v1.0 schema declares run-step.shell as a plain
non-empty-string, without expression context. ScriptHandler uses the supplied
argument format with string.Format(argFormat,resolvedScriptPath); repeated{0}
refers to the same generated script. ScriptHandlerHelpers assigns Python a .py
extension. The correction therefore uses ONLY this static literal shell:
python -I -S -B -X "pycache_prefix={0}.pycache" "{0}".
No env/runner/github substitution, PowerShell wrapper, re-exec, runtime assignment
to sys.pycache_prefix, dropped startup flag or additional process is introduced.

The actual runner script, RUNNER_TEMP and verified BASE must pass unresolved
root-first ordinary directory/single-link script checks before resolution or byte
reads; canonical aliases refuse rather than normalize. The startup prefix must
equal exactly str(actual __file__)+'.pycache', outside and disjoint from BASE.
Its leaf must be absent, including no dangling alias. The script is size-bounded
and hashed from one held identity-checked buffer, then the prefix is mkdir-exclusive
and verified ordinary/canonical/empty. Failed prefixes/files are never deleted or
adopted to retry. The script hash is an observation, not proof of executed memory
or primary-Git/publisher provenance. Metadata failure cannot trigger script reads.

The binding is stored as a bounded, closed, exclusive parent-prefix-binding.json,
with same-buffer digest supplied only inside the existing Python process. The
verified qualifier independently rederives the parent prefix from the controlled
runner-script path, checks ACTUAL -I/-S/-B/-X state, rooted/canonical/disjoint
paths, script hash and descriptor. Parent origin admission explicitly uses that
prefix. The one existing Python unit child still receives its separate BASE/
pycache-prefix through an actual -X argument; its origin helper's default role is
unchanged. The shared origin helper's optional cache-prefix metadata does not grant
authority. Both empty prefixes and script identity are checked before/after;
independent closed readback checks the descriptor/prefixes after producer exit.

Only this workflow, qualifier and owned review document change; raw tracked count
remains1875. Helper7181/matrixb822/installation7f55 and native workload/timeout are
unchanged. Eight new external regression SOURCE methods select the actual inline
binder/helper: static no-context shell/real-X/double-placeholder, wrong startup
prefix, reparse parent, existing prefix, canonical alias, exclusive positive
binding, parent explicit origin prefix and child default origin prefix. They use
owned inert path/stat/BytesIO objects. Original four controls retain their bodies;
any future target-SHA repin is explicit, not transferred prior qualification.
These controls have NOT run; missing new binder is only a feature prerequisite.
Original GitHub validation is the actual configuration RED.

No target import/compile/test, real PowerShell/Git/process fixture, native action,
CI dispatch/rerun/cancel or push is performed for this SOURCE preparation. No
Windows alias fallback or security/ordinary/source/origin guard is relaxed. Any
new hosted path incompatibility remains fail-closed pending original diagnosis.
Independent source review and separate execution/publication grants remain
required; no whole-hosted/Win11/native/physical qualification is claimed.
