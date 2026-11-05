"""Bounded operator contracts and client cursor state; no identity/runtime factory.

The default is AUTHENTICATION_UNAVAILABLE. A deployment must admit a real human
verifier and existing consensus backend separately. A Python principal object is
not authentication evidence. This module does not open listeners or store secrets.
"""
from dataclasses import dataclass
import json
import hashlib
import re
from typing import Protocol
from uuid import UUID


class ContractError(ValueError): pass
class AuthenticationUnavailable(RuntimeError): pass
class AuthorizationDenied(PermissionError): pass


@dataclass(frozen=True)
class CurrentPrincipal:
    actor_id: str
    grant_revision: int
    principal_kind: str
    capabilities: frozenset[str]


class SessionVerifier(Protocol):
    async def require_current(self, context: object, action: str, aggregate_id: str) -> CurrentPrincipal:
        """Verify actual human session, expiry, revocation and current grant."""


class CoordinationCommands(Protocol):
    async def submit(self, lease: object, envelope: dict, session_context: object) -> object: ...
    async def get_command(self, command_id: str, session_context: object) -> object: ...


class _UnavailableVerifier:
    async def require_current(self, context, action, aggregate_id):
        raise AuthenticationUnavailable('AUTHENTICATION_UNAVAILABLE')


_FIELDS={'schema','command_id','actor_id','idempotency_key','generation',
         'aggregate_type','aggregate_id','expected_revision','action','payload'}
_CAPABILITIES=frozenset({'cluster.snapshot.read','control.commands.read',
                       'control.commands.audit_all','research.control'})


def _identifier(value):
    if type(value) is not str or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}',value) is None:
        raise ContractError('IDENTIFIER_INVALID')
    return value


def _integer(value):
    if type(value) is not int or not 0 <= value <= 2**53-1:
        raise ContractError('INTEGER_INVALID')
    return value


def validate_envelope(value):
    """Validate decoded, duplicate-key-rejected JSON; return detached canonical copy.

    The HTTP adapter must reject duplicate JSON keys while decoding and enforce
    the wire-byte limit before parsing. No HTTP decoder exists in this module.
    """
    if type(value) is not dict or set(value)!=_FIELDS:
        raise ContractError('ENVELOPE_FIELDS_INVALID')
    for name in _FIELDS-{'payload','expected_revision'}: _identifier(value[name])
    try:
        if str(UUID(value['command_id']))!=value['command_id']: raise ValueError()
        if str(UUID(value['generation']))!=value['generation']: raise ValueError()
    except (ValueError,TypeError,AttributeError) as exc:
        raise ContractError('COMMAND_ID_INVALID') from exc
    _integer(value['expected_revision'])
    if value['schema']!='unified.command.v1' or value['aggregate_type']!='research':
        raise ContractError('SCHEMA_OR_AGGREGATE_UNSUPPORTED')
    if value['action']!='SetResearchControl': raise ContractError('ACTION_UNSUPPORTED')
    payload=value['payload']
    if (type(payload) is not dict or set(payload)!={'mode','state'}
            or payload['mode']!='LAB_SIMULATION' or payload['state'] not in ('PAUSED','RUNNING')):
        raise ContractError('PAYLOAD_UNSUPPORTED')
    try:
        encoded=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
    except (ValueError,TypeError,UnicodeError) as exc: raise ContractError('JSON_INVALID') from exc
    if len(encoded)>32768: raise ContractError('ENVELOPE_TOO_LARGE')
    return json.loads(encoded)


def parse_envelope(raw):
    """Strict bounded public decoding before contract validation."""
    if type(raw) is not bytes or not 0<len(raw)<=32768: raise ContractError('WIRE_LIMIT')
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result: raise ContractError('DUPLICATE_KEY')
            result[key]=value
        return result
    def invalid(value): raise ContractError('NONFINITE_JSON')
    try:
        value=json.loads(raw.decode('utf-8'),object_pairs_hook=unique,parse_constant=invalid)
        def bounded(item,depth=0):
            if depth>8: raise ContractError('JSON_DEPTH')
            if type(item) is dict:
                for child in item.values(): bounded(child,depth+1)
            elif type(item) is list:
                for child in item: bounded(child,depth+1)
        bounded(value)
        return validate_envelope(value)
    except (UnicodeError,json.JSONDecodeError,RecursionError,OverflowError) as exc:
        raise ContractError('JSON_INVALID') from exc


