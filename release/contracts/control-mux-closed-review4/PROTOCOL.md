# Closed Control multiplex schema bundle — review3

OUTPUT-ONLY exact A1/A6/ROOT ACK pending. Follows immutable review2+review3
corrigendum (published integration dca91e08273aaef3b485c3cd43181499e468489b), but
does not inherit their limited ACK. No shared consumers/product/endpoints changed.
PR31 experimental namespace is NOT this final ABI. Runtime remains BLOCKED.

## Schema identity and canonical encoding

control-mux-closed.schema.json is a single closed draft2020-12 schema with named
definitions for open/subscribe/ACK requests; opened/subscribed/pending/draining/
unknown/error results; canonical command/key preimages; immutable request index,
stored command/receipt and all six mux frame kinds. registry.json pins exact
schema raw SHA and payload-kind/definition. Authorized-view snapshot,
change and authority-observation envelope fields reuse source f41fc73c…;
resource.value representation is explicitly narrowed below for the NEW C3 profile; all messages here are untrusted claims until admitted
provider/barrier/domain validation. No schema/hash proves identity or authority.

All fields listed by an object are required and extra keys reject. Optional values
are explicit JSON null, not omission/empty/string-null. Native HTTP absence is
converted to null only by the exact header-to-command parser. Closed definitions
do not imply all named messages may be accepted on every route: semantic route/
method/body/target/epoch/header equality remains mandatory.

Canonical C3: raw UTF-8 bytes restricted to printable ASCII keys/strings; unique
keys sorted ascending ASCII recursively, quote/backslash escapes only; no BOM,
whitespace or final newline; no Unicode/slash escape aliases, nonfinite values,
case folding or duplicate keys. u63 decimal STRING is exact0..9223372036854775807,
positive fields exclude0. UUID lowercasev4, SHA256 lowercase64hex. Resource domain
payloads require separately pinned A3/A4/A5/A7 schemas before data success; generic
resource.value is not a domain ACK. Preparse caps/depth/node bounds are mandatory.

profile_schema_sha256 is SHA256 of COMPLETE raw canonical schema file bytes.
Schema file never embeds its own computed digest: generic digest field schema is
structural. registry.json and examples are computed AFTER schema bytes are frozen.
There is no self-hash cycle. payload_schema_sha256 resolves registry's exact
profile digest AND declared payload definition for kind, never arbitrary caller
schema. Root/typed-domain algorithms remain independently reviewed dependencies.

## Exact bodies, headers and responses

Routes/roles/CSRF and eight-connection/nine-subscription limits remain as in prior
candidate. POST bodies correspond to open_request, subscribe_request and
snapshot_ack_request. Request X-Request-ID equals body.request_id. Idempotency-Key
is immutable boundedID. X-Expected-Connection-Epoch required for subscribe/ACK/
DELETE; it equals body expected_connection_epoch if present. X-Expected-
Subscription-Epoch required for snapshot ACK/subscription DELETE and equals body.
X-Stream-Attempt-ID required for events GET; all exact UUID/counters. Header casing
is HTTP-insensitive but duplicate values are rejected at admitted RAW front;
canonical internal names/values have no duplicate/coercion aliases. CSRF/auth/
cookies/credentials are checked by real provider and never persisted in digest.

201 OPENED includes initial_mux_cursor and initial_mux_sequence='0'.201 SUBSCRIBED
does not reset outer stream.202 SNAPSHOT_PENDING has bounded positive retry;200
snapshot uses snapshot definition.204 successful ACK or fully-contained CLOSED
has ZERO body bytes, not JSON null or an undocumented result tag.202 DRAINING uses
draining shape until actual termination verified; state never automatically frees
slot on heartbeat/session timeout.201/202 serialized results are stored byte-exact;
204 has SHA256 of EMPTY response bytes and result_schema_sha256=null in receipt.

Errors:400 INVALID_REQUEST;401 UNAUTHENTICATED/SESSION_EXPIRED;403 FORBIDDEN;404
NOT_FOUND;405 METHOD_NOT_ALLOWED with exact Allow;409 CONFLICT for current verified
identity/digest/epoch/role rejection;429 RATE_LIMITED;503 unavailable provider/
authority/admission. Unknown commit is command_unknown, NOT definitive409 rejection.
Error code/reason combinations must match actual checked cause, not caller choice.
result http_status is a decimal status string in stored receipt, not a permission.
Only definitive stored outcomes become immutable receipt; transient UNKNOWN stays
unresolved command state and may not terminate reconciliation or authorize retry.

