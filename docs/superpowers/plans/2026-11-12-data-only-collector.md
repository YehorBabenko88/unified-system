# Data-only Collector C0–C2 implementation plan

> For agentic workers: execute tasks using superpowers:executing-plans or subagent-driven-development. Preserve RED and exact source evidence.

Goal: compose the existing Grid Worker/raw recorder and Unified A4 ObjectStore/Journal sink into a bounded synthetic offline Collector, with real checkpoint/recovery/readback and no provider authority.
Architecture: separate versioned offline Collector profile/entry; old full-runtime/GET_ONLY/service plan unchanged. Worker has an additive workload restriction, finite offline receive path shared with current raw validation. A4 owns persistent context/SQL; ROOT composes only after matching API/source ACK.
Tech stack: existing Python/Grid/Unified/SQLite; PostgreSQL schema checked first on isolated backend; Windows service qualification is separate.
Spec: owner directive 18ba6241-03a8-4fb9-9eae-cf8f0325fe6e (2026-11-12), exact original SHA recorded in integration evidence.

## Constraints

No provider sends, services/accounts/ACL/policy changes, current PostgreSQL writes, protected native/runtime execution, training, public submit, merge or deployment. A2 communication remains blocked. C3–C8 require separate owner gates. Synthetic/LOCAL_UNATTESTED never COMMITTED or verified market history.

## Ownership

- ROOT: NEW unified_system/collector_profile.py, collector_entry.py; NEW tests/collector/test_profile.py,test_entry.py,test_e2e.py; integration manifest/package/harness and this plan.
- Logging worker: NEW unified_system/collector_logging.py and tests/collector/test_logging.py, own branch/worktree.
- A3: grid/worker.py plus dedicated tests/collector/worker_*; Worker constructor launch_profile=None or exact grid.data-only-collector.v1, finite receive_offline.
- A5: grid/owned_worker_service.py plus tests/collector/owned_worker_*; exact factory/profile forwarding and async lifecycle.
- A4: NEW storage/collector_context.py, dedicated tests and collector SQL migration namespace; existing raw sink reused.
- A8: independent exact-source/results review; no target execution implied.

## Review focus

1. Default/full runtime accidentally selected: unknown profile/CLI denies before side effects; retain old bytes.
2. Network/ML/remote WAL startup leaks into data-only path: instrument forbidden imports/effects, finite offline source only.
3. Reconstructed adapters reset failures/allowances: persistent terminal/unknown/reopen and exact ownership tests.
4. Partial raw/Journal/checkpoint and duplicate/gap semantics: actual sink writes and readback, no cursor substitute.
5. Logs leak secrets/exceed finite retention or shutdown hides failures: allowed structured fields, rotation/error propagation, held task retirement.

## Tasks

- [ ] Reconcile primary source HEAD/tree/blob overlays; publish explicit adopted-vs-input manifest.
- [ ] ROOT profile: failing strict version/bounds/provider-deny/source-binding tests, minimal immutable validator, exact-scope results.
- [ ] A3/A5 implement agreed additive Worker/profile/raw factory API and lifecycle regression in separate branches.
- [ ] Logging: failing bounded rotation/redaction/recovery tests, minimal versioned app logger without NSSM edits.
- [ ] A4 persistent context/checkpoint and isolated SQL boundary; no existing DB writes.
- [ ] Compose actual finite synthetic source -> Worker receive -> RawCaptureRecorder -> A4 -> ObjectStore/Journal -> checkpoint/readback.
- [ ] Actual C1/C2 isolated E2E, restart/interrupted-write/duplicate/gap/integrity/failure tests, no external effects or live children.
- [ ] Fix observed defects; preserve originals; hosted exact source; immutable candidate; A8 review.
- [ ] Prepare exact C3 disposable Windows token/Session0/shutdown/logging/PG plan for separate approval. Do not install/start.
