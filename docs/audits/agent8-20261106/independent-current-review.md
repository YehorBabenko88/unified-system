# Independent component and preparation review — current checkpoint

**GO_NO_GO: NO-GO. PHYSICAL_TESTS: BLOCKED. TAILSCALE_REMOVAL: BLOCKED.**

RELEASE_MANIFEST_STATUS: present, preparation-only, not approved or installable. NODE_INVENTORY_STATUS: six declared candidates, mutual authentication and capacity not admitted. CONTRACT_STATUS: exact package integrity verified; endpoint/protocol/full mandatory-case ACKs remain pending. No production implementation, deployment, office network configuration, real accounts or real orders were changed by this audit.

Current open findings: **6 P1 / 1 P2; zero independently confirmed P0, without proof of P0 absence.** F08/F09/F10 have independently verified offline fixes at the source pins below. This does not close broader CI/native/runtime acceptance blockers.

## Agent7: Math112, Strattester71 and Meta77

All announced exact HEAD/tree/base pins independently match original GitHub metadata and fetched Git objects. Focused added suites reproduced **8/8, 41/41 and 24/24**, zero skips. Strattester and Meta source trees were raw-Git-blob checked before and after execution; no non-loopback sockets were allowed. These are synthetic/node-local engineering tests, not authenticated endpoint, real historical-data, market or distributed completion acceptance.

| Repository / Draft | Exact HEAD | Tree |
|---|---|---|
| Math112 | `5f93cf91acc04c6561da2e940cad87f9ac41baf2` | `28b775578e71c674518dc3b35b11dff329a17d25` |
| Strattester71 | `1722244f42d5d71a29b89bdec0e7211f2b723158` | `c484fff43f8b248c87a56af633f2fcd8715a3a0c` |
| Meta77 | `88b45c328bfdc8131ff0c6d139fddd8b27a4050c` | `83304074f9cc3f90c09615c7f6920e1a07eab0c6` |

Math preservation was independently reconstructed: all188 original test files retain their Git SHA1, SHA256 and byte counts; canonical original proof `0696dd46d5386a532060220af8d491b6888e53d7a51082f9defca30684fc857e` matches. All1225 existing inventory entries remain unchanged/in order, with exactly8 additional cross-platform identities. The existing loader test differs by exactly two compile-source additions; assertions/timeouts/maxBuffer and all other bytes match the base. Auditor-owned PowerShell compile-only experiments reproduced missing OwnedPrivateDesktop on the baseline recipe (exit1) and fixed compile success (exit0, empty stderr). This neither launches the Medium-token worker nor resolves0xC0000142.

Original source/CI records and local logs: [phase4](phase4/math-source-and-compile-review.json). Mandatory Math Windows22/24 and native run42246112894, Strattester and Meta current CI remained queued/in progress in the recorded snapshot. No terminal PASS or artifact attestation was inferred. Agent7's broader full-suite counts were not adopted as independent A8 results; this audit independently executed only the focused suites stated above. Strattester/Meta modifications are additive tests and evidence documents; no production source changed. Their evidence-doc allocations were explicitly approved by Integration Owner and then included in ownership revision3.

## Agent5: advisory scheduler and CI correction

Original component HEAD `787c862568eb47177c21393338e743ec01b5f45f`, tree `bc815723d7961a5a956565f14c53c3ed5fe73c8a`, base `2df6f5c2f77f4d883bad1a8623dd8375db529be0`: all8 changed paths match published allocation. Independently reproduced15 component tests and six additional invariant groups: independent resource exhaustion/exact bounds, six ordering permutations,100 reservation-monotonicity cases, invalid snapshots, DST/weekday-iterator/drain behavior, and all nine mutations denying caller payloads. Source imports are limited to dataclasses/fractions/datetime/zoneinfo; no production import hook or client exists.

The original PR workflow tested the default merge ref and lacked source-bound evidence. Owner correction at `942e5f1d1efb28f97fb5eaae7a216424938dd738`, tree `1b2fc3757d0ff2c6f1a1b7c6d5e56dc3ff9646d3`, changes only workflow/docs; scheduler source and tests are unchanged. Independently ran the exact embedded workflow Python block locally:15 actual tests pass, while zero tests,14 tests,15 with a skip and wrong expected SHA all fail closed. Explicit PR HEAD checkout and artifact wiring now exist. Its guard checks HEAD/tree/tracked status, not raw-byte or installed-dependency attestation. Hosted runs42247859028/42247867639 were queued and have no verified terminal artifacts. **Local component/configuration acceptance only; no Windows CI acceptance.** [Evidence](phase5/scheduler-ci-fix-review.json).

