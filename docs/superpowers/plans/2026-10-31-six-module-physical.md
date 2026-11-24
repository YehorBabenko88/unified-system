# Six-module integration implementation plan
> **For agentic workers:** Use superpowers:executing-plans for inline implementation, with independent final review.
**Goal:** Reuse existing branches to produce one simulation/research system and prepare actual 5–6-host Windows deployment.
**Architecture:** Modular coordinated release, one logical owner per function. Preserve source-owned receipt validation and fail-closed physical acceptance.
**Tech Stack:** Python 3.12, Node 22/24, PostgreSQL, Windows PowerShell 5.1/7.
**Spec:** ../specs/2026-10-31-six-module-physical-design.md

## Global constraints
No real orders. No remote merge/branch deletion without confirmation. Do not claim physical PASS from models. Do not request inventory before full deployment preparation. Preserve existing tests and signature/TLS/checksum verification.

## Review focus
- Missing or duplicated module identities must not produce a valid coordinated release.
- Synthetic or partial fleet observations must never qualify physical acceptance.
- Result/schema mismatch must fail before lifecycle progress.
- Host failure during activation must retain a known recoverable release.
- Unavailable GitHub/physical evidence must remain explicit and block readiness.

### Task 1: Audit and recovery
- [x] Inspect main HEADs, remote refs and existing integration branches; record restrictions on API/CI observations.
- [x] Save audit records and recoverable existing local refs; classify branch differences without deleting refs.
- [ ] Obtain unavailable Grid/Strattester pinned branch sources and hosted PR/CI evidence.

### Task 2: Consistent six-module release inventory
Files: unified_system/module_catalog.py, registry.py, lockfile.py, installer.py; tests/test_module_catalog.py.
Interface: MODULE_IDS and OWNER_CAPABILITIES; existing negotiate(), validate_lock(), plan() remain compatible.
- [x] Write tests for a six-module lock/plan, all descriptor identities, duplicate/unknown rejection and single owner per capability; run RED.
- [x] Implement shared inventory, retaining bounded strict validation; run tests GREEN plus full unittest discovery.
- [ ] Commit code, tests and evidence.

### Task 3: Physical acceptance accounting
Files: unified_system/physical_acceptance.py; tests/test_physical_acceptance.py.
Interface: assess(inventory, records, release_sha, run_id) returns overall NOT_RUN/BLOCKED/RECORDED and per-node scenario states; it never grants deployment authority or authenticates untrusted records.
- [x] Test complete exact 5/6-node records, missing nodes/scenarios, duplicates, stale/wrong release, synthetic evidence and failed checks RED.
- [x] Implement deterministic bounded admission accounting and CLI JSON output; record authentication as unverified, never physical PASS.
- [ ] Verify full regression suite and commit.

### Task 4: Positive data pipeline and reusable runtime
- [ ] After source access restored, reuse Grid/Strattester receipt-capable implementations; add positive data-acquisition → Math → strategy/backtest → results → Terminan contract/E2E.
- [ ] Add explicit MetaAnalyse adapter; avoid direct shared-table writers.
- [ ] Extend existing update/install owners with six-module release manifest and actual service lifecycle; test restart, idempotency, failure fencing.

### Task 5: Deployment and acceptance
- [ ] Prepare authenticated local agent and least-privilege owner policy; exercise Windows installation, canary/rolling/rollback, backup/restore and failure cases.
- [ ] Verify exact-head hosted CI, artifact authenticity and required matrices.
- [ ] Only after full preparation request inventory/access; execute on all expected physical hosts and collect actual signed evidence.
- [ ] Keep project incomplete while any required physical case, service or node is unverified.

