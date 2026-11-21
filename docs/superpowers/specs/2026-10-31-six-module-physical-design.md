# Six-module integration and physical deployment design
Date: 2026-10-31. Status: implementation in progress; physical NOT_RUN.
User authorizes autonomous architecture selection and implementation; remote merge/deletion, destructive operations and system-security changes still require separate approval.

## Decision and alternatives
Use independently installable modules with one pinned release manifest and Unified lifecycle. A monorepository would simplify atomic changes but discard useful existing release, test and receipt boundaries during migration. Loose independent installations preserve code but leave cross-module versioning and deployment inconsistent. A modular coordinated release reuses the existing five-source integration and adds MetaAnalyse explicitly.

## Ownership
Grid owns raw trades, footprints and immutable source datasets. Strattester owns historical strategy execution, training, costs, portfolio and result sealing. Math owns numerical/scientific kernels and causal bounded jobs. MetaAnalyse owns independent microstructure/paper analytics; its overlapping collection must feed the canonical Grid adapter rather than a second shared writer. Terminan owns read-only presentation. Unified owns module/version inventories, lifecycle, deploy policy and acceptance. No module gets live order-routing authority.

## Existing code to retain
Unified candidate 29ae8850bb3b75346857fe573844102c9919992a already contains the combined control plane and real source regression. Main in Math/Meta/Unified is README-only; never regenerate those modules before inspecting their branches. Math history-scientific candidate 12e688b339552ef2022e1b941780e6e1faadd0b1 and Meta candidate 21af0a5c0a60c4be570052d0745c52cb8d40421c contain implementations. Existing Math Windows verified update/rollback and Grid installer/service recovery must be extended, not independently replaced.

## Immediate corrections
Legacy descriptor registry, release lock and installer planner know only Grid/Strattester/Terminan, while lifecycle knows five modules and Meta is absent. Create one module identity/ownership catalog for coordinated release operations; preserve prior version-one consumers.
Producer-owned sealed receipt compatibility is mandatory: latest pinned Strattester cannot satisfy the owned_runs interface; no orchestrator-generated fake receipt or forced COMPLETE is allowed. First obtain exact producer branches, then restore versioned sealing in its owner and test positive handoff.
Physical acceptance must enumerate all expected nodes and every required scenario; empty, partial, stale, duplicate, synthetic and wrong-release evidence cannot pass. Unavailable execution stays NOT_RUN rather than success.

## Physical contract
Target 5 or 6 physical Windows hosts, expandable later. Owner supplies inventory only after preparation is complete, per explicit instruction. Use local least-privilege deployment agent with owner-issued scoped enrollment and authenticated TLS. Updates must use publisher-trusted immutable releases, exact CI revision, SHA256, canary/rolling activation, release-aware health, rollback and append-only history. Preserve explicit administrative stop; no hidden persistence. Reuse approved service wrappers/recovery.
A SQLite quorum model is not distributed consensus. Production leader election and replicated writes require an actual consensus-backed fencing authority, a documented two-node loss model and DB replication/PITR restore test. Cloud models never qualify those claims.

## Validation and dependencies
Unit/contract tests, real source-owned disposable-data pipeline, HTTP/browser E2E, regression/security, Windows installer tests, exact-head hosted CI, then per-host physical scenarios. Every failure remains visible. GitHub API/CI cannot currently be inspected (proxy 403); adding api.github.com is saved but not runtime applied. Git branch access was restored with the existing gh auth git-credential helper; all branch objects are available without requesting a new token.
No physical deployment, hosted CI qualification, DB HA, auto updates or whole-system readiness is claimed until independently observed.

