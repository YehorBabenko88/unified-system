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
