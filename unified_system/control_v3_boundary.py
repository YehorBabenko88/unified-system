"""Internal experimental WSGI boundary. Default app admits no data/effects.

Only tests compose synthetic providers; this module starts no server and has no
provider/env/boolean registration or activation switch. Not the final ControlV3 ABI.
"""
from dataclasses import dataclass
import hashlib
import json
import re

from .control_v3_read_adapter import PROFILE, Selector, ReadFailure, canonical, u63

ROOT='/control/experimental/v3/'
UUID=r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}'
ID=r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}'
SELECTOR=re.compile(r'scope=(CONTROL|DATASET)&dataset_id=(~|'+UUID+r')&source_id=(~|'+ID+r')&partition_id=(~|'+ID+r')')


class BoundaryError(ValueError):
    def __init__(self,status=400,code='INVALID_REQUEST',allow=None):
        super().__init__(code);self.status=status;self.code=code;self.allow=allow


@dataclass(frozen=True)
class ParsedRequest:
    method: str
    path: str
    route: str
    selector: Selector | None = None
    cursor: str | None = None
    expected_epoch: str | None = None
    expected_sequence: str | None = None
    request_id: str | None = None
    stream_attempt_id: str | None = None
    command_digest: str | None = None


def _uuid(value):
    if type(value) is not str or not re.fullmatch(UUID,value):raise BoundaryError()
    return value


def _epoch(e,name):
    value=e.get(name)
    if not u63(value,True):raise BoundaryError()
    return value


def parse_request(e):
    method=e.get('REQUEST_METHOD');path=e.get('PATH_INFO');query=e.get('QUERY_STRING','')
    length=e.get('CONTENT_LENGTH','')
    if (type(method) is not str or not re.fullmatch('[A-Z]{1,16}',method)
            or type(path) is not str or not 0<len(path)<=2048 or not re.fullmatch('/[A-Za-z0-9/._:-]*',path)
            or '//' in path or any(p in ('.','..') for p in path.split('/'))
            or type(query) is not str or not query.isascii() or len(query)>2055
            or type(length) is not str or not re.fullmatch(r'|0|[1-9][0-9]{0,4}',length)
            or int(length or '0')>16384 or 'HTTP_TRANSFER_ENCODING' in e
            or e.get('wsgi.input_terminated',False) not in (False,None)):
        raise BoundaryError()
    for name in ('RAW_URI','REQUEST_URI'):
        raw=e.get(name)
        if raw is not None and (type(raw) is not str or raw!=path+('?' + query if query else '')):
            raise BoundaryError()
    routes={ROOT+'capabilities':('capabilities','GET'),ROOT+'snapshot':('snapshot','GET'),
            ROOT+'events':('events','GET'),ROOT+'connections':('admission','POST')}
    route=routes.get(path)
    target=None
    match=re.fullmatch(re.escape(ROOT)+r'(connections|subscriptions)/('+UUID+r')',path)
    if route is None and match:route=('admission','DELETE');target=match.group(2)
    if route is None:raise BoundaryError(404,'NOT_FOUND')
    kind,allowed=route
    if method!=allowed:raise BoundaryError(405,'METHOD_NOT_ALLOWED',allowed)
    if method in ('GET','DELETE') and length not in ('','0'):raise BoundaryError()
    if kind=='snapshot':
        if len(query)>512:raise BoundaryError()
        match=SELECTOR.fullmatch(query)
        if not match:raise BoundaryError()
        scope,dataset,source,partition=match.groups()
        if (scope=='CONTROL' and (dataset,source,partition)!=('~','~','~')
                or scope=='DATASET' and (dataset=='~' or source=='~' and partition!='~')):raise BoundaryError()
        return ParsedRequest(method,path,kind,Selector(scope,*[None if x=='~' else x for x in (dataset,source,partition)]))
    if kind=='events':
        if not re.fullmatch(r'cursor=[A-Za-z0-9_-]{1,2048}',query):raise BoundaryError()
        return ParsedRequest(method,path,kind,cursor=query[7:],
            expected_epoch=_epoch(e,'HTTP_X_EXPECTED_CONNECTION_EPOCH'),
            expected_sequence=_epoch(e,'HTTP_X_EXPECTED_SEQUENCE'),
            stream_attempt_id=_uuid(e.get('HTTP_X_STREAM_ATTEMPT_ID')))
    if query:raise BoundaryError()
    if kind=='capabilities':return ParsedRequest(method,path,kind)
    request_id=_uuid(e.get('HTTP_X_REQUEST_ID'));key=e.get('HTTP_IDEMPOTENCY_KEY')
    if type(key) is not str or not re.fullmatch(ID,key):raise BoundaryError()
    epoch=sub_epoch=None;body=b''
    if method=='POST':
        if e.get('CONTENT_TYPE')!='application/json' or not length or length=='0':raise BoundaryError()
        stream=e.get('wsgi.input')
        if not callable(getattr(stream,'read',None)):raise BoundaryError()
        try:body=stream.read(int(length))
        except (OSError,ValueError,TypeError):raise BoundaryError() from None
        if type(body) is not bytes or len(body)!=int(length):raise BoundaryError()
        def pairs(items):
            result={}
            for k,v in items:
                if k in result:raise BoundaryError()
                result[k]=v
            return result
        try:
            value=json.loads(body.decode('ascii'),object_pairs_hook=pairs)
            if type(value) is not dict or canonical(value)!=body:raise BoundaryError()
            if set(value)!={'schema','request_id','role','app_instance_id','enrollment_revision'}:raise BoundaryError()
            if (value['schema']!='unified.control-open.experimental.v3' or value['request_id']!=request_id
                    or value['role'] not in ('NODE_CONTROL','OPERATOR_CONTROL')
                    or not u63(value['enrollment_revision'],True)):raise BoundaryError()
            _uuid(value['app_instance_id'])
        except (ValueError,UnicodeError,RecursionError,TypeError):raise BoundaryError() from None
    else:
        epoch=_epoch(e,'HTTP_X_EXPECTED_CONNECTION_EPOCH')
        if '/subscriptions/' in path:sub_epoch=_epoch(e,'HTTP_X_EXPECTED_SUBSCRIPTION_EPOCH')
    digest=hashlib.sha256(canonical(dict(profile=PROFILE,method=method,path=path,target=target,
        expected_connection_epoch=epoch,expected_subscription_epoch=sub_epoch,
        request_id=request_id,idempotency_key=key,body_sha256=hashlib.sha256(body).hexdigest()))).hexdigest()
    # This unauthenticated parse digest is not final authenticated idempotency identity.
    return ParsedRequest(method,path,kind,request_id=request_id,expected_epoch=epoch,command_digest=digest)


