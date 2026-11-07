# Independent F16 Git provenance review

Overall NO-GO. F16 remains globally OPEN (P2); 6 P1 and 2 P2 remain open. Physical tests and Tailscale removal BLOCKED.

Environment: isolated Windows clones, Python 3.12 audit venv, synthetic Git fixtures only. No native/financial execution, real orders, network changes or physical fault injection.

| Requirement | Repository / PR | Exact HEAD | Test / expected | Actual | Status | Severity / correction |
|---|---|---|---|---|---|---|
| F16 Git replacement provenance | meta_analyse PR78 | f3c01a23fa5baaeeeb28eb8e9397e72b5ef4d5a1 | 10 clean/blob/tree/commit and dirty-check controls, two namespaces; retain original tree | 10 pass, 0 skip; baseline 88b45c3 has 4 failures/6 passes | PASS, offline only | P2 component fix verified; global F16 pending |
| F16 Git replacement conformance | strattester PR72 | 88a180b29afe9c85ddea26ef98cbe0bec8de24a6 | 10 controls; clean source reaches intentional unknown-gate denial; real dirty source rejected | 10 pass, 0 skip; baseline 1722244 has 4 failures/6 passes | PASS, source preconditions only | P2 component fix verified; financial acceptance remains BLOCKED |
| Mandatory hosted / Windows CI | Both exact heads | Above | Completed original mandatory runs/artifacts | Required jobs QUEUED at snapshot; Meta synthetic/disposable-postgres18 SKIPPED | BLOCKED | No previous HEAD CI result transferred |

Meta tree c155c935a801fa98b7c78219c9798ce1f1be8848; Stratt tree 572e530db6fca4beff5cbfa3efc9317964fca5ef. Fresh primary PR metadata confirms Draft status and exact base/head pins. Meta changes six paths; Stratt three. Product implementation, prior skip/JUnit/financial aggregation policies unchanged; only Git resolution flags, dedicated tests and audit docs changed.

Meta corrects wrong-tree metadata under a commit replacement with unchanged HEAD. Stratt corrects a false-dirty fail-closed availability defect; this review does not claim prior forged financial PASS. Both preserve dirty-source rejection. Source authenticity remains NOT_EVALUATED: replacement-independent metadata does not by itself authenticate every executed source byte in hosted jobs.

Every outer clone has its own .git/common directory and no object alternates; fixtures create independent no-hardlink clones. No refs were changed in developer/shared linked worktrees. Raw tracked blobs were independently verified before/after: Meta 782 files, Stratt 765. Baseline source bytes also verified unchanged. New tests were copied to baseline clones solely for RED controls. The reviewer did not run the complete 68/50 owner-selected suites; only these 10 cases per source, source-diff review and raw-file checks are independently adopted here.

Evidence: [machine report](a7-git-provenance-review.json), per-repository PR/check JSON, baseline/fixed original stdout/stderr and JUnit XML alongside this report. Harness: ../review_a7_git_provenance.py. Required next correction: independently verify pending A3/ROOT and other applicable F16 guards, then reassess global F16; separately complete mandatory hosted CI and integration/physical gates.
