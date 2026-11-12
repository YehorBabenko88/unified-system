# Raw capture adapter offline TDD

Approved source scope: Root decision SHA256 887ad08552808029f420571768c3def4601014a4646079404ecdfe9823e1a776. Exact production base 1da10616a2b8217930f354e17caaa6fcea22dac4 / tree c2b39329924810535add3b02c3f5c5e1b11bdf62. Only new adapter, exact local-link schema and these owned tests/docs are added. Existing ObjectStore/Journal, frozen562/PR89/09b, Grid hooks and shared workflows are untouched.

Both methods async, direct bounded local IO, no internal await/queue/executor/retry. Root creates one owned ObjectStore and a separate initialized private existing Journal in the same private parent. PendingPublicationJournal schemas must not be mixed. Caller supplies RawCaptureProfile with explicit positive sqlite_headroom_bytes and inventory_file_limit; missing/invalid values refuse admission. A3 observation bytes remain opaque and unchanged; Grid owns its canonical/u63/calendar/source-identity validation. The local-link decoder independently enforces exact six fields, full lowercase hashes, exact integer-not-bool counts, null/empty distinction, canonical ASCII and duplicate/float/exponent/negative-zero rejection.

Profile ceilings: 16 total observations, 4 MiB payload occurrence bytes (including hash-deduplicated occurrences), 1 MiB/frame, 16 KiB/observation, one in-flight call, 16 MiB logical observed state. A3's two control slots are within the total and source-owned. Counters derive from the validated Journal, never reset at adapter reopen. Prospective file count includes distinct object hashes and one transient ObjectStore staging alias, including zero-byte objects. Inventory is bounded and current/predicted/post-write logical sizes are checked with supplied SQLite headroom. Orphans/unknown files/staging/sidecars deny new writes and remain retained. UNKNOWN writes latch the instance closed for new captures; read_capture reconciles only an already journal-linked exact hash. Missing link is not a resend grant.

Returned frozen LocalRawCaptureReadback includes actual bounded observation/payload bytes, actual hashes/counts and existing verified Journal body digest. Journal.read verifies stored digests but returns the canonical body without a digest field; the adapter derives that same digest from the verified body. All authority/publication/replica flags are false; durability UNKNOWN. Facts can never authorize current read, source completeness, native commit or quota.

## Original RED/GREEN evidence

All artifacts are retained under the Agent4 task outputs, no cleanup:

* raw-capture-tdd-20261112-red-r1: 12 expected failures, missing approved adapter, exit1, child retired.
* raw-capture-tdd-20261112-green-r1: candidate failed with seven errors; diagnosis reproduced KeyError for the absent digest key. Existing Journal was not modified.
* raw-capture-tdd-20261112-green-r2: 12 PASS after adapter/test oracle correction.
* raw-capture-tdd-inventory-red-r1: targeted bounded-scan regression failed (1000 iterator elements consumed vs expected <=12).
* raw-capture-tdd-20261112-green-r3: 13 PASS after bounded iteration.
* raw-capture-tdd-count-red-r1: independent review P2 reproduced; file-count exhaustion occurred after mutation and yielded WRITE_OUTCOME_UNKNOWN instead of preflight capacity rejection.
* raw-capture-tdd-20261112-green-r4: 15 PASS after prospective object/alias count preflight, zero failures/errors/skips, 1.014 s unittest duration, child exit0/retired. Named scratch files total 1181157 bytes, combined output1977 bytes.

Independent static review accepted the prospective count fix with no remaining findings. It performed no additional test/DB execution. Evidence hashes are recorded separately in EVIDENCE.json. Earlier failed/intermediate runs are not relabelled GREEN.

Tests used existing Python3.12 venv launcher SHA256 0b471133e110cfb53a061cad528ce8e517d7b9ac41a0a396c39ad795a487fc14 with -I -S -B, stdlib only, no event loop, sockets, provider, dependency install or physical corruption. Explicit fresh retained scratch per run. Store/SQLite effects are ordinary owned test writes; append response loss and namespace oversize are Python test mocks, not physical filesystem fault injection. Test helper drives the direct coroutine and rejects suspension instead of creating asyncio selfpipes.

Wall limit 30 s plus 5 s retirement wait targeted only the started own process; output256KiB/state16MiB were postchecked. Recorded CPU/peak-memory samples belong to the Windows venv launcher/process observation and do not establish whole-interpreter-tree CPU/RAM caps; initial RED peak metric was null. No native hard memory/disk quota or strong child-tree boundary qualification is claimed. These are bounded offline unit results, not Root SourceGate, hosted/native/physical/runtime evidence. Root's stricter later allocation supersedes test proposals.

Physical disk transient growth, FS allocation/metadata and SQLite overshoot between measurements remain UNQUALIFIED. No deletion/refund/orphan promotion, service/port/PG change, logical consensus mutation, real provider send, committed dataset/checkpoint, repair or physical backup is admitted. Root/A8 runtime/native/physical gates and separate Grid integration qualification remain required.
