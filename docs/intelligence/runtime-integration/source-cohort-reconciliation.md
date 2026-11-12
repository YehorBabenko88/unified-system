# Gateway READ source cohort reconciliation

Original RED: run `43314338210`, attempt 1, Root source
`902a1704a16841d15d817ce17b48da1d3de19fda`. Both Ubuntu job
`131518284160` and Windows job `131518284451` failed at wrapper line 18,
before helper execution, inventory or qualification test discovery: the expected
helper raw SHA256 was stale. Qualification executed zero tests. The missing
receipt artifact was a secondary consequence of this early bootstrap assertion,
not evidence of application test failures. Original logs/provenance remain intact.

Old helper: commit `063a004770a6d98ba78de7bbd5d4aadcc752ed55`, blob
`8a68c2a6f613d7ba6530afeb807c12880fafaddb`, 7150 bytes, SHA256
`e3733379da5e0cde84573f3279d265c91e16eceb8c94aeeda8983b51031216fe`.
Current helper: first changed at `b48ddc5ff083deeecfdf76185117d0e86aa23e2a`,
blob `21184ff2c1b3a4df6ec0109876fe6b231e8c0a67`, 7315 bytes, SHA256
`75d8951b6a3ee97d05d55af3e970021f63da7b33c27448a063264ce267d7c967`.

Independent primary Git reads confirm top-level imports and function ASTs for
`git`, `ordinary`, `primary_objects` and `inventory` are identical. The helper
delta adds the strict-TLS fixture ID to its dedicated qualification inventory and
changes its dedicated main count/output from 24 to 25. READ consumes only
`git`/`inventory`; it does not invoke that dedicated main. The raw hash guard is
retained and pinned to the reviewed current blob. No helper or Authority behavior
is edited, and no fresh A2 ACK is inferred.

All five original READ discovery tuples were independently inventoried from AST,
without importing the test modules. The result is exactly 147 unique selected IDs:
all original 146 plus
`test_gateway_identity.StrictTLSFixtureTests.test_generated_chain_handshakes_with_explicit_strict_verification`.
The original 146 sorted IDs have compact-JSON SHA256
`7aa5683c7463983bac2a473d86dd56b57e287a097d8d3e1b07c1a9accb995891`.
No old case was removed, renamed, skipped or normalized.

The inventory mirrors unittest package traversal: `tests/storage/runtime` has
`__init__.py`; `gateway_disclosure` and `native_publication` do not, so they are
not recursively selected by the broad storage tuple. Disclosure remains separately
selected under its existing flat module names. A naive recursive file glob would
incorrectly report 191 IDs; that exploratory count is not the discovery cohort.

The AST regression denies unmodelled `load_tests`, wildcard/foreign TestCase
exports, unknown imported class inheritance, conditional test classes/methods,
dynamic factories/aliases/mutations and custom class or method decorators. It
audits current imported local classes as ordinary non-TestCase classes; known
external imports are the explicitly reviewed stdlib/cryptography symbol sources.
Current selected TestCase classes inherit directly from the two standard unittest
bases; no inherited-case expansion is assumed. Ambiguity requires reconciliation,
never a guessed ID set.

Only the wrapper's two constants change: helper pin and exact sorted REQUIRED set.
Discovery configuration, helper source guards, unique-ID equality, test-success,
no-skip and source-before/after checks remain intact. Local verification runs only
the new pure AST/source regressions on pinned Python 3.12.10 with `-I -S -B`.
It does not execute Gateway, loopback TLS/listener, PostgreSQL, provider or native
tests. A complete 147-case READ result remains unqualified until separately
forecast, reviewed hosted CI runs; no rerun/dispatch or publication is authorized
by this source receipt.
