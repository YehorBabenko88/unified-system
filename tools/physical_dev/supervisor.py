"""Test-only own process-family custody; no worker, quota or execution authority.

Import and contract helpers perform no native calls. WindowsSmokeJob is used only
by Root after exact source/package/isolation review. Unknown ancestors may be
stricter. Configured COMMIT/USER-CPU ceilings are not RSS, CPU-rate, reservation,
hard real-time, loaded-DLL custody or native resource qualification.
"""
import ctypes as c
import hashlib,json,math,os,re,subprocess,time,threading
from pathlib import Path

D=c.c_uint32;U=c.c_uint64;P=c.c_void_p;S=c.c_size_t;L=c.c_int64
class BasicLimits(c.Structure):
    _fields_=[('process_time',L),('job_time',L),('flags',D),('minimum_ws',S),('maximum_ws',S),('active',D),('affinity',S),('priority',D),('scheduling',D)]
class IO(c.Structure):
    _fields_=[(n,U) for n in ('reads','writes','other','read_bytes','write_bytes','other_bytes')]
class ExtendedLimits(c.Structure):
    _fields_=[('basic',BasicLimits),('io',IO),('process_memory',S),('job_memory',S),('peak_process_memory',S),('peak_job_memory',S)]
class Accounting(c.Structure):
    _fields_=[('user',L),('kernel',L),('period_user',L),('period_kernel',L),('page_faults',D),('total',D),('active',D),('terminated',D)]
class EndAction(c.Structure):_fields_=[('action',D)]
class FileTime(c.Structure):_fields_=[('low',D),('high',D)]

class SmokeBlocked(RuntimeError):pass

def _need(value,code):
    if not value:raise SmokeBlocked(code)

def limit_blueprint():
    return dict(flags=0x230c,active=16,process_commit=536870912,job_commit=1073741824,user_time_100ns=100000000,end_action=0)

def validate_readback(value):
    expected=limit_blueprint();_need(type(value) is dict and set(value)==set(expected),'LIMIT_READBACK_SHAPE')
    _need(all(type(value[k]) is int and value[k]==v for k,v in expected.items()),'LIMIT_READBACK_MISMATCH')

def _pairs(pairs):
    result={}
    for k,v in pairs:
        _need(k not in result,'DUPLICATE_BOOTSTRAP_FIELD');result[k]=v
    return result

def validate_bootstrap(raw,pid,nonce):
    _need(type(raw) is bytes and 0<len(raw)<=256,'BOOTSTRAP_BOUND')
    _need(type(pid) is int and pid>0 and type(nonce) is str and re.fullmatch('[0-9a-f]{32}',nonce),'EXPECTED_OWN_IDENTITY')
    try:value=json.loads(raw.decode('ascii'),object_pairs_hook=_pairs)
    except (ValueError,UnicodeError):raise SmokeBlocked('BOOTSTRAP_JSON') from None
    _need(type(value) is dict and set(value)=={'pid','nonce'},'BOOTSTRAP_SHAPE')
    _need(type(value['pid']) is int and value['pid']==pid and type(value['nonce']) is str and value['nonce']==nonce,'BOOTSTRAP_OWN_IDENTITY_JOIN')

