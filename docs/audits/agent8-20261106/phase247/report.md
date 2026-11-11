# Phase247 review3 cleanup counter and additional known-handle ownership gap

Math PR110 fixture5721987a15d20c3f9984d52eac4446704566d4b9/tree4dfced3be2ee08fa8a33cead814bb0b92bc5bdcd; external unexecuted compiler controller review3a05e865da136baec3f7945e795733589fdf4cdd8cc92750aed5046b1c081bca7. Packet index9e625d3e6614ae724ce26fffac2c7bd23a5e84abe951cf8d517c68c8dfa82d4a and all members independently size/SHA verified. No owner-function/controller/compiler/model/API execution by A8.

| Requirement ID | Repository | PR | Exact HEAD | Test name | Environment | Expected result | Actual result | Evidence | Status | Severity | Required correction |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A8-COMPILE7-COUNTER3 | math/external tooling |110 fixture|5721987 fixture; controller a05e865|Review2→3 timing delta|SOURCE/DATA only|Uncapped measured duration and unchanged denial|Two exact code replacements only; finite/nonnegative<=5 budget flag/sticky DENY, old deadline DENY retained|[verification](verification.json), [diff](review2-to-review3.diff)|PASS SOURCE metric correction|Informational|No falsePASS claim; no need repeat unchanged selected11 for this counter alone |
| A8-F52 | Same |Same|Same controller (also inherited444 code)|Thread constructor raises after reader attempt mark|Static whole-main control flow|Known unclaimed pipe independently closed; unknown started reader retained uncertain|Attempt mark precedes Thread constructor; constructor failure creates no reader entry; final close skips marked handle|controller-review3.py:125/153/187|FAIL compiler-source readiness|P2 unexecuted proposal only|Reserve handle ownership only once an entry exists; close constructor-failed/unclaimed handle, preserve unknown-start uncertainty. Do not move mark after start and risk closing a possibly running reader. |

Independent AST comparison confirms actual terminate_owned, reader, retirement and diagnostic_policy sections unchanged from444. They retain the already-observed MODELED11 GREEN scope only. Review3 does not inherit whole-main/real Win32/compiler qualification from those four sections or from source counters. Original444, dff/509e and old/candidate model originals remain separate and immutable.

F52 static reproducer: at controller line153, reader_attempts.add(r) succeeds. start_thread at line125 evaluates threading.Thread(...) before constructing/appending its ownership entry. If that constructor raises, no reader entry exists and no reader can close r. Finally line187 closes only handles not in reader_attempts, so r is skipped. Other child termination paths still attempt their work and errors deny qualification; no actual compiler leak, falsePASS or production effect was observed. The gap concerns independent cleanup of an already-held pipe under a known constructor failure. Root/A7 received exact lines before a whole-compiler source ACK.

Required correction must distinguish definitely-unclaimed constructor failure from an UNKNOWN Thread.start outcome. Closing every attempted handle indiscriminately would be unsafe for a possibly active reader; marking only after successful start would also lose ownership when start raises after launching. Owner must provide an explicit per-handle/entry transition and exact source diff, preserving existing controls. No compiler or extra eighth input/control execution is requested or authorized by this report.

Activation proposal fe093167... is independently hashed and retains authorization NOT_GRANTED/allocation_id null; future compiler OUT absent at capture. This is a proposal, not permission. No new machine admission or protected Math retry exists in it. Any later compiler activation remains Root's separate source/custody/effects decision after this correction; A8 does not issue an execution grant.

RELEASE_MANIFEST_STATUS: NOT_APPROVED.
NODE_INVENTORY_STATUS: NOT_ACCEPTED.
CONTRACT_STATUS: No whole-system acceptance.
OFFLINE_TESTS: Prior11 inert GREEN unchanged; no new tests in this phase.
WINDOWS_CI: No new compiler/native/hosted qualification.
PHYSICAL_TESTS: BLOCKED.
P0_P1_P2: New A8-F52 P2 unexecuted-controller readiness issue; prior counts not recomputed from legacy rows. No production P0/P1 or P0-absence assertion.
EVIDENCE: verification.json, raw review3 controller, exact delta, source seals/AST proof/activation proposal.
NEXT_ACTIONS: Preserve a05e/444; owner source-only ownership correction and separate exact review. No compiler, modeled rerun or protected action granted.
GO_NO_GO: NO-GO.
TAILSCALE_REMOVAL_ACCEPTANCE: BLOCKED / NO-GO.
