# C — Data architecture and provenance

Instrument identity must include provider/category/instrument identity, not symbol aliases alone. Reuse existing schemas; no new universal wire format. Record dataset/version/hash, event and observation times, sequence continuity and source provenance separately. Byte integrity, dataset completeness, replication and authority freshness are independent properties.

L1 OHLCV supports bar models with explicit intrabar uncertainty. L2 trades supports observed trade flow, not reconstructed orderbook queue state. L3 requires initial snapshot plus ordered deltas, gap detection and resync; durable historical L3 replay is not established. L4 live paper requires admitted provider policy and observed data. Missing orderbook history means unavailable, never invented book events.

Checkpoint v3: committed_at_utc=null with UNKNOWN_COMMIT_INSTANT is compatible with independently proven commit. Require authoritative committed revision, commit identity and verifiable evidence; confirmed_observed_at_utc identifies its own observation source. COMMIT_UNCONFIRMED remains distinct. No timestamp replaces fencing/revision/authority. Preserve old format semantics and canonical null/timestamp/status/evidence encoding.

Grid current snapshot capability correction does not persist invalidation immediately: the previously available row may remain eligible for five seconds. Proposed separate availability propagation is not approved or wired. No full-history completeness claim or 500-instrument capacity claim follows from analytical throughput estimates.
