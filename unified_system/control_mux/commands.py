"""Typed native identity seam and immutable canonical command preparation.
Constructing context is not authentication. Only Root's qualified in-process
provider may supply it to product composition. No provider is installed here.
"""
from dataclasses import dataclass
from typing import Protocol
import hashlib
import re
from .codec import PROFILE_SHA, encode, decode, validate

@dataclass(frozen=True)
class RawRequest:
    method: str
    path: str
    headers: tuple[tuple[bytes, bytes], ...]
    body: bytes
    native_connection: object

@dataclass(frozen=True)
class AdmittedContext:
    cluster_id: str
    actor_principal_id: str
    actor_session_id: str
    quota_owner_id: str
    role: str
    csrf_policy_ref: str
    enrollment_revision: str
    permissions: frozenset[str]
    native_handle: object

class NativeAdmissionProvider(Protocol):
    def resolve(self, request: RawRequest, operation: str) -> AdmittedContext: ...
    def revalidate(self, context: AdmittedContext, operation: str) -> AdmittedContext: ...

@dataclass(frozen=True)
class PreparedCommand:
    body: bytes
    preimage: bytes
    key_preimage: bytes
    digest: str
    key_sha256: str
    request_id: str

def prepare_open(context, body, request_id, idempotency_key):
    if type(context) is not AdmittedContext or 'OPEN_CONNECTION' not in context.permissions:
        raise ValueError('FORBIDDEN')
    if type(body) is not bytes or len(body)>16384:raise ValueError('BODY_CAP')
    value=validate('open_request',decode(body))
    if value['request_id']!=request_id:raise ValueError('REQUEST_ID_MISMATCH')
    if value['role']!=context.role or value['enrollment_revision']!=context.enrollment_revision:
        raise ValueError('CONTEXT_MISMATCH')
    key=dict(namespace_schema='unified.control.command-key.v3',cluster_id=context.cluster_id,
        quota_owner_id=context.quota_owner_id,original_actor_principal_id=context.actor_principal_id,
        idempotency_key=idempotency_key)
    validate('idempotency_key_preimage',key)
    pre=dict(canonical_body_sha256=hashlib.sha256(body).hexdigest(),canonical_path='/control/v3/connections',
        connection_id=None,expected_connection_epoch=None,expected_subscription_epoch=None,http_method='POST',
        idempotency_key=idempotency_key,operation='OPEN_CONNECTION',original_actor_principal_id=context.actor_principal_id,
        original_actor_session_id=context.actor_session_id,profile_schema_sha256=PROFILE_SHA,
        quota_owner_id=context.quota_owner_id,request_id=request_id,snapshot_id=None,subscription_id=None)
    validate('command_preimage',pre)
    raw=encode(pre);keyraw=encode(key)
    return PreparedCommand(body,raw,keyraw,hashlib.sha256(raw).hexdigest(),hashlib.sha256(keyraw).hexdigest(),request_id)
