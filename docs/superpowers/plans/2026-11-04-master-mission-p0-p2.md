# MASTER MISSION P0–P2 implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Preserve existing Draft PRs and review each deliverable before pushing.

**Goal:** Remove measured blockers and build a real install/uninstall path over the existing admitted LAB runtime, without representing plans as installed software.

**Architecture:** Unified owns installation, progress and operator authorization. Existing module repositories retain their migrations and engines. The installer consumes an externally pinned closed capsule; SCM actions reuse the Grid ownership boundary. Terminan consumes the same durable installation progress rather than maintaining a second installer state.

**Tech Stack:** Python standard library, Windows SCM/PowerShell adapters already in Grid, existing browser Terminan, SQLite durable journals, pinned Python/Node/PostgreSQL capsules.

**Spec:** Three user MASTER MISSION attachments dated 2026-11-04; source inventory `master-mission-20261104/installer-inventory.json` in the chat workspace. Prior evidence remains scoped to its exact source/configuration.

## Global constraints

- LAB_SIMULATION / PAPER ONLY; zero real orders and no production trading credentials.
- No merge, branch deletion, security-policy bypass or unrelated data/service deletion.
- Office topology is LS5 → PC1, PC2, PC3, PC4, LS7. ADMINIT is only a separately admitted SINGLE-PC pilot.
- Source changes and isolated tests are authorized. Each physical installation, service/ACL/database mutation and destructive removal requires the owner's concrete phase confirmation.
- External manifest SHA256, exact closure, source provenance, dependency locks and node-only worker credentials remain mandatory.
- Missing evidence is NOT_RUN/BLOCKED; an unsigned LAB capsule is not a trusted signed release.

## Review focus

- Missing Windows process context must fail before starting SSH; never forward trading/database secrets as a workaround.
- An installer recovery attempt must not adopt a foreign service or overwrite existing data.
- Bootstrap progress must survive restart and remain visibly distinct from actual readiness.
- Uninstall must bind every target to an install receipt and require separate confirmation for complete data removal.
- UI/Telegram operations must use authenticated allowlisted control APIs, not arbitrary shell execution.

### Task 1: Preserve the measured Windows SSH context

**Files:** create `unified_system/worker_transport.py`; test `tests/test_worker_transport.py`.

**Interfaces:** `windows_ssh_environment(source=None) -> dict[str,str]`; consumes trusted parent OS context, returns an isolated client environment with required PROGRAMDATA and no application credentials. This is transport context only, not enrollment authority.

- [x] Reproduce missing PROGRAMDATA rejection and secret filtering in tests; retain actual ssh-G/remote archive A/B receipts.
- [x] Implement the minimum environment factory with case-insensitive duplicate rejection and bounded valid strings.
- [x] Run targeted tests and independent review; include the source in the existing Unified Draft PR.
- [ ] Integrate this factory into the installer-owned SSH executor when that executor replaces the work-only commissioning harness. Do not silently use an old operator lock which omits the new source file.

### Task 2: Resolve mandatory Math and Terminan checks

**Files:** Math existing loader/test diagnostics and source proof; Terminan six workflow concurrency groups/cache job budget.

- [x] Obtain exact cancellation annotations and preserve workflow steps/matrices while fixing event identity collisions.
- [x] Independently verify and push Terminan correction `5ed7ccb41cdc22d24f56c9f4a5e981df2d21faa2`.
- [x] Push Math diagnostic `4a8c2fa833ab4b8deb3b9ce33dd37cd1ff71f50c`: pre-cleanup child state plus separate non-qualifying ProgramData experiment.
- [ ] Wait for actual current-head CI; inspect results before choosing a causal fix. No timeout/security waivers and no passing interpretation of diagnostic variants.

### Task 3: Installer transaction and progress

**Existing interfaces:** `lab_release.verify_capsule`, capsule preparation/source fences, Grid receipt-checked service adapter/deployment journal, `installer.plan`, module-owned migrations.

- [ ] Define CONTROL/WORKER/SINGLE-PC install identity, source/manifest-bound operation plan, resource ownership and rollback receipt. Keep the old dry-run planner explicitly dry-run.
- [x] Implement a durable non-authorizing progress journal and snapshot with restart/CAS/idempotence checks; connect actual installer phase producers in the next slice. Root verification: 45 tests passed, zero skips.
- [ ] Build a thin bootstrap UI over that stream; transfer viewing to the existing Terminan after its real readiness, without starting duplicate backends.
- [ ] Add explicit elevation boundary for creating only receipt-bound LAB services. Design LocalService code/private-state ACLs before any physical execution.
- [ ] Verify isolated install → failure rollback → resume using fake SCM/filesystem boundaries before requesting a physical SINGLE-PC phase.

### Task 4: Uninstaller and first physical gate

- [ ] Implement preserve-data / remove-configuration / complete-removal plans over the same ownership receipts, rejecting foreign resources and links.
- [ ] Verify partial teardown recovery, credential revocation/drain and reinstall; full removal remains separately confirmed.
- [ ] Produce a concrete SINGLE-PC phase plan listing computer, paths, services, ports, data and rollback. Request owner's confirmation only once the reviewable installer/uninstaller artifacts and P0 evidence are ready.

P3–P12 require further subsystem plans grounded in the resulting source and receipts: sequential office rollout, one distributed authority, real historical/scientific/cluster pipelines, causal paper ledger, Terminan, existing Telegram extension, populated recovery and measured load tests. This plan is not physical acceptance and grants no infrastructure mutation.
