# Actual Assignment backend contract targets — dependency RED

ROOT858f0699 priorityD: implement adapters only after explicit supported A2/A4
endpoint/schema ACK. Both owners currently report actual Assignment/reservation/
publication backend NONE. A2 is implementing NEW grid/authority_assignment_v1.py;
A4 has a separate new publication/budget/checkpoint fixture allocation. Existing
be6335 RuntimeLayout/size helpers, async leases, UNWIRED lifecycle/Mux metadata,
ObjectStore byte primitives and A5 model18 do not issue execution grants.

## Ownership and isolation

Separate tests-only feature: feature/agent5-assignment-backend-contracts-20261107,
base7a4185924d4702ade53f518644e45d6ee4f6f451, reusing the previously clean unused
native-managed worktree. Existing PR24 is untouched. ROOT allocated only the new
test file and this document. scheduler_components/assignment_backend.py is reserved
but NOT CREATED: no approved new full-integration base or actual contract exists.
ROOT92b8328 checkpoint is not silently adopted as runtime implementation base.

## Executable RED targets

Run explicitly from repository root:

    python -I -B tests/test_agent5_assignment_backend_contract.py --run-native-contracts -v

Five actual-native targets are selected: stale generation, actual isolated voter
quorum loss, supersession-before-publication, publication-before-supersession,
and concurrent native ordering with one checkpoint/debit at most. No nested
asyncio.run or sync/async alias; unittest owns its isolated async test loop.

Initial result MUST be5 dependency errors at open_actual_owner_fixture because
the actual fixture/backend is absent. This is **RED_DEPENDENCY_UNAVAILABLE**, not
five reproduced native safety defects, not a mock implementation and not a
native assertion result. Test bodies remain NOT_RUN until the actual binding.
There is no success-producing issuer/driver/plugin/environment fallback.

Default generic discovery schedules0 native cases and reports NOT_RUN explicitly;
it must not make unrelated required CI fail merely because no backend exists.
It is NOT a skip or native PASS. Dedicated native acceptance requires explicit
selection, actual source-bound owner fixture and nonzero complete case inventory.
Direct invocation without explicit selection exits2 UNAVAILABLE. Do not relabel
legacy52/model18 success as these native contracts or attach a model to turn RED
green. No new workflow/required-CI admission gate is created by this change.

## Private test fixture boundary — NOT an actual supported API

open_actual_owner_fixture intentionally raises. After exact joint ACK, its owner
binding must expose async run_scenario/close for TEST routing only. These are not
production endpoint names and are not an adapter implementation. Actual requests,
context/actor proof, response/receipt validation, original identity and native
transaction records must use the supported A2/A4 APIs, not these observation names.
ScenarioObservation is untrusted test data, never a native proof/permission.
Passing assertions on caller-made observations cannot qualify actual execution.

Observation counts are confirmed logical effects of the tested original commands,
not raw KV/session/denial-receipt writes or all unrelated storage accounting.
Each original command's logical effect count is bounded0..1. Assignment and
publication statuses use the closed test-observation vocabulary COMMITTED,
REJECTED, UNKNOWN, UNAVAILABLE; this is not a supported production result codec.
COMMITTED requires1 and definitive REJECTED requires0. UNKNOWN/UNAVAILABLE
alone does not prove0 or terminate an earlier uncertain original operation;
scenario-specific assertions still constrain the proven no-quorum window.
In all three ordered/concurrent publication-versus-supersession cases, the initial
assignment is fixture preparation and excluded. assignment_status is the status
of the tested supersession (equal to supersession_status); assignment_effects
counts that ONE original supersession's logical assignment mutation: exactly1
when COMMITTED, exactly0 when REJECTED. Rejection leaves the assignment revision
unchanged; commit must advance it. Count99, missing committed mutation or a
contradictory assignment status rejects even if publication counts are correct.
The publication scenarios require one FRESH logical segment with the complete
replica/hold set required by an explicitly admitted policy. The debit count1 means
ONE logical atomic publication-debit event across ALL required participants, not
one physical replica/charge or one byte. Actual per-node physical charges must
all be evidenced and checked; dedup/reuse needs a separately defined case. A4
review4 N1-only reservation candidate cannot lower a required2-copy policy or
fabricate independent failure domains. Positive native vectors stay NOT_RUN until
the complete policy-compliant participant/closure contract and stand are admitted.
Prepared/uncertain physical charges remain charged, including after rejection;
zero publication debit does not mean those bytes were refunded or never existed.

No-quorum observations refer to committed effects DURING the proved isolated
quorum-loss window, derived from actual stand/native commit evidence, not a boolean
or an impossible consistent read. UNKNOWN may later reconcile as committed after
quorum returns; record that separately under the SAME identity. The test does not
assert that an original uncertain proposal can never commit after recovery.
Race order likewise comes from native mutation commit indices/receipts, not client
wall clocks. Other admission/lease/closure gates must be controlled and stable;
unresolved outcomes remain unavailable/inconclusive, never guessed definitive.

The actual fixture must retain raw source/endpoint/schema/native record and
receipt evidence. It must use the SAME existing Consul transaction order and stable
partition assignment key for publication/supersession, verify actual current lease/
epoch/compound fencing/node+attempt/resource/storage/own hold and closure, debit
current accounting atomically, preserve immutable issuance/history/UUID/key and
reject no-quorum mutations. No caller KV paths/indices/prebuilt ops/boolean proof.
Native limits64ops/32768encoded bytes belong to A2's actual builder and must be
measured there; A5 illustrative key hashes/synthetic ledgers are not aliases.

Only A2-owned isolated test voters may be controlled for no-quorum testing under
actual stand admission. No office node/process/service stop or network partition,
no physical worker or real research/ingestion/provider send, no second consensus.
Factory/stand startup is NOT supplied or executed here. Missing native security/
Root provider remains UNAVAILABLE, not a fixture-based execution admission.

Concurrent outcomes explicitly permit both commands committed when publication
linearizes first; they also permit a definitive CAS rejection of one contender.
They never permit supersession-first plus an old-worker publication commit or
duplicate actual checkpoint/debit. Ordered cases preserve byte-identical original
historical receipts after supersession; old receipt presence is not current grant.
Concurrent publication success also requires nonempty byte-identical historical
receipt preservation. Stale generation requires definitive rejected publication;
no-quorum targets UNAVAILABLE/UNKNOWN, not a contradictory COMMITTED/zero-effects
observation. Any alternative definitive error needs the actual supported contract.
Assertion-quality counterexamples use deliberately untrusted observations only;
they are meta-probes, never a native fixture, grant or backend qualification.

## Next dependency and evidence

Exact supported A2 async assignment signatures/endpoint/schema/key/proof ACK and
A4 issued reservation/immutable budget-policy/current lifecycle/hold/delegation/
closure contribution ACK are required next. Then implement the owned scheduler
adapter and actual test binding on an approved immutable integration base.
Until then FIX_COMMIT for the missing backend is NONE, runtime/Windows/physical
integration is NOT_RUN/NO-GO, and the RED evidence must retain this distinction.
