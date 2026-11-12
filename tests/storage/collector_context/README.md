# CollectorContext C0–C2 component evidence

Base: PR91 `01d7cf17f47a6bfa930a36808a4b0065c5f0f053`, tree
`599f39e91ea83fb1233b3bd5fb407755626b9468`. Scope is new local lifetime wrapper
and proposed PostgreSQL source boundary. Existing raw adapter/core are unchanged.

## API and custody

`CollectorContext.create/open(root, context_id, store_id, binding_sha256, profile)`
require keyword arguments after root. IDs are exact lowercase hex32, explicit
UUID4 and Root binding SHA256 respectively. Root/profile/inode bindings persist.
The caller owns the same context across Worker retries, not a new sink each time.

`require_ready()` is synchronous, returns None or raises. `store_capture`,
`read_capture`, `read_history`, `checkpoint`, `stop`, `mark_terminal` are async
interfaces executing immediate synchronous local IO; they need no event loop and
do not offload, spawn or queue work. `close()` is synchronous, rejects inflight
operations and independently attempts unlock/descriptor close. Local blocking IO
can block its caller. The caller owns deadlines/process custody.

Layout: `collector-owned.json`, one-byte `writer.lock`, `lifecycle.sqlite`, and
`raw/{archive,capture.sqlite}`. Existing ObjectStore/Journal implement storage;
this adds no second authority or raw store. Windows one-byte kernel ownership
excludes another local opener while held. It is not a lease or distributed fence.
Dirty/UNKNOWN/TERMINAL flags survive missing lifecycle responses. Clean STOPPED
can resume only within the persisted profile. Exhausted lifecycle journals reopen
read-only UNKNOWN without requiring another journal row. No orphan adoption or
unknown/terminal reset exists. Checkpoint/readback remain local and UNKNOWN;
publication_confirmed is always false. There is no verified replica claim.

## Actual execution, 2026-11-12

All scratch/output roots below are exclusive and retained under the task's
`outputs/` directory; no existing data was adopted or cleaned.

* `collector-context-tdd-red-20261112-r1`: 14 expected missing-module failures.
* `collector-context-tdd-green-20261112-r1`: initial 14 PASS.
* `collector-context-regression-red-20261112-r2`: conflicting replay remains
  ACTIVE (FAIL), full-journal reopen raises (ERROR), other 14 PASS.
* `collector-context-regression-green-20261112-r2`: 16 PASS after both fixes.
* `collector-context-final-20261112-r3`: 17 PASS, unittest 3.845s, child PID59020
  exit0/retired, measured wall4184ms, own30s deadline. Includes STOPPED response
  loss plus UNKNOWN append failure. Capacity fixture builds valid journal rows
  through private events to bypass normal admission reserve deliberately.
* `collector-context-raw-regression-20261112-r1`: unchanged raw adapter 15 PASS,
  unittest0.803s, direct child exit0.
* PostgreSQL static effect/readback guards: 2 PASS, unittest0.021s. No SQL engine
  parsing/execution; PostgreSQL behavior NOT_RUN.

Python direct binary: `C:/Users/LS-5/AppData/Local/Python/pythoncore-3.12-64/python.exe`,
SHA256 `4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a`,
flags `-I -S -B`, stdlib only. Explicit `A4_CONTEXT_TEST_SCRATCH` existing new
parent is required; each method creates a new private directory. Tests drive
immediate coroutines without an asyncio loop. Real Windows files, SQLite and
one-byte locks are exercised; faults are injected in calls, not physical crashes.

Independent static review identified lifecycle-capacity P2; re-review ACKed both
capacity/replay fixes without execution. No open finding from that review.

## Remaining gates

No overall C1/C2 acceptance, held-child process restart, physical disk-full,
replica recovery, native PostgreSQL, backup/restore, service identity, ACL,
provider, consensus/fencing, assignment publication, deployment or snapshot12
execution is established. Object reopen is not process restart. Logical budgets
and preflight headroom are not physical hard quotas. Root/A3/A5 own composition
and exact runtime admission. Production remains NO-GO pending those contracts
and evidence. PostgreSQL source boundary is documented separately in
`docs/storage/collector-postgres-boundary-v1.md`.
