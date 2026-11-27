# LS5 Physical Development Smoke Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute one source-pinned, non-elevated synthetic BTCUSDT direct target and fresh Terminan render on LS5 after independent isolation admission, retaining exact evidence.

**Architecture:** Root owns one serial physical lane. Existing Strattester and MetaAnalyse functions run in an owned disposable directory; A6 owns a separate fresh-input render harness. A test-only supervisor admits fixed binaries/source files and a fresh local process family, confines its state locations, enforces reviewed Windows Job limits, verifies bytes before/after, and never opens the public/native runtime gates.

**Tech Stack:** CPython3.12.10 stdlib/ctypes, actual existing target adapter, existing Node24.22.1/Playwright1.56.1/Chromium1194, Windows11Pro LS5.

**Spec:** docs/physical-dev/OWNER-DIRECTIVE-20261109.md (exact owner attachment; SHA256961024a67181db37e3c99a66c30af7e92a23324b7f2c913ef6c1b23017d248c3).

## Global Constraints

- Public submit DENY; real provider sends BLOCKED; no real orders.
- No Windows Services, ACL, firewall, ESET, Tailscale, working Consul or production database changes.
- PostgreSQL18 currently listens55432 and is excluded. Only newly allocated SQLite/directory state.
- No protected single-use diagnostics, PR52, worker ResumeThread or CPU-rate qualification.
- Never patch a test snapshot: source fixes in a GitHub commit/Draft PR before package rebuild/retest.
- Existing source baseline Unifiedba2, Strattesteraed8, MetaAnalysef3, Terminan22e; new A6 harness exact HEAD pending.
- Default PLAN_ONLY; execution requires exact immutable package and independent source/isolation review.
- No physical multi-node test or production deployment; Windows Home separate qualification remains pending.

## Review Focus

- Non-elevated token required in both supervisor and child; never fall back to elevation.
- Reparse/hardlink/foreign-writable or preexisting state directories must fail before process start.
- Lost supervisor, timeout or partial child startup must retire only the retained own process family.
- Fresh result bytes must reach the renderer; a fixed committed fixture is not a fresh-run substitute.
- Unqualified kernel/parent-job/browser isolation must block, never disable parent policy or Chromium sandbox.

## Task1: Read-only readiness and immutable source package

**Files:** release/physical-dev/ls5-20261109/LS5-PHYSICAL-DEV-READINESS.json; tools/physical_dev/package.py; tests/physical_dev/test_package.py.
**Consumes:** exact primary Git commits, owner-approved package source/tooling pins, observed LS5 readiness.
**Produces:** bounded file manifest with per-file SHA256, source origin/dependency versions, external package digest, no credentials.

- [x] Read host/OS/resources/services/listeners/processes/ACL ancestors/token/security policy without changes; retain raw originals with hashes.
- [ ] Add failing pure tests for aliases, hardlinks, oversized/extra/changed package members, unsafe output roots and unknown source/tooling pins.
- [ ] Implement fixed source/package admission with server-selected paths and exclusive new state allocation; never repair ACL or adopt old state.
- [ ] Verify tests, publish source commit/Draft before assembling any physical test package; keep all original snapshots immutable.

## Task2: Test-only process-family supervisor and direct target

**Files:** tools/physical_dev/supervisor.py; tools/physical_dev/direct_child.py; tests/physical_dev/test_supervisor_contract.py.
**Consumes:** admitted exact package and actual non-elevated parent/child, fixed three-row synthetic request.
**Produces:** bounded own-process logs, actual direct request/envelope/artifact, source integrity and process-retirement evidence.

- [ ] A5/A8 review proposed Windows Job structures/lifecycle before any physical launch.
- [ ] Add pure failing tests for unknown parent/token/containment, missing readback, output overflow, incomplete cleanup and immutable resource parameters.
- [ ] Implement ordinary verified child that waits on bounded own stdin before starting target/browser; NO CREATE_SUSPENDED, ResumeThread, CPU-rate setter or foreign PID reopen.
- [ ] Proposed anonymous job: kill-on-close, active16, committed job memory1GiB/process512MiB, total USER-CPU10s with terminate-at-end0; query exact readback before GO. Parent/nested-job failure blocks without breakaway or policy changes.
- [ ] Wall watchdog30s and combined output16KiB; terminate/wait only own retained job/process handles, confirm active0, preserve logs. These are TEST-family bounds, not native worker/quota admission or hard real-time claims.
- [ ] Run existing DisposableTargetStand once with fresh SQLite, real Strattester/MetaAnalyse, fixed synthetic BTCUSDT; artifact2070B/f499 expected and LOCAL_UNATTESTED.

## Task3: Fresh Terminan rendering and first pilot

**Files:** A6 owns its fresh-input browser harness and Draft PR; Root owns tools/physical_dev/ls5_smoke.py and release/physical-dev/ls5-20261109 smoke evidence.
**Consumes:** fresh RAW request/envelope/artifact from Task2; exact committed A6 harness/renderer/dependency/browser pins.
**Produces:** screenshots and bounded rendering receipt bound to the fresh input SHA; no authenticated endpoint/chart/verified-market-history claim.

- [ ] A6 prepares committed harness: only own127.0.0.1 ephemeral routes, explicit Chromium sandbox, external browser requests blocked, own TEMP/profile and finally-close, no download/npm install.
- [ ] Verify all package/dependency files and origins; no installed-source edits. State filesystem verification scope precisely (protected source hashes/explicit own outputs, not unobserved global disk activity).
- [ ] A8 independently reviews exact package/source/isolation; only then release the one serial LS5 smoke allowed by owner.
- [ ] Execute direct target then fresh renderer; capture start/stop, resource readback/observations, output caps, artifact/source SHA, and complete own-process cleanup.
- [ ] Any failure: preserve RED, fix in GitHub, qualify/review/re-pin, rebuild disposable copy and retest. No local hot patch.
- [ ] Publish exact package/source/evidence and status. Overall MASTER stays NO-GO until actual remaining positive/distributed gates pass.
