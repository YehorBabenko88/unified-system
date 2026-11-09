# Native scheduler adapter and owned worker implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement task-by-task. Final fresh-context review, no implementer delegation.

**Goal:** Integrate actual existing A2 issuer with A5 job/owned-attempt lifecycle without another scheduler/authority, preserving original identities and fail-closed resource/UTC/fencing gates.

**Architecture:** A2 is the sole actual Consul transaction/issued Assignment/permit owner. A5 owns job adapter and retained Windows process/Job attempt inventory only, not a durable job ledger. Root selects SINGLE-JOB profile-v2/full20 binding; native13 remains unchanged. Actual shared ABI must be coACKed before positive wiring.

**Tech Stack:** Python async owner calls, existing Grid ConsulSessionAuthority, Windows retained process/thread/Job handles, existing Root custody/Journal only for original byte retention.

**Spec:** PR55C741 docs/intelligence/jobs/target-native-review1/DESIGN.md, new Root userdirective20261109 actualNativeAdmission/ResearchE2E, A2 actualissuer/worker ABI pending.

## Global constraints and exact bases

- BaseC741f36e8ddaf58bb8a709b986609916ec6f2358/treeb6e511476e81fb2480b4395b855849437f5b8636.
- Own prior worker commits e86b4cc and4801092 cherry-picked into new feature only; composite b5a54d51da7fbec2d25e4b23f9489a6033069f32/tree63b5eacdb5e98300669a1b4d32946f7bc4a3cead. Worker bytes remain5458dc5d... initially.
- Allowed gateway_jobs.py/gateway_worker.py/tests/gateway_jobs/**/docs/intelligence/jobs/**/owned workflows only. Root/shared contract/Grid/storage/UI files unchanged.
- No independent queue/broker/authority/ledger/PaperLedger; no fake issued rows/COMMITTED/boolean lease verifier.
- Unknown quota/headroom/RSS-vs-commit/CPU-share/UTC/lease/session/attempt proof => no resume/dispatch.
- Actual own bounded disposable worker tests allowed. PR52 VirtualAlloc remains SOURCE_ONLY, never invoked by this plan. No office/service/production/provider operations.
- Public submit remains DENY; native observations/proofs only actual expected owner APIs after exact coACK.

## Task1: actual suspended attempt preparation/inspection/abort

- [ ] Write tests first for default start deny, nonconstructible/foreign/copied attempt denial, exact source/interpreter pin rejection BEFORE native creation, duplicate original preparation returns SAME owned attempt, and native own suspended creation->membership/limit readback->inspect->abort/empty proof without ResumeThread.
- [ ] Observe RED for missing API, distinguish dependency/unavailable from native safety failures.
- [ ] Add preparation to gateway_worker.py only. Nonserializable inventory-owned attempt handle, retained actual process/primary thread/Job handles, original requestUUID, instance incarnation+attemptUUID, actual creationtime/image/source pin observations. At mostONE active preparation; stale/terminal attempt never silently recreated.
- [ ] Native CreateProcessW is suspended/no inheritance/fixed Python entry/minimized environment. Reuse exact pinned GridWindowsJob and actual private ABI; apply/query trial limits before any resume. Independent preparation NEVER resumes; actual A2 permit/worker profile is a later gate.
- [ ] inspect only actual own inventory; query retained handle creationtime/image/membership/process state and real host/process memory diagnostics. Descriptor is local DATA, not Assignment/permission/status proof.
- [ ] abort only exact owned attempt, latched before cleanup; prove Job empty+process signaled and close all retained handles. Uncertain exit remains poisoned/no release/no automatic retry.
- [ ] Run focused unit/fault assertions and explicit bounded native suspended-child test. No Meta, native grant or PR52 allocation. Source-bound pre/post receipts; commit exact source.

## Task2: cofreeze actual A2/worker-source ABI then job adapter

- [ ] Receive actual primary source and exact APIs for submit/lookup/begin_dispatch/require_dispatch/record_computed/cancel and actual current worker enrolment/session/resource hold source. Existing AssignmentAuthority execute/reconcile are closed; method-shape proposals do not satisfy this step.
- [ ] Publish A5 expected-instance attempt/capture and originalT/H/P/S/N/D mapping; require opaque actual issuer/worker handles, no JSON or None proof. Root/A2/A5 exact coACK before positive wiring.
- [ ] Add RED tests for changed original bytes/key/profile, foreign issuer/attempt, RUNNING replay no new start, stale incarnation/session/lease/epoch/fence, quota/resource/UTC unknown, cancellation race, restart same original lookup. Use actual owner disposable fixture only for positive native tests; unavailable fixture stays unavailable.
- [ ] Route gateway_jobs.py through fixed source-qualified owner classes, not caller callbacks. Own local inventory is not authoritative job status; status/cancel/restart derive actual original owner observations. No local receipt promotion.
- [ ] Run actual source-bound native contract tests only when real issuer/profile/ACL/quorum fixture qualifies. Record complete actual transaction proof/budget from A2, not candidate examples.

## Task3: bounded worker resume/computation and E2E

