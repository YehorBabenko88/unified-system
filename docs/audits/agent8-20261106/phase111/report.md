# Agent8 phase111 — original PR54 hosted artifact verification

| Requirement ID | Repository | PR | Exact HEAD | Test | Environment | Expected | Actual | Evidence | Status | Severity | Required correction |
|---|---|---|---|---|---|---|---|---|---|---|---|
| CI111-UBUNTU | unified-system |54|83d35ce4b18cb6adc556c8e1412ad7b0cffef2e8|original run42632828686 attempt1 artifact13681098824|A8 readonly Root originalZIP+directGitHubREST|API digest/length andmemberhashes/sourcepinsmatch|290872B SHAe18032880fe462239c7d81a64c4698ced385f8c33678277a57f42dd10fed13ec;5members;all4 receipt-listed payloads rawlength/hashmatch;21tests0skip/sourceequal;actualartifact2070B/f4997d7d26211676cd8664e53d7999f8b71f203510f3b9a275b439c403e03940|ubuntu-artifact-metadata.original.json;ubuntu-qualification.original.json;artifact-verification.json;originalZIP|PASS|—|Only original Ubuntu direct-target artifact verification; no newWindows/nativechainqualification|
| CI111-WINDOWS | unified-system |54|83d35ce4b18cb6adc556c8e1412ad7b0cffef2e8|original failed Windows artifact13682889468|same read-onlystand|preserve FAIL despite partialreceipt|283000B SHA3d4bb1294c143cb046cc0526947d289d4d67dee31ed8a101e343056b3e64badd;ONLYqualification.json;21tests/sourceequal but lacks failure/errorcounts and actualpayloads;originaljob129213210871FAIL/1error per phase107rawlog|windows-artifact-metadata.original.json;windows-qualification.original.json;artifact-verification.json;originalZIP;phase107original-log-verification|FAIL|historicalmandatoryCI|Receipt count is execution count, not success; keep original failedCI distinct from correction|
| CI111-SOURCE | unified-system+strattester+meta_analyse |54/A7pins|83d/aed8/f3c|both artifact source maps versus independent primaryGitobjects|A8 batchcatfile/hashGitblobOIDs|both before/after maps match actual commits|1583Unified+800Stratt+782Meta primaryBLOB maps independentlycomputed; both hostedreceipts before/afterexactmatch|primary-object-source-binding.json;both qualificationoriginals|PASS|—|Gitobjectbinding not physicalnode/runnerattestation|
| CI111-LEVELS | six repos |unadmitted|newb144notcovered|mandatory releaseCI/nativeE2E|NOT_RUN|no acceptance transfer|this is original83d artifact inspection, no new test/nativeworker/profile/issuer/publication/physical run; b144hosted remains separatelypending|phase108ci snapshot;phase106gates|BLOCKED|existingreleasegates|TerminalexactmandatoryWindows/Linuxartifacts and integrated ownerapprovedsource|

No archive extraction or executable invocation. ZIP entrynames were duplicate-free/top-level only; receipts/member payloads inspected as bytes. Raw ZIP bytes were downloaded earlier by Root; A8 independently verified against current original GitHub artifact metadata/digest and inspected every listed member. OriginalUbuntu jobSUCCESS was independentlyobserved phase106; phase111 now closes content inspection beyond metadata only. This does not reclassify original overall runFAIL/WindowsFAIL. Both receipts lack failure/errorcounts; source_before==after and tests_run==21 alone cannot supply PASS, especially on failed Windows job.

RELEASE_MANIFEST_STATUS:original exactsourceartifactsverified, no integratedreleaseapproval.
NODE_INVENTORY_STATUS:no new inventoryacceptance.
CONTRACT_STATUS:native integration ownerACKs absent.
OFFLINE_TESTS:no new execution; artifactchecksPASS/originalWindowsFAILpreserved.
WINDOWS_CI:original83dFAIL; newerb144terminalmandatoryNOTQUALIFIEDhere.
PHYSICAL_TESTS:BLOCKED.
P0_P1_P2:no newfinding;6P1/3P2baseline+nativeP0gatesOPEN.
EVIDENCE:thisdirectory/API metadata+originalZIP+members/sourcebinding+bundleSHA256SUMS.
NEXT_ACTIONS:verify currentexactmandatoryCI/jobs/artifacts independently;actual native integratedsource/ACKs and qualifiedE2E.
GO_NO_GO:NO-GO. TAILSCALE_REMOVAL:BLOCKED. No reruns/protectedMathdiagnostics/officefaults/networkchanges/orders/deployments.
