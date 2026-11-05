"""Bounded operator contracts and client cursor state; no identity/runtime factory.

The default is AUTHENTICATION_UNAVAILABLE. A deployment must admit a real human
verifier and existing consensus backend separately. A Python principal object is
not authentication evidence. This module does not open listeners or store secrets.
"""
from dataclasses import dataclass
import json
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
    def require_current(self, context: object, action: str, aggregate_id: str) -> CurrentPrincipal:
        """Verify actual human session, expiry, revocation and current grant."""


class CoordinationCommands(Protocol):
    def submit(self, lease: object, envelope: dict, session_context: object) -> object: ...
    def get_command(self, command_id: str, session_context: object) -> object: ...


class _UnavailableVerifier:
    def require_current(self, context, action, aggregate_id):
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
    except (ValueError,TypeError,AttributeError) as exc:
        raise ContractError('COMMAND_ID_INVALID') from exc
    _integer(value['expected_revision'])
    if value['schema']!='unified.command.v1' or value['aggregate_type']!='research':
        raise ContractError('SCHEMA_OR_AGGREGATE_UNSUPPORTED')
    if value['action']!='SetResearchControl': raise ContractError('ACTION_UNSUPPORTED')
    payload=value['payload']
    if (type(payload) is not dict or set(payload)!={'mode','state'}
            or payload['mode']!='LAB' or payload['state'] not in ('PAUSED','RUNNING')):
        raise ContractError('PAYLOAD_UNSUPPORTED')
    try:
        encoded=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
    except (ValueError,TypeError,UnicodeError) as exc: raise ContractError('JSON_INVALID') from exc
    if len(encoded)>32768: raise ContractError('ENVELOPE_TOO_LARGE')
    return json.loads(encoded)


class OperatorGateway:
    """Admission seam, not an authority or authenticator.

    The backend independently revalidates the current principal, quorum, revision,
    durable idempotency binding and execution fence. Never wire an untrusted
    caller-supplied verifier through an HTTP/configuration surface.
    """
    def __init__(self, backend, principal_provider=None):
        self._backend=backend
        self._provider=principal_provider if principal_provider is not None else _UnavailableVerifier()

    def _principal(self, context, action, aggregate_id):
        principal=self._provider.require_current(context,action,aggregate_id)
        try:
            _identifier(principal.actor_id); _integer(principal.grant_revision)
            valid=(principal.principal_kind=='HUMAN' and type(principal.capabilities) is frozenset
                   and bool(principal.capabilities) and principal.capabilities <= _CAPABILITIES)
        except (AttributeError,ContractError,TypeError): valid=False
        if not valid: raise AuthorizationDenied('HUMAN_CURRENT_GRANT_REQUIRED')
        return principal

    def submit(self, lease, envelope, session_context):
        envelope=validate_envelope(envelope)
        principal=self._principal(session_context,envelope['action'],envelope['aggregate_id'])
        if principal.actor_id!=envelope['actor_id'] or 'research.control' not in principal.capabilities:
            raise AuthorizationDenied('ACTION_DENIED')
        # Canonical actor comes only from verified provider output.
        envelope['actor_id']=principal.actor_id
        if self._backend is None: raise AuthenticationUnavailable('CONTROL_BACKEND_UNAVAILABLE')
        return self._backend.submit(lease,envelope,session_context)

    def get_command(self, command_id, session_context):
        try:
            if str(UUID(command_id))!=command_id: raise ValueError()
        except (ValueError,TypeError,AttributeError) as exc: raise ContractError('COMMAND_ID_INVALID') from exc
        principal=self._principal(session_context,'ReadCommand',command_id)
        if 'control.commands.read' not in principal.capabilities: raise AuthorizationDenied('ACTION_DENIED')
        if self._backend is None: raise AuthenticationUnavailable('CONTROL_BACKEND_UNAVAILABLE')
        # This intermediate result is private; no response is disclosed yet.
        # Backend independently enforces scope too; ownership comes from durable
        # receipt metadata, never request JSON.
        receipt=self._backend.get_command(command_id,session_context)
        if receipt is None: return None
        if type(receipt) is not dict: raise ContractError('RECEIPT_INVALID')
        actor=_identifier(receipt.get('actor_id'))
        aggregate=_identifier(receipt.get('aggregate_id'))
        current=self._principal(session_context,'ReadCommand',aggregate)
        if ('control.commands.read' not in current.capabilities or
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
