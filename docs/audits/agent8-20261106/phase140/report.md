# PR74 descriptor cleanup successor: source-only acceptance

Exact Draft PR74 HEAD `e5e9d440a5c8c44b4daaecbe6ed518c990481c74`, tree `00dd3c02c31ee14fe92ffd4af268dde86e5ba3a2`, independently confirmed against GitHub metadata and Git objects. Both source modules must be adopted together: materialize SHA256 `451ad1f9bb12c779e761f1c0aae88ed6903b4f00762515b0ceeef8fd161f9325`; export_git `6e7adc557b3cbb51717868346c83ae82f645625bad6ce8385042304e36bd0823`.

| Requirement ID | Repository / PR / Exact HEAD | Test name / Environment | Expected | Actual / status | Evidence | Severity / Required correction |
|---|---|---|---|---|---|---|
| A8-HEAD-140 | unified-system / PR74 / e5 above | GitHub Draft metadata, Git tree, all raw primary bytes / isolated review clone | Exact immutable source binding | PASS_SOURCE:1654 files, no extras | [metadata](GitHub-PR74.original-metadata.json), [source map and AST](source-verification.json) | No new source discrepancy |
| A8-F31 | Same exact pair | Static cleanup control flow review / no helper import | Independent close attempts; original error preserved; cleanup cannot return success | SOURCE_CORRECTION_ACK; runtime qualification NOT_RUN | Same source/AST | P2 remains pending independent runtime regression; adopt BOTH modules |
| A8-FAULT-140 | Same | Owner80 and Root integrated101 / not A8 runs | Independent execution evidence | NOT_RUN_BY_A8, owner claims not authenticated here | Scope recorded here | No runtime PASS transfer |
| A8-PACKAGE-140 | Actual assembled package not supplied | Isolation/package acceptance | Exact package/external manifest, invocation and readiness | BLOCKED pending concrete package review | Root status only | Separate admission remains required |

The shared helper loops over only the two issued descriptors, catches each close failure independently, and attempts each close once without ambiguous retry or deletion. Both callers explicitly initialize original=None and capture only exceptions raised inside their own operation. An already-handled caller exception therefore cannot suppress a fresh cleanup failure. With an operation failure the original exception is re-raised and gets an OWNED_FD_CLOSE_FAILED note; otherwise the first cleanup failure propagates with roles/types noted. Partial output remains evidence. This source correction addresses the precise sequential-close defect; it does not prove OS close success or absence of retained descriptors at runtime.

Six added inert regressions cover each copier's target-close failure, prior write failure plus close failure, and handled caller-except context. They assert both close attempts and primary exception identity, with fallback limited to fixture-owned pending descriptors. A8 inspected their source but did not import or execute them. Owner80 and Root101 remain distinct LOCAL_NOT_HOSTED claims. Assembly and shared package bytes are unchanged from f6; all previously reviewed source bounds and single-link destination policy remain scoped as before. No new high-confidence actionable finding was identified in this four-file diff.

Initial own clone checkout normalized line endings, so raw-byte inventory correctly rejected it twice before any success claim. Only this disposable review clone was rewritten from its exact Git blobs, then all1654 raw files matched. These were audit preparation failures, not application tests. No production file or owner implementation was edited.

Root reports integrated PR69 HEAD461ee1d51f432dc1ccf419f22fd7c1cd41095a8e/tree62f3440a89b63e7454afebdeeb93c38b013a2f75 with both corrections and101 local pure passes. That integrated HEAD and receipt were not independently qualified in this addendum. Root's earlier f6 normal byte export is not evidence of e5 cleanup fault behavior. Root reports the full plan rejected20187 files versus20000 cap and is preparing a smaller exact shallow source copy without raising limits; A8 has not authenticated that plan or an assembled package. No execution admission follows from this source ACK.

RELEASE_MANIFEST_STATUS: actual assembled immutable package/external manifest SHA pending.
NODE_INVENTORY_STATUS: no new A8 host inventory or custody admission.
CONTRACT_STATUS: F31 SOURCE_CORRECTION_ACK at e5 only; existing core phase138 scope preserved.
OFFLINE_TESTS: static source/raw checks only;0 A8 helper imports/calls/fault tests.
WINDOWS_CI: owner80/Root101 not A8 or hosted acceptance; F26 remains open.
PHYSICAL_TESTS: BLOCKED for physical fault injection; no A8 physical execution.
P0_P1_P2:7 open P1 /6 P2; F31 source corrected, independent runtime qualification pending; absence of P0 not proven.
EVIDENCE: exact original PR metadata,1654-file raw map, reviewed AST and module digests.
NEXT_ACTIONS: review concrete assembled package, external SHA, invocation and fresh isolation readiness; independently qualify admitted runtime fault regressions separately.
GO_NO_GO: NO-GO. TAILSCALE_REMOVAL_ACCEPTANCE: BLOCKED; no automatic removal.
