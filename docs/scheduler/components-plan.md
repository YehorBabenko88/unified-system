# Isolated scheduler components — approved scope implementation plan

Base branch: mission/operator-control-plane; immutable SHA 2df6f5c2f77f4d883bad1a8623dd8375db529be0.
Feature: feature/agent5-scheduler-components-20261106.
Owner-approved paths: scheduler_components/**, tests/test_agent5_scheduler_components.py, docs/scheduler/**, .github/workflows/agent5-components.yml.

Intent: independently test placement and schedules while shared authority/storage protocol is gated.
No live authority client, storage publication, activation hook, second consensus or physical change.

1. Write failing pure-function tests for vector capacity, pressure, freshness, benchmark, health/roles/locality and explicit queue reasons.
2. Implement immutable typed candidate/resource inputs and deterministic placement; output candidate only, never grant or reservation.
3. Write failing Europe/Berlin boundary/cross-midnight/DST tests; implement aware-instant windows with starting-day semantics and explicit DRAINING decision.
4. Write failing all-operation safety-gate tests; implement closed authority boundary with no backend/socket/client.
5. Run local isolated/full suite, run Windows-only component CI, request independent review, publish draft PR against component base branch.

All policy thresholds and weights are required caller inputs; no invented production TTL or load limits.
Windows needs tzdata when system IANA database is absent. Missing timezone data fails closed.
Model/load measurements cannot establish production resource or authority limits.

Ledger: pure placement is advisory; reservations, authoritative freshness, stale-worker fencing and atomic publication remain A2/A4 backend responsibilities.
