# LS5 isolated smoke source preparation

Status: SOURCE_PREPARATION / EXECUTION_NOT_ADMITTED. This is not an installer,
native worker issuer, resource qualification, distributed E2E or release gate.
Root owns the serial LS5 lane. No Job construction, target or browser execution
has occurred for this source. Package assembly and exact-package A8 review remain
pending; `--execute` is a test mode, never authorization.

## Scope and ownership

Root owns `tools/physical_dev/{supervisor,bootstrap,ls5_smoke}.py` and their three
contract test files. Package integrity library/test/plan originated byte-exact
from Agent package PR70, commit73bb603c1ec4dd02b2f5cca06377ed677199e54e;
the subsequent Root correction is recorded below.
No shared runtime adapter or target algorithm is changed. Fixed source selection
maps the existing adapter's Git source reads to the admitted exact Git executable.
A6 owns Terminan PR77 commit161ea1e0fc3a3a4cd64783b0e111e1e119e14d71.
Its fresh renderer, not a stored fixture, is the intended second stage.

The intended source family is Unified runtime ba2b1cec0c2b114586afb73696e282117eede987,
Strattester aed8a7c8a952f96803c207d5e90b133969a47f04, MetaAnalyse
f3c01a23fa5baaeeeb28eb8e9397e72b5ef4d5a1 and A6 PR77. The harness itself must also
be committed, independently reviewed and included by exact commit/tree/raw bytes.
Descriptive manifest metadata is not source proof. The old pinned primary-object
verifier is executed with BOTH its command and batch readers bound to fixed Git.

## Proposed process bounds

Ordinary, non-elevated direct Python/Node bootstraps wait for a bounded own pipe
GO. The parent retains the original Popen HANDLE, checks PID/creation FILETIME,
image path and nonadmin token, assigns the SAME process to a NEW anonymous own
Job, then checks membership and exact limits before GO. No suspended process,
ResumeThread, CPU-rate setting, PID reopen, existing Job mutation or breakaway.

New empty Job flags0x230c: active16, process COMMIT512MiB, job COMMIT1GiB,
aggregate USER CPU10s, termination end-action0, kill-on-close. A supervisor thread
outside the target family requests own-Job termination after monotonic work20s;
cleanup is separately bounded. The Job handle is not closed while the watchdog
native call is unjoined. This is NOT a hard real-time watchdog, RSS limit,
CPU-rate limit, resource reservation, loaded-DLL attestation or worker permit.
An unknown ancestor Job can be stricter. Parent/OS freeze is not solved here.

Source/package provenance preparation precedes the target-family timer and does
not start an application target; it can take longer than the proposed30s family
window. A5 correctly identified that the old batch reader's wait(timeout15)
occurred AFTER blocking reads. A subsequent timer-only version still blocked the
controller when both retirement and a pipe read failed. That actual failure path
was reproduced with an inert blocked reader and failing terminate/wait; original
RED is `ls5-blocked-reader-cleanup-red.log`. The prepared successor performs pipe
read/write/flush/wait operations in retained daemon workers, with the controller
waiting on bounded result queues (exchange15s). Terminate/wait5 is itself run in
a separately bounded6s own-handle worker. Pipe close is independently bounded2s.
Unretired workers retain their original stream/Popen closure; failure remains
UNKNOWN and prevents target admission, rather than claiming thread cancellation
or confirmed cleanup. The controller can record failure even when retirement
fails. A monotonic300s source
preparation deadline is checked before each command/exchange; no new operation
starts after it. Context cleanup attempts every retained batch even on failure.
Global/system Git configuration and lazy fetch are disabled only in the child
environment; fixed built-in read commands do not request providers or hooks.
This is cooperative bounded preparation plus cleanup, not hard real-time or
survival of a frozen supervisor/OS. Fresh exact-source review remains required.

Only retained own Job/Popen handles may be terminated. SDK cleanup denial or
unconfirmed exit remains failure even if Root later tears down its own Job.
Only protected package hashes and explicit fresh outputs are observed: no
unobserved whole-disk no-write claim or defense against hostile same-user/admin.
No existing service, database, ACL, policy, network setting or office peer changes.

## Review findings and regressions

A5 source-only review report SHA256
cbd39bf6b1c89b8bb7a2187eb7afbacc3ec6e6d78d8d670614658b4159d1bb6c
identified late capture acceptance, exception-skipped cleanup and basename-only
Git admission. Root also found the old verifier's unbound batch reader.

Prepared fixes: validate captures before GO and after pipe retirement; aggregate
output16KiB and final work deadline; isolate each retained-process cleanup error;
pin both provenance Git readers and the target's read-only source Git child;
add an outside-target watchdog with join-before-close lifetime. These have
deterministic no-child unit coverage, not physical enforcement proof.

Retained original RED logs under the private evidence root:
`ls5-primary-git-capture-red.log`, `ls5-cleanup-red.log`,
`ls5-watchdog-red.log`, `ls5-bootstrap-git-red.log`.
Working source suite:45 unique tests, zero skips. Original package24 tests are
included in that count; they are not45 new runtime tests. Exact committed source
qualification and independent review are still required.

A8 also identified native Git lazy-fetch risk: Python socket audit does not
contain Git's native helpers. Both provenance and backend source-Git environments
now deny lazy fetch/all transport protocols and global/system config, and disable
prompts. Every source repository must be an independent local `.git` directory;
partial/promisor markers/config, alternate object stores, common-dir/worktree
config, grafts and include config deny before Git launch. Inert-file regression
RED `ls5-git-offline-red.log` is retained. No remote/fetch test was executed and
no historical network activity is attributed from this static finding.

The assembly preparer reproduced Windows pathname/descriptor mode differences
on inert `.exe` bytes: lstat33279 versus fstat33206. Package73 incorrectly compared
the full mode across APIs. Root preserved `ls5-exe-mode-red.log`, added an inert
executable-extension regression, and compares file type plus device/inode/link
count/size/mtime across APIs. Full mode/ctime stability is still required within
each API; hardlink/reparse checks are unchanged. No executable fixture was run.
The source review also found own-Job handle state was discarded before a failed
CloseHandle; the correction preserves custody/state until successful close,
covered by `ls5-job-close-red.log` and a nonnative regression.

## Remaining admission gates

- Exact GitHub source, clean primary checkout, complete pure suite/raw pre/post.
- Independent A5/A8 successor source review, including cleanup/watchdog closure.
- Full private copied toolchain/dependency/browser file inventory, pinned source
  and external immutable manifest SHA; aliases/hardlinks/extra/mutated files deny.
- Fresh canonical ACL/resource/token read-only confirmation; no ACL repair.
- Exact-package A8 isolation admission. Current phase137 was docs-only NO-GO.
- One serial LS5 smoke only after these gates; preserve every original RED.

Public submit DENY; publication LOCAL_UNATTESTED; provider sends BLOCKED;
physical cluster, native worker, production and main merge NOT_AUTHORIZED.
MASTER MISSION remains IN_PROGRESS / NO-GO.
