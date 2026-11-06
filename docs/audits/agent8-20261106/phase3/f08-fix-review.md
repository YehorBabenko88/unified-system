# F08 independent fix review

PR: https://github.com/YehorBabenko88/unified-system/pull/22

Exact source: `c0965c5612227662d3673820865aeee703cb5452`.

**F08: FIX VERIFIED — offline exact-source scope only. Overall NO-GO remains.**

The auditor loaded the exact committed validator bytes independently of checkout newline conversion. The original valid ownership document is accepted. All15 negative probes are rejected: the original Windows case alias, parent traversal and backslash aliases; seven owner-added malformed variants; plus Git metadata, NUL.txt, nested traversal, mixed-case collision and trailing-space paths. The10 source registry regression tests also pass with zero skips. All five manifest reference hashes match the exact Git blobs.

Original failure evidence remains in phase2. Recheck evidence: [f08-recheck.json](f08-recheck.json), [registry-regression.log](registry-regression.log). Reproduction harness: [recheck_f08.py](../recheck_f08.py).

At observation, exact-source registry CI jobs `registry (windows-2022)` and `registry (ubuntu-24.04)` are **queued**, not PASS. [Original check snapshot](current-check-runs.json). No completion of mandatory Windows CI is inferred from the local tests.

Current open findings: **6 P1 / 1 P2; zero independently confirmed P0, with no proof of P0 absence.** F08 is retained as a resolved, source-scoped finding and must be revalidated if the relevant source changes.

Global ownership ACK remains pending A7/A8 metadata and other allocation checks. Mandatory-gate registry ACK remains pending explicit workflow/case/platform/run-attempt/skip mapping. The package is not an approved installable release. Runtime admission, physical acceptance, deployment and Tailscale removal remain BLOCKED/not authorized.

Integration Owner has received the exact-source result and scope limitations. No production implementation was changed by the auditor.
