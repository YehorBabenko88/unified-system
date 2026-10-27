# Architecture v0

Installer (future) -> supervisor -> module capability manifests and read-only adapters -> Terminan. The supervisor controls orchestration only, not trading authority.

States: INFRA_PREFLIGHT -> INFRA_READY -> STRAT_RESEARCH -> STRAT_RESULT_SEALED -> HANDOFF_VERIFIED -> GRID_READ_ONLY_READY -> OBSERVING. BLOCKED and DEGRADED are explicit. Strattester handoff is historical research, not live market evidence. Grid operation and trading require separate external authorization.

Missing modules remain UNAVAILABLE and cannot be silently replaced by synthetic data. Every module publishes a stable protocol version and capabilities. Reject incompatible major versions, invalid identities, and mismatched artifact hashes. Never share a writable SQLite database or grant Terminan order credentials.

Existing sources: Grid docs/UNIFIED_RESEARCH_LIFECYCLE.md; Terminan terminan/source_contract.md; Terminan Issue #21. This prototype is an offline mock and is not a real installer.
