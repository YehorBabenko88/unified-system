# Phase66 — Math116 independent numerical review

Requirement IDs: A8-HEAD, A8-OFFLINE-NUMERICAL, A8-SOURCE-GUARDS, A8-WINDOWS-CI.
Repository: math. Draft PR: https://github.com/YehorBabenko88/math/pull/116
Exact HEAD: ff1c42cad883f54c06293884ef29a290dd74e306
Tree: 68623befcb4de563e1d284569fea56b3d9c8de45
Base: 917d99672e37db59835a8ab23b03c99826b12d78.

Environment: own detached no-hardlinks raw-LF clone, local Windows Python3.12.10. Synthetic trades only. No orders, provider calls, installation, native activation, physical faults or network settings changes.

| Test | Expected | Actual | Status | Evidence | Severity / required correction |
|---|---|---|---|---|---|
| Exact HEAD/tree/four allocated paths | exact pin and unchanged source | four paths, all687 raw files equal before/after | PASS | local-review.json; workflow10.original.json | none in bounded scope |
| Actual committed stdlib workflow | ten mandatory tests, zero skips | 10/0 | PASS | workflow10.stderr.log | local execution only |
| Broader history suite | all25, no skip | 25/0, includes workflow10 | PASS | stdlib25.stderr.log | counts not additive |
| Primary-base overflow reproduction | reproduce invalid infinite support and block interval; current refuse/finite | reproduced and corrected; input unchanged | PASS | numerical-oracle.json; oracle-executed.py | no profitability claim |
| Independent rational mean oracle | finite, same sign, error at most1ULP in sampled cases | 516 vectors:505 exact,11 within1ULP;64 independently replayed seeded samples | PASS | numerical-oracle.json | fsum/division not universally correctly rounded |
| Four inert negative source fixtures | reject before any tests | cache/shadow/tracked mismatch/replace refs all refused,0 tests | PASS | guard-controls.json; guard-*.stderr.log | scoped guard only, global F16/F17 unchanged |
| Hosted Windows and Ubuntu matrix | terminal successful jobs and original artifacts | runs42368002687/42367969223 attempt1 queued, conclusion null | BLOCKED | ci-*.original.json | P1 acceptance gate: obtain terminal mandatory CI and original artifacts |
| Physical/native/Tailscale removal | separately admitted release and proof | not exercised | BLOCKED | owner authorization and current-acceptance-status.json | existing gates remain |

Initial A8 script-generation ValueError occurred before any tests and was corrected by a standalone harness. This was an audit harness error, not a product failure or waived test.

Bounded numerical correction is independently verified locally. Overall NO-GO; Tailscale removal BLOCKED/NO-GO. Existing open6P1/3P2 unchanged, no new implementation P0. Protected diagnostic2446 and consumed run42352374979 were not modified, rerun, relabelled or cancelled. No PASS transfers between local Windows execution, hosted Windows CI, integration, physical, or Tailscale removal.


Phase66 qualification correction: dedicated workflow10 had clean full pre/post receipt. Broader25 functional PASS left four ignored python/__pycache__ files from child -I-S without-B; tracked687 raw hashes still equal, but full post25 receipt independently REJECTED_CACHE before0tests. Caches retained, not cleaned. No clean-inventory PASS for25. See phase66/post25-cache-rejection.json and post25-guard.stderr.log.
