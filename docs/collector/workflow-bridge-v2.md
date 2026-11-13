# Static V2 workflow preflight: DATA only

`scripts.ci_collector_c3_workflow_bridge_v2.select_static_authorization(raw, *, context, source_root, now=None)` returns detached `STATIC_VALID_NOT_ADMITTED` evidence. `selected` is always false while qualified workflow/factory/artifact/owner admission and actual protected review are missing. This is neither an application failure nor a phase/native permission. No caller readiness flag, callback, provider, token or kernel parameter exists.

The exact eleven-string context shape is the existing V2 broker shape, but `job_name` here is the static job `collector-preflight`; it must not impersonate the future assigned `collector-c3` job. Push/PR, wrong repo/attempt/source/context deny before source IO. The actual frozen codec checks canonical authorization bytes, integrity hash, V2 schema, typed bounds and expiry. Commit/hash strings identify input bytes; no HTTP acquisition or approval is inferred.

The static-source acquisition helper is private `_primary_source`: exact b4f raw helper bytes, bounded existing primary Git verification of the selected standalone checkout/head/tree. The fixed `integration/collector/v1/source-inputs.json` bytes are ordinary/single-link/bounded, re-read, and checked against the authorization and primary blob SHA1/SHA256/size. The source snapshot shape/count/byte bounds and case collisions are checked. A linked-worktree Git file is not a standalone primary checkout. This layer binds SourceManifest **bytes**, not its A5 semantic/source/software admission; no new owner schema or source authority is invented.

The original static-source increment contained no HTTP. The separate configuration-only helper below now defines a fixed readonly GET, but this source/inert verification performs no actual HTTP. There is no workflow edit, CLI, authorization-file writer, protected-review acquisition, native body, or call to `installation_service.run_collector_raw_qualification`. The genuine future entry contract remains unimplemented/unqualified and cannot be substituted with method existence, a signature, fake facts or `True`. V1 validator/provider/codec/helper bytes remain unchanged. Old V1 permissions do not authorize V2.

Inert TDD executes the actual selector and frozen codec, with only the private Git acquisition replaced by bounded synthetic snapshot DATA. Own scratch files exercise real readers/hash/link checks; the reparse test supplies inert lstat facts. One own hardlink pair is retained, not a junction/native-service qualification. Source tests do not run Git, HTTP, providers, app/SQL/service/SCM/ACL/native APIs or the future factory. The shared fixture builds in-memory inert authorization DATA, never an issued operator record.

Initial feature-absent scaffold: 20 cases,18 failures/2 errors (missing feature, not an old source defect). First implementation:20 PASS. Added actual case-colliding-directory regression:21 cases,20 PASS/1 assertion failure; original source/log retained. Minimal snapshot collision fix:21 PASS,zero failure/error/skip. These are working inert source controls, not canonical whole-source, hosted or C3 qualification. Real acquisition, workflow routing/title/protected environment, artifact transport and factory joins remain separately held pending Root source review/allocation.

# Typed-key regression correction

Context and primary-snapshot dictionaries reject non-builtin string keys before
set comparison or lookup. Snapshot head/tree values also require builtin strings
before equality. Regression cases retain the original five failing assertions
and verify rejection without invoking caller equality. The selected 23 inert
checks do not execute primary Git acquisition, HTTP, a workflow or a service.


# Protected-environment CONFIG observation before scheduling

`observe_protected_environment_config(authorization_raw, *, context, now=None)`
returns detached `CONFIG_OBSERVED_NOT_ADMITTED` data, always `selected:false` and
`execution_authority:false`. It is a configuration observation, never actual
review, source admission, job selection, method-presence readiness or A5 factory
permission. The context is the existing exact eleven-string static preflight
shape with job_name collector-preflight; actual V2 collector-c3 run/review/history
must still be acquired and validated later. Missing actual protected review
remains listed in missing_gates after a successful CONFIG observation.

Future workflow wiring must run this in a preflight job WITHOUT any environment
declaration and deny failures BEFORE scheduling any job referencing
collector-c3-operational-v2. GitHub may create a missing environment when a job
references it; neither declaring that environment in preflight nor scheduling an
ungated job is acceptable. This module does not implement workflow routing, close
the time-of-check/time-of-use gap, or prove future policy immutability. Later real
V2 approval acquisition repeats configured-policy and actual non-None review
history joins. No environment creation or policy settings writes exist here.

The private acquisition reads GITHUB_TOKEN internally, requires exact builtin
str,1..4096 characters and no CR/LF before headers. The sole endpoint is
https://api.github.com/repos/YehorBabenko88/unified-system/environments/collector-c3-operational-v2.
It calls the unchanged frozen ci_service_operational_admission.get, which uses
GET, fixed API/raw origin policy, NoRedirect,20-second timeout, exact URL/status,
no pagination and<=65536 response bytes. No public token, opener, provider,
callback, supplied API facts or selected/True override is accepted. Token/headers/
URLs/errors are not emitted or hashed. LocalService never receives this helper
or a CI token; later genuine Admin preflight is its intended consumer.

Before JSON decoding, response must be exact bytes and bounded; existing strict
JSON rejects duplicate/nonfinite keys/values. GitHub metadata extras are allowed,
while all security facts have exact builtin types before comparison: positive
environment ID/exact fixed name;1..16 protection rules with unique positive IDs
and known unique types; exactly one required_reviewers; actual bool
prevent_self_review;1..100 User reviewer entries with positive unique IDs and
case-insensitively unique valid logins, nested type User; approved_by must match
one exact login. Known wait_timer rules require builtin integer0..43200. Unknown
protection-rule meanings deny. can_admins_bypass, if present at environment/rule,
must be actual bool; deployment_branch_policy, if non-null, has the exact two
boolean fields protected_branches/custom_branch_policies. These checks observe
existing policy, never change it or add an unconditional two-person requirement.

Existing verify_protected_review(context, environment, history=None, ...)
performs CONFIG-only reviewer/self-review checks. If existing prevent_self_review
is false, the approved owner may equal current actor; true is respected and denies
that equality. None history here never stands in for later required actual V2
approval. Credential identity/configuration alone is not proof of human approval.

The closed result fields are status,selected,execution_authority,environment,
response_body,missing_gates. environment contains only id,name,required_reviewer
{id,login},prevent_self_review. response_body contains actual bounded response
SHA256/bytes; it is integrity metadata, not authority. The result uses canonical
JSON-compatible detached builtin facts; no raw API metadata/errors/body/token is
returned. Public failures are closed CONFIG_CONTEXT_REJECTED,
CONFIG_AUTHORIZATION_REJECTED,CONFIG_ACQUISITION_REJECTED or
CONFIG_PROTECTION_REJECTED, never exception text. Missing/403/redirect/oversize/
malformed/unknown/unconfigured cases deny.

Inert TDD:9 feature-absent tests produced13 missing-method errors; implementation
then32 PASS=9 configuration controls+23 unchanged static-selector regressions.
Only existing GET is patched with inert API bytes; no network, settings, approval
record, workflow/job/factory, provider/native/service/SCM/ACL/PG effect executes.
Existing selector tests retain own bounded file/hardlink fixture operations and
mock private primary acquisition. Logs are PowerShell text captures, not original
byte-stream qualification evidence. Source remains separate from actual hosted
workflow wiring, protected reviewer approval and Native C3 acceptance.
