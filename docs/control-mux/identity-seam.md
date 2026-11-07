# Root identity seam proposal (runtime implementation pending)
No identity is accepted from headers, payloads, serialized admitted booleans or fixture contexts in product composition.

Root supplies an in-process NativeAdmissionProvider protocol:
resolve(request: RawRequest, operation: Operation) -> AdmittedContext | AdmissionDenied
revalidate(context: AdmittedContext, operation: Operation) -> AdmittedContext | AdmissionDenied
Both calls must validate actual transport/native principal, session expiry/revocation, current RBAC, enrollment and CSRF for mutations. Revalidate immediately before authority preparation and before definitive mutation. No cached positive validity interval implied. Civil-time credentials retain native time gates. Missing provider always503.

Proposed immutable dataclasses (not yet executable authority):
RawRequest(method: str, path: str, headers: tuple[tuple[bytes,bytes],...], body: bytes, native_connection: object). Native connection handle originates only at Root listener composition; never reconstructed from JSON.
AdmittedContext(cluster_id: str, actor_principal_id: str, actor_session_id: str, quota_owner_id: str, role: str, csrf_policy_ref: str, enrollment_revision: str, permissions: frozenset[Operation], native_handle: object).
These fields are claims UNTIL returned by Root's trusted provider. They are never bearer credentials or public constructor-based authorization.

Consul authorization binding seam also needs Root-defined pinned principal/session/enrollment/policy record layout. Store captures actual current records and their positive ModifyIndices itself; checks session lock and those indices in SAME transaction with leader check-session + check-index, generation + slot-ledger CAS and command/index/receipt writes. No caller-supplied arbitrary KV paths, native indices or prebuilt transaction operations. Do not treat double Python revalidation as a replacement for atomic revocation fencing.

Until Root supplies qualified native composition and exact Consul identity layout, exported HTTP application stays unavailable; owned isolated HTTP fixtures are test-only. Coordinator authority must be existing Grid authority; no new election service. Root must confirm bridge record semantics before this seam can qualify a mutation.
