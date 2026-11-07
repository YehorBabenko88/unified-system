"""Windows owned-pipe peer capture: observation, never authentication/grant.

Native impersonation is permitted only in an explicitly registered isolated
sterile child host. Production host admission is intentionally unavailable.
"""
import ctypes as c
from dataclasses import dataclass, field
import multiprocessing as mp
import os
import sys
import threading
import time

SUPPORTED=sys.platform=='win32' and c.sizeof(c.c_void_p)==8
_U32=c.c_uint32
_I32=c.c_int32
_HANDLE=c.c_void_p
_BUF=65536
_HOST=None
_API=None
_SLOTS=threading.BoundedSemaphore(16)
_PROCESS_SLOTS=threading.BoundedSemaphore(16)


class NativeCaptureError(RuntimeError):
    def __init__(self,code):self.code=code;super().__init__(code)


def _need(ok,code):
    if not ok:raise NativeCaptureError(code)


class _LUID(c.Structure):_fields_=[('low',_U32),('high',_I32)]
class _FT(c.Structure):_fields_=[('low',_U32),('high',_U32)]
class _STATS(c.Structure):
    _fields_=[('token',_LUID),('auth',_LUID),('expiry',c.c_int64),('type',_U32),('level',_U32),
              ('charged',_U32),('available',_U32),('groups',_U32),('privileges',_U32),('modified',_LUID)]


class _Win32:
    def __init__(self):
        _need(SUPPORTED,'WINDOWS_X64_REQUIRED')
        self.k=c.WinDLL('kernel32',use_last_error=True);self.a=c.WinDLL('advapi32',use_last_error=True)
        def bind(d,name,restype,*args):
            f=getattr(d,name);f.restype=restype;f.argtypes=list(args);setattr(self,name,f)
        P=c.POINTER;B=c.c_int32
        for name in ('GetCurrentProcess','GetCurrentThread'):bind(self.k,name,_HANDLE)
        for name in ('GetCurrentProcessId','GetCurrentThreadId'):bind(self.k,name,_U32)
        bind(self.k,'CloseHandle',B,_HANDLE)
        bind(self.k,'GetFileType',_U32,_HANDLE)
        bind(self.k,'GetProcessId',_U32,_HANDLE)
        bind(self.k,'GetProcessTimes',B,_HANDLE,P(_FT),P(_FT),P(_FT),P(_FT))
        bind(self.k,'WaitForSingleObject',_U32,_HANDLE,_U32)
        bind(self.k,'DuplicateHandle',B,_HANDLE,_HANDLE,_HANDLE,P(_HANDLE),_U32,B,_U32)
        for name in ('GetNamedPipeClientProcessId','GetNamedPipeServerProcessId','GetNamedPipeClientSessionId'):
            bind(self.k,name,B,_HANDLE,P(_U32))
        bind(self.k,'GetNamedPipeInfo',B,_HANDLE,P(_U32),P(_U32),P(_U32),P(_U32))
        bind(self.k,'LocalFree',_HANDLE,_HANDLE)
        bind(self.k,'TerminateProcess',B,_HANDLE,_U32)
        bind(self.a,'OpenProcessToken',B,_HANDLE,_U32,P(_HANDLE))
        bind(self.a,'OpenThreadToken',B,_HANDLE,_U32,B,P(_HANDLE))
        bind(self.a,'GetTokenInformation',B,_HANDLE,c.c_int,_HANDLE,_U32,P(_U32))
        bind(self.a,'ImpersonateNamedPipeClient',B,_HANDLE)
        bind(self.a,'RevertToSelf',B)
        bind(self.a,'IsValidSid',B,_HANDLE)
        bind(self.a,'GetLengthSid',_U32,_HANDLE)
        bind(self.a,'ConvertSidToStringSidW',B,_HANDLE,P(c.c_void_p))


def _api():
    global _API
    if _API is None:_API=_Win32()
    return _API


def _register_isolated_sterile_host():
    """Private fixture bootstrap, not a production launcher/admission proof."""
    global _HOST
    parent=mp.parent_process()
    _need(parent is not None and parent.is_alive() and mp.current_process().name=='UnifiedNativePeerCaptureHost','STERILE_HOST_REQUIRED')
    api=_api()
    _HOST=(os.getpid(),parent,threading.get_native_id())
    return api


def _require_sterile_host():
    _need(_HOST is not None and _HOST[0]==os.getpid() and _HOST[1].is_alive(),'STERILE_HOST_REQUIRED')


