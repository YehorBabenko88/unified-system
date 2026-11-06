> Latest bounded update: [F11 fix recheck](phase9/f11-fix-review.md). Current open findings:6 P1/1 P2; F11 fixed offline at exact0b3af3e. Hosted/runtime/physical/Tailscale acceptance remains BLOCKED; earlier snapshots are historical.

# Independent security, CI and physical acceptance — Agent 8

Snapshot: 2026-11-06T15:05:26.716427+00:00 (6 November 2026, Europe/Berlin).

**Overall: NO-GO. TAILSCALE_REMOVAL: BLOCKED / NO-GO.** No merge, deployment, network reconfiguration, Tailscale removal, real orders or destructive cleanup performed by this audit.

Open findings: **P0: 0 independently confirmed defects; P1: 6; P2: 1.** This is not proof that no P0 exists. Failed mandatory gates and unperformed physical qualification independently prevent GO.

This is an interim independent acceptance report. It does not assert completion of the physical mission. Findings are assigned to the repository owner via Integration Owner; production implementation was not edited.

## Scope and evidence boundaries

Two independently fetched, paginated open-PR snapshots contain 432 stable PR HEADs. Latest check-runs were enumerated for all 432 SHAs with pagination. This verifies identity metadata at the observation time, not every checkout or artifact. The new audit PR is outside this baseline snapshot.

Detailed workflow runs, latest-attempt jobs and artifact metadata were collected for the newest three open PRs in each repository and the six local checkout SHAs (deduplicated). Latest run/job/artifact lists use up to 100 entries; any larger totals are coverage gaps. Older PRs have check metadata only. Artifact payload review covers eight selected ZIPs, not every CI artifact.

All eight downloaded ZIP hashes match GitHub API SHA-256 digests. These hashes establish downloaded-byte consistency, not release authority or physical acceptance. Native subject source hashes additionally match independently read exact-HEAD Git blobs. Terminan cache manifest member hashes match. JUnit XML was parsed independently.

## Repository and CI inventory

| Repository | Open PRs | Stable HEAD snapshots | HEADs with failed latest checks | No checks |
|---|---:|---:|---:|---:|
| unified-system | 20 | 20 | 8 | 0 |
| bybit-cluster-grid | 102 | 102 | 18 | 0 |
| strattester | 65 | 65 | 50 | 0 |
| math | 108 | 108 | 74 | 0 |
| meta_analyse | 72 | 72 | 27 | 1 |
| Terminan | 65 | 65 | 43 | 0 |

Check failures include historical branches and explicit NO-GO sentinel jobs; these counts are not distinct product defects. A successful check subset does not establish all mandatory CI PASS.

Newest PRs below are observation targets, **not an approved six-repository release**. Matrix rows refer to these observed heads; cross-node source binding remains UNQUALIFIED.

