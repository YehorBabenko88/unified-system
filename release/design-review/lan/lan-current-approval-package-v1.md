# Current LAN and Egress approval package — immutable review edition 1

2026-11-06. WAITING_EXPLICIT_OWNER_DESIGN_APPROVAL / NO-GO.
This is the current coherent design presentation. It supersedes historical status statements, alternatives left undecided and obsolete Egress front-links in lan-transport-design-20261106.md. That older file and all exact ACKed artifacts remain historical, unchanged. This document asks no new question; the existing single direct-user design approval request remains pending.

## Exact scope and approval state

Primary component base: YehorBabenko88/unified-system branch mission-exec/network-probe-transport-20261105, BASE_SHA b12c6c24eeb2c59aa099f1c516d77508f36b20a6, BASE_TREE 41912cd64982d152417dcf74b250bc056142a450. It is a development base, not an integrated release. Main is not an implementation base. No A1 feature checkout, product code, executable tests or Draft PR exists yet.

Current approved cross-owner Egress design: [egress-wire-contract-v2-review2.json](egress-wire-contract-v2-review2.json), SHA256 16606dee585398ae6d92139ffc1cf2ed37a4d2e08759aaa08f0c3b85958b8049. A2 and A3 exact-byte scoped protocol/design ACKs and ROOT closed-profile approval are complete. Full executable/runtime ACK is false. Earlier Egress v1/v2-review1 and their pending-ACK statements are history, not the current approval state. Their ACKs do not transfer to altered bytes.

ROOT package reviewed at exact 57e8f7524912b52ebbb639bd6d5d4fd5e2961622 (Draft PR22): coordination/bybit-egress-design-freeze.v1.json SHA256 0edf7eed9c4f4d6afc49b7f33bac9d1800ca71fcb86e4e2591c02c9d222a73d1; coordination/ownership.v1.json revision3 SHA256 22150f804b1b3a0d6e2047887585b1b550d189bb410fbc894ef566c553594ebe, independently verified and own scope ACKed. ROOT may publish later packages; no floating latest ref or admission is inferred here.

Own allocated files only: unified_system/lan_transport.py, unified_system/network_budget.py, tests/test_lan_transport.py, tests/test_network_budget.py, docs/network/lan-transport-design.md. Intended isolated branch agent1/direct-lan-transport-20261106 and work/unified-system-lan-agent1 after direct user design approval. Shared contracts, installer, native security admission, Grid authority files and scripts/network_readonly_probe.ps1 remain outside this allocation. ROOT must assign any adapter edit there explicitly. Do not change HA, Scheduler, Storage schemas, Terminan or research modules.

ROOT authorized isolated closed-profile implementation after cross-owner ACK, but explicitly recognizes the separate direct-human full-design gate. User's BASE BRANCH DECISION requires design approval by Integration Owner and user, permits only audit/design/contract analysis/test planning before that approval; later revision3 message explicitly denies final full-design ACK. This remaining human gate is separate from completed Egress owner review. No new permission request is duplicated here or in ROOT.

## Selected proposed architecture

Selected design recommendation is Approach A: application mTLS transport plus the unchanged fixed read-only SSH observer. This is the author's selected proposal for human approval, not a claim that the user selected it. SSH application-subsystem alternative is no longer the implementation proposal; choosing it later requires a new design/ACK. Existing observer contracts are preserved; they are not an application data-stream implementation.

lan_probe_inventory.py admits protected external five-worker SSH inventory and distinct pinned keys; network_probe_transport.py executes bounded fixed observations with journal uncertainty/cleanup; worker_transport.py filters SSH OS environment; network_deployment_guard.py stops current owned deployment when fresh network evidence is missing/changed/degraded. ROOT is consolidating these existing b12 components unchanged on its integration branch. That does not implement new application transport, mTLS, shared budgets, reconnect streams or Egress enforcement.

Application registry proposal unified.lan-peer-registry.v1 has cluster_id, monotonic registry generation, policy/trust digests and exactly six stable enrolled node identities, fingerprints, allowed roles and revisioned endpoint lists. User-provided private IPs remain unverified hints. No raw public IP is stored in this package. Registry discovery reads admitted literal endpoints; no subnet scanning, auto-enrollment, multicast or mandatory DNS/Tailscale. Address changes require admitted revision; certificates/identity remain independent of IP. Old address occupation never establishes peer identity.

