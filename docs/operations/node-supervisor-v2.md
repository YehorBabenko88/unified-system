# Node Supervisor V2: isolated receipt prototype

Base: `49a970270570548e5d4f0c5a440d30e238bb21f1`. Development implementation only. MASTER MISSION remains IN_PROGRESS / NO-GO. Physical commissioning, Windows Home/Pro service qualification, and native authority are NOT_RUN/UNAVAILABLE.

## Reuse matrix and decision

| Existing component | Decision |
| --- | --- |
| `journal.Journal` | Reuse SQLite transactions, hash chain, CAS append, 100000-record hard cap. Typed v1 receipts use existing OBSERVING envelope without altering legacy states. |
| `supervisor.Supervisor` | Preserve pure research handoff behavior. Separate local receipt lifecycle has no process launcher. |
| `fleet_control` | Model only; never accepts or produces native authorization. |
| `installation_service`, `service_actuator`, service bootstrap/entry | Existing owned-resource mechanisms remain authoritative for their own scopes. No invocation or replacement; deployment adapter belongs to integration owner. |
| Scheduler / Consul / Control API | Global scheduling, leases and admission remain external. No new consensus or admission callback. |
| Existing source guard | CI bootstraps from primary immutable Git bytes, then enforces raw equality before/after tests. |

Decision: no second SQLite engine/schema, generic executor, native service installer or consensus implementation. `NodeTaskJournal` records immutable closed intents and non-authorizing receipts. A private single-writer parent directory with protected ACL and sufficient disk is a deployment prerequisite; namespace checks do not attest ACLs or protect against a hostile administrator. Existing legacy journals cannot be adopted: mixed/unknown receipts fail closed. Use a dedicated new journal file.

## API and bounds

`NodeTaskJournal(path, max_records=10000, max_bytes=16777216)` exposes create/get/transition/snapshot/reconcile. Thirteen operation names are allowlisted. Identifiers are bounded ASCII references, never paths. No file-content, command, token, secret, network endpoint or executable payload is accepted. Preconditions/postconditions are limited to local receipt/journal checks; unknown expectations block completion. Proof is a bounded reference only and never validated as authority. Timeout is 1..60 seconds; initial deterministic handlers do bounded journal work only, with no external process or polling.

`NodeSupervisorV2(journal, node_id=..., node_incarnation=..., cluster_id=...)` exposes submit/inspect/run_readonly/reconcile. REPORT_STATUS and CHECK_HEALTH observe only this local journal's verified receipt chain. They do not assert OS, service, disk, installed release or remote health. All other operations block with PLAN_ONLY_NATIVE_AUTHORITY_UNAVAILABLE. No physical operation, shell execution, service mutation, provisioning, orders or arbitrary log collection exists.

AUTHORITY, SOURCE and FRESHNESS are independent UNKNOWN axes. Local journal integrity PASS is only a chain observation. AUTHORIZED is an historical lifecycle label, never an admission proof. Callers cannot inject booleans, callbacks, types or serialized fences to admit effects. `effects_authorized` is always false and physical acceptance is always NOT_RUN.

## Recovery and evidence retention

The append-only wrapper preserves original intent and every receipt. Exact duplicate submissions return the latest durable record. Task-ID or idempotency-key collisions reject a different intent. State advancement uses the existing journal CAS check. Invalid transitions, unknown schemas, digest corruption and I/O failures block; no in-memory advancement is returned on failed persistence.

Restart reconciliation never executes a handler. CREATED/VERIFIED/AUTHORIZED/PREPARED become INTERRUPTED; RUNNING/VERIFYING become UNKNOWN_OUTCOME. Terminal results remain unchanged. There is no automatic retry, rollback or transition out of uncertainty. Reconciliation establishes no actual-system outcome or authority freshness; those need separately reviewed native evidence and owner resolution. A completed operation is not replayed after restart.

Retention is bounded by count and file size, with a conservative 32KiB growth reserve. Capacity exhaustion blocks new writes and preserves existing evidence. There is no deletion, pruning, adoption, rotation or unbounded retry. Filesystem allocation overhead and hostile concurrent changes are outside the private single-writer precondition; full-database errors fail closed. Existing Journal read/validation is bounded by its hard count limit; wrapper intents/receipts have stricter closed schemas and sizes.

## Verification scope

Tests exercise closed schema/type rejection, immutable duplicate/collision behavior, invalid transitions, receipt copying, corruption, legacy adoption denial, capacity/full-database errors, restart before/during/after, no blind replay, all other operation denial, identity binding and proof injection denial. Initial RED import failures preceded source implementation; intermediate RED caught an illegal completion transition and a Windows test fixture connection leak; both were corrected.

Mandatory CI runs CPython 3.12.10 on Windows and Ubuntu with pinned actions, no dependencies, no cache, `-I -S -B`, exact PR head, primary Git raw bootstrap and before/after source receipts. Evidence lives outside the checkout. Model/disposable tests do not qualify native service lifecycle, Home/Pro compatibility, authority/fencing, protected execution, rollback or physical nodes. Independent Agent 8 review and actual mandatory CI results remain release gates.
