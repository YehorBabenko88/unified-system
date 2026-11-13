# Static V2 workflow preflight: DATA only

`scripts.ci_collector_c3_workflow_bridge_v2.select_static_authorization(raw, *, context, source_root, now=None)` returns detached `STATIC_VALID_NOT_ADMITTED` evidence. `selected` is always false while qualified workflow/factory/artifact/owner admission and actual protected review are missing. This is neither an application failure nor a phase/native permission. No caller readiness flag, callback, provider, token or kernel parameter exists.

The exact eleven-string context shape is the existing V2 broker shape, but `job_name` here is the static job `collector-preflight`; it must not impersonate the future assigned `collector-c3` job. Push/PR, wrong repo/attempt/source/context deny before source IO. The actual frozen codec checks canonical authorization bytes, integrity hash, V2 schema, typed bounds and expiry. Commit/hash strings identify input bytes; no HTTP acquisition or approval is inferred.

The only real acquisition helper is private `_primary_source`: exact b4f raw helper bytes, bounded existing primary Git verification of the selected standalone checkout/head/tree. The fixed `integration/collector/v1/source-inputs.json` bytes are ordinary/single-link/bounded, re-read, and checked against the authorization and primary blob SHA1/SHA256/size. The source snapshot shape/count/byte bounds and case collisions are checked. A linked-worktree Git file is not a standalone primary checkout. This layer binds SourceManifest **bytes**, not its A5 semantic/source/software admission; no new owner schema or source authority is invented.

This increment contains no workflow edit, CLI, HTTP, authorization-file writer, protected-review acquisition, native body, or call to `installation_service.run_collector_raw_qualification`. The genuine future entry contract remains unimplemented/unqualified and cannot be substituted with method existence, a signature, fake facts or `True`. V1 validator/provider/codec/helper bytes remain unchanged. Old V1 permissions do not authorize V2.

Inert TDD executes the actual selector and frozen codec, with only the private Git acquisition replaced by bounded synthetic snapshot DATA. Own scratch files exercise real readers/hash/link checks; the reparse test supplies inert lstat facts. One own hardlink pair is retained, not a junction/native-service qualification. Source tests do not run Git, HTTP, providers, app/SQL/service/SCM/ACL/native APIs or the future factory. The shared fixture builds in-memory inert authorization DATA, never an issued operator record.

Initial feature-absent scaffold: 20 cases,18 failures/2 errors (missing feature, not an old source defect). First implementation:20 PASS. Added actual case-colliding-directory regression:21 cases,20 PASS/1 assertion failure; original source/log retained. Minimal snapshot collision fix:21 PASS,zero failure/error/skip. These are working inert source controls, not canonical whole-source, hosted or C3 qualification. Real acquisition, workflow routing/title/protected environment, artifact transport and factory joins remain separately held pending Root source review/allocation.

# Typed-key regression correction

Context and primary-snapshot dictionaries reject non-builtin string keys before
set comparison or lookup. Snapshot head/tree values also require builtin strings
before equality. Regression cases retain the original five failing assertions
and verify rejection without invoking caller equality. The selected 23 inert
checks do not execute primary Git acquisition, HTTP, a workflow or a service.
