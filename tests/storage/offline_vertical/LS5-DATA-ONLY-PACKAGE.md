# First isolated LS5 storage package

2026-11-12. SOURCE_READY / EXECUTION_GATE_PENDING / NO-GO.

Nearest implemented backend: existing Unified PR56 ObjectStore + SQLite Journal, HEAD 1da10616a2b8217930f354e17caaa6fcea22dac4 / tree c2b39329924810535add3b02c3f5c5e1b11bdf62. Selected Storage sources contain no PostgreSQL/asyncpg dataset backend. Creating one would be new implementation; a separate PostgreSQL service is not needed for this legitimate DATA_ONLY profile. PostgreSQL integration remains unavailable pending an existing reviewed adapter and separate instance gate. No production PostgreSQL, service or data path is opened.

## Exact package and evidence

Source branch feature/storage-offline-source-20261111 contains only tests/docs in this directory; production APIs remain exact 1da. Existing source_cases.py (20470c61...) five methods and negative_source_cases.py (98336772...) eight methods are preserved. New restore_source_cases.py adds two local copy/restore methods; readback.sql contains actual SQLite read-only queries. Exact full raw pins are in the separately generated source package inventory, not assertions of execution.

Agent 3 owns Grid D6 d6b72b66ff1b85b7e6b956568342ad6bd8bfcfbe / tree 066bbe51900e88dd53541baf29a777037ed10b5b, synthetic producer f1f548daeeae5f41df497f849a275df512a92b32d02e8d83c47d9fe836fad3b6 and review2 suite 2980f58c2678ee4cf1688a5b717d66faaa536dc56e4c68535f5c09821d3ddfca. Root calls producer once, passes the same six exact byte entries to adapter/Storage suites. No fixed scientific packet, invented identity schema, duplicate ingestion/store or committed manifest is introduced.

Historical actual evidence: PR56 recorded four hosted prerequisite jobs at exact 1da, 22 cases/job and six separate inventory controls, not native/physical acceptance. Original verification SHA256 f50a51788deffe2f67d9f9eb82a82329f247515564b3cdca6c6e8fceff546ddf. New five/eight/two source suites have no execution results in this package. A3 reports Root offline11 attempt1/diag2 FAILED_OR_UNKNOWN with zero methods/entries at import/effects boundaries; do not describe those attempts as ingestion/readback PASS. Their original evidence and Root classification remain authoritative; this document does not reclassify them or retry them.

## Concrete proposed allocation (Root must approve/enforce)

* Node LS5 only, foreground bounded child under Root custodian; no daemon, listener, port, Windows service or scheduled task. DB port: NONE. DB name: local.sqlite inside each exclusively created case root.
* Proposed new parent: C:/Users/LS-5/Documents/Codex/2026-11-06/codex-agent-4-distributed-storage-integrity/outputs/ls5-data-only-20261112-r1. This is a path proposal, not allocated state. Root must reject preexistence/alias/identity uncertainty and provide separate child-suite parents; never adopt an existing root.
* Raw archive: each admitted ObjectStore objects/<SHA256>. Optional gzip bytes in the restore test use standard-library gzip.compress(mtime=0) and full exact decompression readback; this is test-data encoding, not a newly implemented compression/archive service or verified physical backup. Raw original bytes remain stored separately.
* Proposed limits per separately allocated child: one process, wall 60 s, CPU 10 s, RAM 256 MiB, final mutable state 16 MiB, stdout/stderr combined 1 MiB; no provider/DNS/connect/HTTP/WS/process spawn. These are proposed policy values, NOT implemented reservations or measured budgets. Root must review/enforce applicable OS/resource mechanisms before effects. Read-only admitted runtime/dependency capsule bytes are accounted separately.
* Root pins executable/native DLLs/dependencies, source namespace and absolute origins; empty CWD, minimal environment, absent-.env probe only, bytecode/site hooks disabled. Existing Grid Settings import reads environment/.env. No runtime install/download/provision is performed by this package.

## Actual calls and readback

Existing ObjectStore.create/open/put/read/verify; build_local_closure/stage_local_closure/readback_local_closure/copy_local_closure; Journal.initialize/read and PendingPublicationJournal.retain/mark_attempt_uncertain/recover_original/verify_staged_original/observation. readback.sql checks SQLite structure and actual transitions rows through a read-only connection; Journal.read still validates chain digests. There is no SQL dataset catalogue or COMMITTED checkpoint table in this backend. The declared local closure is the byte inventory, not native metadata publication.

Proposed cases: A3 six adapter/UTC/dedup/gap assertions; A4 five exact-byte/closure/journal readback; separately gated eight negative limits/corrupt/missing/conflict/UNKNOWN cases; separately gated two restore cases. These are separate inventories, not an already qualified combined 21-method run. Root selects one exact bounded packet at a time; previous run admission does not transfer.

Restore source test one copies the existing byte closure to new backup and restore roots, reopens and hashes every restored object, then separately round-trips compressed raw. Test two corrupts one byte in a just-created owned backup object after identity/link checks, calls actual copy_local_closure and requires failure before any destination object. All copies are on LS5; failure-domain independence and physical backup success remain unproved. Corrupt file and all final artifacts remain retained. Existing ObjectStore internally unlinks only its own transient staging alias after identity checks.

## Shutdown, rollback and remaining blockers

Shutdown: Root owns one child's exact handle/PID+start identity, bounded wait and reader drain; no broad process-name kill. Stop only that allocated child on timeout. SQLite connections use existing context-managed Journal methods. There is no listening service to stop. Rollback is stop the own child, preserve all new directories/evidence and leave production/source baselines unchanged; no automatic directory or database deletion.

Current reopen assertions are same-process object reopen. True checkpoint/process restart and interruption require a separately reviewed two-child plan: phase A retains exact opaque bytes and records local uncertainty, Root conclusively retires child A and drains readers, phase B opens only the same exclusively allocated private paths and verifies original bytes/hash chain/UNKNOWN; producer output and quality are rechecked against pinned fixture bytes. No such child runner or actual interruption is admitted here. Atomic historical checkpoint, active authority cursor, native committed receipt, independent replica placement, physical restore, ENOSPC and Windows power-loss durability remain BLOCKED.

GO requires Root exact package/effects/runtime selection and explicit physical allocation. Neither source review nor Draft PR authorizes deployment, real sends, logical metadata mutation under strictD4, existing DB access, cleanup or service/network changes. Agent 2 ACK-dependent operations remain closed.
