# Supervisor V2 bounded reuse matrix

Source base: `49a970270570548e5d4f0c5a440d30e238bb21f1`. This is a targeted source inspection, not another six-repository audit.

| Existing module | Actual implementation reused | Boundary still open |
|---|---|---|
| supervisor.py::Supervisor | Pure handoff state/snapshot | No process/service execution; three-module legacy view is not six-node health |
| journal.py::Journal | SQLite append/CAS/hashchain and bounded records | Local single-writer consistency only; protected directory/native authority separate |
| fleet_control.py::FleetControl | Existing disposable planning model and validation concepts | Caller votes are not Consul/native authorization; never elect a replacement leader |
| installation_transaction.py::source_plan | Actual immutable capsule byte verification and inactive staging plan | Source origin/capacity/native authorization not evaluated; no activation |
| installation_service.py::service_plan/ServiceResource | Existing planned/manual-stopped service resource path | Real service identity, native gate and explicit owner phase required; no auto registration |
| service_entry.py / service_bootstrap.py | Existing source-pinned protected entry | No new service entry or automatic pin replacement by Supervisor |
| service_actuator.py / service_activation.py | Existing scoped actuation/revision controls | No new permission from a task, CI success, digest or callback |
| network_deployment_guard.py | Existing stop-current-operation/no-reset interlock | Its Bybit observer must not run without common egress/quota admission |
| Current A2/A4/A5 components | Existing authority/storage/scheduler ownership | Supported positive native adapters still absent; do not use FleetControl model as fallback |
| Current LAN / Control Mux / Terminan | Existing framing, closed native factories and read-only UI direction | Real native bridge, committed stream and operations projection mapping pending |

Node Supervisor, Mission Controller and CI Controller share the existing local Journal engine but use distinct typed record namespaces; they do not reinterpret each other's records or legacy states. A development task cannot be cast to an executable node task. Windows service prototype reuses existing protected service lifecycle; physical installer remains PLAN_ONLY. LAB unsigned integrity remains separate from TRUSTED_RELEASE, which stays BLOCKED_NO_TRUSTED_PUBLISHER.

## Architecture decision

Extend the existing local journal with isolated typed receipt namespaces. Keep development work-item records separate from node intents and keep all operational authority in the existing Consul/native admission path. New Root deployment preparation calls the existing actual capsule verifier and inactive installation source_plan; its execute method always denies. The Windows service prototype revalidates an existing stopped-service plan and exposes NOT_OBSERVED/NOT_NATIVE_QUALIFIED; it does not create, register, start or stop a Windows service. Coordinator and Home worker roles remain separate.

## Current software scope

This slice provides executable PLAN_ONLY preparation, not a qualified running Supervisor service. Only two local journal observations are currently offered by the separate Supervisor component; eleven allowlisted operations still require their actual safe handlers/adapters. Full Windows startup/logoff/restart, Pro/Home, protected journal ACL, service identity, native key/IPC, active update/rollback and actual health qualification remain pending. No approved rollback follows from a backup hash reference. The queued hosted CI and independently tested local components are separate evidence categories.
