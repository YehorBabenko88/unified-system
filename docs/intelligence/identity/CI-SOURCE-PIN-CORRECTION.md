# CI source pin and evidence attribution correction

Root identified P1 in original workflow: default PR merge checkout, a self-derived
expected HEAD and persisted credentials. Fixed checkout uses the immutable event
pull_request.head.sha or push github.sha, shared EXPECTED_HEAD environment, exact
ref, fetch-depth0 and persist-credentialsfalse. core.autocrlf=false is scoped to
checkout's Git environment, no global Git configuration mutation.

Qualification compares HEAD to the external expected event pin, checks every
tracked byte against unreplaced primary Git blobs before imports and after tests,
rejects unexpected files/directories, source caches/shadows and symlink/reparse
ancestors, and requires the exact unique24 identity test IDs. No extra/missing/
duplicated/replaced test inventory accepted merely by total count.
Actual guard helper controls: one clean positive plus seven negative conditions
in six stdlib test methods, including actual owned Windows junctions. RED against
old helper preserved; green against new helper separately reported. Guard controls
are not TLS/native tests and are not added to the24 identity test count.

Attribution correction: Root identified the forged issuer vector by source review
and requested a regression. A2 executed the old-source RED and subsequent fix;
Root did not claim to execute that RED. Source-refinements wording corrected.
Previous raw logs and 2cb6b21 qualification remain unchanged at their original
source scope. Runtime gateway_identity.py and its admitted84093865 module hash
are unchanged by this CI/qualification/documentation correction.

Hosted event-pinned Windows/Linux PASS still requires terminal original job logs;
local qualification and Root component source ACK do not imply hosted acceptance.

Additional primary-object control: A2 reproduced a corrupted loose blob stored
under the original OID and matching altered tracked bytes; header-only comparison
accepted it. Qualification now independently recomputes commit, recursive tree
and every blob Git OID from actual bytes, in addition to SHA256 source manifests.
Tree-corruption fixture was already refused by Git on this platform (not a newly
reproduced helper bypass); explicit tree recomputation is still required.
Successor guard inventory: eight methods, one clean positive plus nine negative
conditions. Prior six-method/seven-negative logs remain scoped to the earlier
helper. No global source-qualification finding closure is claimed; A8 independently
retests its original exact cryptography-shadow vector against the successor.

Hosted observation update: original2cb, intermediateeed4 and final063a identity
runs completed failure/attempt1; jobs API returned no jobs. A2 separately reproduced
a concrete workflow YAML parser failure at the pip command's unquoted colon-space
in --only-binary=:all:. Fixed by a run block scalar. Actual isolated PyYAML6.0.3
parser RED/green logs retained; validation-only environment is separate from the
hashlocked crypto runtime. This establishes the local invalid-YAML defect, not an
invented hosted annotation or successful runner/test execution. No rerun requested;
new pushed source naturally generates its own original workflow event.
