# ROUND 3 — E/C/B resource-side writer fence acceptance contract

Status: **MODEL_ONLY / NATIVE_DB_FENCE_NOT_ADMITTED / CODE NO_GO / PRODUCTION NO_GO**.
Root candidate baseline `f05f9a73581b1c15c4cc78da2801c9f2f5dd08d0`; E source branch `gpt/e-lan-fault-boundary-20261126`.
Canonical dependencies B Grid #299/#300, C PostgreSQL #163, D Terminan #126/#127.

## P0 security finding: role-level INSERT permission is NOT a single-writer fence

At C #163 `unified_system/lab_postgres.py::provision`, `lab_writer` is granted direct
`INSERT ON TABLE provenance_minutes`. The read-only `provenance_storage_witness`
checks table privileges, immutable trigger and ownership; this is good **row
custody**, but it does **not** prevent two live processes using `lab_writer`
from inserting distinct rows. `provenance_minutes` immutability triggers protect
mutations but cannot alone establish a unique active writer.

**Never** claim canonical exclusive writer admission based on that witness or
on Root's `ConsulSessionAuthority.validate`. Consul `ModifyIndex` is a
monotone candidate token, **not** a PostgreSQL transaction constraint.

## Root source model now available

`unified_system/grid_writer_fence_model.py` is a pure, inert transition
validator with exact `WriterLeaseIdentity` fields:
`owner` (bounded stable identifier), `session_id` (UUID4), `token` (positive
signed 63-bit integer), `instance_id` (UUID4), `source_sha256`, `schema_sha256`
(exact lowercase SHA256). Model state includes
`schema=unified.grid-writer-fence-model.v1`,
`scope=ISOLATED_LAB_ONLY`, durable `generation`, `identity`, `active`.
`claim_model` requires a strictly greater token even after a stop; it
rejects active old writer, missing old-process quiescence and token replay.
`write_matches_model` checks exact identity and generation; **it is not a
runtime write grant**. `native_writer_admission` always denies.

The model accepts a caller-supplied `legacy_quiescent=True` ONLY for pure
transition tests. It does **not** inspect processes, prove lease health,
authorize DB writes or turn JSON into protected evidence. Real service
startup must never pass this boolean through as permission.

## C-owned SQL transaction obligations (for coordination, NOT SQL executed)

1. C establishes a private DB-owner-maintained fencing table, with durable
   high-water `token`, monotonically increasing `generation`, exact pinned
   `source_sha256`/`schema_sha256`, active `session_id`/`instance_id`,
   DB connection identity and revocation state. Non-owner clients MUST have
   neither UPDATE nor INSERT access to that table.
2. Initial/renewed claim is a *single serializable/locked database transaction*:
   lock the same target row; require an independently admitted Root lease and
   verified native old-process quiescence; require candidate token strictly
   greater than stored high-water; reject active old writer. CAS/commit must
   be atomic and double-start contenders must produce **exactly one winner**.
   Failure to establish quiescence or lease authority means DENIED, not retry
   with a higher arbitrary token.
3. Every canonical market-data **write** must be mediated by a C-owned
   transaction-level fence that atomically validates the current active
   generation, exact writer/connection identity and nonrevoked token before
   inserting. Old connections that survived a switch must fail at their NEXT
   write even when holding previously valid application credentials.
4. **Direct `lab_writer INSERT` access to the protected canonical table must
   be eliminated or restricted for the final fenced mode.** Otherwise a
   legacy or stale worker can bypass the fence. Owner must give a tightly
   scoped, independently authenticated write API; SQL function parameters
   or user-settable session GUCs by themselves are not identity proof. Avoid
   accidentally granting SECURITY DEFINER to PUBLIC or allowing SQL search_path
   substitution. Do not change C's existing LAB fixture without C approval.
5. A plain `pg_advisory_lock` / ephemeral Redis/Consul lock by itself is
   insufficient: it neither binds the transaction-level row permission nor
   persists high-water across crash/reacquisition. PostgreSQL owner-only
   durable token + transactional row check remains mandatory.
6. On crash, store durable state remains unknown/active until independently
   proven old connection and process extinction. Owner-only reaper may advance
   status after native check; never infer from a reused PID or an expired
   control lease alone. A new token must exceed high-water.
7. The DB custody witness stays **LAB ONLY**, is bounded and signed or
   independently verified by trusted source/actor; no raw DSN/secret in logs.
   SQL and process receipts must bind the same exact installed Grid wheel,
   schema generation, Math source and target node incarnation. The B-defined
   market-data reader's `PARTIAL` remains *chart-only*; execution/trading and
   paper authorities remain strictly false regardless of fence result.

## B-owned entrypoints

B must identify and pin the exclusive canonical Grid market-data collector
entrypoint. Disable competing `grid/worker.py` and `grid/market_backfill.py`
paths at Root's protected startup gate; do **not** remove legacy source or
unrelated tables until complete parity. The writer interface must call C's
fenced transactional write path (not direct `INSERT`). Grid still owns
source data and versioned `market_data.qualified-read-envelope.v1`; Root
does not synthesize provider authenticity, Math output, PG row custody or
Terminan data.

## Exact acceptance matrix (not yet executed against PostgreSQL)

| Test | Required |
| --- | --- |
| 32 concurrent starters, same token, same target | ONE DB winner, others denied |
| Token bool/zero/reuse/decreasing | DENY |
| Previous writer active, token increased | DENY without independently verified quiescence |
| Old connection makes a write after promotion | DENY in DB transaction |
| Same DB role directly INSERTs outside fence | DENY; no bypass |
| Reused PID, forged process receipt or JSON grant | DENY |
| Source SHA/schema SHA/session/instance mismatch | DENY |
| Owner-only DB fence table UPDATE attempt by Grid | DENY |
| Crash + WAL recovery + explicit prior process extinction | Safe higher-token reacquire, preserved high-water |
| Consul unavailable or inconsistent snapshot | No promotion, no paper or trading |
| Read `PARTIAL` with correct immutable row digest | UI only; no AVAILABLE/paper elevation |
| Production/native admission without trusted owner bindings | `NATIVE_DB_FENCE_NOT_ADMITTED` |

### Evidence limits

E authored 12 pure tests, including 32-contender simulation and 100
stop/reacquisition transitions, and added them to E's six-cell inert workflow.
A Python in-memory lock used by this test illustrates CAS ordering **only**.
It is not a real PostgreSQL lock, does not test concurrent SQL sessions,
does not prove C's native service/OS checks, and may not be used as a green
integration gate. The exact-head CI remains required.

**Open B/C decision:** agree the versioned resource-side adapter API, store
identity rules and where a real write transaction is fenced, before Root
wires the existing `ConsulSessionAuthority` and host native activation.
