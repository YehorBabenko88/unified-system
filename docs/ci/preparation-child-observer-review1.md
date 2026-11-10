# F42 preparation child observer — SOURCE ONLY review1

Status: HELPER SOURCE_IMPLEMENTED_NOT_RUN. Root accepted the628 missing-helper prerequisite (one failed module import, zero12-case execution) and allocated helper SOURCE ONLY. No helper import/compile or12-control execution has run. Qualifier hooks remain HELD.

Base: Unified bfa3b24d8f209d5e91acfa64819d3ebed4967af7. Branch: feature/agent5-f42-observer-source-20261110.
Initial ownership ONLY:
- NEW tests/test_preparation_child_observer.py (12 proposed stdlib/inert controls).
- NEW docs/ci/preparation-child-observer-review1.md (this card).
NEW tests/preparation_child_observer.py is now allocated only for reviewed API implementation source. Existing tools/ci/qualify_preparation_integrity.py remains HELD until actual-helper12 controls are separately allocated/reviewed/qualified. No push, existing test/child command/environment/20s timeout change, native/provider/office/PowerShell fixture, or real crash-child run. A managed worktree request did not return a path; an isolated Git worktree was created from the exact base instead.

## Original observation and purpose

Preserve run42897137339/job130113108432/artifact13801431495, ZIP SHA13ab352ac9882d5b3ae6559b9ad9baab9e1dd6b3ab50c57b670b5bccb082d1ba. Original36 cases:35OK/1ERROR/0skip,24.144s. F42 cause remains UNKNOWN. CPython3.12.10 subprocess.py1630 reports stdout reader-thread join timeout, not proof the child was alive, SQLite blocked, or os._exit23 was reached.

Proposed diagnostic distinguishes observed retained-child poll state from stdout/stderr reader state immediately after the ORIGINAL communicate raises TimeoutExpired, BEFORE subprocess.run executes its standard kill/cleanup. No observation changes red to green or confers process/authority/worker/cleanup proof. This is not an all-green qualification harness.

## Actual-helper source API (not imported or executed)

Source file tests/preparation_child_observer.py exports PreparationChildObserver, with no dependency on project runtime modules. This is source implementation only, not an executed API qualification.

- PreparationChildObserver(): purely in-memory fixed limits; no injected clock/provider/backend, files, threads, imports of project code or process construction.
- begin_constructor(*, at_ns: int) -> int | None: reserve the sole local observation token and append CONSTRUCTOR_BEGIN. None means diagnostic capacity exhausted; never blocks or authorizes process creation.
- end_constructor(token, child, *, at_ns: int) -> None: retain the ORIGINAL child object/reference and bounded integer pid DATA, append CONSTRUCTOR_END/elapsed_ns. No poll/thread/pipe/cleanup method is called here.
- constructor_failed(token, *, at_ns: int) -> None: append CONSTRUCTOR_ERROR/elapsed_ns; no exception message/args, child or cleanup.
- begin_communicate(token, *, at_ns: int) -> None: append COMMUNICATE_BEGIN and remember this call's start.
- communicate_timeout(token, *, at_ns: int) -> None: append COMMUNICATE_TIMEOUT/elapsed_ns and the sequential observation below, ONLY if an event slot remains.
- end_communicate(token, *, at_ns: int) -> None: append COMMUNICATE_END/elapsed_ns without invoking poll or any child operation.
- export_json() -> bytes: serialize a detached canonical sorted compact ASCII envelope AFTER suite/error paths. No file/socket/pipe output. Hard size check, never truncate or discard an earlier event to fit.

Token is a local registry index, not PID authority/job/incarnation identity. Driver keeps its existing actual Popen subclass/type/retained handles; it maps its own object to the token. Inert controls invoke the eventual ACTUAL helper with deliberately unissued objects, not a copy of observer logic. They demonstrate API effects only, not native process behavior.

No public runtime/shared ABI or existing policy is changed. Helper timestamps are supplied by future fixed driver calls to its existing perf_counter_ns; they are diagnostic counter samples only, not trusted UTC, commit time or proof of a strict deadline.

## Fixed budgets and types

