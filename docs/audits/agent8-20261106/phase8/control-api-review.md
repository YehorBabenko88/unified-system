# A2 Draft25 — bounded independent review

Exact source: `320b5d0894019d72aa8927dc5c4246d28c6e5f3c`, tree `7c69196e55afd314e4547d327cf5e1d45eb43d94`, base `2df6f5c2f77f4d883bad1a8623dd8375db529be0`.

**Pure denial component: focused PASS. CI source binding: FAIL (F11, P2). Overall NO-GO.**

The original PR metadata and fetched Git objects match the announced pins. Exactly four allocated files are new; no existing runtime/startup/shared file was changed. The app imports only json/re, exposes no provider/backend/enable constructor, and creates no listener or system I/O.

Independently reproduced16 focused tests with zero skips. An auditor-owned probe exercises99 route/method combinations plus framing, forged identity, malformed-input and HEAD negatives. Protected reads/effect routes remain unavailable/closed; only constant DENY_ONLY capabilities succeed with every runtime boolean false. Request bodies are never read, HEAD sends no content, error envelopes are fixed/nonleaking and do not invent identity, cursor or authority. [Independent result](independent-boundary-review.json), [focused log](focused-tests.log).

The error profile SHA256 `e4b7f009e6f81cc5baa46be604abde8edd05cc6f48dfb5ac711879343c49d20c` matches the original local A6 copy and its scoped review record. It intentionally differs from frozen A6 v1 errors/events; no transport adapter, runtime auth or successful projection is implemented. A6's exact-profile/version-separation ACK is not endpoint compatibility or runtime approval.

## F11 — P2 — CI admits uncommitted source

Requirement: exact-source CI evidence must reject a modified tracked component before qualification.

Reproduction uses a separate auditor-owned disposable clone, never the developer or production checkout. Append an inert comment to `unified_system/control_api_readonly.py`; Git then reports ` M unified_system/control_api_readonly.py`. Execute the exact Python block from `.github/workflows/agent2-control-api.yml` with the correct EXPECTED_HEAD and explicitly synthetic LOCAL_AUDITOR_NOT_GITHUB/LOCAL_ONLY run fields.

Expected: source rejection/nonzero exit. Actual: exit0,16 tests/no skips and an evidence record naming the original committed HEAD/tree. Git blob SHA256 `a54da5317dabf6f7c94cca5ccaf926052c71763d86ac33b007bc04d7df56c62b`; executed dirty-file SHA256 `77a38d66a1cb0ab81528728231d4b667a1bc6b5efba6bd4c16a33edcb1d0bc61`. The guard only checks HEAD, so changed worktree bytes are invisible to it. The modified fixture file was restored afterward.

[Original negative receipt](ci-source-tamper-probe.json), [runner stdout](ci-tamper.stdout.log), [runner stderr](ci-tamper.stderr.log). This demonstrates an acceptance-guard defect; it does not assert that a hosted run was tampered with or that denial can be bypassed.

Correction requested directly from A2 and Integration Owner: before/after expected-source/clean-tree/blob checks, log/source hashes in the receipt, and exact mandatory test identity/count/no-skip guards. Do not change the16 component assertions or introduce runtime wiring to obtain a pass. Source-scoped recheck is required after the fix.

## Original evidence and CI limits

Developer source record SHA256 `8a00f61529fda50ebc6ba3b57ae47d4389096a04dc1c70f83cb392366bea0eee` and all four recorded raw Git blob hashes independently match. Original full-suite log bytes also match its declared hash and contain `Ran724`/`OK(skipped=14)`. This audit did not rerun/adopt that full-suite claim as independent mandatory acceptance; the skipped composed/Windows cases remain separate. [Record-byte review](original-record-byte-review.json).

Dedicated PR run42250381079 has four Linux/Windows Python3.11/3.12 jobs queued and zero artifacts at observation. No hosted qualification is granted. Raw local developer evidence does not repair the workflow source guard.

RELEASE_MANIFEST_STATUS: existing preparation-only/noninstallable package. CONTRACT_STATUS: scoped P0 profile only, frozen A6 v1 incompatibility intentional. OFFLINE_TESTS:16 focused/99 route-method probes PASS. WINDOWS_CI: NOT_QUALIFIED. PHYSICAL_TESTS: BLOCKED. Current open findings:6 P1/2 P2, including unresolved F11. GO_NO_GO:NO-GO. No listener, office process, production account/data/network/Tailscale state, merge or deployment was changed by the auditor.
