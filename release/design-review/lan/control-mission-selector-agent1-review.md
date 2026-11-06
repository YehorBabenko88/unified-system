# A1 mission multiplex and selector review

2026-11-06. SCOPED DESIGN ACK to selector grammar/capacity direction; complete v3 endpoint ABI remains PENDING.

Exact A2 source hashes read and independently verified:
- CONTROL-SYNC-V2-SELECTOR-QUOTA-REVIEW1.md: 6633f15aff9009f02f25431077536331b4a19e6f7052b6177ca69c52b37d755a.
- CONTROL-SYNC-V2-SIX-NODE-RELOCATION-REVIEW1.md: 45e44a3f85524baa9a792f74941f4a8cd76bfedfe5948c5357708f4d20218e3b.
- CONTROL-MISSION-MULTIPLEX-REVIEW1.md: 9e8a65ee65e99be6f8ba34bd5df8c6fefc92dc947852fd58cdce878e1869e55f.

## Closed A1 review scope

ACK exact v2 canonical selector grammar as a bounded design: four ordered fields, explicit ~ null, canonical UUID/id, no aliases/percent/plus/extra/duplicate/empty fields, raw512-byte snapshot query bound; cursor-only events grammar2055 bytes and no caller-authorized context. Grammar parse success is not registry/RBAC admission. Require actual proxy/raw-query preservation before endpoint qualification. No parser/backend call or source edit performed by this review.

ACK the explicit label DEGRADED_ENGINEERING_ONLY for v2 max2 streams/principal; a six-node CONTROL view can contain all six node resources but is not proof six simultaneous clients are served. Two windows plus DATASET is not served by that cap. No polling, principal aliases or hidden channel sharing may disguise that failure. This degraded profile cannot pass final mission multi-window acceptance.

ACK v3 mission capacity as a proposed minimum design target: one operator's six enrolled-node CONTROL clients plus two additional operator CONTROL windows plus one DATASET =8 physical connections/9 logical subscriptions. Node/operator CONTROL capacity is reserved; dataset multiplexes onto an operator connection, not a ninth connection. Separate authenticated views/cursors/observations remain independent. No LAN64KiB framing mapping is inferred; HTTPS admission must be separately qualified. Capacity is not measured or guaranteed until real multi-producer/client tests pass.

ACK sole existing Consul finite slot admission direction, atomic connection/logical-slot binding and durable receipt, no process-local global quota, no implicit leadership/domain lease transfer from UI relocation. Released session/heartbeat absence is not proof an old stream cannot deliver. Slot reuse retains containment and qualified global accounting dependencies. Transport-control priority has hard byte/queue caps and cannot drop ordered data deltas silently. Slow socket freshness expiry is not guaranteed notice delivery.

## Remaining concrete v3 ABI decisions before full protocol ACK

1. Publish one exact new schema and route grammar for connection/open/subscribe/snapshot/unsubscribe/drain and version negotiation, with idempotent command/result keys, request/response fields and error/capacity reasons. The reviewed prose explicitly leaves verbs/frame schema unsettled; A1 cannot claim full endpoint ABI ACK from it. Every mutation of admission metadata must use current authority and authenticated role; no request side effect from unauthenticated query.
2. Define principal association explicitly. Eight connections may be authorized to one operator quota owner while node services have separate machine/service credentials. Bind quota_owner, connection authenticated principal kind, enrolled host, application/session identity and role through an owner-admitted delegation/provider mapping. Machine certificate or a node label cannot authenticate the human or claim another operator's reserved slots. Do not create fake aliases to multiply quotas. Node-slot and human-window grants need exact distinct schema types.
3. Pin child payload schema hashes and mux header types/limits. Define channel_sequence per connection epoch, subscription/delivery epochs, gap/duplicate/old-epoch behavior and canonical selector encoding for subscribe. Mux header overhead must be included in wire cap, not silently fit a132096-byte v2 payload already at its maximum. Bound aggregate encoder working memory separately from queued bytes; two2MiB encoders plus8MiB queued/principal are different admitted resources, not one interchangeable number.
4. Freeze principal-wide byte/rate and connection-attempt/backoff admission plus global memory/encoder ownership across producers, not only slots. Existing v2 heartbeat/queue design ceilings need explicit v3 selection. Safety notice lane remains bounded; never infer notice delivery on stalled socket. No provider-request traffic is triggered by UI subscribe/retry; any future probe must use separate Egress policy/adapter.

These are remaining ABI/provider definitions, not rejection of the stated mission capacity or existing canonical selector proposal. A2/A6/ROOT must jointly publish exact bytes before full v3 protocol freeze. A1 gives no identity/root/retention/time/provider runtime ACK. Native/safeguard and independent test work is unaffected.

Qualification NOT_RUN by A1: two producers/nine subscriptions, claim races, suspended old streams, byte/RSS/fairness/latency, selector/proxy ambiguity, reconnect/relocation and Windows identity. No physical action, network mutation, runtime/source/shared-schema change or automatic user-design approval.
