# Native Control attachment handoff — LS5 local preparation

This describes existing executable APIs, not a new admission profile. It adds no listener, installer, identity provider, record issuer or consensus. Root owns native bridge/raw front and commissioning. Source review: Root189a00ed41b0ca0cd5661c1602f408d3d5fb730b/tree37ee20113154d43b1a3046cc91641bbc56810666; integrated Mux08d6f01d94feb44a17338be8ef3f8871995c284a/tree18db861452f82978806a3f4d81a70b033ce53b02; existing Grid58cfe0f51bc05bb0ee2ed09368a9b64679358c63/tree18d10d013ca111af63668842f3a22c646a7f1da5. Actual source pins are in A2 outputs/NATIVE-CONTROL-ATTACHMENT-SOURCE-189A00E.json. No native/runtime acceptance is inferred from this document.

## Usable existing code

The following composition uses real existing implementations. Arguments come exclusively from Root's separately admitted in-process composition. This is not an authentication factory, does not provision anything and does not qualify a supplied Python object. It must not be exposed as public configuration or invoked with a fixture provider.

```python
from unified_system.control_mux.commands import RawRequest
from unified_system.control_mux.consul_store import MuxAuthority
from unified_system.control_mux.http_api import ControlMuxRuntime


def connect_existing_components(*, grid_authority, generation,
                                native_admission, existing_lease_provider):
    # Root supplies its actual admitted provider and existing Grid instance.
    # No acquire/renew/election, credentials, listener or process is created.
    store = MuxAuthority(grid_authority, generation, admission=native_admission)
    return ControlMuxRuntime(store=store, admission=native_admission,
                             leader_provider=existing_lease_provider)


async def dispatch_from_root_front(runtime, *, method, canonical_path,
                                   raw_header_pairs, exact_body,
                                   bridge_owned_connection):
    # The front must bound framing before buffering and preserve duplicates.
    # Native connection capability is never reconstructed from these bytes.
    request = RawRequest(method, canonical_path, raw_header_pairs,
                         exact_body, bridge_owned_connection)
    return await runtime.handle(request)
```

`ControlMuxRuntime.handle(RawRequest) -> await HttpResponse(status, headers, body)` is the actual dispatch entry point. Headers are tuple[tuple[bytes,bytes],...], not a merged dict; body is exact bytes. Header construction, socket framing and response writing belong to Root's raw front. Preserve status/headers/body, including an empty204 when a future qualified path supports it; never upgrade a202 or fabricate a response after timeout. Above code is ordinary composition of the current code, not permission to activate it. Default `ControlMuxApp` remains503; importing these functions cannot open a socket.

`grid_authority` must be the same existing Grid ConsulSessionAuthority instance that owns the live application lease; Grid validates leases against its private instance session/deadline registry. `existing_lease_provider` is an async no-argument callable returning that existing ConsulLease. It must not synthesize a lease from observed indices or acquire a separate lock/election per HTTP request. No current lease/quorum means unavailable/UNKNOWN, not a local fallback. Namespace must be unified/<approved cluster UUID>, generation an actually issued current UUID matching commands/generation. Mux captures generation and native Consul indices itself. Production Grid config requires HTTPS, approved ACL token, CA and mutual TLS certificate/key; secrets are not HTTP arguments, logs or this document.

## Root native provider callable contract

All four methods are synchronous in the current ABI; they return concrete objects, not awaitables. Native calls must be bounded. Any out-of-process bridge implementation, IPC authentication and timeouts require Root qualification; do not put an awaitable or serialized proof in place of these methods.

| Callable | Required result and ownership |
|---|---|
| resolve(request, operation) | Actual current AdmittedContext from the bridge-owned live connection/request capability, after native identity, enrollment, RBAC and request/session/CSRF policy checks. Raise on denial. |
| revalidate(context, operation) | Same current AdmittedContext, rechecking actual native/session expiry/revocation and current permission. No cached positive time interval or constructor-based grant. |
| identity_binding(context) | Exact Root security_identity_records.IdentityBinding(cluster_id, principal_id, session_id, enrollment_id, policy_id, node_id), each canonical UUIDv4 from actual approved enrollment/mapping. No caller paths or indices. |
| verify_records(context, records) | Compare actual current native SID, logon LUID, node/enrollment, session and current policy against the four immutable parsed records. Return exactly None only on success; otherwise raise. False/True/coroutine/stub is not success. |

AdmittedContext fields are cluster_id, actor_principal_id, actor_session_id, quota_owner_id, role, csrf_policy_ref, enrollment_revision, permissions frozenset and native_handle. Initial supported role is OPERATOR_CONTROL, owner exactly native-resolved principal UUID; NODE/delegation unavailable. A reference string such as csrf_policy_ref is not a CSRF proof. Root must bind the actual request's method/path/body/session/Origin or equivalent required CSRF policy to its live request capability at resolve, and preserve/revalidate that association through store calls. There is no public identity header fallback.

Root owns handle lifetime: capture/query an actual connection/token under its qualified bridge, finish impersonation and confirm RevertToSelf before Python awaits, retain only the permitted capability/handle for bounded dispatch, and close/revoke it in Root's finally path. No PID-only claim, SID string, pipe diagnostic JSON, caller handle integer, serialized admitted=true, or copied fixture context supplies authentication. In particular, a named-pipe client's authenticated token does not automatically authenticate an unrelated HTTP socket/browser; the actual connection/session association still needs Root implementation and review. The current Test-LocalPipeIdentity.ps1 proves only its diagnostic identification primitive.

