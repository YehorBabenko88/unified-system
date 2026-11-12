"""Receipt-owned fresh PostgreSQL 18 lifecycle; never adopts a cluster/process.

The private Admin/System receipt is ownership evidence, not runtime readiness.
Native actions require an external owner phase; tests use inert boundaries.
"""
import copy,hashlib,json,os,re,socket,stat,time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
from . import lab_release,lab_runtime
from .contracts import seal
from .journal import Journal
from .service_bootstrap import canonical,local,stamp,read_file,parse,WindowsActivationKernel

SCHEMA='unified.owned-postgres.v1'
PLAN_FIELDS=frozenset(('schema','service_plan','resource_receipt_sha256','profile_sha256','auth_source','auth_sha256','root_identity','state_identity','namespace','data_root','cluster','port','database','user','bootstrap_user','postgresql_files','vendor_sha256','job_sha256','writer_sid','plan_sha256'))
CONFIG_FILES=('PG_VERSION','postgresql.conf','postgresql.auto.conf','pg_hba.conf','pg_ident.conf')
# https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags
_CREATE_SUSPENDED=0x00000004
CODES=frozenset(('POSTGRES_REJECTED','POSTGRES_OWNER_PHASE_REQUIRED','POSTGRES_OWNER_PHASE_REJECTED','POSTGRES_UNAVAILABLE','POSTGRES_IDENTITY_REJECTED','POSTGRES_ALREADY_EXISTS','POSTGRES_NOT_READY','POSTGRES_PROCESS_REJECTED','POSTGRES_AUTH_REJECTED','POSTGRES_START_PENDING','POSTGRES_POISONED'))
class PostgresBlocked(ValueError):
 def __init__(self,code='POSTGRES_REJECTED'):self.code=code if code in CODES else 'POSTGRES_REJECTED';super().__init__(self.code)
class PostgresStartPending(PostgresBlocked):
 def __init__(self):super().__init__('POSTGRES_START_PENDING')

def need(value,code='POSTGRES_REJECTED'):
 if not value:raise PostgresBlocked(code)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def directory(path):
 path=local(path);s=path.lstat();need(stat.S_ISDIR(s.st_mode));return [s.st_dev,s.st_ino]
def regular(path,limit=1048576):
 path=local(path);before=stamp(path);need(0<before[2]<=limit)
 with path.open('rb') as stream:
  raw=stream.read(limit+1);s=os.fstat(stream.fileno());need((s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink)==before)
 need(stamp(path)==before and len(raw)==before[2]);return raw

@dataclass(frozen=True,slots=True)
class OwnedProcessSpec:
 """Neutral layout only; caller must separately admit runtime/token/argv/env."""
 data_root:str
 code_root:str
 job_sha256:str
 def __post_init__(self):self._checked()
 def _checked(self):
  need(type(self) is OwnedProcessSpec)
  need(type(self.data_root) is str and type(self.code_root) is str and type(self.job_sha256) is str)
  need(re.fullmatch('[a-f0-9]{64}',self.job_sha256) is not None)
  data=local(self.data_root);code=local(self.code_root)
  need(data.is_dir() and code.is_dir())
  directory(data);directory(code)
  need(data!=code and data not in code.parents and code not in data.parents)

def postgres_plan(resource,profile,auth_source,*,boundary=None):
 try:
  record=resource.recorded();service=record['plan'];profile=copy.deepcopy(profile);config=profile['runtime_config'];context=profile['offline_context']
  need(service['role'] in ('CONTROL','SINGLE_PC') and context['role']==service['role'])
  root=local(service['root']);code=local(service['code']);state=local(service['state']);source=local(auth_source)
  need(context['node_id']==service['node_id'] and context['computer_name']==service['computer_name'] and config['release_sha256']==service['manifest_sha256'])
  report=lab_release.verify_capsule(code,service['manifest_sha256']);manifest=report['manifest']
  need(profile['derivation_receipt']['profile_sha256']==sha(canonical(config)) and profile['derivation_receipt']['base_manifest_sha256']==service['manifest_sha256'])
  config=lab_runtime.validate_config(config,manifest,code,hostname=service['computer_name'],offline_context=context)
  vendor_raw=regular(code/'locks/vendor.json');vendor=parse(vendor_raw)
  pg=vendor['postgresql'];need(type(pg) is dict and set(pg)=={'version','files'} and re.fullmatch(r'postgres \(PostgreSQL\) 18\.[0-9]+',pg['version']))
  prefix='runtime/postgresql/';files={name[len(prefix):]:pin for name,pin in manifest['files'].items() if name.startswith(prefix)}
  need(files==pg['files'] and all(name.split('/')[0] in ('bin','lib','share') for name in files))
  need({'bin/initdb.exe','bin/postgres.exe','bin/psql.exe','bin/libpq.dll'}<=set(files) and any(name.startswith('lib/') for name in files) and any(name.startswith('share/') for name in files))
  job='sources/grid/grid/ml_windows_job.py';need(job in manifest['files'])
  dsn=urlsplit(config['programs']['grid']['env']['POSTGRES_DSN']);need(dsn.scheme=='postgresql' and dsn.hostname=='127.0.0.1' and dsn.password is None and not dsn.query and not dsn.fragment)
  user=dsn.username;database=dsn.path[1:]
  for value in (user,database):need(type(value) is str and re.fullmatch('unified_lab_[a-z0-9_]{1,48}',value))
  need(type(dsn.port) is int and 1024<=dsn.port<=65535)
  boundary=WindowsPostgresBoundary() if boundary is None else boundary;writer=boundary.writer_identity()
  need(writer['computer_name'].casefold()==service['computer_name'].casefold())
  body=dict(schema=SCHEMA,service_plan=service,resource_receipt_sha256=record['receipt_sha256'],profile_sha256=sha(canonical(profile)),auth_source=str(source),auth_sha256=config['programs']['grid']['env']['GRID_LAB_AUTH_SHA256'],root_identity=directory(root),state_identity=directory(state),namespace=str(root/'postgres-ownership'),data_root=str(state/'postgres'),cluster=str(state/'postgres/cluster'),port=dsn.port,database=database,user=user,bootstrap_user='unified_bootstrap_'+service['plan_sha256'][:24],postgresql_files=files,vendor_sha256=sha(vendor_raw),job_sha256=manifest['files'][job]['sha256'],writer_sid=writer['user_sid'])
  return {**body,'plan_sha256':seal(body)}
 except PostgresBlocked:raise
 except Exception:raise PostgresBlocked() from None

def check_plan(plan):
 need(type(plan) is dict and set(plan)==PLAN_FIELDS and plan['schema']==SCHEMA and plan['plan_sha256']==seal({k:v for k,v in plan.items() if k!='plan_sha256'}));plan=copy.deepcopy(plan)
 service=plan['service_plan'];root=local(service['root']);state=local(service['state'])
 need(plan['namespace']==str(root/'postgres-ownership') and plan['data_root']==str(state/'postgres') and plan['cluster']==str(state/'postgres/cluster'))
 need(directory(root)==plan['root_identity'] and directory(state)==plan['state_identity'],'POSTGRES_IDENTITY_REJECTED');return plan

def permission(owner,boundary,action,plan):
 need(callable(owner),'POSTGRES_OWNER_PHASE_REQUIRED');need(boundary.writer_identity()=={'computer_name':plan['service_plan']['computer_name'],'user_sid':plan['writer_sid']},'POSTGRES_IDENTITY_REJECTED')
 try:allowed=owner(action,plan['plan_sha256'])
 except Exception:raise PostgresBlocked('POSTGRES_OWNER_PHASE_REJECTED') from None
 need(allowed is True,'POSTGRES_OWNER_PHASE_REJECTED');check_plan(plan)

def _record(journal,plan,stage,**facts):
 journal.append('OBSERVING',{'schema':SCHEMA,'plan_sha256':plan['plan_sha256'],'stage':stage,**facts})

