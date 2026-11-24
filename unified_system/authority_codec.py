"""Root native metadata codec and Consul plan bounds, not market arithmetic.

Extracted from Grid295 c9ffdaa authority_runtime_v1.py. Native canonical JSON
forbids numbers; control transport JSON has a distinct numeric-index policy.
"""
from dataclasses import dataclass
import hashlib,json,re

_ID=re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}')

def _id(value):
    if type(value) is not str or not _ID.fullmatch(value):raise ValueError('IDENTIFIER')
    return value

def canonical(value):
    def walk(v,depth=0):
        if depth>12:raise ValueError('DEPTH')
        if v is None or type(v) is bool:return
        if type(v) is str:
            if len(v)>16384 or any(not 32<=ord(c)<=126 for c in v):raise ValueError('ASCII_STRING')
            return
        if type(v) is list:
            if len(v)>32:raise ValueError('ARRAY_CAP')
            for x in v:walk(x,depth+1)
            return
        if type(v) is dict:
            if len(v)>64:raise ValueError('MEMBER_CAP')
            for k,x in v.items():_id(k);walk(x,depth+1)
            return
        raise ValueError('NON_JSON_OR_NUMBER')
    walk(value)
    raw=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
    if len(raw)>16384:raise ValueError('RECORD_CAP')
    return raw

@dataclass(frozen=True)
class NativePlanMeasure:
    operations: int
    encoded_bytes: int
    encoded_sha256: str

def measure_native_plan(operations):
    """Size only: no send, validation of domain semantics, permission or proof."""
    if type(operations) is not list or not 1<=len(operations)<=64:raise ValueError('OPERATION_CAP')
    raw=json.dumps(operations,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
    if len(raw)>32768:raise ValueError('TRANSACTION_BYTE_CAP')
    return NativePlanMeasure(len(operations),len(raw),hashlib.sha256(raw).hexdigest())
