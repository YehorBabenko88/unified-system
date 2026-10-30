# A: Infrastructure migration inventory and disposable ledger

Admission: PLAN_ONLY. No remote connections, processes, service/ACL/network changes,
production DB operations or orders. Existing Grid/Strattester implementations are preserved.

## Fresh source audit (2026-10-30)

GitHub PR list and freshly fetched pull refs, inspected with git show (no execution):

| Source | PR / immutable head | Tree |
|---|---|---|
| Grid | #249 bf9f108b6777085d6725675eac778d61ec55f42b | c8e8131e353956436b981b6b9857a4c5250460a4 |
| Strattester data-first scheduler | #62 bceb60fbee478b03a73fdf68f85291cab3521d8a | 576f90713955e156e55d3eb9384bbc34b660253b |
| Unified frozen PR4 | b8facc028e00493d8423d15280f87c2047c2b63b | 9ad0c3811711b8f243454b3d86302fa9093baa1a |

Strattester latest listed PR63 is Math contract 62fe967cf7b2358cf8dd7035218db566e566a603;
this audit deliberately inspects the infrastructure/research scheduler PR62, not an assumed merged stack.
Pins prove inspected Git bytes only; they do not authenticate physical machines or independent owner approvals.

## Migration matrix

| Source implementation | Preserve source semantics | Unified interface / phase | Offline negative tests / cutover blocker |
|---|---|---|---|
| Grid grid/resources.py NODE_ID, local_storage_usage | Persisted ProgramData identity; storage measurements; bootstrap fallback is not verified identity | approve_node + heartbeat epoch/sequence, status_snapshot; disposable phase 2 | Unknown node, replay, epoch rotation, missing telemetry; P0 owner-authenticated identity absent |
| Grid grid/enrollment.py create_enrollment_token, normal_enrollment_allowed | CONTROL one-time expiring tokens, PILOT/NORMAL expansion gate, revoked credentials | Approval reference only in model; never imports live enrollment | Reject missing approval; P0 independently signed scoped approval adapter pending |
| Grid grid/fleet_control.py fleet_stop/fleet_resume/_registered_targets | Global STOP dominates local intent; offline credential registry must not become empty; preserve pre-stop operator state; DELETE waits for purge acknowledgments | Infrastructure drain only, no domain STOP/DELETE migration | Drain blocks new placement; P1 domain command/ack adapter remains source-owned |
| Grid grid/scheduler.py weighted_assign/stabilize_assignments | Learned symbol cost, CRITICAL pressure exclusion, sticky assignments and 10% voluntary churn | Source retains market placement; Unified leases generic capacity cumulatively | Oversubscription, zero/NaN capacity; P1 shadow comparison and domain callbacks pending |
| Grid grid/control_plane_failover.py QuorumPolicy | ISOLATED_LAST_NODE permits observation but mutations=false | elect/validate_lease durable term with strict majority of configured model voters; no isolated mutation authority | Lost majority, old term, leader expiry; P0 real external fencing/quorum unavailable |
| Grid installer/bootstrap.ps1, enroll.ps1, configure-tailscale.ps1, provision_postgres.ps1, switch-release.ps1 | Installation, PG18 schemas, release rollback and owner-managed identity remain source scripts; not executed | E installer workstream; no shell invocation in fleet model | P0 Windows G0/owner approval; P1 PS5.1/7 physical compatibility NOT_RUN |
| Strattester strattester/engine/resource_manager.py decide_resources | available RAM/disk absolute floors, checkpoint_release, pause, throttle; research owns heavy-job policy | heartbeat absolute available resource vector + conservative 15% reserve | Resource pressure and finite input tests; P1 module-specific resource thresholds/callbacks pending |
| Strattester strattester/engine/scheduler.py + persistence/sqlite_state_store.py | BEGIN IMMEDIATE claims, lease_owner/token, resource_key exclusion, renew and CAS transitions | submit/place/validate_lease generic infrastructure planning only | Concurrent same-job idempotency; mismatch rejects; P1 source lease bridge and resource_key mapping pending |
| Strattester runtime/cluster_recovery.py reconcile | Defer reassignment until old lease expiry; prefer CAS; terminal jobs unchanged | Higher term/identity revokes validation but cannot reissue until prior modeled expiry | Split brain, restart, stale heartbeat; P1 domain checkpoint/result acknowledgment pending |
| Strattester ops/bootstrap-node.ps1, install.ps1, remote/tailscale.py | SSH/Tailscale role and firewall policy remain owner-managed | E inventory/plan, no automatic invocation | P0 no physical enrollment/security qualification |
| Both databases/backups | Separate Grid/Strattester schemas and research datasets remain source-owned | Disposable SQLite ledger backup/restore only | DB loss, actual SQLITE_FULL rollback, restore requires fresh leader/heartbeat; P0 external restore fencing and real PG18 recovery NOT_RUN |

## Public Python contract

`FleetControl(path, voters)` uses a disposable SQLite file; `approve_node`, `heartbeat`,
`elect`, `submit`, `place`, `validate_lease`, `drain`, `snapshot`, `status_snapshot`,
`backup`, `restore`. Explicit integer seconds in core; status_snapshot accepts milliseconds.
Resources are available CPU units, RAM bytes and disk bytes using one consistent caller contract.
Jobs reserve resources cumulatively, including unexpired leases from older terms/identities.
No automatic rebalance; existing healthy placement remains sticky. `avoid_domains`
is an explicit placement requirement, not proof of independent failure domains or N+1 HA.

`status_snapshot(now_ms)` returns bounded-meaning display data: nodes list with
id/epoch/sequence/state/zone/last_heartbeat_ms, modules=[], unknown cpu/memory/disk
utilization and db_sizes=null, identity_verified=false, available_resources;
links=[], databases=[], alerts=[] (no inferred network edges or fabricated DB sizes).
Consumers must treat unavailable observations as unavailable, never healthy zeroes.

Caller owner_approval and votes are synthetic assertions, NOT authenticated receipts.
Single-file transactions are not distributed consensus. Modeled leases cannot execute
work and every receipt says execution_authorized=false. Backup restore resets leader,
leases and heartbeat admission and changes token incarnation; a live deployment would
also require independently durable fencing against outstanding pre-restore work.
Read snapshots use SQLite mode=ro. Mutations mode=rw reject database loss instead of
silently recreating it. SQLite connections close deterministically on Windows.

## Validation and remaining admission

Eleven new tests include fleet sizes 0,1,5,6,7,12; cumulative budgets; duplicate concurrent
placements; old epoch/sequence; identity rotation; stale/offline heartbeat; clock rollback;
missing quorum; stale term; lost leader; old lease expiry before reissue; drain;
restart; DB loss; actual disposable SQLite page exhaustion; backup/restore invalidation;
persisted authority tamper rejection and unavailable display fields. Full existing suite also runs in hosted CI.

P0: authenticated external authority/fencing, owner-approved enrollment, physical G0,
restored-host fencing, real failure-domain/quorum independence and PG18 restore admission.
P1: read-only shadow comparisons, domain lease/cancellation/result adapters, workload quotas,
telemetry authenticity/freshness channel, bounded journal retention, phase3/4 owner cutover.
P2: richer placement scoring/locality, controlled rebalance, module labels and DB metrics.
No source deletion, cutover, live deployment or merge is proposed.

SOFTWARE: disposable model verification only. SOURCE_PROVENANCE: exact source bytes inspected;
owner authentication NOT_EVALUATED. PHYSICAL: NOT_RUN. PRODUCTION: NO_GO.