def provision_postgres(plan,*,owner_phase=None,boundary=None):
 server=None;prepared=False;finished=False
 try:
  need(callable(owner_phase),'POSTGRES_OWNER_PHASE_REQUIRED');plan=check_plan(plan);boundary=WindowsPostgresBoundary(owner_phase=owner_phase) if boundary is None else boundary
  permission(owner_phase,boundary,'ADMIT_POSTGRES',plan);boundary.admit(plan)
  namespace=local(plan['namespace']);data=local(plan['data_root']);need(not namespace.exists() and not data.exists(),'POSTGRES_ALREADY_EXISTS')
  permission(owner_phase,boundary,'CREATE_POSTGRES_ROOTS',plan);boundary.prepare(plan)
  pins={namespace:directory(namespace),data:directory(data)};prepared=True
  def guard(action):
   permission(owner_phase,boundary,action,plan)
   for path,identity in pins.items():need(directory(path)==identity,'POSTGRES_IDENTITY_REJECTED')
  journal=Journal(namespace/'provision.sqlite');journal.initialize();_record(journal,plan,'ROOTS_CREATED',data_identity=pins[data])
  # Read existing CONTROL credentials only after protected secret admission.
  boundary.admit_auth(plan);source=local(plan['auth_source']);raw=regular(source,8192);need(sha(raw)==plan['auth_sha256'],'POSTGRES_AUTH_REJECTED')
  context=dict(scope='OFFLINE_VALIDATION_ONLY',role=plan['service_plan']['role'],node_id=plan['service_plan']['node_id'],computer_name=plan['service_plan']['computer_name'],credential_root=str(source.parent))
  auth=lab_runtime.read_grid_auth(source,plan['auth_sha256'],node_id=context['node_id'],release_id=boundary.release_id(plan),source_commit=boundary.grid_commit(plan),role_context=context)
  password=auth['PGPASSWORD'];need(re.fullmatch('[A-Za-z0-9_-]{32,128}',password) is not None,'POSTGRES_AUTH_REJECTED')
  guard('INITIALIZE_POSTGRES');boundary.initialize(plan,password);_record(journal,plan,'INITIALIZED')
  guard('START_PROVISION_POSTGRES');server=boundary.start(plan,provision=True);_record(journal,plan,'PROVISION_PROCESS_OWNED')
  guard('CREATE_POSTGRES_DATABASE');boundary.configure(plan,server,password)
  proof=boundary.ready(plan,server,provision=True);validate_sql(plan,proof);_record(journal,plan,'SQL_IDENTITY_OBSERVED',system_identifier=proof['system_identifier'])
  guard('STOP_PROVISION_POSTGRES');boundary.stop(plan,server);server=None;_record(journal,plan,'PROVISION_PROCESS_STOPPED')
  guard('SEAL_POSTGRES');boundary.seal(plan,password);_record(journal,plan,'DATA_SEALED')
  record=dict(schema=SCHEMA,plan=plan,data_identity=pins[data],cluster_identity=directory(plan['cluster']),system_identifier=proof['system_identifier'],config_files={name:lab_release.hash_file(Path(plan['cluster'])/name) for name in CONFIG_FILES},pgpass_sha256=sha(regular(namespace/'pgpass.conf',8192)),state='PROVISIONED_STOPPED',runtime_readiness='NOT_PROVEN')
  guard('PUBLISH_POSTGRES_OWNERSHIP');boundary.publish(plan,canonical(record));finished=True;return {'schema':SCHEMA,'status':'PROVISIONED_STOPPED','receipt_sha256':sha(canonical(record)),'runtime_readiness':'NOT_PROVEN'}
 except PostgresBlocked:raise
 except Exception:raise PostgresBlocked() from None
 finally:
  if server is not None:boundary.stop(plan,server) # Only jobs/handles created here; no PID lookup.
  if prepared and not finished:
   try:guard('SEAL_FAILED_POSTGRES');boundary.retain_failure(plan)
   except Exception:pass # Retain, never delete/adopt to force a successful rollback.

def validate_sql(plan,proof,system_identifier=None,*,bootstrap_login=False):
 need(type(proof) is dict and set(proof)=={'version_num','database','user','data_directory','port','system_identifier','bootstrap_login','superuser','createdb','createrole','replication','bypassrls'},'POSTGRES_IDENTITY_REJECTED')
 need(type(proof['version_num']) is int and 180000<=proof['version_num']<190000 and proof['database']==plan['database'] and proof['user']==plan['user'] and local(proof['data_directory'])==Path(plan['cluster']) and proof['port']==plan['port'],'POSTGRES_IDENTITY_REJECTED')
 value=proof['system_identifier'];need(type(value) is str and re.fullmatch('[1-9][0-9]{0,19}',value) and int(value)<2**64,'POSTGRES_NOT_READY')
 if system_identifier is not None:need(value==system_identifier,'POSTGRES_IDENTITY_REJECTED')
 need(proof['bootstrap_login'] is bootstrap_login and all(proof[key] is False for key in ('superuser','createdb','createrole','replication','bypassrls')),'POSTGRES_NOT_READY');return True

class PostgresOwnership:
 def __init__(self,grant,record,boundary):self.grant=grant;self._record=copy.deepcopy(record);self.boundary=boundary;self.server=None
 @property
 def record(self):return copy.deepcopy(self._record)
 def start(self):
  need(self.server is None);self.grant.require_current();self.boundary.admit_runtime(self.grant,self._record)
  try:
   self.server=self.boundary.start(self.record['plan'],provision=False)
   deadline=time.monotonic()+20
   while True:
    self.grant.require_current();need(self.server.alive(),'POSTGRES_PROCESS_REJECTED')
    try:proof=self.boundary.ready(self.record['plan'],self.server,provision=False);break
    except PostgresBlocked as error:
     if error.code not in ('POSTGRES_START_PENDING','POSTGRES_NOT_READY') or time.monotonic()>=deadline:raise
     time.sleep(.05)
   validate_sql(self.record['plan'],proof,self.record['system_identifier']);return self
  except PostgresBlocked:
   self.close();raise
  except Exception:
   self.close();raise PostgresBlocked('POSTGRES_NOT_READY') from None
 def require_current(self):
  self.grant.require_current();self.boundary.require_running(self.grant,self._record);need(self.server is not None and self.server.alive(),'POSTGRES_PROCESS_REJECTED');return True
 def close(self):
  if self.server is not None:
   server=self.server;self.boundary.stop(self.record['plan'],server);self.server=None

def read_postgres_ownership(grant,*,boundary=None):
 try:
  grant.require_current();need(grant.descriptor['service_plan']['role'] in ('CONTROL','SINGLE_PC'))
  plan=grant.descriptor['service_plan'];anchor=Path(plan['root'])/'postgres-ownership';kernel=grant._kernel
  raw,_=read_file(anchor/'receipt.json',262144,kernel,grant.service_sid,anchor)
  need(sha(raw)==grant.descriptor['qualification_refs']['database_evidence_sha256'],'POSTGRES_IDENTITY_REJECTED');record=parse(raw)
  need(type(record) is dict and set(record)=={'schema','plan','data_identity','cluster_identity','system_identifier','config_files','pgpass_sha256','state','runtime_readiness'} and record['schema']==SCHEMA and record['state']=='PROVISIONED_STOPPED' and record['runtime_readiness']=='NOT_PROVEN')
  pgplan=check_plan(record['plan']);need(pgplan['service_plan']==plan and pgplan['auth_sha256']==grant.descriptor['auth_sha256'] and pgplan['profile_sha256']==sha(canonical(grant.profile)),'POSTGRES_IDENTITY_REJECTED')
  need(directory(pgplan['data_root'])==record['data_identity'] and directory(pgplan['cluster'])==record['cluster_identity'],'POSTGRES_IDENTITY_REJECTED')
  need(set(record['config_files'])==set(CONFIG_FILES))
  for name in CONFIG_FILES:need(lab_release.hash_file(Path(pgplan['cluster'])/name)==record['config_files'][name],'POSTGRES_IDENTITY_REJECTED')
  raw,_=read_file(anchor/'pgpass.conf',8192,kernel,grant.service_sid,anchor);need(sha(raw)==record['pgpass_sha256'],'POSTGRES_AUTH_REJECTED')
  boundary=WindowsPostgresBoundary() if boundary is None else boundary;boundary.admit_runtime(grant,record);return PostgresOwnership(grant,record,boundary)
 except PostgresBlocked:raise
 except Exception:raise PostgresBlocked('POSTGRES_UNAVAILABLE') from None