mTLS uses dedicated cluster CA trust, required client/server certificates, chain/validity/EKU checks, exact enrolled leaf SHA256 and node SAN URI urn:unified:<cluster_id>:<node_id>. Do not replace certificate validation with claimed frame identity or IP trust. Hostname matching can only be replaced by this explicit identity-binding verifier, never CERT_NONE. Protected file-backed key admission and reliable SAN/EKU parsing still need native/runtime qualification or an explicitly approved dependency; no homegrown certificate parser or committed private key. Provision CA offline; rotate via admitted bounded overlap, revocation and session closure. Authentication grants no application authority.

Proposed registry revocation closes affected sessions within 1 second of local policy notification; endpoint-only revision drains within 5 seconds. Freshness expiry fails closed; static locally admitted policy is not renewed by mandatory LS5 heartbeats. These are design targets, not measured guarantees.

## Connections, framing and bandwidth

Separate control and data TLS connections per peer, bound to authenticated identities and a fresh session nonce, share node/peer aggregate accounting. Frame limits: 64KiB data, 4KiB control payload, 16 streams/peer, 1MiB queued/peer, 8MiB/node. Validate bounded headers before allocation. Receive credit is per stream in cumulative payload bytes, starts zero and is replenished only after consumer releases memory. Grants are session-bound; reconnect drops old credits and does not replay uncertain payloads.

Proposed handshake deadline 5s, idle timeout30s, heartbeat10s, one attempt per peer/two concurrent outgoing handshakes per node, at most12 accepted unauthenticated sockets. Retry uses full jitter over capped exponential 0.25s..30s; stable60s session resets retry state. Auth/policy failures wait for admitted revision, not hot retry. Caller deadline/cancellation bounds waits. DELIVERY_UNKNOWN returns responsibility for idempotent application recovery to the caller; transport supplies no exactly-once delivery or quorum/lease assertion.

LAN bandwidth controls are application-byte token buckets, independent from provider request budgets. Static per-node TX/RX rates/bursts sum within cluster ceilings; no borrowing/reallocation after LS5 loss or restart. Shared local process accounting is required for node-wide claims; process-only buckets are insufficient. A local protected enforcement/IPC component is not a new distributed authority. Production rates, bursts, trusted time/skew and native IPC/key/ACL admission remain unqualified; fixture rates are not production defaults. Restart cannot enlarge ceilings; invalid/missing policy denies. Bytes/retries are charged before socket effects and before ingress dispatch; TLS/TCP overhead is measured separately, not claimed under an application-byte ceiling.

Control has bounded reserved capacity and role/class restrictions; live ingestion precedes bulk within admitted class policy. No arbitrary caller promotion or unlimited control traffic. Bounded queues, credits and deadlines propagate overload to producers; no unbounded buffering or silent dropping. Control latency target in isolated fixtures is p99 queue-to-write<=250ms for1KiB frames under bulk load, with declared samples/window/load; not a network delivery or HA guarantee.

## Frozen Bybit Egress domain

A1 owns transport/enforcement and reservation/usage/cooldown domain ledger; A2 supplies the existing Consul authority/fencing guard; A3 owns costs/endpoints/response interpretation/priority; A5 consumes advisory capacity. No new election, duplicate global limiter or independently mutable authoritative projection.

Frozen contract binds corrected A3 policy FILE SHA256 973f84f87de066d6686dfbe1177dc583637fa819aa21f988303e3a649abae3f1 and BODY digest b3ea69e77ef17b3cd2a894f16df32cb1caba3178efb8814800d4017507e15ca3; policy spec5af7db7f95c3b3df1b4d6e337734a316222b519465a80206b15707bdb2066e20; operation vectors6f261f9ed0c814bd5c90faf2e6c7dbc55b0e5a5457ced6fd4eb09e18b35a726b. These exact external artifacts remain policy-owner files; scoped A1 design/interface ACK is not activation. All policy operations are enabled=false with null validity; unknown operation denies.

Egress mapping is externally admitted and destination/route/time-specific. Same admitted public IP/provider environment shares one canonical IP quota across nodes, binding aliases and applicable hostnames. A reported common IP at ipify for six hosts does not prove Bybit route equivalence or account for unmanaged NAT consumers. Unknown/changed mapping creates no new pool and denies new grants. No network/router changes are part of mapping.

Reserve all applicable rate/window/endpoint/account/connection constraints atomically. Current policy covers only public linear instruments, one-minute klines and exact WS connect/ping/subscribe/unsubscribe, with additive local-safety cap and owned-slot requirement. Unsupported operations, including monitoring time endpoint below, remain denied. Policy body numeric canonicalization stays ascii-int-v1; runtime wire v2 uses checked u63 decimal strings/epoch-ms. No silent conversion of frozen policy digest bytes.

