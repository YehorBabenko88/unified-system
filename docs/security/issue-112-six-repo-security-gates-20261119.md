# Issue #112 — independent six-repository security audit (2026-11-19)

Status: **IN PROGRESS / NO_GO**. This document is an evidence ledger, **not** a clean security attestation.

## Scope and source baseline
Repositories: `strattester`, `bybit-cluster-grid`, `unified-system`, `math`, `Terminan`, `meta_analyse` (owner `YehorBabenko88`).

GitHub API inspection established the following `main` SHAs:
| Repo | main SHA |
|---|---|
| strattester | `37ff7e9d12a4d2dccd788fc493c28557dbe8bcea` |
| bybit-cluster-grid | `d537d525296ef34f727996e240ae6c60102c6082` |
| unified-system | `b9b03a1ce9f887dbe113fd22d0bda8932f46ef80` |
| math | `ccfe97dd88b1ebee9bd19795002a30d0bd1c1ca3` |
| Terminan | `fee79f4b15fc1f9efcff9ca12c403688b0026260` |
| meta_analyse | `2317c79d78654d8006d99b914532a089554677da` |

All six have multiple draft PRs and non-main branches; main is README-only for unified-system, math and meta_analyse. A main-only scan is insufficient. No credentials or sensitive values are included in this report.

## Observed high-priority security review candidates
- Unified PR #109: offline five-repository boundary inventory and test workflow; its GitHub workflow result for head `1c1c320b3ef68775183806feddd92bc53eabc88f` is SUCCESS, **not** a six-repository full-history scan.
- Unified #110: Collector/Storage/Authority/Guardian/Observer privilege boundaries; workflows `tests.yml`, `installer-security.yml`.
- Grid #289 / Math #118: exact-byte duplicated research kernels and `scripts/history_ci.py`; inspect runtime import and supply-chain exposure before canonicalization.
- Terminan #84 / PR #85: pin CI actions and disable persistent checkout credentials.
- Strattester #85 / PR #84: pin CI actions and read-only checkout.
- Unified #112 is the sole full-history security gate; do not treat earlier indexed default-branch secret searches as comprehensive.

## Required independent scan — pending execution
1. On a trusted isolated audit machine, obtain **full mirrors** of each repository, including all accessible refs and PR heads; record ref name, SHA, object count and missing/inaccessible refs. Re-run fetch immediately before signing results. Include reachable history and inspect dangling objects where feasible. Treat LFS objects, release artifacts and binaries as separate inventories.
2. Run version-recorded `gitleaks git --log-opts="--all"` (or version-equivalent history mode) and TruffleHog on each mirror; keep raw findings in restricted storage, never public CI artifacts. Distinguish verified, unverified and false-positive results. Do not print secrets.
3. Audit `.github/workflows` for SHA-pinned actions, minimum token permissions, checkout persistence, untrusted PR execution, artifact/log leakage, third-party scripts, dependency lockfiles and provenance. Run CodeQL/Semgrep/dependency review where supported.
4. Inspect Windows installer/PowerShell, SSH/firewall, PostgreSQL service accounts and ACLs, logs, Telegram notifications, API exposure, and credential injection. Use isolated disposable infrastructure; do not connect production databases or enable real orders.
5. For confirmed exposures: immediately revoke/rotate using private channels; record only category, path, commit, masked fingerprint, exposure classification and remediation owner. Coordinate any history rewrite and clone invalidation separately; never force-push or delete refs under this issue.
6. Require an independent reviewer and a physical Windows validation before declaring GO.

## Evidence and release gates
| Gate | Status |
|---|---|
| Six default-branch SHA inventory | PARTIAL — API snapshot only |
| All PR/ref SHA inventory | INCOMPLETE — paginated inventory needed |
| Full Git object and LFS scan | NOT RUN |
| Gitleaks / TruffleHog verified findings | NOT RUN |
| Workflow and dependency review | PARTIAL — candidate PRs identified |
| Windows installer/SSH/PG privilege audit | NOT RUN |
| Independent reviewer sign-off | NOT RUN |
| Unified release | **NO_GO** |

No code deletion, merge, production deployment, credential rotation, or history rewrite has been performed as part of this evidence report.

## Stage 6 — Meta Analyse source-preservation and security retirement gate (2026-11-19)

Pinned candidate `YehorBabenko88/meta_analyse` Draft PR #81 `b49505da42a274f7232fabe5d847c91f7218a0ce`, stacked on #78 `f3c01a23fa5baaeeeb28eb8e9397e72b5ef4d5a1`. Exact source tree API enumerated **83 Python modules under `src/meta_analyse/`** (tree not truncated); this is NOT exhaustive Git history, LFS, tags, releases or branch reachability. PR #81 changed seven files: `.github/workflows/ci.yml`, `docs/unified-stage3-retirement-map.md`, `scripts/check_math_consumer_parity.py`, `src/meta_analyse/desktop.py`, `src/meta_analyse/orderflow_archive_reader.py`, `tests/test_desktop_flow_contract.py`, `tests/test_flow_history_storage.py`. The rest of the library remains.

