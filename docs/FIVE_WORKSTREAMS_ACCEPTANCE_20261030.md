# Five-module integration checkpoint — 2026-10-30

## Exact immutable source candidates (do not merge until verified)

| Workstream | PR | Source HEAD | Purpose |
|---|---|---|---|
| A | unified-system #5 | a291169355f4724aeb367a14babfc74205c32cda | node ledger, resources, lease/fencing, drain, backup planning |
| B | unified-system #7 | c42554a4244d4acc53165130faa8fe9e822a398e | durable lifecycle, observer barrier, retry/recovery |
| C | unified-system #8 | 501a382dbf0b257c6c1b8811b8168867f33e3eea | independent Strattester/Grid boundary |
| D | Terminan #50 | 6cfa160c0df2c812cae4d94d451e83d8446e0e1b | read-only fleet dashboard and Chromium controls |
| D | math #99 | 565d947d68c2adac7d59a3e9f44453543e13eebc | bounded independent math worker |
| E | unified-system #6 | abdf8adbcba39feac267593dfea4909568b5aa8d | offline dependency-lock and Windows security plan |

All Unified A/B/C/E branches have common base PR4 HEAD b8facc028e00493d8423d15280f87c2047c2b63b and their changed file paths do not overlap. This does NOT prove semantic/API compatibility. Terminan #50 and Math #99 depend on their own stacked branches and must not be cherry-picked without reviewing ancestry.

## Mandatory order and independent module operation

1. Unified read-only inventory -> owner-reviewed signed installation plan -> separately authorized physical provisioning and verification -> infrastructure admitted.
2. Terminan read-only UI may start once infrastructure is admitted, displaying node topology, database sizes, load, stage and provenance.
3. Unified requests Strattester history sync and research through a versioned idempotent API; Strattester independently verifies coverage and emits a sealed immutable completion receipt.
4. Unified validates exact source/owner receipts, dataset fingerprint, source/known-at times, and completeness before handing historical-only data to Grid.
5. Grid starts independently qualified live market-data collection. Historical data never becomes live L2; no trading/order authority follows.
6. Math research runs independently on allocated compute. Paper trading is a separate opt-in mode with isolated accounts and explicit permission.
7. The full system aims at continuous Grid collection with independently tested lease fencing, quorum, storage durability, backup/restore and failover.

Disconnected modules must remain usefully autonomous in their own safe modes. Unified-down means no new distributed assignments or infrastructure mutations.

## Integration gates

G0: source HEAD/tree pinned and diff inspected; no overlap is only a preliminary check.
G1: upstream exact-head tests and artifacts successful (not queued, cancelled or unqualified skips); validate original ZIP bytes and SHA256.
G2: combined disposable CI run with all four Unified workstreams imported on a clean branch, full Python/PowerShell regression and 0/1/5/6/7/10-node fleet matrix; no silent mocks substituting source producers.
G3: Terminan+Math interoperability, read-only API version negotiation, full Chromium interactions (refresh, search, filters, node selection, stale cancellation, stage progress) and data quality.
G4: external owner identity, quorum/fencing, replay-resistant trust policy, trusted release chain, source provenance and real exchange completeness.
G5: separately authorized physical read-only G0, then explicitly scoped infrastructure apply, rollback and recovery with approval.
G6: independent paper-trading qualification; live trading is NOT_AUTHORIZED.

## Current verdict

PLAN_ONLY accepted as a design/programming scope only. Hosted CI A/B/C/E/D: QUEUED/NOT ACCEPTED at capture. Locally reported 142 tests and one skip do not prove combined hosted acceptance. Physical NOT_RUN, source provenance BLOCKED, production NO_GO. No merge, node enrollments, actual Windows/SSH/Tailscale/ACL/service/PG mutations or exchange orders.

## Follow-up

Create a separate integration candidate only after exact-head CI and evidence arrive. Preserve originals. Independent review of lease semantics, authority boundaries, DNS/SSH/Tailscale identity, signed artifact pins, backups, programmatic topology, Terminan controls and Math compute cancellation is required.
