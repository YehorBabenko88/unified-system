# Agent I — Round27 concrete disposable transaction

**NO_GO.** This is source implementation, not trusted publisher or native Windows qualification. It adds a narrow wrapper over the **existing** `InstallationTransaction` and does not create any competing supervisor, service owner, PostgreSQL owner, Consul transport, installer or destructive uninstaller.

## Exact surface

- `unified_system/disposable_installation.py` — `DisposableInstallation.from_capsule` calls existing `source_plan`; `preview` makes zero writes; `stage(disposable_approval=True)` delegates to existing exclusive `InstallationTransaction.create/open/stage`; `observe` replays existing durable receipt; `rollback` delegates to existing retained-bytes logical rollback; `uninstall_preview` refuses removal because a staged capsule is not a receipted Windows service.
- `tests/test_agent_i_disposable_installation.py` — nine newly authored tests, stdlib + repository original offline capsule fixture. Tests cover no effects, approval refusal, staged/reopen idempotence, byte retention, uninstall refusal, foreign path preservation, tamper refusal, interrupted stage retention without adoption, and no new executor.
- No existing runtime entrypoints, service modules, PostgreSQL fences, Consul leases, Windows Job launcher, installation/uninstall owner files or frozen PR #166 changed.

## Reproduction on a disposable local checkout

```sh
python -m unittest tests.test_agent_i_disposable_installation -v
python -m unittest tests.test_installation_transaction tests.test_installation_uninstall -v
```

The test fixture uses a new operating-system temp directory and inert offline release bytes. Do not point these tests or `DisposableInstallation` at existing host paths. Any staged bytes remain inactive. `disposable_approval=True` is an explicit **test-only acknowledgement**, never a substitute for release publisher signature, OS-level ACL attestation or owner-signed protected phase admission.

## Safety and recovery contract

- A foreign existing root, unknown ownership journal, bytes changed after staging, interrupted copy that created the target, or hash mismatch is **not adopted, deleted or retried**. The evidence remains in place.
- No service is started, stopped, registered, elevated or deleted; no PostgreSQL cluster created or removed; PG 5432, user state, AV, UAC and network remain untouched by this wrapper.
- Existing `InstallationTransaction.rollback` is logical and retains every byte. There is **no destructive rollback** or uninstall action in this slice.
- Existing separately receipted APP_ONLY `installation_uninstall.Uninstaller` remains the sole scoped deletion adapter and requires actual service identity and owner guard; not called here.
- Signed publisher provenance, installed wheel RECORD, F handle protection, A Windows Job/SCM, C SQL and E Consul handoff are all independent release gates, currently **NOT_RUN** for this new code.

## Required owner handoffs

A: Do not treat staging as service activation or native positive acceptance.
C: unknown-bootstrap PGDATA and lock never touched; require dedicated non-5432 instance.
E: no Consul session, authority or promotion added.
F: independently inspect path/TOCTOU, foreign-root and journal failure handling.
G: preserve `installation_transaction.py`, `installation_uninstall.py` and service removal until exact migration evidence; no retire proposal follows.
J: port **only three Round27 files**, not this branch's inherited A history, into a non-frozen integration branch with exact HEAD pins and original test receipts.

**CODE NO_GO / PRODUCTION NO_GO.**

## Round28 scoped inactive disposal addition (2026-11-27)

The original `InstallationTransaction` now records `DISPOSE_INTENT` before any file mutation and `DISPOSED_INACTIVE` only after exact release files and expected directories are removed. The journal, state root, install root and empty release directory are **retained**. A crash after the durable intent produces `DISPOSAL_UNCERTAIN_REVIEW_REQUIRED`; no retry, staging or rollback is automatically allowed. There is deliberately **no automatic recovery that adopts missing members**.

`DisposableInstallation.dispose_inactive(disposable_approval=True)` restricts this opt-in operation to a new disposable test workspace directly under the OS temporary root with a `unified-agent-i-` prefix. It validates the original staged Git/capsule manifest and full member closure before any unlink; each member hash and directory identity is rechecked at the individual mutation boundary. Foreign files, changed members, links and changed parent identities block rather than being removed. `fail_after_members` is an explicit test-only deterministic interruption hook. Hostile concurrent filesystem races, private ACL and publisher authenticity remain **NOT PROVEN**, so this is NOT a production removal authority.

`uninstall_preview()` remains a denial for a staged capsule without a separately receipted stopped Windows service. This distinct **code-only disposable disposal** is NOT the existing APP_ONLY service Uninstaller and never uninstalls a real service, PostgreSQL, configuration, user state or backup. No recursion or whole-root deletion is performed.

Round28 test fix: the original `tests.test_lab_release.fixture` returns a Python manifest dictionary, not the manifest SHA. The test harness now writes the canonical `lab-release.json` and computes the actual SHA-256 before constructing `source_plan`; otherwise the earlier nine authored tests could not have exercised real staged bytes. Six additional disposable disposal scenarios are authored. All require original-source execution before PASS can be claimed.

