"""One disposable developer PG process family, NOT a service or DB authority.

No native initialization at import. Native use requires an external Root lease,
reviewed A4 SQL/auth pins, and canonical admitted helper/runtime source.
"""
from dataclasses import dataclass
import hashlib
import math
import os
from pathlib import Path, PureWindowsPath
import threading
import time

# Documented Win32 flag; CPython3.12 does not export CREATE_SUSPENDED.
# https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags
_CREATE_SUSPENDED=0x00000004
CAP=262144
INSTALL=PureWindowsPath('C:/Program Files/PostgreSQL/18')
LEDGER_SHA='0631d79759b3f056e4e573b042beb2fcd4e763a28967127b7d129623a33d6b45'
JOB_SHA='7fd6223de3e28052b1254fa9e33e638132c6db89388bbb2d994b35970802a25c'
LIMITS={'active_processes':32,'job_memory_bytes':1073741824,'process_memory_bytes':536870912,'job_user_seconds':60,'kill_on_close':True,'breakaway':False}
CAPS={'initdb':60.,'server':15.,'psql':30.,'stop':10.}
SQL_NAMES=('bootstrap','migrate','verify','readback')

def need(value,code='PG_CUSTODY_DENIED'):
    if value is not True:raise ValueError(code)

@dataclass(frozen=True)
class Plan:
    root:str
    native:bool=False
    sql_pins:tuple=()
    @classmethod
    def model(cls):return cls(r'C:\INERT\UnifiedCollectorTest\pg-attempt1')

@dataclass(frozen=True)
class Command:
    role:str
    argv:tuple
    sql_name:str|None=None

def command_for(plan,role,sql_name='migrate'):
    root=PureWindowsPath(plan.root);need(root.is_absolute() and '..' not in root.parts)
    exe=str(INSTALL/'bin'/({'initdb':'initdb.exe','server':'postgres.exe','psql':'psql.exe','stop':'pg_ctl.exe'}.get(role,'')))
    cluster=str(root/'cluster')
    if role=='initdb':args=('--pgdata',cluster,'--username','unified_bootstrap_collector_c0c2','--encoding','UTF8','--no-locale','--auth-local','scram-sha-256','--auth-host','scram-sha-256','--pwfile',str(root/'secrets/bootstrap-password'),'--data-checksums','--no-clean','--no-instructions')
    elif role=='server':
        settings=('listen_addresses=127.0.0.1','unix_socket_directories=','max_connections=8','shared_buffers=16MB','work_mem=1MB','maintenance_work_mem=16MB','temp_file_limit=16MB','max_wal_size=128MB','min_wal_size=32MB','fsync=on','full_page_writes=on','synchronous_commit=on','logging_collector=off','log_destination=stderr','log_statement=none','log_min_error_statement=panic','shared_preload_libraries=','session_preload_libraries=','local_preload_libraries=','archive_mode=off','archive_command=','restore_command=')
        args=('-D',cluster,'-h','127.0.0.1','-p','55483')+tuple(x for item in settings for x in ('-c',item))
    elif role=='psql':
        need(sql_name in SQL_NAMES)
        user='unified_bootstrap_collector_c0c2' if sql_name=='bootstrap' else 'unified_lab_collector_app'
        db='postgres' if sql_name=='bootstrap' else 'unified_lab_collector_c0c2'
        args=('-X','--no-password','--set=ON_ERROR_STOP=1','--host=127.0.0.1','--port=55483','--username='+user,'--dbname='+db,'--file='+str(root/'sql'/(sql_name+'.sql')))
    elif role=='stop':args=('stop','-D',cluster,'-m','fast','-w','-t','10')
    else:raise ValueError('CLOSED_PG_ROLE_REQUIRED')
    return Command(role,(exe,)+args,sql_name if role=='psql' else None)

class Capture:
    def __init__(self):self.lock=threading.Lock();self.parts=[bytearray(),bytearray()];self.total=0;self.failed=False;self.reader_errors=[]
    def feed(self,which,raw):
        with self.lock:
            if type(raw) is not bytes:self.failed=True;return
            room=max(0,CAP-self.total);self.total+=len(raw);self.parts[which].extend(raw[:room])
            if self.total>CAP:self.failed=True
    def reader_error(self):
        with self.lock:self.failed=True;self.reader_errors.append('PIPE_READER_FAILURE')
    def private_bytes(self):
        with self.lock:return tuple(bytes(x) for x in self.parts)

