# Gateway manifest disclosure — synthetic-only candidate design

Ownership ACK: ROOT Gateway Runtime Integration directive8791d40c.
Base f9f2d04595cf2360dab78980996ae6c34c9e26fc / tree
7fa3c8ad67c4efece7e2a692f48fb63a9e40ffd3. Separate feature branch/worktree.
Only gateway_disclosure.py, tests/storage/gateway_disclosure/**,
docs/intelligence/storage-disclosure/** and its dedicated workflow are allocated.

## Decision and existing storage

Use the existing ObjectStore and manifest codec for a narrow read-only boundary.
No generic backend dispatcher, second registry/store or replacement authority.
ROOT6825964 inventory identifies existing Strattester fenced report persistence
and opt-in ReadOnlyResultsApp; actual authenticated Gateway experiment/result
retrieval remains NONE. No experiment registry is created by this slice.

ROOT6825964 does not contain PR41's manifest codec. The explicitly allowed codec
base above avoids silently importing a missing dependency or editing ROOT source.
ROOT owns eventual Gateway composition and source admission.

## Proposed exact local API — joint API ACK pending

prepare_manifest_request(raw_bytes) is pure bounded validation and returns only
an untrusted immutable request observation/digest, no data or permission.

get_dataset_manifest(request_bytes, *, owner_read_capability=None,
pinned_owned_store=None) is a candidate
read method, NOT an existing admitted API. Missing/foreign/unverified capability
or source/type handshake denies BEFORE any object/store/provenance/status access.
No caller role, label, bool, None-return callback, JSON object or constructed class
instance can grant disclosure. A2's actual owner-bound type/source/check_current
ABI must be pinned before any positive path exists.

Proposed request fields: schema unified.storage.gateway-manifest-request.v1-review1,
request_id UUIDv4, dataset_id UUIDv4, dataset_revision positive u63 string,
manifest_revision independent positive u63 string, manifest_sha256,
manifest_schema_sha256, consumer_id and view_id UUIDv4.
API-REVIEW2.md and manifest-request.schema.json define the exact successor
request and A2 binding. The two revision domains are never inferred equal.
Canonical C3 ASCII bytes bind the complete request SHA256; no paths, URLs, store
selector, wildcard, authority flags or unknown keys. Maximum request16384 bytes.
This is a distinct new profile, not Root offline query-v1 or A3 row query ABI.

## Actual owner admission required

ROOT direction: actual disposable mTLS authenticates synthetic client/session
against A2's server-owned pinned client registry. A2 alone mints an opaque
process-local read capability bound to actual caller/session, fixed tool, consumer/
view, exact request digest, dataset/revision/root/schema, access scope, actual owned
store resource identity and expiry/revocation. No public mint/deserialization.
Consumer must use exact approved owner check_current, not an injected verifier.
Current checks and return/revocation ordering require exact A2 agreement; a prior
check cannot promise immunity to a later revocation. Positive path is currently
UNAVAILABLE pending this source/type/ABI handshake.

GET_DATASET_MANIFEST is distinct from QUERY_OHLCV, READ_DATA, research submission,
cancel and publication. A full A3 query digest differs from this subrequest digest;
only actual ROOT composition may request a correctly scoped subcapability. No
client reminting, digest alias or inherited authority from a manifest response.

## Positive output semantics to freeze after owner handshake

Output classification SYNTHETIC_SESSION_AUTHENTICATED_ONLY is derived evidence,
never proof input. Native Windows/production authentication stays false. Dataset,
schema/revision/digest are exact locally checked synthetic bindings, not admitted
registry or Consul committed revisions. Publication is UNPROVEN, committed revision
is null, coverage/gaps are UNKNOWN, source is SYNTHETIC_DISPOSABLE_FIXTURE and byte
integrity is LOCAL_HASH_MATCHED_NOT_REPLICA_VERIFIED. Manifest/page/source claims
cannot be promoted to VERIFIED or actual historical truth. No market rows/query,
computed series, experiment/result registry, job completion or new page cursor.

Actual ObjectStore read/hash and strict codec must match all requested/capability
bindings. Unknown schema/profile, wrong instrument/kind, foreign store/view/tool/
session or changed root denies. No BYBIT/bybit or CANDLES/raw implicit conversion.
Referenced pages/coverage/dependencies remain unverified. Output size is bounded;
errors expose only closed codes and never reflect raw request/private paths/keys.

## Tests and gates

First RED: missing module; then reject-before-IO for absent/None/bool/dict/callable/
foreign capability and malformed request. Pure request grammar/canonical/hash
tests do not supply permission. Positive tests wait for actual A2 mTLS registry/
issuer/check-current capability source, not a permissive double. Required positives
then use only actual disposable owner-authenticated fixture storage; negatives
include cross tool/view/consumer/session/store/request, expiry/revocation and
manifest/schema/revision mismatch with zero unauthorized reads.

Preserve prior codec/authority/publication files and CI inventories. Dedicated
workflow must explicitly bind the new inventory/source on CPython3.12.10 Windows/
Ubuntu. No old62 PASS is transferred to a branch with additional storage tests.
No native authority/publication, provider, production/physical/trading, service,
network/security changes or protected/main merge is authorized by this design.
