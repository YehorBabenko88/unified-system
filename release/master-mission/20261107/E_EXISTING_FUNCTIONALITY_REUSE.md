# E — Existing functionality reuse

Reuse Grid ingestion, continuity, feature extraction and replay; existing Strattester engine and PaperLedger/PaperAccount; existing Math statistics and MetaAnalyse; existing Terminan views. Do not create another Python research core, ledger or competing consensus.

| Candidate | Data required | Existing basis | Missing acceptance |
|---|---|---|---|
| False breakout | trades + causal level definition | Trade continuity and replay | Level/exit validation, costs and OOS |
| Absorption | trades + ordered book | Partial tape and book snapshots | True absorption feature and gap-safe history |
| Flow breakout | trades and explicit flow units | CVD/tape partial features | Definition, latency and OOS mapping |
| Retest | causal levels and trades/bars | Existing replay/backtest | Level causality and intrabar uncertainty |
| VWAP reversion | trades or declared bar proxy | Existing aggregate features | Session/units/regime and costs |
| Book imbalance | ordered valid book | Snapshot features; narrow PR268 | Persistent invalidation and historical L3 |
| Speed impulse | timestamped trades | Existing trade ingestion | Clock/latency normalization and selection bias |
| Wall reaction | ordered depth + trades | No durable L3 replay established | Wall lifetime/queue/cancellation evidence |

This is a requirements matrix, not implementation of eight strategies. Source entrypoints and exact test references remain in the 88-row JSON. Terminan legacy /saved and /lab views differ from Sync Research/Paper heading stubs. Fixture-input readiness correction used catalog-required sibling commits, not the six audit snapshots; it does not repin the runtime baseline.
