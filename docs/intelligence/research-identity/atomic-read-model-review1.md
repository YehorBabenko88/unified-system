# Atomic research identity capture: DATA model review1

MODEL ONLY. This does not import or execute the broker, a native fixture or Consul, and is not an actual broker/native reproduction, contract acceptance, publisher proof, scientific READ or mutation permission.

## Frozen source references

Unified base HEAD `96b17905a5be923857aa1e778085eaeec6f0f27f`, tree `e868213d3fd47739c05aa1fc9f70a8d7658a1333`; broker raw SHA256 `481724cd2efca312773fa4152d1c223b46ced6529d96b2d74f452cdf57932d7f`, blob `e10519767bad164534f99e42e5b04eb69d823d9c`. Grid `fb177d14b1e6e399bd9b66ae7cb35d3838acbd81` / tree `2cba4b0a1ee7621ef213600d6334db8e9ac7dae1` is a REFERENCE ONLY; assignment source SHA256 `5b972b6d81eeaf6f2283584c5b0482552fa9bf0717a4379838900a72da791491`. No cross-repo runtime adoption follows.

Design input: A2 source audit `12f54787e71f13bc1e82693cdd023474bed635c0050743bd917e89cb64e21083`, hand-traced recipe `9aa62d3083fd5d643bafc8ce06f7ce2c27f941e69546081acd2e845cf211b044`; Root explicitly allocated only this document and `tests/models/test_research_identity_capture_atomicity.py` for six stdlib DATA cases. No production/ABI changes or push until Root review.

## Model and limits

The single self-contained test file models immutable projected records and explicit store states. It projects identity/generation/state/scope/session joins and per-key indexes; it deliberately does not implement complete native JSON schemas, TLS, real issuer custody, authority clients, cryptography, wall clocks, Raft, HTTP/ACL enforcement, transport or scheduling. Model symbols G0/F/A/P/Q/S and projected records are DATA, not issued contexts/grants/real native identities. A view is ASSUMED to be one store snapshot; no test proves an actual server supplies it.

The sequential model selects each of five records from an explicitly supplied timeline cut, then applies projected joins. The atomic model validates one closed ordered view. Historical pre-change views may legitimately succeed. A mixed tuple that never coexisted must not be represented as a one-view capture. Per-key ModifyIndex values may differ; no shared index is inferred. External changes are deterministic DATA states, not actual writes or permission to write.

Separate models preserve existing `_observe` reobservation of exact key/index/raw/session and `_open_session` check-index fences on its four preliminary records. They do not simulate actual write commit or an accepted end-to-end exploit. Session association is observed at a read point; later committed invalidation demonstrates the historical/future-use boundary. A local require model cannot see external revocation, matching the scoped source concern; local binding/invalidation/expiry/peer checks still apply. No UTC-at-commit assertion is made.

## Implementation plan and ledger

Goal: six bounded deterministic methods, stdlib imports only, no project/fixture imports, exec/compile, processes, network, clocks, credentials, providers, Consul, sessions or job effects.

1. Write six tests against unimplemented model functions; run only this file with isolated CPython and bytecode disabled. Expected RED: all six methods fail through assertions (including bounded subtests), zero setup/import errors/skips.
2. Implement minimal projected sequential/snapshot/reobservation/fence/local checks in that same test file. Expected GREEN: exactly six methods pass, zero skips. Do not run broad pytest/discovery: it imports prohibited native fixtures.
3. Inspect exact diff/allowed paths, retain RED and GREEN originals plus raw source pre/post inventory outside repository. Review and commit locally only; report exact HEAD/tree and IDs to Root. Actual broker/native execution remains unqualified.

Review focus: an impossible mixed-generation/revoked-principal/new-policy tuple; preserving both existing counterguards; session release before versus after snapshot; malformed/filtered/unavailable views; unequal per-key indexes; fixed issuer/original/scope and after-await local validity.

Ruling: evidence artifacts/ledger remain outside the repository; no extra plan/test runner/dependency files are added. Only the two allocated paths are changed. User scope overrides skill suggestions to run a broad suite or install dependencies; those operations would import/execute unapproved fixtures. The exact six-method suite is the complete authorized model lane, not a project-suite PASS.

Ruling: native worktree creation did not return and produced no detected worktree/attachment; after stopping the wait and rechecking, Git fallback created a separate linked worktree from locally obtained exact base. No remote fetch/push, installed tool change or Root primary source edit.

Task1 complete: RED ran six methods with17 assertion failures including subtests, zero errors; GREEN ran6/6 PASS, zero skips. Originals RED-source.txt/RED.log/GREEN.log and exact IDs are retained outside the repository in A2 outputs/A2-ATOMIC-READ-MODEL-20261110. Baseline guard verified all1868 original files against exact base Git blob/raw bytes, with only these two additions and no extra files. No project-wide test/CI PASS is claimed.

Independent reviewer p0_code_review reported no actionable P0/P1/P2, independently ran this exact authorized six-method pure file, and confirmed the scope/freshness/counterguard distinctions. That repeat is not six additional distinct cases or actual broker/native evidence. Root review before push remains required; shared implementation/ABI and real runtime acceptance remain separate.

Strict D4 logical mutations remain DISABLED; native READ/full fixtures/Windows physical HA remain NO-GO. No push, merge or deployment is part of this model stage.
