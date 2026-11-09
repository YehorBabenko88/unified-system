"""Disposable authenticated negative composition; no HTTP or research permission.

Native principal-session writes are real. NOT_ATTEMPTED describes job mutation,
not authentication. Context invalidation is local plus bounded native best effort;
its return is not a native-retirement receipt. The borrowed TLS socket stays owned
by its caller. Only existing source-owned broker/Consul/handler classes are used.
"""
import asyncio
import hashlib
from pathlib import Path
import ssl
import stat
import threading
from urllib.parse import urlsplit

class NativeNegativeDenied(RuntimeError):
    pass

_PINS={
    'grid.coordination':'3dd73d3eb3dfb576f7174a94fab05a0f87fe248ffcacccfa19786ccc74f0776b',
    'grid.authority_runtime_v1':'cfb32db73f1859d9d78b03d886372cc08584c81abd64930b5409a91edc417b64',
    'grid.authority_assignment_v1':'d128cdc5f6b787e3a0ff664c3af6c5d73cdef7a751e974cb990cade3ac39394a',
    'unified_system.gateway_research_identity':'1f9714010143c5243c78494cb25bfe7f2d42e96301f57930212a2f5f3b9c869d',
    'unified_system.gateway_identity':'84093865e8477ef6562100d41137922785446c9cb4e024c9ba7105593a2b36c1',
}

def _fixed_types():
    import importlib
    modules={name:importlib.import_module(name) for name in _PINS}
    for name,module in modules.items():
        filename=vars(module).get('__file__')
        if type(filename) is not str:raise NativeNegativeDenied('PINNED_SOURCE_REQUIRED')
        path=Path(filename)
        if not path.is_absolute() or path.suffix!='.py' or filename.startswith(('\\\\','//')):
            raise NativeNegativeDenied('ORDINARY_SOURCE_REQUIRED')
        for ancestor in (*reversed(path.parents),path):
            info=ancestor.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&1024:
                raise NativeNegativeDenied('SOURCE_ALIAS_REJECTED')
        info=path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or hashlib.sha256(path.read_bytes()).hexdigest()!=_PINS[name]:
            raise NativeNegativeDenied('SOURCE_PIN_MISMATCH')
    return (modules['grid.coordination'].ConsulSessionAuthority,
        modules['unified_system.gateway_research_identity'].ResearchIdentityBroker,
        modules['grid.authority_assignment_v1'].ResearchLabAuthority,
        modules['grid.authority_assignment_v1'].ResearchAdmissionResult)

def _loopback_endpoints(endpoints,lab):
    if lab is not True or type(endpoints) is not tuple or not 1<=len(endpoints)<=3:
        raise NativeNegativeDenied('ISOLATED_LOOPBACK_ONLY')
    for value in endpoints:
        if type(value) is not str:raise NativeNegativeDenied('ISOLATED_LOOPBACK_ONLY')
        try:
            parsed=urlsplit(value);port=parsed.port;host=parsed.hostname
            canonical=parsed.scheme+'://'+('['+host+']' if host=='::1' else str(host))+':'+str(port)
            valid=parsed.scheme in ('http','https') and host in ('127.0.0.1','::1') and type(port) is int and 1<=port<=65535 and value==canonical
        except ValueError:valid=False
        if not valid:raise NativeNegativeDenied('ISOLATED_LOOPBACK_ONLY')

def _owned_client(authority,*,config=None,client=None):
    """Entry custody only; exclusive lifecycle is required throughout cleanup.

    The pinned owned Core constructor supplies no proxy/mounts. This is not a
    credential or protection against arbitrary in-process object mutation.
    """
    import httpx
    authority_type=_fixed_types()[0]
    if type(authority) is not authority_type or authority._owns_client is not True:
        raise NativeNegativeDenied('SOURCE_OWNED_HTTP_CLIENT_REQUIRED')
    if config is not None and authority.config is not config:
        raise NativeNegativeDenied('QUALIFIED_CONFIGURATION_CHANGED')
    current=authority.client
    if client is not None and current is not client:
        raise NativeNegativeDenied('QUALIFIED_HTTP_CLIENT_CHANGED')
    if (type(current) is not httpx.AsyncClient or current.trust_env is not False
            or current.is_closed is not False or current.follow_redirects is not False
            or type(current._transport) is not httpx.AsyncHTTPTransport
            or type(current._mounts) is not dict or current._mounts):
        raise NativeNegativeDenied('OPEN_PROXY_FREE_OWNED_CLIENT_REQUIRED')
    return current

def _original(raw):
    if type(raw) is not bytes or not 0<len(raw)<=16384:
        raise NativeNegativeDenied('BOUNDED_ORIGINAL_BYTES_REQUIRED')

