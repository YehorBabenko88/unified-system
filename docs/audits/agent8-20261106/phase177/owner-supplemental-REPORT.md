# F26 committed test-only qualification

HEAD ab9362706cd8cd75b2fc0f5177481a96a5f73ac4
Tree cfa80d600603d947e79304e075d48787c116a8a1
Two files committed, no push. Base 6e79f2da66212474e9875559ec532c0f65b678a8.

Exactly three sequential owned-process runs, no retry, total 35.750 seconds.
P: active heartbeat case PASS, 3.250 seconds; same requested extra 50 ms under own fixture RLock before original transaction exit, FULL and original deadlines.
M: same active case, same cost, actual data on_idle=False mutant invoked once. ERROR at first renewed.get(timeout=3), _queue.Empty; zero successful application sends. ORACLE_INCONCLUSIVE: mutation wrapper replaces callback before the test's renewal-queue observer can receive its value. This is NOT a proven causal renewal assertion rejection and NOT an oracle PASS. No retry or mutation shipped.
N: unchanged expired-idle real TLS negative PASS, 0.953 seconds, no extra service cost.

Each process had fresh fixture certificates/stores; actual production heartbeat method was never replaced. Fresh LF no-hardlink source clone matched all primary Git blob bytes before/after and contained no extras/bytecode. All owned threads and processes retired. No production/helper/Mux/security/deadline/budget changes. No physical/provider/native/protected actions.

Runner metadata caveat: inherited descriptive fields initial_seconds/periodic_seconds and simulation/code_fix text are generic labels from the earlier runner, not independently observed scheduling. Actual cadence comes from committed test and untouched production heartbeat method: P/M fast readiness patch then production interval on successful readiness; N has no fast patch. Event requested_extra_ms and outcome cost correctly distinguish N=0 from P/M=50. Original runner source and all raw outputs retained for review.

Lane RETIRED. Publication HELD. Test fix under declared simulation only; historical hosted cause NOT_ESTABLISHED, hosted/native/physical/runtime NOT qualified. Root/A8 must review the incomplete oracle before any further allocation.
