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
from .commands import RawRequest,AdmittedContext,prepare_open

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

class ControlMuxRuntime:
    """Explicit async composition; no listener or implicit native provider.

    Root's raw native front must enforce framing/body limits and originate the
    native connection handle. A synthetic fixture is not product authentication.
    WSGI ControlMuxApp above deliberately remains closed until Root integration.
    """
    def __init__(self,*,store=None,admission=None,leader_provider=None):
        self.store=store;self.admission=admission;self.leader_provider=leader_provider
    async def handle(self,request):
        if self.admission is None:return _error(503,'AUTHENTICATION_UNAVAILABLE','PROVIDER_UNAVAILABLE')
        if type(request) is not RawRequest:return _error(400,'INVALID_REQUEST')
        # Header inventory is the RAW front's uncombined sequence, never a WSGI
        # dictionary which can silently merge duplicate security headers.
        try:
            if type(request.headers) is not tuple or len(request.headers)>64:raise ValueError()
            headers={}
            for pair in request.headers:
                if type(pair) is not tuple or len(pair)!=2:raise ValueError()
                name,value=pair
                if type(name) is not bytes or type(value) is not bytes or len(name)>128 or len(value)>4096:raise ValueError()
                if not re.fullmatch(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+",name) or any(c<32 or c>126 for c in value):raise ValueError()
                key=name.decode('ascii').lower()
                if key in headers:raise ValueError()
                headers[key]=value.decode('ascii')
            if 'transfer-encoding' in headers or type(request.body) is not bytes or len(request.body)>16384:raise ValueError()
            if request.path!='/control/v3/connections':return _error(503,'ADMISSION_UNAVAILABLE','PROVIDER_UNAVAILABLE')
            if request.method!='POST':return _error(405,'METHOD_NOT_ALLOWED',extra=(('Allow','POST'),))
            if headers.get('content-type')!='application/json' or headers.get('content-length')!=str(len(request.body)):raise ValueError()
            if any(k.startswith('x-expected-') for k in headers):raise ValueError()
            request_id=headers['x-request-id'];key=headers['idempotency-key']
        except (ValueError,KeyError,UnicodeError):return _error(400,'INVALID_REQUEST')
        try:
            context=self.admission.resolve(request,'OPEN_CONNECTION')
            if type(context) is not AdmittedContext:raise ValueError()
        except Exception:return _error(401,'UNAUTHENTICATED')
        try:command=prepare_open(context,request.body,request_id,key)
        except ValueError:return _error(400,'INVALID_REQUEST')
        if self.store is None or self.leader_provider is None or self.store.admission is not self.admission:
            return _error(503,'ADMISSION_UNAVAILABLE','PROVIDER_UNAVAILABLE',command.request_id)
        try:
            leader=await self.leader_provider()
            result=await self.store.open(leader,context,command)
        except Exception:return _response(503,encode(validate('command_unknown',dict(schema='unified.control.command-unknown.v3',status='UNKNOWN',
            request_id=command.request_id,command_digest=command.digest,reason='AUTHORITY_UNAVAILABLE'))))
        if result.kind=='COMMITTED':return _response(result.status,result.body)
        if result.kind=='CONFLICT':return _error(409,'CONFLICT','REQUEST_ID_CONFLICT',command.request_id)
        if result.kind=='UNKNOWN':return _response(503,encode(validate('command_unknown',dict(schema='unified.control.command-unknown.v3',status='UNKNOWN',
            request_id=command.request_id,command_digest=command.digest,reason='AUTHORITY_UNAVAILABLE'))))
        return _error(503,'ADMISSION_UNAVAILABLE','PROVIDER_UNAVAILABLE',command.request_id)
