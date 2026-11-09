# Agent8 phase108 — exact F25 configuration correction

| Requirement ID | Repository | PR | Exact HEAD | Test name | Environment | Expected | Actual | Evidence | Status | Severity | Required correction |
|---|---|---|---|---|---|---|---|---|---|---|---|
| F25-FIX108 | unified-system |54|b144a5e0fd3af90c975bfc0f0123234628dbb696|actual committed workflow YAML tests|A8 own Windows CPython3.12.10/PyYAML6.0.3 -I -B|all actual workflow run commands are valid strings; colon negative rejected|2PASS0skip; five pip commands now block scalars;1587primaryraw/noextras pre/post equal|own2.stderr.log;primary-verification.json;source.diff|PASS|P1 corrected offline|No hosted PASS inference|
| CI108-PRESERVATION | unified-system |54|b144a5e0fd3af90c975bfc0f0123234628dbb696|protected source equality|primary Git objects|runtime/direct tests/driver/144inventory unchanged|all4 byteequal68761ae; new files only YAML test+lock metadata/triage plus five scoped workflow fixes|primary-verification.json;source.diff|PASS|—|A8 prior22 stays exact687, no rerun/new runtime claim|
| CI108-HOSTED | unified-system |54|b144a5e0fd3af90c975bfc0f0123234628dbb696|original hosted workflow registration|read-only GitHub REST|terminal mandatory Windows/Linux/artifacts qualified|38run snapshot/0conclusionFAIL; named originals queued, not terminal acceptance|ci-current.original.json;ci-summary.json|BLOCKED|existing mandatory gate|Verify terminal exact jobs/artifacts separately|

Tree01537daf676f3d9e4e924ba80026b531912cabd7. F25 status FIX_VERIFIED_OFFLINE_CONFIGURATION_AT_b144. Original687 five parser failures/jobs0 remain immutable in phase107; original83d Windows RED remains historical. These two new tests cover actual all-workflow documents and generic colon parsing, not native execution or GitHub semantic context validation. PyYAML6.0.3 dependency was already present in A8 own environment; no new package installation in this phase. Six platform wheel hashes in owner source are not independently downloaded/qualified by A8 here.

RELEASE_MANIFEST_STATUS: global approved integrated package NOT_RECEIVED.
NODE_INVENTORY_STATUS: no new approved inventory.
CONTRACT_STATUS: integrated exact owner ACKs/actual chain absent.
OFFLINE_TESTS:2PASS0skip,1587rawprimarypre/post/noextras.
WINDOWS_CI:BLOCKED_QUEUED_NOT_HOSTED_PASS.
PHYSICAL_TESTS:BLOCKED.
P0_P1_P2:F25 narrowfixverified; prior baseline6P1/3P2 remains; owner-labelled P0 native gates OPEN.
EVIDENCE:this directory and bundle SHA256SUMS.txt.
NEXT_ACTIONS:terminal exact mandatory CI/artifacts; integrated actual source/owner ACKs.
GO_NO_GO:NO-GO. TAILSCALE_REMOVAL:BLOCKED. No reruns/Math diagnostics/office or network changes.