class PostgresDataKernel(WindowsActivationKernel):
 """Separate four-ACE PG data policy; the service three-ACE policy is unchanged."""
 def _data_security(self,path):
  import ctypes
  owner=ctypes.c_void_p();acl=ctypes.c_void_p();descriptor=ctypes.c_void_p()
  need(self.advapi.GetNamedSecurityInfoW(str(path),1,5,ctypes.byref(owner),None,ctypes.byref(acl),None,ctypes.byref(descriptor))==0 and acl.value)
  try:
   address=acl.value;size=ctypes.c_ushort.from_address(address+2).value;count=ctypes.c_ushort.from_address(address+4).value;need(count==4 and 8<=size<=65535)
   control=ctypes.c_ushort();revision=ctypes.c_uint();need(self.advapi.GetSecurityDescriptorControl(descriptor,ctypes.byref(control),ctypes.byref(revision))!=0)
   rows=[]
   for index in range(count):
    ace=ctypes.c_void_p();need(self.advapi.GetAce(acl,index,ctypes.byref(ace))!=0)
    need(ctypes.c_ubyte.from_address(ace.value).value==0 and 12<=ctypes.c_ushort.from_address(ace.value+2).value<=size)
    rows.append((self._sid(ace.value+8),ctypes.c_uint.from_address(ace.value+4).value,ctypes.c_ubyte.from_address(ace.value+1).value))
   return self._sid(owner),bool(control.value&0x1000),rows
  finally:self.kernel.LocalFree(descriptor)
 def require_data(self,plan,*,recurse=True,sealing=False):
  root=local(plan['data_root']);items=[root]
  if recurse:
   for directory_name,dirs,files in os.walk(root,followlinks=False):
    for name in [*dirs,*files]:
     items.append(local(Path(directory_name)/name));need(len(items)<=300000)
  for path in items:
   owner,protected,rows=self._data_security(path)
   need(owner in (('S-1-5-18','S-1-5-32-544') if sealing else ('S-1-5-18','S-1-5-32-544','S-1-5-19')),'POSTGRES_IDENTITY_REJECTED')
   need(protected==(path==root),'POSTGRES_IDENTITY_REJECTED')
   expected={'S-1-5-18':0x1f01ff,'S-1-5-32-544':0x1f01ff,plan['service_plan']['service_sid']:0x1301bf,'S-1-3-4':0x20000}
   need(len(rows)==4 and {sid for sid,_,_ in rows}==set(expected))
   flags=(3 if path.is_dir() else 0)|(0 if path==root else 16)
   need(all(rights==expected[sid] and ace_flags==flags for sid,rights,ace_flags in rows),'POSTGRES_IDENTITY_REJECTED')
  return True


def _resume_owned_primary(pid,identity,*,kernel=None):
 """Documented Toolhelp/OpenThread/ResumeThread; never imports ambient psutil."""
 import ctypes
 from ctypes import wintypes
 from .runtime_process import _identity
 kernel=ctypes.WinDLL('kernel32',use_last_error=True) if kernel is None else kernel
 class ENTRY(ctypes.Structure):_fields_=[('size',wintypes.DWORD),('usage',wintypes.DWORD),('thread_id',wintypes.DWORD),('process_id',wintypes.DWORD),('priority',wintypes.LONG),('delta',wintypes.LONG),('flags',wintypes.DWORD)]
 kernel.CreateToolhelp32Snapshot.argtypes=[wintypes.DWORD,wintypes.DWORD];kernel.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
 kernel.Thread32First.argtypes=[wintypes.HANDLE,ctypes.POINTER(ENTRY)];kernel.Thread32First.restype=wintypes.BOOL
 kernel.Thread32Next.argtypes=kernel.Thread32First.argtypes;kernel.Thread32Next.restype=wintypes.BOOL
 kernel.OpenThread.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenThread.restype=wintypes.HANDLE
 kernel.GetProcessIdOfThread.argtypes=[wintypes.HANDLE];kernel.GetProcessIdOfThread.restype=wintypes.DWORD
 kernel.ResumeThread.argtypes=[wintypes.HANDLE];kernel.ResumeThread.restype=wintypes.DWORD
 kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle.restype=wintypes.BOOL
 need(_identity(pid)==identity,'POSTGRES_PROCESS_REJECTED');snapshot=kernel.CreateToolhelp32Snapshot(4,0);need(snapshot not in (None,ctypes.c_void_p(-1).value))
 try:
  entry=ENTRY();entry.size=ctypes.sizeof(entry);found=[];more=kernel.Thread32First(snapshot,ctypes.byref(entry));count=0
  while more:
   count+=1;need(count<=100000)
   if entry.process_id==pid:found.append(entry.thread_id)
   entry.size=ctypes.sizeof(entry);more=kernel.Thread32Next(snapshot,ctypes.byref(entry))
  need(len(found)==1,'POSTGRES_PROCESS_REJECTED');thread=kernel.OpenThread(0x0002|0x0040,False,found[0]);need(thread)
  try:
   need(kernel.GetProcessIdOfThread(thread)==pid and _identity(pid)==identity,'POSTGRES_PROCESS_REJECTED')
   need(kernel.ResumeThread(thread)==1,'POSTGRES_PROCESS_REJECTED')
  finally:kernel.CloseHandle(thread)
 finally:kernel.CloseHandle(snapshot)


def _job_class(plan):
 # Existing Grid primitive only: source bytes admitted, no package/backend import
 # or bytecode lookup; resume=False avoids its optional psutil dependency.
 if isinstance(plan,OwnedProcessSpec):
  need(type(plan) is OwnedProcessSpec);plan._checked()
 path=Path(plan.code_root if type(plan) is OwnedProcessSpec else plan['service_plan']['code'])/'sources/grid/grid/ml_windows_job.py';raw=regular(path)
 need(sha(raw)==(plan.job_sha256 if type(plan) is OwnedProcessSpec else plan['job_sha256']));namespace={'__name__':'_unified_owned_pg_job','__file__':str(path)};exec(compile(raw,str(path),'exec'),namespace)
 job=namespace['WindowsJob'];need(callable(getattr(job,'terminate_and_wait',None)),'POSTGRES_PROCESS_REJECTED');return job

def _listener_pid(port,*,api=None):
 """Documented bounded IPv4 TCP_TABLE_OWNER_PID_LISTENER, no port trust probe."""
 import ctypes,struct
 api=ctypes.WinDLL('iphlpapi',use_last_error=True).GetExtendedTcpTable if api is None else api
 api.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint32),ctypes.c_int,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_uint32];api.restype=ctypes.c_uint32
 size=ctypes.c_uint32();status=api(None,ctypes.byref(size),False,2,3,0);need(status==122 and 4<=size.value<=1048576,'POSTGRES_PROCESS_REJECTED')
 for _ in range(3):
  buffer=ctypes.create_string_buffer(size.value);status=api(buffer,ctypes.byref(size),False,2,3,0)
  if status!=122:break
  need(4<=size.value<=1048576)
 need(status==0 and 4<=size.value<=len(buffer),'POSTGRES_PROCESS_REJECTED');raw=buffer.raw[:size.value];count=struct.unpack_from('<I',raw)[0];need(count<=32768 and 4+24*count<=len(raw))
 matched=[]
 for index in range(count):
  state,address,local_port,remote,remote_port,pid=struct.unpack_from('<6I',raw,4+24*index)
  if state==2 and socket.ntohs(local_port&65535)==port:
   need(socket.inet_ntoa(struct.pack('<I',address))=='127.0.0.1','POSTGRES_PROCESS_REJECTED');matched.append(pid)
 if not matched:raise PostgresStartPending()
 need(len(matched)==1 and matched[0]>0,'POSTGRES_PROCESS_REJECTED');return matched[0]


def _job_process_identity(server,pid):
 import ctypes
 from ctypes import wintypes
 from .runtime_process import _win_api,_win_identity
 need(type(pid) is int and 0<pid<2**32 and server.alive() and server.job is not None,'POSTGRES_PROCESS_REJECTED')
 kernel,w=_win_api();handle=kernel.OpenProcess(0x1000|0x100000,False,pid);need(handle,'POSTGRES_PROCESS_REJECTED')
 try:
  kernel.IsProcessInJob.argtypes=[wintypes.HANDLE,wintypes.HANDLE,ctypes.POINTER(wintypes.BOOL)];kernel.IsProcessInJob.restype=wintypes.BOOL;member=wintypes.BOOL()
  need(kernel.IsProcessInJob(handle,server.job._job,ctypes.byref(member)) and member.value,'POSTGRES_PROCESS_REJECTED')
  identity=_win_identity(kernel,w,handle);need(identity[1]==server.identity[1] and int(identity[0])>=int(server.identity[0]),'POSTGRES_PROCESS_REJECTED');return identity
 finally:kernel.CloseHandle(handle)


def _prove_listener(plan,server):
 pid=_listener_pid(plan['port']);need(pid==server.proc.pid and _job_process_identity(server,pid)==server.identity,'POSTGRES_PROCESS_REJECTED');return True

