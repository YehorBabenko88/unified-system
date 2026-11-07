# A8-F17: isolate executed imports from preexisting bytecode

A5 independently reproduced A8's timestamp/size-matched cache witness in an own
no-hardlink clone at 462935b53ef25d4d9be2371bad1cd7230c65f2e7. An inert marker
appended only to runtime.py's cached code executed while unchanged tracked source
and all16 raw blob bindings passed; the old workflow reported52 tests/0skips/PASS.
Disabling bytecode writes with -B does not disable bytecode reads.

The evidence runner now uses -B, a fresh private empty pycache namespace and
write-disable both in the running interpreter and inherited child environment.
Preloaded protected product/test modules reject. Any __pycache__ entry, .pyc or
.pyo under product or tests rejects before execution and after execution; no cache
is deleted to obtain a pass. Ambient PYTHONPYCACHEPREFIX is overridden before
protected imports. Cache directory must remain empty and settings unchanged.
The protected raw-file, Git no-replace, exact52 IDs, preserved30 and zero-skips
checks remain conjunctive. Failure yields no accepted source receipt.

Scope is source-evidence robustness for the controlled test process, not a sandbox
against arbitrary hostile native code/interpreter/site hooks or an authority proof.
Native grants/storage/Windows fleet acceptance remain separate blocked gates.
