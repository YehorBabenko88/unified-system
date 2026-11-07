# Isolated native pipe peer observation

Status: isolated implementation candidate, NOT production admission. Exact base
8bfa00d779438dc204b1e9ee82f496efce9e6154, tree
58753c6c902afa9fe24e65480a197ae9470defc7. Only the module, its focused tests
and this document are allocated to Agent 1. ROOT owns composition and admission.

## ABI and trusted composition

`capture_owned_pipe_peer(pipe_read, expected_process, *, deadline_ns, cancel=None)`
accepts exact OwnedPipeReadLease and OwnedProcessInstance resources and returns
an opaque NativePeerCapture. `check_current()` returns a PeerObservation only
while process incarnation and pipe/read bindings remain current. `close()` is
idempotent. Resources/capture cannot be pickled; public constructors deny.
Observation contains PID, process creation FILETIME, session, Identification
level, SID and authentication LUID. SID/LUID are omitted from repr. No value is
an identity issuer, authentication decision, RBAC/human assertion or grant.
`capture_runtime_peer` always denies ROOT_PRODUCTION_HOST_ADMISSION_REQUIRED.
The proposed ABI is not a shared-owner ACK.

Private trusted adoption consumes an already retained launch process handle
(never OpenProcess by PID) and the server pipe after an actual bounded completed
ReadFile. ROOT's rawfront owns the exclusive last-read lock and monotonically
managed read generation. Those facts are trusted composition prerequisites;
Python private methods/classes/locks are not an authentication boundary. A lease
is single-capture and borrows the pipe until close; ROOT retains pipe ownership.
The native server PID must equal the capture host PID. A parent-owned pipe may
not be forwarded into this helper. A second capture cannot reuse the read.

## Isolated host and native checks

Only an explicitly registered own multiprocessing child named
UnifiedNativePeerCaptureHost may execute the native path. This fixture bootstrap
is not a sterile production-host proof. The same dedicated helper owns pipe and
capture. Existing controller/office processes must never run this path. Host
admission, protected launch, thread policy and composition remain ROOT blockers.

Capture compares the retained live process handle/PID/creation timestamp with
kernel pipe client PID/session, then observes the effective token of the last
read using ImpersonateNamedPipeClient. Only Identification is supported; primary
and effective SID, authentication LUID and session must match exactly. Anonymous,
stronger/delegated profiles, unrelated launched processes and exited processes
deny. Process/pipe facts are rechecked before return. check_current is resource
binding freshness, not logoff or authorization revocation detection.

RevertToSelf is in finally entered before impersonation. Failure or residual or
unconfirmed thread token terminates ONLY this owned disposable host. There is
no caller logging, await, callback, external I/O or successful return while
impersonating; SID/LUID text conversion follows verified revert. Python implicit
allocation, GC and audit hooks are not proven absent. This is another reason
production host admission stays unavailable.

## Bounds and cleanup

At most 16 active captures and 16 adopted process resources per module process;
these are local bounds, not cluster authority. Each capture uses a preallocated
64KiB token query buffer, fixed SID/statistics storage and bounded queries without
retry. Peak three new query/duplicate handles per capture excludes ROOT's
already-owned pipe/process handles. Deadlines and cancellation are cooperative
checks around synchronous native calls, not hard kernel preemption. Cleanup
closes owned duplicates/token handles and releases borrowed read leases; an
uncertain failed handle close does not recycle its capacity. Existing caller
resources remain caller-owned. No privilege adjustment or PID-reuse fallback.

## Focused evidence

Nineteen tests: four fail-closed boundary tests and fifteen own Windows helper
cases, including direct Identification, wrong launched process, Anonymous,
stronger level, process exit before/after capture, closed resources, cancellation,
deadline, preexisting token preservation, read-lock contention and single-use.
Native observations record actual elevation/privilege attributes and handle
counts, not inferred nonadmin, Home/Pro or service qualification. The isolated
pipe has a random name, first-instance/remote-reject flags and a DACL only on
that newly owned fixture object. No existing ACL or system policy is changed.

Slot saturation is injected semaphore occupation, not sixteen live captures.
Revert failure is an injected actual failing native call in the disposable
helper; its termination and owned-client exit are observed. This does not claim
an actual OS RevertToSelf failure was induced. Non-Windows native tests explicitly
skip and cannot establish native PASS. Windows x64 is the supported ABI.

The module has no TLS/certificate parser. Certificate chain, SAN URI, EKU and
fingerprint binding require separate isolated TLS fixtures and exact owner API
agreement. These nineteen pipe tests provide no certificate, shared API, issuer,
production service, real gateway, Bybit, physical LAN or physical acceptance.
No system certificate store, ACL policy, ESET, firewall, Tailscale, route or
physical network change is authorized. All other P0 gates remain blocked.
