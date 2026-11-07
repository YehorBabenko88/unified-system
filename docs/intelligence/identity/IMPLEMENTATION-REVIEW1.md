# Disposable identity implementation — source review required

API proposal review2 exact Root/A3/A4 DESIGN ACK received. Source/positive cross-
owner read and runtime admission are SEPARATE and still pending. No native user,
production crypto/security qualification or actual market data proof.

## Exact sink / constructor / profile

`GatewayAuditSink(*, max_events=1024)`, exact type, limit1..4096.
`DisposableIdentityAuthority(*, server_ssl_context, profile, audit_sink)` requires
that exact sink; None/foreign/duck-typed callback unavailable. Buffer full rejects
before permit mint or current-check success. `drain()` returns tuple of detached
record copies for Root durable sink; it is not a durable commit or remote proof.
Root owns draining/retention/correlation and must bind sink before disclosure.

Profile CLOSED schema unified.gateway.disposable-identity.v1-review1, realm_id,
server_certificate_der (bytes), clients (1..32). Each closed client entry:
certificate_sha256, service_id, delegated_user_id, quota_owner_id, uri,
expires_utc, grants. UUIDs v4, quota opaque ID, exact URI
urn:unified:test:service:<serviceUUID>. Each grant CLOSED tool_name, binding,
owned_store. Binding is exactly review2's seven fields. Store is the actual
Root-commissioned instance, retained by identity; no caller store UUID/path proof.
All profile values copied/frozen except intentionally pinned store reference.
Only immutable grant profiles exist; changes require new issuer instance.
Owner-only revoke_service invalidates old contexts/caps with a monotonic set.

Module provides exact types GatewayClientContext and GatewayReadCapability;
neither public constructor/copy/pickle can issue a handle. Issuer inventory checks
object identity; object.__new__ without inventory membership still cannot grant.
check_current is SYNCHRONOUS, exact successful return None, otherwise
GatewayIdentityDenied or GatewayIdentityUnavailable. Awaitables/nonNone/other
providers are unsupported; owners never run/close/schedule such foreign values.
Two successful current checks per cap (before read and before bounded return);
third check refuses replay. This does not isolate arbitrary hostile Python code
already executing inside the trusted owner process. Context inventory128 and cap
inventory256 are bounded; capacity denies, new issuer required after capacity.

## Real crypto / server prerequisite

Pinned cryptography46.0.3 X509 parser/signature verification, cffi2.0.0 and
pycparser2.23; no hand-written ASN.1. Exact Windows/Linux wheel SHA256 are in own
requirements-{windows,linux}.lock. pip --require-hashes --only-binary=:all: is
required; wheels retrieved from the configured Python package index (standard
PyPI files), file hashes/version/metadata checked separately. Hashes pin bytes,
not vendor trust or a security endorsement. No global requirements modified.
Local Python3.12.10 ssl OpenSSL3.0.16 is test environment, not production admission.

SSLContext must be server-side, CERT_REQUIRED, minimumTLS1.2 and exactly one CA.
Actual client SSLSocket is server_side with SAME context; peer DER fingerprint,
CA signature, notBefore/notAfter, BasicConstraints false, EXACT clientAuth EKU
and EXACT one commissioned URI SAN are verified. No extra SAN accepted.
Commissioned server DER is checked against CA, SERVER_AUTH EKU and exact loopback
IP SAN127.0.0.1. Profile server DER DOES NOT prove SSLContext loaded that key/cert.
Root factory MUST load owned key/cert into that SAME context and a real isolated
client MUST compare observed server DER pin. Tests perform that real client pin.
No server endpoint/listener belongs to A2. Root consumes accepted socket in its
handler before any A3/A4 store read. Socket check observes locally owned SSL state;
it cannot infer an unobserved remote logoff or prevent prior disclosed bytes.

## Expiry / monotonic ordering

Profile UTC expiry exact YYYY-MM-DDTHH:MM:SSZ, future and <=900sec at commission.
Effective wall expiry is minimum client cert, profile and server cert notAfter.
Each also has an independent monotonic deadline anchored to commissioning; later
wall readings never extend it. On every current check compare current real UTC
and monotonic: backwards wall/monotonic or >1sec cumulative wall lag vs elapsed
monotonic permanently poisons issuer CLOCK_UNCERTAIN. Positive UTC jump can expire
sooner, never extend. No clock injection API. Controlled clock unit tests patch
private clock reads only and do not claim actual OS/native clock acceptance.
Registry expiry is also exercised with actual elapsed time after real mTLS.
Owner methods lock same-process state; checks do not hold an owner read transaction
or assert instantaneous cross-process revocation/disclosure atomicity. Root must
coapprove the two-check bounded-read ordering; no streaming/resume grant.

## Tool/resource mapping and classification

Only unified.get_dataset_manifest and unified.query_market_data READ_DATA grants.
Nonread grants unavailable; no research/cancel/fence/debit API or new consensus.
GET manifest binding.schema_sha256 = request.manifest_schema_sha256 (manifest root
schema a599...). QUERY binding.schema_sha256 = request.data_schema_sha256 (row
profile). These are DISTINCT tool-domain grants, not aliases. Dataset revision is
LOCAL synthetic resource revision; manifest revision is separate and bound in
full request bytes/hash. Full query and manifest subrequest require independent
issuer calls for their distinct tools/bytes. No client remint or digest alias.
Consumer/view UUID, exact request digest, dataset/revision/root/schema and actual
store identity bind every cap. Other APIs/claimed roles/JSON flags cannot grant.
Output classification SYNTHETIC_SESSION_AUTHENTICATED_ONLY/nativeauthentication=false
is a limitation, never input proof; coverage/registry/publication remains unknown
or unproven until separately supported by the data owner.

Local tests cover actual owned TLS, denial boundaries, profile copy, expiry and
controlled rollback, audit-full/no-sink, capacity and foreign/copied/forged handles.
Cross-owner positive store/query tests NOT_RUN, shared source API admission PENDING.
Owned temporary PKI/socket/thread cleanup performed; no persistent key output.
