# Disposable Gateway identity and read capability ABI v1-review2

PROPOSAL; explicit Root/A3/A4 exact ACK required before executable adapter.
Base6825964bf52375b134c6eb4487808963a0d128ed/tree2b3988fa4cdd334b6ae63067fdb34987dd0e6840.
Only allocated new gateway_identity.py/tests/docs/workflow; existing APIs unchanged.
Supersedes A2 outputs/GATEWAY-IDENTITY-API-REVIEW1.md df7416ee at proposal scope.

## Server interface and actual authentication

A2 does NOT own an HTTP/MCP server, handler, listener or Gateway composition.
Current actual server endpoint: NONE. Proposed Root-owned interface is an actual
loopback TLS server with CERT_REQUIRED and a per-run disposable CA/context. Root
selects an ephemeral port and exact route/HTTP contract; no A2 invented URL.
The identity module consumes the accepted real server-side SSLSocket. Root MUST
call identity authentication inside its handler before any owner store/query IO.

NEW `DisposableIdentityAuthority(*, server_ssl_context, profile)`:
explicit DISPOSABLE_ONLY commissioning profile; no production mode/fallback.
Profile is provisioned server-side before accepting requests, never request JSON.
It pins realm UUID; server certificate DER SHA256; client entries pin exact client
DER SHA256, exact one URI SAN, clientAuth EKU, issuer realm, synthetic service UUID,
synthetic delegated user UUID, quota owner opaque ID, bounded UTC expiry, active
revision and explicit tool/resource grants. Real SSL chain/cert expiry verification
uses owned per-run CA. Server SAN loopback identity/EKU and client SAN/EKU/fingerprint
are checked explicitly; hostless service URI is an application identity with exact
full-SAN matching, not an assumed generic RFC9525 host verification rule.
Root must coapprove certificate extension parser/dependency and pinned toolchain.
No CA/key/PEM, trust-store install, production SID/LUID or reusable user credential.

`authenticate_connection(server_ssl_socket) -> GatewayClientContext`:
require actual connected server-side SSLSocket, SAME configured SSLContext,
verified peer DER and exact commissioned entry; no arbitrary DER/header/token/
role/bool/dict input. Context is authority-issued, process-local, instance and
connection bound. Actual mTLS authenticates SYNTHETIC service/session ONLY.
Delegated synthetic user is fixed by server commissioning, not human Windows proof.

## Exact read-capability ABI proposed to A3/A4

`authorize_read(context, *, tool_name, request_bytes, binding, owned_store)
 -> GatewayReadCapability`

Root trusted handler supplies exact original bounded request bytes and actual
pinned store instance. `binding` is CLOSED untrusted data validated against the
commissioned server resource grant; caller-selected matching strings are not proof.
All fields REQUIRED: schema=unified.gateway.read-binding.v1-review2,
dataset_id (canonical UUID4), dataset_revision (positive u63 decimal string,
LOCAL SYNTHETIC immutable revision only), manifest_sha256 (lowercase64),
schema_sha256 (lowercase64), consumer_id (UUID4), view_id (UUID4).
tool_name is a separate exact known tool; SHA256(request_bytes) is computed by
the authority, never accepted from a caller. owned_store is object-identity bound
to the actual Root-commissioned instance. No path/SQL/native index/operation list.
No binding field grants data integrity, closure, verified coverage or authority.
Read range/cut/limit semantics remain in exact request bytes and owner schema.

Exact supported initial tool names proposed: unified.get_dataset_manifest (A4),
unified.query_market_data (A3), each READ_DATA. Missing owner tool/resource request
schema and explicit grant mapping => unavailable. No case/kind alias between
offline BYBIT/CANDLES and owner bybit/raw vocabularies. No other catalog tool enabled.

`GatewayReadCapability.check_current(*, tool_name, request_bytes, binding,
owned_store) -> None`

This is the concrete owner boundary: A3/A4 first require
`type(owner_read_capability) is GatewayReadCapability` from this EXACT admitted
module and authority composition, then call check_current before first object
read and immediately before returning bounded output. The check verifies opaque
handle issuance against SAME issuer instance, exact original context/connection,
request digest, full binding/tool/store object identity and current server profile
revision/expiry/revocation. Arbitrary method-shaped objects/None-return callbacks,
subclasses, constructed dataclass copies, copied/serialized handles and foreign
authority contexts fail. Capability has no public constructor/mint factory;
issuance is private to the commissioned authority's authenticated call path.
In-process arbitrary Python execution is outside this trusted owner boundary;
process-local handles are not a sandbox or production remote proof.

Root/A3/A4 must explicitly bind the issuer instance and fixed implementation/type;
importing a same-named module through arbitrary sys.path is not shared admission.
For Grid A3, packaging the exact Unified identity module in the owned disposable
composition is a separate Root integration dependency; no duck-typed fallback.

Owner currently proposed A4 method:
`get_dataset_manifest(request_bytes, *, owner_read_capability, pinned_owned_store)`.
A4 resolves its exact binding from the approved request + fixed store/commissioned
view; mismatch denies BEFORE object access. A3 must ACK its exact query/store
signature and identical permit boundary. Missing interface never becomes success.

## Revocation/expiry, audit and effects

`revoke_service(service_id)` is fixture-owner-only and invalidates issued handles;
not a public route, cluster policy, distributed lease or Consul mutation. Expiry,
certificate expiry, actual connection closure, profile revision/revocation or clock
uncertainty deny. Root must ACK exact expiry/clock/parser and same-process order.
No claim of instantaneous external revocation vs already disclosed bytes.
Initial output bounded/nonstreaming; streaming/resume is separately unsupported.

Scope vocabulary only: READ_DATA, SUBMIT_RESEARCH, READ_RESEARCH, CANCEL_OWN_JOB,
PUBLISH_VISUALIZATION, PROPOSE_CHANGE, OPERATE_NODE. Initial issuer supports only
READ_DATA and rejects nonread grants; all mutation/research/cancel/fencing APIs NONE.
quota_owner_id is commissioned synthetic association, never reservation/debit.
No fabricated mutation fence; no new election, registry service or scheduler.

Authority emits bounded audit DATA (realm/request digest, synthetic service/user/
quota IDs, tool/binding digest, decision/closed reason) without request payload,
cert/key or secret. Root owns actual sink/retention and request correlation. Missing
required sink/owner boundary must block composition; no durable commit claim.

Output classification ONLY: SYNTHETIC_SESSION_AUTHENTICATED_ONLY,
nativeauthentication=false. These fields are output limitations, never input grants.
Owner data retains synthetic provenance, UNKNOWN coverage/gaps and UNPROVEN
publication/registry unless that owner separately proves a stronger property.
Neither capability nor valid local hash may promote that classification.

## After exact ACK

RED first: no cert/untrusted CA/wrong SAN/EKU/fingerprint, caller claims/foreign or
copied handle, wrong request/tool/resource/store/view, expired/revoked/closed peer,
nonread grant deny with ZERO owner IO. Then actual own loopback mTLS positive with
server-provisioned synthetic user/resource READ_DATA and owner-supported fixture
read; actual audit and cleanup. Tests NOT_RUN. No runtime/admission/CI PASS claim.
Native worktree creation hung without path/opID, stopped; readonly Git inventory
confirmed no new worktree, then explicit separate Git worktree created safely.
