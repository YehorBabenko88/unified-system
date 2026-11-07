# F11 independent exact-source fix review

PR25 exact HEAD `0b3af3e872b49ed1848815f7f9ffd42444f89b24`, tree `1769906483356ed41eb8fcd278c5545b1bbafa67`, parent `320b5d0894019d72aa8927dc5c4246d28c6e5f3c`.

**F11: FIX VERIFIED OFFLINE AT THIS SOURCE. Overall acceptance remains NO-GO.**

The diff is restricted to the allocated workflow and documentation. Product code and all16 component tests have identical Git blobs to the independently reviewed parent. No source, assertion, timeout or raw-byte binding was weakened.

## Original counterexample

The auditor reran the same tracked-comment negative fixture against the exact new workflow block, changing only the expected source pin/output destination. The component file remains byte-identical to the earlier counterexample: committed SHA256 `a54da5317dabf6f7c94cca5ccaf926052c71763d86ac33b007bc04d7df56c62b`, modified SHA256 `77a38d66a1cb0ab81528728231d4b667a1bc6b5efba6bd4c16a33edcb1d0bc61`.

At320b5d0 it exited0 and emitted a committed-source receipt. At0b3af3e it exits1 before tests with no qualifying receipt. [Fixed counterexample](original-comment-probe/ci-source-tamper-probe.json). The original failing result remains in phase8. All changes were in auditor-owned disposable clones, not the developer or production checkout.

## Independent guard challenges

The exact embedded CI Python block was executed locally in fresh owned clones. The clean control passes16 actual tests/zero skips. Independently verified all five raw source/blob hash pairs, equal before/after receipts,16 unique expected test identities and the original test-log SHA256.

| Negative case | Actual result |
|---|---|
| tracked comment before tests | reject: tracked source dirty |
| comment hidden by assume-unchanged | reject: raw source differs from committed blob |
| wrong expected HEAD | reject |
| missing mandatory test ID | reject before tests |
| duplicate mandatory test ID | reject before tests |
| one skipped mandatory test | nonzero exit |
| source mutation during tests | reject after tests |
| post-test mutation hidden by assume-unchanged | reject on raw blob comparison |

[All independent guard results](f11-independent-guards.json); [clean local receipt](clean/receipt.json). These are local runner/source-guard results, not hosted attestation; run identifiers are explicitly LOCAL_AUDITOR_NOT_GITHUB/LOCAL_ONLY.

## Windows newline configuration

Two additional owned Windows clones had local core.autocrlf=true/core.eol=crlf. Checkout without the job environment produced different raw shared `__init__.py` bytes and the guard correctly rejected them. Applying the workflow's GIT_CONFIG_COUNT configuration **before checkout** (autocrlf=false/eol=lf) produced exact committed bytes and passed16 tests. The shared file was never edited, and no global/user Git setting changed. [Conversion review](checkout-conversion-review.json).

This confirms the local Windows checkout assumption and preserves strict raw equality; it does not independently execute Linux or the hosted Windows matrix. Reparse/symlink denial was inspected in source; no physical filesystem attack qualification is claimed.

Hosted PR run42252082247's four Windows/Linux Python3.11/3.12 jobs remain queued with zero artifacts at observation. Runtime API, backend/authentication, frozen A6 v1 compatibility, integrated and physical qualification remain NOT_QUALIFIED/BLOCKED. No listener, real orders, merge, deployment, office network or Tailscale changes occurred.

Current open findings return to **6 P1/1 P2**. F11 closure is limited to exact reviewed source/offline guards; future relevant source changes require recheck. Integration Owner and A2 have received the result. Physical acceptance and Tailscale removal remain BLOCKED; **GO_NO_GO:NO-GO**.
