# Four Root unit receipt consistency boundary

This source-only pure validator is NOT a hosted artifact downloader or authentication/admission gate. validateRootRoleCoverage accepts one literal JSON string (maximum2MiB UTF-8), containing schema unified.ci-evidence-role-aggregate-input.v1, expected, run, jobs, pr, artifacts, receipts. Expected has event/ref/runnerSource/runId/attempt/prNumber/workloadHead. REST metadata is caller supplied and unattested; future pinned hosted orchestration must fetch the actual fixed-repository current-run responses and download exact artifactIDs. No arbitrary metadata URL is followed.

Exactly four entries {artifact_id,content} are required. Content is the original canonical cell JSON plus newline, maximum64KiB. GitHub artifacts and jobs lists are complete bounded<=100 responses with unique IDs. Each expected current run/attempt/cell artifact name must resolve exactly once, be unexpired/bounded, and bind workflow_run repository/run/head/branch. Each cell job must be completed/success, with exact run/attempt/head/check-run, and the actual REST referenced_workflows pin must match expected.runnerSource. The overall workflow run must still be in_progress, preserving existing current-run semantics. Source/parent/PR/event/ref guards reuse bindWorkload; its existing default running-job behavior is unchanged, with only an explicit completed phase added for aggregation.

The owned immutable role plan and exact current matrix-workflow byte hash feed validateReceipt. No copied role validator or Math numerical/test-identity algorithm is introduced. All four cells/34unique roles per cell, actual Node/PG versions, file hashes and no-authority fieldsets must match. Old/extra/duplicate/missing/stale/skip/xfail/malformed sets refuse before any publication. Pure functions perform no network, child, file write, database or crypto-signature operation. Source SHA256 checksums are not signature operations or source authentication.

Successful consistency returns CONSISTENT_SOURCE_ONLY with coverage HELD, download_custody NOT_EVALUATED, authority NONE, source_authentication NOT_EVALUATED, native_acceptance NOT_QUALIFIED and production NO_GO. Failed or absent evidence returns fixed HELD/E_ROOT_ROLE_EVIDENCE without echoing inputs. No packet boolean, environment variable or mapping can promote this to hosted coverage.

## Mandatory next custody boundary

Real hosted acceptance still requires a separately reviewed bounded Root archive reader/downloader: fixed GitHub repository/currentrun/artifactID only, validate actual ZIP digest against GitHub metadata (not against JSON), bound compressed/uncompressed bytes, allow exactly the one cell receipt member with CRC/path/extension checks and no filesystem extraction. Existing STORE-only parser is not suitable for GitHub's deflated artifacts and MUST NOT silently bypass them. Until that real loader runs on exact sources, source-only consistent fake packets are never promoted.

Math retains the actual existing validateCoverage validator for six original Math axes. A later thin Math orchestration must explicitly require both the valid six-Math result and real four-Root download validation. This module has no callback or self-asserted sixPassed flag. Six Math axes, four Root cells, original34role IDs and all historical188/1234proof obligations remain preserved. No future published matrix SHA is guessed here.

## Implemented archive-custody descendant

ARTIFACT-CUSTODY.md documents the separately reviewed bounded current-run HTTP/ZIP boundary. The pure packet function continues to return HELD; only the network/archive function can report narrow four-Root unit artifact custody after ZIP digest/CRC/decompression/current metadata and all four receipt bindings. No actual new four-cell hosted result is claimed by source tests.


## RBravo source and bounded HTTP handoff (2026-11-21)

The active role library is pinned to 4ba390b8e12070499d54b12e5609c683c00607ee with 32 raw Git inputs (31 JavaScript files and the collector workflow). `provenance/rbravo-source-repin.json` records each Git blob OID and SHA-256. The original 34 role identities and four Linux cells are unchanged; older source proofs remain historical and immutable.

The matrix bootstrap uses one pinned, Root-only checkout in a fresh private path, disables credentials and autocrlf, validates the literal source SHA before checkout, and checks the canonical HTTP helper raw hash before detached import. Runtime staging obtains that same helper from the declared role-source closure. Bootstrap API, runner API and artifact downloads delegate to the single Root-owned HTTP reader (5-second API and 10-second artifact policies); the duplicate private artifact reader is removed. The measured RBravo loader roster is 92 static controls.

For pull requests, run.head_sha, workloadHead and the actual PR head must agree before and after artifact collection and in receipts. This is distinct from Math six-axis tested merge SHA: its existing merge parent/tree verification remains a separate requirement and is not replaced by equality with the PR head.

Local evidence: 177 contract/fake-artifact controls + 88 source controls pass in Node read-only permission mode; actual RBravo loader has 92 static controls. Eight module programs and two workflow inline programs compile without execution. The original mismatched run/PR-head witness accepted before the new association guard and refuses afterwards. No GitHub checkout action, hosted role, signature, OIDC, SQLite, PG, provider or native code was executed locally. Actual four-cell download custody and all six Math axes remain mandatory. Calibration positives confer no C3/admission authority; overall coverage remains HELD and release NO_GO.
