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
