# Phase237 independent PR79 original hosted cohort review

Repository strattester, PR79. Exact HEAD0c4f64c897aacd78bbec0e1faa886c7003c353ff/tree064ed4b7661fce976f0fd97b236e85d2ebfff7f0. Six attempt1 workflows/26 jobs independently checked against fresh run/jobs/artifact APIs. Original six log ZIPs and API files hashed;23 artifacts freshly downloaded and SHA256 matched fresh API digests. All23 original JUnit XML hashes/counts agree with owner copies. Binding uses run ID plus artifact name: push and PR artifact names repeat.

| Requirement ID | Repository | PR | Exact HEAD | Test name | Environment | Expected result | Actual result | Evidence link | Status | Severity | Required correction |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A8-CORE-PUSH | strattester |79|0c4f64c897aacd78bbec0e1faa886c7003c353ff|tests43041799366|Hosted Windows/Linux3.11/3.13|Mandatory jobs PASS|Both Windows FAIL, both Linux SUCCESS; Windows XML1failure28skip each|[verification](verification.json), run-43041799366/logs-original.zip|FAIL|Mandatory acceptance blocker|Review fixture-only correction separately; preserve original failures/skips |
| A8-CORE-PR | strattester |79|Same HEAD|tests43041826675|Same matrix|Mandatory jobs PASS|Both Windows FAIL, Linux SUCCESS; same closed diagnostic|[verification](verification.json), run-43041826675/logs-original.zip|FAIL|Mandatory acceptance blocker|No production admission relaxation based on fixture failure |
| A8-GATEWAY-PR | strattester |79|Same HEAD|Gateway43041826648|Windows/Linux|38tests pass|Windows38/.383s1FAIL; Ubuntu SUCCESS|[verification](verification.json), run-43041826648/logs-original.zip|FAIL|Mandatory acceptance blocker|Same-copy positive calibration identity inequality requires scoped fixture investigation |
| A8-DATAFIRST-PR | strattester |79|Same HEAD|Datafirst43041826650|Windows/Linux3.11/3.12/3.13|Selected254 each no skips|6×254 XML zero failure/error/skip and jobs SUCCESS|[verification](verification.json)|PASS selected cohort|Informational|Do not transfer to full Windows acceptance |
| A8-ML-PR | strattester |79|Same HEAD|ML43041826643|Hosted CPU|Selected14 no skips|14 zero failure/error/skip; SUCCESS|[verification](verification.json)|PASS selected cohort|Informational|Retain synthetic scope |
| A8-FINANCIAL-PR | strattester |79|Same HEAD|financial43041827260|Hosted engineering/native component jobs plus aggregate|Mandatory aggregate accepted|7 engineering and native job SUCCESS;8 XML no failure/error/skip, native30. Aggregate BLOCKED exit2|[verification](verification.json), run-43041827260/logs-original.zip|BLOCKED|Acceptance blocker|External gates and authenticity remain unresolved |

Full original core/Gateway closed JSON agrees: phase COPY_POSITIVE_CALIBRATION, code SOURCE_UNAVAILABLE, canonical_identity_equal false while absolute/ordinary ancestry/singlelinks/pins true, error NONE and stage COMPLETE. This observes refusal before mutation and identity inequality. Underlying alias/8.3 cause is UNKNOWN; no production-guard defect or authority to weaken it follows. LocalONE at this source and old hosted47 at889 remain separate. Projection47 is not qualified at this source.

Financial original aggregate states status BLOCKED/trading NO-GO/physical_g1 NOT_AUTHORIZED, external blockers including upstream equivalence/OOS/isolation/snapshot/physical/GPU, evidence_authenticity UNVERIFIED_SELF_REPORT. Engineering XML/job success does not qualify those external gates or broad native isolation. Core skips remain visible; no mandatory skip waiver independently accepted here. JUnit testcase entries include subtests and are not naively equated with pytest execution totals.

RELEASE_MANIFEST_STATUS: NOT_APPROVED.
NODE_INVENTORY_STATUS: NOT_ACCEPTED.
CONTRACT_STATUS: Integrated acceptance not granted.
OFFLINE_TESTS: Prior local scopes unchanged.
WINDOWS_CI: FAIL mandatory core/Gateway; selected Datafirst PASS only.
PHYSICAL_TESTS: BLOCKED.
P0_P1_P2: Existing scoped findings unchanged; this records continuing original acceptance failures, not an invented new production P0. No assertion of P0 absence.
EVIDENCE: verification.json; six original API/log ZIP packets; fresh API sets;23 fresh original artifact ZIPs bound by API digest. No owner code or CI rerun executed by A8.
NEXT_ACTIONS: Integration Owner reviews separate fixture-only exact source proposal, then separately authorizes any new attempt. No automatic retries, merge or deployment.
GO_NO_GO: NO-GO.
TAILSCALE_REMOVAL_ACCEPTANCE: BLOCKED / NO-GO.
