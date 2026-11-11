# VirtualAlloc diagnosis — SOURCE ONLY, ROOT execution ACK pending

Branch feature/gateway-worker-virtualalloc-diagnostic-20261107, base exact
480109277c1e80a666f3dbba84b5807cacd2b460/tree651fff9bb987fead6414b4492acc0891873cac27.
PR51 remains stable. Owned additions tests/gateway_jobs/** and docs only.
Nothing in this packet authorizes execution. No production thresholds change.

Fixed workload: TWO sequential fresh disposable children, never concurrent,
one allocation attempt per child, NO retries. Control8388608bytes (8MiB);
overlimit335544320bytes (320MiB), hard upper bound320MiB. Same verified Job
committed cap268435456/active8/native CPU rate1000 before ResumeThread. No memory
pages are touched deliberately; reserving+committing STILL consumes host commit
budget. No actual job/admission/grant, service/network/database/security changes.

Conservative prerequisite before each child and again before resume: real
GetPerformanceInfo AvailableCommit >= 8*320MiB+256MiB =2952790016bytes and
GlobalMemoryStatusEx available physical >=1073741824bytes. Missing/invalid/changed
or below-threshold data refuses, no relaxed fallback. These are refusal margins
for this diagnostic, not capacity/admission limits or measured safe resource policy.
Actual inherited Job/container availability remains unknown and non-admitting.

CreateProcessW suspended with retained process+primary-thread handles; inherited
handles restricted by STARTUPINFOEX handle-list to stdin-read/stdout-write only.
Minimal environment, absolute current interpreter, exact source-hash check and
fixed script entry. Actual pinned GridWindowsJob source/ABI reused; Job membership,
Set/Query flags+limits verified before resume. Parent uses Job process-ID inventory
and actual IsProcessInJob checks to bind reported child PID (CPython launcher can
add processes), retains that verified child process handle; no arbitrary PID use.

Bounded IPC: 4 request/response phases BEFORE/ALLOCATED/FREED/EXITING, max4096bytes
per frame, max16384bytes total from child, one outstanding <=16byte parent command.
Parent PeekNamedPipe+bounded reads, no unbounded communicate/file capture. Child
serializes <=4096bytes BEFORE each write. Absolute parent monotonic10s deadline,
separate parent watchdog calls TerminateJobObject on SAME owned retained Job when
deadline elapses; watchdog never closes Job handle. Cleanup signals/joins watchdog
before handle closure. Deadline/error/partial frame => terminate own Job, prove
ActiveProcesses0 and retained parent process signaled, close every handle. Unknown
quiescence raises/retains NO_RELEASE classification; no retry/quota refund.

Child synchronization: report own before privatecommit; wait ALLOC; call exactly
one VirtualAlloc(NULL,fixedsize,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE); immediately
capture returned pointer and native error. Error is causal only for NULL return;
success-side last error is explicitly undefined/informational. Report DURING while
allocation still held; parent captures same retained Job Extended+Basic and child
privatecommit under phase handshake. Wait FREE; VirtualFree only exact valid pointer
returned by THIS allocation; MEM_RELEASE size0; no arbitrary/client pointers or
retry. Record actual return/error then set pointer retired only after success.
Report AFTER and await EXIT. Any unfinished owned allocation is freed once in child
finally; failed free is not retried and process teardown releases owned resources.

Privatecommit uses documented PROCESS_MEMORY_COUNTERS_EX PrivateUsage, distinct
from WorkingSetSize and Job peak fields. Parent captures child handle creationtime,
Job PID inventory/membership, raw limits/struct sizes/offsets/accounting at each
phase and observation UTC/monotonic timestamps. No host clock becomes commit time.
GetPerformanceInfo/GlobalMemoryStatusEx snapshots, native results/errors/exit codes
are retained. No unsupported attempt-vs-charge explanation is presumed.

Expected interpretation, NOT predeclared PASS: control ordinarily allocates/free;
overlimit may refuse. Unexpected success/failure/peak/current mismatch remains
raw evidence and qualification FAILURE/UNKNOWN, not threshold correction. Current
PR51 original bytearray request512MiB/peak544940032 vs256MiB remains immutable;
new320MiB VirtualAlloc case is a separate allocator experiment, never replacement.
No memory/RSS/CPU-share/headroom/admission qualification follows automatically.

Review before execution must verify full source+resource bounds, ABI declarations,
all failure cleanup branches and pipe/watchdog ownership. Source syntax review
alone is not executed test PASS. ROOT bounded source review/explicit execution ACK
is required before ANY child/VirtualAlloc diagnostic run.

Source-review clarification: the10second monotonic deadline governs each ACTIVE
case after the initial host prerequisite query; source loading, initial prerequisite
queries and cleanup are outside it. Git source read has its own10second timeout;
watchdog join <=1s and Job termination <=5s plus retained-process wait <=5s are
explicit cleanup budgets. These do NOT guarantee a hard total invocation bound
if a native OS API stalls. ROOT must budget and supervise the whole invocation
separately; no repeated run on timeout. If parent is externally terminated, Job
kill-on-close is containment intent, NOT observed quiescence/NO_RELEASE proof.
If8MiB control allocation/free fails, refuse overlimit case (exit2 with retained
control observation) rather than continue. Parent report capped131072bytes before
write. Neither complete diagnostic exit0 nor raw per-case results mean memory
capacity/enforcement qualification. Last-error for BOTH alloc/free is interpreted
only on native failure, explicitly undefined on success.

Independent reviewer read source/hash only, found no material source-level defect;
no module import, harness execution or allocation occurred. Post-review edits
clarified error semantics and conservative control refusal, not additional workload.
ROOT exact source execution ACK remains required.
