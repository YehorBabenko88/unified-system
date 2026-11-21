# Local capability ABI successor3 — expected owner identity

PROPOSED successor, explicit A2/A3/A4/ROOT source/type ACK still required before
positive integration. API-REVIEW2.md/request schema bytes remain unchanged.

Consumer signature becomes:

get_dataset_manifest(request_bytes, *, owner_read_capability,
expected_identity_authority, pinned_owned_store)

All trusted keyword arguments are required. ROOT passes its actual self.authority
and commissioned store instance; neither is client JSON or a caller plugin/class.
Missing/None/foreign source/type/issuer handshake denies before any supplied store
attribute access. No public setter, authority registry or mint factory in Storage.

A2 GatewayReadCapability.check_current takes mandatory expected_identity_authority
in addition to tool_name/request_bytes/binding/owned_store. It verifies exact
actual authority type, self._issuer IS expected authority, then calls the FIXED
DisposableIdentityAuthority._check(expected,...), including actual issuance
inventory/current session/policy/expiry/revocation/request/resource/store checks.
The capability's self-reported issuer or class name cannot choose a callback.

Consumer must use the fixed admitted owner-class method after source/type handshake,
not a caller-overridable check_current attribute or subclass. An arbitrary exact-
class object forged with fake issuer, copied handle or legitimate FOREIGN issuer
sharing the same store is denied. Actual Root-owned expected issuer binding is
essential; matching paths/store UUIDs or module names are insufficient.

This remains one current check per invocation: GETmanifest pre-read and pre-return
uses2; A3 six-object query uses7. These limits are server-owned fixed per tool,
not supplied by request/caller. No dropped checks, automatic reminting or retries.

Request/binding C3 schema2 is unchanged, including independent local dataset and
manifest revisions. GETmanifest root-schema hash and QUERY row-schema hash remain
separate tool domains. Synthetic output labels are never proof input. All native/
publication/provider coverage/registry/physical claims remain unavailable.

Exact actual A2 module/source and owner review3 document are pending. Current
Storage code only exercises pure request validation and unconditional deny-before-
IO. No positive mTLS disclosure, data query or runtime admission is claimed.