- [ ] CoACK real resource semantics/headroom (RSS != jobcommit,1000m != native10%), fixed source custody/interpreter/entry/bounded IPC/output/deadline, actual native worker session/attempt/current holds and one-use dispatch permit.
- [ ] Only then implement resume through actual expected A2 require_dispatch and same owned attempt. OS resume is not atomically Consul commit; cancellation/residual compute/final current fencing must be explicit.
- [ ] Execute actual A7 pinned producer on exact input; verify returned raw artifact/descriptor/source hashes and record COMPUTED through actual current A2 job CAS. No fake Meta success/native grant.
- [ ] Keep storage COMMITTED/projection/completion closed until actual A4 eligible two-domain closure+A2 sole publication receipt+A7 durable existing ResultStore projection coACK. No COMPUTED->COMPLETED alias.
- [ ] Actual worker loss/cancel/restart/dupe/noquorum/headroom/timeout/overflow source-bound tests, Windows/Ubuntu CI and A8 independent review; Draft PR, no merge/production.

## Review focus

Retained-handle lifetime/cleanup and new object after restart; original bytes/idempotency/immutable profile binding; prepared-child overhead before native reservation; actual worker source vs principal broker identity; resource units and absent current UTC/native lease proof; no fake positive owner fixture.

## Rulings and current gates

Ruling: task1 real suspended preparation/abort is independently authorized, but source bytes and local descriptors cannot admit a worker/job. No shared ABI guessed. Task2/3 positive wiring stays BLOCKED until A2 actual source/coACK and real resource/UTC qualification.
Ruling: no new durable attempt queue/ledger; process-local owned handle inventory prevents same-process duplicate preparation only. Durable restart idempotency must come from actual A2 original lookup before any future reprepare/resume.
Ruling: source-only VirtualAlloc52 is excluded even though new owned-worker tests are authorized.

## Task1 verification checkpoint (2026-11-09, not integration acceptance)

Observed 6 deterministic boundary tests plus 2 explicitly selected real Windows suspended-process cases: 8 PASS. Existing worker-limit fault assertions: 5 PASS. No ResumeThread, authority mutation, Meta computation, storage publication, or PR52 diagnostic execution.

Review fixes: frozen native13 constraints are fully checked before OS access; one process-wide preparation reservation blocks other inventories even with different declared node labels. Unknown cleanup poisons the owner and retains that refusal gate. Headroom/interpreter/source pin failures are covered by deterministic inert-kernel assertions. Native13 validation RED recorded 5 failing mutation subcases before the fix.

The local 16 KiB input bound follows frozen13/C3; one active preparation and 32 retained originals are conservative refusal safeguards, not load-qualified production limits. Headroom margins, committed-memory cap and CPU rate are preparation diagnostics only. No operational admission, RSS/CPU translation, lease duration, capacity age, batch size, storage budget or renewal limit is certified by this checkpoint.

Task1 source-bound receipt and final review remain required before completion. Tasks2/3 are pending actual A2 API/enrollment and ROOT runtime integration base; no positive shared wiring is present.

## Follow-up: explicit unsupported resource capabilities and closed recovery

ROOT acknowledged PR57/7338a80 and authorized standalone negative recovery/cancel tests. Current ROOT CI branch is not an integration runtime base. Implement a local DATA-only canonical capabilities report in GatewayWorker: admitted_fields empty, unsupported_fields explicit for CPU millicores/share, RSS, committed memory, commit/physical headroom. Each field records actual observation/configuration scope and the unresolved enforcement/mapping gap. Include this report in local OS observations; never return a grant or qualification PASS. Keep a machine-readable documentation mirror with exact equality tests.

TDD: test missing report RED, add report, verify report is immutable bytes and all six unsupported dimensions remain unsupported. Add isolated negative tests for fresh ResearchJobs instances retaining the same original during lookup/reconnect UNKNOWN, cancellation before/after failed lookup staying UNKNOWN, and reconstructed/foreign local observation failing inventory checks. These are local closed-boundary tests, not native restart/cancel acceptance. Re-run focused tests with exact source guard, fresh review, update existing Draft PR57 and notify ROOT/A2/A8. No resume, PR52 execution, authority fallback or shared API wiring.

## Follow-up: CPU hard-cap pure policy v1

ROOT requested executable conversion/qualification matrix, no CPU workload or resume. Add frozen pure-policy result and strict integer-only conversion in gateway_worker.py; tests in test_cpu_policy.py. Constrain v1 to one active group, full process/system affinity, matching active CPU count, known no CPU-controlled parent and DFSS disabled. Unknown/restricted/multi-group topology returns UNSUPPORTED. Bound total requested+already-reserved millicores by 1000*N. Derive rate=floor(10*m/N), reject zero quantum; represent delivered nominal bound as exact numerator rate*N / denominator 10 millicores, never floating point. Result always admission_supported=False/behaviorally_qualified=False. Caller topology/reservation inputs are DATA, not attestation or an atomic hold.

Observe actual retained suspended child's group/count/affinity in local snapshots, with before/after equality; do not set a derived rate or resume. Regression matrix checks rounding, boundary and aggregate no-oversubscription, unknown ancestry/DFSS and topology restrictions. Existing 1000-rate set/query stays diagnostic only. Add official Microsoft sources and qualification matrix; keep admitted_fields empty and RSS/commit distinct. Capture RED/GREEN, read-only review, exact-source tests and update PR57; notify ROOT/A2/A8.
