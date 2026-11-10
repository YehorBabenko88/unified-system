# A4 inventory22: независимая source/evidence проверка

| Requirement ID | Repository | PR | Exact HEAD / tree | Test name | Environment | Expected result | Actual result | Evidence link | Status | Severity | Required correction |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A8-A4-EXACT | unified-system |56, local successor not pushed |1da10616a2b8217930f354e17caaa6fcea22dac4 /c2b39329924810535add3b02c3f5c5e1b11bdf62 | Exact source/diff | Read-only owner worktree | Only3 allocated files | Exact3 paths; tracked raw Git bytes match | [verification](verification.json),[diff](exact-source-diff.patch) | PASS tracked source | — | Not a full worktree qualification |
| A8-A4-IDS22 | Same |56| same | AST lists /guard preservation | A8 AST only | Original17 retained+5 separately pinned; closed unique22 | Original ordered17 unchanged; both group hashes exact;22 source IDs match; old guard function AST unchanged | verification /source | PASS source correction | — | Actual22 fixture and hosted successor still required |
| A8-A4-PURE6 | Same |56| same | Original validator controls | Owner original CP312.10-I-S-B log |6 unique PASS/0skip |6 PASS .001s; RED is one setup KeyError, not6 native failures | original logs/taskdelta | PASS scoped original evidence | — | No A8 execution; full fixture/driver not qualified |
| A8-A4-WORKTREE | Same |56| same | Physical noextras | A8 file inventory | No non-Git files |6 ignored CP315 .pyc files found; Git status still clean | verification extra_files | FAIL readiness | Qualification blocker | Use a separately qualified fresh checkout for any future lane; no deletion by A8 |

Source correction ACK is confined to the3 allocated files. Validator rejects missing/extra/duplicate/same-count substitutions and preserves pinned17+5. Six controls call that actual validator before fixture discovery in main; helper filename does not match default test discovery. Runtime/report/printed counts derive from validated set length; original workflow/matrix/production implementation unchanged by this commit.

The first full raw/noextras check failed because six ignored caches exist. Subsequent tracked-only verification independently confirmed every committed file equals raw Git; it did not erase the noextras failure. A8 did not import project code, run qualifier main, reproduce the six controls or delete caches. Their provenance/time is not established, and they are not attributed to the claimed pure run. Existing physical guard should reject these extra files before fixture imports if this directory were used.

Original log/taskdelta SHA pins verified. They do not include a persisted exact fresh source before/after map proving the original six-control execution environment; current tracked bytes and original claimed run remain separate evidence axes. No old17/new5 storage, SQLite, ObjectStore or crash-child execution by A8. No source/publication/semantic/native/physical admission follows from a static inventory repair. Source ACK is a review result, not an A8 push, merge or fixture-execution authorization.

RELEASE_MANIFEST_STATUS: not approved release assembly.
NODE_INVENTORY_STATUS: no new observation.
CONTRACT_STATUS: strict D4/logicalDISABLED/publicDENY/runtimeNO_GO.
OFFLINE_TESTS: source correction and original6 pure scoped ACK; actual22 NOT_RUN.
WINDOWS_CI: successor NOT_RUN/NOT_QUALIFIED; old RED unchanged.
PHYSICAL_TESTS: BLOCKED.
P0_P1_P2: this phase identifies worktree readiness failure; no production corruption/native defect inferred.
EVIDENCE: verification.json, exact raw3 sources/diff, original taskdelta/logs.
NEXT_ACTIONS: Root review decision; independently qualify fresh source and separately allocated actual22 fixture lane, then original hosted successor results.
GO_NO_GO: NO-GO.
TAILSCALE_REMOVAL_ACCEPTANCE: BLOCKED /NO-GO.
