# G — Physical acceptance and release readiness

Fresh six-node read-only observation is archived in six-node-stage0.json; all five pinned LAN SSH connections returned observations. This is not full Stage0 or Windows qualification PASS. Known candidate runtime file versions are not exhaustive installed-runtime qualification. No node, policy, service, firewall, network, key or trust store was changed.

| Stage | Scope / approximate time | Gate and recovery |
|---|---|---|
| 0 | LS5 inventory, permissions, ports, backup planning; 15–30 min | ACL currently rejects untrusted writable installation root; PLAN_ONLY rejects provisional lock; fix package and recheck, no security weakening |
| 1 | Isolated exact-artifact installer/security test; 20–40 min | Source/manifest/hash/dependency/native gates; no install if denied |
| 2 | Gated LS5 paper pilot; 30–60 min | Approved directory and rollback package; stop only current deployment on degradation |
| 3 | Sequential PC4 → PC3 → PC2; 20–40 min each | Separate node admission, preserve existing data/services and recovery access |
| 4 | PC1 then LS7 Home; 30–60 min each | All 14 Home criteria independently NOT_RUN until executed |
| 5 | Ten-instrument history/live paper; 10 min live minimum | Provider sends remain BLOCKED pending separately admitted quota/time/NAT/authority policy |
| 6 | Backup/restore/restart/failover/rollback and soak | Isolated fault tests first; office fault injection requires separate owner authorization |

Times are planning estimates, not measurements or commitments. No executable current installation package is admitted. Recovery plan must identify exact prior artifact and verified backup before any update; current backup administrator access has not been demonstrated end-to-end. Existing service presence is not that proof. Tailscale stays retained; removal BLOCKED. No automatic DNS, network-service, adapter, router, firewall or Tailscale reset.

TRUSTED_RELEASE=BLOCKED_NO_TRUSTED_PUBLISHER. LAB unsigned is allowed only after all integrity and runtime security gates. Production deployment and main merge remain unauthorized. PHYSICAL_ACCEPTANCE=BLOCKED/NO-GO.
