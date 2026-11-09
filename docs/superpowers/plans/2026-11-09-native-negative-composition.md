# Native Negative Composition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exercise actual mTLS authentication, fixed existing broker and native job handler to an honest DENY/UNKNOWN, with no admitted research execution.

**Architecture:** A new disposable-only Gateway composition opens an actual broker context over its owner-provided accepted loopback TLS socket, invokes fixed ResearchLabAuthority submit/lookup, validates only closed negative DATA and locally invalidates its own context. Existing Consul/Assignment remain the sole native authority; no public HTTP endpoint, broker, queue, worker or effect permit is added.

**Tech Stack:** CPython3.12.10, stdlib, existing pinned cryptography/httpx dependencies, actual isolated Consul1.22.2 three-voter/mTLS fixtures.

**Spec:** User Target Adapter v1 -> Native Job Admission -> Research E2E directive; A2 explicit REAL_MTLS_INTERNAL_NEGATIVE_COMPOSITION_NO_HTTP_ENDPOINT co-ACK; Grid539239e3c11ec9e86aa24365d74a68301fdf1185 docs/coordination/assignment-v1/native-job-admission-20261109/NEGATIVE-PATH-API.md SHA256a8261b30d12b4924e4f501ee6474dc6a2c0c3704eabe5353ebc48938fa2c7d3a.

## Global Constraints

- Base Root3af06455b601a328e94339327a0597eada802c38; preserve all existing files and manifest/Grid40e catalog.
- New Grid component539 module SHA1d578644ecbe881554bc3dd61d49227db2171ea2037d22599df44a73d698fd27; broker1f9714010143c5243c78494cb25bfe7f2d42e96301f57930212a2f5f3b9c869d; existing READ840 unchanged.
- Own NEW files only: unified_system/gateway_native_negative.py; tests/gateway_native_negative/**; docs/intelligence/native-negative/**; release/integration/native-negative-v1/**; dedicated workflow; this plan.
- No production/physical deployment, provider sends, orders, policy/network changes, protected diagnostics, worker Resume or CPU load.
- Strict real loopback lab authority and accepted TLS sockets only; do not accept a custom identity issuer, callback, JSON grant or duck-typed provider.
- Results are DATA only: submit DENIED/unqualified resources or UNKNOWN/unqualified reconciliation; lookup only UNKNOWN; original SHA exact, NOT_ATTEMPTED and effect_permitted is False.
- Authentication creates/invalidates owned native principal sessions. NOT_ATTEMPTED refers to job mutation; do not falsely claim zero native authentication writes.
- Per-request invalidate_context locally latches before await; native destroy is bounded best effort. Do not infer confirmed native retirement from successful return. Preserve original operation failure plus cleanup uncertainty.
- Source-only/negative qualification is not full scientific E2E, positive job admission, human Windows identity or public endpoint acceptance. Public submit stays DENY.

## Review Focus

1. Non-loopback or alternate source must reject before authentication/native IO.
2. Unexpected positive/result/type/equality claims never become a negative-path success or permission.
3. Current revocation, expiry, stale leader and no quorum remain actual errors, not resource observations.
4. Cleanup error must not mask the original operation error or falsely imply native retirement.
5. Fresh session binding preserves original bytes/digest and cannot cause job creation or duplicate effects.

## Task 1: Actual closed negative composition

- [ ] Add one real mTLS/Consul test importing the missing composition after actual fixture setup.
- [ ] Record RED with exact source identities and unchanged raw files; no fake callback or issued job row.
- [ ] Implement the minimum disposable composition and strict result validation.
- [ ] Add actual submit/replay, lookup, invalid original/socket, revocation/stale leader and real quorum-loss/cleanup tests; pure result-contract negatives separate.
- [ ] Run selected tests and independently review original-error/cleanup semantics.
- [ ] Commit new source; qualify fresh no-hardlink clone with strict primary Git bytes pre/post for Root and Grid, exact IDs/no skips, own process cleanup.

## Task 2: Publish reviewable source pair

- [ ] Add immutable successor component manifest, declared source-only permissions false and dedicated Windows/Ubuntu CI with hash-pinned dependencies.
- [ ] Preserve existing full mandatory security workflows and original RED evidence.
- [ ] Open own Draft PR, attach it, provide exact HEAD/tree/log/receipt hashes to A8 and owners.
- [ ] Keep hosted and independent qualification pending until actual terminal evidence arrives. No merge.
