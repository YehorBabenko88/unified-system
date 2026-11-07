# Phase 2 — isolated acceptance addendum

Observed UTC: 2026-11-06T15:36:17.757152+00:00.

**Overall NO-GO. PHYSICAL_FAULT_INJECTION=BLOCKED. PRODUCTION_DEPLOYMENT=NOT_AUTHORIZED. TAILSCALE_REMOVAL=BLOCKED.**

This addendum supersedes the initial report only for the newly executed component scenarios below. It does not convert any component PASS into full offline, CI, integration, physical or Tailscale-removal acceptance.

## Required status fields

- RELEASE_MANIFEST_STATUS: **BLOCKED**. PR22 is an audit baseline, not an approved installable release.
- NODE_INVENTORY_STATUS: **BLOCKED**. Current approved node inventory has not been supplied to this auditor.
- CONTRACT_STATUS: Five Git-blob reference hashes PASS at PR22 `34a2adf94b0e2170bf91f8641766e23481e269b2`; endpoint ACKs and mandatory-case registry approval pending. Ownership validator has a reproduced path-alias defect.
- OFFLINE_TESTS: Selected component suites PASS; full mandatory product coverage remains unqualified.
- WINDOWS_CI: **FAIL**. Original pinned-baseline Unified13 and Math110 check records include failing Windows jobs. Local Windows execution is not Windows CI.
- PHYSICAL_TESTS: **BLOCKED by explicit user instruction**.
- P0_P1_P2: **0 independently confirmed P0, 6 open P1, 2 open P2**. No claim that P0 is absent.
- GO_NO_GO: **NO-GO**.

## Executed suites and source identity

| Suite | Exact HEAD | Environment | Result | Evidence |
|---|---|---|---|---|
| Grid WAL/storage/coordination/Budget Anchor | `71084a336520187d6e260531a2f5d15555ba0e0c` | Windows Python3.12; temp data; non-loopback connect denied | 151 PASS, 0 skip | [JUnit](grid-offline.xml), [receipt](grid-run-receipt.json) |
| Network Budget Model/Store | `77e2958f4e50302225574caf1893a2f636a0d8e4` | Windows Python3.12; temporary stores | 94 PASS, 0 skip | [JUnit](budget/grid-offline.xml), [receipt](budget/grid-run-receipt.json) |
| Terminan cache/session/recovery | `7ed3708df53c8850fd11fc8331440bdfee99aa3e` | Windows Python3.12; temporary SQLite and loopback HTTP | 71 PASS, 0 skip | [log](terminan-tests.log), [receipt](terminan-receipt.json) |
| Integration registry regression | `34a2adf94b0e2170bf91f8641766e23481e269b2` | Local offline | 8 PASS; independent alias probes reveal defect | [regressions](registry-tests.log), [probe](coordination-probe.json) |

Grid, Budget and Terminan source trees were compared against their exact committed raw Git blobs before and after the successful suite. Dependency versions are recorded in [python-dependencies.txt](python-dependencies.txt); this locally resolved environment is not an approved release lock or an installed-wheel attestation.

Terminan tests include an actual killed synthetic SQLite writer and WAL recovery, stale lease token rejection, concurrent six-thread idempotent submission, incomplete history/duplicate data, stale/gap/disconnected book resnapshot, and loopback request-worker shutdown. R4 session receipts are synthetic lifecycle objects; real Windows operator-session expiry and distributed relocation remain NOT_RUN.

## Actual Windows loopback process test

Auditor-owned harness started three persistent Consul processes and a fourth independent restore target, all bound to 127.0.0.1 with scratch data directories. It imported Grid coordination/command code at `71084a336520187d6e260531a2f5d15555ba0e0c`. No service registration, firewall/VPN changes, real accounts or orders were used. Every process was stopped via its owned process handle and the scratch stores were retained.

With **Consul1.22.2 + BoltDB**, actual majority election, durable command/retry, synthetic denied-provider rejection, Raft leader crash and successor election, stale application-owner fencing, two-voter loss with UNKNOWN outcome, complete process restart retaining voter IDs and receipts, and snapshot backup/restore to a separate single-voter test cluster all passed. [Original process receipt](native-consul-boltdb/native-consul-receipt.json), [execution log](native-consul-boltdb-run.log).