RESERVED, definitive DENIED and UNKNOWN are distinct. Command identity includes operation, authenticated principal and command ID; consume/report IDs cannot collide with reserve. Irreversible consume is charge before possible send, not proof HTTP was sent. Reconciled receipt never authorizes a second send. All retries get new attempt/cost; unknown acquisition is reconciled with original intent before another operation. Attempt revisions are per-attempt, scope changes use all-or-none CAS through existing authority; generation is recovery namespace stable on routine leader failover. Late trusted reporting service may tighten historical superseded-executor obligations without granting new authority.

Usage/slots/max cooldown/adjusted lower caps/observation dedup and protected immutable obligation roots survive restart, policy/mapping/generation changes. Missing roots are not zero usage. Closed gates block every allowance increase: reserve, consume, refund, slot/window/cooldown reclamation, adaptive recovery and frozen-scope reopening. Only verified non-increasing tightening/reconciliation under current authority remains conceptually permitted. Consul session checks are not exact wall-clock expiry; Bybit does not enforce our fence. Strict-time and paused-sender containment are CLOSED/UNQUALIFIED, freeze uncertain scopes across future windows and block unsafe takeover. No live quota activation or real provider send is authorized.

## Existing read-only probe is also a budget consumer

Exact b12 source scripts/network_readonly_probe.ps1 performs DNS and raw TCP443 checks, then Net.HttpWebRequest GET to https://www.microsoft.com/ and https://api.bybit.com/v5/market/time. GET time is public/read-only but still consumes provider IP request quota, response bytes and normal node bandwidth. The script currently has no common acquire/consume/report adapter; SSH admission/output bounds/one call per probe do not enforce aggregate NAT quotas. Its catch path marks failures but does not durably interpret or report rate-limit cooldown. Calling it directly while a policy is disabled would bypass the proposed enforcement.

Required before any activation of this Bybit probe path:

1. A3 adds an exact public-time operation descriptor, cost/scope/response policy and vectors in a NEW policy revision; current six-operation policy does not admit /v5/market/time. A1/A2/A3/ROOT ACK the changed bytes; do not mislabel it as instruments/kline to obtain allowance.
2. ROOT assigns the script/invocation integration adapter outside A1's existing five-file allocation. Adapter must bind authenticated probe service, exact remote executor/incarnation, observed/admitted destination-specific egress and common NAT scopes. Central LS5 reservations alone are not proof of the remote send route or ownership.
3. The sole governed HTTP-send path must perform authority-backed reserve and irreversible consume, enforce all closed gates, bind the exact attempt/operation and report bounded status/headers/unknown outcomes through a current admitted reporting service. Passing a cached grant, boolean or receipt into arbitrary PowerShell cannot create a safe send path; check/send race remains unqualified. No bypass for monitoring, health checks, retries or deployment baselines.
4. Include probe retries/failures in durable quota/byte accounting and cooldown; cancellation/timeout does not refund a possibly sent request. Capture bounded WebException response/header evidence for policy interpretation rather than silently losing throttle state; no arbitrary response body/secret logging.
5. Missing policy/authority/mapping/gate/adapter -> do not issue the Bybit HTTP GET. Report BLOCKED/NOT_RUN through an Owner-approved observation schema, never fabricate api=PASS. Existing network_deployment_guard requires successful baseline connectivity including Bybit; therefore a blocked check stops deployment under unchanged v1 semantics. Do not weaken the guard or claim a complete baseline. A separate configuration-only diagnostic would require explicit versioned schema/Owner agreement.

DNS/TCP reachability alone is not provider HTTP success. Microsoft access is outside Bybit request accounting but still within admitted node byte/connectivity policy; no unapproved provider probes or redirection. ROOT consolidation of unchanged source is preservation only, not probe activation or budget qualification. No script edit or probe execution was performed by A1.

## Integration dependencies and ports

ROOT manifest at57e8f75 is revision3 AUDIT_BASELINE_NOT_INTEGRATED_RELEASE, runtime_admission=BLOCKED. Component bases differ from runtime inventory: A1 b12c6c24..., A2/A4/A5 2df6f5c2..., A3 d537d525..., A6 7ed3708d...; ROOT owns reconciliation/source admission and shared contracts. These pins are not a coherent installable release or permission to cherry-pick dependencies unreviewed.

