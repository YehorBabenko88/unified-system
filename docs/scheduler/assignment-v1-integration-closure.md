# Assignment v1 — integration closure worksheet, revision 2 proposal

Status: INTEGRATION_PENDING / NO-GO. This worksheet does not amend the frozen v1 hashes.
Frozen spec c9fcadbb580194f5471b69a2c2ee5f4ec79719c0a9c5bc9daaf1f56861e39140.
Frozen schema 799f07457bbd8419da4e859f27425ec58b884b89330e4224577f372070224a79.

## Identity mapping proposal (joint API ACK pending)

All IDs are opaque, stable registry identifiers; never IP, hostname, drive letter or a display symbol.
New registry identifiers use randomly allocated UUIDs and explicit namespace keys. Existing IDs require migration mapping,
not reinterpretation. Case-sensitive opaque equality; no concatenated scope keys.

| Identifier | Uniqueness / issuer | Binding |
| --- | --- | --- |
| cluster_id | globally unique, Integration Owner provisioned | stable deployment identity across normal restarts |
| cluster_generation | unique within cluster, Agent 2 | changes on disaster restore; all old generation grants fenced |
| node_id | unique in cluster, authenticated node registry | hardware enrollment principal; address is mutable metadata |
| worker_id / owner_id | unique in cluster, authenticated worker registry | owner_id equals worker_id by explicit adapter mapping; multiple workers may share node_id |
| worker_incarnation_id | fresh random UUID per process start | bound to node_id + worker principal in authority registration, no independent rights |
| job_id | unique within cluster generation, durable job registry | stable logical job; restart/retry never silently changes identity |
| assignment_id | unique within cluster generation, authority | one immutable assignment revision/owner/incarnation binding |
| lease_id | distinct authority grant identifier if Agent 2 retains it | NOT silently aliased to assignment_id; final mapping pending Agent 2 |
| dataset_id | unique within cluster generation, Agent 4 catalog | stable dataset namespace |
| instrument_id | unique catalog ID within cluster, ingestion/catalog owner | registry binds exact exchange/category/symbol/instrument_version; symbol alone is not identity |
| storage_reservation_id | unique within cluster generation, Agent 4 | scope + volume allocation + budget + expiry binding |

Every mutation, receipt, token and idempotency namespace binds cluster_id + cluster_generation.
Scope counters are keyed by cluster/generation/job/dataset/source/partition; restore must fence old generations before opening writes.
Segment logical dedupe excludes job_id and assignment_id; preservation across generation restore requires explicit dataset reconciliation.
lease_epoch is replacement authority; grant_revision is renewal version; assignment_revision is durable placement/supersession version.
authority_term/leader_lock_index are separate diagnostic/authority provenance, never replacements for these versions.

## Operation closure matrix

All mutations are authenticated, expected-version CAS commands ordered by the existing Agent 2 authority.
Scheduler sends intent; it neither issues tokens nor implements storage publication.

| Operation | Required atomic preconditions/effects | ACK |
| --- | --- | --- |
| Create | current generation/registration, fresh capacity, prepared compute/storage bindings; durable revision+epoch allocate and ACTIVE grant | Agent 2/4 PENDING |
| Supersede | compare current assignment/grant/state; fence old identity and publish replacement in same authority order | Agent 2 PENDING |
| Renew | current grant/incarnation/state, valid time/reservation/drain; advance grant_revision, invalidate old token | Agent 2/4 PENDING |
| Validate reservation | same scope, current reservation/budget revision, actual remaining entitlement, valid expiry; inside commit, not remote precheck | Agent 4/2 PENDING |
| Publish | current grant/registration/state/drain; root/job-checkpoint CAS, physical allocation debit, outbox and receipt in one ordered boundary | Agent 2/4 PENDING |
| Cancel | commit terminal fence first, reconcile UNKNOWN receipts, release only proven unused entitlement | Agent 2/4 PENDING |
| Restart/rejoin | fresh incarnation; reconcile committed receipts/checkpoint; new assignment revision/epoch/reservations | Agent 2/4 PENDING |
| No quorum | no new authority mutations/publication; local stop and stale diagnostics only; UNKNOWN stays UNKNOWN | design ACK only |

