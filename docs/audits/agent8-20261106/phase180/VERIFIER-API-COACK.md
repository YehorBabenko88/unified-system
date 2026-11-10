# Pure native-support provenance verifier: before-edit allocation and ABI

2026-11-10. A2 scoped co-ACK proposal for ROOT's internal CI helper. This is a source DATA verifier, not a runtime gate/capability, installer, loader, second authority or test executor. Root static report fbeb4ca4a2f0fb5a97d204de0fb2aa985c656a4e701940077ba403f4a8ef6d2f was fully read and bytes matched. Original failure logs and existing qualifier/source contracts remain immutable.

## Exact allocation

Proposed repository: YehorBabenko88/bybit-cluster-grid, ROOT exclusive new files only:

* tools/ci/verify_native_test_support.py
* tests/ci/test_native_support_bootstrap.py
* docs/ci/native-test-support-verifier.md

No Agent2 concurrent edits. If Root intends another repository, explicitly confirm/revise the allocation before edits; these relative paths do not imply blanket ownership across repos. Existing .github/workflows/preflight.yml, mission3-qualification.yml, conftest, requirements/locks, native fixture imports, runtime and all old definitions remain NO_EDIT. Root/A2/A8 separately review exact source/artifact closure and authorize any later native segment; no import or execution permission comes from this helper co-ACK.

## Eligible immutable SOURCE graph, not execution graph

SOURCE-GRAPH.json and two full committed inventory files bind:

* Gridfb177d14b1e6e399bd9b66ae7cb35d3838acbd81/tree2cba4b0a1ee7621ef213600d6334db8e9ac7dae1,824 primary blobs.
* Unified native support1f6b0b5c231853607f5bec780f1544cd32bf577d/tree5aa0025f564f16500e2ea5546b7bdd31deab758d,1519 primary blobs.
* Historical Unifiedf155126a95e80139b1b9679c1870ffd66c29360e/treee129873c435c8b11d2126307a67b604601e7e4b8, exact tests/test_gateway_identity.py blob72b1a05acd21f31e68616ada59cb9d03d7c3e37d/SHA256b26fe114c778a8b8a95bc3de822dd7c7a4f57dd12277e9fdcbc96cfb5bc4199f and docs/intelligence/identity/run_qualification.py blob8a68c2a6f613d7ba6530afeb807c12880fafaddb/SHA256e3733379da5e0cde84573f3279d265c91e16eceb8c94aeeda8983b51031216fe. Historical bytes must exist locally before verification; no fetch, exec or import fallback.

Named native-group module origins are closed in the descriptor: Grid native_snapshot_consul_lab; Unified test_native_profile_v2 -> test_native_broker -> consul_lab plus exact real broker/identity/Journal definitions; Grid coordination/runtime/assignment. Full committed raw inventories cover their local source trees. They do not prove broad336-file pytest compatibility, third-party dependency installation or absence of every undeclared dynamic dependency; graph coverage must be explicit before native imports.

Support1f6 is NOT approved as a global replacement for legacy Unifiede0c2ea20aa4f1bd9476d1046e7e4b41f1b12d8e9. Preserve old group pins until their owner approves a new compatible pair. Do not put two incompatible unified_system origins into one shared PYTHONPATH/interpreter. If later qualification has legacy and native groups, it requires explicit source-bound isolated interpreter/import inventories and complete mandatory case accounting; this descriptor does not select, skip or drop tests.

The verifier itself may live in a newer tooling commit, but the fb177 target descriptor verifies ONLY fb177, not that newer head by inference. No cyclic self-embedded HEAD/hash or alias-to-current-HEAD substitution. Future target revisions require an explicit external descriptor/source binding, not a claimed automatic source/runtime adoption.

## Exact proposed DATA API to confirm before implementation

`verify_native_test_support(graph_path: pathlib.Path, *, expected_graph_sha256: str, source_roots: dict[str, pathlib.Path]) -> dict`