Run on a **disposable checkout**, not a user or production machine:
```sh
python -m unittest tests.test_agent_i_disposable_installation -v
python -m unittest tests.test_installation_transaction tests.test_installation_uninstall -v
```

Round28 focused status at authoring: source code and Git blob comparison PASS; test runtime PASS=0, FAIL=0, SKIP=0, NOT_RUN=15 authored methods. Native Windows/PG/Consul/live operations and 22 physical gates remain NOT_RUN. Independent F/J owner acceptance is pending. **CODE NO_GO / PRODUCTION NO_GO**.


## Round29 actual isolated test receipts and TOCTOU closure

The 15 ORIGINAL test methods from I PR182 ROUND28 (Git blob
`811c9db6847260afe6f84120245e782923233bd4`) were executed
locally using Python 3.13.5 on Linux. Git blob SHA1 was verified identical
for `installation_transaction.py`, `disposable_installation.py`,
`tests/test_agent_i_disposable_installation.py`, `lab_release.py`,
`journal.py` and `contracts.py`. Minimal auxiliary modules
(`runtime_process._safe_path`, `lab_capsule_acl._safe`,
`installation_progress.safe/identifier`, and the LAB fixture) were
extracts of canonical helper functions rather than the entire repository.
**15 PASS / 0 FAIL / 0 ERROR / 0 SKIP** in this *source-bound partial
checkout*. Do not confuse it with full-repo CI, installed publisher
provenance, or native Windows proof.

A separate failpoint probe against the original ROUND28 exact code
demonstrated a genuine path TOCTOU defect: after source hash validation
but immediately before `Path.unlink`, replacing `release/deps` with
a symlink redirected deletion to `outside/requirements.lock`. The
operation subsequently failed, but the unrelated file was already lost.
This was confined to a newly created temporary fixture; no user files
were involved. **Original ROUND28 disposal must NOT be accepted.**

ROUND29 corrects the existing `installation_transaction.py` in-place:
- `_anchored_deletion_supported` refuses all Windows/path-only disposal
  (no native Win32 DeleteFile-by-retained-handle approval). It admits
  only POSIX `O_NOFOLLOW|O_DIRECTORY` and `dir_fd` operations.
- Code and manifest deletion now pin a retained parent directory
  descriptor and retained regular-file descriptor, re-hash exact bytes
  with `fstat`/directory-relative `stat`, and invoke `unlink` using
  the retained parent `dir_fd`, never a late absolute parent path.
  Empty directory deletion likewise uses parent-anchored `rmdir`.
- The same adversarial injected parent-swap now preserves the foreign
  file and leaves `DISPOSE_INTENT` + audit state, refusing retry.
  POSIX `dir_fd` lowers one demonstrated race; it is **NOT fully
  hostile race-proof**, nor production service/ACL/Root authority.

Original 15 plus four added focused tests then executed with exact
ROUND29 I source blobs on Linux: **19 PASS / 0 FAIL / 0 ERROR / 0 SKIP**.
Four added cases cover unsupported-native-delete denial, TOCTOU parent
swap preservation, rollback journal write failure preserving exact
staged code, and symlink member refusal. On Windows, POSIX-only
positive assertions are intentionally SKIP; no equivalent native
destructive path is enabled.

For scoped service lifecycle, a NEW test-only file
`tests/test_agent_i_scoped_service_lifecycle.py` composes EXISTING
`ServiceResource.create/inspect`, `Uninstaller.run(APP_ONLY)`,
`tests.test_installation_service.FakeWindows` and
`tests.test_installation_uninstall.FakeRemoval`. It exercises stopped
registration -> owned removal with state/journal retention, foreign-code
refusal, register crash/no implicit adoption and wrong-host refusal.
There is no additional production SCM, activation, supervisor or
service-uninstaller implementation. **These 4 service-composition
methods are newly AUTHORED / NOT_RUN** in the local partial checkout;
full original test dependencies were not downloaded. Original host,
wheel signer, Windows Job, PostgreSQL 18, Consul TTL, production and
physical acceptance remain **NOT_RUN/DENIED**.

Exact I HEAD and Git blobs must be frozen again by F/J after selective
transplant; this document does not authorize release. **CODE NO_GO /
PRODUCTION NO_GO**.

## ROUND30 — last-component TOCTOU: DENY until proven exclusive namespace

F/J independently identified that the ROUND29 POSIX descriptor-relative guard
protects the **parent** but does not make the leaf file `stat`/hash and
`unlink(name, dir_fd=...)` atomic against an adversary swapping the final
name. Exact code already has a durable intent and fail-closed recovery, but
that is **not** sufficient to prevent deletion of a replaced foreign leaf.

