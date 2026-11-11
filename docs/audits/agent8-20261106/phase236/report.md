# Phase236 independent actual stock matrix DATA acceptance

| Requirement ID | Repository | PR | Exact HEAD | Test name | Environment | Expected result | Actual result | Evidence link | Status | Severity | Required correction |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A8-STOCK24-ACTUAL | unified-system | Module PR not freshly reverified in this phase | d69b699466fb8b15785e0a4e886cbf60c8c91dd3 | One explicit stock exception classifier unit /24 subcases | Root allocated MCI133 local Windows | Actual frozen case IDs, expected RETURN, original outcome and bounded own-handle retirement evidence | 1 unit/24 actual unique subcases PASS;7 TRUE17 FALSE;1 owned PS exit0/no fallback/unknown;6 Git+1 Python retired/readers retired | [verification](verification.json), [receipt](receipt.json), [profile](matrix-profile.json), [original stderr](stock-matrix-unit.stderr.original.bin) | PASS LOCAL STOCK CLASSIFIER ONLY | Informational | Preserve narrow scope and consumed namespace; mandatory Windows CI remains separate |

Receipt SHA256031ec79862874c7483fc9326316b3a506c16bc71c4e2a1a9f4339112b1f5db04; profile82f80a3e293fe5e19b38ac76cfd7716a609a77ab751a8ce522019c8215eee2a7. All receipt artifact raw hashes independently checked. Actual24 subcase IDs independently compared to frozen test CASE_IDS through stdlib AST literal inspection, without executing owner code. Unit raw stderr reports one test OK and no failure/error/skip, stdout matches raw profile digest. Original profile observes actual _run_matrix RETURN and unittest addSubTest outcomes under the source-reviewed driver, not a copied classifier.

All seven recorded process roles' output byte counters equal original raw stdout+stderr and remain within caps. No recorded primary/cleanup/evidence/local bound failures or new threads; all direct waits/readers retired. One own nested PS handle recorded exit0/no fallback cleanup/no uncertain state. Source Git pre/post identity,1873 mode/blob/size inventory and clean outputs identical. Independently current1873 source and841 runtime files rehashed, cache empty. Timing remains cooperative observed: whole elapsed is before final artifact/receipt publication, no strict whole wallclock or kernel/family containment.

Nested raw PS streams are explicitly NOT independently retained. This accepts the observed stock managed exception classifier unit, not native C# Run, compiler, installation/service/SCM/ACL, F42 cause, protected Math, office/provider actions, full mandatory hosted Windows CI or physical acceptance. A8 ran only its own DATA verifier, not owner code/tests/PowerShell; no retry.

RELEASE_MANIFEST_STATUS: NOT_APPROVED.
NODE_INVENTORY_STATUS: NOT_ACCEPTED.
CONTRACT_STATUS: No new integrated acceptance.
OFFLINE_TESTS: LOCAL actual1unit24stocksubcases PASS only.
WINDOWS_CI: Mandatory hosted Windows acceptance NOT_GRANTED by local result.
PHYSICAL_TESTS: BLOCKED.
P0_P1_P2: Existing scoped register unchanged, F26/F42 remain OPEN; no absence-of-P0 claim.
EVIDENCE: Original receipt/profile/all role raw artifacts copied into this phase.
NEXT_ACTIONS: Integration Owner records exact scoped result and prepares separately reviewed mandatory Windows CI; no automatic rerun or consumed namespace reuse.
GO_NO_GO: NO-GO overall.
TAILSCALE_REMOVAL_ACCEPTANCE: BLOCKED / NO-GO.