- MAX_CHILDREN=1: the exact selected original crash case creates one direct Python child. Further construction is declined for OBSERVATION only; existing owner custody/cleanup must still track every real process and diagnostic incomplete stays visible.
- MAX_EVENTS=8: constructor begin/end plus original and standard-cleanup communicate begin/end fit in six events, with two event slots spare. No retry or extra communicate is introduced.
- HASH_PREFIX_BYTES=256: SHA256 over at most256 bytes PER pipe buffer snapshot. At most512 bytes hashed per timeout event. Do not hash whole output or label prefix_sha256 as full-buffer digest.
- MAX_EXPORT_BYTES=16384: fixed-key/count/enum/numeric/hash envelope hard cap, independent of source stdout volume. Cap failure is diagnostic failure, never partial output/native success.
- dropped_events saturates at2147483647, so repeated overflow cannot grow arbitrary counter memory. Event overflow sets incomplete=true. No overwrite/eviction of old events and no child observation after the event cap.
- at_ns must be exact int (not bool),0<=value<2**63 and >= current phase start. Invalid time/unknown non-None token raises ValueError before event/history/child effects. end_constructor(None, ...) ignores that child and marks diagnostic incomplete; this is not permission to abandon owner process cleanup.
- One event is at most fixed metadata with bounded integer pid/time/returncode, enums and two64hex prefix hashes. No argv/code/env/path, raw stdout/stderr, exception text, repr/object formatting, TLS/credentials, native grant or authority fields.
- These are conservative diagnostic-memory limits derived from ONE frozen command/call pattern, not measured resource/admission budgets or a wall-time bound on poll/OS scheduling.

Event records carry kind,token,at_ns and where applicable elapsed_ns/pid. All timings describe sequential entry/end samples. They do not assert an exact kernel creation/exit/timeout instant.

## Timeout snapshot and allowed effects

Order is fixed: ONE child.poll(), then stdout_thread.is_alive(), then stderr_thread.is_alive() for attributes that exist; inspect CPython _stdout_buff/_stderr_buff afterward. Do not query stdout/stderr/stdin pipe properties at all. Returncode from poll is exact signed-u63 int (not bool) or None. None => RUNNING at that query; integer => EXITED/that code; errors => ERROR/None and incomplete. Bool/other types => UNSUPPORTED/None and incomplete.

Thread states: ABSENT/ALIVE/STOPPED/ERROR/UNSUPPORTED. Call only is_alive once for each present thread; no join, wait, lock, pause or thread creation. Errors are normalized without exception text. Observer operates on the suite thread, not the cancellation thread, and adds no global lock across an existing wait.

Buffer observation supports ONLY exact list of zero or one exact bytes item, matching this pinned CPython binary-mode reader implementation. Never invoke arbitrary len/bytes/iteration conversion on another object:
- absent => state ABSENT;
- [] => EMPTY/chunks0/bytes0/prefix_bytes0/prefix_sha256 null;
- [bytes] => PRESENT/chunks1/bytes=len(bytes)/prefix_bytes=min(256,len)/prefix_sha256 of that prefix;
- other type, multiple chunks, nonbytes item => UNSUPPORTED, no attempted coercion/hash and incomplete.
Non-PRESENT byte/prefix facts are null unless EMPTY as above. No reference to raw buffer bytes is serialized; the existing child already owns its buffers. Length/hash/thread state can be observed at different instants. Child poll may be23 while reader state ALIVE: record BOTH without a root-cause verdict.

Permitted future effects are in-memory bookkeeping, bounded builtin metadata reads/hash, and the ONE retained-object poll/native nonblocking query plus thread.is_alive calls. They are sequential, not atomic, hard real-time, whole-host instrumentation, EOF proof or native authority evidence.

Exact poll effect: real Popen.poll may cache an observed exit in that object's returncode. This is an intentional observation-side mutation of the EXISTING retained object, not termination/reaping ownership transfer or child exit proof at an earlier instant. Even poll()==23 must not suppress or replace the original TimeoutExpired. Standard subprocess.run remains responsible for its original cleanup decisions; do not claim instrumentation is timing/behavior-invisible.

