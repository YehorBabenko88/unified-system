# Storage Stage1 nonproduction contract slice

This additive slice contains pure untrusted contracts, an in-memory byte verifier and a nonexecuting retention planner. It opens no listener, factory, DB, filesystem mutation, authority commit, actual backup/repair or cleanup executor. It creates no second SQLite/consensus authority. Existing modules are untouched.

## Boundary and API

`decode_untrusted_claim(bytes)` bounds canonical JSON, rejects duplicate keys, numeric literals, non-ASCII values and noncanonical encoding, and returns a detached UNTRUSTED claim. It is a generic parser, not Agent 3's V3 checkpoint schema validator. `require_publication_authority(...)` always raises PROOF_ADAPTER_UNAVAILABLE. No supplied callback, environment value or parsed COMMITTED field can promote it.

`SegmentClaim.from_mapping(dict)` requires exact Stage1 fields: schema, dataset_id, instrument, source_id, partition_id, data_kind, schema_version, encoding, start_ms, end_ms, sha256, byte_length and record_count. Instrument has exchange/category/symbol/instrument_version; versions/counters/time bounds use canonical checked u63 strings. Schema is unified.storage.segment-claim.stage1, schema_version1, encoding jsonl.stage1. This fixture framing is not an ingestion/storage adapter or supported format declaration for existing Grid WAL/Bybit raw responses.

`verify_segment_bytes(raw, claim)` checks full SHA256/length, newline-terminated frames, closed framing record schema, record count, exact instrument and half-open event range. Each JSONL record contains schema_version, event_time_ms, instrument and payload object; records are bounded by the local claim parser. No caller path is opened. It returns BYTES_MATCHED_UNTRUSTED, authority_verified=false, source_completeness=UNKNOWN. Hash/framing agreement does not prove publisher trust, complete source coverage, durable storage or a VALID replica.

`plan_retention(RetentionFacts)` consumes frozen proposed replica/pin/closure facts and returns KEEP or QUARANTINE_CANDIDATE. Byte-matched survivor claims must name distinct nodes and volumes; existence-only, missing, wrong-hash or unavailable claims do not count. Active research/dependency pins, unknown closure, unresolved gaps, live uploads, insufficient survivors or unelapsed retention preserve data. Every returned plan has executable=false and ACTUAL_AUTHORITY_PROOF_UNAVAILABLE. There is no Verified Delete or quarantine action, trusted-copy count, authoritative snapshot or permission token. It cannot guarantee a caller's facts are current; actual authority/replica/pin proof remains absent. Retirement and disk pressure confer no deletion permission.

All identifiers/facts remain claims. Full coupled eligibility/revocation/GC protection, durable survivor obligations, actual volume incarnations/allocation accounting, authority session/grant CAS and receipt verification remain later owned adapter work. Planner candidates cannot enter a production executor.

The current survivor selection is an input-order-dependent conservative lower bound, not maximum bipartite matching. It can retain extra candidates unnecessarily when node/volume labels overlap. This minor planning limitation is deferred; it cannot increase survivors beyond an actual distinct-label selection or enable an effect. Physical independence and current proof still require a real adapter.

## Exact checkpoint compatibility inputs

Test-only snapshots preserve Agent 3 NEW owner V3 schema SHA4de720d9391e5a89c0577b5298c283e742fbfe490c4454c184e31c2348589ea4 and producer mapping review4 SHA570437ac72c718b46d620db04e58b768dc962db34df856cc7ad25313462ac539. Nested tests/storage/.gitattributes preserves raw fixture bytes including line endings without editing shared attributes. Owner decision is Unified381b18bab7f1162db4eef7f348b6e1c921e76403, release/contracts/checkpoint-v3-time/DECISION.json.

Immutable content keeps required committed_at_utc:null and exact commit_time_status:UNKNOWN_COMMIT_INSTANT. confirmed_observed_at_utc is external audit, never backhashed into original publication content. COMMIT_UNCONFIRMED has no content/evidence success; structurally COMMITTED remains untrusted. These tests exercise compatibility and deny-only boundaries, not the full A3 codec or actual A2 publication evidence. Old formats are not rewritten or aliased.

## Verification

Python3.11+ standard library only. Run from repository root:

```
python -B tests/storage/run_stage1.py
python -B -m unittest discover -s tests -v
```

The Stage1 runner requires an explicit exact 26-case inventory and zero skips, binds physical source/fixture hashes before and after the run, and reports HEAD/tree plus dirty state. A dirty-source run is not represented as committed source. Fixtures alone may use a disposable filesystem; product modules have no file-write API.

Every runner Git subprocess forces `git --no-replace-objects`; any refs/replace entry is rejected before test discovery. `python -B tests/storage/probe_runner_guard.py` verifies original blob/tree replacement rejection ONLY inside a separate disposable .git clone with no shared replace refs. This source-guard evidence is separate from the unchanged26model cases and from runtime acceptance.

RED logs cover missing contracts/segment/retention implementations and the initial forgeable ByteCheck authority flag; GREEN logs are local evidence only. The result is not runtime replication, durable checkpoint recovery, restore acceptance, Windows HA/NTFS qualification or physical backup/cleanup evidence. Baseline/project failures/skips and hosted/physical NOT_RUN states must be reported separately in the handoff.

## Storage ADR

Keep pure facts and byte verification independent from authority. Matching bytes can help detect corruption, but cannot create a distributed commit or delete permission. The selected event-ordered v3 authority and exact owner checkpoint mapping are future explicit adapters; no precheck/local commit fallback, lifecycle-receipt alias or synthetic success is installed. No full feature/runtime admission follows from this independent slice.
