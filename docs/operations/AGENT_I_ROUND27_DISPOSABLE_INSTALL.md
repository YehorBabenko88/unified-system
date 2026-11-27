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


## ROUND32 — native Windows original HANDLE removal candidate; still DENIED

The canonical APP_ONLY Uninstaller now has `_win_handle_dispose_member` INSIDE the existing original owner module, not a second service remover. Its candidate uses CreateFileW(GENERIC_READ|DELETE, FILE_SHARE_READ only, OPEN_EXISTING, FILE_FLAG_OPEN_REPARSE_POINT), plus FILE_FLAG_BACKUP_SEMANTICS for directories. It refuses reparse, identity/mtime/size/hash mismatch, hardlinks, unsupported final handle paths and native API failures. A retained CRT descriptor reads the SAME originally opened OS HANDLE, compares the original journal device/inode/bytes/mtime_ns/sha256, then uses SetFileInformationByHandle(FileDispositionInfoEx=21, DELETE|POSIX_SEMANTICS) on THAT original kernel file object, not a second pathname lookup. Unsupported native operations have NO Path.unlink/Path.rmdir fallback. A nonempty directory is DENIED.

IMPORTANT: both Uninstaller._run(APP_ONLY) AND the primitive directly check `_exclusive_code_removal_proven()` which still ALWAYS RETURNS FALSE. This keeps all normal file deletion DENIED even when a caller attempts to import the helper directly. No caller boolean/temp-root/service receipt lifts it. The test-only mock patch does not constitute F/A release authorization. The Windows primitive is CODE CANDIDATE, not native-accepted or capable of host installation.

Six additional original existing-suite negative/native tests in tests/test_installation_uninstall.py: exact original handle owned disposable file deletion (Win32-only); same-byte different inode refusal (Win32-only); empty directory original-handle delete (Win32-only); nonempty directory foreign member retention (Win32-only); direct helper invocation without independent proof refusal (cross-platform); non-Windows call refuses without mutation (POSIX-only). Total APP_ONLY authored methods now 28, plus four separate scoped FakeWindows methods. Four Win32-only cases require original native runner; Linux cannot prove them. 28 original suite methods and four scoped fixture methods remain NOT_RUN in the partial checkout until J/A/F acquire full source/fixture test execution.

Owner F/A must verify native FILE_ID_INFO/Python fstat cross-representation, retention/multiple preexisting handles, directory CRT support, path aliases, reparse and hardlink attacks, thread races, restart/wire loss and durable journal correctness before even proposing a security gate change. The original APP_ONLY path-based mock test semantics are retained; the production Windows path has no late name-delete fallback.

References: https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew ; https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-setfileinformationbyhandle .

No main merge, force push, frozen #166 change, ADMINIT, real service/host operations, user DB/data, trades, or security weakening. CODE NO_GO / PRODUCTION NO_GO.

## ROUND33 — retained-parent and full 128-bit native file identity candidate

