"""Fixed Consul identity guard records, NOT native authentication or admission.

Only a qualified native provider can resolve these IDs from a Windows principal.
The authority adapter must consistently read these exact keys, validate records,
then check their actual ModifyIndices in the SAME transaction as every effect.
This module performs no I/O, provisions nothing, grants no capabilities, and does
not replace native expiry/revocation checks or the existing Consul leader fence.
"""
from dataclasses import dataclass
import json
import re
from types import MappingProxyType


class IdentityRecordError(ValueError):
    pass


@dataclass(frozen=True)
class IdentityBinding:
    cluster_id: str
    principal_id: str
    session_id: str
    enrollment_id: str
    policy_id: str
    node_id: str


_UUID=re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}')
_ID=re.compile(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}')
_REV=re.compile(r'[1-9][0-9]{0,18}')
_OPS=frozenset({'OPEN_CONNECTION','OPEN_SUBSCRIPTION','ACK_SNAPSHOT',
                'CLOSE_SUBSCRIPTION','CLOSE_CONNECTION','GET_COMMAND'})
_COMMON=frozenset({'schema','kind','cluster_id','principal_id','state','revision'})
_EXTRA={
    'principal':frozenset({'node_id','sid'}),
    'session':frozenset({'session_id','enrollment_id','policy_id','native_logon_id'}),
    'enrollment':frozenset({'enrollment_id','node_id'}),
    'policy':frozenset({'policy_id','role','permissions'}),
}


def _need(ok,code):
    if not ok:raise IdentityRecordError(code)


def guard_keys(binding):
    """Derive paths only from canonical UUIDs; never accept caller KV paths."""
    _need(type(binding) is IdentityBinding,'BINDING_TYPE')
    for name in binding.__dataclass_fields__:
        value=getattr(binding,name)
        _need(type(value) is str and _UUID.fullmatch(value) is not None,'BINDING_UUID')
    prefix=f'unified/{binding.cluster_id}/security/v1/'
    return MappingProxyType({
        'principal':prefix+'principals/'+binding.principal_id,
        'session':prefix+'sessions/'+binding.session_id,
        'enrollment':prefix+'enrollments/'+binding.enrollment_id,
        'policy':prefix+'policies/'+binding.policy_id,
    })


def _pairs(pairs):
    result={}
    for key,value in pairs:
        _need(key not in result,'DUPLICATE_KEY')
        result[key]=value
    return result


def _reject_number(_):
    raise IdentityRecordError('NUMBER_NOT_SUPPORTED')


def decode_guard_records(binding,raw_records):
    """Return immutable structural records, never a trusted principal/context.

    Inputs are actual Consul values read by the authority adapter. Their indices
    must be captured by that adapter, not supplied through an HTTP/native claim.
    ACTIVE is necessary but insufficient for admission. No timestamps grant a
    cached validity interval. Session destruction/current native logon validity
    remain the native provider's responsibility.
    """
    guard_keys(binding)
    _need(type(raw_records) is dict and set(raw_records)==set(_EXTRA),'RECORD_INVENTORY')
    parsed={}
    for kind,raw in raw_records.items():
        _need(type(raw) is bytes and 0<len(raw)<=16384,'RECORD_BYTES')
        try:
            record=json.loads(raw.decode('ascii'),object_pairs_hook=_pairs,
                              parse_int=_reject_number,parse_float=_reject_number,
                              parse_constant=_reject_number)
        except (UnicodeError,ValueError,RecursionError) as exc:
            raise IdentityRecordError('RECORD_JSON') from exc
        _need(type(record) is dict and set(record)==_COMMON|_EXTRA[kind],'RECORD_FIELDS')
        _need(record['schema']=='unified.security.identity-record.v1' and record['kind']==kind,'RECORD_SCHEMA')
        _need(type(record['state']) is str and record['state']=='ACTIVE','RECORD_INACTIVE')
        revision=record['revision']
        _need(type(revision) is str and _REV.fullmatch(revision) is not None and int(revision)<=2**63-1,'REVISION')
        for name in ('cluster_id','principal_id','session_id','enrollment_id','policy_id','node_id'):
            if name in record:
                _need(type(record[name]) is str and record[name]==getattr(binding,name),'CROSS_BINDING')
        if kind=='principal':
            sid=record['sid']
            _need(type(sid) is str and len(sid)<=184 and re.fullmatch(r'S-1-[0-9]+(?:-[0-9]+){1,15}',sid) is not None,'SID')
        elif kind=='session':
            logon=record['native_logon_id']
            _need(type(logon) is str and re.fullmatch(r'[0-9a-f]{16}',logon) is not None,'NATIVE_LOGON_ID')
        elif kind=='policy':
            role=record['role'];ops=record['permissions']
            _need(type(role) is str and _ID.fullmatch(role) is not None,'ROLE')
            _need(type(ops) is list and len(ops)<=len(_OPS) and all(type(x) is str and x in _OPS for x in ops),'PERMISSIONS')
            _need(ops==sorted(set(ops)),'PERMISSION_ORDER_OR_DUPLICATE')
        canonical=json.dumps(record,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')
        _need(canonical==raw,'NONCANONICAL_RECORD')
        parsed[kind]=MappingProxyType({k:tuple(v) if type(v) is list else v for k,v in record.items()})
    return MappingProxyType(parsed)
