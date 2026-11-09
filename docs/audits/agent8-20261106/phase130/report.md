# PR278 independent owned-client proxy correction

Exact Grid Draft PR278 HEAD `b0ddb78fed04cc29c7b0290ae75d1d8af84fcfec`, tree `308ff8bba75911853f5edc8f14ea63b4218f8a40`, base19fa. Independently fetched GitHub PR metadata reports this exact current head and Draft state. Of six changed paths, the sole Core implementation change adds trust_env=False to the existing owned AsyncClient constructor. New Core SHA is `3dd73d3eb3dfb576f7174a94fab05a0f87fe248ffcacccfa19786ccc74f0776b`. Assignment module d128/Core predecessor868 and Root034 source pins are not silently rewritten. Source/safety review preceded execution.

| Requirement ID | Repository / PR / exact HEAD | Test | Environment | Expected | Actual / status | Evidence | Severity / correction |
|---|---|---|---|---|---|---|---|
| A8-F27-CORE-FIX | Grid PR278 /b0ddb78 above; support Unified1f6 | Actual owned client with inherited proxy set BEFORE construction, then env removal AFTER | Own Windows CPython3.12.10/httpx0.28.1, own three-voter ACL Consul and own loopback trap | Native consistent read succeeds directly, trap0, ownedTrue/trust_envFalse/follow_redirectsFalse, client closed by authority | PASS | [Original stdout](stdout.log), [test log](stderr.log), [raw source receipt](receipt.json) | Core-component correction verified only; Root consumer gate remains open |
| A8-PROXY-INJECTION-CONTROL | Same sources | Actual injected-client ownership/lifecycle, no request | Same stand, second dedicated child | Remains unowned/trust_envTrue, not closed by authority | PASS; caller explicitly closes injected client, trap0 | [Own child/lifecycle observations](own-lifecycle-observations.json) | No safe-route admission proved for arbitrary injected clients |
| A8-EXACT-HEAD-278 | Same PR | Independent connector metadata plus primary commit/tree | Read-only GitHub/Git | Draft and reported exact HEAD agree | PASS for PR278 at observation | [Original metadata](GitHub-PR278.original-metadata.json) | Not a fresh global six-repository head check |

Two unique committed tests passed with zero errors/failures/skips. The actual owned read returned three voters and exactly one leader, so trap0 is accompanied by positive native response evidence, not merely no traffic. HTTP_PROXY/HTTPS_PROXY/ALL_PROXY point only to the own trap with NO_PROXY empty in the dedicated child before construction; removing them later is not the correction. The actual request is HTTP consistent GET /v1/operator/raft/configuration. No HTTPS proxy-delivery experiment is claimed. The injected case makes no request and only qualifies ownership/close semantics.

820 Grid and1519 support primary files matched Git raw bytes before/after, with no extras. All three retained own Consul Popen handles were waited (114512,135744,138284), both bounded child calls returned0, and both own trap threads were shut down/joined by committed assertions. Trap records a count only, not tokens/headers/path/body. Fixture startup itself creates the disposable cluster; test clients perform no session/create, registration/job KV, worker or protected-effect call. No external provider/office/network policy/Tailscale changes occurred. Interpreter bootstrap and child exit observations are not native PID identity qualification.

Owner GREEN/RED receipts and source-closure claims were not independently authenticated here; A8 executed its own two current cases. Original RED5344 was not rerun. Earlier16/25/12 counts are not transferred. F28 failed-entry cleanup remains present because assignment d128 is unchanged. No actual Root consumer with the new Core was qualified: old034 pins Core868 and remains immutable. Actual client identity, ownership/closed-state admission, same authority, exclusive lifecycle through operation/cleanup and safe local invalidation after lost custody still require a separately reviewed Root/broker successor.

RELEASE_MANIFEST_STATUS: no approved release/adoption inferred.
NODE_INVENTORY_STATUS: not requalified.
CONTRACT_STATUS: Core owned-constructor correction verified; consumer/native freeze pending.
OFFLINE_TESTS: two unique current cases PASS /0 skip.
WINDOWS_CI: hosted NOT_RUN here; Ubuntu and mandatory hosted matrix not accepted here.
PHYSICAL_TESTS: BLOCKED.
P0_P1_P2: 8 open P1 /4 P2 unchanged. F27 Core fix verified, overall F27 open pending consumer admission; F28 OPEN. Absence of P0 not proven.
EVIDENCE: original current logs, lifecycle observations, exact PR metadata and primary maps above.
NEXT_ACTIONS: explicit Root/Core source-pair successor, client custody negatives and separately fixed local-entry cleanup; independently verify exact hosted evidence.
GO_NO_GO: NO-GO; TAILSCALE_REMOVAL BLOCKED.
