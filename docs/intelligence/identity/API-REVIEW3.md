# Disposable read capability LOCAL ABI successor v1-review3

EXACT PROPOSAL ACK by A2; ROOT direction agreement; A3/A4 exact ACK pending.
Previous API-REVIEW2.md be18e8dfa3a9b2006a0e7abc2a9d9218f05b65a18b989a2b881c7d1445212c63
remains unchanged. Only this LOCAL owner/permit ABI is superseded, not binding
JSON schema or Grid/Assignment/Mux/shared native API.

Owner functions:
`get_dataset_manifest(request_bytes, *, owner_read_capability,
expected_identity_authority, pinned_owned_store)`
`query_market_data(request_bytes, *, owner_read_capability,
expected_identity_authority, pinned_owned_store)`

Root trusted composition passes its actual commissioned `self.authority` as
expected_identity_authority, never request JSON or a value taken from the cap.
Owners reject missing/bool/dict/None/method-shaped authority before object IO.
Only exact admitted unified_system.gateway_identity.DisposableIdentityAuthority
and GatewayReadCapability types/source are supported. Module name alone is not
source qualification or production provider admission.

EXACT authority owner-method successor (Root final selected alternative):
`DisposableIdentityAuthority.require_issued_read(capability, *,
tool_name, request_bytes, binding, owned_store) -> None`

expected_identity_authority is REQUIRED in owner functions, no default. Owner
checks exact admitted authority type and DIRECTLY calls fixed class method
DisposableIdentityAuthority.require_issued_read(expected_identity_authority,
capability,...). It checks exact capability and authority types, cap._issuer IS
expected_identity_authority and actual issuer inventory membership, then DIRECTLY
dispatches fixed DisposableIdentityAuthority._check(expected_identity_authority,
capability,...) including session/request/resource/store checks.
No dynamically selected issuer._check, callback or method-shaped None provider.
Foreign valid issuer even sharing the same Store, CA, identities and resource grant
cannot authorize this Root composition. Object.__new__ forged cap without real
inventory membership denies. This remains a trusted in-process Root boundary,
not a sandbox against arbitrary malicious Python constructing issuer internals.

Each call counts EXACTLY one current-check. Fixed server-owned budgets:
unified.get_dataset_manifest =2 (before read, before return);
unified.query_market_data =7 (before each of six object reads, before return).
No extra entry check, caller budget, cap remint, omitted check or manifest/query
tool alias. Wrong expected issuer/tool/request/binding/store never grants or
consumes successful-check count. Additional future reads require new exact profile.

require_issued_read is synchronous. Exact None success, otherwise closed
GatewayIdentityDenied/GatewayIdentityUnavailable; no awaitables/nonNone fallback.
Owners do not run/close/schedule foreign coroutines or trust arbitrary None-return.
Existing capability-local check_current remains unchanged for prior local tests;
it is NOT sufficient for owner disclosure. A3/A4 must use the new fixed authority
owner method above at every read/return boundary instead of direct cap checks.

Binding schema unchanged unified.gateway.read-binding.v1-review2: dataset_id,
dataset_revision LOCAL resource counter, manifest_sha256, schema_sha256, consumer_id,
view_id plus schema. GET schemaSHA=manifest root schema; QUERY schemaSHA=row schema.
Exact original bytes bind independent tool/subrequest digests. Store is actual
Root-pinned object identity. Dataset/manifest/native revisions remain separate.

Audit, parser, clock, mTLS commissioning and nonread closure remain as exact source
refinement documents. Root proves actual server cert/key/context load by actual
client DER pin; profile DER is not that proof. Actual source SHA/issuer lifecycle
qualification and positive cross-owner integration require subsequent review.
No production/native identity, publication/coverage/registry proof or mutation.
