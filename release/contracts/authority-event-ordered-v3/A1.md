# Agent 1 — event-ordered authority v3 review1 scoped semantic ACK

2026-11-06. SCOPED SEMANTIC/COMPATIBILITY DESIGN ACK. No gate automatically changes.

Exact proposal independently hashed and read: AUTHORITY-EVENT-ORDERED-V3-REVIEW1.md SHA256 d9d02baec67d5efbdb3124626d6e9d017cc9d5a2d19025f9293f4cc9f789a8d5.
Traceability review SHA256 66d317091a69817aa6790d0fe3f9d4b9339e2b2c268033ac1990a314883b0880 verified/read; evidence file hash64a83ea87016d756be0eb7b612b11379392763f2522efc29c12d3e02e5484295 verified. Negative historical-search claims remain bounded and attributed; A1 did not audit every original mission attachment or private peer chat.

## Owner requirements available to A1

Direct user original LAN scope requires reconnect, timeout, retry/backoff/jitter, mutual authentication, real-flow budgets and persistence of local limits after LS5 loss. Direct user's Bybit Egress Contract message requires distributed quota reservation, restart-persistent usage/cooldown, retry accounting, failover control and partition safety. Critical exact invariants include “После restart нельзя сбрасывать действующий cooldown.” and “При потере кворума запрещено выдавать новые распределённые разрешения, если нет доказуемо безопасного заранее выделенного лимита.” None of the direct human instructions available in this A1 chat specifies literal wall-clock expiry at Raft majority commit/FSM apply or an exact physical UTC commit scalar.

A1's earlier strict-expiry language and gate-closed Egress drafts are agent-authored proposed contracts, later scoped peer/ROOT design ACKed with gates closed. They are not proof the user required that stronger temporal primitive. Correcting this attribution is appropriate. It must not erase actual provider cooldown/window, certificate expiry, operation deadline or owner work-window requirements.

## Accepted new-profile semantics

The proposed event-ordered profile is compatible in A1's reviewed scope with sole existing Consul authority,2/3 majority, no grants/mutations/dispatch admissions on absent authority, current leader AND exact lease session/index plus generation/grant/resource predicates, atomic all-or-none debit/closure/idempotency and rejection after committed invalidation/revocation even without successor. A paused RPC with committed invalidation ordered before it must fail; a publication ordered first retains its historical receipt/debit. Cached heartbeat/count or caller token possession grants no authority. UNKNOWN is not global NO_QUORUM or definitive rejection.

Ordinary failover cannot reset recovery generation, quota obligations or domain revisions. Partial/unknown session+grant renewal is UNKNOWN, not an extended token. Local databases remain recoverable projections, not a second authority. Every eligibility/GC/allocation mutator must participate in the same reviewed protection protocol; oversized transactions cannot be split into partially authoritative chunks.

Truthful submitted/observed-committed audit fields and authority/domain ordering are acceptable as NEW versioned semantics, without invented exact commit UTC. Existing checkpoint-v1 committed_at_utc cannot be silently reinterpreted. A3/A4 own explicit checkpoint/schema/audit adapter ACK; A1 gives no such domain ACK. This proposal does not automatically alter frozen Egress16606dee... or strict drafts; any Egress successor must explicitly select the event-ordered profile and obtain fresh exact byte ACKs.

## Separate gates that remain mandatory

Civil-time policies are separate: Bybit rolling receipt-window limits, cooldown >=policy/provider minimum, cert/credential expiry and client operation deadlines still require qualified time/uncertainty and persistent accounting. Session invalidation order is not elapsed provider-window evidence. No early cooldown/window reclamation or adaptive increase follows from adopting this profile; timestamp unknown means deny relevant allowance increase. Direct user restart/partition invariants remain intact.

External Bybit does not enforce Consul fence. A charged/admitted process paused before socket write may resume later; event-ordered control publication cannot contain it. Retain unknown send debt/slots, freeze affected canonical NAT scopes across policy/mapping/recovery and block unsafe successor reuse until independent sender/socket containment is qualified. No zero-stale-send or instantaneous partition-stop claim is accepted. LAN fixed byte ceilings likewise never expand on leader loss/restart.

Human/service identity, endpoint factories, exact typed key/session lifecycle adapter, durable bounded roots and real3-voter Linux/Windows failure tests remain unimplemented/unqualified dependencies. Source-policy and probe-budget requirements persist, including inert-bootstrap NOT_RUN versus operational checks. Display freshness, local timer stops and Consul TTL estimates must not be labelled exact expiry-at-commit.

## Verdict and limits

No direct owner instruction in A1's available messages is contradicted by this explicit new profile, provided the retained invariants and separate civil-time/containment boundaries above hold. SCOPED SEMANTIC/COMPATIBILITY ACK for the exact proposal bytes; no A1 concrete semantic change requested. Fresh joint owner decision/new wire artifacts/allocation still required before implementation or gate changes. No inheritance into old ACKed schema, no runtime API/authority/containment/physical acceptance ACK.

No source/schema/physical/network changes or executable tests performed for this review. A1's separate direct-human full-LAN-design approval gate remains pending. Overall DESIGN_REVIEW / NO-GO for operational deployment.
