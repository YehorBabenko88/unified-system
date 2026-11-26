# ROUND 18 continuation — exact source→wheel→installed gating

Read-only non-atomic GitHub snapshot (2026-11-26): A `743329b1161e8967335d5c6d6e1ea8bd669251ee`, B `6d9373a435f4f99ff15f999622c4e1143d9a832e`, C `7ebebce569f2ec616ed631c57b4d267abda340a1`, D `89022d7885d279bb1fd2f695b59f2c243b431ad2`, E `1c2edb2564c48a1348d3ad4ee94fe8fa0b425b18`. The single Draft integration #166 remains `9349d7f3ed93ef82d120976816b968e0b716b067` with no F runtime integration.

## Canonical B packaging: OWNER CHOICE RECEIVED

B has now amended **the existing** `market-data 0.2.0.dev0` `pyproject.toml` (Git blob `4fb4e72360605cd92b3afab3837015b4ac29dace`) to include exactly four dotted `grid.*` `py-modules` plus `market_data`, `market_data_v2`, NOT the whole legacy Grid. The earlier proposal to physically move the files under `market_data/` is SUPERSEDED. No second packaging path or writer is authorized. B `RootCanonicalWriterFactory` lives in the original async writer module (blob `35bf202bb1674238d53b74f962af966d2a699fa2`), not an alternative SQL writer. E `LabWriterOperationPermit` source (blob `ed966cc79aee3da33a5c658737486139c16b7e3c`) is compatible in argument shape at source level but its issuance still DENIES `LAB_OPERATION_INSTALLED_WHEEL_UNVERIFIED`. This remains essential.

Independent SHA256 of exact current B source (not wheel):
- `grid/canonical_lab_fenced_writer.py` blob `247d7fab2738e1892a05979e407f637f9df62784`; SHA256 `db78f50146528fb6a3f4a6907a1679dd1e45cf2820efcee90e03d6c9e46e615a`
- `grid/c_async_fenced_writer.py` blob `35bf202bb1674238d53b74f962af966d2a699fa2`; SHA256 `216f03122f6bb168234019e1dbaa3380c8c35a789be8f3a1bf9fec1a5de5972c`
- `grid/c_lab_journal_adapter.py` blob `ab93c6d421c3d3f0232060f6ded7ac01bf8eeda0`; SHA256 `69bb02182e73bfe4d80f98fa8f1cec846d18334693aa8443eec88babb901f01a`
- `grid/canonical_lab_continuous_collector.py` blob `873e83839bee9ceb1cca710a5291ba2cf5f7f038`; SHA256 `293f89bc59481299b65c3d138171cae4b18c5045386d1319f1a8dc3818a9eca9`
- required parent `grid/__init__.py` blob `3dc1f76bc69e3f559bee6253b24fc93acee9e1f9`; SHA256 `91447944015cec709e8aa7655f7e9d64e1e4508e7023a57fe3746911c0fc6fed`

Exact allowlist in `docs/git-consolidation/round18-b-wheel-source-pins.json`. This is a machine-input candidate from GitHub, **not protected Root-signed activation**. B must actually build and produce original wheel+sdist, then prove these five members occur in wheel and installed RECORD. E must independently validate the true installed package origin and live release/lease; an F offline checker result is never operation authority.

## Executed F package verification

`tools/f_wheel_qualification.py` Git blob `310264da7a3b79632843c6a9f09628c7e80235a0` checks a pinned wheel ZIP, its archived RECORD, separately rewritten pip installed RECORD, installed byte hashes, path safety, duplicate entries, package METADATA, console entry-point metadata and expected source files. A real **offline pip --no-index --no-deps --target install of a SYNTHETIC test wheel** was executed. `tests/test_f_wheel_qualification.py` blob `9f58333bac69ce3e2b966a53f81b1419e0764acd`: Python 3.13.5, 26/26 PASS; py_compile PASS. Includes script tamper denial and deterministic fixture. No actual B wheel was built or installed, no real CLI executed, no import-origin or native E2E proven. `all_installed_bytes_authenticated`, `release_authenticated`, `writer_admitted`, `root_admitted` are always FALSE: unverified .pth, pyc, import hooks, activation cannot become authority from file hashes.

