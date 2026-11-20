# Unified System

The canonical application has four owners:

| Module | Responsibility | Repository |
|---|---|---|
| market_data | Acquisition, history, provenance and persistence | strattester |
| math | Numerical kernels, rounding and statistics | math |
| terminan | Analytics, UI, simulation and strategy replay | Terminan |
| unified_system | Infrastructure, services, installation and integration | unified-system |

Release status: **NO_GO**. Source migration is in progress. Exact-head hosted CI, clean Windows installation, update/recovery, original-data backup/restore and independent operational acceptance remain release gates. Grid and Meta Analyse are preserved migration sources until all unique capabilities and necessary data have moved.

The infrastructure command validates a pinned runtime configuration in prepare mode:

```text
python -m unified_system --config C:\path\runtime.json
```

Preparation validates four owners and creates no runtime. Protected service activation uses separately admitted source, identity, credentials and ownership receipts. Worker source preparation offers export, prepare and inspect; materialization invokes the admitted ACL backend and requires separate qualification. It creates no fleet credential. The historical offline demonstration and its separate lifecycle implementation have been removed.

See [canonical architecture](docs/canonical-architecture.md), [signing policy](docs/CODE_SIGNING_POLICY.md), and source-bound evidence in MASTER #111. Existing user data and services are preserved. Trading checks use simulation.
