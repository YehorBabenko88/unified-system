# Disposable Windows pipe identification qualification

`scripts/Test-LocalPipeIdentity.ps1` and explicit `tests/windows_identity/run_pipe_qualification.py` exercise actual Windows kernel pipe/token APIs under an unelevated account. Not a login service, broker installation, RBAC/session provider, credential store, IPC admission or runtime factory.

Each case creates a new random FIRST_PIPE_INSTANCE, remote-client-rejected message pipe with a protected DACL limited to the current kernel user SID. The child is a newly owned hidden PowerShell process connecting locally with an explicit token impersonation level. No privilege adjustment, credentials, trust-store/account/service changes, arbitrary client code, firewall or network configuration operations exist.

After a fixed4-byte handshake, GetNamedPipeClientProcessId must match the owned child. The server requires an initially unimpersonated thread, checks ImpersonateNamedPipeClient success, opens TOKEN_QUERY only, accepts exactly SecurityIdentification, reads kernel SID/authentication LUID and always reverts in finally. Failure to revert terminates the disposable helper rather than continuing. The SID is compared only for this same-account fixture and exported as a hash. No claimed username/header is used.

Tests: actual Identification positive; wrong PID, Anonymous and SecurityImpersonation negative. Every owned child exits or is terminated through its own process handle within bounded cleanup. Original stdout/stderr and source hash are preserved in `release/evidence/native-pipe-identification-20261107/`. Missing Windows/script yields failure, never PASS/skip.

Limitations: no cross-account acceptance, interactive-session identity lifetime/lock/revocation, native human-to-principal enrollment, service identity or persistent broker ACL qualification. No actual Control Mux attachment or CSRF, delegation, RBAC, mTLS key provisioning or production runtime authorization. Those remain independent mandatory gates.

Primary references: https://learn.microsoft.com/en-us/windows/win32/api/namedpipeapi/nf-namedpipeapi-impersonatenamedpipeclient and https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getnamedpipeclientprocessid . SecurityIdentification does not require granting SeImpersonatePrivilege; this fixture never adjusts it.