F independent R32 review (#174 comments 7217336245 and 7217362080) identified two practical omissions: original candidate compared only CRT st_dev/st_ino and used a path-based directory emptiness read. This existing canonical Uninstaller native helper is now amended as source candidate:

- `_win_handle_dispose_member(path, owned, kind, parent_identity)` takes the original sealed MEMBER_INTENT parent identity, validates it before any Win32 call and opens the original parent as a retained HANDLE with share READ (not write/delete). Unsupported/renamed/foreign/reparse parent refuses.
- `GetFileInformationByHandleEx(FileIdInfo=18)` records exact 64-bit volume serial and 16-byte native FileId of both held parent and member, and rechecks both before disposition. Original CRT identity and sealed member receipt still checked for FILE; the native 128-bit FileId is compared across the retained HANDLE lifetime but is NOT YET bound into a trusted installation-time journal. That missing installation-time full-identity binding is a **release blocker**, not an implied proof.
- Empty-directory inspection uses `GetFileInformationByHandleEx(FileIdBothDirectoryRestartInfo=11 / FileIdBothDirectoryInfo=10)` on the SAME original directory HANDLE, allowing only '.'/'..' entries. No `Path.iterdir()` is used for native directory validation, and no CRT `open_osfhandle()` is invoked on a directory HANDLE. Unsupported enumeration, nonempty directory or any unexpected Win32 error is DENIED.
- Files still use original HANDLE through CRT `os.fstat/read`, sha256 rehash, link-count=1, identical original member identity and refreshed 128-bit native member/parent identity before `SetFileInformationByHandle(FileDispositionInfoEx=21)`; no name-delete fallback. The paired original native Windows test file now passes exact parent identity and includes foreign parent-identity mismatch and hardlink negative cases.
- Both canonical `_exclusive_code_removal_proven()` checks (entry and direct helper) are STILL hardcoded False; `InstallationTransaction._exclusive_namespace_proven()` is separately False. No native effects are reachable through normal public invocation. No same-privilege test monkeypatch is an authority mechanism.

**QUALIFICATION LIMITATIONS**: no native Windows2022/2025 execution of latest helper, no original full-suite APP_ONLY test PASS, no installation-time FileIdInfo seal, no attested user-PC ownership, no hostile concurrent writer/rename or restart/SCM/SQL exercised, no native directory emptiness proof PASS. Even with full held HANDLE checks, don't change either release gate until F/A independently approve the original Windows disposable matrix and source/identity binding. Exact R33 native candidate is NOT production installation/uninstall readiness.

Runtime scope unchanged: no real host/Windows SCM, admin elevation, user PostgreSQL, trades, data deletion, main/force or frozen PR #166 changes. CODE NO_GO / PRODUCTION NO_GO.


## ROUND34 — installation-time Win32 FileIdInfo V2 receipt (candidate; deletion DENIED)

MASTER #111/7218376419 and I #174/7218372898 require installation-time VolumeSerial+128-bit FileId sealing, parent binding, strict V1 migration and crash evidence. This change uses the EXISTING `ServiceResource` journal and `Uninstaller` only. It does not create another installer, superuser service, file cleaner, mathematical apparatus, database or remote-client owner.

`unified_system/installation_service.py` retains the V1 service plan schema and adds a SEPARATE typed `NATIVE_FILE_IDS` transition after `CODE_STAGED` and before `ACL_SEALED`. New private `NATIVE_RECEIPT_SCHEMA='unified.installed-file-identity.v2'`. Windows-only `_native_file_identity(path)` opens the original path with `CreateFileW(FILE_READ_ATTRIBUTES, FILE_SHARE_READ only, OPEN_EXISTING, OPEN_REPARSE_POINT|BACKUP_SEMANTICS)` and uses original retained handle `GetFileInformationByHandleEx(FileIdInfo=18)` to capture native nonzero volume serial plus exact 16-byte FileId, rejects reparse and closes the held handle. Captured entries cover root, code, ownership directory, preserved state directory, current ownership `service.sqlite` journal, EVERY original manifest file, each manifest directory, plus staged `lab-release.json`; all entries are protected by canonical receipt hash `seal(body)` and the existing durable SQLite hash chain. A 60KB canonical receipt cap prevents silent loss/truncation under the existing 64KB row/2MB journal limits. Oversized capsules remain an installer **NO_GO** until a separately reviewed chunked owner receipt exists.

The original `ServiceResource._read()` recognizes 6-transition V1 and 7-transition V2 layouts. It never automatically upgrades V1 to native-qualified; V1 `recorded()['native_file_identity']` is `None`. Non-Windows test installs get an explicit versioned `{'schema':..., 'status':'NOT_RUN'}` marker, also `native_file_identity=None`: simulated IDs cannot become installed evidence. Partial V2 before REGISTERED is readable for forensic review, but `recorded()` and `inspect()` deny adoption. Registration is after native receipt; a failure before/after the transition retains resources for operator review, never retries or auto-deletes.

`unified_system/installation_uninstall.py` has an additional V2 admission check in `_members` for the ORIGINAL `WindowsRemovalBoundary` (V1/partial/no native record DENIED) and binds the stored installation-time native identity of both parent and leaf to the SAME original Win32 handles in `_win_handle_dispose_member` before disposition; mismatched full volume or 128-bit IDs DENY. The original separate `_exclusive_code_removal_proven()` gate remains ALWAYS FALSE in BOTH the public APP_ONLY path and direct native helper; the other `InstallationTransaction._exclusive_namespace_proven()` is also ALWAYS FALSE. This is CANDIDATE correctness, not actual native uninstaller permission or user-machine readiness.

The updated original tests exercise V2 layout and V1 fail-closed compatibility, invalid version/receipt/extra member/missing manifest entry/boolean volume, interrupted SEAL crash with retained staged code and refusal to adopt, and Windows-only native mismatched stored FileId or volume refusal. They must be executed in a complete native runner; only separate earlier unchanged original disposable 20-test suite is locally executable in the partial source checkout.

Outstanding P0: NO native Windows2022/2025 original tests; no independent F/A installed-time full member FileId/retained-handle proof; no Windows SCM/ACL process acceptance; staged FileId captured post-stage, not protected by a retained native HANDLE held continuously since create; untrusted same-privilege administrative writers remain out of scope; large manifests cannot fit one native receipt; native file deletion/cross-volume/ancestor rename/restarter replay not independently qualified. F/A/J must run original service+uninstaller+scoped 28+32+4 test files and adversarial native tests without user data/real machine effects, then resolve these before any GO.

No main merge, force, frozen PR #166 change, ADMINIT, user PostgreSQL/PG5432, real trade or data removal, Codex/Claude, or security policy weakening. CODE NO_GO / PRODUCTION NO_GO.

ROUND34 source follow-up: `Uninstaller._members()` checks the current original FileIdInfo of installed root, ownership directory, preserved state directory and ownership/service.sqlite against V2 before it could admit the real Windows removal boundary. A present code directory must also keep its original install-time FileIdInfo. If code is absent, recovery can only proceed through preexisting durable intents; a new directory identity is never adopted. These checks are read-only and remain behind the disabled physical-delete entrypoint.

Hosted GitHub Actions for the R34 candidate reported instant `completed/failure` with no jobs returned (e.g. 46000955207, 46000955607; created and updated one second apart). These cannot be counted as executed unittest FAIL, or as PASS; the reason requires runner/Actions service diagnosis by owners. No retry/dispatch/cancel performed. Independent local executable source evidence remains limited to the original unchanged 20 methods and exact V2 receipt validation excerpt.


## ROUND 35 — V2 ancestor observations and crash/size gates (2026-11-27)

**Still CODE NO_GO / PRODUCTION NO_GO.** Source change only; this
does not authorize a service install or any physical deletion.

In canonical `installation_service.py`, the V2 install-time FileId roster
now includes the complete install-root ancestor chain, intermediate
subdirectories omitted from the manifest's directory list, each manifest
member, the installed manifest itself, and the service ownership journal.
Both native observations must match for **every** member and ancestor before
`NATIVE_FILE_IDS` can be journaled. Win32 FileStandardInfo additionally
rejects delete-pending objects and regular files with multiple hardlinks;
the native query or capability being unavailable fails closed.
The existing 60000-byte journal receipt cap remains a refusal rather than
a truncation. Earlier V2 receipts that lack the new mandatory roster will
not be silently upgraded or admitted to native removal.

**Security boundary:** two path-based native observations do NOT hold all
parent handles continuously from initial staging, and cannot establish
hostile-writer exclusion against an intermediate swap and restoration.
The SHA-256 journal seal is not an independent publisher signature or OS
trust root. Native Windows 2022/2025 SCM, FileIdInfo, FileStandardInfo,
held-handle ancestor swap, junction/reparse, hardlink race, unsupported
filesystem, interruption/restart, large capsule, ACL and recovery remain
unqualified until tested on J's isolated disposable runner with A/F
independent review. Both `_exclusive_code_removal_proven()` and
`_exclusive_namespace_proven()` must remain unconditional **False**.

New source tests in `tests/test_installation_service.py` exercise
pure roster construction (including a manifest that omits parents),
malformed traversal rejection, stable native mock reads, drift and volume
negative cases, and 60000-byte receipt denial. These tests do not invoke
real Windows SCM or disposition. The existing crash-before-ACL and V1
recovery negative cases remain in the original suite. The per-HEAD
PASS/FAIL/ERROR/SKIP/NOT_RUN classification is recorded in issue #174.
Do not promote earlier R34 local PASS to R35 HEAD.

J may selectively import **only** these five owned files after pinning
the exact current HEAD and reviewing test evidence:
`unified_system/installation_service.py`,
`unified_system/installation_uninstall.py`,
`tests/test_installation_service.py`,
`tests/test_installation_uninstall.py`, and
`docs/operations/AGENT_I_ROUND27_DISPOSABLE_INSTALL.md`.
Do NOT import the whole PR #182 (inherited 2239-file diff),
merge main, touch frozen #166, use live SCM/user data/PG, or
enable any physical deletion gate.


## ROUND 35 later cycle — retained native handle custody source candidate

Follow-up to F security review: `_NativeReceiptCustody` now opens every
observed namespace member and ancestor using `CreateFileW` with
`FILE_SHARE_READ | FILE_SHARE_WRITE` (but **without FILE_SHARE_DELETE**),
so SQLite can append to its ownership journal during the custody period.
It captures native FileIdInfo/FileStandardInfo from the
**same retained handles**, compares fresh native path observations, and keeps
the original handles open through `NATIVE_FILE_IDS`, `ACL_SEALED`,
`REGISTER_INTENT` and `REGISTERED` journal transitions. No delete sharing
is granted by custody acquisition. A context manager closes every retained
handle, including on the exception path; OS termination also closes process
handles. Reopening after a crash never reuses these handles as proof.

This is an **unqualified candidate**, not a completed hostile-writer proof:
some Windows filesystem/SMB configurations may reject the new share mode;
large manifests can exceed OS handle budgets; a malicious administrator,
ACL modification, concurrent log/SQLite writes or an unsupported native API
may prevent capture. Any such case must fail closed, not trigger a fallback
or permission relaxation. A crash during SCM native registration may leave
a stopped but incompletely receipted service, which must not be adopted.
No previously installed V2 or V1 receipt is upgraded.

Native Windows2022/2025 genuine tests, reboot/restart, hostile ancestor
junction/swap, FileId drift, independent F acceptance, J selective
integration and raw CI logs remain required. Scoped tests in the original
service test file validate fake handle close order, exception cleanup,
readback mismatch refusal, and static nesting of the registered transition
inside the custody scope. Fake/static tests do not prove genuine Win32.

**Both physical deletion gates remain unconditional FALSE**.
No physical deletion, user data, real SCM deployment, ADMINIT, production
PG, live trades, main merge, force push or frozen PR #166 changes. No
code-retirement authorization is implied. **CODE NO_GO / PRODUCTION NO_GO.**

### ROUND35 additional fail-closed handle budget

`_NativeReceiptCustody` currently refuses to retain more than **512**
handles and never falls back to path-only registration. This limit can
reject normal large releases and is therefore an **installation blocker**
until a separately reviewed bounded roster/chunk protocol exists; it is
not a production-ready scalability feature. A static assertion confirms
SQLite write sharing remains enabled while delete sharing is denied.
The owner source and native retention tests remain subject to independent
F and J acceptance and must not be counted as native PASS by this text.

## ROUND35 follow-up — bounded original V2 roster preflight

The last source iteration adds `_native_receipt_roster_budget(paths)`
immediately before Windows `_NativeReceiptCustody` opens any handle.
It enforces at most **512 identities**, each key at most **300 UTF-8
characters**, and a conservative `sum(112 + len(key UTF-8)) <= 56000`
estimate. The existing exact canonical V2 row limit of **60000 bytes**
remains separately mandatory. No roster is shortened, sampled, chunked,
silently upgraded, or permitted to bypass native identity verification.
This is a **denial policy**, not a throughput qualification.

The same capacity check now also runs **before BEGIN/root creation and
before `lab_release.stage_capsule()`**, after the existing source capsule
verification. A deterministically oversize source roster is denied
without creating an installed root or entering SCM. A second check remains
after staging, before any retained handle is opened, to refuse unexpected
changes or manifest drift; if that later check refuses, the partial root
is retained as forensic evidence, never deleted or adopted automatically.
These checks do not establish that a real release fits the budget.

The repo fixture is small; no real assembled release manifest /
file-and-directory inventory was independently available in this cycle.
Thus a numeric claim that the present 512-handles/56000-byte limit
fits the actual full unified release is **NOT_ATTESTED**. J must obtain
the immutable release manifest and report exact required handle count,
canonical receipt byte count, and Windows2022/2025 resources before
any installer qualification. F must independently review root ancestor
path/retained-handle semantics, journal sharing and cleanup on exceptions.

New original tests cover a bounded small synthetic roster, count overflow,
path-key overflow and preflight byte-estimate overflow. All current-HEAD
original native Windows tests remain **NOT_RUN**, not PASS. The two
physical deletion predicates remain unconditional `False`.
**CODE NO_GO / PRODUCTION NO_GO.**

### Canonical capsule capacity versus installer admission

Original `unified_system/lab_release.py` at Git blob
`1084158079d961c73d805350ff57731292c44137`
accepts up to **100000 `files`** and up to **100000 `directories`**
in the V1 manifest schema. That is a verified **source-contract
mismatch** with the Windows V2 native custody limit of **512 total
roster keys**, and the 60000-byte journal receipt cap. It is not proof
that any particular assembled release actually contains more than 512.
Do not raise the limit, truncate identities, split receipts or relax
no-delete-sharing solely to make a large release pass. Large release
support needs an independently reviewed design and real manifest
counts and raw Windows fixture evidence. Until then the intended
outcome for an oversized real candidate is safe pre-BEGIN rejection.

Current exact-HEAD original tests are not executed by this document;
GitHub source checks and synthetic method-count bounds are evidence
only for static logic. **PRODUCTION NO_GO**.

## ROUND35 P0 native directory-open correction (2026-11-27)

Independent F review found that the retained Win32 custody opened **directories**
without `FILE_FLAG_BACKUP_SEMANTICS`, which Microsoft requires for a
`CreateFileW` directory HANDLE. The canonical owner code now chooses flags
from the exact roster role, not an untrusted leaf-attribute probe:

- `root`, `code`, `ownership`, `state`, `ancestor:*`,
  `directory:*`, `parent:*`: `OPEN_REPARSE_POINT | BACKUP_SEMANTICS`
  (`0x02200000`).
- `file:*`, `ownership:service.sqlite`: `OPEN_REPARSE_POINT`
  (`0x00200000`).
- Unknown and empty role qualifiers are **rejected** before native open.

For all roles the only share mode is `FILE_SHARE_READ|FILE_SHARE_WRITE`
(`0x3`), **never** `FILE_SHARE_DELETE`. The original native
`FILE_ID_INFO`, reparse, FileStandardInfo and receipt rules are unchanged.
The held-handle path still runs across ACL/SCM receipt transitions, and
releases each handle on failed acquisition, failure and normal exit.

Original `tests/test_installation_service.py` includes executable
role-to-flags cases and two fake-kernel tests of the **production**
`_NativeReceiptCustody.__enter__` / `__exit__`: per-role Win32 flags,
write/no-delete sharing, retained lifetime and reverse-order cleanup on
partial handle failure. The fake Win32 tests **do not imply** that a native
Windows2022/2025 handle open, SQLite sharing, ACL, SCM or crash has passed.
All such original native cases and real release inventory sizing require
independent F/J qualification at the exact commit. No physical deletion,
no main merge or force push, no automatic promotion. Both gates are FALSE.
**CODE NO_GO / PRODUCTION NO_GO.**
