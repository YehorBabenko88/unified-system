# Node Supervisor V2: isolated receipt prototype

Base: `49a970270570548e5d4f0c5a440d30e238bb21f1`. Development implementation only. MASTER MISSION remains IN_PROGRESS / NO-GO. Physical commissioning, Windows Home/Pro service qualification, and native authority are NOT_RUN/UNAVAILABLE.

## Reuse matrix and decision

| Existing component | Decision |
| --- | --- |
| `journal.Journal` | Reuse SQLite transactions, hash chain, CAS append, 100000-record hard cap. Typed versioned receipts use existing OBSERVING envelope without altering legacy states. |
| `supervisor.Supervisor` | Preserve pure research handoff behavior. Separate local receipt lifecycle has no process launcher. |
| `fleet_control` | Model only; never accepts or produces native authorization. |
| `installation_service`, `service_actuator`, service bootstrap/entry | Existing owned-resource mechanisms remain authoritative for their own scopes. No invocation or replacement; deployment adapter belongs to integration owner. |
| Scheduler / Consul / Control API | Global scheduling, leases and admission remain external. No new consensus or admission callback. |
| Existing source guard | CI bootstraps from primary immutable Git bytes, then enforces raw equality before/after tests. |

Decision: no second SQLite engine/schema, generic executor, native service installer or consensus implementation. `NodeTaskJournal` records immutable closed intents and non-authorizing receipts. A private single-writer parent directory with protected ACL and sufficient disk is a deployment prerequisite; namespace checks do not attest ACLs or protect against a hostile administrator. Existing legacy journals cannot be adopted: mixed/unknown receipts fail closed. Use a dedicated new journal file.

## API and bounds

`NodeTaskJournal(path, cluster_id=..., node_id=..., node_incarnation=..., max_records=10000, max_bytes=16777216)` exposes create/get/transition/snapshot/reconcile. Thirteen operation names are allowlisted. Identifiers are bounded ASCII references, never paths. No file-content, command, token, secret, network endpoint or executable payload is accepted. Preconditions/postconditions are limited to local receipt/journal checks; unknown expectations block completion. Proof is a bounded reference only and never validated as authority. Timeout is 1..60 seconds; initial deterministic handlers do bounded journal work only, with no external process or polling.

`NodeSupervisorV2(journal, node_id=..., node_incarnation=..., cluster_id=...)` exposes submit/inspect/run_readonly/reconcile. REPORT_STATUS and CHECK_HEALTH observe only this local journal's verified receipt chain. They do not assert OS, service, disk, installed release or remote health. All other operations block with PLAN_ONLY_NATIVE_AUTHORITY_UNAVAILABLE. No physical operation, shell execution, service mutation, provisioning, orders or arbitrary log collection exists.

AUTHORITY, SOURCE and FRESHNESS are independent UNKNOWN axes. Local journal integrity PASS is only a chain observation. AUTHORIZED is an historical lifecycle label, never an admission proof. Callers cannot inject booleans, callbacks, types or serialized fences to admit effects. `effects_authorized` is always false and physical acceptance is always NOT_RUN.

## Recovery and evidence retention

The append-only wrapper preserves original intent and every receipt. Exact duplicate submissions return the latest durable record. Task-ID or idempotency-key collisions reject a different intent. State advancement uses the existing journal CAS check. Invalid transitions, unknown schemas, digest corruption and I/O failures block; no in-memory advancement is returned on failed persistence.

Restart reconciliation never executes a handler. CREATED/VERIFIED/AUTHORIZED/PREPARED become INTERRUPTED; RUNNING/VERIFYING become UNKNOWN_OUTCOME. Terminal results remain unchanged. There is no automatic retry, rollback or transition out of uncertainty. Reconciliation establishes no actual-system outcome or authority freshness; those need separately reviewed native evidence and owner resolution. A completed operation is not replayed after restart.

Retention is bounded by count and file size, with a conservative 32KiB growth reserve. Capacity exhaustion blocks new writes and preserves existing evidence. There is no deletion, pruning, adoption, rotation or unbounded retry. Filesystem allocation overhead and hostile concurrent changes are outside the private single-writer precondition; full-database errors fail closed. Existing Journal read/validation is bounded by its hard count limit; wrapper intents/receipts have stricter closed schemas and sizes.

## Verification scope

