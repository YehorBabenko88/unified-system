# ROUND 15 — F integration contract: single recovery lifecycle

Date: 2026-11-26. **Integration PR #166 remains frozen** at `9349d7f3ed93ef82d120976816b968e0b716b067`. This document is a cross-owner acceptance contract, **not** executable recovery, OS proof, SQL authorization, or permission to merge.

## Ownership and exact source provenance

- A: `runtime_process.py` blob `b3ac50e176ab1fa7d139b6adb3006ab89a075548`, one `ProcessDriver.owned_process_state`. A #162 `f2a0245ae9edc2805e1e9be28e6c3a649ec401b4` adds tests only.
- C: `lab_pg_recovery.py` blob `8d717403233fed2047e6e0de3d93fd507d39b4b1`, C #163 `bbdc4e87b64a2516528270eb0c7925ce97d24ee5`. C exclusively owns LAB `LabPostgres`, SQL/WAL, restart, recovery and backend extinction.
- E: `lab_process_extinction.py` blob `dce2a878ab161dbecb25e9111f9176d49de99100`; `lab_pg_recovery_lane.py` blob `7cd73572e0018311fd0202c8c7bb8b1d1be5bfbc`, E #164 `c6bfff7e30d6b68bd23107edf3a9bf4098a00004`. E consumes A's tri-state, coordinates Root authority and ordering but does not own PG stop/start.
- B: #300 `2e5227e79023091a7481b540536f50a6b2e125fb`, four canonical Grid runtime blobs still B30 frozen; B alone owns collector and writer.
- D: #126 `80da873c5251a0505519249325a4591f8bb003d9`, canonical Terminan/PaperEngine, Math sole computation.
- F: #165 source-only qualification and the **sole** integrated #166 branch. This contract cannot be substituted for complete native evidence.

## Four concrete P0 failure modes confirmed by MASTER

1. In C `recover_exclusive_lab_cluster`, `pg._verify_owned`, `pg.started`, and `pg._verify_postmaster` are invoked BEFORE `type(pg) is LabPostgres`; validating a caller-supplied object after invoking its methods is unsafe.
2. C deadline starts after validation + SQL `_old_record`, and the remaining checks are only between potentially blocking `pg.sql`, `pg.stop`, `pg.start`; it is **not** a global deadline.
3. E's `stop_dedicated_cluster` leaves `pg.started=False`, while C requires started and an old backend `STILL_ALIVE`; E stop→C recover cannot run. C restart→E stop is also unsafe.
4. E `asyncio.wait_for(asyncio.shield(future), timeout)` returns from timeout while the executor thread can continue calling `pg.stop`; `shutdown(wait=False,cancel_futures=True)` does not terminate an already running thread. E's `_busy=False` in `finally` is NOT evidence of completion. The old worker must remain quarantined until actual completion and positive C/A OS evidence.

## Canonical serialization / authority matrix

One Root recovery operation per exact dedicated LAB owner identity. **C** owns one serializable lifecycle actuator for STARTED / PARTIALLY_STOPPED / STOPPED / UNKNOWN states; **E** submits one authorized recovery request and does not execute an independent stop/restart action. A must positively bind original postmaster incarnation and all descendants/listeners; stale pidfile, port-free and `alive()==False` do not prove extinction. The lane must be crash-safe and idempotent on repeated requests; old timed-out workers may never overlap with a new restart.

| Current state | Safe handling | New generation permitted? |
| --- | --- | --- |
| STARTED, old backend still alive | Revoke Grid scheduling/grants, retain Root/OS owner, C serial stop/recover | NO until full receipts |
| PARTIALLY_STOPPED after timeout | Quarantine old recovery worker, verify physical completion; then C resumes from durable journal | NO |
| STOPPED by previous E containment | C must accept precise STOPPED state under same owner/operation, must **not** demand old STILL_ALIVE SQL | NO until restarted + fresh readback |
| UNKNOWN worker/process/backend | Fail-closed, preserve owner custody; no concurrent retry | NO |
| RECOVERED SQL, no A OS/listener witness | Diagnostic only, no sealed receipts | NO |
| Fully recovered + verified A/C/E dual evidence + B ABI | Issue fresh epoch/generation/token and new backend/executor/journal/Grid, then D read-only | Conditional after native E2E |

## Required corrected protocol

1. C validates `type(pg) is LabPostgres`, major==18, exclusive owner marker, non-5432 port and exact cluster identity BEFORE any `pg` method access; never accept user-supplied `quiesced=True` as a Root grant.
2. E blocks new Grid commands, revokes trusted local admission, stops future executor submission, signals old Grid, and retains old OS/PG process handles and custody. UNKNOWN from A process witness remains denied.
3. Acquire one C-owned lifecycle operation lock with protected operation ID; timestamp deadline **before** potentially blocking I/O. All stop/start/SQL subprocess calls need bounded remaining-time enforcement, cancellation semantics and ongoing worker tracking. A timeout is UNKNOWN; leave lock/quarantine until terminal completion, not merely future cancellation.
4. E and C agree **one** orchestrated branch: E may request C stop-only containment; **the same C operation** must later recover from STOPPED using the same owner identity. E cannot separately invoke PG stop on a C-recovered cluster. Strict custody gates prevent simultaneous stop/start.
5. C on a fresh trusted session verifies SQL fence high-water, immutable rows, `content_id`, pending/checkpoint and unknown COMMIT before fresh admission. Never blind-replay. Retained old postmaster identity and backend PID+start must be independently proven extinct. PostgreSQL port 5432 and foreign data roots remain forbidden.
6. B/E/C resolve writer ABI without fake synchronous True: exact Root-minted, revocable same-executor and same-PG-backend proof, with one canonical `public.lab_fenced_insert`. Reject old generation/token/epoch and new clone of old collector or journal.
7. On all physical and durable proofs, E creates fresh generation/epoch/token; C provides **new** backend; E creates fresh executor, B creates fresh grant/journal/collector, Terminan reads canonical Math result. No old object may be rebound or reused.
8. Verify crash/restart, WAL, pending + checkpoint, lost ACK/unknown commit, 100,000-streaming trade conservation, long/short fee and spread equivalence, no duplicate writer/market client/PaperEngine, Windows+Linux and complete uninstall limited to disposable owner.

## Minimal native source cohort for subsequent approval

A #162 `f2a0245a` → E #164 `c6bfff7e` (A OS tri-state provider, E **consumer only**) → C #163 `bbdc4e87` (one PG lifecycle implementation) → B #300 `2e5227e7` (four frozen runtime files) → Math `9e6acbd9` → D #126 `80da873c`. F #165 security/packaging receipts; single #166 must be advanced only by F with MASTER approval, protected original blobs and full dependency/wheel/import/entrypoint checks.

The four defects above are **UNFIXED in these pinned owner sources**; ownership is clear, not native approval. **CODE NO_GO / PRODUCTION NO_GO.**