## Preparation package and ownership

Initial package `c7307af...`: all30 indexed Git blobs matched,13 registry tests pass/zero skip. Revision3 at `57e8f7524912b52ebbb639bd6d5d4fd5e2961622`: all32 indexed members matched and13 registry tests pass/zero skip; A7 evidence-doc allocations and A6 PR69/A3/A4 dependency metadata were corrected. Own A8 scope/path ACK is restricted to ownership SHA `22150f804b1b3a0d6e2047887585b1b550d189bb410fbc894ef566c553594ebe`.

Latest metadata-only package at `1beee163b8657420498214ef47b1356aac96f014`: index SHA256 `6cca8855e37c66b428b6e71b52150e67af39a62aa9afc2450dab8c56e23df039` and all33 indexed Git blobs independently match. Registry/test code did not change from reviewed57e8f75; the broad13-test suite was not redundantly rerun for this metadata-only update. Exact package verification executed successfully on all33 members. All six source baseline HEAD/tree pins match prior original GitHub commit records; they remain an audit baseline, not a combined admitted release. The added component-review accurately records source-scoped A6 fixes and no hosted/runtime/physical qualification. [Package evidence](phase6/preparation-r4-review.json).

Original A1/A2/A3 scoped ACK files hash-match the freeze records, but their contents explicitly exclude executable endpoints, strict expiry, containment and activation. The original A1 register says human design approval NOT_GRANTED; Integration Owner separately confirmed that this direct-human gate remains required. The registry's isolated-implementation authorization field cannot override that gate. No A1 human approval is inferred. [Original ACK identity review](phase6/egress-ack-review.json).

## Agent6: Terminan Sync69 defects and verified fixes

Original HEAD `166b85e888d7d0ade24bd945761ad501a94e060c` passed42 existing tests. Two independent counterexamples nevertheless failed:

| Finding | Expected | Actual at166b85e | Severity |
|---|---|---|---|
| F09 dataset snapshot NO_QUORUM | Immediately downgrade global LIVE | Remained LIVE/QUORUM_CONFIRMED | P2 |
| F10 synchronous subscription error | Stay disconnected, close handle, bounded retry | LIVE/connected; one subscription; no retry/close | P2 |

Original failing source hashes and results are retained in [sync-independent-faults.json](phase7/sync-independent-faults.json). Both defects were sent directly to A6 and Integration Owner, without editing their implementation.

Fix HEAD `42686cd8fafcefaed3c5df5adaee5173d27543fd`, tree `81c684c85bda2b64dc9a327d3667f56eeb8defc1`: original independent probes now pass. F09 yields NO_QUORUM; F10 yields RECONNECTING/connected=false, two retries/two closes. All45 Node tests pass/zero skip, four receipt guard tests pass, three schema fixture/meta-schema checks pass. Exact source receipt runner independently executed locally and reported MODEL_CONTRACT_ONLY_NOT_RUNTIME. [Fixed probes](phase7/sync-fixed-probes.json), [local source receipt](phase7/sync-fixed-contract-receipt/receipt.json).

Source/CSP/handler review confirms an additive loopback preview: no configured control adapter, commands always unavailable, no credential/session persistence or existing launcher activation. Six independent HTTP checks confirmed static asset/CSP, absent API and path traversal404, POST501, and foreign Host/Origin403; the owned server was stopped. This test applies to unchanged serve.py at166b85e; it is not a real API/RBAC check. Browser screenshots/WCAG and actual relocation were not independently executed in this review.

The corrected CI uses explicit PR HEAD and bounded45-count/no-skip TAP receipt with source hashes. The source guard records normalized Git blob identity and distinct raw worktree hashes; it is not raw-byte equality or a final before/after attestation. Actual hosted runs42248767726/42248777217 were queued, so no Windows/Linux CI PASS is granted.

## Gates and next actions

OFFLINE_ACCEPTANCE: selected component PASS only. WINDOWS_CI_ACCEPTANCE: current candidates pending; failed baseline mandatory gates remain open. INTEGRATION_ACCEPTANCE: BLOCKED without approved coherent runtime, authenticated endpoints and joint scenarios. PHYSICAL_ACCEPTANCE and TAILSCALE_REMOVAL_ACCEPTANCE: BLOCKED.

Next required evidence is terminal exact-source CI with original logs/artifacts, full Math native qualification, actual auth/expiry/RBAC, coherent integrated HA/data/relocation acceptance, and explicit user/owner gates. No queued/cancelled job, compile-only result, synthetic callback, scoped design ACK or package hash match is a substitute. Integration Owner receives this audit PR's exact commit and receipt URL; relevant source changes require fresh scoped review.
