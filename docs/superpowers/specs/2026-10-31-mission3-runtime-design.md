# Mission 3 runtime and pre-deployment design

Continue the six exact Mission 2 commits. Physical deployment, office machines,
real databases and physical-node updates are forbidden. Cloud-owned disposable
containers and ephemeral hosted CI are permitted. No merge or remote deletion.

## Decisions

Keep Grid as the single fleet/task/rollout authority. Add a node-local module
supervisor in Unified; it is not a second fleet scheduler. Existing v1 PLAN_ONLY
status remains unchanged; `/internal/v2/runtime` publishes actual six-module
process/readiness observations and explicit NOT_RUN physical qualification.

Each ModuleSpec has module_id, version, api_major, dependencies and immutable
entrypoint policy supplied by the verified release/agent. A driver starts/stops
owned processes and supplies release-aware functional readiness. PID/HTTP200
alone is insufficient. Startup is dependency ordered; stop reverses it. Failed
startup rolls back only newly started modules. Durable administrative stop is
never undone by recovery. Restart/backoff is bounded. Dynamic registration and
unload preserve dependency/version contracts and cannot replace running code.

DeploymentAgent bridge: start_release(manifest, release_root), stop_release(),
health_release(release_id). Health returns release_id, release_sha256, ready and
six module entries with exact version and ready boolean. Signed release trust,
node enrollment and node/update permits are separate mandatory checks.

For actual distributed consensus, extend Grid with optional Consul Raft sessions
and consistently read KV fencing; retain existing PG epochs as separate resource
fences. PG-only row leases are not distributed consensus. Consul was chosen over
etcd/ZooKeeper/WSFC for native Windows distribution, HTTP API and lower additional
runtime complexity; actual Windows qualification is still required. Five voters
are tested in a local isolated lab. Configured DCS failure cannot fall back to
PG-only leadership. No cross-resource atomicity is claimed.

PostgreSQL promotion requires a current DCS lease, independently verified hard
fencing of the prior primary and replay through the acknowledged LSN. Unknown
fence/LSN/quorum blocks promotion. Five-PG ANY2 synchronous replication is the
target lab; three-PG ANY1 is only a smoke configuration and cannot qualify
two-node-loss write availability. WAL/PITR, actual restore and lag are measured.

Release v3 extends the existing signed manifest and Grid rollout tables: exact
six-module closure, immutable artifacts, external publisher pin, canary, one
active node transition, exact release-aware health, bounded rollback. Physical
execution defaults to denied; installer defaults to Prepare. Ephemeral Windows
CI execution is separately scoped, never office deployment.

## Verification

Preserve all assertions and original compatibility lanes. Use RED/GREEN tests,
real subprocess readiness/recovery, real Raft voters, real PostgreSQL replication
and restore, native Windows PowerShell5.1/7 CI and pinned Chromium. Record exact
HEAD/tree/hash/run/attempt. Missing/failed/NOT_RUN evidence never counts as PASS.
