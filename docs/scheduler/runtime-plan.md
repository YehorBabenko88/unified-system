# Scheduler runtime incremental plan, 2026-11-07

ROOT explicitly allocated runtime.py, attempt_registry.py, domain_v1.py,
worker_control.py, schemas/*.json and tests/test_agent5_scheduler_runtime.py.
Continue PR24 at db455c4926ddd50d0be7c3c615a8e4c073d12775, base
mission/operator-control-plane@2df6f5c2f77f4d883bad1a8623dd8375db529be0.
No second worktree, shared API edit, consensus, publication or fleet operation.

Goal: execute durable scheduler command handoff and worker control through explicit
authority dependencies; preserve uncertain requests across crashes. This advances
the local runtime, without qualifying an absent native authority/storage adapter.

1. Write independent failing tests for canonical typed intents, decimal units,
   immutable original IDs, pre-submit crash, UNKNOWN, reconciliation, process
   incarnation, duplicate dispatch, schedules/draining and missing admission.
2. Implement strict NEW domain encoding and SQLite command outbox. Local sequence
   numbers are never assignment revisions. No expiry-based refund/retry.
3. Implement runtime execution/reconciliation and worker handoff. Adapter must
   validate terminal receipts and fresh dispatch eligibility. Missing adapter
   fails closed. Persist dispatch uncertainty before worker invocation; recovery
   queries worker by original ID instead of repeating start.
4. Exercise actual local subprocess control with an explicitly synthetic worker;
   its output is untrusted and is never published or adopted as a checkpoint.
5. Run original 30 cases and new independent cases. Obtain fresh review of the
   complete change. Extend hosted acceptance separately with raw source bindings;
   existing 30-case inventory is preserved. No local test becomes Consul/Windows
   hosted/physical PASS.

Pending integration: A2 current EventAuthority is EFFECT_UNWIRED, not a dispatch
grant. A4 has no implemented reservation/publication API as of this proposal.
ROOT/A2/A4 must freeze exact native keys, types and index checks before wiring.
Native publication and supersession must share one Consul transaction order.