LIVENESS is now explicitly CONNECTION scoped: null subscription_id/epoch, closed
connection_liveness payload with UUID only, no inner cursor/revision/root/authority.
Subscription authority_observation remains separate and state-bound. SnapshotReady
announces authorized immutable snapshot ID/hash/size<=2097152, not inline snapshot.
Frame JSON<=133120 and exact SSE `data: `+JSON+LF+LF<=133128. Payload<=131072,
snapshot<=2097152; aggregate limits/fairness/containment remain unqualified design
constraints, not measurements. Domain/error connection-notice identity equality,
kind/context/schema/epochs/mux sequence and all inner relationships are semantic
checks beyond JSON Schema. Outer failure clears every connection subscription LIVE.

## Canonical digest preimages (no raw credentials)

hash-preimages.json contains byte-exact synthetic ASCII strings and SHA256s for
one request body, full15field command preimage and idempotency-key descriptor.
command_digest=SHA256(C3(command_preimage)). canonical_body_sha256 is actual HTTP
body hash; DELETE hashes zero raw bytes, NOT canonical JSON null. Complete method,
operation, canonical_path, target IDs/epochs and original actor/session/key/UUID
remain in command digest even for empty body. Same key different target/session/
body/method/epoch/request conflicts. Body rewrite/canonicalization after command
preparation is forbidden; schema/profile changes require explicit new binding.

Idempotency lookup key descriptor EXACT namespace_schema, cluster_id,
quota_owner_id, original_actor_principal_id, idempotency_key. It deliberately
EXCLUDES target/session/request/body so cross-target/session key reuse collides
and is rejected by immutable command digest, rather than opening a second record.
Cluster/owner/actor come from actual admitted authority/identity, never caller JSON.
Current session may read old receipt under current reconciliation capability;
it cannot impersonate original session or revive original cursor.

## Immutable receipt lookup namespace and uniqueness index

N is existing qualified Grid Consul namespace. Keys are generation-independent:

* N/control-v3/requests/<requestUUID> — UNIQUE immutable request index within this
  authority cluster, across actors/owners/profiles/recovery generations.
* N/control-v3/commands/<SHA256(C3(idempotency_key_preimage))> — original full
  command digest/preimage, immutable identity and mutable PENDING->terminal state.
* N/control-v3/receipts/<receiptUUID> — immutable definitive canonical result hash,
  original command/key/request binding. receiptUUID is allocated at preparation;
  this is an opaque reference, not a future self-index or bearer credential.

Before any admission effect, one current fenced native transaction check-index0
claims request index and command-key binding and durable PENDING original intent.
Same requestUUID under ANY other original binding conflicts; do not scope this
index by actor/target so GET commands/UUID cannot become ambiguous. UUID allocation
is randomv4 but uniqueness is ENFORCED by CAS, not assumed from probability.
Command completion atomically commits admission metadata/receipt/result and updates
the existing original command record. No separate SQL authority or local-only
index. Root source/layout/provider allocation is still required before code.

GET /control/v3/commands/<requestUUID>: current authentication+ReconcileControl-
Admission permission, then actual consistent read of exact index. Verify original
index/key/digest/actor-session/receipt/profile, native positive ModifyIndices,
byte hashes and exact stored result. Unauthorized owner returns redacted404 or403
under fixed provider policy, never another owner's data. Current session must be
authorized to reconcile original binding; historical result is never fresh cursor/
slot permission. A zero-row lookup stays UNKNOWN under unresolved intent. More
than one mapping/legacy alias, conflicting linkage, corrupt profile or inconsistent
pair is503 command_unknown.reason=CONFLICTING_EVIDENCE or
error_v3.reason=RECEIPT_AMBIGUOUS; NEVER pick first/latest or infer
rejection. Preserve original identity/slot/byte debt while uncertain. Tombstone
request/key uniqueness through retention/recovery; TTL/history GC cannot reuse an
old request or erase unresolved socket obligations. Durable unresolved intent and
definitive receipt retrieval are different from transport replay.

Native index is attached AFTER actual consistent receipt observation, never stored
as predicted future own index or derived from timestamp. Hashes and fixture refs
in this bundle are MODEL_ONLY. qualified current provider/session/containment,
global quota/byte/encoder ledger, actual native proofs and two-producer Windows/
Linux load/relocation evidence remain independent runtime admission gates.

## Validation scope

build_bundle.py generates canonical raw artifacts using write_bytes and hashes
AFTER writing schema. validate_bundle.py checks schema, positive/negative messages,
canonical and exactu63 vectors, hash preimages and synthetic request-index lookup
ambiguity/identity/linkage cases. It is NOT an endpoint, actual identity/Consul
adapter, root verifier, native containment or load test. Fresh exact A1/A6/ROOT ACK
is requested; no old limited ACK is upgraded by these tests.

Terminal receipt lookup explicitly returns original definitive error for DEFINITIVE_REJECTED; it does not demote terminal rejection to UNKNOWN. Successful204 validates null result schema and SHA256 of zero response bytes, not JSON null. Header/body relationships, native proof and route-specific authorization remain separate semantic checks. Included base-sync-v2.schema.json is the preserved f41fc73c input so schema generation is self-contained/offline.

