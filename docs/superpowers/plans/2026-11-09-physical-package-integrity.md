# Pure package integrity implementation ledger

Base: `ba2b1cec0c2b114586afb73696e282117eede987`.
Owned files: `tools/physical_dev/package.py`,
`tests/physical_dev/test_package.py`, and this plan. Root owns physical execution.

I am using the executing-plans skill for the bounded package portion of Root's
LS5 physical development plan. The owner directive does not grant this library
runtime, native-worker or physical-test authority.

- [x] RED: snapshot closure, namespace and identity/size mutations.
- [x] Implement snapshot with hard file/count/byte bounds and guarded local paths.
- [x] RED: external digest, canonical closed manifest and descriptive metadata.
- [x] Implement in-memory manifest creation and data-only verification.
- [x] Exact isolated focused suite; preserve all RED/intermediate logs.
- [ ] Commit, fresh exact source/test receipt, push owned branch and Draft PR.
- [ ] Independent Root review before import or any physical action.

Ruling: manifest bytes are returned in memory and supplied externally to verify,
not written inside the package â€” self-containing digests cannot pin their own
bytes. Every on-disk file under root, including hidden files, is a package member.
Empty directories are checked for path/alias/reparse safety but are not file
manifest entries; file-only closure does not attest empty-directory inventory.

Ruling: source metadata has closed descriptive fields `description`, `sources`
(name/repository/commit/tree), and `dependencies` (name/version). Valid SHA syntax
does not establish Git provenance, approved origins, dependency trust or consent.
Root must separately admit exact sources/tooling. Fixed public submit DENY and
runtime/physical authorization false are checked, never derived from model data.

Ruling: default/hard ceilings are 20000 files, 1 GiB total content, 1024 path
characters, 255 characters per component, 8 MiB manifest bytes, 64 KiB metadata,
32 descriptive sources and 128 dependencies. Callers may reduce snapshot limits.
Count/size integers reject bool. Portable path checks reject traversal, drive/
backslash/controls, Win32 aliases/device names and casefold or normalization
aliases. Namespace directory visits are also bounded to prevent empty-tree walks.

Ruling: stat/open/fstat and post-read identity/size/time comparisons detect ordinary
concurrent modification. They do not prove hostile-parent exclusion, immutable
filesystem semantics, private ACLs or atomic protection against an administrator.
No ACL changes, process execution, network, installer or production operation is
provided. Tests touch owned temporary fixtures only, without broad disk walks.


Verification ledger: 23 focused CPython 3.12.10 `-I -S -B` tests PASS with
zero skips. RED missing-library import, namespace aliases and surrogate paths
were observed before implementation/fixes; every intermediate failure is retained
outside the source tree under physical-package-evidence-20261109.

Ruling: Windows `DirEntry.stat` can report zero link/inode fields, so actual
Path.lstat data supplies namespace identity. A retained own-fixture probe found
pathname and descriptor ctime differ while identity/size/mtime match. Those
fields must agree across APIs; full ctime is still checked before/after within
each API. No native timestamp or reparse qualification is inferred from a mocked
metadata control. Actual hardlink fixtures are tested; the symlink test uses a
real symlink when available and an explicit metadata guard control otherwise.