A original Windows ProcessDriver source blob `06e9389d4d53b62ffe72c81d0a12f4eda5b63b50` has retained Job receipt, but E Root binding and native Windows/SCM/port closure remain unproven. C canonical PG recovery blob `ef9c14aacd8437d4b9f9ebbe2fb8a956fb93382f` has advisory OS-backed lock, not trusted full Root lease; interrupted WAL/unknown-COMMIT/native PG18 proof not complete. Historical strategy parity D component success is not global proof.

**Admissible release/production result: NO. CODE NO_GO / PRODUCTION NO_GO.** All newly installed runtime and privileged permission issuance remain DENIED until native proof and MASTER approval.

## Historical Round17 snapshot (not current authority)

# F ROUND 17 — minimal executable native cohort admission gate

This file is the **current** F gate as of 2026-11-26; exact GitHub non-atomic snapshot. It supersedes the historic ROUND 16 pins in its earlier revisions. Sole integration Draft PR #166 is **frozen** at `9349d7f3ed93ef82d120976816b968e0b716b067`. Existing PR #165 contains F-only qualification; NO mixed runtime imported.

Current verified Draft heads: A `5bcaed7d916d72837064da9ab938e28c35695624`; B `20656417e61d26a294809cf649c37a37906b6dcf` and custody `39a6cf4d8c039ca99bbfc00ca7cc2359bef5c60c`; C `3bbd846dff646164903aeec2e2ef5cca7de1b9b0`; D `4fd05211f10aa69108b598b0849abc842ec91899`; E `d231a0ad657b7e12f89ddc9cde2ef6b5b028a125`; Math snapshot `9e6acbd9e12a91189f57234828e31640983af553`; F prior head `5570856074437362ff7b7af0306cc386ec6cff4f`.

## Actual exact-head code, without inaccurate historical blockers

- A `unified_system/runtime_process.py` Git blob `3c948515932584ae72fd3acaa0d5c21f877a50bf`: sole `ProcessDriver.owned_process_state`, `RetainedOsProcessWait`, retained `RetainedWindowsDescendantCensus`, and `OwnedWindowsJob`. Its `verify_complete_extinction` and `assign_suspended_child` are **deliberate unconditional DENY**, not working suspended-process containment. Real native A-owned `CreateProcessW(CREATE_SUSPENDED)` + original process/thread handles → trusted Job assignment before resume → Job member/descendant/endpoint extinction is MISSING.
- C `unified_system/lab_pg_recovery.py` Git blob `877ca501323c4387883084851564e814f9920d45`: C **already** binds original owner+namespace+generation+fencing token+backend PID/start to private pgdata root/inode and original postmaster, imports A `RetainedOsProcessWait`, and holds exact kernel OS wait across C-only stop/restart. Prior ROUND16 assertions “C has only `_STATES[pg]`” and “C does not consume A retained postmaster” are **obsolete and must not be used for new approval**. But `_DATA_OWNERS` is process-local; another process can manage same physical root unless C adds OS-backed resource exclusivity across process/crash/timeout. 15 PG18 native test METHODS authored, no concluded native evidence.
- C `unified_system/lab_pg_fence.py` Git blob `d525940eba4b2a57c15b9127854c839000e6af0b` binds `backend_start` to the same C SQL fence revalidation snapshot; neither this readout nor the C WAL diagnostic is an operation grant.
- E `unified_system/lab_pg_recovery_lane.py` Git blob `954d6af2d35578340730db44f725d2758c2643e3`: `recover_once` currently **unconditionally raises `LAB_ROOT_BOUND_EXTINCTION_NOT_IMPLEMENTED`**. E correctly does not execute a second PG `stop`/`start` mechanism; the denial is deliberate and safe, but NOT executable recovery.
- B frozen canonical writer `grid/canonical_lab_fenced_writer.py` Git blob `8b93466a79fa234468a3cdc44106bd5e153e81c4`; other B30 blobs and sha256 are exact in manifest. B legacy `require_current() is True` and E async grant lack one authenticated owner-thread permit. No fake `True`, new writer, duck-type or asyncio-in-poisoned-thread workaround.
- D current `4fd05211f10aa69108b598b0849abc842ec91899` retains POC research composition, but historic `POC_MEAN_REVERSION` and 20 imported strategies remain SPEC_ONLY absent dynamic source-equivalence evidence. Math remains sole computation and Terminan sole PaperEngine.

