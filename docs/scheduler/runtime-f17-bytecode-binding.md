# A8-F17: isolate executed imports from preexisting bytecode

A5 independently reproduced A8's timestamp/size-matched cache witness in an own
no-hardlink clone at 462935b53ef25d4d9be2371bad1cd7230c65f2e7. An inert marker
appended only to runtime.py's cached code executed while unchanged tracked source
and all16 raw blob bindings passed; the old workflow reported52 tests/0skips/PASS.
Disabling bytecode writes with -B does not disable bytecode reads.

The evidence runner now starts with -I -B, a fresh private empty pycache namespace and
write-disable both in the running interpreter and inherited child environment.
Preloaded protected product/test modules reject. Any __pycache__ entry, .pyc or
.pyo under product or tests rejects before execution and after execution; no cache
is deleted to obtain a pass. Ambient PYTHONPYCACHEPREFIX is overridden before
protected imports. Cache directory must remain empty and settings unchanged.
An initial interpreter cache prefix rejects. Isolated startup excludes the working
directory; the repository enters sys.path only after source/cache/inventory checks.
The protected raw-file, Git no-replace, exact52 IDs, preserved30 and zero-skips
checks remain conjunctive. Failure yields no accepted source receipt.

Scope is source-evidence robustness for the controlled test process, not a sandbox
against arbitrary hostile native code/interpreter/site hooks or an authority proof.
Native grants/storage/Windows fleet acceptance remain separate blocked gates.

Follow-up: A8 reproduced an untracked root typing.py shadow after CWD admission.
A5 independently reproduced52/PASS plus inert marker at0d6eb43. The import root
must be guarded as a whole: every tracked Python/extension/archive/path-hook file
is now raw-blob bound, all untracked importable files anywhere below root reject,
all repository cache entries reject, and symlink/reparse entries reject without
following them. .git internals are excluded from traversal. Generated evidence
JSON/logs are permitted; an importable file is never exempted as an output.

Final hardening binds every tracked file, rejects every unexpected repository
file, and requires the evidence directory initially empty even when outside the
repository. Only the runner's exact component-tests.log may be newly present at
the post-check; receipt.json is emitted after that check. Native .git control-file
metadata is excluded. Original blobs are fetched with no-replace batch mode and
OID/type/length/framing checks to avoid one Git process per tracked input.
