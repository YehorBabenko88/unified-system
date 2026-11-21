# Actual isolated manifest disclosure component — source review pending

Supersedes the earlier staging statements that this component always denies.
Request schema2 and owner-method local ABI successor3 are unchanged. Old proposal
documents are preserved, including the unselected capability-keyword alternative.

## Implemented path

ROOT must first load the single canonical unified_system.gateway_identity module
from exact admitted A2 commit2cb6b21eac5617ff39ad7a96b7e1c73118e0af00,
source SHA84093865e8477ef6562100d41137922785446c9cb4e024c9ba7105593a2b36c1.
Storage does not import plugins or accept a verifier callback. It checks ROOT's
already-loaded module/source/loader/classes and fixed owner-method origin before
using it. Missing/source-mismatched/foreign classes deny before object IO.
The complete capsule/dependency pre-import guard and commissioning remain ROOT's
prerequisites; this is not a sandbox against arbitrary hostile Python in-process.

get_dataset_manifest requires actual owner_read_capability, independent trusted
expected_identity_authority and the Root-commissioned actual ObjectStore instance.
Fixed DisposableIdentityAuthority.require_issued_read checks actual issuer/session/
inventory/request/tool/resource/store/expiry/revocation before read. One actual
ObjectStore.read verifies bounded root bytes; strict existing manifest codec
checks shape, canonical encoding, lineage/revision and requested dataset/hash.
The response is serialized/measured before the second fixed owner check and return.
No cap.check_current, dynamic issuer method, arbitrary None or class name is proof.

## Exact local result

Return type is BYTES, canonical compact sorted ASCII JSON, max32768 bytes:
schema unified.storage.gateway-manifest-disclosure.v1-review1;
status SYNTHETIC_MANIFEST_DISCLOSED; original request ID/digest;
authentication SYNTHETIC_SESSION_AUTHENTICATED_ONLY, native_authenticated=false;
applied access scope tool/consumer/view/mode; dataset ID and LOCAL SYNTHETIC
resource revision; separate LOCAL UNCOMMITTED manifest revision/hash/schema/root;
coverage/gaps UNKNOWN; publication/registry UNPROVEN; committed_dataset_revision=null;
source SYNTHETIC_DISPOSABLE_RESOURCE_NOT_SOURCE_ATTESTATION;
integrity LOCAL_HASH_MATCHED_NOT_REPLICA_VERIFIED; closure_verified=false.

This is an owner-local result candidate, not automatically admitted shared MCP,
HTTP or UI wire. ROOT must review its exact framing and remeasure any outer envelope.
No market rows, source truth, replica status, experiment/result registry, computed
series, paper events, worker permission or Consul publication is supplied.

## Actual tests and provenance

Original actual-positive RED used real A2 TLSFixture/issuer/capability but old
unavailable consumer; it failed before any root read. GREEN uses actual disposable
per-test CA/server/client certificates and live same-context server SSLSocket;
client observes loaded server DER exactly. Pinned helper source b26fe114c778a8b8a95bc3de822dd7c7a4f57dd12277e9fdcbc96cfb5bc4199f.
ROOT actual composition base fafeb8e16c01e1973594a21d5e55d10110e2c6fa
tree f39a8601cc8394529c4b79fcc56cd06ba11c4988 supplies the single canonical
package/type plus original ObjectStore/manifest codecs. Only allocated A4 product/
test overlays are used in an owned private clone; no ROOT source branch is edited.

Negatives cover legitimate foreign issuer sharing the same store, reopened same
root/store UUID, forged cap and fake issuer callback, tool/request/view/consumer/
revision/schema mismatch, actual revoke/expiry/closed TLS/audit capacity, revoke
during actual read, consumed-cap replay, corrupt owned object, inconsistent content,
fixed-method dispatch, source tamper and complete output bound. Zero unauthorized
object reads are asserted; authorized corrupt/mismatched content can require one
integrity read but never returns partial data. Fault hooks do not mint permission.

The fixture is A3's exact synthetic manifest root
8d216a8bc1117c240ef45d96b57f415779a14e7ee438dcf5c4109d3826b8b719.
No referenced rows/pages/coverage are claimed verified. PKI/socket/thread/temp-file
cleanup is explicit. Crypto env is A2's hash-locked own env reused read-only;
that does not newly qualify vendor/native/OS security. Actual tests are counted
separately from A2/ROOT's24. Whole Gateway HTTP/MCP path and native/physical/
production/provider/financial/trading admission remain NOT_RUN/BLOCKED.
