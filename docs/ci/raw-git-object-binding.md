# Bind CI source to primary Git objects

Raw-byte comparisons must disable Git replacement objects before resolving the
source tree or reading blobs. Otherwise a locally created refs/replace mapping
can substitute a different blob while the declared HEAD/tree stay unchanged.
This concerns source-evidence robustness on a trusted disposable test runner; it
is not an allegation of actual hosted tampering or native execution attestation.

ROOT reproduced the gap at c9f3735 in a separate owned clone with its own .git:
a harmless durable.py comment plus a replacement blob and hidden index flag
passed all75 tests and the old source guard although executed SHA256 differed
from the original primary Git blob. No replacement refs or source objects were
written to a primary repository or shared/linked worktree.

All Git subprocesses in the integration source guard now explicitly invoke
git --no-replace-objects, including the initial ls-tree and subsequent metadata,
status and blob queries. Exact75 IDs, prior59 cases, zero-skip policy, raw EOL,
regular-file checks and source-before/after comparison remain unchanged.

Original RED and corrected clean/replacement probes are retained under
release/evidence/f16-root. Other repositories' guards have separate ownership and
source-scoped conformance review; their old results are not automatically
qualified by this correction. Production/runtime/physical admission stays closed.

## F17 product import caches

A raw `.py` comparison and `-B` do not prevent reading timestamp-matched preexisting `.pyc`. Final integration runner now starts a fresh isolated Python interpreter, rejects every repository `.pyc`/`.pyo` and unexpected `.py` before product/test imports and after execution, and refuses redirected `sys.pycache_prefix`. Only then is the admitted repository added to sys.path. Nothing is cleared to turn a contaminated run green. This protects product/test source attribution, not a hardened interpreter or independent authenticity of the installed Python/stdlib/dependency supply chain. Hash-pinned dependencies remain separate.
