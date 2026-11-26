# Git consolidation and release-security checkpoint (2026-11-26)

Parent: [#111](https://github.com/YehorBabenko88/unified-system/issues/111). Agent F: [#156](https://github.com/YehorBabenko88/unified-system/issues/156).

## Current independently paginated inventory

| Repository | Branches including main | Open PRs | main SHA |
| --- | ---: | ---: | --- |
| unified-system | 153 | 142 | `b9b03a1ce9f887dbe113fd22d0bda8932f46ef80` |
| bybit-cluster-grid | 333 | 137 | `d537d525296ef34f727996e240ae6c60102c6082` |
| math | 162 | 136 | `ccfe97dd88b1ebee9bd19795002a30d0bd1c1ca3` |
| Terminan | 116 | 113 | `fee79f4b15fc1f9efcff9ca12c403688b0026260` |
| strattester | 232 | 114 | `37ff7e9d12a4d2dccd788fc493c28557dbe8bcea` |
| meta_analyse | 95 | 81 | `2317c79d78654d8006d99b914532a089554677da` |
| **Total** | **1091** | **723** | |

Method: GitHub REST /branches and /pulls?state=open, all pages (per_page=100), counted independently per repository; the six snapshots were collected sequentially while other agents were changing refs. **This is not an atomic cross-repository snapshot.** Six JSON files in `docs/git-consolidation/snapshots/2026-11-26/` provide every observed branch/PR exact SHA, same-repository PR relationship and conservative `REVIEW_REQUIRED` / `NOT_EVALUATED` classifications. All six were reread and validated against their own contents with zero HEAD mismatch. Historical 1061 / 703 figures are superseded by subsequent creation of branches and PRs; full unique-change and semantic disposition evidence is still pending.

## Provable SHA lineage

- unified-system [#158](https://github.com/YehorBabenko88/unified-system/pull/158) HEAD `21bfdd1dce4b7436053b5d526a5fd93336c20b74` is direct ancestor (one commit, zero behind) of [#161](https://github.com/YehorBabenko88/unified-system/pull/161) HEAD `e686099a835ec5f950a1320acd4d6c2d83a66720`. #161 adds pin regression tests; **candidate** to preserve both, but CI is not green.
- meta_analyse [#83](https://github.com/YehorBabenko88/meta_analyse/pull/83) HEAD `6b6471149efcaec76acd8335afef63884fc5543d` is direct ancestor (one commit, zero behind) of [#85](https://github.com/YehorBabenko88/meta_analyse/pull/85) HEAD `7bd4cb9048f261d7936f2a9640f05ff8f42b1c77`.
- meta_analyse [#84](https://github.com/YehorBabenko88/meta_analyse/pull/84) HEAD `a98012b7a1a8fde1b0989aa4ec5b098cb3b066da` deletes tracked loopback TLS fixtures and adds tree/distribution guard. Its CI workflow edits overlap #85 and require deliberate integration.
- unified-system [#160](https://github.com/YehorBabenko88/unified-system/pull/160) HEAD `f30b32c78c0d41f67e1eb292c8b217fa1dc7e784` contains dependency matrix. Grid [#297](https://github.com/YehorBabenko88/bybit-cluster-grid/pull/297) HEAD `7387a3ef26a7786706662a27104f9fa563d3af0d` is stacked on Grid #296 HEAD `bf29f81b238c6236417f0ed9a13feea3dcbb5bec`. Strattester [#122](https://github.com/YehorBabenko88/strattester/pull/122) HEAD `7a25df9bc2f9aac143dc33e7025cf4e5dbf57398` proposes psycopg 3.3.6.

## Security and CI acceptance

- #161 exact-head run [45709581019](https://github.com/YehorBabenko88/unified-system/actions/runs/45709581019): three Linux matrix cells PASS; three Windows cells FAIL at `NATIVE_PHASE_TIMEOUT_15S` in installation native/service tests. Four new Action pin tests pass in Windows logs. Root-cause independence from these PR edits not yet proven.
- Historical scan reported 0 REAL-LIKELY after 23567 blob checks, but excluded 13 binary blobs and truncated long lines; **does not establish absence of credentials**. Never publish candidate secret values.
- TLS fixture exclusion is **not release validated** until actual wheel/sdist/installer artifacts have been inspected, including all archive members.
- Previous owner audit identified 178 duplicate groups. No group may be retired on count/name/age or simple line-set overlap: prove unique functional equivalence, consumer cut-over, regression and negative cases, rollback and independent sign-off.

## Consolidation decision policy

`KEEP` while unique behavior unverified; `SUPERSEDED_CANDIDATE` only with exact ancestry/byte and consumer evidence; `MIGRATE` only after target owner tests prove equivalence; `CLOSE/DELETE` always requires separate MASTER authorization. Do not infer code integration from green PR CI, do not merge into main, do not execute real trades, and do not alter user PostgreSQL or install local services.

**CODE NO_GO / PRODUCTION NO_GO.** Scope of this commit is documentary only; it does not assert local test execution or release safety.

## Round 2 implementation and verification constraints

- Added `tools/git_consolidation_snapshot.py` and `tests/test_git_consolidation_snapshot.py`: read-only paginated GitHub inventory with refusal on stale same-repository PR heads, duplicate refs, missing main or unbounded pages.
- Added `tools/git_history_secret_triage.py` and `tests/test_git_history_secret_triage.py`: streaming, value-redacted historical blob pattern checks for binary and lines >4000 bytes; this is a triage aid, not proof of secret absence. Full-history mirror scan has **not** been executed; embedded archives, unreachable objects and Git LFS data need separate coverage.
- Meta security integration is a separate [draft PR #86](https://github.com/YehorBabenko88/meta_analyse/pull/86) stacked on SHA-pinned #85: contains #84 packaging guard and removal of 11 stale loopback PKI fixture files from its active tree. Added bounded archive/link checks and negative tests. **No Git history rewrite**. Exact-head CI remains unaccepted.
- GitHub Actions on this Root documentation/tools PR were still queued at last observation; no local test execution claimed. Container GitHub network access is unavailable, so full clone/runner tests must be verified in hosted CI. Current overall release remains CODE NO_GO / PRODUCTION NO_GO.
