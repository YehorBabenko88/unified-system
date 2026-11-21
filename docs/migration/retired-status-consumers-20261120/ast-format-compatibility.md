# AST fingerprint representation

Python3.13 changed ast.dump's default to omit optional empty lists: https://docs.python.org/3.13/library/ast.html#ast.dump . Existing immutable14assertion fingerprints include these lists. The verifier explicitly requests show_empty=True and falls back to the original API on3.11/3.12. No inventory/archive/assertion hash is repinned.

The original7archive tests include two formatter API calibrations. Both pass on local3.11/3.12; the3.13-style default is a formatter surrogate, not actual3.13 execution. The dedicated workflow now mandates3.11/3.12/3.13 on Windows/Linux. Actual3.13 results must come from the new exactHEAD CI. Runtime obligations remainHELD/NO_GO.
