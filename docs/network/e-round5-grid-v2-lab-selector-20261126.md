# E Round 5 — exact B Grid-v2 LAB selector and protected Terminan read capability

**Status:** LAB-only selector authored, **NATIVE_START DENIED** until C writer
fencing is independently attested by Root and A protected-service acceptance.
No hosted CI PASS claimed, no
native Windows service, PostgreSQL, Consul or Bybit activity performed.

**Root candidate:** existing draft #164, branch `gpt/e-lan-fault-boundary-20261126`.
**B Grid v2 source:** draft #300 exact commit
`f57781a947af138a2099bebe553b89c3c5ee726e`.
**D Terminan consumer:** #126 `cf1448f8d30399f8787f69f9abfcb5cf992a4209`.
**C native DB resource owner:** #163 `89ccdf58b31c8466fc45b9d8235acddc9c6b3428`.
All are draft candidates; ancestry/CI does not imply qualified release.

## Two independent source admission checks updated together

1. `unified_system/lab_release.py::_parse_v1_manifest` retains the
   original `REPOSITORIES['market_data']=YehorBabenko88/strattester`
   for all legacy source and synthetic collector manifests. A new
   `YehorBabenko88/bybit-cluster-grid` origin is accepted **only** by
   `unified.lab-release.v1` with `mode=LAB_SIMULATION`, the exact
   B commit and a separately pinned three-file SDK v2 source cohort.
   Trusted/production manifests and synthetic collector v2 are **not**
   reinterpreted as native startup permission.
2. Both `unified_system/lab_runtime.py::launch_profile` and
   `unified_system/service_module_runtime.py::_module_arguments` resolve
   the same `market_data_entry_contract.entry_for_manifest` selector.
   Old Strattester source always requires
   `--module market_data.cli -- serve`. Approved Grid v2 requires
   `--module market_data_v2.read_api -- serve`; any cross-over,
   fallback, arbitrary module, unknown commit or missing pin is refused.

The exact B three add-on paths under `sources/market_data` are
`market_data_v2/{__init__,qualified_read_contract,read_api}.py`, each in
the externally hashed capsule file manifest. **One** `market-data`
dependency must have version `0.2.0.dev0` and a separately hash-pinned
lock file. The original Data49 package and historical source bytes remain
untouched. A package-name alias or second installed wheel is not approved.

**Important deterministic ABI mapping:** Root's original ModuleSpec and
LAB capsule version grammar is strict semver and does **not** accept the
PEP440 spelling `0.2.0.dev0`. Thus the exact protected Root source
version is **`0.2.0-dev0`**, explicitly mapped by the selector to the
**single** B wheel version `0.2.0.dev0`. This avoids weakening all
module version validation and preserves the historical tests. The B managed
`market_data_v2.read_api.main(['serve'],startup_admission=...)` now
accepts Root's protected positional argv and reads the source module
version from the protected `UNIFIED_MODULE_VERSION` environment.

## Native startup still fails closed

The v2 import path in `service_module_runtime.serve_module` invokes the
existing E `grid_writer_fence_model.native_writer_admission()` **before**
importing `market_data_v2.read_api`. This deliberately always raises
`NATIVE_DB_FENCE_NOT_ADMITTED`, because C's earlier
`lab-postgres-custody.v1` owner/trigger witness alone allowed direct INSERT.
**C has now authored a separate** `lab_pg_fence.py` (observed C #163
`332362151931ac767ac22f878d2b865736249a2b`) that revokes direct
`lab_writer INSERT` and offers an owner-installed PostgreSQL
`SECURITY DEFINER` transactional write function, durable generation/token,
backend PID/start identity, revoke and catalogue checks. This is the
**canonical C-owned DB fence candidate** and is not reimplemented by E.
However neither native C CI execution, Root live Consul lease/host quiescence
nor a trusted Root-to-C startup API has been accepted; a pure model CAS is
not a genuine fence. No Root service may bind even the v2 read-only listener
under this pending gate.
The protected prestart denial is a conservative intermediate integration
state, not a native end-to-end implementation.

C must independently execute/qualify its new DB fence and agree with E
on trusted old-process extinction, Root control lease binding, exact
source+schema+session+node incarnation and **per-write transaction-level**
enforcement forbidding direct same-role INSERT bypass. A coordinates
source-pinned service activation and native
Windows proof; B identifies single canonical collector and excludes
legacy `grid/worker.py` and `grid/market_backfill.py`; E can then
replace the always-denied startup adapter in a separately reviewed change.
No second listener, supervisory authority, Consul lock or database writer
is introduced here.

## Terminan private capability is reused, not duplicated

Existing `runtime_process.ProcessDriver._market_data_read_capability`
already selects exactly **one** alive/ready Root-owned market_data child,
verifies the current release, source SHA40, matched process incarnation
and authenticated health response, then internally constructs
`{port,token,source_commit,release_id,epoch}` for Terminan at startup.
`ProcessDriver.start` strips *all* ambient/program/child-supplied
`UNIFIED_MARKET_DATA_READ_CAPABILITY` and injects only this Root-minted
private handoff for Terminan, without persisting it in the process journal
or exposing it to status. D validates source identity, release and private
bearer before serving, then checks Root admission before and after v2 read.
A Grid restart rotates its token/epoch, so a stale D capability cannot
authenticate against the new B listener; a missing source denies spawn.

Nine new **inert** capability tests use fake process snapshots and fake
`Popen` to validate no ambient injection, exact five-field capability,
single source, wrong release/SHA, endpoint, readiness, token and changed
epoch. Thirteen new LAB Grid v2 selector/guard tests validate source
origin, version and wheel mapping, package pins, LAB scope, synchronized
argv and native-denial-before-import. Neither suite executes native
Windows/PG18, validates OS PID ownership or proves real external source
authenticity. The dedicated six-cell E workflow is requested to execute
these along with preexisting LAN/reconnect/fence tests.

## Remaining acceptance before CODE_GO

- Hosted six-cell exact HEAD E suite and mandated LAN Mux; resolve actual
  Windows `DISCONNECTED` first-close root cause from logs, no timeout relaxation.
- Verified B candidate built single v2 wheel `0.2.0.dev0` SHA and exact
  sdist RECORD; B1 902 roster, source commits and package ancestry.
- C-owned native ephemeral PostgreSQL 18: canonical producer `market_data`,
  real immutable role/trigger witness, non-bypassable transactional writer
  fencing, 32 concurrent writers + crash/reacquire and stale-role negatives.
- Re-anchored Root capsule with approved source and actual wheel lock,
  current protected native service identity and old-listener/legacy-writer
  quiescence; **not currently permitted**.
- B v2 managed loopback HTTP read from actual PG18 read-only connection
  and D v2-only chart `PARTIAL` with Math source; no mock SQL in positive E2E,
  no source/provider authenticity or exchange completeness upgrade,
  `paper_admitted=false` and `trading_authorized=false` always.

**CODE NO_GO / PRODUCTION NO_GO**. No main merge, force push, branch
deletion, user PostgreSQL modification, real trade, credential disclosure
or physical service activation.
