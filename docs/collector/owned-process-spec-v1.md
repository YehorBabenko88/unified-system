# Owned process layout ABI v1

`unified_system.service_postgres.OwnedProcessSpec(data_root, code_root,
job_sha256)` is an immutable, exact typed layout for reuse of the existing
`OwnedJobProcess`. It is not a PostgreSQL plan, authorization record or launcher.
The legacy plan mapping path and PostgreSQL ownership journal remain separate.

All three fields must be exact strings. Roots must be existing absolute ordinary
local directories, disjoint from one another, with no links/reparse traversal.
The hash must be 64 lowercase hexadecimal characters. Layout validation occurs
both at construction and consumption before temporary capture files or process
allocation. Subclasses are rejected. The only permitted job helper is the existing
`code_root/sources/grid/grid/ml_windows_job.py`; the existing regular-file/hash
source loader and required synchronous `terminate_and_wait` capability apply.

For this neutral layout `restricted` must be exactly `False` and `launch` must be
`None`. It cannot enter PostgreSQL's restricted-process or journal branch. The
same `OwnedJobProcess` implementation creates a suspended child, verifies owned
identity, assigns the existing Grid Job, resumes, and uses synchronous Job
quiescence for retirement and existing poison/error behavior. There is no second
Popen implementation, Job kernel, PID adoption, token, ACL or SCM operation here.

A genuine Collector bootstrap owner must first admit the complete immutable
runtime and source, exact argv and explicit environment, bounded writable state,
LocalService/Session0 context, and the separately approved operational scope.
This layout performs none of that admission and never grants runtime authority.
The owner must retain failure evidence when quiescence cannot be proved.

Qualification uses actual specification validation and the existing constructor
with inert injected Popen, identity, Grid Job, resume and drive-type boundaries.
No native process, Job, WinAPI, service, token or ACL is exercised. Existing
PostgreSQL regressions must still pass with the same inert drive-type boundary.
