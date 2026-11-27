# Agent I — Round 26 deployment audit and release gate

Status: **CODE NO_GO / PRODUCTION NO_GO**. This document is a source audit and a non-executing operator plan, not authorization to deploy. Based on A HEAD `ad7efedb0cae0893ca1c6ba1c76c9335b507bb6b` and MASTER #111 comment 7215159570 (2026-11-27). C/E/B versions and native gates are not qualified.

## Source inventory (pinned A tree)

| Surface | Current implementation | Deployment decision |
| --- | --- | --- |
| `unified_system/installer.py`, `docs/INSTALLATION.md` | lockfile validator and DRY_RUN_ONLY report | Reuse as dry-run; **not** an executable installer |
| `installation_transaction.py` | capsule verification, identity-scoped staging and journal; activation BLOCKED | Reuse unchanged; no automatic activation |
| `installation_service.py`, `service_activation.py`, `service_actuator.py`, `service_entry.py` | owner-bound service resource contracts | Owner A/C/E must review native bindings |
| `scripts/UnifiedOwnedService.psm1` | bounded native stopped-service interface, LocalService | Native tests still red/unknown on Server 2022 |
| `installation_uninstall.py`, `scripts/UnifiedOwnedServiceRemoval.psm1` | APP_ONLY separately receipted stopped service and code removal | Not a full host-data purge; mutable state retained |
| `service_postgres.py` | scoped owned PostgreSQL planning; separate data root and owner | Agent C alone approves DB life cycle |
| `node_supervisor_v2.py`, `docs/operations/node-supervisor-v2.md` | local journal receipt observer, effects_authorized=False | Reuse; not a second process or fleet supervisor |
| `supervisor_deployment.py` | deployment preparation model | No native deploy authority |
| `docs/RECOVERY.md` and `acceptance/20261106/rollback-plan.md` | fail-closed unknown outcome and preparation-only rollback | No executable fleet rollback |

**Do not retire any of these without Agent G's path-by-path migration ledger.** Source integrity and mocked tests do not imply publisher trust, protected Windows viability, or installed wheel provenance.

## Release ownership and control boundaries

- Unified System: only lifecycle, service ownership, installer, release coordination and supervisor contracts.
- Grid: only Bybit transport and canonical market writer. No second Grid-facing ingestion/writer in operations.
- Math: computation only; Terminan: UI/consumer only; do not install duplicate runtime authorities.
- C PostgreSQL owns dedicated instance lifecycle and durable fence; E owns Consul acquisition/renewal/fail-closed handoff; A owns Windows Job/SCM process-tree extinction; F independent security review; J cohort manifest and signed artifact handoff. G approves any removal.
- Node monitor is **observation only**. Read-only health cannot mint a lease, reassign the owner, restart a fenced writer or authorize a deployment.
- An update cannot activate a new writer until the old backend identity and process tree are extinguished, the precise C fence is durably revoked, Consul identity is checked, and the protected issuer grants a fresh generation.
- On timeout, unknown COMMIT, uncertain revoke, missing lease proof, ambiguous service or hash mismatch: BLOCK; preserve evidence; no auto-retry/promotion.

## Dependencies to inventory and pin before installer activation

| Category | Required offline/preflight proof |
| --- | --- |
| Host | supported Windows build/edition, architecture, physical/virtual status, required rights and UAC prompt; no UAC bypass |
| Runtime | exact CPython and wheel ABI, signed binary inventory, VC runtime if actual package depends on it, all transitive dependencies and hashes |
| Database | separate owned PostgreSQL 18 distribution, service, dedicated data root, free port **not 5432**, ownership/fence SQL protocol, backup PITR proof |
| Coordination | Consul actual version and issuer identity; mutual TLS and authenticated peer enrollment; no invented bootstrap quorum |
| Storage | private ACL, disk headroom, per-release code/state/checkpoint/log/backup roots, protected journal, capacity, backup media |
| Network | explicit per-role inbound/outbound ports, mTLS names, DNS resolution, supported offline/local install; no firewall/AV/Tailscale modifications by installer |
| Trust | approved publisher, verifiable signature and pinned immutable multi-repo manifest; SHA256 equality alone is not publisher trust |
| Operations | stable service identity, desired start/stop order, documented health evidence freshness, log retention, approved alert sink, rollback compatibility matrix |

