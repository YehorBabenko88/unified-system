# LAN Mux exact inventory repair

Original attempt-1 run `42853578322` at source
`b48ddc5ff083deeecfdf76185117d0e86aa23e2a` failed on Windows job
`129960469241` and Ubuntu job `129960468874` at the workflow's hardcoded
50-ID assertion, before execution. Original run/jobs JSON and log ZIP are retained
privately under `lan-mux-b48-original-inventory-20261110` in the CI evidence root.
Its artifact inventory is empty. The original logs do not print discovered IDs;
the ID comparison is a source reconstruction and discovery-only observation,
not an invented original test transcript or a component PASS.

The previous workflow count was already stale at PR77 source
`dd4ef015d9ed20065ccdc2c563e80046015d9193`: those three modules contain 52 unique
IDs. Historical source `9680babc85ca605f8450936f5410728898d5b71e` has 50 IDs.
The two later cases are the expired-idle-peer TLS negative and the owned-budget
child-cleanup regression. Source b48 adds 16 pure failure-diagnostic cases to
the 52, removing none. Discovery at CPython 3.12.10 confirms 68 unique IDs with
no loader errors; it does not execute any of them.

`release/lan-mux-test-inventory.json` version 1 records all 50 historical IDs,
the two PR77 additions, the 16 assembly additions, the exact current 68 IDs,
and primary source-head/raw-file-hash provenance. Pure validation independently
pins the 50-, 52-, and 68-ID digests. Missing, extra, duplicate, or removed IDs
fail closed, even if a lower count is substituted. Changing the inventory in
the future requires a reviewed version/digest update, not selection narrowing.

The workflow runs nine pure inventory controls, then validates the existing
three-module discovery against the exact manifest before running the suite.
All previous test cases, source guards, isolated interpreter flags, no-skip
requirement, TLS/security assertions, actions pins, deadlines, matrix, and
admission limits remain. No fixture test is deleted or masked. The shared
component inventory is untouched; this new pure test module is scoped here.

Preparation validation is limited to pure inventory RED/GREEN, source/AST/YAML
checks, exact fresh LF checkout raw-Git checks, and discovery without execution.
No TLS/network/native fixture, provider, service, installation, or physical
qualification is claimed. Original RED is preserved. Root/A8 review and a later
explicit fixture assignment are required before push or execution approval.

Root integration adds tests/lan_failure_diagnostics.py to the dedicated
pull-request path filter (A8 coverage observation). Other direct product/test
dependencies were inspected and are already present. This broadens required
qualification triggering; it does not bypass any source or runtime gate.
