# F ROUND 16 — minimal executable native cohort gate

Source-pinned non-atomic GitHub snapshot dated 2026-11-26. **This is a release-safety gate, not yet an executable integrated runtime.** The existing sole integration Draft PR #166 `9349d7f3ed93ef82d120976816b968e0b716b067` stays untouched. The owner branches remain A `324d6bfd85624e21213180dc66a9c67d4ac790ce`, B `8594cc8812225dee6c4f292a7692486bb443ca06`, C `3046f9dbfe9b587370ba0bffbfb716b59a4f56ca`, D `254c6888e1b6665bdf83ff42794e2389a53c8ace`, E `5490cf118eccb27e59905a89d4c5dac2c8b3fcbc`; B custody `39a6cf4d8c039ca99bbfc00ca7cc2359bef5c60c`, Math `9e6acbd9e12a91189f57234828e31640983af553`. All are separate Draft/unmerged source cohorts.

## Actual currently inspectable cross-owner code

- A sole `ProcessDriver.owned_process_state` and `RetainedOsProcessWait`: `runtime_process.py` Git blob `3e28008ba11dab55ecd77af2e0faf35b0a013d41`. Retained exact kernel process wait, plus read-only TCP/SCM/descendant snapshot primitives, but NOT a sealed RootProcessExtinction or full child-confinement proof.
- C sole `contain_exclusive_lab_cluster` / `recover_exclusive_lab_cluster`: `lab_pg_recovery.py` blob `60a09733751182c97ba3c49436a5b88ea7fcb7b0`. `LabPostgres` blob `95d12797286953daa7308d54dbc04216e1bb7e08`. No A retained postmaster wait applied to physical recovery; C SQL success is diagnostic only.
- E Root dispatcher `LabPgRecoveryLane.recover_once` delegates to **C only**: blob `69341dd3e3c726beacf74e07568f1e7f1a121b76`. Previous E stop-only implementation is OBSOLETE. E typed observer blob `dce2a878ab161dbecb25e9111f9176d49de99100`; revoker blob `5cff0321098c17f9241c58f974645cf76ff4dd14`.
- B four canonical runtime blobs remain FROZEN and independently pinned in `round14-cohort.json`, with SHA256 taken from B exact own test. No second SQL writer or unreviewed runtime change.

## Before F may update #166 with ANY mixed runtime files

1. **C stopped-ownership binding (P0):** `_STATES.get(pg) is None` must NOT authorize a STOPPED cluster. Require a C-owned, immutable saved stop operation ID and old postmaster exact retained OS identity plus data-root/owner marker, old backend PID+backend_start and old generation/token/owner/namespace. A stopped state from another Python object or after interpreter restart is UNKNOWN unless fresh physical Root/C attestation is independently reconstructed. Store snapshot keyed by canonical physical cluster identity rather than Python object.
2. **Cross-object physical exclusion (P0):** E `_RECOVERY_OWNERS.add(pg)` and C `_STATES[pg]` cannot prevent another `LabPostgres` instance addressing the same data directory. C must own one OS-backed / filesystem resource lock or equivalent process/cluster authority, with lifetime across worker timeout; E may use only C owner-issued identity/handle, never mirror another process-level supervisor or lock. No new restart while old worker could still act.
3. **A postmaster evidence (P0):** after C validates the original owner/PG18/executable/postmaster/data-dir, retain exact Windows HANDLE or Linux pidfd from A `RetainedOsProcessWait` BEFORE C performs C-owned stop; hold through wait-exited. A process snapshot or pidfile removal never proves extinction. Independent descendant/listener ownership + SCM evidence must be proved or UNKNOWN. C can reuse A primitive but must not create second OS observer.
4. **E authenticated proof (P0):** current E checks only `type(root_process_evidence) is RootProcessExtinction`; this class is not a sufficient authority. Root must verify issuer provenance, live original ownership, release/source, old generation/token/epoch, old handle PID+creation/image, exact PostgreSQL instance and time-of-use freshness. Freeze/copy typed immutable `old` and `streams` BEFORE threading; revalidate against C immutable readback in owner thread. No public dataclass bool, JSON or `quiesced=True` grant.
5. **B/E/C writer operation grant (P0):** B `CanonicalLabMinuteWriter` requires sync `native_admission.require_current() is True`, E sealed `LabWriterGrant` is async. B/C/E jointly implement one genuine, revocable **synchronous owner-thread operation validation** attached to one C SQL backend, owner+namespace+generation+fencing token+epoch+backend PID/start+executor+exact installed package+operation/content_id. Forbid asyncio.run inside poisoned SQL worker, fake True, second writer or SQL outside C `public.lab_fenced_insert`.
6. **Native proof (P0):** independent disposable PostgreSQL18/Windows process+listener and actual WAL interrupted-commit fault; immutable row, content_id/fingerprint, durable high-water/pending/checkpoint, stale generation/token rejection; exactly-once new Grid collector/journal/executor/backend, Math→Terminan chart/strategies; no live Bybit or user PG5432.

## Packaging and consolidation acceptance

One source-pinned package name/owner (`market-data`) and only Grid Bybit connection. Require pinned tree/blob SHA, four frozen B30 SHA256, verified builder, wheel + sdist bytes SHA256, unpack installed `RECORD` and import origin, CLI entrypoint, reproducible exact per-OS lock and vendor dependencies, Windows/Linux native runner results. F security scanner must scan full history, LFS pointer/object coverage, nested archives and built packages without revealing secret values. Existing AST group-count discrepancies **178 vs 174** and Grid↔Root **32 vs 31** must be reconciled at function+source-SHA level; retain all unique Strattester and Meta behavior until dynamic parity proof.

## Acceptance decision matrix

| Gate | Current source | Native receipt required | Verdict |
|---|---|---|---|
| A OS state | Implemented primitive | Exact parent+descendant+listener+SCM lifecycle | BLOCKED |
| C PostgreSQL | Serialized source | Bound stopped state+physical lock+retained postmaster+WAL | BLOCKED |
| E Root authority | C-delegating dispatcher | Nonforgeable old owner/epoch proof, immutable call args | BLOCKED |
| B writer | Frozen four files | Genuine in-thread operation grant, one SQL writer | BLOCKED |
| F release | Exact source pins only | Wheel/sdist/installed origin, CI+LFS+security | BLOCKED |
| D/Math | Separate, no second engine | Native data consumer and historical algorithm parity | BLOCKED |

**CODE NO_GO / PRODUCTION NO_GO.** No merge, no force push, no CI cancellations/retries, no user services/database/5432, no real trades, no Claude/Codex.