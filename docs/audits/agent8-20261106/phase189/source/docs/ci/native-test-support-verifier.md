# Native test support: source DATA verifier

`tools/ci/verify_native_test_support.py` supplies only this API:

```python
verify_native_test_support(graph_path: pathlib.Path, *,
    expected_graph_sha256: str, source_roots: dict[str, pathlib.Path]) -> dict
```

This is an ordinary read-only source verifier, not a loader, test runner, permit,
installation tool, runtime authority, or replacement for existing bootstrap pins.
There is no CLI, executable override, network request, version probe, download,
import/compile/exec of fixture bytes, `find_spec`, pytest collection, or global
`sys.path`/environment mutation. Existing workflows, dependencies, and native
fixtures remain unchanged.

## Sealed contract

Implementation allocation follows A2 seal
`7084862b5a81537464f3bfdd873dba5a6bc821fb39d1638e0f7c1f3ee7b158ec`,
source graph
`21b4538247894158777ee2506fabafc5e830da7c641c64bbd108d99fecd8506d`,
ABI `6bde04db9e6f59a94fe6d99cfe8a613a939499e5ee39927e3b3809a49c35bc73`,
and superseding P2 card
`d78035cddecce78d158b5cbf1ab546dd13f09358944ac651cbc0c00734cba21d`.
Raw UTF-8/CRLF descriptor and inventory bytes must match before parsing. Semantic
JSON equivalence does not satisfy a raw hash. Duplicate keys, unknown fields,
unsafe/ambiguous paths, unbound source origins, and absent history fail closed.

Current v1 targets Grid `fb177d14b1e6e399bd9b66ae7cb35d3838acbd81` and Unified
native support `1f6b0b5c231853607f5bec780f1544cd32bf577d`, with two historical
objects from `f155126a95e80139b1b9679c1870ffd66c29360e`. A newer tooling commit
does not become the verified target by inference. The caller provides exactly
the two canonical local source roots. It cannot request fallback to an ambient
private checkout or select a different executable/provider. Managed worktree
administrative pointers may identify an ordinary local common object store;
alternates, replacements, grafts, promisor packs, include-config indirection,
source symlinks/reparse points, unsafe hardlinks, UNC/device paths, and extra
source/cache files are rejected. Missing historical objects are never fetched.
An unresolved linked-worktree `commondir` path and its lexical ancestors are
checked before canonical resolution, so resolution cannot erase an ancestor
symlink/reparse alias. Ordinary existing `../..` administration remains valid.

The full primary inventories, commit identities, reconstructed Git tree
identities, blob identities, modes, declared sizes and SHA256 hashes are checked.
Actual working bytes and HEAD are checked again before returning DATA. File
descriptors retain identity/size/mtime checks during bounded reads. The result is
a point-in-time observation; it is not protection against arbitrary in-process
mutation or future changes to an already observed filesystem.

## Bounded Git transport

**Windows execution is blocked before any Git spawn** with the closed code
`GIT_VERIFICATION_FAILED`; the documented restriction is
`WINDOWS_GIT_FAMILY_CONTAINMENT_UNQUALIFIED`. The installed shim's file/link
identity does not prove its spawned Git family's custody. No bin substitution,
Windows Job/native API, private copy, ACL/link change, or installed-tool change
is implemented. The previous e654 source and its real graph rejection before
any Git child remain separate original evidence, not a new attempt or PASS.

Only Linux can reach the source-only POSIX transport, using the existing fixed
`/usr/bin/git`. Missing APIs or an unqualified context reject before spawning.
The caller must be a fresh CPython `-I -S -B` process, on its main thread, with
no pre-existing Python worker threads, default SIGCHLD handling, and cooperative
exclusive ownership of child reaping. It must not install competing native
reapers or change process/signal state concurrently. The verifier does not
change a global signal handler or environment to manufacture these conditions.
`waitid` with WNOWAIT/WEXITED/WNOHANG and session/group APIs must exist. Other
POSIX systems are not qualified. There is no PATH/private-copy fallback or tool
installation. A missing/unsafe executable or object store rejects.

The Linux model launches with `start_new_session=True` and checks that its still
waitable child has PID=PGID=SID. It observes exit through non-reaping `waitid`,
never `Popen.poll`, retaining the zombie leader and its numeric identity. On
success, timeout, or quota failure, it signals only that owned group with SIGKILL
before bounded leader-exit observation and pipe/thread retirement. Only then is
the leader reaped. It never signals by PGID after reaping. Ownership or cleanup
uncertainty produces no matching DATA result and never licenses a signal to an
unproved group. This is not containment against malicious descendants that
escape their process session/group. Actual Linux kernel/process-family behavior
has **not** been qualified by the pure model tests; Root/A2/A8 post-review and a
separate explicit allocation are required before any real transport exercise.

