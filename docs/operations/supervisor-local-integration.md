# Supervisor local component integration specification

This test-only branch starts at local assembly commit
`eeb539d6e254769b5d0e7a0f5f3cb629ce673ffe`, tree
`feee281f84e917fe4963ef4d1afbcdc29e898936`. That assembly is not an approved
native/runtime base. No existing source, test, shared contract or attributes
file is changed here. MASTER MISSION remains IN_PROGRESS / NO-GO.

Six integration cases exercise actual public component APIs against temporary
local SQLite journals and an inert fixture capsule:

1. A persisted/reopened Development Task fails NodeOperation parsing and
   Supervisor submission, including an attempted merged dictionary cast.
   No node journal is created by rejected submissions.
2. The exact archived Math API run/jobs responses ingest through CI Controller,
   reopen as QUEUED / runner 0 / UNASSIGNED / CONSUMED, and remain non-authorizing
   when referenced by a persisted Development Task. No API request is made.
3. REPORT_STATUS completes with LOCAL_RECEIPTS_ONLY and survives reopen;
   authority/source/freshness remain UNKNOWN, physical acceptance NOT_RUN, and
   deployment's local health and Windows qualification remain unknown/not run.
4. REQUEST_DRAIN is BLOCKED even when stored development axes claim PASS and
   approved=true. Such observations are not native grants.
5. Actual capsule byte verification feeds the existing inactive installation
   transaction plan. Install/state targets remain absent, execution is blocked,
   and a previous-release reference does not authorize or verify rollback.
6. CI SUCCESS and source/development PASS claims leave deployment PLAN_ONLY,
   physical acceptance NOT_RUN and trading/effects unauthorized. The capsule
   stays LAB_SIMULATION, and an attempted TRUSTED_RELEASE label is rejected.

Only existing fixture functions are imported. TestCase classes are not imported
as globals, preventing discovery multiplication. Node `run_readonly` writes only
its owned disposable journal; these tests do not describe it as a UI read.
The service prototype's existing fixture setup may be reused by its fourteen
primary tests; no native/Windows service test bodies are selected.

## Archived evidence identity

The two files under `release/evidence/supervisor-local-integration-fixtures/`
are byte-for-byte copies of Agent 7's original
`outputs/math115-observation-240m/run.json` and `jobs.json`, respectively:

| Fixture | SHA256 |
| --- | --- |
| `math-run-42352374979.json` | `24670c428528cea08c791fe31e3a7561bff78dd058006f20bdab8c2da09e03ec` |
| `math-jobs-42352374979.json` | `a9447f5db6237d4811da9275202963c4dc043728188f35175787adf2f026fa6f` |

The existing `release/** -text` rule protects those raw bytes. Tests verify both
hashes before parsing. The controller receives the parsed run and single job in
its supported capture envelope; raw originals remain unchanged. This is an
archived observation, not a statement about the current live run. Its original
run 42352374979 / attempt 1 / job 128343065197 / source
`2446d04624469e34aa96ed766be7a4887d6d654c` is never dispatched or retried.

## Verification scope

The dedicated pinned CPython 3.12.10 Windows/Ubuntu stdlib workflow selects exact
test identities: Node 32, CI 22, Mission 39, Journal 8, Root deployment 14, and
these six integration cases: **121 unique tests**, zero skips required.
Full tracked primary-source bytes are checked against raw Git blobs before and
after a fresh `-I -S -B` child. Unexpected files/directories, symlinks/reparse
entries and bytecode/cache artifacts are refused. There is no dependency install,
cache, network provider, native grant mock, runtime activation or deployment.

The baseline had no integration specification file; this is recorded as
BASELINE_INTEGRATION_SPEC_ABSENT rather than an invented production failure.
Adding passing integration assertions documents existing compatible contracts;
it does not claim to fix an unobserved source bug. No broad baseline discovery
is run. Local component success does not qualify actual source admission,
native authority/fencing, Windows service behavior, Home/Pro, private ACLs,
rollback execution, Terminan wire/UI integration or physical installation.
