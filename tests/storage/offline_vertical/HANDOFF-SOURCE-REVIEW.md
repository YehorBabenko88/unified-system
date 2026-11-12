# Offline source handoff for Root review

Status: SOURCE_ONLY / NOT_RUN / NO_RUNTIME_ADMISSION. Date: 2026-11-11.

## Exact inputs and ownership

Storage base: Unified PR56 HEAD 1da10616a2b8217930f354e17caaa6fcea22dac4, tree c2b39329924810535add3b02c3f5c5e1b11bdf62. Own branch feature/storage-offline-source-20261111 adds only this directory. No e410, bfa or PR265 adoption.

Grid base: PR283 HEAD d6b72b66ff1b85b7e6b956568342ad6bd8bfcfbe, tree 066bbe51900e88dd53541baf29a777037ed10b5b. Agent 3 owns fake adapter, normalization, fixture quality and Grid tests; Agent 4 owns immutable local bytes, exact closure readback and local journal reopen tests. Root owns custody, assembly and any future execution allocation.

A3 source artifacts under C:/Users/LS-5/Documents/Codex/2026-11-06/codex-agent-3-bybit-historical-live/outputs/offline-vertical-source-review1-20261111:

* prepare_synthetic.py SHA256 f1f548daeeae5f41df497f849a275df512a92b32d02e8d83c47d9fe836fad3b6.
* source_cases.py SHA256 4f96daad9b6944b517b3392b32db41df316b36e6ad834368a99de55221064476. This successor replaces e4cc9487 source: make_suite(entries) consumes the same prepared entries as Storage, without calling the producer again.

A4 source_cases.py SHA256 20470c61eb7fe8ef7809653bded0d3916d1be402d5312a9a358911771c36da7f. These are raw source hashes, not evidence of execution. A4 read the complete A3 source files and checked their raw hashes without importing them. No cross-repository runtime compatibility is asserted.

## Existing API boundary, scoped ACK

After separate Root admission only, prepare_local_test_entries(grid_root) returns an in-memory tuple of six existing build_local_closure entries (role, exact bytes, empty dependencies). Roles: artifact = generic synthetic normalized output; descriptor = local fixture provenance; request = exact disabled D6 request plan bytes; input_rows = exact synthetic raw bundle; input_coverage = local fixture observations; producer_metadata = non-authority replay marker. These names do not claim Strattester scientific artifact semantics or a native publication wire. No fixed c548/f499 packet is reused. Dependencies remain empty, so only the declared byte set is checked, not semantic dependency closure.

A4 make_suite(disposable_parent, entries) preflights exact tuple/roles, byte type, distinct hashes, empty dependencies and aggregate <=65536 bytes. Root supplies the already-reviewed entries, no producer import or invocation inside the Storage suite. Future setUpClass creates a new absolute, nonexisting disposable parent exclusively. Existing paths, databases and other agents' worktrees are never adopted; no automatic cleanup.

Existing ObjectStore.create/open/put/read/verify and build_local_closure/stage_local_closure/readback_local_closure preserve exact bytes. Local InventoryReadback remains native_replica_eligible=false, failure_domain_qualified=false, semantic_closure_verified=false and publication_confirmed=false. Reopen is local object/journal reopen, not process-crash, power-loss or cross-node recovery qualification.

Journal initialization targets only a newly exclusively created local.sqlite file. PendingPublicationJournal retains separately labelled opaque-local-custody-test-only:<raw SHA256> bytes, not a native intent or checkpoint. Duplicate retain creates one local record; reopen must recover exact bytes and UNKNOWN with no publication, retry or hold-release permission. No attempt marker/send is issued.

No generic market-event manifest/page builder exists at this seam. Do not fabricate manifest page semantics, source schema validation, historical checkpoint, authoritative cursor or committed receipt to fill that gap. Existing manifest candidate codec is separate and not exercised here. Unsupported dataset/checkpoint atomic join remains BLOCKED.

## Synthetic identity, time and quality

A3 source uses bybit/linear/BTCUSDT instrument_version='1'; identity is fixture data, not validated registry identity. Existing schema SHA256 b921dbae8dcc2231b571d11bc028ae7d04009234662760f8b72d5e3e70fdc5c7 is referenced only, not imported/adopted.

UTC half-open fixture interval [1767225600000,1767225780000), observed_at=1767225781000. Trade input timestamps are Unix seconds; candles/book milliseconds. Four trade input rows contain one exact duplicate trade ID; expected normalized count three. Minute 1767225660000 is explicitly missing. Cross-sequence jumps are not provider-gap proof. Provider continuity UNKNOWN and publication LOCAL_UNATTESTED are preserved. Marker purpose is LOCAL_REPLAY_TEST_MARKER_NOT_HISTORICAL_CHECKPOINT with null authority_cursor and UNKNOWN native_outcome.

## Planned bounded cases

A3 six methods: existing adapters/local entries; archive time reversal; cross-sequence jump; invalid sequence; trade reconnect ambiguity; invalid book levels. A4 five methods: raw exact bytes/idempotent reopen; foreign store identity rejection; exact local closure reopen/no publication; unavailable native result paths; exact opaque original/journal reopen/UNKNOWN. Subtests remain distinct from method count. All eleven methods NOT_RUN; no result count is inferred.

Future execution requires Root review of both complete source files, exact D6 source and fixture custody, dependency/runtime closure, import-time behavior, isolated child lifecycle, bounded output and exclusive allocation. No provider/network/background runtime, MicroEventStorage.start, archive_worker, production database, migration, deletion, deployment or scheduler/authority changes. Ordinary local writes occur only inside a later explicitly allocated disposable directory. Parent namespace replacement by a hostile concurrent process is not qualified by these unit cases; Root must supply an isolated admitted parent.

Agent 3 confirmed scoped ACK after reading A4 source and card: existing local byte/closure/journal mapping only, not execution/native/semantic/schema/checkpoint admission. A4 read the complete narrowed A3 successor suite and verified its hash; scoped ACK covers the same entries-only mapping. Root would call the producer once and pass the same entries to both factories. Generated bundle/output hashes remain UNOBSERVED. Exact Grid checkout: C:/Users/LS-5/Documents/Codex/2026-11-06/codex-agent-3-bybit-historical-live/work/grid-bybit-plan-source-d6b72-20261111; D6 HEAD/tree rechecked read-only.

GO/NO-GO: joint source review may proceed. Actual offline run NOT_AUTHORIZED. Positive distributed publication/current scientific READ and strictD4 remain BLOCKED. Root review, custody and allocation are separate.
