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