Mux itself consistently reads the four fixed principal/session/enrollment/policy keys, validates Root canonical records and current operation/enrollment, invokes verify_records, then includes their actual positive ModifyIndices in the same native transaction as current Grid check-session/check-index, generation, affected record checks and command/receipt CAS. A2 does not accept supplied paths/indices/txn operations. Root must implement the actual approved record issuer/revoker and native lifecycle coupling; parsing ACTIVE records does not issue a session. Eight actual tests demonstrate record-revocation races reject PREPARE/FINAL, not atomic Windows-logoff/credential-expiry linearization. Native expiry/logoff and a Consul transaction are different systems: Root must explicitly qualify their ordering/coupled revocation semantics before claiming a native event instantly fences an already collected transaction. Event-ordered authority does not waive native credential lifetime gates.

## Existing endpoint behavior

| Method/path | Current actual behavior after native/authority admission |
|---|---|
| POST /control/v3/connections | OPERATOR OPEN201, durable original intent/receipt and bounded connection hold. |
| POST /control/v3/connections/<uuid>/subscriptions | CONTROL metadata201 WAIT_SOURCE only. No authorized snapshot bytes/READY/LIVE; DATASET unavailable. |
| POST /control/v3/subscriptions/<uuid>/snapshot-acks | Strict original binding/epochs checked; without actual authorized source returns503, no ACK204/intent. |
| DELETE /control/v3/connections/<uuid> | Actual fenced DRAINING202, original immutable; retains parent/nested debt. No contained204/release/reuse. |
| DELETE /control/v3/subscriptions/<uuid> | Actual fenced DRAINING202, retains subscription and parent debt. |
| GET command/snapshot/stream | Not wired/admitted; no success, no schema/model ACK promoted into endpoint admission. |

POST requires application/json and exact canonical Content-Length, body<=16384. DELETE requires zero bytes, absent/zero Content-Length, no Content-Type. Canonical UUID paths/epochs and existing Review4 request/key headers apply; duplicate headers, transfer-encoding and invalid framing reject. Raw front must reject ambiguous requests before unsafe body allocation; the in-process runtime is not a network parser. No native provider returns503 before reading request fields. Native resolve denial returns401. Malformed admitted input400; wrong method405; unavailable composition503. Original command digest exists before command_unknown may be emitted. Root must not translate503 into a definitive rejection or invent a digest.

Internal current-authorized `await store.reconcile(context, original_request_uuid)` returns Outcome with actual observed positive receipt_index for committed history. It is not a public GET endpoint or a new-operation permission. Original202 never becomes204; response bytes/status/hash remain original. Narrow existing mutation profile requires the current native actor/session to own its parent. Cross-session/cross-PC cleanup or identity mapping is a separate Root policy decision, not a caller-provided UUID alias. Missing/ambiguous legacy private hold records stay unavailable; no debt-free migration.

## Concrete remaining inputs / blockers

| Priority / owner | Missing callable or evidence at inspected Root source |
|---|---|
| P0 Root native/security | Actual four-method provider, live connection/request binding, bounded raw front and qualified handle/token lifetime. Current pure decoder and pipe diagnostic are insufficient. |
| P0 Root enrollment/security | Real approved four-record issuance/revocation, current Windows identity mapping, CSRF/session/role/expiry producer. No fixture records or self-issued identities. |
| P0 Root commissioning + A2 authority | Separately admitted local existing Consul test namespace/triplet, identity/generation/lease and TLS/ACL/package prerequisites. Currently not admitted. Office voters LS5/PC4/PC3 remain2/3; LS5 alone must not mutate office state. No reducing voters or replacement consensus. |
| P0 Root release/installer | Immutable installable component/dependency release closure, actual native attachment, backup/admin-channel/rollback gates; no A2 install/service/listener operations. |
| P1 Root/domain owners | Actual authorized view/barrier/snapshot producer and qualified delivery/readers/encoder/reassembly containment. Until available, READY/LIVE/positiveACK204/release stay closed. |
| P1 Root native/security | Explicit native logoff/expiry/revocation ordering and same-current-session/cross-PC ownership policy; no Consul index interpreted as UTC or cached credential grant. |
| P1 Root integration + A6/A8 | Separate actual endpoint/native attachment review at exact new source; prior model and synthetic-identity stand audits do not admit a physical pilot. |

Root explicitly retains office quorum2/3; a separately admitted LS5-local existing Consul test namespace/triplet can demonstrate a local pilot only, never physical office HA. At this source even that local authority namespace/identity/package has NOT been admitted. No other node, provider traffic, service/listener/security changes or deployment is authorized by this handoff.

## Next bounded joint verification once Root supplies actual source

1. Pin actual bridge/front source and admission dependencies; independently inspect the four method implementations and handle association. No substitute provider.
2. Compose the above real runtime with that actual provider and existing Grid instance in the separately approved namespace. Preserve default503 outside this explicit composition.
3. Exercise actual local authenticated HTTP OPEN201 -> immutable retry/reconcile, malformed/duplicate request denial, actual wrong/expired/revoked native identity rejection before intent, no-quorum/fenced transaction denial, and UNKNOWN recovery. Retain real raw receipts/indices and exact release pins.
4. Check native logoff/connection substitution/CSRF and disposal/impersonation cleanup with Root's independently qualified harness. Every failure retains debt and closes admission. No success from a Boolean/fixture.
5. Only Root's stage record may promote local runtime evidence. Snapshot/source/containment, office2/3 and later Windows nodes remain separate unmet gates. No READY/release fake.

Current decision: GO for source/interface preparation; NO_GO for native attachment, installation and physical acceptance. This handoff changes no product behavior or wire contract.
