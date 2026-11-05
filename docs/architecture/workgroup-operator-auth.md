# Workgroup operator authentication: native subject prototype

Status: contract/prototype only. Runtime factory DENY. No credentials, local
accounts, certificates, policy changes or office authentication tests are created.
Compile and invalid-context tests do not qualify completed-context extraction,
human authentication, TLS/CBT, owner reauthentication or physical operation.

## Local account identity contract

The office uses local Windows accounts only. Microsoft documents that workgroup
Windows authentication uses NTLM and local accounts are checked in the server's
local account database. A client account on PC1 is therefore not an independent
identity authority trusted by LS5 merely because it sends a PC1 name.
[NTLM overview](https://learn.microsoft.com/en-us/windows-server/security/kerberos/ntlm-overview).

Canonical subject is `(issuer_local_SAM_SID, authenticated_TokenUser_SID,
enrolled_issuer_generation)`. Issuer SID comes from the accepting machine's
`LsaQueryInformationPolicy(PolicyAccountDomainInformation)`; user SID comes only
from `QuerySecurityContextToken` on a completed, native-owner-retained SSPI
context followed by `GetTokenInformation(TokenUser)`. Windows SID parsing and
equality verify the user's account-domain SID against actual local SAM SID.
Never substitute the server process identity or a JSON username/SID.
[LSA account domain API](https://learn.microsoft.com/en-us/windows/win32/api/ntsecapi/nf-ntsecapi-lsaqueryinformationpolicy),
[context token API](https://learn.microsoft.com/en-us/windows/win32/api/sspi/nf-sspi-querysecuritycontexttoken),
[SID scope](https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/manage/understand-security-identifiers).

Protected enrollment supplies issuer generation and explicit HUMAN subject
allowlist. This internal configuration is not a bearer grant. Same-name accounts
on LS5/PC4/PC3 are distinct subjects; only an owner-approved, separately
authenticated and audited link can map them to one opaque cluster actor. No
matching passwords or accounts across six machines are required. Reinstall,
cloning or issuer generation changes require re-enrollment, never name fallback.
The account-purpose registry must exclude service/node identities: a generic SAM
user account's purpose cannot be inferred solely from a remote network token.
Someone possessing a human account's credentials is not distinguished from that
account holder by SID inspection alone. This prototype claims no human-presence
factor or protection against compromised human credentials.

The prototype rejects uncompleted/non-NTLM context, foreign SAM, unknown subject,
Guest RID, anonymous/system/service SIDs, service logon group and machine-style
account names. It inspects tokens but never impersonates a thread, launches a
user process, adjusts privileges or changes account policy. It grants no RBAC role.
An admitted native owner must retain a read/lifetime lock throughout the borrowed
context lease; an arbitrary serialized handle is never accepted by a runtime API.
`NativeContextOrigin.InboundAcceptCompleted` is a trusted native composition
assertion, not OS direction attestation from `negotiation.State`. Its future owner
must record the actual inbound `AcceptSecurityContext` completion and hold the
server-role/lifetime invariant. Outbound contexts are rejected before lease use.
The current negative harness uses a visibly synthetic owner; no such owner can
register with a runtime factory, and the actual inbound owner is NOT_IMPLEMENTED.
Token handles, native context-info buffers, LSA handles/buffers and allocated
token-info buffers are closed/freed. The context itself remains the owner's.

## Proposed transport and client boundary, not implemented

Use native Negotiate SSPI under existing OS security policy; workgroup fallback
may use NTLMv2. NTLM is deprecated and NTLMv1 was removed in Windows 11 24H2;
no future support guarantee follows from this prototype. Blocked NTLM or missing
provider capability means authentication unavailable; do not enable protocols or
weaken system policy to obtain a pass.
[Negotiate selection](https://learn.microsoft.com/en-us/windows/win32/secauthn/microsoft-negotiate),
[Windows deprecations](https://learn.microsoft.com/en-us/windows/whats-new/deprecated-features).

The future per-human native Terminan client should prompt for the selected
coordinator-local account through `SspiPromptForCredentialsW`, using opaque
identity buffers, DO_NOT_SAVE/NO_CHECKBOX, then pass only native credential handles
into SSPI. Credential material must never enter Python/JS strings, browser
storage, application logs or a custom password database. Native buffers and
credential handles must have reviewed cleanup. This lifecycle requires actual
provider qualification; no prompt or credentials are implemented here.
[SSPI credential prompt](https://learn.microsoft.com/en-us/windows/win32/api/sspi/nf-sspi-sspipromptforcredentialsw).

TLS server identity must be verified before credential exchange. Require matching
channel binding on both sides and target-name/service binding. TLS alone does not
prevent forwarding; service binding alone is insufficient. No TLS termination
proxy, missing-binding allowance or audit-only acceptance in the initial contract.
No delegation, CredSSP, worker credential forwarding or automatic credential
reuse. No DisableLoopbackCheck, LocalAccountTokenFilterPolicy, SeImpersonate or
other policy/registry/privilege workaround.
[Microsoft EPA guidance](https://learn.microsoft.com/en-us/windows/win32/secauthn/epa-support-in-service).

An existing SSPI context or cached logon is insufficient for critical action
freshness. The future provider must prove a new action-bound native credential
ceremony and separately consume the owner's concrete dry-run confirmation.
If the issuing coordinator fails and no other independently enrolled subject is
available, new login and fresh reauthentication are BLOCKED. Never merge subjects
by username. Existing quorum-backed opaque sessions retain only their reviewed
expiry/revocation policy; session continuation is not fresh owner proof.

## Existing integration seams and unchanged denials

Unified `OperatorGateway` remains async and default AUTHENTICATION_UNAVAILABLE;
positive current grant, explicit capabilities and command/receipt digest bindings
are unchanged. This branch does not register a principal provider. Native
`CanonicalSubject` explicitly carries TLS_CBT_NOT_QUALIFIED and cannot construct
an authorized runtime `CurrentPrincipal` through an admitted factory.

Terminan `unified_runner.py` binds loopback. `unified_server.py` retains
Host/Origin checks; `/api/session` is a synthetic R4 receipt and POST still uses
the legacy dispatcher. A future reviewed per-human client transport seam must
preserve these boundaries; module health nonce and UI lifetime are not operator
authority. Do not remotely bind this server to introduce authentication.

Grant/session/audit state belongs to the existing quorum-backed control-plane
authority. Native identity is only an input to server-side authorization. Atomic
grant revocation/admission and durable executor fencing remain separate P0 gates.
Closing Terminan or expiring a UI cookie cannot cancel accepted background jobs;
the executor uses current durable actor policy and supersession fences.

## Required hosted negative lane and positive qualification plan

The required Windows lane compiles the two actual C# files with the OS Framework
compiler and executes the negative harness. It tests absent owner, outbound owner,
empty context, native invalid-handle rejection and invalid generation, including
lease release. The inventory is built only after each successful negative case;
the native case must observe actual `SEC_E_INVALID_HANDLE`, not just exit zero.
Missing compiler/native API or unexpected success fails; no skips. Inputs and
compiler hashes plus exact source HEAD are retained. Its receipt explicitly says
positive subject extraction NOT_RUN, TLS/CBT NOT_QUALIFIED, factory DENY and
authentication NOT_QUALIFIED. A receipt parser cannot upgrade these outcomes.

The launcher is restricted to an explicitly requested ephemeral hosted job.
Environment checks are a test-location guard, not authentication, host attestation
or runtime authorization. No office execution of the native harness is admitted.

Before a positive lane, root must review a disposable Windows workgroup plan:

1. Actual completed native SSPI exchange with real local account credentials,
   then exact canonical issuer/user extraction; no substituted current-process
   identity. Owner lifetime lock and early disposal/concurrent context tests.
2. Separately created issuer-local accounts with different passwords; same
   username on two issuers remains different. Guest, service/node, foreign SID,
   wrong password, anonymous, disabled account and unregistered human denials.
3. Actual trusted TLS plus correct/missing/mismatched CBT, wrong certificate,
   wrong target and relay-negative cases. Existing restrictive policy must fail
   closed without changes. Verify no delegation/impersonation privilege request.
4. Fresh credential prompt versus stale/replayed ceremony; grant revocation,
   session expiry, owner confirmation replay and issuer failure. No credential
   material or native handles in public artifacts.
5. Only afterward review the admitted native provider factory and Terminan
   composition. Native context extraction alone never qualifies native auth.

The positive lane may need ephemeral accounts/certificates, but none are created
by this change. Office acceptance remains a separate expressly approved phase.
