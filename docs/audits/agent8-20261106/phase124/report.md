# PR54 exact639 independent local component acceptance

Exact HEAD `639e8f82cc624348b25a43934b6655d6a378a26c`, tree `60d8ef3e06b0fd71f1378134126eaad3e57273d6`, parent b144. Four changed paths only. The TLS test file is byte-identical to PR66 4e297c2. All prior 144 mandatory IDs and the primary b144 inventory SHA are preserved, with precisely one new injected-inactive-predicate TLS case. Production LAN/runtime/target files are unchanged. The workflow retains Ubuntu24.04/Windows-latest x Python3.11/3.12, exact-source guards, exact count and no-skip assertions.

| Requirement ID | Repository / PR / exact HEAD | Test | Environment | Expected | Actual / status | Evidence | Severity / correction |
|---|---|---|---|---|---|---|---|
| A8-F26-INTEGRATION-SOURCE | Unified PR54 / 639e8f8 above | Four-file delta, inventory and exact PR66 import | Independent primary Git reads | Preserve every prior case and add one | PASS, prior hash a69eb60 verified | [Source review](source-inventory-review.json) | Scoped source verification |
| A8-F26-LOCAL-145 | Same exact HEAD | Exact workflow inline driver, all 145 mandatory IDs | Own fresh no-hardlinks Windows CPython3.12.10 environment, tzdata2026.6, -I -B | 145 unique / zero errors, failures or skips, source unchanged | PASS; 1588 primary files checked before and after | [Exact executed driver](exact-inline-driver.py), [original test log](qualified-env/partial-integration-ci-tests.log), [source-bound receipt](qualified-env/partial-integration-ci-evidence.json) | Local component acceptance only; F26 remains P1 OPEN |
| A8-HARNESS-INITIAL | Same source, separate initial clone | Initial omitted dependency attempt | Direct base CPython without tzdata | Reproduce workflow setup | FAIL: 145 tests run, 10 missing-tzdata error observations; outer210s timeout interrupted post-source receipt | [Original initial log](initial-missing-tzdata-tests.log), [status](initial-attempt-status.json) | A8 setup/timeout failure, not product defect or historical hosted RCA |
| A8-F26-HOSTED | Same candidate | Four hosted matrix legs and original artifacts | Hosted Ubuntu/Windows x Python3.11/3.12 | All required exact-head runs/artifacts pass | NOT_RUN by A8 in this phase | Original b144 failures remain in phase122 | P1 OPEN pending original hosted evidence |

A8 omitted the workflow dependency installation in its first interpreter choice. All ten error observations were missing tzdata/Europe-Berlin lookup errors (including subtest errors, not ten unique cases). The original log is retained. A fresh separate clone and existing own dependency environment with tzdata2026.6 corrected preparation; installed file hashes are recorded as observed files, not a wheel-digest attestation. The corrected run uses the exact unmodified extracted inline driver, with a600-second outer harness bound; no product timeout or test assertion was relaxed. The first210-second bound had interrupted slow primary raw-byte verification, so no source-qualified receipt or PASS is assigned to that attempt.

The successful local receipt's run ID explicitly says A8_LOCAL_PHASE124_NOT_HOSTED. 145 local cases, A1's focused2 and Root's reported145 are distinct executions, not additive unique coverage. Hosted b144 DIRECT22 acceptance does not transfer to639. Original hosted failure cause remains UNKNOWN. Owner145 receipt and static reviewer claims were not independently authenticated here; A8 ran its own driver.

RELEASE_MANIFEST_STATUS: no approved release inferred.
NODE_INVENTORY_STATUS: not requalified.
CONTRACT_STATUS: mandatory inventory/source integration verified, no runtime admission.
OFFLINE_TESTS: local source-bound145 PASS /0 skip, initial environment failure retained.
WINDOWS_CI: hosted matrix NOT_QUALIFIED_HERE.
PHYSICAL_TESTS: BLOCKED.
P0_P1_P2: 7 open P1 /3 P2 unchanged; absence of P0 not proven.
EVIDENCE: exact driver, original receipts/logs and prior inventory hash linked above.
NEXT_ACTIONS: independently inspect original hosted matrix jobs/artifacts at exact release HEAD.
GO_NO_GO: NO-GO; TAILSCALE_REMOVAL BLOCKED.