def _load_libpq(path):
 import ctypes
 library=ctypes.WinDLL(str(path),winmode=0x00000100|0x00000800)
 kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.GetModuleFileNameW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_uint];kernel.GetModuleFileNameW.restype=ctypes.c_uint
 name=ctypes.create_unicode_buffer(32768);count=kernel.GetModuleFileNameW(library._handle,name,len(name));need(0<count<len(name) and local(name.value)==path,'POSTGRES_IDENTITY_REJECTED');return library

class _LibpqConnection:
 """Fixed closed libpq18 ABI, bounded nonblocking I/O, never returns raw errors."""
 def __init__(self,dll,parameters):
  import ctypes
  self.dll=dll;self.connection=None
  signatures={'PQconnectStartParams':([ctypes.POINTER(ctypes.c_char_p),ctypes.POINTER(ctypes.c_char_p),ctypes.c_int],ctypes.c_void_p),'PQconnectPoll':([ctypes.c_void_p],ctypes.c_int),'PQsetnonblocking':([ctypes.c_void_p,ctypes.c_int],ctypes.c_int),'PQsendQuery':([ctypes.c_void_p,ctypes.c_char_p],ctypes.c_int),'PQflush':([ctypes.c_void_p],ctypes.c_int),'PQconsumeInput':([ctypes.c_void_p],ctypes.c_int),'PQisBusy':([ctypes.c_void_p],ctypes.c_int),'PQgetResult':([ctypes.c_void_p],ctypes.c_void_p),'PQresultStatus':([ctypes.c_void_p],ctypes.c_int),'PQntuples':([ctypes.c_void_p],ctypes.c_int),'PQnfields':([ctypes.c_void_p],ctypes.c_int),'PQgetlength':([ctypes.c_void_p,ctypes.c_int,ctypes.c_int],ctypes.c_int),'PQgetvalue':([ctypes.c_void_p,ctypes.c_int,ctypes.c_int],ctypes.c_void_p),'PQclear':([ctypes.c_void_p],None),'PQfinish':([ctypes.c_void_p],None)}
  for name,(args,result) in signatures.items():function=getattr(dll,name);function.argtypes=args;function.restype=result
  keys=(ctypes.c_char_p*(len(parameters)+1))();values=(ctypes.c_char_p*(len(parameters)+1))()
  for index,(key,value) in enumerate(parameters.items()):keys[index]=key.encode('ascii');values[index]=value.encode('utf8')
  try:
   self.connection=dll.PQconnectStartParams(keys,values,0);need(self.connection,'POSTGRES_NOT_READY');deadline=time.monotonic()+5
   while True:
    status=dll.PQconnectPoll(self.connection)
    if status==3:break
    need(status in (1,2,4) and time.monotonic()<deadline,'POSTGRES_NOT_READY');time.sleep(.01)
   need(dll.PQsetnonblocking(self.connection,1)==0)
  except Exception:self.close();raise
 def query(self,sql):
  import ctypes
  need(type(sql) is str and 0<len(sql.encode())<=8192);need(self.dll.PQsendQuery(self.connection,sql.encode())==1,'POSTGRES_NOT_READY');deadline=time.monotonic()+6;payload=b'';count=0
  while True:
   flushed=self.dll.PQflush(self.connection)
   if flushed==0:break
   need(flushed==1 and time.monotonic()<deadline,'POSTGRES_NOT_READY');time.sleep(.01)
  while True:
   while self.dll.PQisBusy(self.connection):
    need(time.monotonic()<deadline and self.dll.PQconsumeInput(self.connection)==1,'POSTGRES_NOT_READY');time.sleep(.01)
   result=self.dll.PQgetResult(self.connection)
   if not result:break
   try:
    count+=1;need(count<=8);status=self.dll.PQresultStatus(result);need(status in (1,2),'POSTGRES_NOT_READY')
    if status==2:
     need(self.dll.PQntuples(result)==1 and self.dll.PQnfields(result)==1);length=self.dll.PQgetlength(result,0,0);need(0<length<=65536);payload=ctypes.string_at(self.dll.PQgetvalue(result,0,0),length)
   finally:self.dll.PQclear(result)
  need(count>=1);return payload
 def close(self):
  if self.connection:
   connection=self.connection;self.connection=None;self.dll.PQfinish(connection) # Close socket/results even on cancellation/deadline.

def _parse_postmaster_opts(raw):
 import ctypes,shlex
 text=raw.decode('utf8').strip();need(0<len(text)<=8192)
 if os.name!='nt':return shlex.split(text)
 shell=ctypes.WinDLL('shell32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True);count=ctypes.c_int()
 shell.CommandLineToArgvW.argtypes=[ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_int)];shell.CommandLineToArgvW.restype=ctypes.POINTER(ctypes.c_wchar_p);kernel.LocalFree.argtypes=[ctypes.c_void_p]
 result=shell.CommandLineToArgvW(text,ctypes.byref(count));need(result and 1<=count.value<=64)
 try:return [result[index] for index in range(count.value)]
 finally:kernel.LocalFree(result)

