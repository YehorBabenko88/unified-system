# Unified System

Contract-first, fail-closed orchestration for independent Strattester, Grid and Terminan modules.

**Status: experimental, offline-only.** No deployment, real trading, G1, service/ACL/DB mutation or physical acceptance is authorized.

Run `python -m unittest discover -s tests -v` and `python -m unified_system.cli --demo` with Python 3.11+; standard library only.

Modules remain independently installable. The supervisor never imports module internals. See `docs/ARCHITECTURE.md`.
