# Five-source integration implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement task-by-task.

**Goal:** source-owned disposable integration of the five pinned modules.
**Architecture:** real Python source APIs, SQLite temporary state, Node worker
subprocesses and Chromium using API-produced observations.
**Tech Stack:** Python unittest, Node22, Playwright Chromium, GitHub Actions.
**Spec:** ../specs/2026-10-30-five-source-design.md

## Global constraints
PLAN_ONLY; SOURCE_PROVENANCE BLOCKED; PHYSICAL NOT_RUN; PRODUCTION NO_GO.
Preserve original branches. No exchanges or physical mutation.

## Review focus
Untrusted nested authority, unsupported versions, oversized fleet bodies,
stale lease reuse, absent dependencies must fail closed without fabricated truth.

### Task 1: Fleet/lifecycle boundary
- [ ] Write and run negative tests for authority-bearing nested fleet snapshots.
- [ ] Validate source-owned fleet schema at Lifecycle.snapshot and HTTP boundary.
- [ ] Exercise actual fleet sizes, resource exhaustion, fencing and recovery.
- [ ] Run full unittest suite.

### Task 2: Five-source proof
- [ ] Record actual source pins and verify each checkout before imports.
- [ ] Exercise Terminan infrastructure consumer with real lifecycle snapshots,
  missing-module combinations, invalid versions and unavailable storage.
- [ ] Exercise Strattester/Grid history boundary and Math bounded worker source.
- [ ] Run Chromium controls using generated actual snapshots.
- [ ] Add exact-head matrix artifacts and publish Draft PR.
- [ ] Download ZIPs, SHA256, report run/attempt/jobs and remaining P0/P1/P2 gaps.