* graph_path is canonical absolute local ordinary file; bounded JSON<=2MiB. Expected SHA256 is lowercase64, matched BEFORE trusting descriptor. source_roots has exactly grid and unified_native_support, canonical local roots, no aliases/symlinks/reparse/unsafe hardlinks. These are caller-selected locations for verification, not caller-selected authority or executable module providers.
* Parse closed known schema/fields, reject duplicate JSON keys, unknown schema, malformed hashes/paths, duplicate module origins, ambiguous casefold paths, extra/missing inventory nodes. Inventory paths are bounded relative POSIX under graph_path.parent, never traversal. Retain bound inventory SHA/length before parsing.
* Fixed read-only Git object commands only, replacement objects/config helpers disabled; verify exact HEAD/tree and primary object identities plus actual working raw bytes, no extra source/cache files/reparse. No checkout/reset/fetch/install/cleanup. Read the two exact historical objects without executing them. Source command executable/lifecycle must follow Root's existing source tooling policy.
* Validate declared module origins statically against role/root/path/hash; never import project modules, exec/compile fixture bytes, use pytest collect-only, importlib.find_spec or manipulate sys.path. Dotted find_spec can import a parent: it is not permitted here. AST parsing if needed must not execute decorators, loaders or setup code.
* Retained requirements lock and native binary leaf pins are REFERENCE DATA only. Current locks do not provide the whole broad CI runtime+pytest/per-platform/Python wheel/install closure; old fetch script checks a leaf but does not establish a reviewed archive/publisher chain. Missing exact approved dependency/binary provenance remains INCOMPLETE; no guessed wheels, bare executable/version run, download, certificate/clock/worker call or private Windows path fallback.

Return a plain closed DATA dictionary with schema=grid.native-test-support-verification.v1, graph_sha256, status, sources, historical_objects, module_origins, artifact_closure, unresolved_codes, fixture_import_allowed=false, native_execution_allowed=false. status is SOURCE_MATCH_DATA_ONLY when exact source graph matches but execution-artifact closure is pending; MATCH_COMPLETE_DATA_ONLY may be used only for a future separately co-ACKed complete artifact descriptor. Never represent either as an opaque permit or automatic import authorization. Each source result contains only role/head/tree/raw_files/inventory_sha256/raw_match; historical result role/head/path/blob/sha256/raw_match; module origin result module/role/path/sha256/raw_match. No key/token/environment or source contents are printed.

Malformed or mismatching required DATA raises `NativeSupportVerificationError(ValueError)` with a bounded closed code, e.g. UNKNOWN_SCHEMA, GRAPH_SHA_MISMATCH, INVALID_PATH, WRONG_HEAD, WRONG_TREE, RAW_MISMATCH, EXTRA_SOURCE_FILE, MISSING_HISTORICAL_OBJECT, ORIGIN_CONFLICT. No fallback to another revision, private directory or ambient module. Exact code list should be fixed in Root's implementation/doc and tests; additional categories need review, not arbitrary raw error payload disclosure.

This is not an always-DENY wrapper: matching committed source bytes can produce a successful DATA verification; altered/missing/ambiguous source rejects. It is also not a positive native fixture gate: absent artifact provenance stays unresolved and import/execution flags stay false even on DATA success. Any complete artifact descriptor/eligibility runner is another explicitly reviewed step, not implied by this source-only scope.

## Required pure regression scope

Root-owned temporary synthetic source/artifact graphs may test a matching DATA result and missing/wrong head/tree/blob/raw hash, omitted historical dependency, duplicate/ambiguous origin, path escape/casefold/reparse/cache/extra file, source-order dependence/private fallback and graph tampering rejection. Mark such data fixtures MODEL/DATA_ONLY, never a real issuer, native binary qualification or passed Consul fixture. Include inert sentinels proving verifier does not import/execute fixture modules, launch native binaries, call network, mutate source or alter environment/global module paths. Native positive/principal setup, TLS, Consul, worker/Job, browser and office calls remain forbidden.

Root freezes exact API/error/report fields and repository/doc allocation with A2 before edits; A2's graph/descriptive provenance co-ACK does not supply A8/native execution authorization. Existing ordinary source verification can proceed under current authorization; no change to strict Option1, logical DISABLED, public DENY or actual positive APIs NONE.
