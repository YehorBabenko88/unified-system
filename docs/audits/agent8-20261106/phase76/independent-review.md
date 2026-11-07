# Phase76 — Node Supervisor840 independent review and WAL resource-bound defect

Requirement IDs A8-HEAD, A8-NODE-SCOPE, A8-JOURNAL-NEGATIVE, A8-RESOURCE-BOUND, A8-WINDOWS-CI. Repository unified-system; Draft https://github.com/YehorBabenko88/unified-system/pull/38.
Exact HEAD840511a8567e8b016733d7dc2566d7890dff39b9/tree5529a7fe006f430ec11a72791ecca37bd2e94544; sixNEWpaths vs49a970270570548e5d4f0c5a440d30e238bb21f1. No existing production module edits.
Environment own fresh detached no-hardlinks raw-LF clone, local Windows/Python3.12.10 -I-S-B, own synthetic SQLite files/new temporary roots only. No native/service/office/network/provider effects. Existing Journal reused as typed OBSERVING receipt engine, not consensus or admission.

| Test | Expected | Actual | Evidence | Status | Severity / correction |
|---|---|---|---|---|---|
| Actual committed workflow |30mandatory, fullraw/inventory prepost |30PASS/0skip/1327primaryraw blobs checked incl recomputedGitOID |receipt.json; source-before.json; tests.log |PASS |local scoped tests only |
| PC1 vsLS5 and foreign cluster/incarnation |constructors reject without mutation |6own refusals, originalPC1taskCREATED and DBbytes unchanged |scope.stdout.json; scope-executed.py |PASS |scope fix verified at840only |
| Corrupt/foreign/idempotent/restart/no-effect |strict typed journal, no blind execution replay |named mandatory tests PASS; RUNNING/VERIFYING restart UNKNOWN, no actual native effects |tests.log |PASS |lifecycleAUTHORIZED is label only |
| Symlink vector |actual symlink fixture must be available |test reports SYMLINK_CREATION_UNAVAILABLE on this host and returns; zero unittest skips does not prove symlink path |workflow30.stdout.log |NOT_RUN |no waiver or actual symlink acceptance claim |
| max_bytes including SQLite state |do not accept beyond configured journal budget |max65536 accepted20creates/snapshot20 while main8192+WAL115392+SHM32768=156352 |wal-budget.stdout.json; wal-budget-executed.py |FAIL |P2 A8-F19: refuse WAL/SHM/nonapproved mode or enforce full bounded accounting before all reads/writes; add held-reader regression |
| Public operations/native |only readonly local receipt status/health;11others PLAN_ONLY |30tests and source show unavailable native effects, no SCM/provider/dispatch |tests.log; exact modules |PASS |no real health/source/fencing/grant proven |
| Hosted Windows/Ubuntu |terminal exact mandatory jobs/artifacts |primary snapshot saved, no terminal PASS asserted |ci.original.json |BLOCKED |P1 gate, local Windows is separate |
| Physical/Home/native |approved installed release and actual checks |not exercised |receipt.json |NOT_RUN |physical/native/installation remainblocked |

WALreproduction uses one writer (normal Journal methods) plus a held SQLite READtransaction in own test root. It changes no host policy. It proves resource-accounting omission, not native identity or authority bypass. Closing reader can checkpoint; first no-held-reader exploration did not exceed budget and its failed probe assertion/code are retained separately as audit exploration, not product failure/waiver. Reproduction DB retained outside evidence bundle, no userdatabase modified.

Finding handed to Root and A1 for owning-agent routing; A8 did not edit implementation. Candidate resource-bound acceptance HOLD pending exact owner correction. New open counts6P1/4P2; confirmedimplementationP0 remains0 with no absenceproof. Overall NO-GO, Tailscale removal BLOCKED/NO-GO. Earlier b6 scope defect is owner-reported historical; own840scope refusal is fresh independent evidence.
