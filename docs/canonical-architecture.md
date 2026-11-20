# Canonical architecture migration

Status: NO_GO. This source candidate changes the active owner roster; it is not an installation or migration receipt.

| Previous owner | Canonical owner | Repository |
|---|---|---|
| Grid acquisition/storage, Strattester datasets | `market_data` (`market-data`) | `YehorBabenko88/strattester` |
| Numerical implementations across modules | Math | `YehorBabenko88/math` |
| Meta Analyse analytics, Strattester research, paper/replay | `terminan` | `YehorBabenko88/Terminan` |
| Unified orchestration | `unified_system` | `YehorBabenko88/unified-system` |

Active contract changes: release `unified.release.v4`, lock version 2, Windows package lock v3, lifecycle `unified.lifecycle.v2` / API 2.0. Retired module identifiers are rejected rather than aliased. Research producer is `terminan`; dataset/snapshot producer is `market_data`. API callers and synthetic test fixtures use these canonical owners. Source repository names remain explicit remote identities, not Python import aliases.

Lifecycle names: `STRAT_HISTORY_SYNC` → `MARKET_HISTORY_SYNC`; `STRAT_RESULT_SEALED` → `ANALYSIS_RESULT_SEALED`; `GRID_MARKET_READY` → `MARKET_DATA_READY`. An old lifecycle snapshot is incompatible and must not be silently rewritten. No existing user database was opened or changed. Existing archives retain their original bytes and digests; source-owned migration/restore evidence is required before retirement.

Remaining release gates: protected service bootstrap/source-admission closure, data-first orchestration split, capsule builder and installer source closure, exact-SHA Windows/Linux CI, native install/update/recovery/uninstall, physical Qt acceptance, complete migration of unique Grid/Meta functionality and necessary data. Historical repository/source preservation is intentional until those gates pass. No repository/branch/data deletion is implied by this candidate.

Security scope: source edits and reviewed pure Python checks only. No PowerShell/CMD replay, Windows installer/service action, protection changes, live trading or real funds. Norton incident remains INVESTIGATION_REQUIRED.

Confirmed obsolete deletion: `unified_system/fixtures.py` and its exclusive `tests/test_fixtures.py` consumer. The module only admitted two hardcoded historical Grid/Strattester revisions; no active Python caller remained. Current source/release admission uses the full manifest and exact source-fence checks. Immutable historical evidence files and Git history remain unchanged.

Removed the obsolete synthetic demo CLI and exclusive Supervisor/Coordinator/dashboard/report implementations after confirming all active callers were in that demo closure. The shared canonical hash utilities and durable Journal remain because installer, mission and storage consumers use them. The actual entry point is `python -m unified_system --config ...` with prepare as the default. Retired Grid fleet-credential parsing was removed after the service/worker consumers moved to private process capabilities and dedicated database credentials.
