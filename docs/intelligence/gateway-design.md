# Intelligence Gateway — isolated preparation slice

Owner directive: release/owner-directives/intelligence-gateway-20261107.txt.
Root base: 55ebd47 (immutable complete SHA in ownership registry). User approved
Gateway design direction and isolated implementation after ownership ACK. ROOT
owns only the new paths below; no existing shared contract is changed.

## Decision and alternatives
Extend Python Unified with a pure contract/preparation facade first. A new service
or generic callback dispatcher would duplicate control and let arbitrary adapters
bypass admission; do not add those. Register authenticated MCP tools only after
native client identity, per-tool policy, quotas and owner APIs are approved.
This is an implementation staging decision, not owner approval of a new wire ABI.
No MCP server, credentials or client registration is configured by this slice.

## Reuse matrix
| Existing mechanism | Reuse boundary | Current limitation |
| --- | --- | --- |
| control_api_readonly.ControlAPIReadOnlyApp | public capabilities / denial pattern | not authenticated data API |
| control_mux.http_api.ControlMuxRuntime | native admission + command reconciliation | client MCP identity / research tools not mapped |
| node_supervisor_v2 / node_task_journal | node-local operations and receipts | not research authority or client auth |
| mission_controller | development context and exact source/CI claims | records never grant node operations |
| ci_queue_controller | archived bounded CI capture | no network collector |
| storage contracts / ObjectStore / Storage V3 owner | manifests, integrity, publication | actual admitted registry/closure still unavailable |
| Grid A3 market data / book cut proposal | source identity, historical causality | no approved Gateway query backend |
| A5 Assignment + A2 authority | job admission, fencing, cancellation ownership | no actual research dispatch adapter yet |
| Strattester existing paper ledger | execution/results/cost accounting | never introduce another ledger |
| Math / MetaAnalyse | numerical/statistical jobs | no new research core; native Math blocked |
| Terminan A6 Sync / Operations | authenticated visualization | no Gateway artifact route yet |
| immutable release / installation plans | later deployment admission | PLAN_ONLY, no activation |

## Implemented local API
catalog(): proposed 34 logical names, each runtime BLOCKED. This is documentation
and local discovery, not a claim that Codex sees installed MCP tools.
prepare_query(dict): closed v1 metadata, source-pinned dataset reference, explicit
instrument version, strict UTC half-open range, bounded limit/offset. Returns
NOT_EXECUTED, no rows, UNKNOWN coverage/gaps, UNVERIFIED integrity/units/source.
Offset is bounded preparation metadata, not an approved production cursor ABI.
prepare_research_plan(dict): closed version, periods ordered/disjoint/in range,
explicit fidelity, cost strings, Math configuration digest, seed/resources;
returns content-addressed NOT_SUBMITTED plan. No experiment/job is persisted.
Canonical preparation JSON uses sorted keys, ASCII escaping, compact separators,
no NaN; SHA256 binds exact canonical bytes. It is separate from C3/Storage V3.
runtime_call(name,arguments): always blocks before accessing arguments, including
callables, credentials, approval text or claimed roles. No backend callbacks.

## Identity / RBAC matrix (required future composition)
| Level | Required gate | Current admission |
| --- | --- | --- |
| Observation | native authenticated scoped principal + per-tool disclosure | unavailable |
| Research | previous gates + quota + owned immutable request + fencing | unavailable |
| Operations | Control API policy + explicit approvals + release/Node admission | unavailable |
No principal/role/authority field is accepted in preparation contracts. These
are untrusted local inputs, not minted identities. Retrieved hypothesis text
remains data. API errors contain closed codes and never echo input or secrets.
No arbitrary shell, raw endpoint, path, order, service or process execution API.

## Remaining deliverables / integration order
Owner ACKs and exact immutable adapters first; then per-tool client admission,
resource/rate budgets, audit sink and redaction; admitted Storage query/coverage,
A5 research dispatch and owned cancellation; existing immutable experiment
registry binding; A6 visualization references and observer event contracts;
MCP transport registration; isolated actual-engine E2E; independent historical
E2E only after provider/data admission. No model-created market/result payloads.
Runtime malformed response validation, durable job reconnect, cancellation,
reproducibility and concurrent experiments have NOT been tested in this slice.
No synthetic engine/ledger stands in for absent actual owners.

## Rollout / qualification
New stdlib tests and exact-source Windows/Ubuntu workflow only. Independent A8
review requested after publication. No actual-engine E2E, authenticated MCP,
Windows Home/Pro, service, physical, provider or runtime PASS claimed. No install,
network changes, main merge or real trading. MASTER MISSION IN_PROGRESS / NO-GO.