Linearization MUST be one existing authority transaction checking exact assignment/grant/state/registration/reservation/budget/drain revisions and
publishing authoritative root/checkpoint/outbox/receipt references. Supersession changes the same checked record.
Local SQL is a recoverable projection, not a second atomic commit authority.
Strict time expiry remains P0: current Consul transaction cannot evaluate wall-clock time atomically.
A paused process after precheck may resume after expiry. Session validity and precheck+CAS do not establish strict expiry.
No scheduler implementation can repair this by inventing another lease service.

request_id maps bijectively to operation-scoped idempotency_key under generation/dataset/scope/authenticated owner.
Different operation means different key. Canonical full semantic intent digest binds the mapping.
Global segment dedupe remains a separate guard; successor cannot rekey UNKNOWN old intents to bypass reconciliation.
Adoption has zero additional segment bytes but consumes actual newly allocated metadata/checkpoint/outbox bytes.
Job checkpoint CAS and dataset root revision are distinct; uncertain allocations remain charged until reconciled.

## Limits: measurement plan, not invented production values

All production limits below are UNSET. Frozen schema's individual string sizes are provisional structural review bounds,
not performance-qualified limits. Its unbounded decimal/list dimensions are explicitly not deployable.
Synthetic benchmark sizes and TTLs in tests are TEST_ONLY.

| Limit | Required experiment / approval basis |
| --- | --- |
| Assignment canonical bytes | sweep drain cardinality/token/identity lengths; measure validation/serialization CPU, allocation and transport/authority ceilings |
| Metadata bytes | actual manifest/checkpoint/outbox allocation and authority root-reference sizes; measure fanout and recovery |
| Batch bytes | actual ingestion/research payloads across disk/network pressure; bound drain/lease completion latency |
| Active assignments per worker | concurrent CPU/RAM/network/working-space admission with realistic workloads, queue latency and memory ceiling |
| Capacity max age | perturb load and telemetry delay; measure error between observed and actual allocatable capacity |
| Lease max lifetime | authority failure/suspension/skew/recovery experiments and reassignment availability SLO |
| Reservation / renewal bounds | expiry races, actual physical byte reconciliation, renewal load, transaction operation/byte ceilings |

The supplied envelope_probe.py measures only isolated JSON envelope cost and retained snapshot memory.
It cannot justify lease TTL, capacity freshness, batch throughput, maximum concurrent running jobs or a Consul transaction budget.
No production limit is promoted from a local synthetic observation alone. Joint resource targets/SLOs and Integration Owner approval are required.

## Independent test coverage and limitations

tests/scheduler_design/trace_audit.py is an offline single-scope observed-history auditor, not an authority emulator.
Hand-authored traces inject stale revisions, incarnation changes, expiry, generation changes, no quorum,
resource exhaustion, duplicate effects, invalid checkpoint recovery and both serialized publish/supersede orders.
The auditor trusts supplied atomic-snapshot facts; it cannot prove the source transaction actually captures them atomically.
Real adapter tests must capture authoritative before/after state and receipts, including process suspension before commit.
Pure schedule tests cover Europe/Berlin half-open boundaries, cross-midnight weekday ownership, DST skip/repeat.
Windows requires tzdata; missing timezone data fails closed. Independent tests carry pinned review dependencies.
Workflow agent5-design-tests.yml runs only these fixtures/schema checks; PASS does not establish fleet/runtime acceptance.

## Execution ledger

Ruling: keep frozen spec/schema unchanged while joint wire mapping is pending — prevents an unreviewed schema from inheriting an earlier ACK.
Ruling: test-only auditor consumes facts instead of implementing publication — respects Agent 2/4 ownership; real expiry/atomicity remains unproven.
Ruling: synthetic limits remain TEST_ONLY — local envelope speed cannot establish physical resource or authority limits.
P0 remains joint expiry/transaction protocol + exact runtime base + full API ACK.
