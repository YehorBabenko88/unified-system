# Publication source review packet — 2026-11-11

Proposed title: feat(market-data): prepare bounded data-only Bybit request plans

Exact local head d6b72b66ff1b85b7e6b956568342ad6bd8bfcfbe,
tree066bbe51900e88dd53541baf29a777037ed10b5b. Proposed NEW Draft stacked on
feature/agent2-strict-utc-countermodel-20261110 atfb177d14b1e6e399bd9b66ae7cb35d3838acbd81.
Readonly GitHub metadata confirms existing PR281 is Agent2's Draft with that HEAD,
whose own upstream base is different (2f94...). PR281 is not Agent3's new PR and
will not be overwritten or silently retargeted. Two local commits descend from
fb177, adding seven owned files only. Source branch/ancestry and snapshot included.
Base movement requires fresh review; main is not substituted.

## Actual qualification, independently crosschecked as retained DATA

Root MCI179→180 held original OUTER-RESULT SHA256
507be9ecc58aa79d3e58035345bdcf7923166e99b8365a205d0adde64f4f2124
was verified from raw original file. Raw stdout
3c624bb0e7a452cd9ff026c039b5f91b53de5bb2b300628fd5351eec2d25c49a,
stderr f434793e56963f34737e7f291d94e280ae5b807a33d810d8db4bb2c48c033684.
Root parent state SCOPED_FULL62_OBSERVED_SUCCESS_NOT_PROVIDER_ADMISSION,
child0, direct/readers retired, no lifecycle/reader errors,3.578s observed phase,
0s observed cleanup,20098B under256KiB;831 source/841 runtime pre/post equal and
cache checks passed. Raw stderr shows62 tests and OK. Actual62 IDs were separately
compared with static4e8c inventory: exact15 declared+47 generated, no masking.
Zero failures/errors/skips/expected failures.11 closed diagnostic markers observed.
The test runner's reported test-body time .036s is distinct from parent phase.

This is offline pure-module PASS only, not hosted CI/Windows CI acceptance,
cluster/ingestion/failover/provider budget/pipeline enforcement or runtime GO.
No test was re-executed during packet preparation. Prior MCI145 is immutable
DENY/UNKNOWN with cleanup_uncertain TRUE, despite retired/closed flags; no double-
kill cause or cleanup PASS is inferred. Later success does not rewrite that run.

RAW831-SOURCE-PINS is exact existing raw manifest; all831 physical hashes were
rechecked with clean source clone. Frozen cardfdbc, testb832, profiles166/973 and
fixture attributes remain unchanged. Status doc is an additive owned path, not
card edit. No doc status commit is made after qualification to change its HEAD.

## Publication/CI review boundary

DRAFT-PR-BODY.md is review text only, not a GitHub mutation. ELIGIBLE-COHORT.md
maps exact branch/path events:0 push jobs,13 PR jobs across7 unfiltered workflows.
No push, PR creation/update, manual dispatch, CI execution or merge performed.
Some CI checks use default PR merge source; actual source identities must be
verified rather than inheriting this exact local test claim. No mandatory test
is removed/disabled and no foreign workflow is edited.

PROVIDER-CLOSURE.md separates the actual origin-closed qualified62 route from
legacy provider-facing full-suite and narrower CI routes. Concrete reviewed
Bybit HTTP/WS/TCP/archive test edges use mocks/pure functions, but complete broader
cohort transitive provider safety remains UNKNOWN. UNKNOWN is not asserted as a
specific observed send or module defect. No wholesale13-job provider-safety ACK
is supplied; Root must approve that broader effects boundary before publication.

A1 exact module scoped contract ACK129e402... was read-only hash verified.
A2 exact module ACK was explicitly requested; earlier card ACK is not upgraded
by silence. A8 original DATA review is Root-requested/pending. ACK-MATRIX records
scope and unresolved gates. None authorizes shared ABI adoption or actual sends.

Publication BLOCKERS: A2 exact module reconfirmation; A8 independent retained-data
review; Root source/base/cohort/provider-effects and publication grant. No concrete
new P0/P1/P2 module finding is asserted; broad cohort proof gap remains explicit.
SCOPED_OFFLINE62=PASS; HOSTED_CI=NOT_RUN; PUBLICATION=NO-GO; PROVIDER/RUNTIME=BLOCKED.