Required integrations: A2 authority typed guard/Consul transactional endpoint still unimplemented at reviewed source; A3 policy/ingestion adapter incl monitoring-time amendment; A4 chunk/commit acknowledgement, no storage schema change; A5 advisory capacity and overload handling, no job authority; ROOT protected Windows service/key/IPC admission, installer optional-Tailscale policy, source/port/identity provisioning. Control API P0 deny-only review ACK does not supply real identity or Egress API. No direct edits to those modules.

|Purpose|Minimal proposed port|Scope/status|
|---|---|---|
|Application mTLS control/data|TCP7443|Six explicitly admitted hosts/service executable only; collision/provisioning approval pending; not opened|
|Existing SSH observer|TCP22|LS5 to enrolled workers through existing pinned trust; no arbitrary application stream|
|Local bandwidth enforcement|Named pipe|ACL-qualified local clients; no TCP admin channel|
|Provider/public observations|Outbound TCP443|Exact approved destinations/operations through budgets; Bybit probe blocked pending adapter/policy/gates|

No arbitrary LAN-wide rule, multicast discovery, DNS/DHCP/route/firewall/ESET/Tailscale/router change. Runtime is nonprivileged and exposes no network-repair broker. Installer currently requires tailscale in installer_security.py; removal of that mandatory package dependency is ROOT-owned, not satisfied by LAN probe absence of fallback.

## Validation, bootstrap and rollback

After direct full-design approval: invoke implementation planning, create isolated feature from exact b12, edit only allocated files, meaningful tests, review, Draft PR and exact HEAD/tree. Closed-profile work validates bounded schemas, immutable policy/registry admission, identity bindings and conservative failure behavior; it cannot substitute fake providers/clock/authority for runtime qualification. No activation during tests; provider negative tests use isolated modeled or loopback peers with explicit fixture labels.

Required LAN cases: six identities on real TLS loopback; wrong CA/SAN/fingerprint/EKU/expired/missing certificate; IP move/spoof at old address; reconnect/deadline/jitter/cancellation/half-close; malformed/slow/oversized frames; credits/queue ceilings; actual flow byte accounting and control/live/bulk fairness; shared per-node accounting and LS5 loss without ceiling expansion. Windows native key/ACL/IPC and hosted contract CI remain separate evidence.

Required Egress cases are frozen negative_test_specs plus UNKNOWN original-intent reconciliation, no replay send, shared NAT aliases, restart/failover/partition/cooldown, consistent all-scope CAS, closed gates for reclamation/refund, late report from superseded executor, protected roots, no current-service substitution and probe-time unknown operation/disabled policy denial. Artifact/golden-vector checks already performed are not these executable tests. Strict-time/paused-sender gates cannot be opened merely because a mock passes.

Tailscale-independent isolated acceptance requires an environment with no Tailscale runtime dependency, six explicit admitted private peers and normal security policy; office Tailscale stays enabled. Test install admission separately after ROOT policy changes. Physical acceptance remains NOT_RUN and requires mandatory readiness gates, exact plan/hosts/load/evidence/rollback; no agent physical action is inferred from design approval.

Bootstrap provisions protected CA/registry/policy/keys and admitted service identity/IPC outside runtime, verifies exact hosts/ports/read-only baseline and existing narrow allowances. Any missing prerequisite blocks. Rollback stops only owned transport and restores admitted application package/registry/policy; preserves uncertain delivery/quota obligations and reconciles them through owners. Never repairs networking, removes Tailscale, disables security, deletes foreign data or resets provider counters.

## Current evidence and decision

BASE/ownership/freeze/contract hashes verified; A2/A3/ROOT closed-profile design approvals complete. Product code/harness/CI/native/physical acceptance NOT_STARTED/NOT_RUN. No A1 PR or implementation HEAD/tree. P0: direct user full-design approval missing, application/runtime contracts unimplemented, strict-time/containment unqualified. P1: mandatory installer Tailscale dependency; native identity/ACL/IPC and provider route/unmanaged NAT proof; monitoring Bybit adapter/policy amendment; Windows CI and physical qualification. P2: production bandwidth and latency tuning not measured.

This coherent package plus immutable frozen Egress bytes is the concrete current approval material; it replaces historical pending-ACK summaries only. It does not broaden ROOT's freeze into full LAN runtime approval, activate disabled policy or modify any shared schema. Status remains WAITING_EXPLICIT_OWNER_DESIGN_APPROVAL / NO-GO.
