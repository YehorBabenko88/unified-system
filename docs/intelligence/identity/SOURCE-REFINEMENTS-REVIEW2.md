# Exact source refinements — review2

Supersedes the implementation-review1 two-check limit for QUERY ONLY. Manifest
capability has exactly2 successful current-check budget, query exactly7 (six bounded
object reads plus final return). Budgets fixed server-side by exact tool name,
never caller profile/request number. Wrong tool/request/store/binding cannot
consume or increase valid-check budget. Manifest third and query eighth deny.
A3/A4 profile/source ACK and Root positive composition remain separate gates;
local cap tests do not claim an admitted query/store adapter.

Context stores ORIGINAL exact peer DER fingerprint, compared on every current
check, not membership in some other commissioned peer entry. Socket remains
same actual owned server-side TLS context and local connection.

Security revocation is latched BEFORE mandatory audit append. Audit-full may
raise GatewayIdentityUnavailable but cannot preserve/re-enable prior handles.
Audit READ_DENIED covers authorization/current-check refusal, without reflecting
untrusted request/tool contents. SERVICE_REVOKED records target_service_id even
if no target identity was authenticated. Events carry closed decision and reason.
Audit-full itself denies; draining only frees buffer, never reverts revocation.
These fix independently reviewed P1/P2 issues with reproduced RED controls.

Exception ABI remains exact synchronous None on success, GatewayIdentityDenied
or GatewayIdentityUnavailable on refusal/unavailable. No arbitrary callback or
None-as-provider-proof. Actual authority instance/source/type must be admitted.
Audit sink drain returns detached data copies, not globally immutable signed
records or durable receipts. Root owns durable correlation and sink writes.

Initial tests missing-module RED10; later cumulative-clock/context-bound RED2;
independent audit/revocation RED2; Root query-check-budget/peer-pin RED2. These
are new isolated implementation regressions, not preexisting production bugs.
PKI/TLS positive and negatives are real disposable loopback; controlled-clock
and corrupted-private-binding controls are unit tests, not OS/native acceptance.
No cross-owner read, research/mutation/cancellation/native/physical permission.

Root identified by source review a forged exact-type handle pointing to a fake
issuer whose _check returned None; A2 reproduced the requested vector in its own
RED test. Fixed by exact admitted authority TYPE check and direct
fixed-class verifier dispatch, followed by actual issuer inventory membership;
no receiver-selected _check callback. Root must STILL bind its actual qualified
authority instance/issuance in the same trusted callchain before invoking owner
read; class type alone does not qualify a fabricated issuer or hostile Python.