def capture_runtime_peer(*args,**kwargs):
    raise NativeCaptureError('ROOT_PRODUCTION_HOST_ADMISSION_REQUIRED')


def _close(handle):
    if handle:_need(_api().CloseHandle(handle)!=0,'OWN_HANDLE_CLOSE_FAILED')


def _process_identity(handle):
    api=_api();pid=api.GetProcessId(handle);created=_FT();exit_time=_FT();kernel=_FT();user=_FT()
    _need(pid>0 and api.WaitForSingleObject(handle,0)==258,'PROCESS_NOT_LIVE')
    _need(api.GetProcessTimes(handle,c.byref(created),c.byref(exit_time),c.byref(kernel),c.byref(user))!=0,'PROCESS_TIMES_UNAVAILABLE')
    return int(pid),(int(created.high)<<32)|int(created.low)


def _duplicate_process(handle):
    _need(type(handle) is int and handle>0,'OWN_PROCESS_HANDLE_REQUIRED')
    api=_api();result=_HANDLE();me=api.GetCurrentProcess()
    _need(api.DuplicateHandle(me,handle,me,c.byref(result),0x1000|0x100000,False,0)!=0,'PROCESS_DUPLICATE_DENIED')
    return int(result.value)


class OwnedProcessInstance:
    def __init__(self):raise NativeCaptureError('PRIVATE_NATIVE_ADOPTION_ONLY')

    @classmethod
    def _from_created_process_handle(cls,handle):
        """Root launcher only: source handle MUST have been retained at launch."""
        _require_sterile_host();_need(_PROCESS_SLOTS.acquire(False),'PROCESS_RESOURCE_LIMIT')
        dup=None
        try:
            dup=_duplicate_process(handle);identity=_process_identity(dup)
            obj=object.__new__(cls);obj._handle=dup;obj._identity=identity;obj._closed=False
            obj._lock=threading.Lock();return obj
        except BaseException:
            if dup:_close(dup)
            _PROCESS_SLOTS.release();raise

    def close(self):
        with self._lock:
            if not self._closed:
                self._closed=True;_close(self._handle);_PROCESS_SLOTS.release()

    def __reduce_ex__(self,protocol):raise TypeError('NATIVE_RESOURCE_NOT_SERIALIZABLE')


class OwnedPipeReadLease:
    def __init__(self):raise NativeCaptureError('PRIVATE_NATIVE_ADOPTION_ONLY')

    @classmethod
    def _after_completed_read(cls,handle,*,generation,read_lock):
        """Root rawfront only, after actual bounded ReadFile completion.

        Root owns creation/DACL/remote rejection and actual frame generation.
        The lease borrows this server handle, exclusively, until close.
        """
        _require_sterile_host()
        _need(type(handle) is int and handle>0 and type(generation) is int and 1<=generation<2**63,'OWN_PIPE_READ_REQUIRED')
        _need(type(read_lock) is type(threading.Lock()),'OWN_READ_LOCK_REQUIRED')
        _need(read_lock.acquire(False),'PIPE_READ_LEASE_BUSY')
        try:
            obj=object.__new__(cls);obj._handle=handle;obj._generation=generation;obj._lock=read_lock;obj._closed=False
            obj._consumed=False;obj._claim_lock=threading.Lock()
            _pipe_identity(obj);return obj
        except BaseException:read_lock.release();raise

    def close(self):
        if not self._closed:self._closed=True;self._lock.release()

    def __reduce_ex__(self,protocol):raise TypeError('NATIVE_RESOURCE_NOT_SERIALIZABLE')


def _pipe_identity(lease):
    _need(type(lease) is OwnedPipeReadLease and not lease._closed,'PIPE_LEASE_CLOSED')
    api=_api();flags=_U32();server=_U32();client=_U32();session=_U32()
    _need(api.GetFileType(lease._handle)==3,'PIPE_HANDLE_REQUIRED')
    _need(api.GetNamedPipeInfo(lease._handle,c.byref(flags),None,None,None)!=0 and flags.value&1,'PIPE_SERVER_END_REQUIRED')
    _need(api.GetNamedPipeServerProcessId(lease._handle,c.byref(server))!=0 and server.value==os.getpid(),'PIPE_NOT_OWNED_BY_CAPTURE_HOST')
    _need(api.GetNamedPipeClientProcessId(lease._handle,c.byref(client))!=0 and client.value>0,'PIPE_CLIENT_UNAVAILABLE')
    _need(api.GetNamedPipeClientSessionId(lease._handle,c.byref(session))!=0,'PIPE_SESSION_UNAVAILABLE')
    return int(client.value),int(session.value),lease._generation


