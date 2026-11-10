# A3 — exact review2 priority/accounting direction ACK

2026-11-10. SOURCE/DESIGN ONLY; no code changes, application imports, builder
execution, tests, provider/NAT/native/office calls or implementation admission.

Read and independently raw-hash matched the exact pre-seal draft:

- ADDENDUM.md:
  ead5786f0ddd0e540c31fe32c35f7b1bfeb2f8d36cc0cf63e9f5495e7e2a1a46.
- measurements.json:
  cbdefcc18a7ab4954a5450da44d47f57140e678b11d25e98a3ad0788a78925b1.

DECISION: SCOPED EXACT PRIORITY/SHARED-BUDGET DESIGN-DIRECTION ACK for those two
files. Prior review380f736cff271d3f6414d28403a87c7617fb30982fcd97e7b4c14bdfae9efeb1
findings are addressed AT PROPOSAL SCOPE. Original seal2c1a... stays immutable.
This does not ACK a not-yet-issued successor seal or unrelated packet members.

## Acknowledged corrections

1. Protected bounded heartbeat/critical control/admitted management including SSH
   and HIGH live capacity precede ALL large HA requests AND responses. HA response
   reservation supplies capacity, not priority promotion. Research cannot select
   control/live class through request fields. Existing live/backfill priorities
   remain intact; this review allocates no production numeric policy.

2. Large HA data uses existing admitted BULK/research capacity. Genuinely tiny HA
   controls retain their actual critical class, but ALL their bytes also enter the
   SAME-domain derived HA share. Node/peer physical debit once, actual class debit
   once; attribution is a joined constraint, not another authoritative bucket,
   limiter or physical-byte debit. No free WANT/CREDIT/control promotion.

3. Whole-exchange direction projection is explicit:
   clientTX/serverRX37030+4106+4102=45238B;
   serverTX/clientRX5286+4102=9388B; sum54626B.
   The proposed quarter-share is per existing directional residual BULK domain,
   not a new combined54626B/s authority. Both directions and overhead must fit
   before credit/native work; unknown projection or insufficient residual denies.

4. Protected LIVE/heartbeat/SSH reservations cover shared node/peer/class totals,
   queue, credit, memory and executor boundaries. No protected-capacity borrowing
   or automatic cap enlargement. Concrete SSH accounting and TLS/TCP/service
   overhead margins are REQUIRED but NONE_PENDING; the document does not pretend
   LAN code already controls foreign SSH processes or changes OS/network settings.

5. Candidate buffer arithmetic is internally consistent:
   2*(65536+32768+32928+2048+1024+4096+16384)+65536=375104B,
   below proposed524288B HA subpool. This is accounting data only, not a verified
   allocator/Python/SSL heap or existing8MiB pool-enforcement proof. Native capture,
   HTTP and Journal memory do not silently borrow protected LIVE resources.

6. Existing owner scheduling/service and maximum NONPREEMPTIBLE TIME remain
   NONE_PENDING. One frame/1exchange per second/byte limits do not prove latency
   or no starvation. No blocking native/custody/parsing is admitted on protected
   servicing paths, and no new runtime/worker is prescribed. Missing any adopted
   reservation/headroom/SSH/overhead/quantum/service contract keeps the PROFILE
   DISABLED with bounded refusal within250ms before data credit/native send.

## Frozen Bybit and nonbypass boundary

Frozen provider IP/request/WebSocket/cost/usage/cooldown authority is unchanged.
LAN bytes and HA directional share are not Bybit request quotas or connection
permission. No HA/control/live priority grants provider sends, refund, fresh
allowance, NAT scope or UNKNOWN replay. All frozen provider sends remain BLOCKED.
No second global limiter, new authority or provider policy/source revision.

Before-send refusal under sustained LIVE load is allowed. Possible-send mutation
retains SAME-original UNKNOWN/known private state and obligations regardless of
response starvation/timeout; no rekey/retry/refund/eviction. Transport reservation
does not authorize native mutation or disclosure. Logical mutation/time gates
remain disabled/unimplemented; actual HA APIs and implementation base are NONE.

## Scope excluded and next exact gate

No A3 ACK of19KV/session selectors, capture counts/metadata/space allowances,
native coherent snapshot/response grammar, local custody/disk fit, protocol kinds,
credit ABI, numeric production rates or authority/time semantics. Those remain
their named owners' decisions, not accepted by reading their neighboring text.

New seal may reference this exact direction review, but new/changed member bytes
need their own review. Exact reservation/attribution/current-spend joins and
blocking-time/servicing measurements must precede implementation/activation or
qualified no-live-starvation claim. Prior required saturation/no-bypass regressions
remain NOT_RUN. No positive runtime evidence or PASS count is created here.

GO: corrected priority/accounting DESIGN DIRECTION ONLY.
NO_GO: activation, no-starvation/latency proof, provider/native/production/physical.
