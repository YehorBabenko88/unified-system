# Intelligence Gateway implementation plan

Goal: add an independently testable, non-actuating preparation boundary to Unified.
Architecture: reuse owner APIs through future approved adapters; no new engine,
ledger, registry or authority. Tech: stdlib Python 3.12.10. Spec: user directive
and docs/intelligence/gateway-design.md. Existing P0 tasks continue unchanged.

- [x] Inspect current Control API, Supervisor, Mission, CI, Storage owner seams.
- [x] Reserve new files and immutable source base; separate feature/worktree.
- [x] Write contract/security tests, capture missing-module RED, implement local
  catalog/query/research preparation; 16-case initial GREEN.
- [ ] Execute committed exact source in fresh raw clone; publish full evidence.
- [ ] Draft PR and independent A8 review.
- [ ] Owner API/schema ACKs; do not infer permission from silence.
- [ ] Actual authenticated client, quota/fencing, query and research dispatch.
- [ ] Existing registry/visualization/observer integration and actual-engine E2E.
- [ ] Terminal required CI and independently qualified runtime admission.

Review focus: unknown fields/secret inputs, malformed scalar types, bounded JSON,
partial/stale source metadata, text pretending authority, no fake market data,
period ordering vs genuine leakage proof, costing vs existing ledger semantics,
claims vs actual effects. Every local result remains unverified/nonexecuted.
