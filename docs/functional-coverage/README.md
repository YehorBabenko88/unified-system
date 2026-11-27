# H — Functional capability ledger (ROUND26)

This is an auditable **source-path inventory**, **not a production capability claim**. Source pins and original implementation paths are in `capability-ledger.v1.json`. All 27 capabilities have `NOT_RUN_EXACT_PIN` until original CI/evidence is attached. Nothing is marked READY or COMPLETE.

## Status model

- `SOURCE_PRESENT`: observed source entry point; not proof of runtime operation.
- `CANDIDATE_MIGRATED`: candidate implementation or port exists; requires verified data, equivalence and owned integration.
- `PARTIAL_CONSUMER`: bounded/read-only/partial function exists, not full source-verified E2E.
- `NOT_INDEPENDENTLY_VERIFIED`: no adequate direct evidence of the requested end-to-end function.
- `UNKNOWN_SOURCE`: no confirmed source; no synthetic exchange claims.

## Concrete source observations

1. Grid `market_data_v2/read_api.py::qualified_snapshot` exposes `/internal/v2/candles/qualified`: **bounded 1m**, limit 1..1000, with status `UNAVAILABLE` or strictly qualified `PARTIAL`-class data, **not complete exchange history**. The managed listener requires Root startup identity. `market_data_v2/qualified_read_contract.py` validates a closed provenance record.
2. Terminan `terminan/qualified_partial.py` validates immutable-looking Grid `PARTIAL` observations for **display only** and explicitly denies paper/strategy authorization; a matching consumer exists but no native browser qualification is inferred.
3. Math `python/market_compute_api.py` is the pure SDK and provides `math.market.orderflow.stream.v1`; `market_math` owns footprint, delta, POC, volatility, timeframe/numeric and paper kernels. Bound stream resource usage and compare against original source oracle before migration approval.
4. Grid `market_data/history_range_audit.py::assess_declared_history_range` deliberately reports `BOUNDARIES_PRESENT`, not history completeness. Do not infer interior coverage from a first/last timestamp. `market_data/data_capabilities.py` lists OI/funding/book capabilities but flags alone are **not proof** of actual feeds/history.
5. Distinct Meta/Strattester candidates exist for historical archives, streaming books, trade archives and strategy research; protected or old source paths remain in evidence until positive equivalent contracts are accepted. `market_cap` has no confirmed canonical input and must remain `UNKNOWN_SOURCE`.

## Immediate functional slice to accept jointly with B, D and J

`Grid: original immutable 1m records → Grid v2 qualified PARTIAL DTO → Math: pure verified quantitative function → Terminan: display-only PARTIAL and no paper authority`.

Required original-pin acceptance: pinned identity, strict DTO fields/schema, sorted unique minute starts, provenance/source identity, bounded page+stream memory, correct price/volume/delta/POC units, timestamp/event availability and exact gap semantics. Negative controls: missing/ambiguous record, forged freshness, discontinuity, absent source, unsupported timeframe, duplicate trade, unsupported OI/funding/history, huge payload and false READY. **Do not fill missing candles with synthetic market history.**

The next transport slice is historical trades/archive + detected gaps + delta/footprint/POC, then funding/OI with separately attested availability. All supported timeframes must be enumerated from the actual Grid provider code before promising an interval list. A higher timeframe derived from incomplete 1m data must stay unqualified. Historical L2 is not assumed available.

## Cross-owner handoffs / acceptance

B is the sole Grid/Bybit collector and public read provider; D is the sole Terminan consumer/strategy owner; Math owns computation, G retires only with proven equivalence and J integrates only approved slices. All source tests / native Windows / browser / source-attested provider E2E remain **NOT_RUN by H**. No CI manual dispatch, no merge to main, no trade, no change to frozen PR #166 or security gates.

**CODE NO_GO / PRODUCTION NO_GO.**
