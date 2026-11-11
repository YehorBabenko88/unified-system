# A8 independent PR32 isolated acceptance

Requirement: CONTROL-MUX-OPEN / native verifier contract / fail-closed quorum.
Repository: unified-system; Draft PR https://github.com/YehorBabenko88/unified-system/pull/32.
Exact HEAD: 3d48763288a2ff2a4337000943a15f03a9ac45c1; tree b4109101b3b6442702e8d6f3af450d9fadbc2603.
Dependency: Grid 58cfe0f51bc05bb0ee2ed09368a9b64679358c63, independently cloned without hardlinks/alternates.
Environment: isolated Windows Python3.12 environment, hash-required wheel lock, three owned loopback Consul1.22.2/BoltDB processes and synthetic identity/data. No service/firewall/ESET/Tailscale or office-node changes.

Expected: exactly10 mandatory unit IDs,15 real Consul/HTTP event IDs,8 source-guard negatives, no skips, raw source unchanged, all owned processes stopped.
Actual: PASS all counts;658 primary and672 Grid tracked raw inputs verified before/after. Original evidence: source-bound.json, real-consul.json, real-consul.log, source-guard-controls.json and log.

Additional independent MODEL cases: False/True rejected, None accepted by exception-style validator contract, raised error rejected, inherited Protocol stub raises/rejected. Five cases PASS,0skip; evidence independent-verifier-contract.json. These synthetic-provider checks do not establish any native principal/session authentication.

Actual Consul scenarios include lost prepare/final response reconciliation, idempotent original receipt, capacity bound, current revoked fixture policy denial, stale actual leader transaction denial, owned voter loss/restart and no-quorum UNKNOWN. Explicit session handoff is a fixture action, not admission of fleet coordinator failover.

Qualification: REAL_HTTP_GRID_CONSUL_OPEN_PRIMITIVE_SYNTHETIC_NATIVE_IDENTITY_ONLY. Default missing-native composition remains closed. No native authentication, final integrated endpoint, GET proposal ACK, fleet Windows/Home, physical, or Tailscale-removal PASS. No real orders. No unapproved host-network changes.

Harness correction: first invocation used relative evidence output while child cwd differed; it stopped before real Consul tests with missing parent-path receipt. Preserve outputs/phase44 and own first clone; corrected invocation used fresh clone and absolute paths. This is an A8 invocation error, not a product-test waiver.

Severity: existing integrated authentication/runtime acceptance gaps remain P1. Required correction: qualified real native admission provider and independently bound final composition/mandatory endpoint evidence. Overall NO-GO; physical and Tailscale removal BLOCKED.
