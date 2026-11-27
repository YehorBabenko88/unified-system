# Fixed-parent materializer ledger

Base: 4eaa98671129e71fe20462b1921969078ea43b2b; preserve that PR71 pin.
Owned new files: materialize.py, test_materialize.py and this document only.
assembly.py/package.py remain unchanged.

- [x] RED missing helper and meaningful refusal controls.
- [x] Implement materialize(canonical_plan_bytes, external_plan_sha256).
- [x] Focused source tests; retain RED and partial-failure fixture assertions.
- [ ] GitHub source commit/Draft update before Root can assemble a real package.

Root approved fixed parent:
`C:/Users/LS-5/.codex/native-e2e-evidence-20261109`.
Only an absent immediate `ls5-package-<canonical identifier>` child may be created.
No generic destination or caller-selected parent. Parent ACL remains an external
Root readiness gate; no ACL edits or authority are provided here. Unit tests
patch only the fixed-parent constant to owned inert temporary fixtures.

Before any destination write: bounded canonical closed JSON, duplicate-key
refusal, external SHA256, exact approved destination spelling, and byte-identical
recomputation through the read-only assembly planner. This verifies plan shape,
selected source/component/profile paths and global 20000-file/1GiB limits.

Copy uses ordinary source identity/size/type checks before/open/after, bounded
chunks with pinned size+SHA256, exclusive new output directories/files and final
destination integrity snapshot. Unexpected existing objects refuse. Failures
retain every partial output; there is no deletion or cleanup function. Root must
protect source/destination namespaces; checks do not establish hostile-parent
atomicity. No process, native Job, browser, network, installer or runtime action.

Only unit fixture copying is authorized in this subtask. Actual fixed-parent
assembly remains Root-only after source/isolation review. A correct external
digest proves bytes, not permission: public submit DENY and runtime/physical
execution authorization false remain unchanged in returned copy receipts.

Local verification: 55 focused tests PASS, zero skips on CPython3.12.10
-I -S -B (15 materializer, 16 planner, 24 original package). Tests cover late
exclusive-file collisions, short/zero writes, pinned source growth during held
copy, changed source before allocation, malformed/raw/oversized plans, unchanged
authority bits, and retained partial files on failure. No actual fixed-parent
copy was run. Full raw Git verification and GitHub pin follow this source commit.
