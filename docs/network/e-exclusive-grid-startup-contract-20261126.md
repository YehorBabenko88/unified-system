# E — Root-owned exclusive Grid startup, lease and release architecture

Date: 2026-11-26. Scope: design/verification contract only. CODE/PRODUCTION NO_GO.

## Ownership boundary

- Root Unified System: **only** process/service supervisor, boot/start/stop, registration, immutable installation, Consul control authority, host-state validation and updater/uninstaller.
- Grid: **only** Bybit REST/WS, bounded catch-up, canonical live ingestion, market-data migrations and data writer. A single installed Grid artifact/cohort is chosen at source admission.
- C-owned PostgreSQL lifecycle: isolated PostgreSQL 18 boot, schema admission, role separation and **resource-side fencing** of market-data writes.
- Math and Terminan: computation and consumer UI, not a competing writer or lease service.
- Deprecated `grid/worker.py`, `grid/market_backfill.py` and legacy service entrypoints stay physically present during migration but **must not be active** alongside canonical market_data. Only Agent B can alter them after parity is established.

## Existing authority reuse, not a second election

At Root candidate `f05f9a73581b1c15c4cc78da2801c9f2f5dd08d0`, `unified_system.consul_authority.ConsulSessionAuthority` is the single Root Consul session transport with one `{namespace}/leader` key and monotone ModifyIndex fencing token. The current `validate(lease)` and `renew(lease)` are time/Consul checks, not resource-side fencing; they cannot prevent a stale Grid writer from continuing to send data.

Use this **existing** authority. No second Consul client in Grid, Math or Terminan, no different lock namespace silently accepted as leadership, no independent Root command queue. The lease is necessary but insufficient for start.

## Startup state machine (proposal for B/C contract review)

`NOT_ADMITTED -> ROOT_CONTROL_HELD -> HOST_QUIESCENT -> RESOURCE_FENCED -> SOURCE_ADMITTED -> RUNNING -> DRAINING -> QUIESCENT`

Mandatory checks before `RUNNING`:

1. Root service grant remains current and source-pinned (exact installed Grid wheel bytes/source SHA, process/executable identity, immutable manifest and expected node incarnation).
2. Root Consul control lease owner/session/token and current generation are valid; no UNKNOWN/indeterminate result, stale token or reused identity.
3. Native process and service inventory proves **all** legacy writer and Bybit worker entrypoints quiescent on each participating host, with no child processes or untracked fallback launcher. The observer must fail closed when any process metadata is inaccessible or ambiguous.
4. C-controlled PostgreSQL resource-side writer exclusion is obtained **atomically** for the canonical writer identity and schema generation. Token is fenced at the *write transaction*, not merely at process boot. Startup must reject a legacy role that could still write the same canonical target. Do not use a simple JSON receipt as grant; require verified native authority and DB-side enforcement.
5. B-identified canonical Grid executable/wheel/transport is the only writer admitted; no simultaneous legacy WS, REST backfill, shadow worker or second WebSocket transport.
6. Activation passes the same Root-controlled service and network deployment guards. A failed check leaves zero new child processes, with a refusal receipt not containing passwords, keys or data payloads.

Root must not fabricate any of checks 3–4 from comments, fake receipts, historical CI, non-current cached process listings or an unverified user-supplied PID. C and B must agree on a versioned exact DTO plus positive/negative evidence before implementing the real startup wiring.

## Failure and recovery rules

- Lease lost, timeout, inconsistent read, invalid certificate or native inventory UNKNOWN -> deny new starts, fence future writes, publish unready; never keep reporting CONNECTED.
- Old worker still alive or failed-to-stop -> new canonical startup DENIED. Never forcibly kill arbitrary PIDs to make admission green.
- New writer crashes -> PostgreSQL releases process-bound lock only after verified process/connection termination; stale fence generation rejected on restart.
- Consul communication outage -> do not promote another controller merely from local timeout. Existing processes need explicit ongoing resource-side fencing and bounded containment; no claim of safe failover without independent native test.
- Upgrade -> drain old writer, persist checkpoint/replay bound, verify process quiescence and writer-fence release, admit new pinned artifact and generation, then run negative duplicate/partial-restoration tests.
- Rollback -> only an explicitly vetted old artifact/source+schema pair may be admitted after previous canonical writer has demonstrably quiesced; no UNKNOWN-to-success or unverified DB downgrade.
- No resource-side writer fence exists yet; therefore deployment is **DENIED**, not temporarily admitted.

## E / B / C integration deliverables

**B:** exact canonical Grid `market_data` runnable path, source/wheel digest, transport ownership, versioned provenance DTO, canonical tables and legacy writer deny-list. B owns all Grid code and canonical market writes.

**C:** single DB writer identity, ownership namespace, resource-side lease/fence contract and deterministic negative tests for cross-process duplicate starts, stale fencing token, crash/restart, role bypass, migration drift, UNKNOWN and orphaned connections. C owns PostgreSQL LAB and real schema changes.

**E:** existing Root supervisor/Consul authority wiring only after above contract is agreed; fail-closed host quiescence and versioned service activation gate. No new independent supervisor, installation stack, Consul cluster or bybit transport. E owns actual no-overlap process/lifecycle tests within a separate gpt/ branch and must coordinate file ownership with A.

## Single installer architecture (planning only)

Reuse `unified_system/installer_security.py`, `installation_transaction.py`, `service_bootstrap.py`, `service_activation.py` and `supervisor_deployment.py`. One immutable signed/pinned capsule contains Root runtime and canonical Grid/Math/Terminan wheels; component metadata are checked before any child creation. An installer performs PLAN -> SOURCE/OWNER/PLATFORM/ACL VERIFY -> QUIESCE -> FENCE -> STAGE -> ACTIVATE -> HEALTH -> COMMIT or explicit verified ROLLBACK. This is not a call to install now.

Protected native credential storage and existing PG are never overwritten or adopted. Uninstall requires explicit ownership, confirmed shutdown, exact scope and user authorization; no broad cleanup or deletion of unrelated databases/files. Multi-node rollout is sequential with no cross-host concurrent writer promotion. Unsigned, substituted or unpinned artifacts fail closed.

## Acceptance matrix (not yet run)

| Case | Required behavior |
| --- | --- |
| Consul lease lost or stale fence | DENY new Grid start and future writes |
| Two simultaneous canonical writers | Exactly one can hold resource-side fence; other DENIED |
| Legacy Grid worker still alive | DENY new canonical writer, preserve old process evidence |
| Unreachable/inconclusive host observer | DENY; never infer quiescence from timeout |
| Migrated schema/role mismatch | DENY before process launch or market-data writes |
| PostgreSQL crash/restart | Verified stale connection cleanup, no parallel writer promotion |
| Invalid Grid artifact hash/identity | DENY before touching services or database |
| Network/mTLS partition | DENY unsafe promotion; preserve evidence |
| Successful planned handoff | Single writer, exact provenance and native process evidence |
| Installer rollback/uninstall | Full owned-scope proof; unrelated user data untouched |

No native OS/network/Consul/PG service has been started or modified by this review. A's PowerShell and C's PostgreSQL LAB code were not touched. Physical six-node acceptance and production admission are pending.
