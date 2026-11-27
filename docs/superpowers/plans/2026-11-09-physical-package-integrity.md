# Pure package integrity implementation ledger

Base: ba2b1cec0c2b114586afb73696e282117eede987.
Owned: tools/physical_dev/package.py, tests/physical_dev/test_package.py, this plan.
Root owns execution and independently reviews/imports compatible source.
Executing-plans and TDD skills applied to the package-only Root plan task.

- [x] RED for missing library and namespace/root failures; retain originals.
- [x] Bounded file snapshot with hidden files and pre/post identity checks.
- [x] Closed canonical manifest generation and external-SHA verification.
- [x] Source metadata explicitly descriptive; every authority flag fixed false.
- [x] Focused CPython3.12.10 -I -S -B tests: 24 PASS, zero skips.
- [ ] Fresh exact-source inventory and focused isolated process verification.
- [ ] Push owned branch and Draft PR; no merge or physical execution.
- [ ] Independent Root review before import or any physical action.

Ruling: manifest bytes are returned in memory and supplied externally to verify.
They belong outside package root because self-containing digest closure is not
possible. Every on-disk file, including hidden files, is a member. Empty
directories are namespace-checked but not represented in this file-only manifest;
verification does not attest an empty-directory inventory.

Ruling: source_metadata has closed fields description, sources (name/repository/
commit/tree), dependencies (name/version). Syntax-valid pins do not establish
Git provenance, approved origins, dependency trust or execution consent. Root
must separately admit actual sources/tooling. Fixed public_submit DENY,
runtime_admission false, physical_execution_authorization false remain checked.

Ruling: ceilings are 20000 files, 20000 directories, 1GiB content, 4096 absolute
path characters, 1024 relative path characters, 255 per component, 8MiB manifest,
64KiB metadata, 32 sources and 128 dependencies. Snapshot limits may reduce
file/byte ceilings. Bool is not an integer. Relative namespaces reject traversal,
drive/backslash/controls, Unicode surrogates/normalization aliases, Win32
aliases/device names and casefold collisions at file and directory prefixes.

Ruling: stat/open/fstat and final namespace snapshots detect ordinary mutation,
identity replacement and concurrent growth/content change. Windows DirEntry.stat
can supply zero link/inode fields, so Path.lstat supplies actual namespace data.
Retained own-fixture probes found pathname and descriptor ctime can differ while
identity/size/mtime match. These latter fields must agree across APIs; full ctime
is still compared before/after within each API. No hostile-parent atomicity,
private ACL, immutable filesystem, administrator containment or native worker
admission is claimed. No copying, process/network/installer or ACL operations.

Qualification: actual hardlink fixtures are tested. Symlink tests use a real
symlink when available and an explicit metadata-control fallback otherwise;
that control is not native reparse qualification. No physical smoke is started.
All failed runs/probes are retained in external physical-package-evidence-20261109.
A documentation update encountered Windows default text encoding; this plan is
rewritten as explicit UTF-8 ASCII. Source/test bytes were unaffected by that error.
