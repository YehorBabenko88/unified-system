# Phase68 — independent integrated LAN MUX review

Requirement IDs A8-HEAD, A8-LAN, A8-AUTH-NEGATIVE, A8-BUDGET, A8-RECONNECT, A8-WINDOWS-CI. Repository unified-system, Draft https://github.com/YehorBabenko88/unified-system/pull/26.
Exact executed HEAD8bfa00d779438dc204b1e9ee82f496efce9e6154/tree58753c6c902afa9fe24e65480a197ae9470defc7. Source integration89932fec1821d956b9dfd0ab0011d732c5b96369/tree093b01c68b4131172169da359787af9de5bd886c.
Environment own detached no-hardlinks raw-LF clone, local Windows/Python3.12.10/OpenSSL ephemeral CA and own loopback TLS processes/temporary SQLite only. No host trust-store or network-policy changes, office hosts, provider sends or real orders.

| Test | Expected | Actual | Evidence | Status | Severity / correction |
|---|---|---|---|---|---|
| Exact composition |4owner blobs exact, budget/TLS fixture unchanged |9680babc/89932fec/8bfa four raw blobs equal;1318primary object OIDs recomputed and physical raw equal |primary-composition-verification.json |PASS |component scope only |
| Actual workflow file with Windows main guard |50 exact tests, zero skip, clean pre/post |50PASS/0skip/1318raw |workflow50.original.json; workflow50.stderr.log |PASS |local Windows, not hosted |
| Original causal race reproduction |old HASH cause replaced by CLOSED |new Event-gated actual TLS regression against primaryacf4 source loaded in memory: expected1failure,0error; fixed test PASS in50 |primary-old-regression.stderr.log; primary-old-regression-executed.py |PASS |old code not deployed/changed |
| Closed factories/self node |reject before socket side effects |2additional tests PASS, native transport/MUX factories reject and self-connect leaves empty connection/memory state |extra.stderr.log; extra-executed.py |PASS |does not supply native identity |
| Quota/unknown send/no automatic replay |shared debit blocks writes; partial send UNKNOWN once; reconnect not replay |actual named tests PASS within50, explicit completed replay separately charged |workflow50.stderr.log |PASS |transport not logical exactly-once or admission authority |
| Original indexed evidence |13raw members match length/SHA, driver matches workflow |13verified, RED/import/spawn errors retained as original owner records |owner-evidence-index.original.json; owner-* |PASS |owner execution not A8 evidence substitute |
| Windows/Ubuntu hosted matrix |terminal successful jobs and artifacts |42368972590/42368967965 attempt1queued/null |ci.original.json |BLOCKED |P1 acceptance gate: obtain original terminal jobs/artifacts |
| Physical/Tailscale removal/native B |separate installed release admission |not exercised |current-acceptance-status.json |BLOCKED |native factory remains closed; no office acceptance |

50includes deterministic regression, no additive count for repeated tests. New extra2 are separate. Workflow guards remain scoped/site-enabled; no global environment-authenticity/F16/F17 closure. All owned loopback transport/reader/process fixtures stop through test teardown. Overall NO-GO, Tailscale removal BLOCKED/NO-GO.