class CustodyDenied(RuntimeError):
    def __init__(self,receipt):self.receipt=receipt;super().__init__('PG_QUALIFICATION_DENIED')

class PgCustodian:
    """Fixed serial phase transport; no retries, autonomous restart or DB verdict."""
    def __init__(self,plan,backend,*,clock=time.monotonic):
        self.plan=plan;self.backend=backend;self.clock=clock;self.start=self._now();self.end=self.start+180.
        self.records=[];self.job=None;self.capture=Capture();self.errors=[];self.error_total=0;self.closed=False;self.family_retired=False;self.readers_retired=False
        self.server=None;self.server_starts=0;self.confirmed_stops=0;self.sql_count=0;self.init_done=False;self.backend.admit(plan)
    def _now(self):
        n=self.clock();need(type(n) in (int,float) and math.isfinite(n));return n
    def _error(self,code,error=None):
        self.error_total+=1
        if len(self.errors)<64:self.errors.append({'code':code,'error_type':None if error is None else type(error).__name__[:64]})
    def _remaining(self,end):
        try:return max(0.,end-self._now())
        except BaseException as e:self._error('CLOCK_UNCERTAIN',e);return 0.
    def _healthy(self):need(not self.closed and not self.errors and not self.capture.failed and self._now()<self.end-20.)
    def _launch(self,command,phase_end):
        need(command==command_for(self.plan,command.role,command.sql_name or 'migrate'))
        need(len(self.records)<16);self.backend.before_command(command);need(self._now()<=phase_end)
        entry={'role':command.role,'process':None,'job':None,'readers':[],'waited':False,'resumed':False,'creation_unknown':True}
        self.records.append(entry)  # Reserve BEFORE constructors/native creation.
        self.backend.create_suspended(entry,command);need(entry['process'] is not None);entry['creation_unknown']=False
        self.job=self.backend.attach(entry,self.job)
        need(self.backend.configure_and_readback(self.job)==LIMITS)
        need(self.backend.member(entry,self.job) is True)
        for which in (0,1):
            owner={'which':which,'reader':None,'attempted':False,'safe':False};entry['readers'].append(owner)
            owner['reader']=self.backend.reader(entry,which,self.capture);owner['attempted']=True
            owner['reader'].start()
        self._healthy();need(self._now()<=phase_end);entry['resume_attempted']=True;self.backend.resume(entry);entry['resumed']=True
        return entry
    def _join(self,entry,end):
        safe=len(entry['readers'])==2
        for owner in entry['readers']:
            reader=owner['reader'];joined=False
            if reader is not None and owner['attempted']:
                try:reader.join(timeout=self._remaining(end));joined=True
                except BaseException as e:self._error('READER_JOIN_UNCERTAIN',e)
                try:owner['safe']=joined and reader.ident is not None and reader.is_alive() is False
                except BaseException as e:self._error('READER_STATE_UNCERTAIN',e)
            if not owner['safe']:safe=False
        if safe:
            for which in (0,1):
                try:self.backend.close_pipe(entry,which)
                except BaseException as e:self._error('PIPE_CLOSE_UNCERTAIN',e)
        else:self._error('READERS_NOT_RETIRED')
        return safe
    def _wait(self,entry,end):
        code=self.backend.wait(entry,self._remaining(end));entry['waited']=True;need(code==0)
        need(self._join(entry,end));need(not self.capture.failed)
    def run(self,command):
        try:
            self._healthy();need(command.role!='server')
            if command.role=='initdb':need(not self.init_done and self.server is None)
            else:need(self.server is not None)
            phase_end=min(self.end-20.,self._now()+CAPS[command.role])
            entry=self._launch(command,phase_end)
            while self.backend.poll(entry) is None:
                self._healthy();need(self._now()<phase_end);self.backend.sleep(min(.01,self._remaining(phase_end)))
            need(self._now()<=phase_end);self._wait(entry,phase_end);need(self._now()<=phase_end)
            if command.role=='initdb':need(self.backend.active(self.job)==0);self.init_done=True
            if command.role=='psql':self.sql_count+=1
            if command.role=='stop':
                self._wait(self.server,phase_end);need(self.backend.active(self.job)==0);self.server=None;self.confirmed_stops+=1
            return self.snapshot()
        except BaseException as e:
            self._error('PRIMARY_FAILURE',e);self.close();raise CustodyDenied(self.snapshot()) from None
    def start_server(self):
        try:
            self._healthy();need(self.init_done and self.server is None and self.server_starts<2)
            phase_end=min(self.end-20.,self._now()+15.)
            self.server=self._launch(command_for(self.plan,'server'),phase_end);self.server_starts+=1
            need(self.backend.poll(self.server) is None)
            return self.snapshot()  # Spawn/live is NOT readiness.
        except BaseException as e:
            self._error('PRIMARY_FAILURE',e);self.close();raise CustodyDenied(self.snapshot()) from None
    def wait_server_ready(self):
        try:
            self._healthy();need(self.server is not None);end=min(self.end-20.,self._now()+15.)
            while self.backend.server_ready(self.server,self.job) is not True:
                self._healthy();need(self._now()<end and self.backend.poll(self.server) is None);self.backend.sleep(min(.01,self._remaining(end)))
            need(self._now()<=end);return self.snapshot()
        except BaseException as e:
            self._error('PRIMARY_FAILURE',e);self.close();raise CustodyDenied(self.snapshot()) from None
    def close(self):
        if self.closed:return self.snapshot()
        self.closed=True
        try:cleanup_end=min(self.end,self._now()+20.)
        except BaseException as e:self._error('CLOCK_UNCERTAIN',e);cleanup_end=self.end
        for entry in self.records:
            if self.job is None and entry['job'] is not None:self.job=entry['job']
        if self.job is not None:
            try:self.family_retired=self.backend.terminate_and_wait(self.job,self._remaining(cleanup_end)) is True
            except BaseException as e:self._error('JOB_RETIREMENT_UNCERTAIN',e)
        elif self.records:self._error('CREATION_OR_JOB_OUTCOME_UNKNOWN')
        else:self.family_retired=True
        reader_states=[]
        for entry in self.records:
            if entry['process'] is None:self.family_retired=False;continue
            kill=True
            try:kill=self.backend.poll(entry) is None
            except BaseException as e:self._error('PRIMARY_POLL_UNCERTAIN',e)
            if kill:
                try:self.backend.kill_primary(entry)
                except BaseException as e:self._error('PRIMARY_KILL_UNCERTAIN',e)
            try:self.backend.wait(entry,self._remaining(cleanup_end));entry['waited']=True
            except BaseException as e:self._error('PRIMARY_WAIT_UNCERTAIN',e)
            reader_states.append(self._join(entry,cleanup_end))
            if entry['waited']:
                try:self.backend.close_primary(entry)
                except BaseException as e:self._error('PRIMARY_HANDLE_CLOSE_UNCERTAIN',e)
        self.readers_retired=all(reader_states) and len(reader_states)==len(self.records)
        if self.capture.failed:self._error('OUTPUT_LIMIT_OR_READER_FAILURE')
        try:self.backend.after()
        except BaseException as e:self._error('POSTCHECK_UNCERTAIN',e)
        try:
            if self._now()>cleanup_end:self._error('CLEANUP_OBSERVED_DEADLINE')
        except BaseException as e:self._error('CLOCK_UNCERTAIN',e)
        return self.snapshot()
    def snapshot(self):
        return {'scope':'OWNED_PG_TOOL_CUSTODY_ONLY','closed':self.closed,'family_retired':self.family_retired,'readers_retired':self.readers_retired,'errors':list(self.errors),'error_overflow':self.error_total-len(self.errors),'server_starts':self.server_starts,'confirmed_stops':self.confirmed_stops,'forced_server_retirement':self.server is not None,'primary_waited_all':all(e['waited'] for e in self.records),'protocol_complete':self.init_done and self.server_starts==self.confirmed_stops and self.server_starts>0 and self.sql_count>0,'output_observed':self.capture.total,'output_retained':sum(map(len,self.capture.private_bytes())),'transport_ok':bool(self.records) and self.closed and self.family_retired and self.readers_retired and not self.errors,'database_qualified':False,'source_roles':[e['role'] for e in self.records]}
    def private_output(self):return self.capture.private_bytes()
    def __enter__(self):return self
    def __exit__(self,*exc):self.close();return False

