# Durable five-module lifecycle implementation plan

> **For agentic workers:** Use superpowers:executing-plans; the user selected autonomous safe execution.

**Goal:** Implement stream B from CODEX_FIVE_MODULE_SEQUENCE.md without launching modules or granting physical authority.
**Architecture:** SQLite atomic event/state transactions, immutable operation IDs, explicit recovery barrier and injected source-owned verification. Independent observer/Math status and optional fleet provider. An additive read-only WSGI endpoint exports bounded snapshots.
**Tech Stack:** Python standard library, SQLite, unittest, Windows/Linux CI.
**Spec:** docs/CODEX_FIVE_MODULE_SEQUENCE.md at b8facc028e00493d8423d15280f87c2047c2b63b.

## Global constraints
PLAN_ONLY; no process launches, network/security/production mutations, paper/live execution, merge or source-branch writes. Existing legacy coordinator remains intact.

## Review focus
Replay/collision, stale source epochs/sequences, concurrent writers, crash/tamper/disk-full rollback, all partial module combinations, observer barrier and irreversible downstream invalidation.

### Task 1: Durable state machine and read-only adapter
Files: unified_system/lifecycle.py, unified_system/lifecycle_api.py, tests/test_lifecycle.py.
- [ ] Add failing tests for source-gated order, independent Math/observer, operation idempotency, cancellation/retry/recovery, module absence and corruption.
- [ ] Observe missing implementation failure.
- [ ] Implement atomic transactions and strict observation verification with default-deny callbacks.
- [ ] Test injected write failure rollback and concurrent sequence fencing; run full existing suite.
- [ ] Document migration matrix and API; commit/push independent Draft PR and verify exact-head CI, including evidence artifact.
