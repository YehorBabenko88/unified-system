# Durable development mission context

Status: internal contract proposal; DEVELOPMENT only. MASTER MISSION remains
IN_PROGRESS / NO-GO. No physical installation is authorized.

## Reuse and decision

Approved source base: `49a970270570548e5d4f0c5a440d30e238bb21f1`.

| Existing mechanism | Reuse / boundary |
| --- | --- |
| `unified_system.journal.Journal` | Existing SQLite transactions, hash chain, 100000-record bound, sequence CAS. No second journal engine, consensus, pruning or shared-file edits. |
| `unified_system.contracts` | Existing ContractError and canonical ASCII JSON serialization. |
| FleetControl / Scheduler / Consul authority | Remain owners of operational admission and scheduling; this component has no authority API. |
| Supervisor / installer / recovery | No execution, install, shell, deployment or automatic recovery bridge is introduced. |
| CI / GitHub / Codex | Store exact externally supplied references only; no collection, retry, network or PR automation in the module. |
| Terminan | Detached read-only Python projection proposed below; no shared UI edits. |

The controller persists development requirements and work items as typed
`OBSERVING` Journal receipts. The first receipt must be the exact
`{"kind":"development-mission","schema_version":1}` marker. Each following
receipt has exactly `kind=development-task`, integer `schema_version=1`, and
`task`. Opening always validates the existing Journal hash chain and replays
every receipt. Legacy or unknown schemas are refused, including valid old
OBSERVING journals. Creating exclusively reserves a previously absent path;
it never adopts or overwrites an existing database.

## Python interface

`MissionController.create(path)` creates an explicitly new development journal.
`MissionController.open(path)` validates an existing journal without modifying it.
`put(task, expected_sequence=n)` validates and atomically appends using existing
Journal CAS. `projection()` returns a detached JSON-compatible dictionary:

```json
{"schema_version":1,"sequence":1,"tasks":{},"grants_node_operations":false,"native_authority":false}
```

Tasks are keyed by canonical task ID. Projection sequence includes the initial
marker. An exact duplicate at a current sequence appends nothing; a stale
sequence is rejected even for a duplicate. Task ID, mission ID, owner,
repository, exact 40-hex base SHA and allowed-file scope cannot be changed under
the same identity. Create another task for a new base or scope. Dependencies may
change only if all referenced tasks exist and the full graph remains acyclic;
insert prerequisites first. Unknown dependencies and self cycles are rejected.

The closed versioned task schema records requirements, acceptance tests,
evidence requirements, completion criteria, next actions, blockers, repository
and PR references, owners, dependencies, evidence SHA256, CI workflow/run/attempt/
job/source SHA/artifact references and authorization-state observations.
External CI source may differ from base SHA because it describes the tested
revision; the caller must establish its provenance. This component does not
verify CI, approvals, claimed ownership, signatures or GitHub references.

Source, tested, integrated, Windows and physical axes are separate observations
with UNKNOWN/PASS/FAIL/BLOCKED. There is no READY state or calculated aggregate
readiness. Even a stored physical PASS or approved=true is unverified supplied
data, never native authority. Consumers must prominently preserve that meaning.
No method exports or converts a development record into Node Operation, grants
execution, schedules work, or promotes deployment admission. Models and CI
success cannot qualify Windows Pro/Home or physical installations.

## Bounds, preservation and failure behavior

Lists have at most 128 items, IDs at most 128 characters, text at most 2048,
repository-relative file paths at most 256, and task receipts at most 65536
canonical JSON bytes. There are at most 1024 task identities and Journal's
existing 100000 transitions. Canonical IDs and SHAs reject trailing LF. Absolute,
drive, traversal and empty-component file paths are rejected. JSON Schema is
the structural companion; Python additionally checks semantic/path/byte/graph/
identity constraints. No third-party validator is required.

Updates append complete validated snapshots; every original receipt, including
failed CI and approval observations, remains in the integrity chain. Latest
projection is current state; original Journal receipts remain the audit source.
No compaction, deletion, automatic schema migration or corrupt-file repair is
implemented. Capacity exhaustion is a refusal requiring a separately designed
retention/archive decision, never permission to delete evidence.

A crash before commit leaves the last committed record; a crash after commit
replays it on reopen. A crash during first initialization may leave an unusable
reserved file, which open refuses; the implementation never silently adopts or
deletes it. Filesystem write errors are surfaced to the caller and no retry
loop exists. The caller must protect the journal directory against replacement
and other local writers. Hash chains detect corruption, not malicious rewrites
by an attacker who controls the whole file; there is no external signed anchor.

## Qualification scope

Dedicated stdlib CI pins CPython 3.12.10 on Ubuntu and Windows, inventories
tracked bytes against raw Git blobs before/after a fresh isolated test process,
and requires exact mandatory mission plus primary Journal test identities.
No cache, dependency install or external runtime provider is used by tests.
Component crash/reopen, stale writer, duplicates, immutable collisions,
corruption, unknown schema, bounds, DAG and fake-success tests are software
evidence only. Independent review, integrated UI behavior, native Windows
service behavior, Windows Home/Pro qualification, deployment and physical
commissioning remain separate gates.
