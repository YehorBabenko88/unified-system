# Exact manifest request and owner capability mapping — review2

PROPOSED owner API binding. A2 ABI design reviewed at7575388e, raw
be18e8dfa3a9b2006a0e7abc2a9d9218f05b65a18b989a2b881c7d1445212c63.
Its actual module/source/type and ROOT profile/parser/clock/audit qualification
remain required before positive disclosure. No local fake provider is accepted.

## Request

Closed canonical ASCII JSON, max16384 bytes, sorted unique keys, no whitespace/
numbers/normalization. All nine fields required:

* schema = unified.storage.gateway-manifest-request.v1-review2
* request_id, dataset_id, consumer_id, view_id: canonical UUIDv4
* dataset_revision: positive u63 string, LOCAL SYNTHETIC RESOURCE revision
* manifest_revision: independent positive u63 string, local manifest-root revision
* manifest_sha256: lowercase SHA256 of exact root bytes
* manifest_schema_sha256: exact selected local candidate schema digest

Initial local codec schema digest is
a599b399cb8809ad72a2ecdb778a4e7e419f88a6cadcf2da20489cf93d12fd10.
Unknown schema/profile denies, no caller-selected validator/fallback. Neither
revision is a Consul committed revision or native index, nor are the two inferred
equal. Fixture resource revision7 may bind a root whose manifest revision is1.

prepare_manifest_request(request_bytes) returns an immutable untrusted observation,
canonical request SHA256 and detached binding data. It never grants disclosure.

## Exact owner capability use

get_dataset_manifest(request_bytes, *, owner_read_capability=None,
pinned_owned_store=None) is the proposed narrow boundary.

A2 alone authenticates the actual same-context server-side mTLS SSLSocket and
mints GatewayReadCapability. Exact fixed module unified_system.gateway_identity,
class/source/issuer instance must be admitted by ROOT composition, not imported
by arbitrary caller plugin/name. Consumer verifies exact owner type and actual
source handshake; no subclass/copy/JSON/dataclass/flag/None/bool/callback is proof.
No public constructor or setter is supplied by Storage.

A2 binding is exactly:
schema unified.gateway.read-binding.v1-review2; dataset_id; dataset_revision;
manifest_sha256; schema_sha256=request.manifest_schema_sha256; consumer_id; view_id.
No extra field, field omission, case/kind conversion or digest alias. The owner
computes SHA256 of COMPLETE exact request bytes, including manifest_revision,
request UUID and all other fields. Actual owned store OBJECT identity is separately
commissioned; matching store UUID/path alone is insufficient.

Fixed tool is unified.get_dataset_manifest. On the exact issued object invoke:
check_current(tool_name=...,request_bytes=...,binding=...,owned_store=...).
It is synchronous and returns exactly None after actual issuer/current-session/
registry/policy/expiry/revocation/request/resource/store checks. Every non-None or
awaitable result denies; no nested event loop or finalization of suspended owner
work. None is not proof independently: exact actual owner handle and handshake
are prerequisites. Recheck immediately before bounded output, with actual owner
revocation/expiry semantics; no instantaneous external-revocation guarantee.

Until exact actual A2 source/type handshake exists, get_dataset_manifest always
denies BEFORE parsing data or accessing any supplied object/store attribute.
Pure request preparation remains independently usable without permission.

## Output and downstream restrictions

Only after actual scoped synthetic capability approval, use actual ObjectStore
read/hash and manifest codec; bind returned root dataset/revision/hash/schema to
the original request and owner scope. No arbitrary file/path/SQL/URL access.
Malformed or inconsistent authorized content returns a closed error, never partial
rows or a positive fallback. Output is bounded, nonstreaming.

Classification is SYNTHETIC_SESSION_AUTHENTICATED_ONLY from actual owner evidence,
native_authenticated=false. Dataset resource revision and manifest root revision
are explicit separate local values; authoritative committed revision is null.
Coverage/gaps UNKNOWN, publication/registry UNPROVEN, source SYNTHETIC_ONLY and
integrity LOCAL_HASH_MATCHED_NOT_REPLICA_VERIFIED. No computed result/series/job
completion, source truth, schema/closure VERIFIED or production admission.

A3 query needs its OWN tool+full-query capability. This manifest subrequest digest
cannot authorize row IO; only ROOT may compose correctly scoped subrequest issuance.
No additional experiment/result registry, catalogue or read service is introduced.

## Dedicated tests

New gateway_disclosure tests are a separately selected standalone suite (no package
initializer). Existing exact62 manifest suite remains its original fixed inventory;
the new dedicated mandatory workflow selects both that suite and all disclosure
cases explicitly. This is separate test scope, not an inherited62 PASS or a hidden
positive admission waiver. Root composition/mTLS positive evidence remains NOT_RUN
until exact owner implementation/source ACK.
