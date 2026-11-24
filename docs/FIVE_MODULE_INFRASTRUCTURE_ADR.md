# ADR-004: Unified owns infrastructure and fleet (design, no deployment)

## Five independently operable repos
- unified-system: sole **infrastructure authority** for enrollment, machine identity, dependency inventory, release/DB provisioning plans, network overlay, fleet lifecycle, scheduling leases, leader election, snapshots/backups, recovery and audit. Owns node registry and infrastructure schemas. Controls are separated from data-plane operations.
- bybit-cluster-grid: exchange ingestion, live book/tape, market features, Grid research/strategy and market work execution in separately authorized modes. Retains domain placement *requirements* and job execution, but fleet authority moves behind Unified API.
- strattester: historical datasets, backtesting, models, training, run provenance, checkpoints and research jobs; asks Unified for compute leases, but owns research semantics.
- math: numerical algorithms, formal research, validation, mathematics evaluation; independently callable by versioned Math API.
- Terminan: read-only user interaction, topology and monitoring, independent local UI. Never owns orchestration, service creation, database mutation or trade keys.

## One first-machine bootstrap
1. A **read-only inventory/PlanOnly** checks OS edition/version, CPU/RAM/disks, Python/PowerShell/Node/Git, OpenSSH, Tailscale, DB engines and their actual instances/ports, compatible package digests, host/network/ACL conditions, backups and recovery requirements. Existing installation is PRESERVED, no unconditional upgrade.
2. Produce a signed owner-reviewable desired-state plan: packages, exact versions, disk allocation, services, DB schemas/tables, directories, firewall/Tailscale policy, identities and effects. Show delta and rollback limits before approval. No force install, no live DB DDL from initial observer.
3. After *separate* authorization and independently qualified Windows security gates, atomic staged installer applies narrow approved mutations and records irreversible effects. Idempotent reconcile, no blind reinstall/overwrite. Maintain per-module runtimes and per-database ownership.
4. Launch read-only Terminan from an independently verified release so operator can inspect completed and outstanding steps. Even if module backends are absent, Terminan remains available and labels them UNAVAILABLE.
5. Enroll remaining five owned office PCs separately via verified operator bootstrap/SSH or owner-approved tagged Tailscale enrollment, then future approved nodes automatically. Auto-discovery is observation, not authorization to install on an unknown machine.

## Network and user separation
Use Tailscale's Windows system service with owner-managed tagged device identities, tailnet grants/ACL policy, key rotation/revocation and machine-level administrative controls; alternatively host-managed WireGuard/SSH where appropriate. A regular Windows user should have no administrative rights to the service/control keys. **Do not use stealth, hide processes, intercept user sessions, or prevent administrators from disconnecting their own equipment.** Windows OS admins retain ability to manage connectivity. Configure non-admin access according to vendor-supported device policy, maintain transparent endpoint inventory, consent and audit. Never embed reusable auth keys or exchange secrets in the UI. Remote administration only via separately authorized identities, roles and policy.

## HA and scheduling (office starts at six)
Fleet registry has machine_id independent of hostname/IP; enrollment lifecycle DISCOVERED -> APPROVED -> ENROLLING -> VERIFIED -> ACTIVE -> DRAINING -> RETIRED/QUARANTINED. Identity, attested heartbeat epoch, capability report, scheduler pressure, disk budgets and source ownership tracked independently. Heartbeats have TTL and monotonic generation. Missing heartbeat = SUSPECT -> OFFLINE, never immediate deletion.
- Lease-fenced task placement uses workload requirements, normalized CPU/memory/disk/network telemetry, headroom, data locality, labels and module caps. Sticky assignment + limited voluntary churn; emergency drain only within hard resource and safety constraints.
- Separate replacement replicas across different failure domains; N+1 reserve is a capacity constraint, never a guarantee. Nodes report actual available RAM/disk, not guessed capacity.
- All mutating leadership requires quorum and an external durable term/fencing token; network partitions with no quorum must become READ_ONLY/NO_LEADER, **never** execute Grid actions. Previous Grid isolated-last-node observation is NOT authority.
- When nodes are added: qualify, warm data, start with read-only health, then explicit pool admission and rebalance. On removal: DRAIN, checkpoint, handoff, verify, revoke secrets, retire; sudden failure waits for lease expiry and required quorum before reissue. Never double-run side-effecting tasks.
- Six PCs do not guarantee fault tolerance if all rely on one switch, power source, Internet connection, single DB, single disk or a lone coordinator. Real HA requires independent replicas, durable quorum, failure-domain mapping and tested restore.

## API ownership and compatibility
Unified /internal/v1/infrastructure/capabilities, /nodes, /topology, /resources, /storage, /databases, /plans and /operations are bounded read-only discovery. Mutations use independently authenticated scoped command APIs, explicitly approved desired-state version, owner actor, expiry, idempotency key, expected-state, lease fencing and audit receipts; no mutations through GET.
Domain modules request resources via job submission/lease APIs with quotas, callback receipts and cancellation. Push events use producer epoch + sequence + checkpoint; gaps require fresh snapshot. If Unified is offline, each module continues its safe autonomous local operation (research/offline UI/local math); distributed placements and infrastructure mutations suspend.

## Migration ownership; NO DELETE
Phase 1 inventory existing Grid/Strattester installers, fleet, scheduler, node registry, Postgres and failover contracts. Phase 2 build Unified authoritative equivalents, offline tests and adapters. Phase 3 shadow read-only compare placement decisions and topology. Phase 4 individually authorized per-component cutover after exact-head CI, physical G0 and owner approval. Phase 5 deprecate *only duplicated infrastructure* in source repos; retain domain scheduling inside modules. Never blindly move migrations or delete existing installer files before data/owner migration is demonstrated.

## Explicit current admission
PLAN_ONLY. No installs, service or ACL changes, Tailscale enrollments, firewall edits, DB creation/migration, network changes, physical PC operations, live orders, or PR merge. This ADR is architecture, not executable physical readiness.