class _Launch:
 """Mutable launch journal is never authority without this live owner's Job.

 A prior interrupted/poisoned controller cannot reconstruct quiescence from a
 PID file. Such launches stay blocked for separately approved owner recovery.
 """
 def __init__(self,plan):
  import uuid
  self.plan=copy.deepcopy(plan);self.data=directory(plan['data_root']);self.cluster=directory(plan['cluster']);self.stream=None;self.journal=None;self.done=False
  try:
   path=local(Path(plan['data_root'])/'lifecycle.lock');self.stream=path.open('a+b');need(path.lstat().st_nlink==1)
   self.stream.seek(0)
   if os.name=='nt':
    import msvcrt
    msvcrt.locking(self.stream.fileno(),msvcrt.LK_NBLCK,1)
   else:
    import fcntl
    fcntl.flock(self.stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
   if self.stream.seek(0,2)==0:self.stream.write(b'0');self.stream.flush();os.fsync(self.stream.fileno())
   self.stream.seek(0)
   self.lock_identity=stamp(path);self.directory=local(Path(plan['data_root'])/'launches');marker=canonical({'schema':SCHEMA,'plan_sha256':plan['plan_sha256'],'data_identity':self.data,'cluster_identity':self.cluster})
   if self.directory.exists():need(regular(self.directory/'namespace.json')==marker,'POSTGRES_POISONED')
   else:
    self.directory.mkdir(exist_ok=False)
    with (self.directory/'namespace.json').open('xb') as file:file.write(marker);file.flush();os.fsync(file.fileno())
   files=list(self.directory.iterdir());need(len(files)<=257,'POSTGRES_POISONED')
   for file in files:
    if file.name=='namespace.json':continue
    need(re.fullmatch(r'[a-f0-9]{32}\.sqlite',file.name) and 0<stamp(file)[2]<=1048576,'POSTGRES_POISONED');rows=Journal(file).read();need(1<=len(rows)<=16,'POSTGRES_POISONED')
    for row in rows:need(row['state']=='OBSERVING' and row['receipt']['schema']==SCHEMA and row['receipt']['plan_sha256']==plan['plan_sha256'] and row['receipt']['launch_id']==file.stem,'POSTGRES_POISONED')
    need(rows[-1]['receipt']['stage']=='STOPPED_CLEAN','POSTGRES_POISONED')
   # No pre-existing PID/opts can be claimed by this new launch intent.
   for name in ('postmaster.pid','postmaster.opts'):need(not local(Path(plan['cluster'])/name).exists(),'POSTGRES_PROCESS_REJECTED')
   self.identifier=uuid.uuid4().hex;file=self.directory/(self.identifier+'.sqlite')
   with file.open('xb'):pass
   self.journal=Journal(file);self.journal.initialize();self.mark('LAUNCH_INTENT',data_identity=self.data,cluster_identity=self.cluster)
  except Exception:self.release();raise PostgresBlocked('POSTGRES_POISONED') from None
 def check(self):
  need(self.stream is not None and directory(self.plan['data_root'])==self.data and directory(self.plan['cluster'])==self.cluster and stamp(Path(self.plan['data_root'])/'lifecycle.lock')==self.lock_identity,'POSTGRES_POISONED')
 def mark(self,stage,**facts):
  self.check();self.journal.append('OBSERVING',dict(schema=SCHEMA,plan_sha256=self.plan['plan_sha256'],launch_id=self.identifier,stage=stage,**facts))
 def launched(self,server):self.mark('OWNED_PROCESS',pid=server.pid,identity=server.identity,argv_sha256=sha(canonical(server.argv)))
 def quiesced(self):self.mark('QUIESCED')
 def poison(self):
  if self.journal is not None and not self.done:
   try:self.mark('POISONED')
   except Exception:pass
 def no_process(self):
  self.quiesced()
  for name in ('postmaster.pid','postmaster.opts'):need(not local(Path(self.plan['cluster'])/name).exists(),'POSTGRES_POISONED')
  self.mark('STOPPED_CLEAN');self.done=True;self.release()
 def retire(self,server):
  self.check();need(server.confirmed_quiescent,'POSTGRES_POISONED')
  try:
   try:_listener_pid(self.plan['port'])
   except PostgresStartPending:pass
   else:raise PostgresBlocked('POSTGRES_POISONED')
   snapshots={}
   for name in ('postmaster.pid','postmaster.opts'):
    path=local(Path(self.plan['cluster'])/name)
    if not path.exists():continue
    raw=regular(path,8192);identity=stamp(path)
    if name=='postmaster.pid':
     lines=raw.decode('utf8').splitlines();need(len(lines)>=4 and lines[0]==str(server.pid) and local(lines[1])==Path(self.plan['cluster']) and lines[3]==str(self.plan['port']),'POSTGRES_POISONED')
    else:
     args=_parse_postmaster_opts(raw);need(len(args)==len(server.argv) and local(args[0])==Path(server.argv[0]) and args[1:]==server.argv[1:],'POSTGRES_POISONED')
    snapshots[path]=(identity,raw)
   self.mark('OWNED_FILES_VERIFIED',files={path.name:{'identity':identity,'sha256':sha(raw)} for path,(identity,raw) in snapshots.items()})
   for path,(identity,raw) in snapshots.items():
    self.check();need(stamp(path)==identity and regular(path,8192)==raw,'POSTGRES_POISONED');path.unlink()
   self.mark('STOPPED_CLEAN');self.done=True;self.release()
  except Exception:self.poison();raise PostgresBlocked('POSTGRES_POISONED') from None
 def release(self):
  if self.stream is not None:
   stream=self.stream;self.stream=None
   try:
    stream.seek(0)
    if os.name=='nt':
     import msvcrt
     msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
    else:
     import fcntl
     fcntl.flock(stream,fcntl.LOCK_UN)
   except OSError:pass
   finally:stream.close()

class _RestrictedProcess:
 """Own newly created restricted postgres handle; no PID-based termination."""
 def __init__(self,plan,argv,environment):
  import ctypes,subprocess
  from ctypes import wintypes
  kernel=ctypes.WinDLL('kernel32',use_last_error=True);advapi=ctypes.WinDLL('advapi32',use_last_error=True);self.kernel=kernel;self.handle=None;self.stdin=None
  class SIDATTR(ctypes.Structure):_fields_=[('sid',ctypes.c_void_p),('attributes',wintypes.DWORD)]
  class STARTUP(ctypes.Structure):_fields_=[('cb',wintypes.DWORD),('reserved',wintypes.LPWSTR),('desktop',wintypes.LPWSTR),('title',wintypes.LPWSTR),('x',wintypes.DWORD),('y',wintypes.DWORD),('xsize',wintypes.DWORD),('ysize',wintypes.DWORD),('xchars',wintypes.DWORD),('ychars',wintypes.DWORD),('fill',wintypes.DWORD),('flags',wintypes.DWORD),('show',wintypes.WORD),('reserved_size',wintypes.WORD),('reserved_bytes',ctypes.c_void_p),('stdin',wintypes.HANDLE),('stdout',wintypes.HANDLE),('stderr',wintypes.HANDLE)]
  class PROCESS(ctypes.Structure):_fields_=[('process',wintypes.HANDLE),('thread',wintypes.HANDLE),('pid',wintypes.DWORD),('tid',wintypes.DWORD)]
  kernel.GetCurrentProcess.restype=wintypes.HANDLE;kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.LocalFree.argtypes=[ctypes.c_void_p]
  advapi.OpenProcessToken.argtypes=[wintypes.HANDLE,wintypes.DWORD,ctypes.POINTER(wintypes.HANDLE)];advapi.OpenProcessToken.restype=wintypes.BOOL
  advapi.ConvertStringSidToSidW.argtypes=[wintypes.LPCWSTR,ctypes.POINTER(ctypes.c_void_p)];advapi.ConvertStringSidToSidW.restype=wintypes.BOOL
  advapi.CreateRestrictedToken.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.DWORD,ctypes.POINTER(SIDATTR),wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,ctypes.c_void_p,ctypes.POINTER(wintypes.HANDLE)];advapi.CreateRestrictedToken.restype=wintypes.BOOL
  advapi.CreateProcessAsUserW.argtypes=[wintypes.HANDLE,wintypes.LPCWSTR,wintypes.LPWSTR,ctypes.c_void_p,ctypes.c_void_p,wintypes.BOOL,wintypes.DWORD,ctypes.c_void_p,wintypes.LPCWSTR,ctypes.POINTER(STARTUP),ctypes.POINTER(PROCESS)];advapi.CreateProcessAsUserW.restype=wintypes.BOOL
  original=wintypes.HANDLE();restricted=wintypes.HANDLE();allocated=[]
  try:
   need(advapi.OpenProcessToken(kernel.GetCurrentProcess(),0x0002|0x0008|0x0001,ctypes.byref(original)))
   disabled=(SIDATTR*2)()
   for index,sid in enumerate(('S-1-5-32-544','S-1-5-32-547')):
    pointer=ctypes.c_void_p();need(advapi.ConvertStringSidToSidW(sid,ctypes.byref(pointer)));allocated.append(pointer);disabled[index].sid=pointer.value
   # Restricted version of caller token: no SE_ASSIGNPRIMARYTOKEN requirement,
   # no AdjustTokenPrivileges, logon credentials, new account or policy change.
   need(advapi.CreateRestrictedToken(original,1,2,disabled,0,None,0,None,ctypes.byref(restricted)))
   startup=STARTUP();startup.cb=ctypes.sizeof(startup);process=PROCESS();command=ctypes.create_unicode_buffer(subprocess.list2cmdline(argv));block=ctypes.create_unicode_buffer('\0'.join(key+'='+value for key,value in sorted(environment.items(),key=lambda item:item[0].casefold()))+'\0\0')
   need(advapi.CreateProcessAsUserW(restricted,argv[0],command,None,None,False,0x00000004|0x00000400|0x08000000,block,plan['data_root'],ctypes.byref(startup),ctypes.byref(process)),'POSTGRES_PROCESS_REJECTED')
   self.handle=process.process;self.pid=process.pid;kernel.CloseHandle(process.thread)
  finally:
   for pointer in allocated:kernel.LocalFree(pointer)
   if restricted:kernel.CloseHandle(restricted)
   if original:kernel.CloseHandle(original)
  kernel.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)];kernel.GetExitCodeProcess.restype=wintypes.BOOL
  kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];kernel.WaitForSingleObject.restype=wintypes.DWORD
  kernel.TerminateProcess.argtypes=[wintypes.HANDLE,wintypes.UINT];kernel.TerminateProcess.restype=wintypes.BOOL
 def poll(self):
  import ctypes
  status=ctypes.c_uint();need(self.kernel.GetExitCodeProcess(self.handle,ctypes.byref(status)));return None if status.value==259 else status.value
 def terminate(self):need(self.kernel.TerminateProcess(self.handle,1))
 def wait(self,timeout):need(self.kernel.WaitForSingleObject(self.handle,int(timeout*1000))==0);return self.poll()
 def close_handle(self):
  if self.handle:self.kernel.CloseHandle(self.handle);self.handle=None