class _PipeReader:
    def __init__(self,pipe,which,capture):
        self.pipe=pipe;self.capture=capture
        def drain():
            try:
                while True:
                    block=pipe.read(4096)
                    if not block:break
                    capture.feed(which,block)
            except BaseException:capture.reader_error()
            finally:
                try:pipe.close()
                except BaseException:capture.reader_error()
        self.thread=threading.Thread(target=drain,daemon=True)
    @property
    def ident(self):return self.thread.ident
    def start(self):self.thread.start()
    def join(self,timeout):self.thread.join(timeout)
    def is_alive(self):return self.thread.is_alive()

SUPPORT_PINS={'unified_system.service_postgres':('58dc1ca96e57003922499ee6acd2ff49a5fabd27805878473ca45577145d5756',58115),'unified_system.runtime_process':('7cdf208ac44d45dca5c0785719b846d28a52ae7754781450547d8a8ef81da7b2',15974),'unified_system.service_bootstrap':('a8012a04c4a0507a72bd6ba38c63ad0af855d5f25efea7669ea11db1386d8d45',25050)}

def _ordinary(path,file=False):
    import stat
    p=Path(path);need(p.is_absolute() and '..' not in p.parts and not str(p).startswith('\\\\'))
    for q in [*reversed(p.parents),p]:
        s=q.lstat();need(not stat.S_ISLNK(s.st_mode) and not getattr(s,'st_reparse_tag',0) and not getattr(s,'st_file_attributes',0)&1024)
        need(stat.S_ISREG(s.st_mode) and s.st_nlink==1 if file and q==p else stat.S_ISDIR(s.st_mode))
    return s