def validate_receipt(value,command_id,generation):
    """Reject unrecognized/private backend data rather than projecting it away."""
    common={'schema','command_id','generation','commit_status','effect_status'}
    known=common|{'actor_id','grant_revision','idempotency_key','digest','action',
                  'aggregate_id','revision','leader_lock_index','consensus_modify_index'}
    if type(value) is not dict or set(value) not in (common,known): raise ContractError('RECEIPT_FIELDS_INVALID')
    if (value['schema']!='unified.command-receipt.v1' or value['command_id']!=command_id
            or value['generation']!=generation): raise ContractError('RECEIPT_BINDING_INVALID')
    try:
        for ident in (command_id,generation):
            if str(UUID(ident))!=ident: raise ValueError()
    except (ValueError,TypeError,AttributeError) as exc: raise ContractError('RECEIPT_UUID_INVALID') from exc
    if set(value)==common:
        if value['commit_status']!='UNKNOWN' or value['effect_status']!='UNKNOWN':
            raise ContractError('RECEIPT_STATUS_INVALID')
    else:
        if value['commit_status']!='COMMITTED' or value['effect_status']!='PENDING_UNWIRED':
            raise ContractError('RECEIPT_STATUS_INVALID')
        for field in ('actor_id','aggregate_id','idempotency_key'): _identifier(value[field])
        for field in ('grant_revision','revision','leader_lock_index','consensus_modify_index'):
            _integer(value[field])
        if min(value['grant_revision'],value['revision'],value['leader_lock_index'],value['consensus_modify_index'])<1:
            raise ContractError('RECEIPT_INDEX_INVALID')
        if value['consensus_modify_index']<=value['leader_lock_index']:
            raise ContractError('RECEIPT_INDEX_ORDER_INVALID')
        if (value['action']!='SetResearchControl' or type(value['digest']) is not str
                or re.fullmatch('[a-f0-9]{64}',value['digest']) is None): raise ContractError('RECEIPT_INTENT_INVALID')
    return json.loads(json.dumps(value,allow_nan=False))


