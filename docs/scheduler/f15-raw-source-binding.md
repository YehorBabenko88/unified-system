# F15 — raw source snapshot binding correction

A8 reproduced the metadata-only evidence defect on175b48a: a harmless tracked
comment plus assume-unchanged kept HEAD/tree/status clean and yielded30 tests PASS
with receipt.passed=true although executed raw bytes differed from committed source.
Agent5 independently reproduced this RED in an isolated local clone. This is not
an allegation that hosted runs were tampered with, or a scheduler runtime defect.

The narrow correction changes only the dedicated workflow and own audit docs.
No scheduler module, component test body,30-ID inventory, dependency or factory changed.

## Guard

The job sets core.autocrlf=false/core.eol=lf through Git environment configuration
before checkout. The guard does not forgive CRLF or normalize any input bytes.
For captured source HEAD, NUL-delimited ls-tree supplies path/mode/blob OID.
cat-file reads each committed blob by OID, avoiding revision:path command ambiguity.
Raw regular files, including their non-reparse directory chain, are checked before
test import and after execution. Protected inputs are all tracked scheduler_components
files, the dedicated test file, exact inventory JSON and dedicated workflow. Required
inputs and unexpected non-cache package files are checked as well.

Each snapshot publishes path, Git mode/blob OID, expected/actual byte counts and
SHA256, regular-file status and match result. The existing HEAD/tree/status check
is supplementary; index flags cannot substitute for the raw comparison.
The inventory is read only after raw binding admission. Final success requires
matching valid before/after snapshots, exact30 IDs, no skips/errors/failures and
the original test-log hash. Receipt remains component-evidence.v2.

## Isolated controls

Agent5's local clone harness uses actual30 tests and runs the embedded candidate
Python block. Controls are not hosted evidence:

- Clean LF files:30 PASS, zero skips, both snapshots match.
- Hidden comments in source, test or workflow, and hidden inventory whitespace:
  precheck rejects before running tests despite clean index status.
- Hidden CRLF rewrite: rejects without normalization forgiveness.
- Missing protected file or regular file replaced with directory: rejects.
- Hidden comment after30 successful tests: after snapshot rejects receipt success.

Raw source snapshot checks do not attest installed dependencies or continuously
observe runtime memory. Independent A8 exact-source review and new hosted artifact
verification are required; earlier175b/942e receipts are historical only.