No default credentials, secrets in bundles/logs, hardcoded node IP, implicit download from latest GitHub, silent elevation, or use of PG 5432.

## Proposed isolated artifact and lifecycle (not implemented)

1. J packages pinned **immutable** cohort: Unified/Grid/Math/Terminan exact HEAD, original dependencies, provenance, hashes, trust signature, SBOM and content-closed manifest.
2. I validates signature/policy, host/edition/space/ports/ACL/service conflicts and owner-written admission contract; unsupported system or missing evidence is a hard stop.
3. Only with explicit operator approval, stage into a fresh private version directory and persist exclusive intent; never overwrite or adopt a pre-existing resource.
4. Existing Unified lifecycle creates services and dedicated C-owned PostgreSQL resource with verified owner receipt. No second process supervisor or DB owner.
5. Activation runs through existing Root/Consul/SQL/Windows Job gates; no read-only health or local journal state counts as authorization.
6. Release handoff is code-only until schema compatibility, data-preserving migrations, C backup/restore qualification and full generation fencing are independently certified.
7. On incomplete install: mark UNKNOWN/BLOCKED and preserve state; compensation may remove **only** known inactive, uniquely owned application code after owner review. No unconditional recursive deletes.
8. Uninstall defaults to dry-run inventory. Require exact owner receipt, stopped process-tree evidence, no active writer/leases and explicit per-resource approval. Data and backups are retained by default; user-data purge is a separate manual, irreversible approval and is NOT included in this work.
9. Upgrade: stage new code alongside old; signed manifest + schema-compatible dry-run + backup proof; stop/fence old; admit new; verify health; commit activation. Failed code activation may restore prior immutable code **without** resetting authority generation or old lease; DB rollback/recovery is separately C-owned.
10. Alerts: bounded sanitized event type/node ID/release ID and timestamps; no raw credentials, patient/PII, SQL DSNs or network reset/recovery actions. Offline spool must be bounded.

## Deployment roles (proposal; requires owner approval)

CONTROL: existing Unified coordination and observable fleet state; never a second authority.
WORKER: Grid ingestion on designated single admitted writer only, per-node bounded compute workers; Math computation services as separately approved.
UI: Terminan gateway consumer; may be colocated with CONTROL when resources allow.
STANDBY: cold worker/DB recovery candidate; remains non-writer until durable old-owner revoke and new fencing generation. No optimistic promotion.

A six-PC assignment is **NOT_RUN** pending exact hardware/resources/network/roles; do not hardcode machine-specific hostnames or invent redundant primary status.

## External owner handoffs / blocking questions

- **A**: original Win2022 native jobs currently 3 × 168 PASS / 6 FAIL / 2 SKIP; demonstrate full service/child/process-tree extinction and SCM status on supported editions.
- **C**: explicit dedicated PG port !=5432, cluster ownership, correct Consul session SQL ABI, consistent unknown-COMMIT fencing, physical backup/PITR restore and cleanup quarantine.
- **E**: exact acquired Consul session, consistent KV identity, TTL expiry during old COMMIT, no two active writers; blocked uncertain release.
- **F**: publisher trust, full-history secrets/dependencies, protected installed binary gate and adversarial failover review.
- **G**: complete legacy installer/supervisor duplicate ledger, replacement and regressions before deletion.
- **J**: exact SHA cohort, multi-repo signed immutable build, provenance, SBOM, receipts, release artifacts, evidence and gate board.

All gates remain **NOT_RUN or FAIL** unless linked to exact original evidence. No real computers touched.
