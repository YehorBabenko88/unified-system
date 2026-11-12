# Root launch card: M0 / M1 / M2

2026-11-12. SOURCE_ONLY / ROOT_EXECUTION_GATE_PENDING. Existing ObjectStore + SQLite, no port/daemon/PostgreSQL changes. Production base exact 1da10616a2b8217930f354e17caaa6fcea22dac4 / tree c2b39329924810535add3b02c3f5c5e1b11bdf62. Source-only Draft PR89 supplies the invocation module; no production core edits. File SHA256 and byte inventory are in source-package-inventory.json. Do not use a stale manifest/commit: Root selects the final exact PR head and external manifest digest.

## Exact software/data input

A3 producer prepare_synthetic.py SHA256 f1f548daeeae5f41df497f849a275df512a92b32d02e8d83c47d9fe836fad3b6 against Grid D6 d6b72b66ff1b85b7e6b956568342ad6bd8bfcfbe / tree 066bbe51900e88dd53541baf29a777037ed10b5b. Root admits it once, gets six existing local closure entries: artifact, descriptor, request, input_rows, input_coverage, producer_metadata. Aggregate payload <=65536 bytes, unique hashes, empty declared dependencies. No fixed scientific descriptor/codec or schema migration.

Raw synthetic fixture provenance: bybit/linear/BTCUSDT instrument_version='1' as fixture data only; [1767225600000,1767225780000) UTC milliseconds; observed 1767225781000. Raw CSV four rows including one duplicate, SHA256 d039f5c8da1047d9aa9558f51b3b0cb06b5711ce498e993334498744a674363b. Two candle rows and book snapshot/delta are exact literals in producer. Generated six-payload hashes and lengths are UNOBSERVED until the admitted producer actually runs; record them from returned entries and freeze the exact LocalByteClosure bytes outside each child before restart. Never invent generated pins in advance.

## Three explicit calls (Root custodian, not a standalone CLI)

The admitted custodian loads exact pilot_phases.py by its pinned path; no automatic discovery or main entry point. The following are invocation notation, NOT authorization to execute:

```python
entries = producer.prepare_local_test_entries(admitted_grid_root)  # ONCE
closure = build_local_closure(entries).canonical_bytes             # pin externally
m0 = pilot.seed(new_private_root, entries)
# Root conclusively retires M0 child and readers, then starts admitted M1 child.
m1 = pilot.inspect(same_private_root, exact_retained_closure_bytes)
# Root retires M1 before separately allocated M2, all handles/process identities recorded.
m2 = pilot.restore(same_private_root, exact_retained_closure_bytes,
                   new_private_restore_parent)
```

Root must pass exact closure bytes to later children through its reviewed bounded input mechanism; this package adds no file exchange framework or process launcher. Same-process calls establish only reopen; a process-restart result requires actual distinct child identities and retirement evidence from Root. A3 review2 suite 2980f58c... can assert the decoded synthetic UTC/dedup/gaps from the same original entries, but its prior source ACK is not execution evidence or an automatic additional test allocation.

M0 creates only the new root/archive ObjectStore and new exclusively created local.sqlite. It stores exact six payloads and LocalByteClosure, retains that closure as opaque local test bytes, repeats retain and uncertainty markers idempotently. Expected actual local rows: two, phases RETAINED then ATTEMPT_UNCERTAIN. M1 checks full object hashes, original bytes, journal chain and SQL rows after reopening. SQL uses SQLite mode=ro + query_only, PRAGMA integrity_check, COUNT(*) and actual sequence/state/previous_hash/digest/receipt rows, then decodes those receipts. Report includes actual six decoded payload records and their exact sizes/hashes. There are no market-schema SQL tables or authoritative checkpoints here.

M2 validates the source first and copies the complete existing closure through new backup and restored ObjectStores; re-hashes all restored bytes. Local roots are not independent failure domains. It explicitly reports journal_restored=false and physical_backup_verified=false: this phase restores immutable byte closure only, not a live SQLite database, cluster authority or physical backup. Separate negative/restore test suites are not implicitly run by these phases. Gzip source tests remain optional separately allocated test encoding; the pilot stores original raw bytes unchanged.

## Exact mutable namespace and bounds

Proposed root: C:/Users/LS-5/Documents/Codex/2026-11-06/codex-agent-4-distributed-storage-integrity/outputs/ls5-data-only-20261112-m0-r1. Proposed separate restore parent: same task outputs/ls5-data-only-20261112-m2-r1. Neither is allocated by this source work. Root may choose other new paths after identity review; preexisting paths are rejected. Archive paths are archive/objects/<hash>, SQLite local.sqlite. M2 uses its own backup and restored children. Keep source/runtime/dependency capsule read-only and separate.

Earlier A4 proposed ceilings were one child, 60 s wall, 10 s CPU, 256 MiB RAM, 16 MiB mutable state, 1 MiB combined output. They are not permission to expand an existing Root packet: Root's tighter allocation wins (A3 reports current 15+5 / 30+5 wall/retirement bounds, shared 256 KiB output and 2 MiB result limit). The exact applicable Root caps must be attached before any phase runs. Existing payload validation is not OS quota enforcement. Root must admit and enforce limits, secure the new parent against aliases/concurrent modification, and review inherited handles. Every final artifact is retained; existing ObjectStore.put internally unlinks only its own verified temporary staging alias. No test-data deletion, database migration or live database copy.

Before imports: Root reviews CPython/stdlib/native DLL closure including _sqlite3, dependency/module namespace, no bytecode/site/.pth hooks, empty CWD/minimal environment/absent-.env probe only. Existing Grid Settings and SSL/public trust reads require Root's actual applicability gate. Independently enforce DNS/connect/HTTP/WS/process denial before imports, without altering office network settings. Runtime/import boundary failures must remain FAILED_OR_UNKNOWN, never ingestion PASS. ObjectStore's Windows namespace durability remains unqualified; no WinAPI shim or power-loss claim.

## Stop / recovery / rollback evidence

Root controls exact own child handle/PID/start identity and reader drainage; timeout stops only that child. Record pre/post source/package/runtime seals, admitted root identities, six actual payload byte hashes, exact closure bytes/hash, SQL rows and row_count, original phase/native UNKNOWN, each phase output, process exit, monotonic duration and all boundary failures. Do not infer successful child restart from in-process reopen.

Rollback: retire only own child, preserve own roots and evidence, leave existing PG18.6/services/provider/network state untouched. No automatic recursive cleanup. Corruption/interruption/SQLite backup restore are separate bounded packages, not hidden effects in M0/M1/M2. Native COMMITTED/authority cursor/replica eligibility/source authenticity remain unavailable; strictD4 and Agent2 ACK-dependent effects stay closed.

No execution has occurred for this new module. Independent static source review found no actionable P0/P1/P2 findings and performed no imports, Python execution, tests or DB operations. This module is a separate source successor, not part of the frozen 562-file/offline11 capsule or its admission. Root selection and Root/A8 required checks precede physical sequential allocation.
