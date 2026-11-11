# Phase245 original OLD MODELED11 RED and correction of A8 read-failure wording

| Requirement ID | Repository | PR | Exact HEAD | Test name | Environment | Expected result | Actual result | Evidence | Status | Severity | Required correction |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A8-COMPILE7-OLD11 | math/external Python tooling |110 fixture source|5721987a15d20c3f9984d52eac4446704566d4b9; external olddff pin|11 selected actual-function controls|Root MCI204 inert backend only|Original exact observed RED, no predictions|11methods:3positivePASS8FAILmethods/11assertion records including subtests;0ERRORskip|[verification](verification.json), [receipt](receipt.json), stdout.log/stderr.log|FAIL old model controls, qualified original DATA|Proposal source defects only|Candidate behavioral acceptance is separate; no compiler/native proof |
| A8-READ-FAILURE-CORRECTION | Same |Same|olddff|Actual read-failure trace and source|SOURCE+original model evidence|Accurate completeness interpretation|Old reader sets overflow; logs_complete alreadyfalse; test fails missing read_failed fact|Original stderr trace; phase244/controller-old.py|CORRECTED A8 interpretation|Audit wording correction|Do not retain claim old read failure makes completeness true; close/EOF/retire/write/member defects are separate |

Original receipt40f51977e82e8bee778168b3566c1997c991ff68ad3036dd89c869767eba0020, stdout3105B SHA1ca0648463d6d796d2dc46c4e6c900dcd8c92de7651b89603f2e353cda72d037, stderr13110B SHA8879b659784a04aafdbc99fe340166e1f6dc112d8416202ecb5179582f3a1d2d independently matched. Exact11 collected/started IDs agree with phase244 BINDINGS and original verbose run. Three succeeded methods remain distinct from eight failed methods and11 failure assertion/subtest records. Parent records own child exit1/retired/readers safe, no errors/uncertainty, source pre/post equality,1.453s observed process phase. No hostwide process or hardwall proof.

Both current original/candidate source pins match reviewed bindings;841 current runtime raw sizes/SHA independently rehashed. Actual source-selected controls are the frozen541991 methods reviewed in phase244; no full compiler-controller module import or target Win32/compiler call occurred on the recorded route. A8 did not execute any owner function, selected AST, test, compiler or API.

Explicit correction: A8's earlier source wording that a read failure could leave original_logs_complete true was too broad. In old dff reader, READER_FAILURE also calls overflow.set(), and old completeness checks not overflow. The original modeled read-failure traceback reaches the final read_failed assertion and fails because that state fact remains false; its earlier completeness-false and DENY assertions already passed. This observation does NOT reproduce complete=true after a read failure. It does not erase the separately reproduced close-failure and missing EOF/retirement/log-write/evidence-member completeness problems. The corrected444 source requires all of those state facts, but its actual GREEN is not assumed here.

Negative methods can fail at their first assertion: old direct-termination/mixed-output/completeness errors are observed at specific traceback lines, not proof every later DENY/retirement assertion was reached. Eleven failure records are not eleven distinct methods. Native-startup control is an inert numeric-classification check, not native execution or original Math DLL-initialization RCA.

RELEASE_MANIFEST_STATUS: NOT_APPROVED.
NODE_INVENTORY_STATUS: NOT_ACCEPTED.
CONTRACT_STATUS: Whole integration not accepted.
OFFLINE_TESTS: Actual old11 inert RED only; candidate11 NOT_RUN/not predicted in this phase.
WINDOWS_CI: No new hosted result.
PHYSICAL_TESTS: BLOCKED.
P0_P1_P2: Proposal defects/source corrections retain their scopes; no native/production P0 absence or closure inference.
EVIDENCE: Original receipt/stdout/stderr plus verification.json and phase244 source/bindings.
NEXT_ACTIONS: Root separately considers candidate inert attempt; preserve original RED and this correction. Compiler requires later distinct review/allocation; protected Math remains CONSUMED_NO_RETRY.
GO_NO_GO: NO-GO.
TAILSCALE_REMOVAL_ACCEPTANCE: BLOCKED / NO-GO.
