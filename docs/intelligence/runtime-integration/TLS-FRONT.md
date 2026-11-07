# Disposable loopback TLS front

ROOT-owned gateway_runtime_composition.DisposableGatewayFront is a real explicit
loopback-only TLS listener with OS-selected ephemeral port. It validates that the
Root SSLContext is server-side CERT_REQUIRED/minimumTLS1.2. Root still commissions
actual CA/cert/key/SAN/EKU/fingerprint; this class does not certify those properties.
It has no deployment/service factory, host/port override, engine, store, credential
or provider callback injection. Initial listener lifetime is caller-owned only.

Maximum4 workers, backlog4,2-second total handshake+request deadline,8192-byte
headers/32headers,4096-byte individual value, canonical Content-Length <=32768.
No keepalive/chunking/duplicateheaders/query/pathencoding. Host must match actual
loopback address+port. Bounded static capability catalog GET/HEAD only; protected
query/manifest/research-jobs always503 BEFORE body reads or owner effects. These
paths are Root prototype composition routes, not admitted owner APIs. Server
claims no actual Gateway client identity; chain-verified TLS is not per-tool RBAC.

Local9actualTLS tests plus existing16offline tests. Regression: malformed HEAD
initially returned a body; captured1failure then corrected all error paths to
suppress HEAD bodies. Ephemeral certificates reuse existing test_lan_transport
fixture, not a new PKI/trust store. Tests use own children/tempfiles and own loopback
only, no office/provider connections. Shutdown joins only owned listener/workers;
no restart or arbitrary kill. Source-bound25test workflow uses exact raw Git guards.

A2 actual opaque identity/audit and A3/A4 disclosure must be integrated and exact
owner-source reviewed before any resource route opens. A5/A7 actualjob/result/A6chart
remain independent requirements. No full vertical/native/HomePro/runtime PASS.