def _held(path,pin=None,size=None,limit=268435456):
    import stat
    p=Path(path);a=_ordinary(p,True);need(0<=a.st_size<=limit and (size is None or a.st_size==size))
    def common(s):return s.st_dev,s.st_ino,stat.S_IFMT(s.st_mode),s.st_size,s.st_mtime_ns,s.st_nlink,getattr(s,'st_birthtime_ns',None)
    def same(s):return common(s)+(s.st_mode,s.st_ctime_ns)
    with p.open('rb') as f:
        b=os.fstat(f.fileno());need(common(a)==common(b));raw=f.read(a.st_size+1);c=os.fstat(f.fileno())
    z=_ordinary(p,True);need(len(raw)==a.st_size and same(a)==same(z) and same(b)==same(c))
    need(pin is None or hashlib.sha256(raw).hexdigest()==pin);return raw

class WindowsBackend:
    """Thin native adapter over existing Grid Job + Unified resume/identity APIs.

    support_modules must ALREADY be source-admitted file-backed modules by Root;
    this class never imports an ambient Unified/Grid package or service grant.
    Construction/preparation is native work and requires a separate Root lease.
    """
    def __init__(self,plan,support_modules,job_source):
        need(type(plan) is Plan and plan.native is True and os.name=='nt')
        import ctypes,json,types
        self.c=ctypes;self.plan=plan;self.root=Path(plan.root);self.job=None;self.configured=False;self.server=None;self.context_identity=None
        need(set(support_modules)==set(SUPPORT_PINS))
        for name,module in support_modules.items():
            need(type(module) is types.ModuleType and module.__name__==name and module.__spec__ is not None and module.__spec__.origin==module.__file__)
            pin,size=SUPPORT_PINS[name];_held(module.__file__,pin,size)
        self.pg=support_modules['unified_system.service_postgres'];self.runtime=support_modules['unified_system.runtime_process'];self.bootstrap=support_modules['unified_system.service_bootstrap']
        self.kernel,self.w=self.runtime._win_api()
        raw=_held(job_source,JOB_SHA,7044,65536);namespace={'__name__':'_collector_existing_pg_job','__file__':str(job_source)}
        exec(compile(raw,str(job_source),'exec',dont_inherit=True),namespace);self.job_class=namespace['WindowsJob']
        ledger_path=Path('C:/Users/LS-5/.codex/collector-postgres-test-preparation-20261112/INSTALLED-PG18-RAW-INVENTORY-v1.json')
        self.ledger=json.loads(_held(ledger_path,LEDGER_SHA,limit=2097152));need(self.ledger['file_count']==1772 and self.ledger['root']=='C:/Program Files/PostgreSQL/18')
        self.files={str(Path(row['path'])):row for row in self.ledger['files']}
        need(len(self.files)==1772);self.security=self.bootstrap.WindowsActivationKernel();self.secret_root=self.root/'secrets'
        need(len(plan.sql_pins)==4);self.sql={name:(sha,size) for name,sha,size in plan.sql_pins};need(len(self.sql)==4 and set(self.sql)==set(SQL_NAMES))
        for sha,size in self.sql.values():need(type(sha) is str and len(sha)==64 and all(c in '0123456789abcdef' for c in sha) and type(size) is int and 0<size<=262144)
    def _token(self):
        c=self.c;w=self.w;k=self.kernel;a=c.WinDLL('advapi32',use_last_error=True);u=c.WinDLL('userenv',use_last_error=True)
        a.OpenProcessToken.argtypes=[w.HANDLE,w.DWORD,c.POINTER(w.HANDLE)];a.OpenProcessToken.restype=w.BOOL
        a.OpenThreadToken.argtypes=[w.HANDLE,w.DWORD,w.BOOL,c.POINTER(w.HANDLE)];a.OpenThreadToken.restype=w.BOOL
        a.GetTokenInformation.argtypes=[w.HANDLE,c.c_int,c.c_void_p,w.DWORD,c.POINTER(w.DWORD)];a.GetTokenInformation.restype=w.BOOL
        a.CheckTokenMembership.argtypes=[w.HANDLE,c.c_void_p,c.POINTER(w.BOOL)];a.CheckTokenMembership.restype=w.BOOL
        a.ConvertStringSidToSidW.argtypes=[w.LPCWSTR,c.POINTER(c.c_void_p)];a.ConvertStringSidToSidW.restype=w.BOOL
        k.GetCurrentProcess.restype=w.HANDLE;k.GetCurrentThread.restype=w.HANDLE;k.LocalFree.argtypes=[c.c_void_p];k.LocalFree.restype=c.c_void_p
        u.GetUserProfileDirectoryW.argtypes=[w.HANDLE,w.LPWSTR,c.POINTER(w.DWORD)];u.GetUserProfileDirectoryW.restype=w.BOOL
        thread=w.HANDLE()
        if a.OpenThreadToken(k.GetCurrentThread(),8,True,c.byref(thread)):
            try:raise ValueError('IMPERSONATED_DEVELOPER_REFUSED')
            finally:need(bool(k.CloseHandle(thread)))
        need(c.get_last_error()==1008);token=w.HANDLE();need(bool(a.OpenProcessToken(k.GetCurrentProcess(),8,c.byref(token))))
        primary=None
        try:
            elevation=w.DWORD();size=w.DWORD();need(bool(a.GetTokenInformation(token,20,c.byref(elevation),4,c.byref(size))) and size.value==4 and elevation.value==0)
            for text in ('S-1-5-32-544','S-1-5-32-547'):
                pointer=c.c_void_p();need(bool(a.ConvertStringSidToSidW(text,c.byref(pointer))))
                try:member=w.BOOL();need(bool(a.CheckTokenMembership(None,pointer,c.byref(member))) and not member.value)
                finally:need(not k.LocalFree(pointer))
            required=w.DWORD();a.GetTokenInformation(token,1,None,0,c.byref(required));need(0<required.value<=65536)
            buf=c.create_string_buffer(required.value);need(bool(a.GetTokenInformation(token,1,buf,len(buf),c.byref(required))))
            sid=self.security._sid(c.c_void_p.from_buffer(buf).value)
            size=w.DWORD(32768);profile=c.create_unicode_buffer(size.value);need(bool(u.GetUserProfileDirectoryW(token,profile,c.byref(size))))
            return sid,Path(profile.value)
        except BaseException as e:primary=e;raise
        finally:
            if not k.CloseHandle(token):
                if primary is not None:primary.add_note('TOKEN_CLOSE_UNCERTAIN')
                else:raise ValueError('TOKEN_CLOSE_UNCERTAIN')
    def _private(self,path,sid):
        owner,protected,rows=self.security._security(path)
        need(owner in (sid,'S-1-5-18','S-1-5-32-544') and len(rows)==3 and {r[0] for r in rows}=={sid,'S-1-5-18','S-1-5-32-544'})
        need(all(mask==0x1f01ff for _,mask,_ in rows))
    def _seal_inputs(self):
        import stat
        expected_dirs={str(Path(r['path'])) for r in self.ledger['directories']};seen=set();dirs=set()
        def walk(path):
            _ordinary(path);need(str(path) in expected_dirs);dirs.add(str(path))
            for p in path.iterdir():
                s=p.lstat();need(not stat.S_ISLNK(s.st_mode) and not getattr(s,'st_reparse_tag',0) and not getattr(s,'st_file_attributes',0)&1024)
                if stat.S_ISDIR(s.st_mode):walk(p)
                else:
                    need(str(p) in self.files);row=self.files[str(p)];_held(p,row['sha256'],row['bytes']);seen.add(str(p))
        for part in ('bin','lib','share'):walk(Path(INSTALL)/part)
        need(seen==set(self.files) and dirs==expected_dirs)
    def admit(self,plan):
        need(plan is self.plan);sid,profile=self._token();local=profile/'AppData/Local'
        need(self.root==local/'UnifiedCollectorTest/pg-attempt1');_ordinary(local);self._private(local,sid)
        need(not self.root.exists() and not self.root.is_symlink());self._seal_inputs();
        try:self.pg._listener_pid(55483)
        except self.pg.PostgresStartPending:pass
        else:raise ValueError('FIXED_PG_PORT_OCCUPIED')
        self.context_identity=(sid,profile)
        # Only own NEW directories. No ACL writes and no existing cluster adoption.
        parent=self.root.parent
        if not parent.exists():parent.mkdir()
        _ordinary(parent);self._private(parent,sid);self.root.mkdir()
        for name in ('cwd','temp','logs','secrets','sql','results'):(self.root/name).mkdir()
        self._private(self.root,sid);self.root_identity=(_ordinary(self.root).st_dev,_ordinary(self.root).st_ino)
    def before_command(self,command):
        need(command==command_for(self.plan,command.role,command.sql_name or 'migrate'))
        need(self._token()==self.context_identity);need((_ordinary(self.root).st_dev,_ordinary(self.root).st_ino)==self.root_identity)
        row=self.files[str(Path(command.argv[0]))];_held(command.argv[0],row['sha256'],row['bytes'])
        sid=self.context_identity[0];self._private(self.secret_root,sid)
        if command.role=='initdb':
            p=self.secret_root/'bootstrap-password';_ordinary(p,True);self._private(p,sid);need(0<p.stat().st_size<=512)
        if command.role=='psql':
            need(self.server_ready(self.server,self.job),'OWNED_PG_LISTENER_NOT_READY');name=command.sql_name;sha,size=self.sql[name];_held(self.root/'sql'/(name+'.sql'),sha,size,262144)
            p=self.secret_root/'pgpass.conf';_ordinary(p,True);self._private(p,sid);need(0<p.stat().st_size<=4096)
        if command.role=='stop':
            need(self.server is not None and self.poll(self.server) is None and self.member(self.server,self.job))
            lines=_held(self.root/'cluster/postmaster.pid',limit=8192).decode('utf-8').splitlines()
            need(len(lines)>=4 and lines[0]==str(self.server['process'].pid) and Path(lines[1])==self.root/'cluster' and lines[3]=='55483')
    def create_suspended(self,entry,command):
        import subprocess
        env={k:v for k,v in os.environ.items() if k.upper() in ('SYSTEMROOT','WINDIR','COMSPEC')}
        need(all(any(k.upper()==name and v for k,v in env.items()) for name in ('SYSTEMROOT','WINDIR','COMSPEC')))
        env.update(PATH=str(Path(INSTALL/'bin'))+';'+str(Path(env.get('SystemRoot',env.get('SYSTEMROOT','C:/Windows')))/'System32'),TEMP=str(self.root/'temp'),TMP=str(self.root/'temp'),HOME=str(self.root/'cwd'),USERPROFILE=str(self.root/'cwd'),APPDATA=str(self.root/'cwd'))
        if command.role=='psql':env.update(PGPASSFILE=str(self.secret_root/'pgpass.conf'),PGSSLMODE='disable',PGGSSENCMODE='disable',PGCONNECT_TIMEOUT='2')
        proc=subprocess.Popen(list(command.argv),executable=command.argv[0],cwd=self.root/'cwd',env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0,shell=False,close_fds=True,creationflags=_CREATE_SUSPENDED|subprocess.CREATE_NO_WINDOW)
        entry['process']=proc  # Hold immediately; every following action may fail.
        entry['identity']=self.runtime._win_identity(self.kernel,self.w,self.c.c_void_p(int(proc._handle)))
        need(Path(entry['identity'][1])==Path(command.argv[0]));entry['command']=command
        if command.role=='server':self.server=entry
    def attach(self,entry,job):
        proc=entry['process'];need(proc.poll() is None)
        if job is None:
            try:job=self.job_class(proc.pid,resume_primary_thread=False)
            except BaseException:entry['attachment_uncertain']=True;raise
        else:need(bool(job._kernel.AssignProcessToJobObject(job._job,self.c.c_void_p(int(proc._handle)))))
        entry['job']=job;self.job=job;return job
    def configure_and_readback(self,job):
        c=self.c;w=self.w
        class Basic(c.Structure):_fields_=[('process_time',c.c_int64),('job_time',c.c_int64),('flags',w.DWORD),('minimum',c.c_size_t),('maximum',c.c_size_t),('processes',w.DWORD),('affinity',c.c_size_t),('priority',w.DWORD),('scheduling',w.DWORD)]
        class Io(c.Structure):_fields_=[('v'+str(i),c.c_uint64) for i in range(6)]
        class Extended(c.Structure):_fields_=[('basic',Basic),('io',Io),('process_memory',c.c_size_t),('job_memory',c.c_size_t),('peak_process',c.c_size_t),('peak_job',c.c_size_t)]
        flags=0x2000|0x8|0x100|0x200|0x4
        if not self.configured:
            limits=Extended();limits.basic.flags=flags;limits.basic.processes=32;limits.basic.job_time=60*10000000;limits.process_memory=536870912;limits.job_memory=1073741824
            need(bool(job._kernel.SetInformationJobObject(job._job,9,c.byref(limits),c.sizeof(limits))));self.configured=True
        actual=Extended();size=w.DWORD();need(bool(job._kernel.QueryInformationJobObject(job._job,9,c.byref(actual),c.sizeof(actual),c.byref(size))) and size.value==c.sizeof(actual))
        need(actual.basic.flags==flags and actual.basic.processes==32 and actual.basic.job_time==600000000 and actual.process_memory==536870912 and actual.job_memory==1073741824)
        return dict(LIMITS)
    def member(self,entry,job):
        c=self.c;w=self.w;fn=job._kernel.IsProcessInJob;fn.argtypes=[w.HANDLE,w.HANDLE,c.POINTER(w.BOOL)];fn.restype=w.BOOL;answer=w.BOOL()
        return bool(fn(c.c_void_p(int(entry['process']._handle)),job._job,c.byref(answer))) and bool(answer.value)
    def server_ready(self,entry,job):
        need(entry is not None and self.poll(entry) is None and self.member(entry,job))
        try:pid=self.pg._listener_pid(55483)
        except self.pg.PostgresStartPending:return False
        need(pid==entry['process'].pid)
        need(self.runtime._win_identity(self.kernel,self.w,self.c.c_void_p(int(entry['process']._handle)))==entry['identity'])
        return True
    def resume(self,entry):self.pg._resume_owned_primary(entry['process'].pid,entry['identity'])
    def reader(self,entry,which,capture):return _PipeReader((entry['process'].stdout,entry['process'].stderr)[which],which,capture)
    def poll(self,entry):return entry['process'].poll()
    def wait(self,entry,timeout):return entry['process'].wait(timeout=max(0.,timeout))
    def kill_primary(self,entry):entry['process'].kill()
    def active(self,job):
        c=self.c
        class Accounting(c.Structure):_fields_=[('t'+str(i),c.c_int64) for i in range(4)]+[('faults',c.c_uint32),('total',c.c_uint32),('active',c.c_uint32),('terminated',c.c_uint32)]
        info=Accounting();need(bool(job._kernel.QueryInformationJobObject(job._job,1,c.byref(info),c.sizeof(info),None)));return info.active
    def terminate_and_wait(self,job,timeout):
        # Even if clock/budget failed, attempt owned kill; late work cannot PASS.
        return job.terminate_and_wait(max(.001,min(20.,timeout)))
    def close_pipe(self,entry,which):(entry['process'].stdout,entry['process'].stderr)[which].close()
    def close_primary(self,entry):entry['process']._handle.Close()
    def sleep(self,seconds):time.sleep(seconds)
    def after(self):self._seal_inputs();need(self._token()==self.context_identity)
