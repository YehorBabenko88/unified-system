

## Phase104 — PR53 original broker CI failure and narrow owner correction

Unified DraftPR53. Originalsource65169396d550989b6b9fc78d4f3a64a1c906172b; failed original run [42397196705](https://github.com/YehorBabenko88/unified-system/actions/runs/42397196705),eventpush/checksuite114863682310. CorrectedHEAD31e0351b9f21ac53f3eb47a23bf45d06a58e1fe1/tree787be69ece1b533dff284195bbedd34a0ae5196e. New original PR-run [42632834956](https://github.com/YehorBabenko88/unified-system/actions/runs/42632834956) namedGatewayresearchprincipalnativeConsul. Six explicit read-onlyREST/public-page requests for this independentcase;no inferencefromPR54orownerclaims/no nativetest/manualworkflowrerun/settings/sharedfileedit.

| Requirement ID | Repository / PR / Exact HEAD | Test name | Environment | Expected result | Actual result | Evidence link | Status | Severity | Required correction |
|---|---|---|---|---|---|---|---|---|---|
| A8-F24-ORIGINAL | unified-system #53 /6516939 | originalworkflowvalidation | originalREST/publicannotation | validmatrixjobscreated |run42397196705completedFAIL/eventpush/namefilepath/jobs0/check-runs0;originalannotationline25col34runnerunrecognizedinrunner.temp;primaryworkflowjobenvsameexpression | phase104/original-run.json;original-jobs.json;original-check-runs.json;annotation.original.txt;invalid-workflow.original.yml | FAIL | P1CIconfiguration | MoveConsulbinaryvariableintosupportedSTEPcontextwithoutweakeningchecks |
| A8-F24-FIX | unified-system #53 /31e0351 | actualnewGitHubregistration | primaryGit+originalPRrun | correctedcontext/actual2jobs |onlyworkflowchanged;onevarjobenv->qualificationSTEPenv;new42632834956eventPRexact31/nameactualworkflow;2matrixjobscreated | verification.json;workflow-correction.original.diff;corrected-run.original.json;corrected-jobs.original.json | PASS | P1CONFIG_FIX_VERIFIED_JOB_REGISTRATION_ONLY | NotterminalexecutionPASS |
| C104-WINDOWS | unified-system #53 /31e0351 | mandatoryWindowsnativeprincipaldriver | GitHubwindows-latest | originalterminal15/0skip/artifacts |job129213231028QUEUED/null/runner_id0;no driverexecutionresult | corrected-jobs.original.json | BLOCKED | existingCIgate | Verifyterminalactualtests/logs/artifacts/exactHEAD |
| C104-LINUX | unified-system #53 /31e0351 | mandatoryLinuxnativeprincipaldriver | GitHububuntu-24.04 | originalterminal15/0skip/artifacts |job129213231455QUEUED/null/runner_id0 | corrected-jobs.original.json | BLOCKED | existingCIgate | Independentlyverifyoriginalterminaloutcome;noinvalidoldrunretry |
| C104-SOURCE | unified-system #53 /31e0351 | source/test/API/schemaequality | primaryGitobjects | onlyCIplacementchange |broker1e9f4bb/test/qualification/API+4recordschemasALL8pathsbyteequal651;diffonlyworkflow | verification.json;workflow-correction.original.diff | PASS | — | CodeequalitynotnewHEADnative15executionqualification |
| C104-AUDITLIMIT | unified-system #53 /6516939 | historicalphase99staticreviewcorrection | originalauditpreserved | nooverstatementofreview |phase99source-onlyworkflowreviewdidnotcatchunsupportedcontext;neworiginalGitHubannotationnowestablishesexactcause;oldsource/UI/nativeevidenceunchanged | phase99/report.md;phase104/annotation.original.txt | FAIL | A8staticreviewlimitationacknowledged | Requireactualnamedrun/jobregistrationandterminalmandatoryCIbeforeacceptance;neverinferfromotherworkflow |
| C104-LEVELS | allreleaselevels | acceptancepreservation | independentlevels | noPASStransfer |c02A8own15+2remainphase98;651ownfocused1phase99;31newnativetests0;publicsubmit/targetadapter/job/worker/nativeUTCatcommit/twodomain/nativehumanphysicalNOT_ADMITTED | phase98/report.md;phase99/report.md;currentstatus | BLOCKED | existingreleasegates | ActualtargetTxn/mandatoryCIandhigherlevelsseparate |

A8-F24narrowconfigurationcauseisFIX_VERIFIED_CONFIGURATION_AT_31e0351_JOB_REGISTRATION_ONLYbecauseGitHubactuallycreatedbothmatrixjobs. Originalfailurewasverifiedindependentlyinitsownrun/jobs/emptycheckruns/publicHTML,notassumedfromsamepatterninPR54. RawpublicHTMLsha b6a381ca...retainedlocally/unpublished;faithfulannotationandoriginalRESTplusprimaryYAMLpublished. Ownerownworkflowfixleftbroker/15testIDs/sourceguard/ACL/schemaunchanged. Thisdoesnotproveactualnative15ranat31,thatWindows/LinuxpassedorCIartifactsarecomplete. RemainingmandatoryCIgateBLOCKED;existingopen6P1/3P2unchanged,narrowF24originalP1+fixretained.

No previousauditsrewrittenandno newproductexecution. ActualConsulstandtestsarenotrerunmerelyforCIcontextchange. P1heremeansmissingmandatoryCIconfiguration,notnativeauthorizationescalation. Nativeexpiry-atcommit/workerresource/two-domainacceptancegapsremainunclosed. No brokeradapter/sourceproof/jobgrantorpublicsubmitadmissiontransfer.

RELEASE_MANIFEST_STATUS: EXACTPR53PINS_KNOWN_GLOBAL_RELEASE_NOT_APPROVED.
NODE_INVENTORY_STATUS: NOT_NEWLY_ADMITTED.
CONTRACT_STATUS: DISPOSABLEPRINCIPALREADCAPTURE_ONLY_NOJOBWORKERADMISSION.
OFFLINE_TESTS: NO_NEW_NATIVE_TESTS_OR_PRODUCT_RUN_PHASE104.
WINDOWS_CI: BLOCKED_NEW_WINDOWS_JOB_QUEUED_NO_RUNNER.
PHYSICAL_TESTS: BLOCKED.
P0_P1_P2: confirmedopen6P1/3P2unchanged;F24P1configurationcausefixed31/jobregistrationonly.
EVIDENCE: phase104originalREST+publicannotation+primaryworkflow/neworiginalPRrun2jobs/8protectedsourcepins.
NEXT_ACTIONS: Root/A2CIcontrollerverifiesoriginalterminaljobs/artifactswithinreadbudget;no manualrerun/settings/noanalogy-basedPASS. Actualruntimeintegration/nativephysical/Tailscalegatesremainseparate.
GO_NO_GO: NO-GO. TAILSCALE_REMOVAL_ACCEPTANCE: BLOCKED/NO-GO.