Tests exercise closed schema/type rejection, immutable duplicate/collision behavior, invalid transitions, receipt copying, corruption, legacy adoption denial, capacity/full-database errors, restart before/during/after, no blind replay, all other operation denial, identity binding and proof injection denial. Initial RED import failures preceded source implementation; intermediate RED caught an illegal completion transition and a Windows test fixture connection leak; both were corrected.

Mandatory CI runs CPython 3.12.10 on Windows and Ubuntu with pinned actions, no dependencies, no cache, `-I -S -B`, exact PR head, primary Git raw bootstrap and before/after source receipts. Evidence lives outside the checkout. Model/disposable tests do not qualify native service lifecycle, Home/Pro compatibility, authority/fencing, protected execution, rollback or physical nodes. Independent Agent 8 review and actual mandatory CI results remain release gates.

## Local v2 review correction

Local intent schema `unified.node-operation.v2` requires a lowercase canonical UUIDv4 authority_generation REFERENCE ONLY. Value provenance remains UNKNOWN; this component neither mints nor authenticates an issued runtime generation. This is not a global wire/producer contract or native authority ACK. Historical b82af6d v1 integer intents remain in commit history; old v1 records are rejected without rewriting, migrating or adopting a database.

New-file creation uses O_CREAT|O_EXCL, retains the reservation descriptor through initialization/append and checks single-link device/inode identity before/after. A failed reservation remains for owner inspection, never automatically deleted. Empty preexisting legacy databases also reject without adoption. Existing databases require read-only quick_check, exact legacy schema inventory and the complete typed hash-chain inventory before writes. Foreign tables, replacement, hardlinks and symlinks reject. Stat checks do not establish hostile-parent/kernel namespace atomicity or protected ACLs; a protected parent and actual native authority remain unresolved deployment gates.

Review regressions: 24 mandatory local tests. Four new actual RED failures reproduced creation-race adoption, failed-reservation deletion/absence, foreign-table adoption and inode replacement; two UUID-v2 RED errors preceded the local schema correction. Raw logs are retained outside checkout. Symlink test reports SYMLINK_CREATION_UNAVAILABLE when host privileges do not permit creating one; that result is not a native symlink/Home qualification. Two read-only local observations and eleven explicitly blocked operations remain the implemented scope.

## Immutable local journal scope, receipt v2

Local receipt marker `unified.node-task-journal.v2` includes an immutable scope `{cluster_id,node_id,node_incarnation}` in every hashchained record, equal to the complete intent scope. All three constructor keywords are mandatory, including for an absent/empty path. The first successful CREATED append establishes persisted scope using exclusive reservation and Journal CAS sequence zero. Different-scope concurrent first writers cannot both append; the losing writer rejects. Scope projections are copies backed by a private tuple, and may not rebind journal or controller identity.

Existing journal constructors and every read, create, transition, snapshot and reconciliation validate the entire persisted chain against configured scope. A controller constructor and each entrypoint verify its context against the journal. A foreign scope fails before receipt mutation; recovery never relabels another node/incarnation. Old receipt.v1/unbound histories, including historical b6f58f4, reject unchanged without migration or fake ownership. NodeOperation.v2 reference-generation semantics remain unchanged. Scope strings are local data references, not authenticated node enrollment, native ownership, producer ACK or permission grants.

The current mandatory inventory has 32 tests. Scope regression RED captured the original foreign-controller acceptance plus missing mandatory scope API, followed by tests for all three scope dimensions, mixed persisted chains, concurrent empty writers, immutable projections, swapped controller contexts and old receipt refusal. Historical b6f58f4 evidence and ROOT reproduction remain distinct from the new candidate.


SQLite resource-bound admission: NodeTaskJournal accepts only a quiescent,
single-writer DELETE-mode database. Before SQLite reads or writes it rejects
existing -wal, -shm and -journal paths (including dangling links), WAL header
versions and any mode other than DELETE. It never checkpoints, switches modes,
recovers or deletes those files. An externally changed database remains blocked
pending owner recovery. The private directory/exclusive lifecycle prerequisite
still applies; these checks do not protect against concurrent external mode
changes or a hostile administrator. The existing conservative write headroom
is not a general disk quota for unrelated processes. Held-reader WAL and
synthetic sidecar regressions exercise rejection without modifying evidence.
