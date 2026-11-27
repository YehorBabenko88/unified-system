# Agent I — disposable → physical PC acceptance checklist

**No commands in this document authorize installing on real hardware.** Each step requires release cohort lock, separately approved operator change record and independently auditable receipts. Keep CODE NO_GO / PRODUCTION NO_GO until signed off by MASTER, A/C/E/F/J.

| ID | Gate / operation | Evidence required | Initial |
| --- | --- | --- | --- |
| I-01 | Pin Unified/Grid/Math/Terminan commit/tree/wheel hash, signatures, SBOM | immutable J manifest and F review | NOT_RUN |
| I-02 | Windows 11 / Windows Server test matrix, exact OS editions, Python ABI | A original runner logs and physical receipt | NOT_RUN |
| I-03 | Verify local admin approval, no UAC bypass, isolated LocalService ACL | interactive/manual recorded owner approval | NOT_RUN |
| I-04 | Check paths/namespace ownership, private ACL, disk/CPU/RAM, no collisions | preflight receipts; immutable before snapshot | NOT_RUN |
| I-05 | Check existing PG 5432 remains untouched; dedicated C PG port/data root | exact before/after port and service inventory | NOT_RUN |
| I-06 | Verify Consul trust, mTLS identity, KV lease and allowed ports | E + F signed source/freshness receipts | NOT_RUN |
| I-07 | Validate offline artifact hashes AND publisher authenticity | J/F signed provenance | NOT_RUN |
| I-08 | Dry-run installation, assert zero effects and zero user data changes | deterministic diff and test receipts | NOT_RUN |
| I-09 | Install in disposable Windows host; verify scoped isolated service/DB | original event logs, SCM/PG receipts, hashes | NOT_RUN |
| I-10 | Start/stop/restart with actual protected Windows Job extinction | A independent original native evidence | NOT_RUN |
| I-11 | Force termination/reboot; no orphan descendants/listeners, no unsafe auto-resume | A/C/E crash evidence | NOT_RUN |
| I-12 | Real Consul expiry inside PostgreSQL COMMIT; no second writer | E/C/B persisted SQL + consistent KV evidence | NOT_RUN |
| I-13 | Unknown outcome/lost SQL response: reconcile four exact identifiers | C/E negative and durable receipts | NOT_RUN |
| I-14 | Run bounded read-only per-node health and stale/partition status | sources and freshness, no authority inference | NOT_RUN |
| I-15 | Verify alerts sanitized, bounded and authenticated | redacted alert test and failure receipts | NOT_RUN |
| I-16 | Offline backup, restore into isolated non-prod cluster; PITR chain | C exact checkpoint/WAL/hash acceptance | NOT_RUN |
| I-17 | Upgrade same signed cohort / rollback failed code activation | old/new immutable manifests and no stale lease reuse | NOT_RUN |
| I-18 | Install/upgrade interrupted at every durable phase | no blind replay; UNKNOWN preserved; manual reconcile | NOT_RUN |
| I-19 | Dry-run uninstall, then isolated APP_ONLY removal; preserve data/backup | matched ownership/service-absence receipts | NOT_RUN |
| I-20 | Confirm unrelated services, AV, firewall, UAC, networking, PG5432 unchanged | before/after inventories with exact diffs | NOT_RUN |
| I-21 | Repeat on each supported PC role and 6-PC controlled failover | per-node independent evidence/no dual owner | NOT_RUN |
| I-22 | F independent adversarial security review + J exact cohort attestation | all blockers resolved, MASTER explicit GO | NOT_RUN |

Mandatory score vocabulary: **PASS / FAIL / SKIP / NOT_RUN**. SKIP requires explicit scope reason and cannot satisfy a mandatory production gate. Any contradictory or stale receipt yields FAIL/UNKNOWN, never optimistic PASS.

Stop immediately on service identity mismatch, mutable state ambiguity, untrusted publisher, expired/ambiguous Consul lease, uncertain SQL commit, unsupported Windows loader result, unresolved database ownership, or incomplete backup; preserve logs and manually reconcile. Never change AV, firewall, router, UAC or PG 5432 to make a test pass.

Suggested evidence directory per execution (outside source checkout): `I-acceptance/<UTC-run-id>/manifest.json`, `host-preflight.json`, `original-logs/`, `service-identity.json`, `pg-fence.json`, `consul-kv.json`, `test-results.json`, `independent-review.json`. Encrypt restricted artifacts; publish only sanitized hashes and outcomes. Do not claim to have produced them without actually executing the tests.