class _RawToken:
    def __init__(self):
        self.sid=(c.c_ubyte*68)();self.sid_length=0;self.stats=_STATS();self.session=_U32()


def _query(token,kind,buffer):
    needed=_U32()
    _need(_api().GetTokenInformation(token,kind,buffer,_BUF,c.byref(needed))!=0 and 0<needed.value<=_BUF,'TOKEN_QUERY_REJECTED')
    return int(needed.value)


def _read_raw_token(token,buffer,target):
    """No textual conversion/logging/callback/I/O. Buffers preallocated."""
    api=_api();size=_query(token,1,buffer);ptr=c.cast(buffer,c.POINTER(_HANDLE))[0]
    begin=c.addressof(buffer)
    _need(ptr is not None and begin<=ptr and ptr+8<=begin+size,'TOKEN_SID_POINTER')
    _need(api.IsValidSid(ptr)!=0,'TOKEN_SID_INVALID');length=int(api.GetLengthSid(ptr))
    _need(8<=length<=68 and ptr+length<=begin+size,'TOKEN_SID_BOUNDS')
    c.memmove(target.sid,ptr,length);target.sid_length=length
    _need(_query(token,10,buffer)>=c.sizeof(_STATS),'TOKEN_STATS_BOUNDS')
    c.memmove(c.byref(target.stats),buffer,c.sizeof(_STATS))
    _need(_query(token,12,buffer)==4,'TOKEN_SESSION_BOUNDS');c.memmove(c.byref(target.session),buffer,4)


def _materialize(raw):
    api=_api();text=c.c_void_p()
    _need(api.ConvertSidToStringSidW(raw.sid,c.byref(text))!=0,'SID_STRING_REJECTED')
    try:sid=c.wstring_at(text)
    finally:api.LocalFree(text)
    _need(len(sid)<=184,'SID_TEXT_BOUNDS')
    luid=f'{raw.stats.auth.high & 0xffffffff:08x}{raw.stats.auth.low:08x}'
    return sid,luid,int(raw.session.value)


def _thread_has_token():
    api=_api();token=_HANDLE()
    if api.OpenThreadToken(api.GetCurrentThread(),8,True,c.byref(token)):
        _close(token.value);return True
    _need(c.get_last_error()==1008,'THREAD_TOKEN_STATE_UNAVAILABLE')
    return False


def _failfast_own_host():
    # No return/logging/callback under an un-restored identity. Host is an own
    # dedicated child; never run capture in controller or an existing service.
    _api().TerminateProcess(_api().GetCurrentProcess(),0xE0420001)
    os._exit(73)


@dataclass(frozen=True)
class PeerObservation:
    process_id: int
    process_creation_100ns: int
    session_id: int
    impersonation_level: int
    sid: str=field(repr=False)
    authentication_luid: str=field(repr=False)
    qualification: str='ISOLATED_NATIVE_OBSERVATION_NOT_ADMISSION'


class NativePeerCapture:
    @property
    def observation(self):return self._observation

    def __init__(self):raise NativeCaptureError('PRIVATE_NATIVE_CAPTURE_ONLY')

    def check_current(self):
        _require_sterile_host();_need(not self._closed,'CAPTURE_CLOSED')
        _need(not self._expected._closed,'EXPECTED_PROCESS_CLOSED')
        _need(_process_identity(self._process)==self._process_identity_expected,'PROCESS_INSTANCE_CHANGED')
        _need(_pipe_identity(self._pipe)==self._pipe_identity_expected,'PIPE_INSTANCE_CHANGED')
        return self.observation

    def close(self):
        if not self._closed:
            self._closed=True
            try:_close(self._process)
            finally:self._pipe.close()
            _SLOTS.release()

    def __enter__(self):self.check_current();return self
    def __exit__(self,*args):self.close()
    def __reduce_ex__(self,protocol):raise TypeError('NATIVE_CAPTURE_NOT_SERIALIZABLE')


