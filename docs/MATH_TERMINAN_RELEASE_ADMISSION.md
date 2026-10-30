# Cross-repo acceptance blockers — Terminan #57 and Math #103

Verified 2026-10-30 from GitHub PR heads, check-runs, and the Math strict CI runner.

## Terminan #57: eligible for *integration testing*, not physical acceptance
- Exact source commit: dbbc1c6c3b3982280af6f20b70980e4caf151b4c.
- Hosted latest checks include 10 SUCCESS and 6 historical CANCELLED entries. The author documents exact final green contract/dashboard/cache runs, with one bounded Windows cache rerun; do not call cancelled first attempt a PASS.
- The R4 book ladder bound regression was caused by an extra decorative spread row. Exact source boundedness, Chromium DPR tests and cache artifacts still require independent consumer-side smoke on the combined release candidate.
- The Terminan branch is based on an existing stacked integration parent; do not cherry-pick it into Unified, only pin/read and verify its standalone consumer contract.

## Math #103: mandatory full CI explicitly BLOCKED
- Exact source commit: 0b75c0a3583f9823d2b554806468fa541f20b35c.
- Current check-run inventory includes 52 SUCCESS and 10 FAILURE. Green bounded-worker jobs do not override mandatory full PostgreSQL matrix failures.
- scripts/test-full-ci.mjs builds one *unfiltered* inventory of every tests/*.test.mjs, rejects any root skipped/todo counts, and runs on ubuntu-latest Node22/24 x PostgreSQL16/18.
- The author identified 22 Windows-only tests in the full Ubuntu inventory. This is a CI/portability policy architecture blocker, not permission to skip tests or weaken assertions.
- Recommended independent Math workstream: classify exact Windows-only tests; preserve all original assertions; move OS-specific tests into a mandatory Windows execution cell and create an explicit, verified union-of-inventories/expected-assertion manifest. A platform test only counts when actually executed on the supported OS. Prove no test identities are lost, duplicated, deselected or silently skipped, and retain mandatory PostgreSQL16/18 x Node22/24 coverage. If existing zero-skip contract must remain literal on Ubuntu, first resolve that policy contradiction in a reviewed ADR rather than silently editing the guard.
- No changes to Math PR #99 or #103 are made in this integration candidate. Do not label full Math acceptance GREEN until the new independently tested policy and all required cells pass.

## Cross-module risk
- Unified combined candidate is PLAN_ONLY and no executable module launch adapter is admitted. A successful synthetic test does not establish source authenticity, trusted Tailscale identity, durable quorum, real exchange completeness, physical containment, paper-trading readiness or production deployability.
- Require source-owned immutability and exact-run artifacts from all five projects, independent review of Windows/admin/Tailscale/PG identity, and owner approval before physical operations.

## Codex deliverables
Open an isolated Math Draft PR from exact current #103 head. Do not change it in place or merge. Publish a platform-coverage design with test inventory SHA, negative mutation cases (missing, duplicate, unexpected skip, host mismatch, hidden selector), full Windows and Linux hosted runs, exact run/attempt/job logs, and artifact ZIP SHA256. Keep existing gated physical/production restrictions. A Terminan follow-up is only needed if pinned consumer smoke fails on its verified source head.