def child_environment(run_root):
    root=Path(run_root);_need(root.is_absolute() and root==root.resolve(strict=True) and root.is_dir(),'OWN_CANONICAL_RUN_ROOT')
    system=os.environ.get('SystemRoot','C:\\Windows');value=str(root)
    return {'SystemRoot':system,'WINDIR':system,'PATH':str(Path(system)/'System32'),'PATHEXT':'.EXE;.COM',
        'TEMP':value,'TMP':value,'TMPDIR':value,'HOME':value,'USERPROFILE':value,'LOCALAPPDATA':value,'APPDATA':value,
        'PYTHONDONTWRITEBYTECODE':'1','GIT_OPTIONAL_LOCKS':'0','GIT_NO_REPLACE_OBJECTS':'1',
        'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'NUL','GIT_NO_LAZY_FETCH':'1','GIT_ALLOW_PROTOCOL':'','GIT_TERMINAL_PROMPT':'0'}

def stop_reason(start_ns,now_ns,output_bytes):
    _need(all(type(v) is int and v>=0 for v in (start_ns,now_ns,output_bytes)) and now_ns>=start_ns,'WATCHDOG_COUNTER_UNKNOWN')
    if output_bytes>16384:return 'OUTPUT_BOUND'
    if now_ns-start_ns>=20000000000:return 'WORK_DEADLINE'
    return None

def cleanup_summary(active,exit_codes):
    _need(type(active) is int and active==0 and type(exit_codes) is list and exit_codes,'OWN_CLEANUP_UNCONFIRMED')
    _need(all(type(code) is int and code==0 for code in exit_codes),'OWN_EXIT_FAILED_OR_UNKNOWN')
    return dict(status='OWN_FAMILY_RETIRED',runtime_admission=False,physical_cluster_admission=False,
        resource_qualification='NOT_GRANTED',native_job_permission=False)

class OwnWatchdog:
    """Supervisor thread, outside the target family, no PID-based operations.

    This is a monotonic cooperative supervisor deadline, not hard real-time or
    protection against a frozen supervisor/OS. Never closes a possibly reused
    handle: the owning controller keeps the Job alive until this thread joins.
    """
    def __init__(self,job,started):
        self.job=job;self.started=started;self.stop=threading.Event();self.expired=threading.Event();self.error=None
        self.thread=threading.Thread(target=self._run,name='own-job-watchdog',daemon=True)
    def _run(self):
        remaining=max(0,(self.started+20000000000-time.perf_counter_ns())/1000000000)
        if self.stop.wait(remaining):return
        self.expired.set()
        try:self.job.terminate_own()
        except BaseException as error:self.error=type(error).__name__
    def start(self):self.thread.start()
    def finish(self,timeout=1):
        _need(type(timeout) in (int,float) and math.isfinite(timeout) and 0<=timeout<=1,'WATCHDOG_JOIN_BUDGET')
        self.stop.set();self.thread.join(timeout)
        _need(not self.thread.is_alive(),'OWN_WATCHDOG_NOT_RETIRED')
        _need(not self.expired.is_set() and self.error is None,'OWN_WATCHDOG_EXPIRED_OR_FAILED')

class WindowsAPI:
    """Fixed platform calls, no injected provider or PID-based process reopen."""
    def __init__(self):
        _need(os.name=='nt' and c.sizeof(P)==8,'WINDOWS_X64_REQUIRED')
        _need((c.sizeof(BasicLimits),c.sizeof(ExtendedLimits),c.sizeof(Accounting),c.sizeof(EndAction))==(64,144,48,4),'WIN32_ABI_UNKNOWN')
        self.k=c.WinDLL('kernel32',use_last_error=True);self.a=c.WinDLL('advapi32',use_last_error=True)
        for name,args,result in [('CreateJobObjectW',[P,c.c_wchar_p],P),('SetInformationJobObject',[P,c.c_int,P,D],c.c_int),
            ('QueryInformationJobObject',[P,c.c_int,P,D,c.POINTER(D)],c.c_int),('AssignProcessToJobObject',[P,P],c.c_int),
            ('IsProcessInJob',[P,P,c.POINTER(c.c_int)],c.c_int),('TerminateJobObject',[P,c.c_uint32],c.c_int),
            ('CloseHandle',[P],c.c_int),('GetCurrentProcess',[],P),('GetProcessId',[P],D),('GetComputerNameW',[c.c_wchar_p,c.POINTER(D)],c.c_int),
            ('QueryFullProcessImageNameW',[P,D,c.c_wchar_p,c.POINTER(D)],c.c_int),
            ('GetProcessTimes',[P,c.POINTER(FileTime),c.POINTER(FileTime),c.POINTER(FileTime),c.POINTER(FileTime)],c.c_int)]:
            function=getattr(self.k,name);function.argtypes=args;function.restype=result
        self.a.OpenProcessToken.argtypes=[P,D,c.POINTER(P)];self.a.OpenProcessToken.restype=c.c_int
        self.a.GetTokenInformation.argtypes=[P,c.c_int,P,D,c.POINTER(D)];self.a.GetTokenInformation.restype=c.c_int
        self.a.CreateWellKnownSid.argtypes=[c.c_int,P,P,c.POINTER(D)];self.a.CreateWellKnownSid.restype=c.c_int
        self.a.GetLengthSid.argtypes=[P];self.a.GetLengthSid.restype=D
    def check(self,result,code):
        if not result:raise SmokeBlocked(code+':'+str(c.get_last_error()))
    def query(self,handle,kind,shape):
        value=shape();size=D();self.check(self.k.QueryInformationJobObject(handle,kind,c.byref(value),c.sizeof(value),c.byref(size)),'JOB_QUERY')
        _need(size.value==c.sizeof(value),'JOB_QUERY_SIZE');return value
    def nonadmin(self,process_handle):
        token=P();self.check(self.a.OpenProcessToken(process_handle,8,c.byref(token)),'TOKEN_QUERY_OPEN');failure=None
        try:
            elevated=D();size=D();self.check(self.a.GetTokenInformation(token,20,c.byref(elevated),4,c.byref(size)),'TOKEN_ELEVATION')
            _need(size.value==4 and elevated.value==0,'ELEVATED_PROCESS_REFUSED')
            elevation_type=D();self.check(self.a.GetTokenInformation(token,18,c.byref(elevation_type),4,c.byref(size)),'TOKEN_ELEVATION_TYPE')
            _need(elevation_type.value in (1,3),'FULL_ADMIN_TOKEN_REFUSED')
            needed=D();self.a.GetTokenInformation(token,2,None,0,c.byref(needed));_need(4<=needed.value<=1048576,'TOKEN_GROUP_BOUND')
            raw=c.create_string_buffer(needed.value);self.check(self.a.GetTokenInformation(token,2,raw,needed.value,c.byref(needed)),'TOKEN_GROUPS')
            class Entry(c.Structure):_fields_=[('sid',P),('attributes',D)]
            class Header(c.Structure):_fields_=[('count',D),('first',Entry)]
            count=c.cast(raw,c.POINTER(D)).contents.value;offset=Header.first.offset
            _need(offset+count*c.sizeof(Entry)<=needed.value,'TOKEN_GROUP_SHAPE')
            admin=c.create_string_buffer(68);admin_size=D(68);self.check(self.a.CreateWellKnownSid(26,None,admin,c.byref(admin_size)),'ADMIN_SID')
            expected=admin.raw[:admin_size.value]
            for index in range(count):
                entry=Entry.from_buffer(raw,offset+index*c.sizeof(Entry));length=self.a.GetLengthSid(entry.sid)
                _need(8<=length<=68,'TOKEN_SID_BOUND')
                if c.string_at(entry.sid,length)==expected:_need(not(entry.attributes&4) or bool(entry.attributes&16),'EFFECTIVE_ADMIN_REFUSED')
            return dict(elevated=False,elevation_type=elevation_type.value,effective_administrator=False)
        except BaseException as error:
            failure=error;raise
        finally:
            try:self.check(self.k.CloseHandle(token),'TOKEN_CLOSE')
            except BaseException as cleanup:
                if failure is None:raise
                failure.add_note('Token cleanup: '+type(cleanup).__name__)
    def process_identity(self,process,expected_image):
        _need(type(process) is subprocess.Popen and os.name=='nt' and process.poll() is None,'LIVE_OWN_DIRECT_POPEN_REQUIRED')
        handle=P(int(process._handle));pid=self.k.GetProcessId(handle);_need(pid==process.pid and pid>0,'RETAINED_PROCESS_PID_MISMATCH')
        image=c.create_unicode_buffer(32768);length=D(len(image));self.check(self.k.QueryFullProcessImageNameW(handle,0,image,c.byref(length)),'PROCESS_IMAGE')
        _need(Path(image.value).resolve(strict=True)==Path(expected_image).resolve(strict=True),'PROCESS_IMAGE_MISMATCH')
        times=[FileTime() for _ in range(4)];self.check(self.k.GetProcessTimes(handle,*[c.byref(v) for v in times]),'PROCESS_CREATION')
        token=self.nonadmin(handle)
        return handle,dict(pid=pid,creation_filetime=(times[0].high<<32)|times[0].low,image_path=image.value,token=token,
            identity_scope='RETAINED_HANDLE_AND_IMAGE_PATH_NOT_LOADED_DLL_ATTESTATION')

class WindowsSmokeJob:
    """NEW anonymous own Job only. Never accepts/opens an existing Job or PID."""
    def __init__(self):
        self.api=WindowsAPI();self.handle=None;self.processes=[];self.closed=False;self.terminated=False
        name=c.create_unicode_buffer(256);size=D(len(name));self.api.check(self.api.k.GetComputerNameW(name,c.byref(size)),'HOST_IDENTITY')
        _need(name.value.upper()=='LS5','LS5_ONLY_PILOT')
        self.parent_token=self.api.nonadmin(self.api.k.GetCurrentProcess())
        try:
            self.handle=self.api.k.CreateJobObjectW(None,None);self.api.check(self.handle,'OWN_JOB_CREATE')
            limits=ExtendedLimits();wanted=limit_blueprint();limits.basic.flags=wanted['flags'];limits.basic.active=wanted['active']
            limits.basic.job_time=wanted['user_time_100ns'];limits.process_memory=wanted['process_commit'];limits.job_memory=wanted['job_commit']
            self.api.check(self.api.k.SetInformationJobObject(self.handle,9,c.byref(limits),c.sizeof(limits)),'OWN_JOB_LIMITS')
            action=EndAction(0);self.api.check(self.api.k.SetInformationJobObject(self.handle,6,c.byref(action),c.sizeof(action)),'OWN_JOB_END_ACTION')
            self.readback=self.read_limits();validate_readback(self.readback)
            _need(self.accounting()['active']==0,'NEW_JOB_NOT_EMPTY')
        except BaseException as error:
            try:self.close()
            except BaseException as cleanup:error.add_note('Own job constructor cleanup: '+type(cleanup).__name__)
            raise
    def _owned(self):_need(self.handle is not None and not self.closed,'OWN_JOB_CLOSED')
    def read_limits(self):
        self._owned();v=self.api.query(self.handle,9,ExtendedLimits);e=self.api.query(self.handle,6,EndAction)
        return dict(flags=v.basic.flags,active=v.basic.active,process_commit=v.process_memory,job_commit=v.job_memory,user_time_100ns=v.basic.job_time,end_action=e.action)
    def accounting(self):
        self._owned();v=self.api.query(self.handle,1,Accounting);m=self.api.query(self.handle,9,ExtendedLimits)
        return dict(active=v.active,total=v.total,terminated=v.terminated,user_100ns=v.user,kernel_100ns=v.kernel,
            peak_commit_process=m.peak_process_memory,peak_commit_job=m.peak_job_memory,
            scope='OBSERVED_OWN_JOB_COUNTERS_NOT_RESOURCE_OR_RSS_QUALIFICATION')
    def attach_before_go(self,process,expected_image):
        self._owned();handle,identity=self.api.process_identity(process,expected_image)
        self.api.check(self.api.k.AssignProcessToJobObject(self.handle,handle),'OWN_JOB_ASSIGN')
        member=c.c_int();self.api.check(self.api.k.IsProcessInJob(handle,self.handle,c.byref(member)),'OWN_MEMBERSHIP_QUERY');_need(member.value==1,'OWN_MEMBERSHIP_MISSING')
        validate_readback(self.read_limits());self.processes.append(process)
        return identity
    def terminate_own(self):
        self._owned();self.api.check(self.api.k.TerminateJobObject(self.handle,73),'OWN_JOB_TERMINATE');self.terminated=True
    def wait_empty(self,seconds=10):
        self._owned();_need(type(seconds) in (int,float) and math.isfinite(seconds) and 0<seconds<=10,'CLEANUP_BUDGET');deadline=time.perf_counter()+seconds
        while True:
            value=self.accounting()
            if value['active']==0:return value
            if time.perf_counter()>=deadline:raise SmokeBlocked('OWN_FAMILY_NOT_RETIRED')
            time.sleep(.05)
    def close(self):
        if self.closed:return
        handle=self.handle
        if handle is not None:self.api.check(self.api.k.CloseHandle(handle),'OWN_JOB_CLOSE')
        self.closed=True;self.handle=None
        # Popen exclusively owns its process handles. Do not raw-CloseHandle them.
    def __enter__(self):self._owned();return self
    def __exit__(self,kind,error,traceback):
        try:self.close()
        except BaseException as cleanup:
            if error is None:raise
            error.add_note('Own job close: '+type(cleanup).__name__)
        return False
