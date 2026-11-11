# Phase241 independent Math / Meta exact-source CI metadata and original logs

Fresh PR/run/job metadata and nine selected original job logs independently checked. All66 raw files in owner index matched size/SHA. The nine newly fetched original log responses match archived bytes exactly. No project code, tests, models, native artifacts or binaries executed; no CI dispatch/rerun/cancel. Current artifact records are pointers only in this phase, not independently downloaded binary/XML qualification.

| Requirement ID | Repository | PR | Exact HEAD | Test name | Environment | Expected result | Actual result | Evidence link | Status | Severity | Required correction |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A8-MATH110-MATRIX | math |110 OPEN Draft|5721987a15d20c3f9984d52eac4446704566d4b9|24exact-head Actions runs/91jobs|Hosted|Mandatory Windows/native accepted|21runSUCCESS3FAIL;84jobSUCCESS7FAIL|[verification](verification.json), fresh metadata and originals|FAIL release gate|Acceptance blocker|Resolve original Windows assertions/native qualification separately |
| A8-MATH-CHECKOUT | math |110|Same run HEAD; actual PR merge5d7d2c87ef048ba09c7bf10a140db7f6653f828e|PG push/PR and native build identity|Original logs+primary Git API|Executed identity accurately retained|Push checkout572; PR checkoutmerge5d7; primary trees both4dfced3be2ee08fa8a33cead814bb0b92bc5bdcd|[verification](verification.json), fresh commit API files|PASS identity distinction only|Informational|Never rename merge commit to HEAD; tree equivalence not commit equivalence |
| A8-MATH-PG | math |110|Push572/PRmerge5d7|42056843737/42056857558 WindowsNode22/24|Hosted|Original failure identified without invented RCA|Opaque case48a281 ERR_ASSERTION/TEST_CODE_FAILURE phaseUNCLASSIFIED/workerUNAVAILABLE; coverage fails Windows dependency|Original selected job logs|FAIL|Acceptance blocker|Map source/test evidence separately; workflow name does not prove PostgreSQL-server defect |
| A8-MATH-NATIVE | math |110|Run572/executedmerge5d7|42056857844 job127347473966|Windows|Actual native qualification|DLL_INITIALIZATION_FAILED / qualification NONE in original diagnostics|Original job log|FAIL / NOT_QUALIFIED|Native acceptance blocker|No native RCA or qualification from contract-job success |
| A8-META78-MATRIX | meta_analyse |78 OPEN Draft|f3c01a23fa5baaeeeb28eb8e9397e72b5ef4d5a1|3exact-head runs/10jobs|Hosted Windows/Linux|Accurate ordinary CI and standalone status|2runSUCCESS1SKIP;8jobSUCCESS2SKIP; original Windows3132passed1skip/3133 gate observation|[verification](verification.json), two fresh original Windows logs|PASS ordinary CI observation only|Scope limitation|Retain one skip and no runtime/native/whole integration promotion |
| A8-META-STANDALONE | meta_analyse |78|Same F3|42287346090|Standalone ADMINIT final|Required final integration accepted|Both jobs SKIPPED; not PASS|Fresh jobs metadata|BLOCKED/NOT_RUN|Acceptance gap|Separate exact authorized final path; do not transfer ordinary CI success |
| A8-MATH-PROTECTED | math |115 source separate|2446d04624469e34aa96ed766be7a4887d6d654c|42352374979|Fresh metadata only|Preserve consumed diagnostic evidence|Attempt1 completedSUCCESS unchanged; existing diagnostic result nonqualifying/DLL initialization causeUNKNOWN|Fresh protected run metadata|NOT_QUALIFIED|Native acceptance limitation|CONSUMED_NO_RETRY; metadata success not native acceptance |

Current MetaF3 original Windows logs show successful synthetic JUnit gate observation. The historical FINAL_INTEGRATION_JUNIT_REJECTED event belongs to fa487/run41669712005, not F3. Owner historical original readback and ancestor evidence are archived with provenance; this phase does not rerun that parser or independently promote historical allowed-skip diagnosis to current full acceptance. No current Meta artifact bundle was downloaded here. Current HEAD/tree/checkout facts and original logs remain distinct from claimed transitive runtime safety.

Original Math opaque assertion and DLL initialization failure are observations, not a proved source cause. Matching committed trees do not establish identical processes, binaries or commit identities. Protected Math original status remains separate from PR110 selection. Combined commit status pending with zero contexts is not proof of queued Actions: fresh actual Actions runs above are terminal. Branch-protection required-context policy was not queried here.

RELEASE_MANIFEST_STATUS: NOT_APPROVED.
NODE_INVENTORY_STATUS: NOT_ACCEPTED.
CONTRACT_STATUS: Whole system and final standalone acceptance not granted.
OFFLINE_TESTS: No new execution by A8.
WINDOWS_CI: Math Windows/native FAIL; Meta ordinary CI scoped SUCCESS, standalone SKIPPED.
PHYSICAL_TESTS: BLOCKED.
P0_P1_P2: Existing scoped register unchanged; no assertion of P0 absence or closure from workflow counts.
EVIDENCE: verification.json, all indexed originals, fresh PR/run/jobs/commit metadata and nine byte-identical fresh original log responses. Current artifacts are metadata pointers only.
NEXT_ACTIONS: Owners map original source failures and supply separately reviewed exact corrections/evidence. No protected rerun or runtime grant.
GO_NO_GO: NO-GO.
TAILSCALE_REMOVAL_ACCEPTANCE: BLOCKED / NO-GO.
