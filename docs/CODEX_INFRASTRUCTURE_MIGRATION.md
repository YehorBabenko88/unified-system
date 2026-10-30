# Codex workstreams for infrastructure ownership (independent Draft PRs only)

A — Grid inventory: find every Grid fleet bootstrap/heartbeat, scheduler, failover/replica, Tailscale, service, PG schema and installer entrypoint. Produce source/tree SHA and a migration matrix: responsibility, safe read-only Unified interface, exact domain semantics to preserve, trust boundary and offline negative tests. No deletion or changes to Grid operational branches.

B — Strattester inventory: discover installer.ps1/ops/bootstrap-node.ps1, Tailscale, cluster recovery, resource manager, scheduler, SQLite/PG owners, job-lease semantics. Separate infrastructure from research-specific scheduling. Publish a read-only inventory design and regression tests in an isolated Strattester Draft PR, no real SSH/winget/firewall/ACL calls.

C — Math + Terminan: inspect Math PR97 bounded evaluation API and Terminan current monitor/UI PRs. Define Math resource/capability contract, read-only fleet/network graph visualization with nodes, verified edges, loads, disks/database sizes, service statuses and management actions that submit operator approval requests only. Do not infer network edges from mere host membership. Preserve Terminan no-order authority.

D — Unified installer: separate Draft PR to design a Windows 11/10 PS5.1/7 inventory and PlanOnly for six initially registered PCs, no write. Signed version-lock; no arbitrary downloads, no untrusted MSI/winget updates or remote command execution. Build capacity/failover/fencing synthetic tests, independent quorum and rollback constraints.

Every agent: exact source SHA, tests and CI run/attempt/job, evidence hash, P0/P1/P2, no merge/deployment. Never change physical machines or override local Windows administrator controls. User-visible network agent must be transparent and managed only under authorized workstation policy.
