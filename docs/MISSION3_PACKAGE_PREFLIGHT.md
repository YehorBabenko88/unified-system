# Isolated prepare-only package preflight

The native caller must verify an absolute Python executable and the raw
`unified_system/package_preflight.py` against independently supplied hashes before
launch. Package contents, publisher fields and environment variables cannot
supply those tooling pins. Launch the raw script with effective `-I -S -B`:

```
PinnedPython -I -S -B PinnedPreflight --source-root ROOT --source-head HEAD40 --source-tree TREE40 --source-guard-sha256 GUARD64 --git-executable ABSOLUTE_GIT --git-sha256 GIT64 --package-root PACKAGE --publisher-sha256 PUBLISHER64
```

All source/Git/publisher pins are external inputs. The helper verifies the raw
source guard against its external pin, executes those verified bytes directly,
and uses that shared guard with the exact pinned Git executable to verify the
complete Root commit/tree before importing any Root package. Its postcheck
requires the same source bytes. A fresh private temporary cache is set before
project imports and removed on both success and failure. Optional `--cache-root`
selects an existing local directory; otherwise a lexical system-temp setting is
validated before any directory creation. UNC, mapped drives, links and reparse
namespaces are refused before descendant metadata access.

The helper reuses `release_manifest.parse_manifest`; it does not duplicate the
release schema. Each of the six artifact files is opened read only, checked as a
single-link regular file, and hashed in bounded chunks against the declared
size/digest. It does not extract archives, install services, contact a database,
perform enrollment or authorize execution. It does not verify CMS itself.

Successful JSON has schema `unified.package-preflight.v1`, mode `PREPARE_ONLY`,
`modules: 6`, the canonical manifest SHA256, source head/tree and release ID.
`signature` remains `EXTERNAL_CMS_REQUIRED`, services `NOT_INSTALLED`, physical
`NOT_AUTHORIZED`, and execution/trading/physical-deployment flags false. The
native caller must retain its separate pinned CMS publisher check and physical
execution restrictions. A successful preflight is integrity evidence only.

`python -m unittest tests.test_package_preflight tests.test_release_manifest -v`
uses disposable local source repositories and inert artifact fixtures. It proves
that an actually executable timestamp-valid poisoned cache and hostile ambient
import path cannot replace the pinned source; tampered source/tooling, missing
interpreter flags and bad artifacts fail closed. Native Windows caller tests
remain separate.