The first fixture used the vendor default WAL backend and failed on every voter at startup: `fail to open write-ahead-log ... sync ...raft/wal: Access is denied`. [Failed receipt](native-consul/native-consul-receipt.json) and original process logs are retained. The fresh BoltDB run is a separate configuration/result; it does not erase the WAL failure. No existing raft directory was removed or migrated.

The binary ZIP digest matched the [official Consul1.22.2 checksum list](https://releases.hashicorp.com/consul/1.22.2/consul_1.22.2_SHA256SUMS); binary SHA-256 is in the receipt. The [vendor Raft configuration reference](https://developer.hashicorp.com/consul/docs/reference/agent/configuration-file/raft) documents the selectable storage backends. This fixture dependency differs from the pinned Linux CI image (Consul2.1.0); no cross-version release qualification is inferred.

This was loopback transport, not direct inter-node LAN. TLS/ACL and real human auth were disabled/unqualified in the synthetic lab. No local OS network partition was created, and no real disk was filled. WAL capacity BufferError is a logical disk-pressure simulation only.

## Original hosted Linux consensus evidence

Independently downloaded [run42088042386 / artifact13451546239](https://github.com/YehorBabenko88/bybit-cluster-grid/actions/runs/42088042386/artifacts/13451546239) for Grid exact HEAD `71084a336520187d6e260531a2f5d15555ba0e0c`, attempt1. ZIP SHA256 `1d4de71e26ffc1c958f31ebfd2f2e46bd6dd3bbd0e0afae4deb058d30cfb27a4` matches the original API digest.

Verified before/after source HEAD/tree, declared member hashes, pinned fixture-lock hash, all96 non-skipped JUnit identities against independent local source collection, and all20 required scenario names/counts including real three-voter restart, one-versus-two network partition, minority denial/majority commit, heal and budget-anchor CAS. Reviewed source invokes Docker kill/disconnect/connect on owned isolated containers. [Independent review receipt](hosted-consensus-review.json).

This is PASS for **review of original HOSTED_LINUX evidence**, not a new local Linux execution. Docker is unavailable locally. The artifact explicitly says budget_store_integration=NOT_WIRED and snapshot/backup restore NOT_RUN. The local Windows restore experiment above remains a separate evidence level and dependency configuration.

## New defect A8-F08 — P2 — ownership path aliases

PR22 exact module `unified_system/integration_registry.py` compares case-sensitive, unnormalized strings. Add to A2.allowed_files any of `UNIFIED_SYSTEM/LAN_TRANSPORT.PY`, `unified_system/../unified_system/contracts.py`, or `unified_system\contracts.py`: verify_ownership returns True, despite aliases of A1 or ROOT-reserved Windows paths. The original ownership document passes and all five referenced Git-blob hashes match; the defect is in path validation rather than stale hashes.

Expected: reject noncanonical repository-relative paths and Windows case aliases before overlap checks. Actual: all three probes accepted. [Reproduction output](coordination-probe.json); [auditor probe](../coordination_review_probe.py). Runtime is unwired/BLOCKED, so no runtime privilege bypass is asserted. Reproducer and required correction were sent directly to Integration Owner. A7 still references comparative PR111 while the new assignment calls for remediation from110/70/76; A8 checkout path is work/unified-audit, not the planned work/unified-system.

A8 ACKs only its own audit-doc scope in principle. Global ownership validator and mandatory CI registry ACK are withheld until corrections and exact workflow/case/platform/run-attempt/skip mapping are independently verified.

## Retained unsuccessful audit attempts

The first Grid attempt lacked pydantic-settings. The second had an auditor socket guard that blocked Windows asyncio self-pipe connections and invalidated async results. The third lacked FastAPI. The first Terminan attempt omitted the tests directory from the import search path. These environment/harness failures are retained in labeled subdirectories and are not reported as product failures or silently converted to PASS. Successful reruns used unchanged product source.

## Next actions

Integration Owner was asked for one approved release-manifest.json, integration-baseline.json, ownership-registry.json, node-inventory.json, authority-fencing-v1, assignment-v1, storage-publication-v1, terminan-control-api-v1, CI/evidence index and rollback plan. Existing documents are not assumed approved. Recheck Agent7 remediation Drafts when exact SHAs arrive; independently review the ownership fix and mandatory registry; keep physical and Tailscale-removal gates BLOCKED.