## Review2 operation/state/status/result compatibility (A1-CLOSED-R1-01)

Review1 remains immutable and NOT APPROVED. A1 reproduced hash-consistent but incompatible OPEN/204, OPEN/201/UNKNOWN and OPEN/201/error lookups; A2 also reproduced wrong-operation and DELETE/201 in RED. Review2 requires operation-result-matrix.json BEFORE returning either historical success or rejection. Matrix raw SHA is embedded in schema profile bytes (x-operation-result-matrix-sha256) and registry, so profile_schema_sha256 binds exact matrix semantics without a hash cycle. Manifest pins every byte.

COMPLETED allowed tuples only: OPEN_CONNECTION POST201/opened; OPEN_SUBSCRIPTION POST201/subscribed; ACK_SNAPSHOT POST204/EMPTY; CLOSE_CONNECTION and CLOSE_SUBSCRIPTION DELETE202/draining or204/EMPTY. All other combinations fail UNAVAILABLE_CONFLICT even when every hash/link matches. Method, exact canonical route target, required/null target/epoch fields and empty DELETE body hash must agree with original operation. Non-OPEN success results match captured connection/epoch; draining matches exact subscription/epoch or both null.

DEFINITIVE_REJECTED requires the closed error_v3 definition and exact status-to-error-code matrix (including valid409 CONFLICT). UNKNOWN/command_unknown is NEVER a terminal receipt for any status/state. PENDING remains unresolved only.204 requires no body, null result schema hash and SHA256 zero bytes; it is valid only for ACK/CLOSE, never OPEN/SUBSCRIBE.202 DRAINING is historical command acceptance, NOT delivery containment/slot release. Actual endpoint/runtime must enforce this semantic matrix in addition to schema/canonical/hash checks; shape or a successful tuple model grants no authority.

Positive regression vectors cover OPEN201, SUBSCRIBE201, ACK204, CLOSE204/202, valid409 rejection; negative vectors cover all A1 cases plus wrong method/route/DELETE body and UNKNOWN as definitive rejection. Findings and RED probes are preserved separately. No shared consumer/source/PR31 edits, old ACK transfer, native/provider/physical or final runtime acceptance.

## Review2 language-independent numeric policy (A6)

C3 TRANSPORT MESSAGES permit NO JSON numeric literals anywhere, including generic resource.value.1,1.0,-0,-0.0,1e-07 and every other number token reject; booleans remain distinct booleans. Counters use the exact checked u63 strings; prices/amounts or other numeric domain data require the owner's explicit exact STRING schema/units/scale and separate ACK. Strings such as "1", "1.0", "-0.0", "1e-07" preserve their bytes and are NOT automatically equivalent, parsed, normalized or rounded. A domain may reject a string spelling, but this transport never coerces amounts. New recursive c3_value schema excludes numbers structurally in resource payloads. JSON Schema ARTIFACTS/manifest counters may contain numeric constraints; they are not transport messages and do not use this numeric-token rejection rule.

Do not equate JS JSON.stringify or Python dumps with C3 automatically. Use an explicit recursive canonical writer, sorting every object key by ASCII byte order and emitting exact supported primitive tokens. In particular numeric-looking keys "10" precede "2" in C3; JS object enumeration can reorder them numerically, so stringify of a sorted ordinary object is insufficient. Cross-language vectors include rejected1.0/-0.0/1e-07 and numeric key-order aliases, plus preserved exact string spellings and ASCII ordering. Maximum domain depth/node/byte and semantic source-schema gates remain mandatory. This explicitly narrows the NEW unapproved review2 transport profile; frozen review1/base-sync artifacts and PR31 experimental source stay unchanged.

## Review2 durable original body and OPENED consistency

Stored command now REQUIRED original_body_ascii retains EXACT immutable canonical HTTP POST bytes (ASCII, <=16384), not only a digest. DELETE retains exactly empty string/zero bytes. Persist original preimage+body+key/request index BEFORE uncertain handoff. Verify SHA256(body bytes)=original_preimage.canonical_body_sha256, parse C3 and validate operation's pinned request definition and target/header/body equality on recovery, including PENDING intent, before any replay. Never infer role/selectors/snapshot ACK cursor/hash from a result or regenerate a lost body; missing/mismatched body means unverified recovery, no new command/key. Stored native record<=32768encoded bytes remains conjunctive; reject oversized preparation before index/slot effects, never drop body to fit.

