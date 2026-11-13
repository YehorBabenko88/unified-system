# Collector observational inspection v1

Source-only successor of67fe3275e3c3498d22896dc24a732bbf10e0720d /
treeb47e7adca105d2f24c007659763199d7e4397793. This source epoch is not qualified
by prior Root902/C0/C1/C2 or Gateway READ receipts. C3 remains operationally blocked.

## API and custody

`CollectorContext.inspect(root, *, context_id, store_id, binding_sha256, profile)`
is synchronous bounded local I/O. It does not construct a CollectorContext,
generate a writer incarnation/UUID, acquire a kernel writer lock, write a flag,
initialize/append a Journal, create/adopt/delete data, start tasks or resume work.
It must not be substituted with `open()`: open deliberately resumes clean state.

Before inspection the parent must independently own exclusive namespace custody
across child shutdown and inspection, and prove all owned Job processes and I/O
quiescent. One PID exit, task cancellation, an S byte or equal hashes cannot prove
that another writer is absent or cannot start. Inspector grants no custody or
authentication/authority and does not infer quiescence. This remains a separate
Root contract; inspect success must not be used to mint it.

Returns frozen `CollectorContextInspection` with exact context/binding/store,
state, writer_flag, checkpoint or None, actual history tuple, orphan_paths,
source_files (relative path, identity, bytes, mtime_ns, SHA256), logical_byte_count.
Nested checkpoints/raw readbacks and file records are frozen with immutable
bytes/tuples. classification=LOCAL_UNATTESTED, native_outcome=UNKNOWN,
publication_confirmed=false, quiescence_verified=false. Mtime is a source-change
check, never timestamp authority, freshness, a lease or native durability proof.

## Validation and resource scope

Existing input/profile/root checks and exact marker bytes bind the supplied IDs,
profile, root/raw-directory and writer-lock identities. The namespace walker is
bounded by the existing inventory profile; unexpected files/directories/links
outside raw objects/staging reject before SQLite access. No normalization is added.
Each full before/after byte pass has the persisted aggregate logical ceiling
(at most16MiB). Files are regular/single-linked and path/handle identities match.
The same directory identities and file names/lengths/mtimes/hashes must hold
before and after all decoding/readback. This observation cannot eliminate a
malicious concurrent writer/ABA race; caller custody is mandatory.

These caps bound logical bytes/files, not allocated disk space, hard memory/CPU
or process-time quotas. Two full byte passes plus bounded Journal decoding and
actual linked-object readbacks occur; do not describe the complete operation as
only one16MiB read. Read-only inspection does not require unused write headroom.

Before any SQLite connection, both Journal headers must be existing rollback-mode
SQLite files (read/write header bytes1/1). WAL headers2/2, sidecars, hot-journal
names and unexpected source files reject without attempting recovery. This avoids
claiming mode=ro by itself prevents WAL shared-memory/sidecar effects. No
immutable=1 shortcut or recovery/repair PRAGMA is used.

`Journal.read(*, max_records=100000)` adds one validated optional bound: exact
builtin int1..100000, a parameterized LIMIT max_records+1, reject overflow. Its
default chain verification, return shape and missing-file read semantics remain
unchanged. Inspector's actual lifecycle/raw queries use profile limits <=128/16
(sentinels129/17); it decodes the raw rows with existing decode_local_link and
uses existing RawCaptureAdapter._read/ObjectStore verification. It never invokes
_records(), whose default Journal bound remains100000+1. Other existing callers
are not newly claimed to use the inspector's smaller limits.

The pure lifecycle decoder and footprint walker are extracted from existing
writer methods; create/open/resume retain their existing behavior. Inspection
validates strict builtin lifecycle fields before semantic comparison/hash indexing.
Existing Journal chain hashes, raw content hashes/lengths and every completed
lifecycle observation/digest are reconciled. No fake FD/Journal/writer or second
storage engine is used. Missing checkpoint is explicitly None, not fabricated.

Only exact S plus valid STOPPED/no inflight, complete matching indexed/completed
history and no unlinked files reports STOPPED. Dirty/U/unfinished/inconsistent
completion or retained unlinked objects/staging files report UNKNOWN. Terminal
flag/event remains TERMINAL even when partials are retained. Orphan bytes are
hashed solely as source evidence, never adopted or verified against their name.
Linked corruption, missing referenced data, bad chains/bindings or source changes
raise explicit rejection; inspection never repairs or returns a confirmed dataset.

## Evidence boundary

Actual private Windows SQLite/ObjectStore tests only; no service/SCM, ACL, TLS,
PostgreSQL server, native C3 control, provider or office operation. Initial13 RED
cases establish a missing new API, not13 production defects. Added Journal tests
reproduce the absent max_records argument before implementation. Original logs
remain in Agent4 task outputs/collector-inspection-red-20261113-r1 and
collector-inspection-journal-red-20261113-r2. First15 GREEN in green-20261113-r3;
combined56 GREEN in full-green-20261113-r4 (unittest5.554s).
Final expanded60 GREEN in final-green-20261113-r5 (unittest6.018s):20 inspection/
bound cases plus17 context/15 raw/8 default Journal regressions. Includes absent
checkpoint, clean resume after inspection, extras denied before connection and
cumulative small-profile overflow with retained bytes unchanged.

The combined cohort uses new inspector/bound tests, frozen PR96 context17/raw15
test sources and the unchanged baseline Journal8 suite against this successor's
modules. Actual SQLite trace checks129/17 and mode=ro; negative controls prohibit
writer construction/UUID/kernel/write methods and writable os.open flags. It
checks unchanged bytes/names/identities, dirty/terminal states, corruption,
retained partials, source races, binding/profile mismatch and overflow. Existing
Journal8 tests clean only their own disposable temporary files; retained new
context/raw/inspection scratch and original logs are not cleaned.

Exact regression test-source SHA256: context17
148e4321b762e3c5cc25a5ddee05fe7abac0da0664c313b7fee47fd4dd46c84f;
raw15 16d79ff4aca7de50f9379f115f7a12dfe4c6dc3f0c65ec4750e3c54d72381f21;
Journal8 2c0d0df21803f7450d82c60aca64f898c599070e1ac8459d8e800c3fa5a3d2d2.
Direct Python3.12 executable SHA256
4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a,
flags -I -S -B, stdlib only; explicit retained scratch and an own30s child deadline.
EXECUTION.json retains the final child PID/exit/retirement/wall observation.
This is a bounded test observation, not native process/runtime-family qualification.

Independent static review, Root/A8 source forecast and new exact-source/runtime
qualification are separate from these local tests. No push/deployment/admission
or prior PASS transfer is authorized by this document.
