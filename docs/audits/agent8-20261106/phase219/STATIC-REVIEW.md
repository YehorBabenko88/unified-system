# Terminan inherited runtime40 static review

Source: PR68 HEAD 7ed3708df53c8850fd11fc8331440bdfee99aa3e, tree 96963f7e749e73c8c81e7650bdee4f2a0a05923a. Reviewed the runtime_lab_UI_tools allocation in PER-FILE-OWNERSHIP-AND-SOURCE.json and all 40 corresponding source-135 files. All 253413 bytes match declared lengths, SHA256 and independently computed Git blob SHA1 identities. Exact per-file records are in VERIFIED-40-HASHES.json; ownership-map SHA256 e9b5209f172fee8830d21bdb24c58d4b49aa15feca14b670e756e5f895c90493.

## Finding R40-1 — P2: benchmark RAF escapes disposal and lifecycle accounting

Locations: terminan/r2_preview.js:196 and terminan/r4_preview.js:234; disposal at r2:180–184/r4:218–222; metrics at r2:177/r4:215.

Each benchmark awaits requestAnimationFrame without retaining its handle or a cancellation/settlement callback. The only cancelled and counted RAF is s.raf, which belongs to normal rendering. Therefore starting a benchmark and disposing before its next callback leaves a live benchmark callback/promise while metrics reports rafPending=0. Generation/disposed checks occur only after that callback runs. In a retained hidden iframe, the browser may suspend RAF delivery, so the promise and benchmarkRunning lock have no bounded cancellation path. This affects lifecycle/evidence accuracy and prompt workload cancellation; it does not grant source/execution authority or establish an unbounded allocation leak.

Minimal correction: independently own the benchmark RAF handle and pending rejection/settlement; cancel and settle it on disposal and cancellation, and include it in lifecycle accounting. Preserve the existing workload/sample bounds. Add an inert scheduler regression that holds the benchmark RAF, disposes or invalidates generation, and proves promise settlement and zero outstanding scheduler entries without delivering a browser frame. Existing r4.spec.cjs cancellation cases use seek while visible and do not exercise this boundary.

This is a static code-path finding, not a browser reproduction. No P1 identified in the reviewed scope.

## Reviewed behavior and limits

Reviewed protected provenance/startup call order, loopback Host/Origin and session gates, authenticated readiness disclosure, bounded snapshot reading/publication and strict schemas, stale/partial/unavailable preservation, render-buffer retention, workspace routing, cache response identity, browser assertions and evidence closure. Module readiness intentionally does not depend on the aggregate core-ready flag; test_module_readiness.py explicitly covers avoiding that startup cycle. Unverified observations remain unverified and physical/trading/deployment gates remain closed in the reviewed contracts. Missing ownership/admission acknowledgement was not treated as a code defect.

This review uses sealed packet bytes and static reading only. No project imports, collection, tests, browser, native process, network, GitHub action or runtime qualification was performed. External SourceFence implementation and the other 95 packet files were not semantically audited here; protected startup conclusions are limited to its visible caller/API and allocated tests. This is not an entire-135 acknowledgement, A8 admission, runtime/physical approval, hosted PASS, or proof that no other defects exist. Root owns shared CI10; A6 owns final synchronization/operations. No source files were edited.
