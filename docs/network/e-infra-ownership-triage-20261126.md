# E — Infrastructure ownership and LAN triage (2026-11-26)

Issue: unified-system#155; coordinator: #111. Scope is the canonical candidate, not the README-only `main`.

## Exact baselines

- Unified: `f05f9a73581b1c15c4cc78da2801c9f2f5dd08d0` (candidate PR #149).
- Grid legacy: `c9ffdaa2af52c4d55871a48655a77a0c669da80f` (candidate PR #295).
- E isolated reconnect branch/PR: `gpt/e-lan-fault-boundary-20261126` / #164.

## Observed Windows failure, not a proven cause

Historical Windows job [138561269096](https://github.com/YehorBabenko88/unified-system/actions/runs/45426906430) completed the TLS pairing but `test_real_mtls_payload_credit_classes_and_actual_byte_accounting` failed at `tests/test_lan_transport.py:110`, `s.receive()`, raising `TransportError: DISCONNECTED` from `Connection._current()`. The same job passed `test_six_real_isolated_nodes_independent_of_tailscale`, wrong-certificate, wrong-EKU and expired-certificate tests. This establishes *connection closed during payload exercise*; it does NOT prove that certificate validation is broken or that a particular worker/credit path caused the close.

Root LAN transport is `LanTransport.isolated`; `LanTransport.runtime` explicitly refuses native admission. The isolated `listen()` and `connect()` reject non-loopback endpoints. Component qualification is not evidence of office LAN readiness.

PR #164 fixes a separate confirmed policy defect: retry history was retained after successful connection and caller cancellation after a retryable failure could turn into a retry. It does not claim to close the original TLS reader failure.

## Legacy ownership candidates (first five source families only)

| Grid legacy source | Canonical Unified source | Finding / migration limit |
| --- | --- | --- |
| `grid/coordination.py` | `unified_system/consul_authority.py` | Consul session/lease subset extracted; Grid source still contains `coordinator_authority` and `floating_leader_guard` not copied into Root |
| `grid/coordination_commands.py` | `unified_system/consul_command_store.py` | Command parsing/admission moved with different Root principal integration; verify every Grid consumer before retirement |
| `grid/authority_runtime_v1.py` | `unified_system/authority_codec.py` | Strict native JSON and operation measure subset extracted, but Grid layout/partition identity remains outside this module |
| `grid/authority_assignment_v1.py` | `unified_system/research_authority.py` | Root only owns negative research-authority subset; registration and general assignment code not ported |
| `grid/ml_windows_job.py` | `unified_system/windows_job.py` | Both 142 lines; two line differences observed (module description and child-thread error wording). No safe deletion inferred from shape alone |

These are **five source-family mappings**, not a verified classification of all 32 duplicate *groups*. The #155 total remains unverified; a symbol-level 32-row matrix, Grid consumer graph, and independent contract/effect equivalence tests are required before any legacy retirement.

## Single-owner safety contract

- Unified System: supervisor, node membership, Consul authority, registration/fencing, Windows Job primitive, package installation, safe update/uninstall and lifecycle.
- Grid: sole Bybit ingestion, instrument history/live collectors and market-data writes; no second authority after compatible handoff.
- Math: pure mathematical computations.
- Terminan: paper simulator, strategies and UI.

During migration, do **not** run independent Grid and Unified supervisors against the same machine/namespace. Require explicit versioned handoff, lease generation/fence, source-hash pins, source admission, rollback after a confirmed quiescent stop, and no UNKNOWN-as-success shortcuts.

## Mandatory upcoming evidence

1. Isolated Windows/Linux mTLS fail log with bounded, redacted connection/worker/credit close-reason diagnostics.
2. Separate negative cases: expired/wrong-EKU/wrong-URI/wrong-pin; mismatched enrollment, ALPN and cluster generation; retry after transient TCP failure; failed reconnect on stale registry.
3. Stress: two channels, multiple concurrent streams, 2 MiB Mux transfer under original 5-second deadline, cancellation, double shutdown and 30-minute repeat. Never increase timeouts to convert failures to PASS.
4. Actual six-node LAN/SSH, real Consul quorum and Windows services require separate explicit admission/physical run. Never infer from loopback.
5. All 32 candidate duplicate groups, per-symbol callers, authority ownership, Windows installer/upgrade/uninstall and rollback tests before release.

## Present verdict

**CODE NO_GO / PRODUCTION NO_GO**. No production host/service, database, trust-store or network changes. No main merge, security relaxation, data deletion or real trades.