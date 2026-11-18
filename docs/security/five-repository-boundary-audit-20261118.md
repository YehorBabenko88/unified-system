# Five-repository security and duplication review — 2026-11-18

**Status: PARTIAL EVIDENCE REVIEW / NO SECURITY CLEARANCE / NO DELETIONS**

This is an independent, **source-only** review. It does **not** authorize runtime, merge,
cleanup, physical Windows/LAN actions, network scans, secrets verification, trading or
database edits. GitHub's default branches and these exact open Draft candidate SHAs
were inspected. An exhaustive dynamic call graph, complete code secret scan, native
service/Windows token/ACL/DB probe and full dependency CVE evaluation were NOT RUN.

## Scope frozen by user (five repositories)

| Repo | Reviewed candidate HEAD | Tree blobs | Workflows |
|---|---|---:|---:|
| bybit-cluster-grid | `a2495825a2c8f412749b62bb9ebda6f4f79fd8d4` (#288) | 839 | 13 |
| strattester | `d6293f75db7fcc8eed0900521a1ba6bd46b3468e` (#83) | 405 | 2 |
| math | `d4bef309be3a78d790433bcd2d880927a20e32c0` (#117) | 688 | 23 |
| unified-system | `b8c40acb395e3c42fbcbce621e1c347bb5b273cc` (#106) | 1,949 | 45 |
| Terminan | `e23abe3345379e41f979695136fd1261e3cbd238` (#83) | 407 | 12 |

**Important:** `unified-system/main` and `math/main` contain only README,
but the actual implementations exist in Draft branches. All five are public.
No PR branch is assumed merged into main; several PRs have stacked/sibling
bases and cannot be treated as a unified executable release.

## Confirmed exact-byte cross-repository duplication (Git blob OIDs matched)

| Grid path | Math path | Status |
|---|---|---|
| `grid/nonlinear_research.py` | `python/history_nonlinear.py` | EXACT BYTES |
| `grid/position_sizing_research.py` | `python/history_sizing.py` | EXACT BYTES |
| `grid/stochastic_research.py` | `python/history_stochastic.py` | EXACT BYTES |
| `grid/timeseries_research.py` | `python/history_timeseries.py` | EXACT BYTES |
| `scripts/history_ci.py` | `scripts/history_ci.py` | EXACT BYTES |

Additional **archival evidence copy**, not a proven duplicate runtime:
`bybit-cluster-grid/docs/coordination/assignment-v1/target-native-mapping-review1-20261109/originals/gateway_target_adapter.py`
has exactly the same Git blob as
`unified-system/unified_system/gateway_target_adapter.py`.
The archived copy is retained evidence and must not be deleted based
on duplicate detection alone.

The code duplicates are real; however **none is proven dead or removable**.
Math is the proposed source owner of kernels; Grid may retain historically pinned
pure copies until imports, deterministic regression parity, platform dependencies,
offline deployment and rollback are jointly verified. Future source-consumer
composition should use SHA-bound adapter contracts, not a second unrelated Math engine.

## Functional overlap requiring owner qualification (not proved identical code)

- **Grid vs Strattester:** both have market-data acquisition/storage/worker
  modules. Proposed owner split: Grid for sanctioned exchange capture and raw
  provenance; Strattester for dataset/readiness/replay and strategy research.
  Old Strattester `marketdata/bybit_client.py` and L2 recorder require import and
  runtime-path inventory before retirement. No reconnection or deletion allowed.
- **Grid vs Math:** numerical/research kernels and ML orchestration coexist.
  Math owns transformations/validated algorithms; Grid owns ML jobs/resource quotas.
  Compare actual call graph and source pins before changes.
- **Grid vs Unified:** Grid includes `grid/scheduler.py`, `grid/ml_resource_scheduler.py`
  and Worker; Unified includes mission control, collector profiles, worker transport,
  Storage and Authority. Unified owns cross-service admission and coordination,
  Grid owns bounded workload execution. No competing Scheduler deployment.
- **Strattester vs Grid vs Unified:** multiple journals/datastores exist
  with different guarantees (raw ObjectStore/Journal, marketdata SQLite, experiment
  results). They are not interchangeable; do not consolidate without schema,
  provenance, crash/recovery and ownership equivalence.
- **Terminan vs Unified:** Terminan contains `server.py`, `unified_server.py`,
  `r2_server.py`, `r4_server.py`. Qualify which are current UI and test
  servers; do not create another Authority, DB writer, Bybit provider connector
  or independent decision-making gateway.
- **Unified Observer vs Autonomic Guardian #107:** read-only presentation/alerting
  and proposal-only diagnostics have different intended responsibilities.
  Do not create two permanent supervisors with overlapping service powers.

The current integration also references `meta_analyse`. That repository is
**not on the five-repository photo list**; do not remove the dependency or
silently treat it as in-scope without an explicit master decision. `tester`
is excluded.

## Confirmed CI/security review candidates from actual sampled workflow contents

1. `strattester/.github/workflows/tests.yml` on main used unpinned
   `actions/checkout@v4`, `actions/setup-python@v5` and lacked explicit
   top-level `permissions`. A narrow fix is proposed in separate Strattester
   security Draft PR; do not claim branch protection or job checks passed
   without checking the exact new HEAD.
2. `unified-system/.github/workflows/tests.yml` (#106 candidate) uses those
   two tag-based actions. It has `permissions: contents: read` and a hash-locked
   pip install. Owner should pin actions in a separate existing-workflow patch.
3. `unified-system/.github/workflows/installer-security.yml` also has
   tag-based checkout/setup-python/upload-artifact. Inspect and pin after
   reviewing other exact-source dependencies.
4. `Terminan/.github/workflows/tests.yml` (#83 candidate) contains tag-based
   checkout/setup-python/setup-node/upload-artifact actions, though repo token
   has `contents: read`; scope pinning with A6 and preserve full test matrix.
5. `bybit-cluster-grid/requirements.txt` and
   `strattester/pyproject.toml` contain broad package version ranges.
   These are **dependency reproducibility risks**, not evidence of malware.
   Prepare per-Python/OS lock and source policy without silently upgrading
   production dependencies.
6. Sampled Grid and Math workflows contained commit-pinned actions; one
   Math confidential workflow intentionally requested `id-token: write`.
   Verify OIDC audience, subject and use with its owner before any change.
   An OIDC grant is not automatically an incident.
7. Repository-tree filename review did not reveal obvious tracked key files
   matching `.pem`, `.pfx` or private key names. This **does not**
   establish absence of secrets in file content, histories, artifacts or logs.

No tested exploit/compromise, confirmed secret leak, malicious dependency or
SQL injection is established by this review. The next owner audit must run real
scanners with captured privacy-safe evidence (e.g. pinned gitleaks, dependency
vulnerability tooling, selected CodeQL checks) on approved checkouts,
not blindly download or execute untrusted community agent scripts.

## Recommended immutable responsibilities

| Component | Single primary owner | Other repos |
|---|---|---|
| Public market-data capture, normalized raw feed | Grid | read-only consumers |
| Raw custody, hashes, Journal and publishing | Unified/A4 | call source-owned sink |
| Authority, resource/admission/fencing | Unified with owner contracts | never replace with agent powers |
| Strategy lifecycle/replay/experiment | Strattester | Grid computes bounded tasks |
| Numeric kernels, scientific evidence, proof obligations | Math | Grid consumes source-pinned kernels |
| Learning job workers/resources | Grid | Strattester owns experiment definitions |
| Operator visualization and manual research controls | Terminan | no direct DB/provider/trading |
| Observer dashboards/alerts | Unified Observer | read-only |
| Guardian incident proposals | Unified Autonomic Guardian #107 | external broker handles future admitted effects |

## Required remediation sequence

1. Keep all running branches/code and immutable evidence. Do **not** delete
   copies, merged commits, historical Draft PRs, data tables or service files.
2. Independently map actual entrypoints, import sites, ownership and tests for
   each confirmed same-byte file. Produce `USED / ARCHIVAL / UNKNOWN`, never
   infer dead code from filename matches.
3. Pin CI actions on standalone narrow security branches; ensure external
   dependencies, supply-chain provenance and test coverage.
4. Produce cross-repository single-owner API contracts and typed adapters.
   Ensure fail-closed behavior if pinned source/ABI differs.
5. Separate observer read-only, agent proposal, broker permission and
   actual business functions.
6. Only after A8 and owners verify source/test/native equivalence may a
   duplicate runtime implementation be retired, with preserved raw evidence,
   explicit rollback and no change to historic fixtures.

## External reference, not installed

[mukul975/Anthropic-Cybersecurity-Skills](https://github.com/mukul975/Anthropic-Cybersecurity-Skills)
is a **community** skills library (not affiliated with Anthropic).
Read only defensive guidance relevant to CI supply chain, secret scanning,
dependency confusion, mTLS and prompt-injection boundaries. No scripts,
automatic agents, third-party packages or scanners were installed from it.

## Boundaries

`READ_ONLY_CROSS_REPO_REVIEW` / `SOURCE_ONLY`. Not a claim of full
code audit, dynamic application security, native LocalService/Session0, GitHub
branch policy, public provider admission, production DB/network security,
or all CI green. Never merge the audit branch or approve a runtime based on
this source inventory alone.
