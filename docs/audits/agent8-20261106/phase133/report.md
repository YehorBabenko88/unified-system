# PR67 independent minimal local-only broker API

Exact Unified Draft PR67 HEAD `327a3e2ca6106d2d39eb8f0da3802560e63b09e6`, tree `5dba9da0b13884b1db324c694884a7ecf793368a`, parent31105. GitHub connector independently confirms current Draft head. New broker SHA `481724cd2efca312773fa4152d1c223b46ced6529d96b2d74f452cdf57932d7f`. Explicit Grid dependency `2f94da511681811588e0f850a0a0e9dc4479c8b8`, Core3dd/module5b97. Source/safety review preceded execution. Six paths changed; runtime adds only eight synchronous helper lines. Removing that helper produces an AST identical to the whole old module. READ840 is byte unchanged; no wire13/scope/schema change appears in the diff.

| Requirement ID | Repository / PR / exact HEAD | Test | Environment | Expected | Actual / status | Evidence | Severity / correction |
|---|---|---|---|---|---|---|---|
| A8-LOCAL-LATCH-67 | Unified PR67 /327a3e2 above, Grid2f | Three NEW committed actual LocalInvalidationTests only | Own Windows CPython3.12.10/httpx0.28.1, own ACL Consul triplet and actual mTLS contexts | Local latch without lost-client RPC/config/peer/clock access; captures denied; SID remains native; audit failure preserves latch | 3 unique PASS /0 skip | [Executed harness](executed.py), [original test log](stderr.log), [process/result stdout](stdout.log), [raw source receipt](receipt.json) | Scoped minimal API PASS, not Root consumer custody acceptance |
| A8-LATCH-SOURCE | Same exact sources | Whole old module AST and READ hash comparison, exact PR metadata | Primary Git/source reads | Add only the fixed helper, preserve other implementation | PASS | [Source review](source-review.json), [original PR metadata](GitHub-PR67.original-metadata.json) | No broader runtime/26-case transfer |

The first actual case creates genuine broker principal context/capture, replaces the transport with an explicitly proxied real client pointing only at an own trap, and calls the fixed helper with native _request/config/peer/clock fail-if-touched guards. It observes trap0 and restores the known original client before fixture cleanup. Old/future captures deny. A separate safe source-owned client reads the genuine native SID still present; broker retains its session inventory. Zero client/config/peer/clock access is also established by the reviewed eight-line helper; reading the replacement client field alone is not dynamically trapped by this case.

The second case rejects an UNISSUED exact-type context lookalike outside private inventory; it is not a separately commissioned foreign-broker context experiment. A real bounded audit store is filled, then helper raises after adding the owned SID to _invalid. Repeated invalidation returns None without auditing, and another actual context/capture remains unaffected. The third case observes a real unmodified native lock GET response, latches locally in the response observer, then actual final capture recheck denies; actual SID remains present. No native response, issued job or permission proof is fabricated. Return None is not native retirement or authority permission.

1523 Unified and821 Grid files matched primary Git raw bytes before/after, with no extras. All three retained own Consul processes (140608,135716,136584) were waited; own trap thread shut down/joined under committed assertions. Actual fixture authentication creates/cleans only own leader/principal sessions and identity records; it does not issue research jobs, native worker registration or effect grants. No provider, office, protected diagnostic, deployment or network-policy action occurred. Interpreter bootstrap is not native PID identity qualification.

A8 ran only these three new methods, not the full26. Owner26, owner historical partial RED, separate prior23/25/16, Coreproxy2 and localcustody13 results are not transferred to this pair. Owner receipt/source-closure artifacts were not independently authenticated here. No new actionable defect was established in the minimal API review. Root's future consumer must still qualify actual client ownership/identity/closed-state gates, exclusive lifecycle and cleanup after custody loss. This helper alone cannot establish those properties. F27 consumer remains open; no final native freeze or automatic source adoption follows.

RELEASE_MANIFEST_STATUS: no approved release or implicit pin advancement.
NODE_INVENTORY_STATUS: not requalified.
CONTRACT_STATUS: minimal local-only method independently verified; Root consumer/source adoption and native freeze separate.
OFFLINE_TESTS: focused3 new actual cases PASS /0 skip; full26 NOT_RUN.
WINDOWS_CI: hosted NOT_RUN here.
PHYSICAL_TESTS: BLOCKED.
P0_P1_P2: 8 open P1 /3 P2 unchanged; F27 consumer pending, F28 exact local adoption remains acknowledged. Absence of P0 not proven.
EVIDENCE: original logs, executed harness, exact PR metadata and raw maps above.
NEXT_ACTIONS: Root explicit new source-pair consumer, custody-loss/error-path tests and original mandatory hosted evidence.
GO_NO_GO: NO-GO; TAILSCALE_REMOVAL BLOCKED.
