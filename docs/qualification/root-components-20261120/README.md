# Root component CI source repair — NO_GO

Base f69334874c3d5a40c9fabed0a65925260ae3efa1. The four existing component test families already use canonical four-owner fixtures. No Grid/Meta source checkout/import is added or retained by this workflow set. Physical six-node tests remain physical-fleet-count checks, not a six-owner architecture.

Confirmed defect: final-integration and supervisor-local-integration used wasSuccessful()+count+no-skips, which accepts unittest.expectedFailures. The new qualifier rejects expectedFailures and unexpectedSuccesses as well as failures/errors/skips and exact-ID drift. All original161 final IDs (including145 earlier mandatory IDs) and132 supervisor IDs (including async methods) are preserved exactly in groups.json. Combined2 and fleet15 cases remain exact. Original raw workflow snapshots/hashes retain the old gates and roster lineage. No test-method bodies or core/runtime modules are edited.

Four workflows now run only main pushes plus every prior pull_request gate/path selection; workflow_dispatch is available. Existing OS/Python axes remain. five-module-infra.yml becomes four-owner-infra.yml with no alias. All actions use immutable pins; custom PS source identity is replaced by the actual Python qualifier. Full finalTLS/PowerShell/process and supervisor process-crash cases remain actual mandatory HOSTED tests, not fake or skipped local replacements. Original hash-pinned timezone dependency is retained.

The qualifier reuses SourceFence for exact HEAD/metadata/raw Git source/loaded module origin and pre/post checks, plus stricter raw-identical tracked-only repository walking and fresh ordinary local outside-source evidence/cache. Source receipts and logs live outside the checkout. Original compileall obligations use compile(raw,filename,'exec',dont_inherit=True) without execution or bytecode; negative calibrations prove break/return/continue outside valid context refuse (AST parsing alone is insufficient). No native product capability or authority is constructed.

Local proof:6 new pure calibrations +15 existing fleet/inventory +6 existing mission-workflow inventory checks =27 cases PASS eachPython3.11/3.12, with audit denying socket/process/system/ctypes/SQL. Two changed/new Python files and five embedded workflow steps compile without execution. Full161/132 runs, SourceFence Windows/Git/namespace operations, TLS/PowerShell/process tests and hosted outcomes are NOT_RUN locally. This source change is not full E2E/native/physical/production acceptance.

No Root paper/publication/core/native/bootstrap/installer code, external owner source, job cancellation or security settings are changed.

The six pure qualifier calibrations are also mandatory separate hosted gates before each unchanged component roster; their IDs/counts are reported separately rather than folded into161/132.