def handle_request(environ,start_response,adapter=None):
    """Reusable dispatcher. An injected Python adapter is not native admission."""
    status=200;allow=None;ctype='application/json';body=None
    try:
        req=parse_request(environ)
        if req.route=='capabilities':
            body=canonical(dict(schema='unified.control-capabilities.experimental.v3',profile=PROFILE,
                native_admission=False,snapshots_available=False,events_available=False,effects_available=False))
        elif req.route=='admission':raise BoundaryError(503,'ADMISSION_UNAVAILABLE')
        elif adapter is None:raise BoundaryError(503,'AUTHENTICATION_UNAVAILABLE')
        else:ctype,body=adapter.read(req)
    except ReadFailure as exc:
        status=401 if exc.code=='UNAUTHORIZED' else 503
        body=canonical(dict(schema='unified.control-error.experimental.v3',profile=PROFILE,
            code=exc.code,request_id=None,retryable=False,native_admission=False))
    except BoundaryError as exc:
        status,allow=exc.status,exc.allow
        body=canonical(dict(schema='unified.control-error.experimental.v3',profile=PROFILE,
            code=exc.code,request_id=None,retryable=False,native_admission=False))
    labels={200:'OK',400:'Bad Request',401:'Unauthorized',404:'Not Found',405:'Method Not Allowed',503:'Service Unavailable'}
    headers=[('Content-Type',ctype),('Content-Length',str(len(body))),('Cache-Control','no-store'),
             ('X-Content-Type-Options','nosniff')]
    if allow:headers.append(('Allow',allow))
    start_response(str(status)+' '+labels[status],headers)
    return [] if environ.get('REQUEST_METHOD')=='HEAD' else [body]


class ControlV3App:
    """No activation/provider/env arguments; no fixture provider selection."""
    def __call__(self,environ,start_response):
        return handle_request(environ,start_response)