class OwnedJobProcess:
 def __init__(self,plan,argv,environment,*,capture=False,restricted=False,launch=None):
  import subprocess,tempfile
  from .runtime_process import _identity
  if isinstance(plan,OwnedProcessSpec):
   need(type(plan) is OwnedProcessSpec and restricted is False and launch is None)
   plan._checked()
  need(os.name=='nt');self.job=None;self.proc=None;self.identity=None;self.output=None;self.error=None;self.launch=launch;self.confirmed_quiescent=False;self.argv=list(argv);self.pid=None
  try:
   job_class=_job_class(plan)
   if capture:
    self.output=tempfile.TemporaryFile(dir=plan.data_root if type(plan) is OwnedProcessSpec else plan['data_root']);self.error=tempfile.TemporaryFile(dir=plan.data_root if type(plan) is OwnedProcessSpec else plan['data_root'])
   self.proc=_RestrictedProcess(plan,argv,environment) if restricted else subprocess.Popen(argv,cwd=plan.data_root if type(plan) is OwnedProcessSpec else plan['data_root'],env=environment,stdin=subprocess.PIPE,stdout=self.output if capture else subprocess.DEVNULL,stderr=self.error if capture else subprocess.DEVNULL,creationflags=_CREATE_SUSPENDED|subprocess.CREATE_NO_WINDOW,shell=False)
   self.pid=self.proc.pid;self.identity=_identity(self.proc.pid);need(self.identity is not None and Path(self.identity[1])==Path(argv[0]),'POSTGRES_PROCESS_REJECTED')
   self.job=job_class(self.proc.pid,resume_primary_thread=False)
   _resume_owned_primary(self.proc.pid,self.identity)
   if self.launch is not None:self.launch.launched(self)
  except Exception:
   # Before Resume, an unassigned newly-created child has no descendants.
   # After assignment, only the shared primitive's synchronous quiescence can
   # authorize cleanup. Never substitute close()/parent PID exit for this.
   if self.job is not None:
    try:
     self.close()
     if self.launch is not None:self.launch.retire(self)
    except Exception:
     if self.launch is not None:self.launch.poison()
     raise PostgresBlocked('POSTGRES_POISONED') from None
   else:
    if self.proc is not None:
     if self.proc.poll() is None:self.proc.terminate()
     self.proc.wait(timeout=5)
     if hasattr(self.proc,'close_handle'):self.proc.close_handle()
    if self.launch is not None:self.launch.no_process()
   for file in (self.output,self.error):
    if file is not None:file.close()
   raise PostgresBlocked('POSTGRES_PROCESS_REJECTED') from None
 def alive(self):
  from .runtime_process import _identity
  return self.proc is not None and self.proc.poll() is None and _identity(self.proc.pid)==self.identity
 def communicate(self,raw,timeout=30):
  try:
   self.proc.communicate(raw,timeout=timeout);need(self.proc.returncode==0,'POSTGRES_NOT_READY');self.output.seek(0);result=self.output.read(1048577);need(len(result)<=1048576);return result
  finally:self.close()
 def close(self):
  if self.job is not None:
   try:confirmed=self.job.terminate_and_wait(timeout=5)
   except Exception:confirmed=False
   if confirmed is not True:
    if self.launch is not None:self.launch.poison()
    raise PostgresBlocked('POSTGRES_POISONED')
   self.job=None;self.confirmed_quiescent=True
   if self.launch is not None:self.launch.quiesced()
  if self.proc is not None:
   self.proc.wait(timeout=5)
   if self.proc.stdin is not None:self.proc.stdin.close()
   if hasattr(self.proc,'close_handle'):self.proc.close_handle()
   self.proc=None
  for name in ('output','error'):
   file=getattr(self,name,None)
   if file is not None:file.close();setattr(self,name,None)



