# ROUND 3 — Source-grounded Root → Grid v2 → Terminan handoff

Status: **INTEGRATION BLOCKED / NO RUNNING SERVICE / CODE NO_GO / PRODUCTION NO_GO**.
Read-only source review as of 2026-11-26. Do not interpret this as an accepted
multi-repository ABI or a source re-anchor.

## Exact source observations

| Owner | Draft/pin checked | Source | Existing behavior |
| --- | --- | --- | --- |
| E Root | #164 Root candidate derived from `f05f9a73581b1c15c4cc78da2801c9f2f5dd08d0` | `unified_system/service_module_runtime.py` | Hardcodes `ENTRIES['market_data']='market_data.cli'`; `serve_module` calls `module.main(arguments,startup_admission=source)`; protected argv shape is exact |
| E Root | same source pin | `unified_system/runtime_process.py::_market_data_read_capability` | Requires exactly one *currently alive and ready* Root-owned market_data child, same release/source SHA40/epoch; supplies Terminan a private port/token/source_commit/release_id/epoch |
| B Grid | #300 `72423393f2fe9956192f42a72bd3c6066950af21` | `market_data_v2/read_api.py` | New managed-only `GET /internal/v2/candles/qualified`; uses v1.1 `history_api.immutable_minutes`, versioned `market_data.qualified-read-envelope.v1`, and pre/post `require_current` |
| B Grid | same pin | `market_data_v2/read_api.py::main` | **Signature `main(*,startup_admission=None)` is NOT compatible with the current Root `module.main(arguments,startup_admission=source)` call** |
| B Grid | same pin | `market_data/admission.py::startup_identity` | Requires exact market_data environment module ID, 64-hex instance token, module version/release ID and trusted in-process `startup_admission.require_current() is True` |
| C Root PG | #163 `89ccdf58b31c8466fc45b9d8235acddc9c6b3428` | `unified_system/lab_postgres.py` | Owner-only PG18 role/trigger custody witness; does **not** provide unique writer fencing, and existing lab_writer still has direct INSERT |
| D Terminan | existing #126 candidate; advancing | `terminan/data.py::MarketDataReadClient` | Protected client supports historical managed v1 route and current private capability/revocation; v2 route/DTO adapter must be explicitly added by D |

## Admission/ABI mismatch and safe migration

B's v2 handler **does not create a second HTTP service** when it replaces v1
on the same loopback socket; this is the correct design. But simply replacing
Root's `ENTRIES['market_data']` would currently raise a Python call-signature
error. The existing `_module_arguments` also requires the immutable manifest
to pin exactly `--module market_data.cli -- serve`, not
`market_data_v2.read_api`. A source/manifest re-anchor and a versioned
Root dispatch adapter are therefore **required**; do not sneak in a fallback
import or silently change the v1 protected entrypoint.

Proposed nonoverlapping ownership:

1. **B** pins exact additive wheel version/source hash and the `market_data_v2`
   managed handler; defines whether to expose a compatible
   `main(arguments,startup_admission=...)` shim or an explicit separate
   versioned entry with existing protected-module semantics. Retain v1
   `market_data.cli` for historical seal tests.
2. **E** changes Root's protected `service_module_runtime` only after the B
   entrypoint is fixed and an exact manifest pin/owner-approved versioned
   selector is supplied. No automatic switch of existing v1 services.
   Root retains `_market_data_read_capability` as single child and ensures
   old listener/legacy Grid writer cannot be running at the time of v2 start.
3. **C** provides the actual PG18 canonical producer/table reader under
   protected current admission, an owner-only role/trigger witness, **and**
   a nonbypassable transactional writer fence before an active collector starts.
   Source rows must be actual `producer=market_data`, never old Grid rows
   relabeled/rehashed. C changes only C-owned DB LAB.
4. **D** extends the existing private `MarketDataReadClient` allowlist and
   adapter to strict `/internal/v2/candles/qualified` after B's version/shape
   are final. Continue both pre/post Root authorization checks, do not accept
   plain caller JSON as provider or immutable-row proof. `PARTIAL` is
   **display-only** and never paper/trading authorization.

### Required on-host/PG negatives before native admission

- Old v1 listener still bound to the port, old legacy worker alive, multiple
  admitted Grid instances, invalid token or wrong source epoch: new launch DENIED.
- Unmanaged v2 listener/GET, revoked private credential, stale release ID,
  token mismatch or post-read revocation: HTTP access DENIED.
- Wrong producer, invalid Math-row SHA, stale/gap/duplicate revision, unknown
  DB custody or inaccessible PG: read/display unavailable or explicitly
  degraded, never AVAILABLE and never synthetic paper authorization.
- Two concurrent writer sessions, stale fence generation, direct same-role
  INSERT bypass and restart after crash: PG-owner's transactional fence
  rejects the stale writer even if it retains a previous Consul token.
- An unpinned protected manifest, unqualified OS service, reused process ID or
  indeterminate quiescence: Root's startup must DENY without spawning any child.

No live service, PostgreSQL cluster, Consul cluster, private browser, Bybit
network or real trading call was made during this review. A/B/C/D source
control remains owned by those agents. Proof of the complete chain is pending.
