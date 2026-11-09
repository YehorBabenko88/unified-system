# Bounded assembly copy-plan ledger

Base package library: 73bb603c1ec4dd02b2f5cca06377ed677199e54e.
Ownership: assembly.py, test_assembly.py and this plan only. package.py remains
unchanged. Root owns source provenance, private parent admission and execution.

- [x] RED for missing assembly helper.
- [x] Implement read-only component planner and destination boundary checks.
- [x] Focused exact source tests and retained failures.
- [ ] Commit/push owned feature and Draft PR; no assembly or physical actions.

API: plan_assembly(components, destination, max_files=20000, max_bytes=1GiB).
Each closed component has name, source_root, destination_prefix and profile.
Profiles: closed-tree (all files including hidden/.git), python-stdlib (source
root is the full Python installation; omit exact Lib/site-packages subtree,
every __pycache__ subtree and files with .pyc/.pyo suffix, case-insensitively).
All other Python files, including DLLs and extension modules, remain selected.

The selected file table is a deterministic COPY_PLAN_DATA_ONLY result. Skipped
entries list exact source-relative paths/reasons; subtree contents are not
enumerated. skipped_entry_count counts pruned subtree roots and direct files,
not unknown numbers of files inside excluded directories. Global file/byte
bounds cover all components, and a bounded visited-entry count prevents empty
tree expansion. Overflow refuses the whole plan; no truncation or silent cap.

Source roots cannot overlap. Destination prefixes may share folders only when the actual merged file map
has no exact duplicates, casefold aliases or file-as-directory conflicts.
Duplicate final keys are refused before dictionary insertion, even for identical
bytes; global package namespace validation remains mandatory.
Destination must be absent with canonical ordinary existing ancestors, outside
all sources. It is never created or reserved. Private parent ACL remains UNKNOWN;
Root must independently admit it and perform exclusive creation/revalidation
before copying. Namespace checks do not establish hostile-parent atomicity.

The planner reuses package integrity path/hash guards without changing that
module. Source metadata does not establish Git provenance: Root's existing
primary verifier remains responsible for exact origin/commit/tree/raw closure.
No process, native job/browser, actual copy/install, download/network or ACL
write is provided or exercised. Tests use owned temporary files only.


Root authorized byte-exact corrected package.py import from PR69 commit
baa7d4d0255633f4e15a28de599f3852a9573b73 (SHA256
5bd7c81f15bd38019236ab5e5580dff894e1a701902a9351e0217d500db2f0c8).
The original package base is 73bb603c1ec4dd02b2f5cca06377ed677199e54e.
No package logic is independently changed here: this import fixes the observed
Windows .exe pathname/descriptor permission-bit discrepancy, preserving same-API
mode checks and cross-API type/identity/size/mtime. Its failing inert.exe planner
case and actual stat probe are retained externally. Root owns the correction.

The final local suite has 40 focused tests PASS, zero skips (16 assembly plus
24 original package). All source components are re-inventoried after all file
hashes, including a RED/GREEN cross-component concurrent mutation case. Bounds
are global 20000 selected files / 1GiB, 40000 visited entries / 32 components,
and 32MiB returned canonical plan. Closed-tree installs over those bounds refuse
without truncation. No actual package assembly, destination allocation or native
process/browser/Job action was performed.


Root-authorized compatibility adjustment preserves 4a8947c11b9d100f155385182c20956bd0d80368
as an immutable parent. A package-lock singleton seed at prefix tooling can now
coexist with disjoint tooling/node_modules, tooling/git and other file maps.
Source-root overlap, canonical path rules, fixed materializer parent, 20000 files
and 1GiB limits are unchanged. New REDs capture the old blanket overlap refusal
and the duplicate-overwrite risk after its removal. The final 60 focused tests
PASS without skips (21 planner, 15 materializer, 24 package). Only inert temporary
unit fixtures are exercised; no actual package or physical copy was performed.
