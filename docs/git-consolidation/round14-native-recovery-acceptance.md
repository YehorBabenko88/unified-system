# F ROUND 14 — exact cohort and physical recovery acceptance (2026-11-26)

This is an **F-owned release qualification artifact**, not an integrated runtime implementation or a grant of production approval. Source is the exact GitHub commit snapshot in `round14-cohort.json`. Every missing witness remains **NOT_VERIFIED**, not presumed successful.

## One authoritative recovery transition (A/B/C/E handoff)

**A** owns exactly one native process identity and lifetime observer, used by E. It shall retain trusted handle + old PID/creation time/executable identity and release/epoch, including descendants, Windows service/SCM lifecycle and process-owned listener/endpoint census. E shall consume, not duplicate, that observer. `ProcessDriver.alive()==False`, a freed TCP port, historical STOPPED JSON, or a PID mismatch is **not** extinction. `UNKNOWN` blocks replacement.

**C** owns the only independent recovery lane for a dedicated LAB PostgreSQL instance; it must not be scheduled onto the possibly poisoned old `LabOwnerExecutor`. Stop admission, refuse old generation, try graceful close of **owned** SQL connection and verify old backend absence on fresh trusted C session. PG `pg_terminate_backend(pid)` alone cannot safely target an incarnation across PID reuse/TOCTOU. Never terminate arbitrary PID or another user's PG. Where safe backend-local termination cannot be proven, A/C/E may perform bounded shutdown/restart of **exclusively owned disposable LAB PostgreSQL 18** only after authentic cluster directory, child handle, listener port, and ownership are positively established. User PG/5432 are permanently out of scope. At ambiguous process/backend/cluster identity, stop and stay NO_GO.

**B/C/E** issue process and backend extinction receipts *only after physical proof*, within trusted owner authority, bound to old exact process/backend identity, previous Root generation/epoch/token, source and schema, current protected issuance and revocation. No public forgeable dataclass, callable bool, JSON evidence, or `True` adapter. Writer ABI must resolve synchronous `CanonicalLabMinuteWriter.require_current() is True` versus E async `LabWriterGrant` **without** granting the wrong thread or an old backend. The single writer, single journal and serial executor must be proven attached to the same trusted PG session.

## Native acceptance — required order

1. Build and pin source cohort: A, B30 four files, C, E, Math, D; record exact Git trees, package ID/version, dependency locks, wheel/sdist hashes, installed module hash, import origin and real entrypoint.
2. In a physically isolated disposable LAB, establish unique supervisor, Consul authority and PostgreSQL 18 at non-5432 port, with positive ownership evidence (data directory, service/process handle, TCP listener, no foreign PG). No live exchange or production credential.
3. Start fresh generation/epoch/token; admit exactly one B Grid SQL writer; create journal/checkpoint; write synthetic known minute sequence; independently confirm durable rows, source hashes, WAL, high-water and schema.
4. Induce old SQL executor timeout/poison plus in-flight uncertain COMMIT. Assert every attempted old writer/new successor write remains denied while old process/backend receipts are incomplete. Never interpret timeout as rollback.
5. Stop/revoke old Root/Consul authority. Prove old Grid child **and descendants/listener** extinct from trusted OS authority. C independent lane proves old PG backend absent. If owned PG isolated-cluster restart is required, verify exact instance ownership and WAL recovery before new grant. If either witness `UNKNOWN`, reject new owner.
6. On *fresh trusted PG18* read durable fence, WAL/recovery, old backend identity, high-water, checkpoint/pending; resolve uncertain COMMIT by stable content_id with exactly-once constraints, no blind replay. Verify old grant/epoch/fencing token fail after restart and can never reassert.
7. Issue next Root generation/epoch/token and fresh backend/session/executor/journal/Grid. Resume remaining synthetic minutes once only. Compare written content_id set, high-water monotonicity, no missing or duplicate records, no concurrent owners. Math aggregates match conservation oracle and D's chart reads accepted source; PARTIAL remains no trading authorization.
8. Verify healthy stop; bounded LAB uninstall removes only dedicated owned services/PG data and test artifacts. Recheck ordinary PG5432 and foreign processes remain unchanged; do not touch real user data.

**Negative matrix:** access denied process identity; reused PID; wrong executable; unknown grandchild/listener; TCP port reused by unrelated process; poisoned executor; C readback unavailable; stale backend PID/start; ambiguous COMMIT; WAL-only partial pending; old token reused; conflicting package `market-data`; second Bybit client/writer/supervisor; foreign PG data-dir/port. Every uncertainty is fail-closed, not success.

## Acceptance and release evidence hierarchy

`SOURCE VERIFIED` → `GIT BLOB VERIFIED` → `PACKAGE VERIFIED` → `DEPENDENCY VERIFIED` → `CI PASS` → `NATIVE WINDOWS PASS` / `NATIVE POSTGRESQL18 PASS` → `RECOVERY PASS` → `INTEGRATION PASS` → `FULL SYSTEM E2E PASS`. No inferred promotion. The separate Terminan 14/14 job success is component CI only.

## Integration freeze

Single existing PR #166 at `9349d7f3ed93ef82d120976816b968e0b716b067` remains Draft and untouched. A authorized test-only delta preserved. No A/C/E incompatible runtime copy, no B30 repin until owner authorization and physical receipts. Never merge to main; never create competing integration branch. **CODE NO_GO / PRODUCTION NO_GO.**
