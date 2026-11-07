"""Typed native identity seam and immutable canonical command preparation.
Constructing context is not authentication. Only Root's qualified in-process
provider may supply it to product composition. No provider is installed here.
"""
from dataclasses import dataclass
from typing import Protocol, TYPE_CHECKING, Mapping
import hashlib
if TYPE_CHECKING:
    from unified_system.security_identity_records import IdentityBinding
import re
from .codec import PROFILE_SHA, encode, decode, validate, matrix

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
    def identity_binding(self, context: AdmittedContext) -> 'IdentityBinding': ...
    def verify_records(self, context: AdmittedContext, records: Mapping[str, Mapping[str, object]]) -> None:
        """Actual native comparison; return None only on success, otherwise raise.

        Every other return, including False/True, fails the store contract.
        This protocol declaration does not qualify an implementation or fixture.
        """
        raise NotImplementedError('qualified native comparison implementation required')

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


def validate_original(preimage,body):
    """Immutable request/preimage consistency, not current authorization."""
    pre=validate('command_preimage',preimage)
    if pre['profile_schema_sha256']!=PROFILE_SHA:raise ValueError('PROFILE_MISMATCH')
    if type(body) is not bytes or len(body)>16384:raise ValueError('BODY_CAP')
    if hashlib.sha256(body).hexdigest()!=pre['canonical_body_sha256']:raise ValueError('BODY_HASH')
    rule=matrix['operations'][pre['operation']]
    if pre['http_method']!=rule['method'] or pre['canonical_path']!=rule['path'].format(**pre):raise ValueError('ROUTE_MISMATCH')
    if any(pre[k] is not None for k in rule['required_null']) or any(pre[k] is None for k in rule['required_nonnull']):raise ValueError('TARGET_EPOCH_MISMATCH')
    if rule['request_definition']=='EMPTY':
        if body:raise ValueError('DELETE_BODY')
        return None
    value=validate(rule['request_definition'],decode(body))
    if value['request_id']!=pre['request_id']:raise ValueError('REQUEST_ID_MISMATCH')
    # Check every duplicated body binding BEFORE any empty204/result handling.
    for field in ('connection_id','subscription_id','snapshot_id','expected_connection_epoch','expected_subscription_epoch'):
        if field in value and value[field]!=pre[field]:raise ValueError('BODY_PREIMAGE_'+field.upper())
    if pre['operation']=='OPEN_SUBSCRIPTION' and value['kind']!=value['selector']['kind']:raise ValueError('SELECTOR_KIND_MISMATCH')
    return value


def _prepare(context,operation,body,request_id,idempotency_key,*,connection_id=None,connection_epoch=None,subscription_id=None,subscription_epoch=None,snapshot_id=None):
    if type(context) is not AdmittedContext or operation not in context.permissions:raise ValueError('FORBIDDEN')
    if type(body) is not bytes or len(body)>16384:raise ValueError('BODY_CAP')
    key=validate('idempotency_key_preimage',dict(namespace_schema='unified.control.command-key.v3',cluster_id=context.cluster_id,
        quota_owner_id=context.quota_owner_id,original_actor_principal_id=context.actor_principal_id,idempotency_key=idempotency_key))
    rule=matrix['operations'][operation]
    pre=dict(canonical_body_sha256=hashlib.sha256(body).hexdigest(),canonical_path='',connection_id=connection_id,
        expected_connection_epoch=connection_epoch,expected_subscription_epoch=subscription_epoch,http_method=rule['method'],
        idempotency_key=idempotency_key,operation=operation,original_actor_principal_id=context.actor_principal_id,
        original_actor_session_id=context.actor_session_id,profile_schema_sha256=PROFILE_SHA,quota_owner_id=context.quota_owner_id,
        request_id=request_id,snapshot_id=snapshot_id,subscription_id=subscription_id)
    pre['canonical_path']=rule['path'].format(**pre)
    validate_original(pre,body)
    raw=encode(pre);keyraw=encode(key)
    return PreparedCommand(body,raw,keyraw,hashlib.sha256(raw).hexdigest(),hashlib.sha256(keyraw).hexdigest(),request_id)


def prepare_subscribe(context,body,request_id,idempotency_key,connection_id,connection_epoch):
    return _prepare(context,'OPEN_SUBSCRIPTION',body,request_id,idempotency_key,connection_id=connection_id,connection_epoch=connection_epoch)


def prepare_ack(context,body,request_id,idempotency_key,connection_id,subscription_id,connection_epoch,subscription_epoch):
    if type(body) is not bytes or len(body)>16384:raise ValueError('BODY_CAP')
    value=validate('snapshot_ack_request',decode(body))
    return _prepare(context,'ACK_SNAPSHOT',body,request_id,idempotency_key,connection_id=connection_id,connection_epoch=connection_epoch,
        subscription_id=subscription_id,subscription_epoch=subscription_epoch,snapshot_id=value['snapshot_id'])


def prepare_close(context,body,request_id,idempotency_key,connection_id,connection_epoch,subscription_id=None,subscription_epoch=None):
    operation='CLOSE_CONNECTION' if subscription_id is None else 'CLOSE_SUBSCRIPTION'
    return _prepare(context,operation,body,request_id,idempotency_key,connection_id=connection_id,connection_epoch=connection_epoch,
        subscription_id=subscription_id,subscription_epoch=subscription_epoch)
