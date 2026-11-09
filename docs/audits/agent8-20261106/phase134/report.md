# PR68 source/safety review, runtime lane pending

Exact Unified Draft PR68 HEAD `ba2b1cec0c2b114586afb73696e282117eede987`, tree `4e5c535367e4e7711a64096ff6e9c78038c55717`, base034. Initially reviewed from the private local primary commit; subsequently published unchanged. Independent GitHub connector metadata confirms the same Draft head/base, and A8 fetched that exact commit from GitHub. No merge or deployment occurred.

| Requirement ID | Repository / PR / exact HEAD | Verification | Environment | Expected | Actual / status | Evidence | Severity / correction |
|---|---|---|---|---|---|---|---|
| A8-F27-CONSUMER-SOURCE | Unified PR68 /ba2 above; Grid2f | Exact diff, module pins, broker and CI imports, static inventory | Own no-hardlinks clone, primary Git/source reads | Explicit corrected source pair; entry/cleanup client custody checks; no unknown-client cleanup RPC | SOURCE_REVIEW_ONLY: no new actionable blocking source finding in reviewed scope | [Static checks](static-source-verification.json), [primary maps](static-primary-binding.json), [original PR metadata](GitHub-PR68.original-metadata.json) | Existing F27 P1 remains open pending independent runtime qualification |
| A8-F27-CONSUMER-RUNTIME | Same exact candidate | Actual21 and custody-loss fixture | A8 isolated runtime | Later independent exact-source execution after serial lane handoff | NOT_RUN: Root explicitly retains serial runtime lane for Direct22 | No A8 runtime receipt exists | Do not transfer owner21/145/Direct22 PASS; wait for explicit lane release |

All1642 Unified and821 Grid2f files match primary Git raw bytes with no extras. A8 parsed source/AST only, without product imports or runtime fixtures. Four CI files are byte-identical to exact639; broker runtime file is byte-identical to PR67/481. All five pinned module hashes and manifest root modulebb56 match actual admitted source files. Old16 test methods retain equal AST, and exactlyfive additions match the21-ID inventory. Target runtime files are absent from the19-path diff.

The entry gate requires exact owned/open AsyncClient, trust_envFalse, default transport, no mounts/redirects, and captured same client/config identities before authentication and cleanup. On cleanup custody loss, only fixed synchronous local invalidation runs; original operation error retains native-cleanup UNKNOWN and _busy clears in finally. Healthy cleanup retains its prior native best-effort behavior, not a strong retirement receipt.

Exclusive authority/client/config ownership throughout operation AND cleanup remains essential. Entry checks do not establish every-await protection or supported concurrent reconfiguration. The deliberate test fault replaces the client at a controlled error-return boundary after an actual read. Ambiguous open_session SID custody remains UNKNOWN; no exactly-once authentication or automatic orphan adoption/rollback is claimed. These limits are explicit in CLIENT-CUSTODY.md and match the narrow reviewed source scope. Static review does not prove the new fixture actually passed.

No own21/145/Direct22 runtime, Consul, proxy trap or child fixture was started. Root reported its own21 and145 and an in-progress Direct22; those receipts/runs are not independently authenticated or counted here. Source-only review establishes no positive research job, registration/worker grant, native API freeze, hosted matrix, physical acceptance or Tailscale independence.

RELEASE_MANIFEST_STATUS: component candidate only, no approved release.
NODE_INVENTORY_STATUS: not requalified.
CONTRACT_STATUS: consumer source/safety review completed in narrow scope; runtime pending.
OFFLINE_TESTS: static checks only; runtime NOT_RUN.
WINDOWS_CI: hosted NOT_RUN here; F26 remains open.
PHYSICAL_TESTS: BLOCKED.
P0_P1_P2: 8 open P1 /3 P2 unchanged; F27 open, absence of P0 not proven.
EVIDENCE: original current PR metadata, static checks and primary maps above.
NEXT_ACTIONS: explicit Root serial lane handoff, then independent actual21 qualification on exact published source; original hosted artifacts separate.
GO_NO_GO: NO-GO; TAILSCALE_REMOVAL BLOCKED.
