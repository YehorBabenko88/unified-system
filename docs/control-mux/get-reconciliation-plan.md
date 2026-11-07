# Real GET Reconciliation Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline. No new sub-agent implementation needed. Steps use checkbox syntax.

**Goal:** Implement isolated real HTTP GET command reconciliation over actual existing Grid Consul evidence, default native/WSGI still closed.
**Architecture:** Existing GET_COMMAND current-auth read operation only. Extend the existing atomic observation to return the separately validated HTTP200 review2 wrapper from the SAME captured native records/index. Do not rerender original mutation responses or add consensus/role/permission.
**Tech Stack:** Python3.12.10, pinned C3/jsonschema, existing Grid58cfe ConsulSessionAuthority, actual isolated Windows Consul1.22.2 triplet; dedicated Linux/Windows source runner.
**Spec:** exact reconciliation-v3-review2.schema.json a7c9730c6125320c537bd41ddb0d364cfc08eb92ec05d9eb20e73c956868c64e; semantic checker991cd9c90a2e93e9353f3b5bb93f2a1aea9e229cd4d4e9d3a1f90cb3523044f5; protocol9ca2242d692585cdc46840c760c37eda700b718c651915d3114204b56d04655d plus preserved review1 HTTP details. Base0c21256e30aeb3a4184dda97a2bebf24c047acd0/tree3a7568acf3a6bc5fd99a6986db554daa9e3919cf, new feature/agent2-control-mux-get-20261107; refs PR32/33 untouched.

## Global Constraints
- Only own control_mux/tests/docs/dedicated workflow/source runner. Frozen contracts/checker/vectors and Root identity guard source unchanged.
- GET /control/v3/commands/<canonical UUIDv4>, current X-Request-ID query UUID different from original; no body/Content-Type/idempotency or expected-epoch command headers. Current query never enters mutation UUID registry.
- EXACT existing GET_COMMAND in native resolve/revalidate and actual Root policy; no RECONCILE permission/role extension. Existing Root schema cc286b defines this operation. Existing four identity ModifyIndices checked with all actual original evidence in one consistent read transaction; no leader required for authorized history.
- HTTP200 wrapper only for fully linked definitive original evidence. Original mutation status/body/digest immutable. receipt_modify_index actual observed positive native index. Full encoded wrapper<=16384. max-u63 index may be used in local SIZE preflight only, never returned/stored as evidence.
- Clean missing/PENDING503 existing error_v3 reasonNONE; corrupt/conflicting/missing-linked-terminal evidence503 RECEIPT_AMBIGUOUS; no invented digest; current query ID correlation. Owner disclosure denied403/NONE; actual RBAC403/ROLE_DENIED; typed actual invalid/expired human401; provider/unknown exception503. Mapping submitted to Root/A6 for explicit review; no production/native activation.
- No READY/ACK204/release/barrier/snapshot/native invention; defaults503. Existing42cases and18unit kept. New results require exact source proof/review, not old ACK transfer.

## Current-auth field mapping
| Input/operation | Existing exact consumer/guard |
|---|---|
| GET route operation | GET_COMMAND, already in Root _OPS and provider protocol; no new permission. |
| RawRequest/native handle | Root actual provider resolves current admitted context; test fixture explicitly synthetic. |
| Current context identity | Existing cluster/actor/session/owner/role/enrollment/native handle, no schema additions. |
| Actual guard records | Existing Root fixed four keys and decoder, current role/GET_COMMAND/enrollment plus verify_records exactNone/raise; store captures native indices. |
| Original path UUID | Original durable index/key/preimage/receipt/response; original actor/session retained, current owner/actor disclosure match. |
| Current query UUID | Header X-Request-ID; HTTP wrapper query_request_id, distinct from original; no intent/index writes. |
| Result index | Actual captured receipt.ModifyIndex, protected in same read transaction; not a clock/lease/permission. |

## Review Focus
- Cross-owner/current-revoked identity must never disclose historical success; current session can differ only under actual admitted same-owner binding.
- Record deletion/index churn between read and read-transaction validation must deny; never combine a validated outcome with separately reread evidence.
- Hash-consistent body/preimage mismatches, original204 nonempty/null-schema mismatch and original202 current-state mixing must deny before wrapper output.
- Missing/PENDING/UNKNOWN and oversized wrapper must503 with no digest fabrication, mutation, truncation or hold release.
- GET parser duplicates/framing/query-original alias/command-only headers and no-leader history; default closed before provider/read.