def _loopback_tls(sock):
    if type(sock) is not ssl.SSLSocket or sock.server_side is not True:
        raise NativeNegativeDenied('REAL_LOOPBACK_TLS_REQUIRED')
    try:valid=sock.getpeername()[0] in ('127.0.0.1','::1') and sock.getsockname()[0] in ('127.0.0.1','::1')
    except OSError:valid=False
    if not valid:raise NativeNegativeDenied('REAL_LOOPBACK_TLS_REQUIRED')

def _negative_observation(original,value,*,operation):
    _original(original)
    if type(operation) is not str or operation not in ('submit','lookup'):
        raise NativeNegativeDenied('CLOSED_NEGATIVE_OPERATION')
    result_type=_fixed_types()[3]
    if type(value) is not result_type:raise NativeNegativeDenied('EXACT_NEGATIVE_DATA_REQUIRED')
    if any(type(field) is not str for field in (value.outcome,value.reason,value.original_intent_sha256,value.commit_status)):
        raise NativeNegativeDenied('EXACT_NEGATIVE_DATA_REQUIRED')
    pairs={('UNKNOWN','JOB_RECONCILIATION_API_UNQUALIFIED')}
    if operation=='submit':pairs.add(('DENIED','NATIVE_WORKER_RESOURCE_API_UNQUALIFIED'))
    if ((value.outcome,value.reason) not in pairs or value.commit_status!='NOT_ATTEMPTED'
            or value.effect_permitted is not False or value.original_intent_sha256!=hashlib.sha256(original).hexdigest()):
        raise NativeNegativeDenied('UNEXPECTED_RESEARCH_PERMISSION_REJECTED')
    return value

class DisposableNativeNegativeGateway:
    """One in-flight call on its owner loop; no queue, issuer or public endpoint."""
    def __init__(self,authority,generation,*,broker):
        authority_type,broker_type,native_type,_=_fixed_types()
        if type(self) is not DisposableNativeNegativeGateway or type(authority) is not authority_type or type(broker) is not broker_type or type(generation) is not str:
            raise NativeNegativeDenied('ACTUAL_OWNED_SOURCES_REQUIRED')
        _loopback_endpoints(authority.config.endpoints,authority.config.isolated_lab)
        timeout=authority.config.request_timeout
        if type(timeout) not in (int,float) or not 0<timeout<=2:
            raise NativeNegativeDenied('QUALIFIED_REQUEST_DEADLINE_REQUIRED')
        self._client=_owned_client(authority)
        self._native=native_type(authority,generation,broker=broker)
        self._authority=authority;self._broker=broker;self._config=authority.config
        self._loop=asyncio.get_running_loop();self._thread=threading.get_ident();self._busy=False

    async def submit(self,original_lab13_bytes,*,accepted_tls,leader):
        return await self._call(original_lab13_bytes,accepted_tls=accepted_tls,leader=leader,operation='submit')

    async def lookup(self,original_lab13_bytes,*,accepted_tls,leader):
        return await self._call(original_lab13_bytes,accepted_tls=accepted_tls,leader=leader,operation='lookup')

    async def _call(self,original,*,accepted_tls,leader,operation):
        if type(self) is not DisposableNativeNegativeGateway or threading.get_ident()!=self._thread or asyncio.get_running_loop() is not self._loop:
            raise NativeNegativeDenied('OWNER_LOOP_REQUIRED')
        if type(operation) is not str or operation not in ('submit','lookup'):
            raise NativeNegativeDenied('CLOSED_NEGATIVE_OPERATION')
        _original(original);_loopback_tls(accepted_tls)
        authority_type,broker_type,native_type,_=_fixed_types()
        if type(self._authority) is not authority_type or type(self._broker) is not broker_type or type(self._native) is not native_type:
            raise NativeNegativeDenied('ACTUAL_OWNED_SOURCES_REQUIRED')
        _owned_client(self._authority,config=self._config,client=self._client)
        timeout=self._authority.config.request_timeout
        if type(timeout) not in (int,float) or not 0<timeout<=2:
            raise NativeNegativeDenied('QUALIFIED_REQUEST_DEADLINE_REQUIRED')
        _loopback_endpoints(self._authority.config.endpoints,self._authority.config.isolated_lab)
        if self._busy:raise NativeNegativeDenied('NEGATIVE_GATEWAY_BUSY')
        self._busy=True;context=None;failure=None
        try:
            async with asyncio.timeout(15):
                context=await broker_type.open_session(self._broker,accepted_tls,leader=leader)
                if operation=='submit':
                    value=await native_type.submit(self._native,original,context=context,leader=leader,owned_attempt=None)
                else:
                    value=await native_type.lookup(self._native,original,context=context)
                return _negative_observation(original,value,operation=operation)
        except BaseException as exc:
            failure=exc
            raise
        finally:
            try:
                if context is not None:
                    try:await broker_type.invalidate_context(self._broker,context)
                    except BaseException:
                        if failure is None:raise
                        failure.add_note('NATIVE_NEGATIVE_CONTEXT_INVALIDATION_UNKNOWN')
            finally:self._busy=False