Forbidden: pipe read/readline/readinto/write/flush/close/fileno, extra communicate, kill/terminate/wait, joins/locks held across waits, second process, command/env/isolation/timeout changes, retries, host clocks/security changes, SQL connections or reading DB files, imports of project/fixture/helper execution under THIS source lease. Instrumentation does not determine SQLite phase or prove startup cause.

## Future qualifier hook sketch — NOT edited/authorized

1. Keep original child argv/code/cwd/env/capture_output/timeout20, OwnedPopen registration and subprocess.run behavior.
2. Record constructor start/end/failure around existing super().__init__, without any new wait or observer method under a registry lock.
3. In a future scoped communicate override, record begin; call super().communicate with UNCHANGED args once for THAT caller entry. On its TimeoutExpired, record timeout BEFORE re-raising the SAME original exception to subprocess.run. Preserve its traceback/class/standard cleanup. Observer exceptions may only mark bounded diagnostic incomplete; they must not replace the original failure.
4. The standard library may itself invoke communicate again after its own kill. Record that caller entry/end without causing one. The observer must never call communicate.
5. Collect memory only on timeout path. Persist export in worker suite/error finally after standard child cleanup/test result handling, BEFORE any exact36 validation can raise. No synchronous file I/O/prints on timeout path.
6. Root owns exact evidence path and outer cancellation/termination lifecycle. Existing os._exit/OS termination can prevent export; missing diagnostics remain UNKNOWN, never fabricated completion. Helper does not own, release or close process handles.
7. Export wrapper envelope is EXACT {schema,events,retained_children,dropped_events,incomplete}, schema preparation.child-observer.v1-review1. It contains no admission/success/cleanup-confirmed field.

Nothing in the initial lease authorizes these qualifier edits, imports or execution. No test runtime/source freeze is implied by this card. Full future file/import/driver effects require Root review.

## Proposed12 pure controls (source only, zero executed)

The only test implementation of behavior is the future actual helper import. Inert children/pipes/threads have forbidden-operation tripwires. No subprocess, real pipe/thread, SQLite, fixture module or runtime object is constructed.
1. Fixed limits; constructor reference/timing retention makes no child calls.
2. Timeout order poll then two thread checks; no pipe/cleanup calls.
3. Exit23 plus live stdout reader retained as facts with no RCA/cleanup conclusion.
4. Prefix hash/length is bounded and not full-buffer SHA/raw payload.
5. Absent/empty thread/buffer states explicit.
6. Unsupported buffers never coerced, hashed or iterated.
7. Poll/thread errors normalized without sensitive text.
8. From exactly three initial events, make exactly five timeout calls, assert exact8, then make one overflow call. No while/poll-until loop: a buggy helper cannot hang this control. Overflow does not sample child again and marks incomplete.
9. A second construction is declined without observing another child.
10. Export detached/bounded and child-effect free.
11. Bad timings/unknown token produce no poll/history mutation.
12. Constructor failure and two caller-entered communicate pairs record without cleanup actions.

The unchanged test source SHA9de3045395a178421cbf3041ad2261f9221f4dfc9b21d83432bd1046d0d410cc was qualified once BEFORE helper creation: ONE failed module import under exact tests-path named loading/-I-S-B, not12 case errors/F42 reproduction. Receipt SHA4aa27092a8a6ceaad7f315364bcbe003a81ded7fa7f451766be5604527eb0cce;1872 full raw pre/post maps identical, process/readers retired. The NEW helper source has NOT been imported, compiled or executed. Original Windows timeout RED remains the only actual crash-child evidence referenced here.

## Required review decision

Root/independent source review: approve/correct actual helper implementation first. Then separately allocate the12 pure controls; no execution follows merely from source review. Only AFTER reviewed qualified actual-helper controls may qualifier hooks be allocated. Any original crash-child diagnostic remains a separate serial-lane approval. Do not push or dispatch GitHub CI from this lease.

Current helper lease effects: ONE NEW helper source and own doc update; original12-test source unchanged. No qualifier edit, helper imports/compile/tests/fixtures/native/provider/office calls or push. F42 source cause UNKNOWN;20s/original child unchanged. StrictD4/logicalDISABLED/publicDENY/NO-GO.