## Task1 — RED endpoint and semantic tests
- [x] Add unit parser/default-closed tests; actual HTTP GET201 history test fails503 on current source before implementation. Preserve RED log.
- [x] Add runtime validator conformance24vectors and independently varied cap/link negatives; no actual204 production write path.

## Task2 — Actual observation/wrapper and HTTP GET
- [x] New product reconciliation.py pins exact schema, validates full review2 semantics and cap, no authority by schema alone.
- [x] Extend _observe privately with current query correlation; definitive wrapper built only from same captured/validated native index+command+receipt+response. Existing reconcile/mutation responses unchanged.
- [x] Add read method using existing _identity GET_COMMAND; distinguish missing/ambiguous from provider/quorum failure without fake digest. Keep existing owner redaction.
- [x] Add terminal wrapper-size preflight before actual final receipt commit for implemented OPEN/SUB/CLOSE; max-index size bound never used as observed evidence.
- [x] Wire GET raw parsing -> native resolve GET_COMMAND -> actual store observation -> separate200 or existing503/403; no lease-provider call on GET.

## Task3 — Actual HTTP/Grid/Consul fault evidence
- [x] Real HTTP wrapper original201/202, current/original query correlation, exact original bytes/digests/receipt native index, no private KV changes on GET.
- [x] Real HTTP missing/PENDING/corruption/index-race/revoked-current/cross-owner/no-quorum failures; no original mutation writes or digest invention. Positive historical reads need no active app leader.
- [x] Preserve prior42case IDs/18unit; append exact new mandatory inventory and pin model vectors. Source guard8 unchanged.

## Task4 — Publish exact source and review
- [ ] Dedicated branch/workflow selection, new owned docs/progress only. Fresh raw Git materialization and -I-B complete source-bound unit/real/guards run; no skips or cached-bytecode substitution.
- [ ] Independent focused review, fix observed defects, exact raw evidence/output hashes, separate Draft PR. Current Linux/Windows hosted status recorded honestly.
- [ ] Root/A6 current-auth/error/correlation mapping and fresh A8 exact-source audit before owner integration; no native/office/production admission.

## Root/A6 clarification closure and executable progress
Root/A6 chose clean missing/PENDING503/NONE; actual ambiguity RECEIPT_AMBIGUOUS; provider/quorum uncertainty503. Actual native invalid/expired401 only via exact closed NativeAdmissionError kind; unknown/subclass/malformed/foreign/untyped503. Owner/actor disclosure403/NONE vs actualRBAC403/ROLE_DENIED. Four provider signatures, Root schema and GET_COMMAND unchanged. Current valid query correlation on401/403/503, invalidnull. Only native callback boundaries preserve typed denials; post-read storage/hash faults cannot become session denials. This is internal proposed error-class ABI only pending exact source/native-owner review.
RED logs preserved in A2workspace work/mux-get-{parser,document,endpoint}-RED.log: actual initial HTTPGET503 expected200 observed. First green iteration caught wrapper-local raw shadowing via model vectors, and lost-prepare resume exposed size-preflight access to a branch-local preimage; fixed to use original captured stored preimage. Second real iteration correctly failed fault harness assumption: Consul same-valuePUT is a no-op. Actual separate probe first10/same10/changed12; race now changes policy revision or explicitly recreates SAME receipt bytes, not fabricated indices. No old failed run relabeledPASS.
Local preliminary execution:33unit PASS;68real cases PASS (42retained+26GET), native identity explicitlysynthetic; current-source mandatory inventory further adds4negative classification cases for72total pending fresh final qualification. Actual Root provider remainsabsent/default503. maxindex2**63-1 appears only in discarded pure SIZE preflight, never stored/returned/claimedobserved.

Complete current-source local72real/33unit PASS; clean independentp0review/33unitrerun. Final immutable source qualification, hostedCI and Root/A6/A8 exactsource reviews remain pending.
