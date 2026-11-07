# Node Supervisor V2 implementation plan

> For agentic workers: use subagent-driven-development or executing-plans. Each owned module has its own RED → implementation → GREEN → independent review boundary.

**Goal:** Extend existing Unified with durable local operations, development context recovery and bounded read-only CI observation, without adding authority or physical installation.

**Architecture:** Reuse Journal hashchain/CAS, existing protected Windows service/installer boundaries, Scheduler/Consul interfaces and LAN components. Development tasks and node operations remain separate. New deployment adapters only prepare immutable plans; effects remain blocked pending actual native admission.

**Tech stack:** Existing Python 3.12 stdlib, SQLite Journal; existing Windows native/service code. No dependency installation required for pure component CI.

**Spec:** owner directive 794b7802-d3e9-43e5-8ab6-333d6fad9be7; original archived at release/owner-directives/supervisor-v2-20261107.txt.

## Global constraints

- Base 49a970270570548e5d4f0c5a440d30e238bb21f1; each contributor owns separate feature branch/worktree/Draft PR.
- DEVELOPMENT / ISOLATED EXECUTION / PLAN_ONLY FOR PHYSICAL OPERATIONS.
- No second consensus, arbitrary shell, privilege escalation, network policy edits, real orders, main merge or physical install.
- Existing P0 owners A1–A8 remain active; their shared files are read-only to this feature.
- Consumed Math run 42352374979 never rerun; its source and attempt remain fixed.
- Local integrity/status records do not authorize execution; all native and physical axes stay independently unknown/blocked.

## Review focus

- Stored AUTHORIZED, approval references or successful CI cannot become native authority.
- Crash after a possible effect must preserve UNKNOWN_OUTCOME and original intent, never blindly replay.
- Existing/foreign/corrupt SQLite data must not be silently adopted or repaired.
- Backoff and idempotency survive restart; clocks do not replace fencing.
- Plans cannot launch services, register tasks, drain workers or remove/restore data.

## Owned implementation tasks

- [ ] Supervisor owner: typed node-operation receipts over existing Journal; closed allowlist/state graph, duplicate/restart/corruption tests; read-only disposable component only; explicit unsupported effect boundaries.
- [ ] Mission owner: versioned development-task schema, immutable source/scope, bounded DAG/evidence/work history and read-only projection; no node-operation conversion.
- [ ] CI owner: bounded observation snapshots and durable poll schedule; no write/rerun/dispatch API; exact run/attempt/head identity.
- [ ] Root: real capsule integrity-to-deployment PLAN_ONLY adapter, sequential topology and rollback prerequisite plan, existing inactive installation plan reuse; no new privileged actuator.
- [ ] Root/A6: Operations Dashboard projection contract after exact producer ACK, separate local health/authority/release/integrity/replication axes; unavailable facts remain unknown.
- [ ] Per owner: fresh exact-source Windows/Ubuntu workflows and archived RED/GREEN; never waive Home/native gates.
- [ ] A8: independent source/negative/integration review after exact candidate SHAs.
- [ ] Root: integrate compatible candidates into Draft only, evidence-index raw Git bytes, keep release manifest provisional until full gates.

## Physical commissioning

Not authorized. Future order: disposable Windows → LS5 isolated → PC4 → PC3 → PC2 → PC1 Home → LS7 Home; one node at a time, real quorum and rollback/backup checks required at every coordinator update. No automatic destructive rollback; Tailscale retained.
