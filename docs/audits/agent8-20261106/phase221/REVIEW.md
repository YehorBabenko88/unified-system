# Final Sync delta and Operations: allocated static source review

2026-11-10. Reviewer: Agent6, owner-side static review requested by Root. This is
not an independent A8 seal or admission of the 135-path stack. Imports, project
execution, tests, browser/native/provider/physical calls, code changes, policy
edits and new CI runs: zero. Git/blob/hash/data inspection and original CI
metadata/log retrieval only.

## Exact reviewed source and finding

Sync: PR69 HEAD 10e07ef108d155b9ca2278eec6a8361cb92fa488, tree
899ab6ec331784aa4e512050c75665cecfa9385e; all 12 changed/added paths relative to
A8-reviewed intermediate 42686cd8fafcefaed3c5df5adaee5173d27543fd. Operations:
PR70 HEAD c752dff751d964c57daf3b3afe4987ea3377839b, tree
8e19a76b13893f5e6d3103fd599f7fcec25644ca; all four added paths relative to 10e07ef.
Each of the 16 raw files matched its original exact PR Git blob and prior package
SHA256; file pins and exact diffs are attached. Unchanged protocol/client/view and
existing contract/client tests were read as context. No old test outcome is rerun
or extended by this review.

**No new runtime-source P1/P2 identified in this bounded review. One concrete
documentation P2:** `docs/operations/operations-dashboard-contract.md:182` says
"the22 frozen IDs,21passes,0fail/cancel/skip/todo". Final workflow and
`tests/operations/test_dashboard.cjs` require exactly 22 IDs and 22 passes. The
documentation command cannot describe a valid passing receipt. Correct only the
stale pass-count literal when the owner allocates a docs change; do not change
tests/count guards or reinterpret historical 21-case evidence. No fix made here.

No new implementation P0 or P1 is asserted. Missing runtime endpoints and stack
admission remain separate release gates, not newly reproduced code defects.

## Preserved invariants observed in source

| Boundary | Static observation and limits |
| --- | --- |
| Snapshot/generation/revision | Final delta does not alter protocol.js or client.js. Existing install validates stream/generation/cursor/resource metadata, replaces state after validation and requires a coherent snapshot; generation mismatch/gaps/resync clear resume cursor. No C3 frame feeds the v1 reducer. These are source observations, not runtime PASS. |
| Event sequence/dedup | Existing global sequence+1, prior revision and metadata rules remain; exact seen duplicate is ignored, conflicting/out-of-order input resyncs. Dataset sequence/metadata anchors remain separate. New framing returns C3 tokens only; it does not interpret sequence or manufacture authority. |
| Freshness/auth | Existing deadline/status logic and auth-error clearing are unchanged. `canMutate` remains false and `command()` throws. Default view creates SyncClient with no adapter; no authenticated source is assumed from parsed JSON or codec validity. Four integrity dimensions stay separate. |
| Reconnect/lifecycle | Existing epoch, abort, queue/pending bounds and retry rate logic unchanged. C3/Mux errors close decoder and clear its fragment buffer; reconnect requires a new decoder. Completed records in a failing same feed are not returned. Existing synchronous subscribe-failure guards remain unchanged. No new default transport or retry loop added. |
| C3 text boundary | Primitive strings only; ASCII/no numeric JSON tokens/no whitespace aliases; canonical sorted unique keys, restricted escaping and bounded bytes/depth/nodes/members/arrays/strings. Detached frozen values/null-prototype objects and WeakMap-branded tokens; no host graph writer, reflective Proxy probe or authority claim. The 28 fixture vectors were read as data and hash-checked, not executed. |
| Mux framing | Exact data-prefix and LF-LF records; ASCII scan, bounded chunk/record/batch/pending fragments; C3 validation before return; malformed record closes/discards batch. Envelope/domain/epoch/freshness validation is still a future caller obligation. Conservative client caps are not service throughput guarantees. |
| Static preview | serve.py changes only its allowlisted assets to include c3/mux. Existing loopback bind, Host/Origin guard, exact paths, no-store/nosniff and connect-src none remain. No API/backend route added. No server launched by reviewer. |
| Ops parsing | Closed embedded schema and bounded detached JSON decode; decoded duplicate keys refused; integer tokens checked before Number conversion; unique identities/source links/tuple keys, date validity and fixed CI non-authorizing provenance rules retained. Source pins and producer claims remain unverified data. |
| Ops actions/authority | Five operational axes accept UNKNOWN/UNAVAILABLE only. Effects/native authority/NodeOp conversion/grants remain false, installed/service facts unavailable, lifecycle PLAN/BLOCKED/UNKNOWN. Renderer uses textContent and fresh replacement, persistent qualifier banners, collapsed evidence and disabled buttons without handlers/providers/network/timers. Journal COMPLETED/AUTHORIZED/PASS, development physical PASS and CI SUCCESS are explicitly non-authorizing claims. |
| Qualification | Ops workflow pins actions/Node, bootstraps primary Git test bytes, selects exact 22 IDs and verifies complete raw source before/after. Sync runner remains a preliminary selected-source/count receipt: normalized identity plus raw hash recording before execution, no complete raw pre/post closure. This known weaker boundary is not strengthened or rebranded by the new 84 count. No qualification script was run. |

## Original PR CI attribution correction

The earlier broad phrasing that all general PR jobs stopped before tests was
incorrect. Original run 42866017216, attempt 1, exact dc810b0, fails identity step
8 with REVIEW_BASE_DRIFT; Python contracts step 9 is skipped. Steps 10–44 include
many `!cancelled()` conditions and actually continue. Original job metadata and
full logs were retrieved read-only. Per Windows job: 33 later main steps SUCCESS,
2 SKIPPED. Per Ubuntu job: 22 later main steps SUCCESS, 13 SKIPPED. All four job
conclusions and the run conclusion remain FAILURE.

All four execute PS7/R3/R4 propagation, real transport 15/600 lifecycle checks,
R4 15/600 session lifecycle, syntax/compile, pinned browser dependencies, their
OS browser-engine installation, synthetic browser/evidence, R3 workloads/benchmark,
R4 browser/session/evidence, saved-workspace browser/evidence and artifact upload.
Windows additionally executes the PS5.1/console and R2 harness/evidence steps;
Ubuntu executes the owned-child lifecycle step. API step success is attributed to
those original hosted jobs; no fresh runtime result or physical qualification is
claimed here, and no bypass/security-admission conclusion follows from scheduling.

Exact per-job names/numbers/conclusions/timestamps are saved in
`../hosted-original/ORIGINAL-CI-POST-GATE-CORRECTION.json`, with original jobs API
JSON and full log hashes. Earlier reports/logs remain immutable and are superseded
only on this attribution point. No original run was retried, skipped or cancelled.

## Decision boundary

Allocated static review is complete with the one documentation P2 above. This does
not invent an old final ACK, close Root/A8 shared CI10/runtime40 review, or grant
full-stack source admission. Root/A8 determine disposition of these findings and
the exact predecessor composition. Policy script/test edits remain HELD. Existing
45/4, 84, 22 and 30 test counts remain their separately attributed historical
evidence, not new executions in this task. Scientific READ/final visibility NONE;
runtime/physical admission NO-GO.