## Must be implemented by canonical owners before F can move mixed runtime

1. **A** makes its existing single `ProcessDriver` create a LAB-owned child suspended using actual OS `CreateProcessW(CREATE_SUSPENDED)`; retain original thread/process kernel handles, attach to owned Job, verify membership before `ResumeThread`, keep it contained, prove all Job descendants and listeners (plus SCM ownership when relevant) extinct. On Windows or Linux UNKNOWN → DENY. No external PID attachment and no caller-provided suspension flag.
2. **C** adds one **OS-backed exclusive lock** keyed to its already canonical PG18 owner marker and physical pgdata root (device/inode), held throughout containment, timeout, poisoned old worker and subsequent WAL verification. No second PG owner across separate processes. Retain A `RetainedOsProcessWait` contract, never replace it or touch foreign PG/5432; validate old backend identity, WAL, pending/checkpoint/high-water/content_id and unknown COMMIT on actual native PG18.
3. **E** implements nonforgeable issuer/verifier of RootProcessExtinction+RootBackendExtinction with provenance of original OS handles, descendants/listener/SCM, release, owner/namespace, generation, epoch, token and C PG instance/backend PID+start. No direct C dispatch until real physical and credential/lease binding, no caller bool or type-only gate. Do not release original Consul lease on UNKNOWN or old worker unresolved.
4. **B/C/E** implement ONE sealed synchronous same-executor operation permit in real Grid existing writer. Validate Root-issued owner+namespace+generation+fence token+epoch+backend PID/start+executor+installed exact package+operation/content_id, and C sole `public.lab_fenced_insert` remains final SQL check. Never install an async-to-sync `True` shim or second SQL writer.
5. **F** verifies true built wheel/sdist SHA256, installed module bytes/import origin/entrypoint, SQL schema, packaging/lock reproducibility across OS, full Git history+LFS+nested archive security, semantically justified dedup and historical unique function parity. F shall not write conflicting runtime into #166 in absence of verified A/C/E/B implementation and MASTER approval.

## Isolated qualification order

1. Pin and validate exact source Git blobs, B30 four SHA256, package dependency/installer manifest, native Windows/Linux and PG18 versions.
2. C runs only against disposable dedicated LAB (never user 5432); process OS Job/handle is A-controlled, PG resource is C OS-lock controlled, Root/Consul E grant is not forged.
3. Read source and WAL durable high-water, unknown COMMIT, pending/checkpoint, immutable row+content_id; kill disposable LAB postmaster under strictly proved owner and re-run C crash recovery; require actual recovery logs, not clean stop.
4. Prove old Grid descendants, listeners, executor thread and old PG backend physically extinct; new generation/token/epoch/journal/backend/executor/Grid and D Math consumer appear only AFTER full authenticated receipts.
5. Confirm exactly-once rows, old source denial, no double Bybit/writer/supervisor/Math/PaperEngine, 100k streaming conservation, Windows uninstall and **foreign PG unchanged**.

**Current status: ALL NATIVE ADMISSION GATES BLOCKED. CODE NO_GO / PRODUCTION NO_GO.**