| Repository | PR | Exact observed HEAD |
|---|---|---|
| unified-system | [#20](https://github.com/YehorBabenko88/unified-system/pull/20) | `7ac7983acd4f7a5ba10c579e706f3d1f5a800722` |
| bybit-cluster-grid | [#261](https://github.com/YehorBabenko88/bybit-cluster-grid/pull/261) | `71084a336520187d6e260531a2f5d15555ba0e0c` |
| strattester | [#70](https://github.com/YehorBabenko88/strattester/pull/70) | `25eb939f8a816a80ac7c042ce75ec4d9173cd4ce` |
| math | [#111](https://github.com/YehorBabenko88/math/pull/111) | `11c3c470ebec9f9fdb6ec1b69e77b7b8aeea653a` |
| meta_analyse | [#76](https://github.com/YehorBabenko88/meta_analyse/pull/76) | `2c4db055e56e36384a2661d443f9abc7b2331e90` |
| Terminan | [#68](https://github.com/YehorBabenko88/Terminan/pull/68) | `7ed3708df53c8850fd11fc8331440bdfee99aa3e` |

## Independent execution

Windows local Python 3.15.2, isolated clean checkout of Unified #20 `7ac7983acd4f7a5ba10c579e706f3d1f5a800722`. Auditor-owned offline harness: **7/7 PASS**; upstream targeted negative regression: **23/23 PASS**. Logs: [independent negatives](evidence/independent-negatives.log), [upstream negative regression](evidence/upstream-negative-regression.log). Python 3.15 is not a substitute for mandatory CI Python 3.11/3.13.

The tests cover absent authenticator, denied-provider seam, wrong actor/role/node/service identity, unsupported order/destructive/LIVE intents, duplicate/nonfinite/oversized/deep JSON, missing/cloud/duplicate physical evidence and complete fabricated physical PASS claims. Session denial uses an auditor-owned provider double; no actual issued or expired human session was tested. All 90 fabricated physical ledger records still yield RECORDED_UNVERIFIED and no deployment authorization.

Reproduction: `python -I -S -B independent_negatives.py --source PATH_TO_CLEAN_UNIFIED --expected-head 7ac7983acd4f7a5ba10c579e706f3d1f5a800722`.

## Open findings

### A8-F01 — P1 — unified-system: Windows fixture/security acceptance fails

Observed: ACL_CANONICAL_ROOT_REQUIRED; Python 3.11 WindowsPath.is_junction errors; missing five-source-evidence upload.

Required correction: Rebase/include reviewed fixture fixes and independently rerun full Windows 3.11/3.13 plus PowerShell/pwsh security gates.

### A8-F02 — P1 — bybit-cluster-grid: Source admission regressions fail CI

Observed: KeyError owned_source_admission in tests/test_owned_control_source.py; downloaded PG18 JUnit: 1631 cases, 4 failures, 14 skipped.

Required correction: Restore source-admission test lifecycle isolation without skipping revocation negatives; rerun preflight and PG18 qualification.

### A8-F03 — P1 — math: Mandatory Windows Node 22/24 cells fail

Observed: ERR_ASSERTION / DIAG_CHILD_STATUS / worker_phase=COMPILE; platform result tests=98, pass=97, fail=1; Full CI coverage failed.

Required correction: Fix native compile/child-status path and run both mandatory Windows cells plus coverage aggregator.

### A8-F04 — P1 — math: Selected Windows evidence tests merge SHA

Observed: PR HEAD 11c3c470ebec9f9fdb6ec1b69e77b7b8aeea653a; downloaded receipts and checkout log use f1070af8698a5ef584fece43057be049e307ef2a.

Required correction: Run explicit exact-PR-HEAD qualification. Retain merge-result qualification as separate evidence; do not relabel it.

### A8-F05 — P1 — unified-system: Real operator authentication incomplete

Observed: Native artifact verifies compile/invalid-context only: authentication NOT_QUALIFIED, runtime_factory DENY, positive subject extraction NOT_RUN.

Required correction: Qualify actual native inbound context, TLS/CBT, operator session expiry/revocation, peer identity and per-human backend RBAC.

### A8-F06 — P1 — all: Coherent physical acceptance unavailable

Observed: No independently verified coherent release manifest, real all-node cluster, fault-injection run or alternate-access recovery proof for this audit.

Required correction: Integration Owner must publish immutable six-repo candidate and mandatory registry; obtain separate physical fault-injection authorization and execute acceptance.

### A8-F07 — P2 — all: Mandatory skip coverage unresolved

Observed: Passing job conclusions coexist with skipped JUnit cases; no authoritative case-to-requirement map supplied to auditor.

Required correction: Publish mandatory IDs, expected counts/platforms and permitted optional skip reasons; missing/skip/cancelled cannot count as PASS.

Original failed-job URLs, run/attempt/job IDs and decoded log diagnostics: [failure-diagnostics.json](failure-diagnostics.json). Downloaded artifact receipts and digest checks: [artifact-verification.json](artifact-verification.json). Payload checks: [artifact-content-checks.json](artifact-content-checks.json).

Strattester #70 financial-integration run 42052514344 deliberately exits 2 in system-acceptance-NO-GO: component gates PASS while external physical/OOS/coherent snapshot/native isolation/GPU/upstream-equivalence remain BLOCKED. This is an honest closed gate, not a falsely passing suite.

Math provenance `qualified=true` describes its source/provenance check; failed platform test receipts remain failed. It is not interpreted as a system PASS.

## Requirement results

The complete [acceptance-matrix.csv](acceptance-matrix.csv) supplies every requested field, per requirement and applicable repository. No entry below asserts physical PASS.

| ID | Requirement | Status |
|---|---|---|
| A8-01 | Exact HEAD всех PR | BLOCKED |
| A8-02 | CI runs и artifacts | FAIL |
| A8-03 | Обязательная Windows-матрица | FAIL |
| A8-04 | LAN transport | BLOCKED |
| A8-05 | Tailscale independence | BLOCKED |
| A8-06 | Peer authentication | BLOCKED |
| A8-07 | Operator RBAC | BLOCKED |
| A8-08 | Expired sessions | BLOCKED |
| A8-09 | Unauthorized commands | BLOCKED |
| A8-10 | Consensus split-brain | BLOCKED |
| A8-11 | Fencing | BLOCKED |
| A8-12 | Coordinator crash/restart | NOT_RUN |
| A8-13 | Worker loss | NOT_RUN |
| A8-14 | Storage corruption | NOT_RUN |
| A8-15 | Replica recovery | NOT_RUN |
| A8-16 | Backup/restore | NOT_RUN |
| A8-17 | Historical gaps | NOT_RUN |
| A8-18 | Live reconnect | NOT_RUN |
| A8-19 | Duplicate events | NOT_RUN |
| A8-20 | Resource overload | BLOCKED |
| A8-21 | Node schedules | NOT_RUN |
| A8-22 | Terminan relocation | NOT_RUN |
| A8-23 | Concurrent Terminan sessions | NOT_RUN |
| A8-24 | Update/rollback | NOT_RUN |
| A8-25 | Safe uninstall | NOT_RUN |
| A8-26 | Отсутствие real orders | BLOCKED |
| A8-27 | Отсутствие несанкционированных сетевых изменений | BLOCKED |
| A8-28 | Нет фиктивных PASS / mandatory skips | BLOCKED |

## Tailscale removal gate

LAN transport, real consensus, replication, Terminan on every node, failover, restart recovery and independently verified access recovery without Tailscale are all UNQUALIFIED in this audit. Tailscale remains present and Up. Even a later GO must not trigger automatic removal.

## Next actions

1. Integration Owner publishes immutable candidate manifest, node inventory, API/ownership contracts and mandatory case/platform registry.
2. Repository owners close A8-F01–F05 and supply original run/attempt/artifact URLs; auditor rechecks changed exact HEADs.
3. In an approved isolated environment, execute the missing LAN/auth/HA/data/Terminan/update/uninstall scenarios with independent observations. Physical disruptive tests require separate authorization; no such authorization was provided in this audit.
4. Compare original order/egress and network-state evidence for the whole candidate. The auditor’s own lack of trading/network mutations cannot certify other agents or past fleet activity.
5. Reassess all nine user PASS criteria. Any open P0, failed/missing mandatory case, source mismatch or missing physical proof keeps NO-GO.

Evidence index: [all PR HEAD snapshots](all-pr-head-verification.json), [all HEAD CI checks](all-head-ci-checks.json), [coverage](coverage-summary.json), [collection scope](collection-summary.json). Local raw API snapshots are retained under evidence/; remote GitHub URLs identify the original service records. SHA256SUMS.txt detects subsequent local file changes; it is an unsigned auditor manifest, not a trusted publisher signature.
