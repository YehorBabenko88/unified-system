# Windows package lock v2

`unified.windows-package-lock.v2` requires exactly six source identities:
`unified-system`, `grid`, `strattester`, `math`, `meta_analyse`, `terminan`.
Each source retains exact 40-character lowercase commit and tree pins. Python
uses the canonical `MODULE_IDS` catalog; the Windows verifier enforces the same
explicit inventory with case-sensitive identity matching.

Legacy `unified.windows-package-lock.v1` remains supported with exactly its
original five identities, including `unified`. Neither schema accepts the other
inventory; changing only the schema cannot downgrade a six-source manifest.
Unknown schemas fail closed. Both versions retain the PS5.1/7 and PostgreSQL18
contract, bounded dependency closure and artifact bytes, hashes and publisher
pins. The Windows verifier still requires detached SignedCms verification,
expected process SID, protected ACLs and paths without reparse ancestors before
returning its dry-run result. Python validation alone never verifies signatures.

This change authorizes no package execution, source admission, host changes or
physical readiness. Plans remain PLAN_ONLY / admission NOT_GRANTED. Windows
signing tests require Windows and are NOT_RUN in the Linux development session.
