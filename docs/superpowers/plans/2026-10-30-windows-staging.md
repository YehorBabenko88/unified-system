# Windows staging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Produce bounded per-node declarative staging reviews with no physical action or admission.
**Architecture:** Add pure staging.py and isolated fixture tests. CI script writes exact-checkout evidence and a six-logical-slot example. Existing installer/security APIs unchanged.
**Tech Stack:** Python standard library/unittest; Windows/Linux Python3.11/3.13 Actions.
**Spec:** docs/WINDOWS_STAGING_PLAN_ONLY.md

## Global Constraints
PLAN_ONLY; <=64 desired/predecessor nodes each; exactly five source commit/tree pins; no commands, credentials, host I/O or executor; physical NOT_RUN; production NO_GO; admission BLOCKED; all host checks UNVERIFIED. No G1/orders/deployment/merge.

## Review Focus
Unknown nested keys/secret payloads rejected; predecessor claims never confer trust; disjoint membership remains bounded; source changes never install; CI identity is not host admission.

### Task1: Pure source/membership model
Files: unified_system/staging.py, tests/test_staging.py, docs/windows-staging-sources.json.
Consumes: source_lock {schema,sources}; desired [{id,modules,intent}]; previous [{id,modules,source_lock_sha256}]. Produces: build_staging_plan(source_lock,desired,previous=()) -> dict; source_lock_digest(source_lock) -> str.
- [x] Write negative/positive contract tests and run failing import.
- [x] Implement strict exact schema/type/bounds and immutable projection; all checks UNVERIFIED, proposals blocked.
- [x] Run focused suite; verify no import/call path permits I/O or execution.

### Task2: Fixture evidence and hosted qualification
Files: scripts/verify_staging.py, .github/workflows/windows-staging.yml; docs/WINDOWS_STAGING_PLAN_ONLY.md.
- [x] Add source-fixture regression with actual repository source pins and initial six logical slots.
- [x] Implement offline report generator with exact source identity, unittest failure/skip counts, specimen plan and file hashes. No physical probes.
- [ ] Run full source suite and evidence verification on clean commit.
- [ ] Obtain fresh independent review, fix findings, publish separate Draft from2fdd; run exacthead hosted matrix and download actualZIPs/digests.

Ruling: user's explicit autonomous-design choice replaces repeated design approval questions; physical gates remain separate and blocked. Execute inline with one fresh independent final review.

Independent review: P2 module-removal review omission reproduced with failing actual-planner regression; corrected allUPDATE drain/fencing and removal revocation/retention order. Fresh reviewer independently8focusedtestsPASS and approved final source, no further P0/P1/P2. Full prior suite159 PASS with1 pre-existing Windows symlink-unavailable skip; dedicated staging inventory8 has no skips. Hosted qualification pending.
