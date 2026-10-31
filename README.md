# Unified System

Mission 1/2 integration work is on `mission1/six-module-runtime-20261031`.
The coordinated release inventory now recognizes all six modules. Runtime
service orchestration, authenticated deployment and physical acceptance on all
5–6 Windows PCs remain incomplete; unit tests do not establish those claims.
See [the design](docs/superpowers/specs/2026-10-31-six-module-physical-design.md),
[implementation plan](docs/superpowers/plans/2026-10-31-six-module-physical.md)
and [repository audit](docs/audits/2026-10-31/).

Contract-first, fail-closed orchestration for independent Strattester, Grid and Terminan modules.

**Status: experimental, offline-only.** No deployment, real trading, G1, service/ACL/DB mutation or physical acceptance is authorized.

Run `python -m unittest discover -s tests -v` and `python -m unified_system.cli --demo` with Python 3.11+; standard library only.

Modules remain independently installable. The supervisor never imports module internals. See `docs/ARCHITECTURE.md`.