### Security ownership and KEEP / MOVE / MERGE / DELETE
| Existing Meta source | Evidence/classification | Security gate before removal |
|---|---|---|
| `exchange.py`, `collector.py`, `raw_trades.py`, `market_collector.py`, `history.py`, `trade_archive.py`, `bybit_archive_*.py` | MOVE unique data ingestion/archive semantics to **Grid**; independent Bybit runtime paths still exist | Real Grid consumers moved; exact source and manifest hashes; no second network client; restore and gap continuity |
| `core.py`, `footprint.py`, `footprint_engine.py`, `tape_velocity.py`, `wall_tracker.py`, `orderflow_metrics.py`, `level_quality.py` | MOVE domain numeric semantics to **Math**; Math #121 staged candidate compute API, not production cutover | Decimal, zero-price, tie, event-time, negative-input, gap/reconnect parity; exact wheel pin and signed source |
| `desktop.py`, `desktop_service.py`, `level_sync.py`, `level_publish.py`, `core.py:PaperEngine` | MOVE UI/paper/level behavior to **Terminan**; legacy desktop launcher now fail-closed in #81 | One launcher, settings and level preservation; no real orders; strategy provenance; physical UI acceptance |
| `headless_service.py`, `analysis_session.py`, `runtime.py`, `pg_*.py`, `commissioning/prepare-private-cluster.ps1`, `install.ps1` | MERGE only needed service, API authorization and PostgreSQL lifecycle into **Unified**; no second server/installer | SSH identity/known-hosts; DB ACL least privilege; mTLS token boundaries; process ownership, fencing, startup/restart/rollback |
| `flow_history_storage.py`, `orderflow_archive_reader.py`, `market_store.py`, `storage.py`, `storage_migrations.py`, `archive_db_import.py` | MERGE old read path (internal duplicate SQL reader already removed in #81), then Grid read API and Unified-owned cluster; DELETE candidates only after cutover | Data export/restore, instrument and timestamp normalization, role-separated writes, active consumers and data checksums |
| Tests, release evidence, migrations, historical Git refs, datasets, user settings and persisted results | KEEP until individually preserved and independently reproduced | Full refs and artifacts inventory, redacted full-history scan, encrypted backup inventory, rollback and separate owner approval |

### Confirmed legacy caller graph (reported by pinned Meta #81 owner map)
- `desktop_service.py` imports `AnalysisSession`, `BybitPublic`, `Runtime`, `FlowBridge` and `flow_history_storage.read_flow_history`.
- `analysis_session.py` imports `RawPipeline`, `MarketCollector`, `AnalysisCoordinator`; `analysis_coordinator.py` imports `FootprintEngine`, `TapeVelocity`, `MarketClock`.
- `runtime.py` imports `core.PaperEngine`, `core.RollingFlow`; `grid_history_adapter.py` and `ohlcv_research_adapter.py` use `core.untouched_levels`.
- `pyproject.toml` still defines `meta-analyse = meta_analyse.desktop:main`; `headless_service.py:main` is a separate candidate entrypoint. An explicit negative launch test is not proof that previously deployed services stopped.
- `core.Minute.add/Minute.poc`, `footprint.Footprint.add/Footprint.poc/FootprintCell.delta` remain Meta runtime consumers; Math #121 `market_compute_api.compute_batch` is only a staged wheel/CI contract.

### Stage 6 approval barriers (none implicitly satisfied)
1. Enumerate and scan every branch, tag, PR head, reachable commit, Git LFS object and release artifact (Gitleaks/TruffleHog/CodeQL/dependencies) before copying source and before archival. No raw secrets, tokens, DSNs, private keys or unredacted logs may be put in GitHub comments/artifacts. Confirmed leaks require out-of-band owner rotation, not public disclosure.
2. No direct Bybit client, standalone Meta database writer, second server/Qt terminal or PG bootstrap in final Windows deployment. Independently demonstrate source-authentic real public Grid REST→WS continuity, Grid writer fencing and Unified least-privilege roles, not just synthetic CI.
3. Pin both old and target commits, test all imports and consumers, deterministic numerical equivalence plus explicitly documented behavior differences, preservation of settings/history/experiments, startup/recovery/rollback and cross-node fencing.
4. Retain the Meta repository and refs as read-only archive only **after** the above passes and signed owner review. **Deletion requires a separate explicit confirmation naming `YehorBabenko88/meta_analyse`**; this note is not authorization.

### Stage 6 evidence verdict
- **USED/MOVE/MERGE**: paths above are plausible active/runnable candidates, not complete dynamic usage proof.
- **UNUSED/DELETE**: no production file proven unreachable; no deletions authorized.
- **CI**: Meta #81 exact HEAD workflows `44520584960` (Storage) and `44520585183` (CI) were QUEUED; `44520584866` synthetic ADMINIT SKIPPED when checked. Security PR #113 exact HEAD previously `337fbbaf2208fcc8c66bed14cbf995a873af6e22` workflow `44518377138` QUEUED. Older success does not qualify current commits.
- **Physical hosts tested**: zero for this security audit. **Archive readiness**: NOT_READY; **merge-to-main**: NO; **release**: NO_GO.

Source of detailed runtime candidate mapping: `meta_analyse/docs/unified-stage3-retirement-map.md` at the pinned PR #81 HEAD. Security scans remain mandatory and uncompleted.
