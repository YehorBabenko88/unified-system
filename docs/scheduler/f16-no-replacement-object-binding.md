# F16 — native Git object resolution in source evidence

F15 verified raw working-byte binding independently of index flags. F16 is separate:
Git replacement refs can redirect a blob/tree lookup itself. Agent5 reproduced both
old-guard blob and tree replacement controls against6bcf547 in disposable local clones:
altered source was incorrectly accepted with30 tests and receipt.passed=true.
No actual hosted tampering or runtime authority defect is asserted.

The narrow fix passes --no-replace-objects explicitly BEFORE each Git subcommand
used by the embedded source guard: rev-parse and status through its helper, and
the direct ls-tree and cat-file calls. It does not depend on an external environment
flag. Committed blob OIDs/bytes therefore come from native object resolution, not
refs/replace. The raw-binding marker is versioned; evidence schema/inventory remain v2.
Raw EOL/regular-file/before-after checks, exact30 IDs, zero skips and log SHA remain.
No product module, test, schema or inventory bytes change.

Controls use independent --no-hardlinks clones with their own .git and no commondir.
Replace refs are NEVER created in linked worktrees, the feature checkout or primary
repository. Only disposable clone-local objects/refs are written. Probe subprocesses
explicitly remove GIT_NO_REPLACE_OBJECTS to demonstrate the guard's own enforcement.

Candidate results: clean30PASS/0skip; original-blob and original-tree replacement
both reject before tests with raw-input validity=false. F15 hidden pre/post and
raw CRLF/missing/nonregular controls are rerun against the same candidate. These
are local source-evidence tests; hosted artifacts and independent A8 closure are
separate. F15's earlier source-scoped closure remains historical at its own SHA.
