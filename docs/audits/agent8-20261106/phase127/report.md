# Independent proxy isolation finding A8-F27

P1 OPEN. Exact Grid PR274 HEAD `539239e3c11ec9e86aa24365d74a68301fdf1185` uses coordination.py SHA `86814ec2519c272740ac8fae6fb4eae73d14ba51ccec091053ab260c7c024f73`, line88: owned `httpx.AsyncClient(verify=context, follow_redirects=False)` omits trust_env=False. Consumer Unified PR64 HEAD `0342413b76e5574e7e303bfdd8a4ea2417ae8d93` gates literal loopback endpoints but does not establish the actual client's proxy-route custody.

| Requirement ID | Repository / PR / exact HEAD | Test | Environment | Expected | Actual / status | Evidence | Severity / correction |
|---|---|---|---|---|---|---|---|
| A8-F27-ROUTE-ISOLATION | Grid PR274 /539 and Unified PR64 /034 above | Actual owned client transport selection under controlled proxy environment | Own Windows CPython3.12.10/httpx0.28.1, no Consul and no HTTP requests | Literal loopback URL implies only direct local route for isolated admission | FAIL: accepted loopback selects AsyncHTTPProxy when HTTP_PROXY is set and NO_PROXY empty | [Executed probe](executed.py), [original result](stdout.json), [raw source maps](source-binding.json) | P1 OPEN: A2 fix owned client admission/construction; Root rebind qualified consumer source and regress inherited proxy cases |
| A8-F27-NO-PROXY-CONTROL | Same exact sources | Same construction with NO_PROXY=127.0.0.1 | Same probe | Explicit bypass selects direct route | Direct AsyncConnectionPool observed; diagnostic control only | Same original result | Not a production mitigation or acceptance |

The probe creates the actual source-owned ConsulSessionAuthority, calls the actual Root loopback gate and inspects the selected actual HTTPX transport pool. Both client constructions use a synthetic HTTP_PROXY=http://127.0.0.1:9 and a synthetic never-sent ACL token. No request is issued and no Consul process starts. Proxy selection persists after the temporary environment patch exits, confirming that changing ambient variables after client creation is insufficient for existing client custody. During the client probe socket connect/connect_ex and DNS are guarded to raise; their call counts are zero. Windows asyncio first creates its own internal loopback socketpair before these guards; that bootstrap is explicitly outside the zero-call probe claim. An initial overbroad guard blocked that socketpair before the client probe; its original error/harness are retained separately and are not product evidence.

1635 Unified and 800 Grid primary files matched Git raw bytes before/after with no extras. No production source was edited. The [official HTTPX environment documentation](https://www.python-httpx.org/environment_variables/) independently confirms default environment use and HTTP_PROXY/HTTPS_PROXY/ALL_PROXY/NO_PROXY behavior. The actual controlled selection is shown for HTTP; HTTPS route behavior and real proxy delivery were not executed.

Severity rationale: this defeats the isolation guarantee used to admit a native client. In a proxy-configured environment an HTTP authority request could be routed through a proxy with its Consul token/body; that is a source-based risk inference, not observed exfiltration. No evidence establishes that earlier A8/owner fixtures inherited a proxy, leaked tokens or contacted providers. The earlier16 PASS remains valid for its observed fixture, but does not prove arbitrary inherited-environment isolation. This finding is distinct from provider-budget admission F14. Existing TLS validation/production mTLS were not bypassed or tested here.

Required correction: A2 must supply an owned client with ambient proxy routing explicitly disabled, or an equivalently enforced and independently proven admission boundary. Root must bind the actual constructed client and corrected source to its consumer. Sanitizing the environment only after construction or trusting the loopback URL alone is insufficient. Preserve existing source pins/evidence until a separately qualified successor; no silent modification of GridCore868 or Root034. Add isolated inherited-proxy regression with bounded own synthetic endpoints and no external provider access.

RELEASE_MANIFEST_STATUS: no approved release.
NODE_INVENTORY_STATUS: not requalified.
CONTRACT_STATUS: client route custody unresolved.
OFFLINE_TESTS: source-risk reproduced by two actual transport selections; not two research application tests.
WINDOWS_CI: not rechecked here; F26 remains open.
PHYSICAL_TESTS: BLOCKED.
P0_P1_P2: 8 open P1 /3 P2; absence of P0 not proven.
EVIDENCE: original probe, logs and raw maps above.
NEXT_ACTIONS: send reproducible finding to A2 and Integration Owner; independently review corrected exact source/client regression.
GO_NO_GO: NO-GO; TAILSCALE_REMOVAL BLOCKED.