Rather than invent a second file owner or falsely claiming atomic unlink,
the canonical existing `InstallationTransaction.dispose_inactive` now
requires `_exclusive_namespace_proven()` before any durable intent or
unlink. That internal predicate **always returns False** until an independently
reviewed OS-held single-writer namespace proof is implemented by A/F.
Neither `approved_disposable=True`, temporary directory naming, POSIX
permission bits, an owned journal nor SCM state substitutes for this proof.
The fail-closed gate applies on **all platforms**, including POSIX. Windows
remains denied by the prior `_anchored_deletion_supported` guard.

The three deliberately destructive/fault-injection unit tests override this
internal predicate through `unittest.mock.patch` **inside disposable
test fixture only** to verify existing journal semantics and ensure the
regression suite remains executable. This test override is **not an API
or an authorization mechanism for users or production**. A new 20th test
uses the ordinary unpatched source and verifies exact staged bytes and
journal remain unchanged when someone supplies `disposable_approval=True`.
No normal source path deletes files.

Execution: verified original source files in the isolated Linux partial
checkout and ran `python -m unittest tests.test_agent_i_disposable_installation
-v`: **20 PASS / 0 FAIL / 0 ERROR / 0 SKIP**, Python 3.13.5, exit 0.
The earlier ROUND30 baseline of 19/19 PASS was also executed. This is
**not** full-repository or native Windows CI, nor installed wheel/Root
attestation. Four existing stopped-service `FakeWindows`/APP_ONLY
composition methods were inspected against the original GitHub source
but are **NOT_RUN** in the incomplete checkout. Existing Windows
`ServiceResource` and `Uninstaller` remain authoritative, unchanged,
and unqualified for physical machine use.

Release gates: **CODE NO_GO / PRODUCTION NO_GO**, no host actions, no
destructive real-PC or user-state operations, no native service deletion,
no validated full uninstall or real rollback, no main merge or frozen
#166 changes. Do not accept the fact that test-only `unlink` scenarios
PASS as permission for a real uninstall.

## ROUND31 — canonical APP_ONLY uninstaller native deletion denial

A distinct critical path was found in original `unified_system/installation_uninstall.py`:
`Uninstaller._run(APP_ONLY)` stages one durable `MEMBER_INTENT`, then
rechecks `image(path)` / directory identity inside a SQLite critical section
and **deletes by a later `Path.unlink()` / `Path.rmdir()` pathname**.
SQLite ownership receipts and a stopped Windows service do NOT atomically pin
the last filesystem name. A hostile actor could replace the last-component
leaf after the check and before deletion. This is NOT the previously fixed
disposable transaction: the original APP_ONLY owner had a second path.

ROUND31 closes the production entrypoint **by refusing physical deletion
before any service/audit/file mutation**. In canonical `Uninstaller._run`,
the internal predicate `_exclusive_code_removal_proven()` always returns
`False` and `need(...)` is required immediately after validating APP_ONLY
mode, BEFORE `_members`, private audit creation, SCM removal, or `unlink`.
No external caller option, old ownership receipt, test mock, local temp prefix,
ACL setting or signed manifest can authorize this unresolved native mechanism.
The lower-level path-based deletion is NOT claimed secure and remains
reachable ONLY through deliberately patched fixture tests; do not ship a
patched policy or change the default without independent F/A review.

For coverage of existing unique `APP_ONLY` behavior without real host access,
the original `UninstallTests.setUp()` and I's scoped service fixture
temporarily patch this **private predicate** to True inside original inert
`FakeWindows`/`FakeRemoval` and Python `TemporaryDirectory` only.
This preserves the original useful stopped-service, CAS, interrupted
state preservation, foreign-file refusal, and ownership journal test
scenarios while normal runtime calls deny destructive effects.
A new `test_default_owned_app_only_denied_before_audit_or_service_effect`
temporarily restores the unqualified default inside that fixture and asserts
no audit, service change or member deletion. This does NOT prove native
Windows installed release admission or protection against intentional code
tampering by same-privilege Python processes.

Execution status: I original 20-test disposable suite re-executed in
the prior source-bound Linux partial checkout: **20 PASS / 0 FAIL /
0 ERROR / 0 SKIP / exit 0** (original byte-identical I core/test files).
The updated APP_ONLY test files have not been run in a full checkout
because the isolated source-bound checkout still lacks the original
`installation_service` and `scripts/prepare_lab_capsule.py` fixture.
Those updated original APP_ONLY tests are **NOT_RUN** and must be
executed by J/A/F on a genuine full isolated checkout. Native Windows
service lifecycle, file-handle custody, installed wheel, Consul/PG18
and real host removal remain **DENIED / NOT_RUN**.

No actual service, user DB/PG5432, caller data or installed folder was
modified. **CODE NO_GO / PRODUCTION NO_GO**.
