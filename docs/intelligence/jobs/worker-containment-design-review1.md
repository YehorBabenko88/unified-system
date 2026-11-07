# Owned Windows child containment — allocated isolated slice review1

ROOT allocated feature/gateway-worker-containment-20261107 from exact
3e498de973536c2d6393f83abe7d59cb1452a9b4/treeea13a052992acff8268e7e79b99c7a603bcb1fa3.
NEW gateway_worker.py, owned tests/gateway_jobs/** and docs only. No Grid edits.
No native grant, authority issuer, publication, quota release or physical service.

Reuse primary Grid40e9 grid/ml_windows_job.py Gitblobf30a09a3af647518d69f7787879defc4d5fa8ab5,
rawSHA7fd6223de3e28052b1254fa9e33e638132c6db89388bbb2d994b35970802a25c.
Its WindowsJob(pid,resume_primary_thread=False), terminate_and_wait(timeout) and
close are existing methods. Retained _job HANDLE/_kernel and _BasicAccounting
are PRIVATE source-pinned ABI, not generic provider API. The proposed owned
wrapper explicitly binds this exact implementation/type/source and never accepts
an arbitrary caller handle or substitutes a public native authority capability.
Any source/ABI mismatch denies before resume. No optional psutil path is used.

CreateProcessW suspended with actual retained process AND primary-thread handles,
explicit absolute executable/fixed source-owned entry, minimal environment and
no inherited application credentials/handles. Attach to new pinned WindowsJob,
apply own narrow SetInformationJobObject limits to that SAME retained owned handle,
query/readback exact limits, then ResumeThread. Any failure before resume terminates
owned suspended child, proves it exited, closes handles. After attachment require
existing terminate_and_wait actual ActiveProcesses0 before cleanup. Never PID-only
kill/adoption, no suspend/resume of office or service process.

Proposed limit trial: whole Job committed-memory256MiB, active processes8,
CPU hard-rate1000 (fixed10% native Job rate), NOT one logical CPU.
GetProcessAffinityMask and single-group check observed16 processors; inherited
Job/container effective capacity remains unknown, so no millicore mapping. These are
qualification test settings, NOT approved safe research capacity or scheduler
benchmark. Job committed memory is NOT resident working set; CPU rate hard ceiling
is NOT reserved CPU service guarantee. Actual resource profile requires measured
RSS/CPU/pressure/headroom and bounded IPC/output/deadline qualification separately.
Output process handles must be bounded by owner IPC; stdout file read-at-end is
not an output quota. Do not claim final worker admission from kill/memory tests.

Cancellation separates cooperative discard from native Job termination/quiescence.
Unknown quiescence poisons/restricts retry, no hold refund. Actual dispatch entry
stays denied until A2 one-use ResearchDispatchPermit and exact same authority plus
owned_attempt ABI are qualified. Replayed RUNNING never launches a second child.
Consul dispatch commit and OS resume are not atomic; final durable effects require
current A2 grant+CAS. Historical projection/read never restarts worker.

First native probe used no real research/grants: explicit synthetic parent spawns
a sleeping descendant. Initial exact2-process assertion failed because actual
Job accounted4 processes. Cleanup initially lacked waiting for retained parent
handle and obscured cause; fixed failure cleanup waits that owned handle. Corrected
probe requires observed descendants >=2 and records actual4, then Job empty and
parent signaled. This is actual kill/quiescence only, not memory/CPU/admission PASS.
Next probe applies/readbacks memory/CPU/active limits BEFORE resume, captures native
accounting/peak committed usage and exercises quota failures/timeout only against
own disposable processes. No positive authority fixture is created.

Independent review fixed cleanup: unconditional retained-handle close even after
Job termination/query failure, explicit checked process termination/wait; unknown
quiescence raises OWNED_CLEANUP_UNPROVEN_NO_RELEASE. Fault-injection tests are
assertion-quality checks, NOT real OS failure qualification. Real memory probe
reported allocation512MiB refused but native peak committed counter544940032;
limit readback was268435456. Do not infer safe peak/headroom from that counter or
claim cause of MemoryError conclusively. This probe remains unqualified for RSS,
CPU share, pressure, bounded output and admission. Worker start stays denied.
