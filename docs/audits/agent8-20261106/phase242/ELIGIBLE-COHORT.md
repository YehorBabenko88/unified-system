# Proposed publication event eligibility — SOURCE ONLY

Exact workflow image is d6b72b66ff1b85b7e6b956568342ad6bd8bfcfbe,
tree066bbe51900e88dd53541baf29a777037ed10b5b. Seven new paths againstfb177:
grid/bybit_request_plan.py; two docs/market-data/agent3 cards/status;
tests/bybit_request_plan/test_request_plan.py and three fixture/attributes files.
No workflow edits. Candidate head branch source/agent3-bybit-request-plan-card-20261110.

Push on that exact branch:0 eligible workflows/jobs (other push patterns are
main,mission3/** or named foreign feature/codex branches). New Draft pull_request
against the exactfb177 base:7 unfiltered PR workflows,13 expanded jobs below.
Draft status does not suppress these jobs. These are static eligibility counts,
not run/job creation, scheduler acceptance, success, budget grant or permission.

| Workflow | Eligible expanded jobs | Selected execution route |
| --- | ---: | --- |
| history-integration.yml |3: synthetic Ubuntu/Windows + disposable-postgres Ubuntu | scripts/history_ci.py tests 'test_history*.py'; disposable PG18 branch |
| mission3-qualification.yml |2: linux-postgres18, windows-contracts | Linux full pytest --ignore=upstream; Windows deployment-agent tests plus qualification scripts |
| portable-sdk-qualification.yml |2: component-sdk powershell/pwsh | Windows component SDK/portable source qualification, pinned external source/catalog/bootstrap tools |
| preflight.yml |1: python-preflight | Imports config/worker/coordinator/etc; full pytest --ignore=upstream; explicit PG lifecycle/stress selections |
| provenance.yml |3: synthetic Ubuntu/Windows + disposable-postgres Ubuntu | five source/storage/migration/gateway test files; disposable branch two files |
| readonly-gateway.yml |1: synthetic-and-disposable-pg18 | tests/test_terminan_gateway_contract.py against owned PG18 |
| windows-bundle.yml |1: build-windows-bundle | Windows supervisor/runtime selections, release lifecycle unittest and assembly/preflight scripts |

The six other path-filtered PR workflows match coordination/authority/native/event
or named docs paths, not this seven-file delta, and are ineligible for this exact
comparison. No manual workflow_dispatch requested or counted. Recompute eligibility
if base branch/path diff/workflow image changes; never silently retarget to main.

Some workflows explicitly checkout PR head; others use default PR merge checkout.
Do not call every future run exactd6b72 without checking the actual source image.
Basefb177 is an ancestor now; its branch movement or merge-source change requires
fresh review. Default checkout and mandatory jobs are not disabled to force green.

Whole-cohort effects are broader than the qualified62: disposable databases,
native/SDK/child/service tests, external checkouts/downloads and source imports.
SelectedBybit/provider route analysis is in PROVIDER-CLOSURE.md. No13-job execution
or provider-safety qualification is granted by this source map.
