# F26 heartbeat fixture cadence proposal

Status: source approved by Root; publication held pending Root/A8 qualification review.
Base HEAD: 6e79f2da66212474e9875559ec532c0f65b678a8
Base tree: 18c84ddbe65cd4e82d3f32a5210c3ff8617bf0ca

## Change and preserved coverage

The existing heartbeat test temporarily selects 50 ms cadence to establish real
PING/PONG processing and renew an already expired data-read deadline on both
connections. Stop that patch immediately after both original renewal assertions,
before connection-health assertions or bidirectional application sends. Context
exit still restores it on setup/assertion failure. The original heartbeat method
continues running; a wait already in progress may complete once at the old cadence.
No frame injection, heartbeat replacement, budget bypass, deadline increase or
production change is proposed. Production interval is 10 seconds; idle timeout
remains 30 seconds and application deadlines remain the original 5 seconds.

All existing test IDs and assertions remain. Added test IDs: NONE. Original
stale last_rx, real control processing gate, forced old read deadline, both True
renewal assertions, open/health checks and both payload comparisons remain.
Existing expired-idle negative real-TLS case remains unchanged. Failure diagnostics
remain unchanged. No helper or mandatory inventory changes are needed for IDs.

## Executable qualification plan (requires new serial allocation)

1. Run the existing active-control heartbeat case once on this exact reviewed diff,
   with actual owned loopback TLS and fresh temporary SQLite synchronous FULL.
   Inject the SAME requested extra 50 ms own-store transaction service cost as
   the original matched experiment, after the body while holding only its RLock
   and before the original context exit. No cost calibration or debit replay.
   Require both renewals, open connections and both payload comparisons to pass.
   Capture original failure diagnostics on failure. Do not retry automatically.
2. In a separate disposable, explicitly allocated mutation run, make only the data
   read on_idle callback return False at the existing wrapper boundary while
   retaining the actual TLS/control heartbeat method. Run that same active case
   once; require failure at renewal/closure before payload success. This checks
   the test cannot pass when renewal is disabled. Never ship the mutation.
3. Run the unchanged expired-idle negative case once: both real TLS connections
   must close and preserve DEADLINE evidence. No timeout/cap/security changes.
4. Root owns subsequent exact-head mandatory inventory and Windows hosted suite.
   Local outcomes do not transfer to hosted, physical or runtime admission.

These are proposed future executions, not claims of completed tests or current
permission to run. No additional fixture, model, calibration or third arm ran.

## Evidence limits

The authorized matched pair on the base produced A RED at reply CREDIT0/DEADLINE
and B GREEN under the same requested extra 50 ms owned-store service cost, with
only subsequent heartbeat cadence changed. It supports fixture cadence sensitivity
under that declared simulation, not exclusive historical hosted causality or a
production fix. This diff requires independent review and exact-head qualification.
No physical computer or network security settings were changed.

## ROOT integration evidence and limits

Component source ab9362706cd8cd75b2fc0f5177481a96a5f73ac4, tree cfa80d600603d947e79304e075d48787c116a8a1. A8 source/original review phase177 confirms all existing IDs/assertions remain, positive case and unchanged expired-idle negative pass under the declared conditions. This does not preserve or claim sustained 50 ms stress coverage during application sends. F26 remains OPEN pending hosted exact-source qualification; historical hosted cause is not established.

Original P/M/N qualification retained the first M as ORACLE_INCONCLUSIVE: replacing the observer skipped its queue. A separately reviewed, once-only successor changed only the observer's inner callback, leaving the original observer/queue and production heartbeat method intact. The original renewal assertion rejected False: one test, one failure, zero errors/skips, one actual mutation invocation, zero successful APP calls, 49 events with none dropped. All 1858 raw files matched before/after; all 19 owned child processes and threads retired. Family 23.531 s; no automatic retry or P/N repetition.

Revised-M package seal SHA256 86fb2363d7d4123a17b73941bd186c42be833daf632dc6a4b0e953053e1a4803. A8 phase178 reviewed revised harness source only; successor execution originals require separate independent review. A failed mutation case is proof of causal test rejection, not a successful production runtime or a replacement for Windows/Ubuntu LAN68/component161 matrices. No runtime transport or network budget code is changed.
