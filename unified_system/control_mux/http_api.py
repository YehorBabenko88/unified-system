"""Control Mux WSGI composition boundary; native composition pending.
No environment activation, listener, fixture context or header identity fallback.
"""
from .codec import encode, validate

class ControlMuxApp:
    def __call__(self, environ, start_response):
        # Do not read an unadmitted body or expose authority/cluster information.
        body=encode(validate('error_v3',dict(schema='unified.control.error.v3',request_id=None,code='AUTHENTICATION_UNAVAILABLE',reason='PROVIDER_UNAVAILABLE',retryable=False,retry_after_ms=None,evidence_refs=[])))
        start_response('503 Service Unavailable',[
            ('Content-Type','application/json'),('Content-Length',str(len(body))),
            ('Cache-Control','no-store')])
        return [] if environ.get('REQUEST_METHOD')=='HEAD' else [body]


from dataclasses import dataclass
import re
from .commands import RawRequest,AdmittedContext,prepare_open,prepare_close,prepare_subscribe,prepare_ack,NativeAdmissionError,native_admission_kind

@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: tuple[tuple[str,str],...]
    body: bytes

def _response(status,body,extra=()):
    return HttpResponse(status,(('Content-Type','application/json'),('Content-Length',str(len(body))),('Cache-Control','no-store'))+tuple(extra),body)

def _error(status,code,reason='NONE',request_id=None,extra=()):
    return _response(status,encode(validate('error_v3',dict(schema='unified.control.error.v3',request_id=request_id,
        code=code,reason=reason,retryable=False,retry_after_ms=None,evidence_refs=[]))),extra)

