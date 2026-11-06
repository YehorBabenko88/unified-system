# Assignment v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prepare a reviewable Assignment v1 proposal; implement the adapter only after joint ACK.
**Architecture:** Schema and fault matrix are isolated design artifacts. Authority owns the ordered grant/publication boundary; scheduler does not emulate authority.
**Tech Stack:** JSON Schema 2020-12; runtime language/base pending Integration Owner.
**Spec:** docs/scheduler/assignment-v1.md

## Global Constraints

No production API changes before Integration Owner, Agent 2 and Agent 4 ACK.
No scheduler test model can establish consensus/storage correctness.

## Review Focus

Check counter persistence, overlapping segment IDs, response loss, skew bounds and cross-service atomicity against the fault matrix.

### Task 1: Proposed contract
- [x] Record scope, identities, lifecycle, ownership and semantic validation.
- [x] Define strict structural schema and all requested negative fault scenarios.
- [ ] Receive joint owner ACK; record exact contract revisions and runtime base SHA.

### Task 2: Scheduler adapter (BLOCKED by Task 1 ACK)
- [ ] Finalize exact adapter file paths and signatures against approved runtime.
- [ ] Add failing contract tests F01–F20 against real authority/storage test interfaces.
- [ ] Implement only Agent 5 placement/admission/assignment adapter.
- [ ] Run Windows unit and integration matrix; retain command outputs and exact tree.
- [ ] Request review and produce implementation draft PR with limitations.

Task 2 intentionally has no invented production signatures: approval and runtime selection are required inputs.
