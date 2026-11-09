# PR66 independent focused TLS acceptance

Exact HEAD `4e297c264e1c81d1cdb3bbb8161c281b76bb0613`, tree `30293721b3eef8f0d0c65f8020ff4a15dc1f467f`. Source review confirmed one changed test file relative to b144; production transport is unchanged.

| Requirement ID | Repository / PR | Test | Environment | Expected | Actual / status | Evidence | Severity / correction |
|---|---|---|---|---|---|---|---|
| A8-F26-CANDIDATE | unified-system / PR66, exact HEAD above | active heartbeat renewal; inactive predicate closure | Windows, CPython 3.12.10, own loopback TLS, ephemeral certificates and SQLite | Both cases pass under 600 ms delay of own heartbeat startup | 2 unique PASS, 0 skip | [Executed harness](executed.py), [original stderr](stderr.log), [receipt and raw source maps](receipt.json) | Candidate verification only; Root must preserve existing IDs and qualify exact mandatory 145-case hosted matrix |
| A8-F26-HOSTED | unified-system / PR66 | Mandatory CI | Hosted runners | All required jobs and artifacts pass at exact release HEAD | NOT_RUN in this phase; existing b144 failure remains OPEN | Prior phase122 original logs | P1, same existing F26; no new defect count |

The positive test seeds stale last_rx, gates on actual control-reader reentry after heartbeat handling, and retains the real idle predicate while expiring the old data-read deadline. Both renewals were true and bidirectional real TLS payloads arrived. The added negative injects on_idle=False; it verifies real TLS closure on an expired deadline, not naturally elapsed peer inactivity. The additional 600 ms delay is a controlled experiment and does not establish the original hosted runner cause.

All 1587 primary source files matched Git raw bytes before and after; no extra files were present. The interpreter used -I -S -B. No full 52/145-case suite or historical RED was replayed. Owner counts are not A8 counts.

RELEASE_MANIFEST_STATUS: not approved by this focused check.
NODE_INVENTORY_STATUS: not requalified.
CONTRACT_STATUS: no production contract changed.
OFFLINE_TESTS: focused 2 PASS, 0 skip.
WINDOWS_CI: candidate NOT_RUN; mandatory F26 remains open.
PHYSICAL_TESTS: BLOCKED.
P0_P1_P2: 7 open P1 / 3 P2 unchanged; absence of P0 not proven.
EVIDENCE: original logs, executed harness and exact raw maps linked above.
NEXT_ACTIONS: Root owns mandatory inventory and hosted qualification. PR64 and PR65 remain pending independent review; no acceptance transferred.
GO_NO_GO: NO-GO. TAILSCALE_REMOVAL: BLOCKED.