def capture_owned_pipe_peer(pipe_read,expected_process,*,deadline_ns,cancel=None):
    _need(type(pipe_read) is OwnedPipeReadLease and type(expected_process) is OwnedProcessInstance,'OWNED_NATIVE_RESOURCES_REQUIRED')
    _require_sterile_host()
    _need(type(deadline_ns) is int and deadline_ns>time.monotonic_ns(),'CAPTURE_DEADLINE')
    _need(cancel is None or type(cancel) is threading.Event,'CANCEL_EVENT_REQUIRED')
    if cancel is not None and cancel.is_set():raise NativeCaptureError('CAPTURE_CANCELLED')
    _need(not pipe_read._closed and not expected_process._closed,'NATIVE_RESOURCE_CLOSED')
    with pipe_read._claim_lock:
        _need(not pipe_read._closed,'PIPE_LEASE_CLOSED')
        _need(not pipe_read._consumed,'PIPE_READ_LEASE_CONSUMED')
        _need(_SLOTS.acquire(False),'CAPTURE_RESOURCE_LIMIT')
        pipe_read._consumed=True
    api=_api();process=None;primary=_HANDLE();thread_token=_HANDLE();success=False
    try:
        _need(not _thread_has_token(),'SERVER_ALREADY_IMPERSONATING')
        pipe_identity=_pipe_identity(pipe_read)
        with expected_process._lock:
            _need(not expected_process._closed,'EXPECTED_PROCESS_CLOSED')
            process=_duplicate_process(expected_process._handle)
        identity=_process_identity(process)
        _need(identity==expected_process._identity and identity[0]==pipe_identity[0],'CLIENT_PROCESS_INSTANCE_MISMATCH')
        # Allocate all critical storage before impersonation. Python implicit GC
        # and audit hooks are NOT claimed absent; only sterile own host may run.
        buffer=c.create_string_buffer(_BUF);a=_RawToken();b=_RawToken()
        _need(api.OpenProcessToken(process,8,c.byref(primary))!=0,'PRIMARY_TOKEN_UNAVAILABLE')
        try:_read_raw_token(primary.value,buffer,a)
        finally:_close(primary.value);primary.value=None
        _need(time.monotonic_ns()<deadline_ns,'CAPTURE_DEADLINE')
        if cancel is not None and cancel.is_set():raise NativeCaptureError('CAPTURE_CANCELLED')
        try:
            # Enter finally BEFORE the native transition: even an FFI/audit
            # exception after a successful transition must never escape it.
            _need(api.ImpersonateNamedPipeClient(pipe_read._handle)!=0,'IMPERSONATION_REJECTED')
            _need(api.OpenThreadToken(api.GetCurrentThread(),8,True,c.byref(thread_token))!=0,'CLIENT_TOKEN_UNAVAILABLE')
            _read_raw_token(thread_token.value,buffer,b)
        finally:
            # Revert precedes conversion, caller return or cleanup error reporting.
            try:restored=api.RevertToSelf()
            except BaseException:_failfast_own_host()
            if not restored:_failfast_own_host()
            try:
                if _thread_has_token():_failfast_own_host()
            except BaseException:_failfast_own_host()
            if thread_token.value:_close(thread_token.value);thread_token.value=None
        _need(b.stats.type==2 and b.stats.level==1,'IDENTIFICATION_LEVEL_REQUIRED')
        pa=_materialize(a);pb=_materialize(b)
        _need(pa==pb and pb[2]==pipe_identity[1],'DIRECT_PEER_TOKEN_MISMATCH')
        _need(_process_identity(process)==identity and _pipe_identity(pipe_read)==pipe_identity,'PEER_CHANGED_DURING_CAPTURE')
        _need(time.monotonic_ns()<deadline_ns,'CAPTURE_DEADLINE')
        if cancel is not None and cancel.is_set():raise NativeCaptureError('CAPTURE_CANCELLED')
        capture=object.__new__(NativePeerCapture);capture._closed=False;capture._process=process
        capture._expected=expected_process;capture._pipe=pipe_read;capture._process_identity_expected=identity;capture._pipe_identity_expected=pipe_identity
        capture._observation=PeerObservation(identity[0],identity[1],pb[2],1,pb[0],pb[1])
        success=True;return capture
    finally:
        if primary.value:_close(primary.value)
        if thread_token.value:_close(thread_token.value)
        if not success:
            closed_ok=process is None
            try:
                if process:_close(process)
                closed_ok=True
            finally:
                pipe_read.close()
                if closed_ok:_SLOTS.release()