class WindowsPostgresBoundary:
 def __init__(self,*,owner_phase=None):self.owner_phase=owner_phase;self.manifest=None;self.secret_files={};self.runtime_grant=None;self.roots={};self.copies={}
 def writer_identity(self):
  import ctypes
  from .installation_service import current_computer_name
  kernel=WindowsActivationKernel();token=ctypes.c_void_p()
  need(kernel.advapi.OpenProcessToken(kernel.kernel.GetCurrentProcess(),8,ctypes.byref(token))!=0)
  try:
   size=ctypes.c_uint();kernel.advapi.GetTokenInformation(token,1,None,0,ctypes.byref(size));need(0<size.value<=65536)
   buffer=ctypes.create_string_buffer(size.value);need(kernel.advapi.GetTokenInformation(token,1,buffer,len(buffer),ctypes.byref(size))!=0)
   sid=kernel._sid(ctypes.c_void_p.from_buffer(buffer).value);return {'computer_name':current_computer_name(),'user_sid':sid}
  finally:kernel.kernel.CloseHandle(token)
 def _permit(self,plan,action):
  from .service_activation import WindowsRevisionBoundary
  WindowsRevisionBoundary()._assert_writer({'service_plan':plan['service_plan']});permission(self.owner_phase,self,action,plan)
  for path,identity in self.roots.items():need(directory(path)==identity,'POSTGRES_IDENTITY_REJECTED')
 def admit(self,plan):
  self._permit(plan,'ADMIT_POSTGRES_NATIVE')
  from .installation_service import _check_plan
  _check_plan(plan['service_plan']);self.manifest=lab_release.verify_capsule(plan['service_plan']['code'],plan['service_plan']['manifest_sha256'])['manifest']
  kernel=WindowsActivationKernel();root=Path(plan['service_plan']['code'])
  for name in [*self.manifest['directories'],*self.manifest['files'],'lab-release.json']:kernel.require_readonly(root/name,plan['service_plan']['service_sid'],root)
  lab_runtime.verify_sources(root,self.manifest,owner_admitted_root=root)
  need(sha(regular(root/'locks/vendor.json'))==plan['vendor_sha256'])
 def release_id(self,plan):return self.manifest['release_id']
 def grid_commit(self,plan):return self.manifest['sources']['grid']['commit']
 def admit_auth(self,plan):
  # Transit CONTROL credentials must already be protected by the owner broker.
  # Their containing directory is explicitly admitted; no service-owned file.
  path=local(plan['auth_source']);kernel=WindowsActivationKernel();owner,_,rows=kernel._security(path)
  need(owner in ('S-1-5-18','S-1-5-32-544') and {sid for sid,_,_ in rows}=={'S-1-5-18','S-1-5-32-544',plan['service_plan']['service_sid']},'POSTGRES_AUTH_REJECTED')
  need(all(mask==(0x1200a9 if sid==plan['service_plan']['service_sid'] else 0x1f01ff) for sid,mask,_ in rows),'POSTGRES_AUTH_REJECTED')
 def _ps(self,plan,mode):
  self._permit(plan,'POSTGRES_ACL_'+mode)
  from . import installation_service as service
  import base64
  need(mode in ('PREPARE','SEAL','PUBLISH','FAILURE'));need(sha(lab_release.regular(service.MODULE).read_bytes())==plan['service_plan']['executor_sha256'])
  # Fixed reviewed code, fixed paths derived from a closed plan; no arbitrary
  # script, policy bypass, existing-root ACL changes or generic LocalService ACE.
  code="""$ErrorActionPreference='Stop';[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
try{$q=[Console]::In.ReadToEnd()|ConvertFrom-Json;$m=Import-Module -Name ([WildcardPattern]::Escape($env:UNIFIED_SERVICE_MODULE)) -PassThru
& $m {param($q) Assert-OwnedAdmin;Assert-OwnedMarker $q.plan.service_plan
$p=$q.plan;$sid=$p.service_plan.service_sid;$writer=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
if($writer -cne $p.writer_sid -or [Environment]::MachineName -ine $p.service_plan.computer_name){throw 'IDENTITY'}
if($q.mode -ceq 'PREPARE'){
 Set-OwnedAcl $p.namespace $sid 'ReadAndExecute'
 Set-OwnedAcl $p.data_root $writer 'Modify'
}elseif($q.mode -cin @('SEAL','FAILURE')){
 $root=Get-Item -LiteralPath $p.data_root -Force;Assert-OwnedPath $root.FullName
 $acl=Get-Acl -LiteralPath $p.data_root;$acl.SetSecurityDescriptorSddlForm(('O:BAG:BAD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;0x1301bf;;;'+$sid+')(A;OICI;RC;;;S-1-3-4)'));$root.SetAccessControl($acl)
 $items=@(Get-ChildItem -LiteralPath $p.data_root -Force -Recurse);if($items.Count -gt 300000){throw 'LIMIT'}
 foreach($item in $items){Assert-OwnedPath $item.FullName;$a=Get-Acl -LiteralPath $item.FullName;$a.SetOwner([Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'));$a.SetAccessRuleProtection($false,$false);foreach($r in @($a.GetAccessRules($true,$false,[Security.Principal.SecurityIdentifier]))){$a.RemoveAccessRuleSpecific($r)};$item.SetAccessControl($a)}
}
foreach($item in @(Get-Item -LiteralPath $p.namespace -Force)+@(Get-ChildItem -LiteralPath $p.namespace -Force -Recurse)){Assert-OwnedPath $item.FullName;$a=Get-Acl -LiteralPath $item.FullName;$a.SetOwner([Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'));$item.SetAccessControl($a)}
} $q;[Console]::Out.Write('{"ok":true}')}
catch{[Console]::Out.Write('{"error":"POSTGRES_REJECTED"}');exit 1}"""
  env=service._environment();env['UNIFIED_SERVICE_MODULE']=str(service.MODULE);encoded=base64.b64encode(code.encode('utf-16le')).decode()
  raw,status=service._run([plan['service_plan']['native_tools']['powershell']['path'],'-NoProfile','-NonInteractive','-EncodedCommand',encoded],env=env,payload=canonical({'plan':plan,'mode':mode}),timeout=60)
  need(status==0 and json.loads(raw)=={'ok':True})
 def retain_failure(self,plan):self._ps(plan,'FAILURE')
 def prepare(self,plan):
  self._permit(plan,'CREATE_POSTGRES_NATIVE_ROOTS')
  for path in (local(plan['namespace']),local(plan['data_root'])):
   self._permit(plan,'CREATE_POSTGRES_NATIVE_ROOT');path.mkdir(exist_ok=False);self.roots[path]=directory(path)
  self._ps(plan,'PREPARE')
 def _exe(self,plan,name,*,provision=False):
  if provision:self._verify_bootstrap(plan)
  relative='bin/'+name+'.exe';base=Path(plan['data_root'])/'bootstrap-runtime' if provision else Path(plan['service_plan']['code'])/'runtime/postgresql';path=local(base/relative)
  need(lab_release.hash_file(path)==plan['postgresql_files'][relative]);return str(path)
 def _env(self,plan,*,provision=False):
  from .lab_runtime import child_environment
  env=child_environment();env.update(PATH=str(Path(plan['data_root'])/'bootstrap-runtime/bin') if provision else str(Path(plan['service_plan']['code'])/'runtime/postgresql/bin'),TEMP=plan['data_root'],TMP=plan['data_root'],PGPASSFILE=str(Path(plan['data_root'])/'bootstrap/pgpass.conf') if provision else str(Path(plan['namespace'])/'pgpass.conf'),PGCONNECT_TIMEOUT='2',PGCLIENTENCODING='UTF8',PGAPPNAME='unified_owned_postgres')
  for key in list(env):
   if key.upper().startswith('PG') and key not in ('PGPASSFILE','PGCONNECT_TIMEOUT','PGCLIENTENCODING','PGAPPNAME'):del env[key]
  return env
 def _copy_bootstrap(self,plan):
  target=local(Path(plan['data_root'])/'bootstrap-runtime');target.mkdir(exist_ok=False);self.roots[target]=directory(target)
  source=Path(plan['service_plan']['code'])/'runtime/postgresql'
  for relative,pin in plan['postgresql_files'].items():
   self._permit(plan,'COPY_POSTGRES_BOOTSTRAP_MEMBER');destination=local(target/relative)
   for parent in reversed(destination.parents):
    if parent==target or target not in parent.parents:continue
    if parent not in self.roots:parent.mkdir(exist_ok=False);self.roots[parent]=directory(parent)
    else:need(directory(parent)==self.roots[parent])
   need(lab_release.hash_file(source/relative,copy_to=destination)==pin);self.copies[destination]=stamp(destination)
 def _verify_bootstrap(self,plan):
  for path,identity in self.copies.items():
   need(stamp(path)==identity,'POSTGRES_IDENTITY_REJECTED');relative=path.relative_to(Path(plan['data_root'])/'bootstrap-runtime').as_posix();need(lab_release.hash_file(path)==plan['postgresql_files'][relative])
 def _cleanup_bootstrap(self,plan):
  target=local(Path(plan['data_root'])/'bootstrap-runtime')
  for path,identity in self.copies.items():
   need(stamp(path)==identity,'POSTGRES_IDENTITY_REJECTED');relative=path.relative_to(target).as_posix();need(lab_release.hash_file(path)==plan['postgresql_files'][relative])
  # Do not delete an unrecorded addition, replacement or redirected directory.
  actual={local(Path(parent)/name) for parent,dirs,files in os.walk(target,followlinks=False) for name in files}
  expected_dirs={path for path in self.roots if path!=target and target in path.parents}
  actual_dirs={local(Path(parent)/name) for parent,dirs,files in os.walk(target,followlinks=False) for name in dirs}
  need(actual==set(self.copies) and actual_dirs==expected_dirs,'POSTGRES_IDENTITY_REJECTED')
  for path,identity in self.copies.items():need(stamp(path)==identity,'POSTGRES_IDENTITY_REJECTED');path.unlink()
  for parent,dirs,files in os.walk(target,topdown=False):
   for name in dirs:
    path=local(Path(parent)/name);path.rmdir();self.roots.pop(path,None)
  target.rmdir();self.copies.clear()
  for path in list(self.roots):
   if path==target or target in path.parents:self.roots.pop(path)
 def stop(self,plan,server):
  server.close()
  if server.launch is not None:server.launch.retire(server)

 def require_running(self,grant,record):
  grant.require_current();plan=check_plan(record['plan'])
  need(directory(plan['data_root'])==record['data_identity'] and directory(plan['cluster'])==record['cluster_identity'],'POSTGRES_IDENTITY_REJECTED')
  PostgresDataKernel().require_data(plan,recurse=False)
  for name in CONFIG_FILES:need(lab_release.hash_file(Path(plan['cluster'])/name)==record['config_files'][name],'POSTGRES_IDENTITY_REJECTED')
  return True
 def initialize(self,plan,password):
  self._permit(plan,'INITIALIZE_POSTGRES_NATIVE');self._copy_bootstrap(plan);work=local(Path(plan['data_root'])/'bootstrap');work.mkdir(exist_ok=False);self.roots[work]=directory(work)
  for name,raw in [('password.txt',(password+'\n').encode()),('pgpass.conf',('127.0.0.1:'+str(plan['port'])+':*:'+plan['bootstrap_user']+':'+password+'\n').encode())]:
   path=work/name
   with path.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
   self.secret_files[path]=stamp(path)
  child=OwnedJobProcess(plan,[self._exe(plan,'initdb',provision=True),'--pgdata='+plan['cluster'],'--username='+plan['bootstrap_user'],'--pwfile='+str(work/'password.txt'),'--auth-host=scram-sha-256','--auth-local=scram-sha-256','--encoding=UTF8','--locale=C','--no-clean'],self._env(plan,provision=True),capture=True)
  child.communicate(b'',timeout=120)
 def start(self,plan,provision=False):
  if provision:self._permit(plan,'START_PROVISION_POSTGRES_NATIVE')
  else:need(self.runtime_grant is not None);self.runtime_grant.require_current()
  with socket.socket() as probe:probe.bind(('127.0.0.1',plan['port']))
  pidfile=local(Path(plan['cluster'])/'postmaster.pid');need(not pidfile.exists(),'POSTGRES_PROCESS_REJECTED')
  argv=[self._exe(plan,'postgres',provision=provision),'-D',plan['cluster'],'-h','127.0.0.1','-p',str(plan['port']),'-c','listen_addresses=127.0.0.1','-c','unix_socket_directories=','-c','logging_collector=off','-c','log_statement=none','-c','log_min_error_statement=panic','-c','shared_preload_libraries=','-c','session_preload_libraries=','-c','local_preload_libraries=','-c','archive_mode=off','-c','archive_command=','-c','restore_command=']
  launch=_Launch(plan)
  try:
   server=OwnedJobProcess(plan,argv,self._env(plan,provision=provision),restricted=provision,launch=launch);server.owned_files={};return server
  except Exception:
   launch.poison();launch.release();raise
 def _sql(self,plan,server,sql,*,database=None,user=None,provision=False):
  if provision:self._permit(plan,'QUERY_PROVISION_POSTGRES_NATIVE')
  else:need(self.runtime_grant is not None);self.runtime_grant.require_current()
  import ctypes
  from contextlib import ExitStack
  # No libpq environment can silently choose a service/password/options file.
  need(not any(key.upper().startswith('PG') for key in os.environ),'POSTGRES_AUTH_REJECTED')
  _prove_listener(plan,server)
  user=user or plan['user'];database=database or plan['database'];passfile=Path(self._env(plan,provision=provision)['PGPASSFILE']);password=None
  if provision:need(stamp(passfile)==self.secret_files[passfile],'POSTGRES_AUTH_REJECTED')
  else:need(sha(regular(passfile,8192))==self.runtime_record['pgpass_sha256'],'POSTGRES_AUTH_REJECTED')
  for line in regular(passfile,8192).decode('ascii').splitlines():
   fields=line.split(':');need(len(fields)==5)
   if fields[:2]==['127.0.0.1',str(plan['port'])] and fields[2] in (database,'*') and fields[3]==user:password=fields[4]
  need(password is not None and re.fullmatch('[A-Za-z0-9_-]{32,128}',password),'POSTGRES_AUTH_REJECTED')
  root=Path(plan['service_plan']['code'])/'runtime/postgresql';dll_path=local(root/'bin/libpq.dll');need(lab_release.hash_file(dll_path)==plan['postgresql_files']['bin/libpq.dll'])
  connection=None
  with ExitStack() as stack:
   stack.enter_context(os.add_dll_directory(str(root/'bin')))
   # Exact DLL+its closed binary directory+System32; no ambient PATH search.
   dll=_load_libpq(dll_path)
   try:
    connection=_LibpqConnection(dll,dict(host='127.0.0.1',hostaddr='127.0.0.1',port=str(plan['port']),dbname=database,user=user,password=password,require_auth='scram-sha-256',connect_timeout='2',application_name='unified_owned_postgres',options='-c search_path=pg_catalog -c statement_timeout=5000 -c lock_timeout=3000'))
    probe="SELECT json_build_object('backend_pid',pg_backend_pid(),'database',current_database(),'user',current_user,'data_directory',current_setting('data_directory'),'port',current_setting('port')::int,'system_identifier',(pg_control_system()).system_identifier::text,'version_num',current_setting('server_version_num')::int);"
    identity=json.loads(connection.query(probe));need(set(identity)=={'backend_pid','database','user','data_directory','port','system_identifier','version_num'})
    need(identity['database']==database and identity['user']==user and local(identity['data_directory'])==Path(plan['cluster']) and identity['port']==plan['port'] and type(identity['version_num']) is int and 180000<=identity['version_num']<190000,'POSTGRES_IDENTITY_REJECTED')
    _job_process_identity(server,identity['backend_pid']);_prove_listener(plan,server)
    result=connection.query(sql);_prove_listener(plan,server);return result
   finally:
    if connection is not None:connection.close()

 def configure(self,plan,server,password):
  self._permit(plan,'CONFIGURE_POSTGRES_NATIVE');deadline=time.monotonic()+20
  while True:
   need(server.alive(),'POSTGRES_PROCESS_REJECTED')
   try:self._sql(plan,server,'SELECT 1;\n',database='postgres',user=plan['bootstrap_user'],provision=True);break
   except PostgresBlocked:
    need(time.monotonic()<deadline,'POSTGRES_NOT_READY');time.sleep(.1)
  self._sql(plan,server,"CREATE ROLE "+plan['user']+" LOGIN PASSWORD '"+password+"' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;",database='postgres',user=plan['bootstrap_user'],provision=True)
  self._sql(plan,server,'CREATE DATABASE '+plan['database']+' OWNER '+plan['user']+';',database='postgres',user=plan['bootstrap_user'],provision=True)
  self._sql(plan,server,'GRANT pg_read_all_settings TO '+plan['user']+';',database='postgres',user=plan['bootstrap_user'],provision=True)
  self._sql(plan,server,'GRANT EXECUTE ON FUNCTION pg_catalog.pg_control_system() TO '+plan['user']+';',user=plan['bootstrap_user'],provision=True)
  path=Path(plan['data_root'])/'bootstrap/pgpass.conf';need(stamp(path)==self.secret_files[path]);bootstrap=regular(path,8192);app=('127.0.0.1:'+str(plan['port'])+':'+plan['database']+':'+plan['user']+':'+password+'\n').encode();path.write_bytes(bootstrap+app);self.secret_files[path]=stamp(path)
  # Real app login/permissions/data/system identity must succeed before the
  # bootstrap role is disabled. Every SQL session is fenced to our own Job.
  before=self.ready(plan,server,provision=True);validate_sql(plan,before,bootstrap_login=True)
  self._sql(plan,server,'ALTER ROLE '+plan['bootstrap_user']+' NOLOGIN;',database='postgres',user=plan['bootstrap_user'],provision=True)

 def ready(self,plan,server,provision=False):
  need(server.alive(),'POSTGRES_PROCESS_REJECTED')
  pidpath=local(Path(plan['cluster'])/'postmaster.pid')
  if not pidpath.exists() or pidpath.stat().st_size==0:raise PostgresStartPending()
  pidfile=regular(pidpath,8192);need(pidfile.splitlines()[0]==str(server.proc.pid).encode(),'POSTGRES_PROCESS_REJECTED')
  sql="SELECT json_build_object('version_num',current_setting('server_version_num')::int,'database',current_database(),'user',current_user,'data_directory',current_setting('data_directory'),'port',current_setting('port')::int,'system_identifier',(pg_control_system()).system_identifier::text,'bootstrap_login',(SELECT rolcanlogin FROM pg_roles WHERE rolname='"+plan['bootstrap_user']+"'),'superuser',rolsuper,'createdb',rolcreatedb,'createrole',rolcreaterole,'replication',rolreplication,'bypassrls',rolbypassrls) FROM pg_roles WHERE rolname=current_user;\n"
  proof=json.loads(self._sql(plan,server,sql,provision=provision));need(server.alive(),'POSTGRES_PROCESS_REJECTED')
  server.owned_files={name:(stamp(Path(plan['cluster'])/name),regular(Path(plan['cluster'])/name,8192)) for name in ('postmaster.pid','postmaster.opts')}
  return proof
 def seal(self,plan,password):
  self._permit(plan,'SEAL_POSTGRES_NATIVE')
  temporary=str(Path(plan['data_root'])/'bootstrap-runtime').replace('\\','/').casefold()
  for name in ('postgresql.conf','postgresql.auto.conf','pg_hba.conf','pg_ident.conf'):
   text=regular(Path(plan['cluster'])/name).decode('utf8').replace('\\','/').casefold();need(temporary not in text)
  self._cleanup_bootstrap(plan)
  for path,identity in self.secret_files.items():need(stamp(path)==identity,'POSTGRES_IDENTITY_REJECTED')
  for path in self.secret_files:path.unlink() # Only exact files this broker created.
  self.secret_files.clear()
  target=local(Path(plan['namespace'])/'pgpass.conf')
  with target.open('xb') as stream:stream.write(('127.0.0.1:'+str(plan['port'])+':'+plan['database']+':'+plan['user']+':'+password+'\n').encode());stream.flush();os.fsync(stream.fileno())
  self._ps(plan,'SEAL');PostgresDataKernel().require_data(plan,sealing=True)
 def publish(self,plan,raw):
  self._permit(plan,'PUBLISH_POSTGRES_RECEIPT_NATIVE');path=local(Path(plan['namespace'])/'receipt.json')
  with path.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
  self._ps(plan,'PUBLISH');WindowsActivationKernel().require_readonly(path,plan['service_plan']['service_sid'],Path(plan['namespace']))
 def admit_runtime(self,grant,record):
  from .service_bootstrap import read_protected_activation
  actual=read_protected_activation(record['plan']['service_plan']['root']);need(actual.descriptor==grant.descriptor,'POSTGRES_IDENTITY_REJECTED')
  anchor=Path(actual.descriptor['service_plan']['root'])/'postgres-ownership';raw,_=read_file(anchor/'receipt.json',262144,actual._kernel,actual.service_sid,anchor)
  need(sha(raw)==actual.descriptor['qualification_refs']['database_evidence_sha256'] and parse(raw)==record,'POSTGRES_IDENTITY_REJECTED')
  self.runtime_grant=actual;self.runtime_record=copy.deepcopy(record)
  plan=check_plan(record['plan']);need(directory(plan['data_root'])==record['data_identity'] and directory(plan['cluster'])==record['cluster_identity'],'POSTGRES_IDENTITY_REJECTED')
  report=lab_release.verify_capsule(plan['service_plan']['code'],plan['service_plan']['manifest_sha256']);self.manifest=report['manifest']
  kernel=WindowsActivationKernel();root=Path(plan['service_plan']['code'])
  for name in [*self.manifest['directories'],*self.manifest['files'],'lab-release.json']:kernel.require_readonly(root/name,grant.service_sid,root)
  lab_runtime.verify_sources(root,self.manifest,owner_admitted_root=root);PostgresDataKernel().require_data(plan)
  raw,_=read_file(Path(plan['namespace'])/'pgpass.conf',8192,kernel,grant.service_sid,Path(plan['namespace']));need(sha(raw)==record['pgpass_sha256'],'POSTGRES_AUTH_REJECTED')
  for name in CONFIG_FILES:need(lab_release.hash_file(Path(plan['cluster'])/name)==record['config_files'][name],'POSTGRES_IDENTITY_REJECTED')