The child environment is built from
fixed values, not inherited `GIT_*`, PATH, credentials, proxy, or module paths.
System/global configuration, replacement objects, helpers, hooks, lazy fetching,
and network protocols are suppressed; repository include/object redirection is
rejected before spawning. Whitelisted builtins are only HEAD/tree `rev-parse`,
bounded recursive `ls-tree`, and exact-OID `cat-file --batch`.

The whole monotonic deadline starts at API entry and includes validation. Git
children have at most 30 seconds or the remaining whole budget, whichever is
less; one second is reserved within those limits for cleanup. The whole budget
is 90 seconds. Checks surround local metadata and bounded file reads as well as
Git processing; local synchronous filesystem operations depend on the OS returning
and are not a hard real-time kernel-I/O guarantee.

Aggregate stdout is capped at 72 MiB and stderr at 1 MiB across all calls,
including historical reads. Declared primary payload is capped at 64 MiB, counted
once per declared primary file, and each blob at 20 MiB. Descriptor and each
inventory JSON are capped at 2 MiB; at most 4096 files per role, 16 historical
objects, 128 module origins, and 16 reference locks are accepted. Paths have
bounded lengths; object-store metadata traversal is capped at 100000 entries.
Limits are checked before retained-byte allocation. Pipe readers use fixed
64 KiB buffers and an eight-item queue. Neither `communicate` nor an unbounded
pipe read is used. Stderr bytes are counted and discarded, never printed.

An input writer and pipe reader threads are watched by the calling thread.
The Linux retirement path acts on the new owned process group while the leader
remains unreaped, closes owned pipes, and joins owned threads within the remaining
budget. Failed cleanup cannot produce a matching DATA result. An uncertain
ownership failure is a rejection, not a claim of successful family retirement.
No source mutation, arbitrary shell, fixture program, or unrelated process/group
termination is permitted.

## Result and errors

The closed result keys are `schema`, `graph_sha256`, `status`, `sources`,
`historical_objects`, `module_origins`, `artifact_closure`, `unresolved_codes`,
`fixture_import_allowed`, and `native_execution_allowed`. Source records contain
only role/head/tree/raw_files/inventory_sha256/raw_match; historical records
role/head/path/blob/sha256/raw_match; module records module/role/path/sha256/raw_match.
No root path, raw source, environment, token, or child stderr is returned.

Current v1 success is **SOURCE_MATCH_DATA_ONLY**. `unresolved_codes=[]` describes
the absence of structural mismatches, while artifact closure remains
`INCOMPLETE_SOURCE_DATA_ONLY`. Both import/execution flags are always **false**.
`MATCH_COMPLETE_DATA_ONLY` is not implemented or accepted. Reference dependency
locks and Consul leaf hashes are not complete archive/publisher/install closure,
and do not grant fixture eligibility. Legacy Unified `e0c2...` groups remain
separate; this verifier does not globally adopt `1f6...` or certify the generic
336-file test suite, native resource admission, HA, strict-time mutations,
protected positive APIs, or production execution.

`NativeSupportVerificationError(ValueError)` exposes only `.code` and the same
bounded string, from the closed 13 codes:

`UNKNOWN_SCHEMA`, `GRAPH_SHA_MISMATCH`, `INVALID_DESCRIPTOR`, `INVALID_PATH`,
`UNSAFE_FILE`, `INVENTORY_SHA_MISMATCH`, `WRONG_HEAD`, `WRONG_TREE`, `RAW_MISMATCH`,
`EXTRA_SOURCE_FILE`, `MISSING_HISTORICAL_OBJECT`, `ORIGIN_CONFLICT`,
`GIT_VERIFICATION_FAILED`.

## Validation scope

The pure tests build synthetic MODEL/DATA source graphs and inert object/child
protocol doubles. They test DATA success, origin/order/privacy checks, graph and
inventory tampering, duplicate keys, missing history/source, head/tree/object
identity, casefold/path aliases, hardlinks/reparse/cache files, declared primary
and blob budgets, stdout/stderr overflow, whole/child watchdogs, modeled group
signaling before leader reaping, inherited-pipe cleanup after an exited shim,
reader retirement, and zero-spawn Windows/unqualified Linux branches. The
process/session/signal APIs in these tests are inert doubles, not actual kernel
or real Git execution. Inert source bytes are never imported or executed.
Passing these tests does not pass any Consul, TLS, session, worker, browser,
physical, or native fixture. Original RED logs and exact-source qualification
receipts are retained outside the repository. Existing YAML and fixtures are not
edited or rerun by this work.