class OperatorGateway:
    """Admission seam, not an authority or authenticator.

    The backend independently revalidates the current principal, quorum, revision,
    durable idempotency binding and execution fence. Never wire an untrusted
    caller-supplied verifier through an HTTP/configuration surface.
    """
    def __init__(self, backend, principal_provider=None):
        self._backend=backend
        self._provider=principal_provider if principal_provider is not None else _UnavailableVerifier()

    async def _principal(self, context, action, aggregate_id):
        principal=await self._provider.require_current(context,action,aggregate_id)
        try:
            _identifier(principal.actor_id); _integer(principal.grant_revision)
            valid=(principal.grant_revision>0 and principal.principal_kind=='HUMAN' and type(principal.capabilities) is frozenset
                   and bool(principal.capabilities) and principal.capabilities <= _CAPABILITIES)
        except (AttributeError,ContractError,TypeError): valid=False
        if not valid: raise AuthorizationDenied('HUMAN_CURRENT_GRANT_REQUIRED')
        return principal

    async def submit(self, lease, envelope, session_context):
        envelope=validate_envelope(envelope)
        principal=await self._principal(session_context,envelope['action'],envelope['aggregate_id'])
        if principal.actor_id!=envelope['actor_id'] or 'research.control' not in principal.capabilities:
            raise AuthorizationDenied('ACTION_DENIED')
        # Canonical actor comes only from verified provider output.
        envelope['actor_id']=principal.actor_id
        if self._backend is None: raise AuthenticationUnavailable('CONTROL_BACKEND_UNAVAILABLE')
        receipt=await self._backend.submit(lease,envelope,session_context)
        receipt=validate_receipt(receipt,envelope['command_id'],envelope['generation'])
        if receipt['commit_status']=='COMMITTED':
            digest=hashlib.sha256(json.dumps(envelope,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
            if (any(receipt[field]!=envelope[field] for field in
                    ('actor_id','idempotency_key','action','aggregate_id'))
                    or receipt['digest']!=digest or receipt['revision']!=envelope['expected_revision']+1):
                raise ContractError('RECEIPT_INTENT_BINDING_INVALID')
        current=await self._principal(session_context,envelope['action'],envelope['aggregate_id'])
        if ((current.actor_id,current.grant_revision)!=(principal.actor_id,principal.grant_revision)
                or 'research.control' not in current.capabilities):
            raise AuthorizationDenied('AUTHORIZATION_CHANGED')
        return receipt

    async def get_command(self, command_id, session_context):
        try:
            if str(UUID(command_id))!=command_id: raise ValueError()
        except (ValueError,TypeError,AttributeError) as exc: raise ContractError('COMMAND_ID_INVALID') from exc
        principal=await self._principal(session_context,'ReadCommand',command_id)
        if 'control.commands.read' not in principal.capabilities: raise AuthorizationDenied('ACTION_DENIED')
        if self._backend is None: raise AuthenticationUnavailable('CONTROL_BACKEND_UNAVAILABLE')
        # This intermediate result is private; no response is disclosed yet.
        # Backend independently enforces scope too; ownership comes from durable
        # receipt metadata, never request JSON.
        receipt=await self._backend.get_command(command_id,session_context)
        receipt=validate_receipt(receipt,command_id,getattr(self._backend,'generation',None))
        if receipt['commit_status']=='UNKNOWN':
            current=await self._principal(session_context,'ReadCommand',command_id)
            if ((current.actor_id,current.grant_revision)!=(principal.actor_id,principal.grant_revision)
                    or 'control.commands.read' not in current.capabilities):
                raise AuthorizationDenied('ACTION_DENIED')
            return receipt
        actor=_identifier(receipt.get('actor_id'))
        aggregate=_identifier(receipt.get('aggregate_id'))
        current=await self._principal(session_context,'ReadCommand',aggregate)
        if ((current.actor_id,current.grant_revision)!=(principal.actor_id,principal.grant_revision) or
                'control.commands.read' not in current.capabilities or
                (actor!=current.actor_id and 'control.commands.audit_all' not in current.capabilities)):
            raise AuthorizationDenied('RECEIPT_SCOPE_DENIED')
        return receipt


class StreamView:
    """Client reducer for authenticated consistent backend snapshots/events.

    Caller must supply actual verified backend observations, not browser wall
    clock/JSON claims. Time is local monotonic milliseconds; source timestamps
    and revisions remain separate. This class never authorizes mutations.
    """
    def __init__(self):
        self.generation=None; self.revision=0; self.sequence=0
        self._seen=0; self._ttl=0; self._quorum=False; self._connected=False
    def snapshot(self,generation,revision,sequence,received_ms,freshness_ms,quorum):
        _identifier(generation)
        for number in (revision,sequence,received_ms,freshness_ms): _integer(number)
        if not 0<freshness_ms<=60000 or type(quorum) is not bool: raise ContractError('SNAPSHOT_INVALID')
        if (self.generation==generation and (revision<self.revision or sequence<self.sequence)):
            raise ContractError('SNAPSHOT_REGRESSION')
        self.generation=generation;self.revision=revision;self.sequence=sequence
        self._seen=received_ms;self._ttl=freshness_ms;self._quorum=quorum;self._connected=True
    def event(self,generation,sequence,revision,received_ms):
        _identifier(generation)
        for number in (sequence,revision,received_ms): _integer(number)
        if not self._connected or generation!=self.generation:
            self._connected=False;raise ContractError('SNAPSHOT_REQUIRED')
        if sequence==self.sequence and revision==self.revision: return False
        if sequence!=self.sequence+1 or revision<self.revision or received_ms<self._seen:
            self._connected=False;raise ContractError('EVENT_GAP_OR_REGRESSION')
        self.sequence=sequence;self.revision=revision;self._seen=received_ms
        return True
    def disconnect(self): self._connected=False
    def status(self,now_ms):
        _integer(now_ms)
        if self.generation is None:return 'OFFLINE'
        if not self._connected:return 'RECONNECTING'
        if not 0<=now_ms-self._seen<=self._ttl:return 'STALE'
        if not self._quorum:return 'NO_QUORUM'
        return 'LIVE'
