# Codex: CI blockers in Terminan #50 and Math #99 (2026-10-30)

Create **two independent new Draft PRs** from the exact current source HEADs; do not modify original PR #50/#99 branches. Do not merge.

## Terminan #50
Pinned HEAD 6cfa160c0df2c812cae4d94d451e83d8446e0e1b.
Hosted contracts job 123970826320, run 41028059067, fails Chromium R4 bounded workloads: tests/browser/r4.spec.cjs line 44 expects metrics.bookRows <= 40; observed 41. Investigate real rendering/data retention algorithm and off-by-one, especially bid/ask partition and aggregation. Do not simply raise threshold or suppress assertions. Reproduce across DPR 1 and 1.5, fix actual boundedness and add adversarial regression. Re-run exact-head Windows/Linux contracts, R4 and infrastructure dashboard Chromium interactions. Preserve no-order/read-only authority and dynamic fleet controls.

## Math #99
Pinned HEAD 565d947d68c2adac7d59a3e9f44453543e13eebc.
Hosted test job 123966735714 run 41026799664 fails tests/ci-coverage.test.mjs: mandatory PostgreSQL CI must contain 'if: always()' and full matrix. Current .github/workflows/postgres-integration.yml has branch-scoped job-level if excluding fix/walk-forward-forecast-guard. Independently review workflow policy; do not weaken CI coverage or remove assertions to force green. Fix workflow so mandatory Node 22/24 x PG16/18 matrix and evidence run as intended, while respecting any explicitly isolated synthetic branch policy. If policy is incompatible, report the conflict instead of bypassing it. Re-run full exact-head CI and source/worker cancellation tests.

## Report
For each PR: exact head/tree, source-level defect, minimal patch, negative tests, local results, hosted run/attempt/job and artifact SHA256, remaining P0/P1/P2. Distinguish hosted, synthetic, physical and production. No hardware, SSH/Tailscale/ACL/service/PG production changes, G1 or trading.
