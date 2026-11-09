# Fixed-origin installed Git byte export

Root-approved proposal: export_git(destination) returns DATA only. Production
source/pin/parent cannot be supplied as arguments. Source is exactly
C:/Program Files/Git; parent is exactly
C:/Users/LS-5/.codex/native-e2e-evidence-20261109; output must be an absent
immediate ls5-git-export-* child. Root separately verifies source/parent ACLs.

Fixed cmd/git.exe SHA256 before any destination writes:
78211c7ed73988da93a6d8a33d47ec6187f464d7ea2a9a00c182bbd7a1ecf30f.

This narrowly allows already existing regular SOURCE hardlinks only. All source
paths/ancestors remain canonical ordinary and reparse/symlink-free. Complete
pre/post inventories and per-file hashes preserve dev/inode/linkcount/type/size/
mtime plus same-API full mode/ctime comparisons. Chunks are at most64KiB.
Outputs are byte copies created exclusively, verified ordinary single-link,
and never links. All source files including hidden are selected, with no silent
omissions. Limits:20000 files,1GiB,40000 visited entries. Failure retains partial
evidence and never deletes or adopts old outputs.

The returned receipt is external DATA: Root may save it outside the export tree.
It captures installed dependency bytes and their original identities/hashes;
it does not attest vendor signatures, loaded DLLs, approved Git provenance or
execution authority. Public submit DENY/runtime false/physical authorization
false remain fixed. No process, network, ACL edits, installation or deletion.
assembly.py/package.py/materialize.py policies remain unchanged.

- [x] RED missing helper and bounded fixture refusals.
- [x] Implement narrowly fixed-origin exporter.
- [x] Focused tests and fresh exact-source verification.
- [ ] GitHub source pin/Draft before any Root actual export.

Tests patch fixed source/parent/main-pin constants only to owned inert temporary
fixtures. They do not read/export the actual Git installation. Metadata controls
are not native reparse qualification. Root actual export requires independent
source/isolation review after this GitHub source is published.


Local qualification: 74 focused tests PASS, zero skips (14 export + 60 existing
package/planner/materializer). RED covers missing helper, full-prewrite main-pin
race and empty-directory omission. Complete directory closure is now copied and
checked, including empty directories; the receipt lists directories externally.
Main executable digest is checked both early and against the complete prewrite
snapshot, preventing a changed same-size/mtime fixture from reusing an old pin.
The original shared source-hardlink refusals are unchanged. All test exports are
inert owned fixtures with patched source/parent/main pin; no actual installed Git
export or physical app execution occurred. Root actual export remains reviewed,
source-pinned and separately admitted.