Operation matrix also pins request_definition, so body/profile semantics change the matrix/schema profile hash. OPENED.profile_schema_sha256 MUST equal original command profile; quota_owner_ref MUST be the same canonical admitted quota_owner_id (opaque owner identity, not a fresh caller alias); admitted_role MUST equal durable requested role under the admitted provider policy. Hash-consistent contradictory result fields reject even when receipt/index hashes match. Other successful result/target/epoch bindings remain checked; actual native allocation/proof/provider admission remains separate.

Review2 generator/validator sources and reports are included. Run only an OWN SCRATCH COPY to preserve frozen published raw bytes: build_bundle.py, node cross_language_vectors.cjs, then validate_bundle.py. Node report records actual runtime version; newly executed derivative reports do not inherit original raw hashes.40 review1 checks plus new matrix/numeric/body/identity cases remain explicitly synthetic, not actual endpoint/source-identity/consensus/containment proof.

## Review3 common depth and counters (A1-CLOSED-R2-01/A6-CLOSED-R2-02)

Review2 is preserved NOT APPROVED. All languages now consume the same raw-hash-bound codec-bounds.json; its digest is embedded in the schema profile and registry. Depth counts OBJECT/ARRAY CONTAINERS ONLY: root container depth1, nested container adds1, primitive leaves and object keys add0.12containers+primitive leaf ACCEPT;13containers REJECT before recursive parsing where input is raw. A primitive root has container depth0 (wire message shape still requires its declared object schema). No depth cap was disabled or raised.

Node budget counts EVERY JSON value once (object,array,string,boolean,null) PLUS every object key once as a string node. Keys are counted even when their values repeat or are empty.32768totalnodes ACCEPT;32769REJECT. Both codecs enforce the SAME general max64objectmembers,1..128ASCIIbytes/key,16384ASCIIcharacters/value string,1000entries/array and2097152rawASCIIbytes. Preparse bounds and canonical-writer bounds agree; specific frame/request/domain constraints are conjunctive and may be smaller. JSON strings and keys are printableASCII; numeric literals remain forbidden. Codecs cannot infer a domain's economic units/grammar/lineage from string syntax.

Executable generated recipes avoid multi-megabyte inline fixtures while deterministically checking exact2MiB/2MiB+1, node32768/32769 (INCLUDING keys), depth12/13withprimitiveleaves, key128/129, members64/65, string16384/16385 andarray1000/1001. Original A1depth12 CHANGE1173bytes (raw5b1a7c69…) is included and structurally valid; Python/Node bothaccept canonical bytes. Original A6nodecount CHANGE131292bytes (raw59aa160e…) is included, structurally within declared frame/payload byte bounds; BOTH reject NODE_CAP. Schema validity or byte compliance alone never overrides totalnode budget. RED reports preserve prior mismatches, including previously uncounted Node keys and previously missing Python generic bounds.

This remains a NEW OPT-IN C3 transport proposal, not compatibility approval for numeric resource domains or existing200row arrays. Resource.value arrays<=32 and strings<=16384 are still mandatory smaller domain-carrier limits. Do not silently truncate/split rows, stringify arrays to evade limits, convert numbers/amounts, round, relabel lineage, or reuse old schema hashes/root/cursors. Exact string units/scale/grammar/domain/root representations require A3/A4/A5/A7 ACK; a domain that cannot be represented remains UNAVAILABLE until separately versioned/approved representation. Native/provider/globalquota/containment/load/physical admission remains blocked.

Run own scratch copy: build_bundle.py; boundary_cases.py; node cross_language_vectors.cjs; validate_bundle.py. Both codecs verify the schema/bounds pin and emit only boundary-model results. Numeric-key ASCII ordering/exact-string vectors and all operation/result/UNKNOWN/body-recovery tests remain required. No shared/frozen consumers or PR31 changes; no prior ACK transfer.

Both direct MESSAGE writers now enforce the same container/node/key/string/array/byte budgets as decoders before constructing a complete encoded buffer. Aggregate encoded bytes are checked on each emitted token; forbidden numeric values are rejected even for direct writer calls. Python artifact_bytes/artifact_encode serialize schema constraints/reports only and are explicitly NOT message encoders. Guarded Python encode and Node canonical are the message writers. Direct writer boundary assertions accompany raw decoder cases; numeric lexical aliases may parse to values but may never produce an accepted C3 message.


Direct host-value writer constraints (review4): arrays require the ordinary Array prototype, exactly length plus dense own enumerable data indices, and no extra own keys. Holes and inherited indices cannot supply values. The writer captures own data descriptors and iterates indices; it never calls an input instance forEach or accessor. Plain objects require only enumerable own string data fields; symbols, hidden fields, proxies and unsupported host objects fail closed. Frozen plain data remains accepted. Node uses node:util.types.isProxy before reflection; this helper is a Node model, not a portable browser implementation. JSON-decoder inputs cannot create array holes. Existing depth, node, byte and domain caps remain conjunctive. No native/runtime admission follows from these model checks.
