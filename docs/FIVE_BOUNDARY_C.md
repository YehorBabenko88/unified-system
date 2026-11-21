# Independent Strattester/Grid boundary (C)

Frozen Unified PR4 base b8facc028e00493d8423d15280f87c2047c2b63b. Strattester PR43 source943095d00d5d56276f3832c42b36b290bea77a84 and Grid PR249 sourcebf9f108b6777085d6725675eac778d61ec55f42b remain unchanged. Current newer research/Math branches retain their independent ownership; this adapter targets the audited additive v1.1 historical contract rather than assuming compatibility from branch names.

`ReleasePin` separates git commit/tree from a 64hex immutable package digest. The caller must independently establish trust in those pins. `HistoricalBoundary.verify` reconstructs the exact retained input windows, data-quality checks, model/strategy/assumptions, dataset digest and terminal receipt without importing or executing the producer. Only independently admitted identity/revision/run/receipt pins permit `VERIFIED_SOURCE_RECEIPT`. This means owner-policy admission, not independent host/runtime attestation. Empty policy, missing release bytes, corrupt/partial/mixed inputs, unknown versions and rehashed forgeries remain UNAVAILABLE. No receipt authorizes trading or installation.

`lifecycle_verifier` binds only STRAT_RESULT_SEALED/HANDOFF_VERIFY COMPLETE observations to B's exact transition/status/counters. Release bytes belong to the configured oracle, never the JSON event or journal. INFRA/history progress/observer/Grid READY require separate fresh source-owned observations; they cannot be fabricated from a research receipt. `MarketBoundary` verifies the release and bounded page/record identity, content hashes, quality, epoch/windows and numerical consistency. It never upgrades GAP/STALE/UNAVAILABLE or treats historical footprint aggregates as live L2. Current Grid has no independently admitted exchange completeness receipt: PARTIAL remains PARTIAL. Market-data ingestion requires no trading capability, order API or exchange key.

| Source owner | Unified responsibility | Safe cutover |
|---|---|---|
| Strattester history/research and result store | independent receipt/window oracle | opt-in release+owner pins; source-owned SQLite remains single writer |
| Grid current ingestion and footprint producer | read-only page inspection and historical handoff validation | no subscriptions or orders started by this code |
| Existing provenance_v11 conservative adapter | unchanged legacy fail-closed semantics | new oracle separately named; no silent loosening |
| Unified lifecycle | accepts exact bound completion proof | B stack tests needed; no source import at runtime |
| Terminan/Math | observe outputs / independent numerical API | release-pinned adapters, never source authenticity from CI |

`scripts/verify_five_boundary.py` pins source HEAD/tree, runs actual ResearchRunner with a fake history client and disposable SQLite, verifies independent receipt then passes the actual output to Grid's actual handoff validator. Actual FootprintBuilder/minute_record generates a PARTIAL market page. Synthetic package bytes and owner pins are deliberate fixture policy, never real source attestation. Windows/Linux CI runs the script and uploads exact-head/tree JSON+SHA evidence.

P0: no execution/order path. P1 external: real signed packages, owner/source receipts, fresh observer/infra/history progress contracts, exchange completeness evidence and authorized module launch/provisioning adapters. P2: bounded 900KB historical artifact, regular-time-grid source semantics (irregular funding requires independent cadence evidence), per-file source snapshots do not establish globally simultaneous capture. SOFTWARE synthetic-only; SOURCE_PROVENANCE owner policy externally required; PHYSICAL NOT_RUN; PRODUCTION NO_GO.
