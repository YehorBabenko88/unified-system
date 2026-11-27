# Unified integration audit — read-only, 2026-10-31

Recommendation: reuse `origin/codex/five-module-integration-20261030` at `29ae885` as the software integration candidate. It descends from combined `2fdd512`, adds 19 files / 1108 lines, actual pinned-source APIs and Chromium, plus stricter fleet-envelope validation. Do not rebuild from README-only main. This is an existing PLAN_ONLY control plane and regression integration, not an operational five-module launcher.

## Existing branch evidence

- Combined `2fdd512`: immutable workstream file-tree composition over acceptance baseline (`201791f`), cross-stream fleet/lifecycle/security/provenance tests (`8f4e041`), Windows/Linux combined CI (`deb97a2`), 30+ test files, control-plane implementation and extensive architecture/contracts docs.
- `29ae885` extends combined with exact source fencing and source/API/worker/browser proofs (`c42ced1`, `29d61fd`), resource reservation/expiry regression (`cc88785`), distinct stale HTTP snapshots (`bd97729`), Windows path handling (`23d3848`, `29ae885`). Richest relevant integration branch.
- `origin/codex/windows-staging-plan-20261030` (`28cd3c6`) is a sibling of the five-source branch: only one commit beyond combined, adding staging.py, staging tests, workflow and dependency audits. It does NOT include five-source integration. Reuse its bounded staging work later by reviewing that single commit; choosing it as base loses five-source additions.
- `five-workstreams-acceptance` (`beede6`) supplies earlier dependency/observer fixes. `five-infra-a`, `five-lifecycle-b`, `five-boundary-c`, `five-security-e` are source workstreams already represented by combined immutable-tree composition. Their tips alone are narrower bases.

## Architecture and concrete contracts

- Unified orchestrates observations; Strattester owns historical acquisition/research; Grid owns market ingestion; Terminan is an independent read-only consumer; Math runs bounded independent jobs. Existing docs `OPERATING_SEQUENCE_V2.md` and `FIVE_MODULE_INFRASTRUCTURE_ADR.md` support this architecture.
- `Lifecycle` is durable SQLite PLAN_ONLY intent/evidence state: INFRA_PREFLIGHT -> INFRA_READY -> STRAT_HISTORY_SYNC -> STRAT_RESULT_SEALED -> HANDOFF_VERIFY -> GRID_MARKET_READY -> STEADY_STATE. Terminan starts after infrastructure and gates later stages; Math is parallel. Epoch/sequence fences, request idempotence, bounded hash journal, recovery revalidation and downstream invalidation already exist. It never launches code.
- `FleetControl` uses transactional SQLite, model voter quorum, election/lease fencing, resource reservations, draining, retained retirement identities and backup/restore. This is not distributed consensus or measured physical telemetry.
- `release_boundary.py` verifies exact release revision/tree/artifact SHA256, owned-run v1.1 records, coverage, reconstructed dataset windows, identities, fingerprints and independently admitted receipts. Grid historical aggregates are explicitly PARTIAL/GAP/STALE; data collection grants no trading authority.
- Old `adapters.py` is explicitly SYNTHETIC_ONLY/no I/O. Do not mistake it for the new actual-source integration.

## Actual pipelines and meaningful gaps

`integration/verify_sources.py` imports actual Terminan infrastructure consumer, Strattester ResearchRunner/SQLiteMarketStore/ResultStore, Grid history export/handoff/FootprintBuilder, and invokes Math's actual bounded-experiment Node suite. It uses disposable SQLite and offline synthetic exchange rows, not external exchange/network. It checks 0/1/5/6/7/10 nodes, 32 module inventories, resource pressure/reservation/expiry, stale observations and denial cases. Actual Terminan Handler HTTP plus Chromium covers controls, stale requests and recovery; topology/resources/DB sizes stay empty/null where unobserved.

Critical positive handoff gap is documented AND asserted in `test_latest_result_schema_cannot_substitute_for_sealed_receipt`: pinned latest Strattester ResearchRunner.run uses checkpoint/research_permission, does not accept provenance/result_store, and ResultStore lacks owned_runs. Older #43 had sealing support; latest #69 result cannot satisfy Grid/Unified v1.1 owned-run receipt intake. Grid external owner receipt provisioning also remains necessary. A passing negative regression is not successful research-to-Grid handoff.

Pins: Terminan `d10cee69b4fc599e588c88ba105ef77d0c6ff0af`; Math `135b437c83a98738cddb263e0cac78b37e83d1e2`; Grid `d2dcffb43e520db75936eb97389b66db2f3e1365`; Strattester `702d285b5a5af28f0b2e1f4c9a52aeb49582cbef`. These are source candidates, not release admission. Source provenance BLOCKED, physical NOT_RUN, production NO_GO are explicit.

No MetaAnalyse identity appears in Lifecycle.MODULES (only unified-system/terminan/strattester/grid/math). Clarify whether MetaAnalyse is this control plane, a Math capability, or a separate sixth module before expanding contracts; do not silently invent mapping.

## Verification and next steps

This audit inspected Git objects only; no checkout, source edits or test execution. No hosted CI outcome was independently verified. Existing workflow matrix is Ubuntu/Windows x Python 3.11/3.13, Node22, exact external source pins, unittest discovery, source API + six Math bounded-worker tests, npm ci + Playwright Chromium. It is not Math's full Node22/24 x PG16/18 mandatory matrix. One existing local Windows-symlink skip is acknowledged in acceptance docs.

1. Inspect source-owned Strattester receipt-capable branch and current runner differences; restore/version a producer-owned sealing interface rather than synthesizing receipts in Unified. Add one genuine positive disposable sealed-result -> Grid intake -> lifecycle handoff proof, preserving negative coverage.
2. Verify the four pinned external trees exist locally and run existing source-fenced API/browser suites in an isolated branch/worktree when authorized; exact clean trees are enforced by SourceFence, including untracked executable shadows/import origins.
3. Keep infrastructure and runtime adapter work incremental: lifecycle currently records intent, so service start/stop/authenticated module API implementations and physical telemetry collectors remain real functionality work.
4. Review sibling Windows staging commit for dependency inventories and PLAN_ONLY previews after software qualification; preserve non-executing staging boundary.
5. Independently validate CI artifacts and full Math mandatory matrix. Distinguish source regressions, real pipeline success, release authenticity and six-machine operational qualification.