def _headers(pairs):
    if type(pairs) is not tuple or len(pairs)>64:raise ValueError()
    headers={}
    for pair in pairs:
        if type(pair) is not tuple or len(pair)!=2:raise ValueError()
        name,value=pair
        if type(name) is not bytes or type(value) is not bytes or len(name)>128 or len(value)>4096:raise ValueError()
        if not re.fullmatch(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+",name) or any(c<32 or c>126 for c in value):raise ValueError()
        key=name.decode('ascii').lower()
        if key in headers:raise ValueError()
        headers[key]=value.decode('ascii')
    return headers


def _closed_get_query(request):
    # Bounded metadata correlation only. Never read an unadmitted body/authority.
    try:
        if type(request) is not RawRequest or type(request.method) is not str or request.method!='GET' or type(request.path) is not str:return None
        match=re.fullmatch('/control/v3/commands/([0-9a-f-]{36})',request.path)
        if match is None:return None
        original=validate('uuid',match.group(1));query=validate('uuid',_headers(request.headers)['x-request-id'])
        return query if query!=original else None
    except (ValueError,KeyError,UnicodeError):return None


def _native_get_error(kind,query_request_id):
    if kind in ('UNAUTHENTICATED','SESSION_EXPIRED'):return _error(401,kind,request_id=query_request_id)
    if kind=='FORBIDDEN':return _error(403,'FORBIDDEN','ROLE_DENIED',query_request_id)
    return _error(503,'AUTHENTICATION_UNAVAILABLE','PROVIDER_UNAVAILABLE',query_request_id)


class ControlMuxRuntime:
    """Explicit async composition; no listener or implicit native provider.

    Root's raw native front must enforce framing/body limits and originate the
    native connection handle. A synthetic fixture is not product authentication.
    WSGI ControlMuxApp above deliberately remains closed until Root integration.
    """
    def __init__(self,*,store=None,admission=None,leader_provider=None):
        self.store=store;self.admission=admission;self.leader_provider=leader_provider
    async def handle(self,request):
        if self.admission is None:return _error(503,'AUTHENTICATION_UNAVAILABLE','PROVIDER_UNAVAILABLE',_closed_get_query(request))
        if type(request) is not RawRequest:return _error(400,'INVALID_REQUEST')
        try:
            if type(request.method) is not str or type(request.path) is not str:raise ValueError()
            headers=_headers(request.headers)
            if 'transfer-encoding' in headers or type(request.body) is not bytes or len(request.body)>16384:raise ValueError()
            connection_id=subscription_id=original_request_id=None
            uid=r'([0-9a-f-]{36})'
            if match:=re.fullmatch('/control/v3/commands/'+uid,request.path):
                operation='GET_COMMAND';method='GET';original_request_id=validate('uuid',match.group(1))
            elif request.path=='/control/v3/connections':operation='OPEN_CONNECTION';method='POST'
            elif match:=re.fullmatch('/control/v3/connections/'+uid+'/subscriptions',request.path):
                operation='OPEN_SUBSCRIPTION';method='POST';connection_id=validate('uuid',match.group(1))
            elif match:=re.fullmatch('/control/v3/connections/'+uid,request.path):
                operation='CLOSE_CONNECTION';method='DELETE';connection_id=validate('uuid',match.group(1))
            elif match:=re.fullmatch('/control/v3/subscriptions/'+uid+'/snapshot-acks',request.path):
                operation='ACK_SNAPSHOT';method='POST';subscription_id=validate('uuid',match.group(1))
            elif match:=re.fullmatch('/control/v3/subscriptions/'+uid,request.path):
                operation='CLOSE_SUBSCRIPTION';method='DELETE';subscription_id=validate('uuid',match.group(1))
            else:return _error(503,'ADMISSION_UNAVAILABLE','PROVIDER_UNAVAILABLE')
            if request.method!=method:return _error(405,'METHOD_NOT_ALLOWED',extra=(('Allow',method),))
            if method=='GET':
                if request.body!=b'' or headers.get('content-length','0')!='0' or 'content-type' in headers or 'idempotency-key' in headers or any(k.startswith('x-expected-') for k in headers):raise ValueError()
            elif method=='POST':
                if headers.get('content-type')!='application/json' or headers.get('content-length')!=str(len(request.body)):raise ValueError()
            elif request.body!=b'' or headers.get('content-length','0')!='0' or 'content-type' in headers:raise ValueError()
            request_id=validate('uuid',headers['x-request-id'])
            if operation=='GET_COMMAND':
                if request_id==original_request_id:raise ValueError()
            else:key=headers['idempotency-key']
            if operation=='GET_COMMAND':pass
            elif operation=='OPEN_CONNECTION':
                if any(k.startswith('x-expected-') for k in headers):raise ValueError()
            else:
                connection_epoch=validate('positive',headers['x-expected-connection-epoch'])
                if subscription_id is not None:subscription_epoch=validate('positive',headers['x-expected-subscription-epoch'])
                elif 'x-expected-subscription-epoch' in headers:raise ValueError()
        except (ValueError,KeyError,UnicodeError):return _error(400,'INVALID_REQUEST')
        try:
            context=self.admission.resolve(request,operation)
            if type(context) is not AdmittedContext:raise ValueError()
        except NativeAdmissionError as exc:
            if operation!='GET_COMMAND':return _error(401,'UNAUTHENTICATED')
            return _native_get_error(native_admission_kind(exc),request_id)
        except Exception:
            if operation=='GET_COMMAND':return _native_get_error('UNAVAILABLE',request_id)
            return _error(401,'UNAUTHENTICATED')
        if self.store is None or self.store.admission is not self.admission or (operation!='GET_COMMAND' and self.leader_provider is None):
            return _error(503,'ADMISSION_UNAVAILABLE','PROVIDER_UNAVAILABLE',request_id)
        if operation=='GET_COMMAND':
            try:result=await self.store.reconcile_document(context,original_request_id,request_id)
            except Exception:return _error(503,'ADMISSION_UNAVAILABLE','PROVIDER_UNAVAILABLE',request_id)
            if result.kind=='COMMITTED':return _response(200,result.body)
            if result.kind=='DISCLOSURE_DENIED':return _error(403,'FORBIDDEN','NONE',request_id)
            if result.kind in ('UNAUTHENTICATED','SESSION_EXPIRED','FORBIDDEN'):return _native_get_error(result.kind,request_id)
            reason={'AMBIGUOUS':'RECEIPT_AMBIGUOUS','UNRESOLVED':'NONE'}.get(result.kind,'PROVIDER_UNAVAILABLE')
            return _error(503,'ADMISSION_UNAVAILABLE',reason,request_id)
        if subscription_id is not None:
            binding=await self.store.subscription_connection(context,subscription_id,operation)
            if not isinstance(binding,tuple):return _error(503,'ADMISSION_UNAVAILABLE','PROVIDER_UNAVAILABLE',request_id)
            connection_id,actual_connection_epoch,actual_subscription_epoch=binding
            if (connection_epoch,subscription_epoch)!=(actual_connection_epoch,actual_subscription_epoch):return _error(409,'CONFLICT','EPOCH_MISMATCH',request_id)
        try:
            if operation=='OPEN_CONNECTION':command=prepare_open(context,request.body,request_id,key)
            elif operation=='OPEN_SUBSCRIPTION':command=prepare_subscribe(context,request.body,request_id,key,connection_id,connection_epoch)
            elif operation=='ACK_SNAPSHOT':command=prepare_ack(context,request.body,request_id,key,connection_id,subscription_id,connection_epoch,subscription_epoch)
            else:command=prepare_close(context,request.body,request_id,key,connection_id,connection_epoch,subscription_id,subscription_epoch if subscription_id is not None else None)
        except ValueError:return _error(400,'INVALID_REQUEST')
        try:
            leader=await self.leader_provider()
            handler={'OPEN_CONNECTION':self.store.open,'OPEN_SUBSCRIPTION':self.store.subscribe,'ACK_SNAPSHOT':self.store.ack_snapshot,
                'CLOSE_CONNECTION':self.store.close_connection,'CLOSE_SUBSCRIPTION':self.store.close_subscription}[operation]
            result=await handler(leader,context,command)
        except Exception:return _response(503,encode(validate('command_unknown',dict(schema='unified.control.command-unknown.v3',status='UNKNOWN',
            request_id=command.request_id,command_digest=command.digest,reason='AUTHORITY_UNAVAILABLE'))))
        if result.kind=='COMMITTED':return _response(result.status,result.body)
        if result.kind=='FORBIDDEN':return _error(403,'FORBIDDEN','ROLE_DENIED',command.request_id)
        if result.kind=='CONFLICT':return _error(409,'CONFLICT','REQUEST_ID_CONFLICT',command.request_id)
        if result.kind=='UNKNOWN':return _response(503,encode(validate('command_unknown',dict(schema='unified.control.command-unknown.v3',status='UNKNOWN',
            request_id=command.request_id,command_digest=command.digest,reason='AUTHORITY_UNAVAILABLE'))))
        return _error(503,'ADMISSION_UNAVAILABLE','PROVIDER_UNAVAILABLE',command.request_id)
