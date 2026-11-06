"""Executable experimental read logic; provider outputs remain untrusted claims.

No native identity factory, Consul client, listener or activation API. ROOT must
separately qualify real provider composition; test composition is not admission.
"""
from dataclasses import dataclass
import json
import re

PROFILE='unified.control-read-boundary.experimental.v3'
MAX_SNAPSHOT=65536
MAX_BATCH=131072


class ReadFailure(ValueError):
    def __init__(self,code):
        if code not in ('AUTHENTICATION_UNAVAILABLE','UNAUTHORIZED','AUTHORITY_UNAVAILABLE'):
            code='AUTHORITY_UNAVAILABLE'
        super().__init__(code);self.code=code


@dataclass(frozen=True)
class Selector:
    kind: str
    dataset_id: str | None
    source_id: str | None
    partition_id: str | None


@dataclass(frozen=True)
class ReadContext:
    actor_id: str
    session_id: str
    view_id: str
    authorization_revision: str


def u63(value,positive=False):
    return (type(value) is str and len(value)<=19
        and re.fullmatch(r'0|[1-9][0-9]{0,18}',value) is not None
        and int(value)<=2**63-1 and (not positive or int(value)>0))


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')


def bounded(value,limit):
    nodes=0
    encoded_size=0
    def walk(x,depth=1):
        nonlocal nodes,encoded_size
        nodes+=1
        if nodes>4096:raise ReadFailure('AUTHORITY_UNAVAILABLE')
        if depth>8:raise ReadFailure('AUTHORITY_UNAVAILABLE')
        if type(x) is dict:
            if len(x)>48 or any(type(k) is not str or len(k)>128 for k in x):raise ReadFailure('AUTHORITY_UNAVAILABLE')
            encoded_size+=2
            for k,item in x.items():
                encoded_size+=len(canonical(k))+2
                if encoded_size>limit:raise ReadFailure('AUTHORITY_UNAVAILABLE')
                walk(item,depth+1)
        elif type(x) is list:
            if len(x)>100:raise ReadFailure('AUTHORITY_UNAVAILABLE')
            encoded_size+=2+len(x)
            for item in x:walk(item,depth+1)
        elif type(x) is str:
            if len(x)>16384:raise ReadFailure('AUTHORITY_UNAVAILABLE')
            encoded_size+=len(canonical(x))
        elif x is not None and type(x) not in (int,bool):raise ReadFailure('AUTHORITY_UNAVAILABLE')
        else:
            if type(x) is int and abs(x)>2**63-1:raise ReadFailure('AUTHORITY_UNAVAILABLE')
            encoded_size+=len(canonical(x))
        if encoded_size>limit:raise ReadFailure('AUTHORITY_UNAVAILABLE')
    try:
        walk(value);raw=canonical(value)
        if len(raw)>limit:raise ReadFailure('AUTHORITY_UNAVAILABLE')
        return json.loads(raw)  # detach provider-owned data
    except (TypeError,ValueError,RecursionError,OverflowError):
        raise ReadFailure('AUTHORITY_UNAVAILABLE') from None


class ControlReadAdapter:
    """Internal dependency seam, not an admitted runtime factory.

    identity.resolve(parsed_request)->ReadContext|None must perform current real
    auth in future composition. authority.snapshot(context,selector) and
    authority.events(context,request) must perform actual consistent reads there.
    Neither a returned dataclass nor output schema establishes provider trust.
    """
    def __init__(self,identity=None,authority=None):
        if identity is not None and (type(identity) in (dict,bool) or not callable(getattr(identity,'resolve',None))):
            raise ValueError('typed identity dependency required')
        if authority is not None and (type(authority) in (dict,bool)
                or not all(callable(getattr(authority,n,None)) for n in ('snapshot','events'))):
            raise ValueError('typed read dependency required')
        self.identity=identity;self.authority=authority

    def _context(self,request):
        if self.identity is None:raise ReadFailure('AUTHENTICATION_UNAVAILABLE')
        try:context=self.identity.resolve(request)
        except Exception:raise ReadFailure('AUTHENTICATION_UNAVAILABLE') from None
        if type(context) is not ReadContext:raise ReadFailure('UNAUTHORIZED')
        for value in (context.actor_id,context.session_id,context.view_id):
            if type(value) is not str or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}',value):
                raise ReadFailure('UNAUTHORIZED')
        if not u63(context.authorization_revision,True):raise ReadFailure('UNAUTHORIZED')
        return context

    def read(self,request):
        context=self._context(request)
        if self.authority is None:raise ReadFailure('AUTHORITY_UNAVAILABLE')
        try:
            if request.route=='snapshot':
                claim=bounded(self.authority.snapshot(context,request.selector),MAX_SNAPSHOT)
                if (type(claim) is not dict or set(claim)!={'scope','view_id','revision','cursor','state_root','resources'}
                        or claim['scope']!=dict(kind=request.selector.kind,dataset_id=request.selector.dataset_id,
                            source_id=request.selector.source_id,partition_id=request.selector.partition_id)
                        or claim['view_id']!=context.view_id or not u63(claim['revision'])
                        or type(claim['cursor']) is not str or not re.fullmatch('[A-Za-z0-9_-]{1,2048}',claim['cursor'])
                        or type(claim['state_root']) is not str or not re.fullmatch('[0-9a-f]{64}',claim['state_root'])
                        or type(claim['resources']) is not list):raise ReadFailure('AUTHORITY_UNAVAILABLE')
                result=canonical(dict(schema='unified.control-snapshot.experimental.v3',profile=PROFILE,
                    trust='UNTRUSTED_PROVIDER_CLAIM',native_admission=False,**claim))
                if len(result)>MAX_SNAPSHOT:raise ReadFailure('AUTHORITY_UNAVAILABLE')
                content_type='application/json'
            else:
                frames=bounded(self.authority.events(context,request),MAX_BATCH)
                if type(frames) is not list or not 1<=len(frames)<=32:raise ReadFailure('AUTHORITY_UNAVAILABLE')
                result=b''
                for offset,frame in enumerate(frames):
                    if (type(frame) is not dict or set(frame)!={'epoch','sequence','view_id','kind','payload'}
                            or frame['epoch']!=request.expected_epoch or not u63(frame['sequence'],True)
                            or int(frame['sequence'])!=int(request.expected_sequence)+offset
                            or frame['view_id']!=context.view_id or frame['kind'] not in ('DATA','LIVENESS')
                            or type(frame['payload']) is not dict):raise ReadFailure('AUTHORITY_UNAVAILABLE')
                    if frame['kind']=='LIVENESS':
                        if (set(frame['payload'])!={'connection_id'}
                                or type(frame['payload']['connection_id']) is not str
                                or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}',frame['payload']['connection_id'])):
                            raise ReadFailure('AUTHORITY_UNAVAILABLE')
                    data=canonical(dict(schema='unified.control-event.experimental.v3',profile=PROFILE,
                        trust='UNTRUSTED_PROVIDER_CLAIM',native_admission=False,**frame))
                    if len(data)>32768:raise ReadFailure('AUTHORITY_UNAVAILABLE')
                    result+=b'data: '+data+b'\n\n'
                if len(result)>MAX_BATCH:raise ReadFailure('AUTHORITY_UNAVAILABLE')
                content_type='text/event-stream'
        except ReadFailure:raise
        except Exception:
            raise ReadFailure('AUTHORITY_UNAVAILABLE') from None
        if self._context(request)!=context:raise ReadFailure('UNAUTHORIZED')
        return content_type,result
