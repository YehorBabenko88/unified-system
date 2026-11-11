# Revised F26 oracle: SOURCE ONLY / NOT EXECUTED

Target exact source HEAD ab9362706cd8cd75b2fc0f5177481a96a5f73ac4,
tree cfa80d600603d947e79304e075d48787c116a8a1. No repository source change.

Old mutation replaced the test observer itself, so renewed received no value and
the test errored with queue.Empty. Proposed mutation validates the exact owned
idle observer code origin/name/free-variable shape, captures its on_idle closure
cell, validates the captured production _reader lambda, and changes ONLY that
cell to a counting callback returning False. The ORIGINAL idle observer still
calls it, puts False into the ORIGINAL renewed queue, and returns False to the
ORIGINAL frame reader. Original cell restored in finally even on DEADLINE.
This changes only the ephemeral test observer closure, never production source.

Expected causal rejection: original active case assertion
self.assertIs(renewed.get(timeout=3),True) raises AssertionError: False is not True.
The first or second identical renewal assertion may win the thread race. Require
1 test, 1 failure, 0 errors, 0 skips; traceback at that original renewal assertion;
actual MUTANT_INNER_FALSE invocation count >=1; zero successful APP_CALL events;
raw pre/post exact source match; no harness/scope/privacy error; no dropped events;
all owned threads/children retired. Queue.Empty, setup error, shape mismatch,
missed invocation, APP success or unrelated failure => ORACLE_INCONCLUSIVE.
No causal-PASS claim from generic red exit alone.

Future execution requires A8 source review AND separate Root serial allocation.
Runner now rejects P/N before source guard/imports. One M-only process/case, no
retry, no P/N repeat, no cadence/timeout/production method replacement. Same
requested 50 ms own-lock transaction pre-exit service cost, original FULL/security/
5-second application deadlines. Source guard requires CPython3.12.10 -I -S -B,
fresh LF/no-hardlink exact clone, no extra files/bytecode; external output only.
Run bounded by CASE_SAFETY_SECONDS <=84 inside outer90s family; inherited owned
connection close/join, child handle termination/wait/kill and class cleanup remain.
Emit bounded static phase/count/timing evidence, no callback repr, payload or keys.
Inherited ARM_START periodic_seconds is descriptive10, not observed readiness
cadence; outcome now names actual cadence source instead of synthetic timing.

No fixture was executed to prepare this packet. AST parse is syntax-only evidence.
Source-only diff and sealed predecessor remain separate; no push or retry authorized.
