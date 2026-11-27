# Independent Stratt73 CORE CI artifacts and skips

Requirement STRATT73_CORE_WINDOWS_LINUX_CI_EXACT_SOURCE. Repository strattester, PR73, exactHEADa56c24a0f25a0c5ea9222fcd953a49536c91dfc9/tree69728afcfaba28d95c8de52e5ca773b75be09a5f. Run42343442185/attempt1/pull_request; workflow tests.yml. Environment: primary GitHub API metadata/original job logs/artifactZIP bytes and primary Git workflow reads; no local suite or physical execution.

Expected/actual: primary run and all4jobs terminalSUCCESS. Workflow explicitly checks out PR head; each original log records commit exacta56. All4unexpired ZIP digests match primary API SHA256, names and workflow_run.head_sha; eachZIP contains onlypytest.xml. Windows original job logs match A7provided byte counts and hashes. No developer report substituted for original evidence.

| Cell | Job | PASS testcase nodes | SKIP testcase nodes | Successful subtests | XML nodes / suite counter |
|---|---|---:|---:|---:|---:|
| Windows Py3.11 |128315936288|2090|28|35|2118 /2153|
| Windows Py3.13 |128315936497|2090|28|35|2118 /2153|
| Ubuntu Py3.11 |128315936380|2064|54|35|2118 /2153|
| Ubuntu Py3.13 |128315936431|2064|54|35|2118 /2153|

All XML failures/errors0. Each2118testcase identity unique; suite counter2153 includes35subtests reported separately by console, not35additional XML testcase nodes. Original console and XML reconciled without inventing tests or treating skips as pass.

Windows28skips:5collection skips (history cross-repository refs absent),19compiled-native-broker cases (6safeCLI/9compiledbroker/4noncevalidation),2CUDA-unavailable,1source-owner checkout missing,1Gridcontract checkout missing. Linux54includes same28plus actualWindowsjunction/PowerShell-only cases. Full per-case reasons/details retained in independent-review.json. These are observed skips, not independently approved mandatory waivers. Native broker/source-owner/history gates therefore remain unaccepted; jobSUCCESS is CORE CI only.

The exact workflow runs pytest and Windows PowerShell parsing; it does not execute the new78Nodeprojection tests. Their local result is not promoted to this CI. Shared Unified source pin e0c2ea20aa4f1bd9476d1046e7e4b41f1b12d8e9 is an explicit workflow dependency; this evidence review is not a new source/import authenticity qualification. F16/F17 remain separate.

Status CORE_CI_SUCCESS_WITH_EXPLICIT_SKIPS. Required correction before mandatory native/history/SYSTEM acceptance: provision exact required native/source-owner/Grid/producer dependencies and independently qualify required IDs or approved optional waivers; preserve current skipped originals. No SYSTEM/fleet/Home/native/pilot/physical admission, no fullmatrix-to-release transfer. Existing6P1/3P2 unchanged, F07mandatoryskip gap remains open. Overall broader acceptance NO-GO. No retry/rerun/cancel, provider request, native actuation, office/security/network action performed; Math run not polled or actuated in this review.

Evidence original run/jobs/artifact metadata,4original job logs,4originalZIPs, download-index.json and detailed independent-review.json. Reproduction ../fetch_strat73_ci.py and ../verify_strat73_ci_payloads.py. Integration Owner and A7 notified.
