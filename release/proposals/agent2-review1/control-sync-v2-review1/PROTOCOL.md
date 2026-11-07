# Control Sync v2 — output-only proposal, review 1

Exact producer/consumer ACK: PENDING. No product source changed. V1 and P0 deny-only ABIs remain frozen. `control-sync-v2.schema.json` is a new major envelope, not an alias for Terminan v1 or a claim of existing endpoints. Golden vectors and validation are MODEL_ONLY; no runtime adapter, authenticating provider or Consul producer is implemented here.

Proposed routes: authenticated `GET /control/v2/snapshot` and `GET /control/v2/events?cursor=...`; errors use the v2 error envelope at this version boundary. No command route is opened by this proposal. A new exact domain schema registry and identity-provider contract require owner ACK before implementation.

## Revision and authorization semantics

`metadata_revision` identifies the global logical control revision that produced the last visible change of this projection, not the current global head, Raft term/index or a local snapshot counter. It may jump because hidden resources changed between visible changes. Hidden-only changes preserve this view's revision, root and sequence; an observation can therefore confirm the unchanged projection at a newer read barrier without requiring an invisible delta. The opaque authority_read_ref binds the actual verified barrier and projection derivation; the view revision must never be treated as the barrier's global head counter. `change_sequence` is durable and contiguous within one authorization view: each visible atomic delta increments it by one. Hidden changes do not create empty visible deltas. Producer atomically persists view delta, resulting root and cursor progress with the committed projection. Crash/replay must never reuse an existing sequence for different bytes.

The context tuple binds cluster UUID, recovery generation UUID, stream UUID, authorization `view_id` and scope. View ID must bind principal/capability-policy revision and selectors without leaking hidden data. Policy change, generation/stream change or selector change requires a fresh authorized snapshot; old cursor is rejected. Never silently continue a cursor in another view. Cursor is opaque, integrity protected and bound to this tuple, retention position and root. Do not accept arbitrary client-supplied view IDs as authorization.

Snapshot is an atomic authorized projection with a matching consistent authority observation. Changes require exact previous root and previous sequence, next sequence = previous+1, nondecreasing metadata_revision, unique resource identity and 1..100 combined upserts/deletes. Apply the entire validated change or none; reject unknown domain schema hashes. State-root algorithm/canonicalization and exact domain schemas remain an explicit ACK dependency; the envelope's generic resource.value does NOT establish domain validation or a production root algorithm.

Snapshot limit is 1000 resources; oversized result is an explicit error until an atomic pagination protocol is approved. Retention minimum proposal is 600 seconds. Retention bounds must survive producer restart; a cursor before retained history yields code RESYNC_REQUIRED with reason CURSOR_EXPIRED. Never fabricate a contiguous suffix.

## Liveness versus authority observation

Liveness contains only connection ID and context. It cannot change revision, sequence, cursor, root or LIVE status. A socket heartbeat proves the connection answered, not majority authority or current state.

A separate authority-observation covers one exact context/root/sequence/revision at a verified consistent read barrier. It is accepted only for the consumer's currently accepted state. An observation for an older root cannot refresh a newer projection. QUORUM_CONFIRMED needs a verified producer identity, matching durable projection and real consistent read evidence; fields and timestamps alone prove nothing. See [Consul consistency semantics](https://developer.hashicorp.com/consul/api-docs/features/consistency).

Observation timestamps describe the read interval and a bounded display freshness window with explicit clock uncertainty, not commit timestamps or proof that no write happened after the barrier. Consumer validates interval ordering, context/state equality and its approved clock/freshness policy. Until that policy/provider is ACKed, it cannot derive LIVE from this proposal. Lost RPC, timeout or inability to verify quorum means UNKNOWN; NO_QUORUM requires authenticated positive evidence, never merely a timeout. Both expire LIVE and preserve last known data with its stale status. Neither status authorizes mutations.

## Error envelope and version boundary

V2 errors require `schema`, nullable request_id, enumerated code/reason, retryable, nullable decimal-string retry_after_ms and evidence_refs. They intentionally differ from frozen v1's schema_version/integer retry fields and P0's null-request deny profile. No coercion or fallback between versions. A pre-auth failure need not fabricate cluster/view context. References must be authorized opaque evidence IDs; no secrets or cross-view paths.

JSON Schema validates structure and exact decimal-string u63 range. Runtime must additionally validate relationships, roots, signatures/identity, cursor MAC, timestamps, resource uniqueness, payload byte/depth limits and domain schemas. Review vectors cover 17 bounded structural/transition checks including hidden metadata jumps, no heartbeat refresh, gaps, authorization-view changes, duplicate resource and stale observation. They are insufficient for production acceptance.

## Required ACK and implementation gates

A6: exact envelope/routes, separate frame handling, major-version adapter, no v1 mutation. ROOT/A2: identity and consistent barrier provider, durable projection/journal design, root canonicalization, scope disclosure and ownership allocation. A3/A4/A5: exact domain resource schema hashes, projection invariants and bounded sizes. Security owner: principal-policy binding, token transport, cursor protection and failure responses. Integration Owner: allocate concrete Grid files and router changes. This package requests review; none of these ACKs is implied by schema validation.

