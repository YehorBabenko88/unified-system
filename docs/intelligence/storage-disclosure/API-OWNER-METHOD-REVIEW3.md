# Final proposed local owner-method ABI successor3

ROOT selected this variant after the capability-keyword proposal. Old review2
and API-REVIEW3.md keyword-variant draft bytes remain preserved; the latter is
not the selected positive integration ABI. No request/binding JSON is changed.
Exact A2 implementation/source and owner review3 document still need fresh review.

Selected Storage signature:

get_dataset_manifest(request_bytes, *, owner_read_capability,
expected_identity_authority, pinned_owned_store)

All trusted keyword arguments are required. ROOT passes its actual self.authority
and commissioned store object; public JSON cannot select/create/deserialize either.
No inferred expected issuer from capability._issuer or matching class/store path.

After exact admitted source/type handshake, require
type(expected_identity_authority) is DisposableIdentityAuthority and exact actual
GatewayReadCapability type. Invoke the FIXED owner class method:

DisposableIdentityAuthority.require_issued_read(expected_identity_authority,
owner_read_capability, tool_name=TOOL_NAME, request_bytes=original_bytes,
binding=closed_read_binding, owned_store=pinned_owned_store)

The implementation verifies capability._issuer IS that actual expected authority,
actual issuance inventory membership, same real authenticated TLS session/profile,
request digest/tool/resource/store identity and expiry/revocation. It performs
exactly one current check, returning exactly None or raising the closed owner
GatewayIdentityDenied/GatewayIdentityUnavailable exception. Arbitrary callback,
method shape, None/bool/JSON, subclass/forged/copied handle, foreign issuer even
with the same store, or non-None/awaitable output is not permission.

Storage does not call capability.check_current directly for disclosure and does
not access a caller-overridable authority method. No new keyword is added to the
old capability-local method by this proposal. Local old-method tests/evidence
remain their original scope. No nested event loop or finalization of owner work.

GETmanifest has two checks: before its single object read and immediately before
bounded output. A3 query has seven: before each of six actual object reads and
before returning complete bounded output. The first read check is also entry
authorization; no duplicate current check consumes an extra use. Limits belong
to A2's server tool policy, not the request; never remove checks/remint to fit.

Exact request schema2/Root per-tool grants remain required. Resource dataset
revision is LOCAL SYNTHETIC and separate from manifest revision. Manifest ROOT
schema digest is not row-schema digest, and whole-query/subrequest hashes differ.
Synthetic labels are output only. Local hash/codec/fixture coverage cannot grant
native authentication, source truth, publication/registry or VERIFIED replicas.

Positive cross-owner integration remains NOT_RUN until A2's fixed owner-method
source/profile/audit/clock and ROOT commissioning are reviewed and explicitly ACKed.
Current Storage code validates request syntax and denies reads before owner IO.
