"""Stdlib-only protected activation reader; never imports application/state code.

Kernel-verified protected-owner admission is not publisher authentication, host
attestation, runtime readiness or distributed consensus. Full capsule/source/auth
validation belongs to the existing runtime admission path before side effects.
"""
import copy,ctypes,hashlib,json,os,re,stat
from pathlib import Path

POINTER_SCHEMA='unified.service-activation-pointer.v1'
DESCRIPTOR_SCHEMA='unified.service-activation.v1'
REVOKED_SCHEMA='unified.service-activation-revoked.v1'

ERROR_CODES=frozenset(('ACTIVATION_AMBIENT_IMPORT_REJECTED','ACTIVATION_CODE_REJECTED','ACTIVATION_DATABASE_GATE_UNAVAILABLE','ACTIVATION_RUNTIME_REJECTED',)+('ACTIVATION_ACL_REJECTED', 'ACTIVATION_AUTH_REJECTED', 'ACTIVATION_CONCURRENT_UPDATE', 'ACTIVATION_ELEVATED_WRITER_REQUIRED', 'ACTIVATION_FILE_REJECTED', 'ACTIVATION_HOST_REJECTED', 'ACTIVATION_IDENTITY_CHANGED', 'ACTIVATION_KERNEL_REJECTED', 'ACTIVATION_LINK_REJECTED', 'ACTIVATION_NAMESPACE_REJECTED', 'ACTIVATION_NATIVE_REJECTED', 'ACTIVATION_OWNER_PHASE_REJECTED', 'ACTIVATION_OWNER_PHASE_REQUIRED', 'ACTIVATION_PATH_REJECTED', 'ACTIVATION_PLATFORM_REJECTED', 'ACTIVATION_QUALIFICATION_REJECTED', 'ACTIVATION_QUALIFICATION_REQUIRED', 'ACTIVATION_REJECTED', 'ACTIVATION_REVISION_CHANGED', 'ACTIVATION_REVOKED', 'ACTIVATION_SERVICE_TOKEN_REQUIRED', 'ACTIVATION_SIZE_REJECTED', 'ACTIVATION_UNAVAILABLE'))

class ActivationBlocked(ValueError):
 def __init__(self,code='ACTIVATION_REJECTED'):
  self.code=code if type(code) is str and code in ERROR_CODES else 'ACTIVATION_REJECTED'
  super().__init__(self.code)

def need(ok,code='ACTIVATION_REJECTED'):
 if not ok:raise ActivationBlocked(code)

def digest(value):need(type(value) is str and re.fullmatch('[a-f0-9]{64}',value) is not None)
def label(value):need(type(value) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,63}',value) is not None)
def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()

def local(path):
 path=Path(path);raw=str(path)
 need(path.is_absolute() and not raw.startswith(('//',chr(92))) and '..' not in path.parts,'ACTIVATION_PATH_REJECTED')
 if os.name=='nt':
  api=ctypes.WinDLL('kernel32',use_last_error=True).GetDriveTypeW;api.argtypes=[ctypes.c_wchar_p];api.restype=ctypes.c_uint
  need(re.fullmatch(r'[A-Za-z]:[\\/].*',raw) is not None and api(raw[:3])==3,'ACTIVATION_PATH_REJECTED')
 for part in (*reversed(path.parents),path):
  try:info=part.lstat()
  except FileNotFoundError:continue
  need(not stat.S_ISLNK(info.st_mode) and not getattr(info,'st_file_attributes',0)&1024,'ACTIVATION_LINK_REJECTED')
 need(path.resolve(strict=False)==path,'ACTIVATION_PATH_REJECTED')
 return path

def stamp(path):
 info=local(path).lstat();need(stat.S_ISREG(info.st_mode) and info.st_nlink==1,'ACTIVATION_FILE_REJECTED')
 return (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_nlink)

def read_file(path,limit,kernel,sid,anchor):
 path=local(path);kernel.require_readonly(path,sid,anchor);before=stamp(path);need(0<before[2]<=limit,'ACTIVATION_SIZE_REJECTED')
 with path.open('rb') as stream:
  info=os.fstat(stream.fileno());need((info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_nlink)==before)
  raw=stream.read(limit+1);after=os.fstat(stream.fileno());need((after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_nlink)==before)
 need(stamp(path)==before and len(raw)==before[2]);return raw,before

def parse(raw):
 def unique(pairs):
  result={}
  for key,value in pairs:need(key not in result);result[key]=value
  return result
 value=json.loads(raw,object_pairs_hook=unique,parse_constant=lambda _:need(False));need(canonical(value)==raw);return value

class WindowsActivationKernel:
 """Read-only documented Win32 token/owner/DACL checks; no elevation or ACL writes."""
 def __init__(self):
  need(os.name=='nt','ACTIVATION_PLATFORM_REJECTED')
  self.kernel=ctypes.WinDLL('kernel32',use_last_error=True);self.advapi=ctypes.WinDLL('advapi32',use_last_error=True)
  self.kernel.LocalFree.argtypes=[ctypes.c_void_p];self.kernel.LocalFree.restype=ctypes.c_void_p
  self.kernel.GetCurrentProcess.restype=ctypes.c_void_p;self.kernel.CloseHandle.argtypes=[ctypes.c_void_p]
  self.advapi.ConvertSidToStringSidW.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p)];self.advapi.ConvertSidToStringSidW.restype=ctypes.c_int
  self.advapi.OpenProcessToken.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.POINTER(ctypes.c_void_p)];self.advapi.OpenProcessToken.restype=ctypes.c_int
  self.advapi.GetTokenInformation.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_void_p,ctypes.c_uint,ctypes.POINTER(ctypes.c_uint)];self.advapi.GetTokenInformation.restype=ctypes.c_int
  self.advapi.GetNamedSecurityInfoW.argtypes=[ctypes.c_wchar_p,ctypes.c_uint,ctypes.c_uint,ctypes.POINTER(ctypes.c_void_p),ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p),ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p)];self.advapi.GetNamedSecurityInfoW.restype=ctypes.c_uint
  self.advapi.GetSecurityDescriptorControl.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ushort),ctypes.POINTER(ctypes.c_uint)];self.advapi.GetSecurityDescriptorControl.restype=ctypes.c_int
  self.advapi.GetAce.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.POINTER(ctypes.c_void_p)];self.advapi.GetAce.restype=ctypes.c_int
 def _sid(self,pointer):
  text=ctypes.c_void_p();need(self.advapi.ConvertSidToStringSidW(pointer,ctypes.byref(text))!=0,'ACTIVATION_KERNEL_REJECTED')
  try:return ctypes.wstring_at(text)
  finally:self.kernel.LocalFree(text)
 def identity(self):
  class SID_AND_ATTRIBUTES(ctypes.Structure):_fields_=[('sid',ctypes.c_void_p),('attributes',ctypes.c_uint)]
  class GROUPS(ctypes.Structure):_fields_=[('count',ctypes.c_uint),('groups',SID_AND_ATTRIBUTES*1)]
  token=ctypes.c_void_p();need(self.advapi.OpenProcessToken(self.kernel.GetCurrentProcess(),8,ctypes.byref(token))!=0,'ACTIVATION_KERNEL_REJECTED')
  try:
   def information(kind):
    size=ctypes.c_uint();self.advapi.GetTokenInformation(token,kind,None,0,ctypes.byref(size));need(0<size.value<=1048576)
    buffer=ctypes.create_string_buffer(size.value);need(self.advapi.GetTokenInformation(token,kind,buffer,len(buffer),ctypes.byref(size))!=0);return buffer
   user=information(1);user_sid=self._sid(SID_AND_ATTRIBUTES.from_buffer(user).sid)
   groups=information(2);count=ctypes.c_uint.from_buffer(groups).value;need(count<=4096 and GROUPS.groups.offset+count*ctypes.sizeof(SID_AND_ATTRIBUTES)<=len(groups))
   services=[]
   for index in range(count):
    group=SID_AND_ATTRIBUTES.from_buffer(groups,GROUPS.groups.offset+index*ctypes.sizeof(SID_AND_ATTRIBUTES));sid=self._sid(group.sid)
    if re.fullmatch(r'S-1-5-80-(?:[0-9]+-){4}[0-9]+',sid) and group.attributes&4 and not group.attributes&16:services.append(sid)
   need(user_sid=='S-1-5-19' and len(services)==1,'ACTIVATION_SERVICE_TOKEN_REQUIRED')
   function=self.kernel.GetComputerNameW;function.argtypes=[ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_uint)];function.restype=ctypes.c_int
   host=ctypes.create_unicode_buffer(256);size=ctypes.c_uint(len(host));need(function(host,ctypes.byref(size))!=0)
   return {'user_sid':user_sid,'service_sid':services[0],'computer_name':host.value}
  finally:self.kernel.CloseHandle(token)
 def _security(self,path):
  owner=ctypes.c_void_p();acl=ctypes.c_void_p();descriptor=ctypes.c_void_p()
  need(self.advapi.GetNamedSecurityInfoW(str(path),1,5,ctypes.byref(owner),None,ctypes.byref(acl),None,ctypes.byref(descriptor))==0 and acl.value,'ACTIVATION_ACL_REJECTED')
  try:
   class ACL(ctypes.Structure):_fields_=[('revision',ctypes.c_ubyte),('reserved',ctypes.c_ubyte),('size',ctypes.c_ushort),('count',ctypes.c_ushort),('reserved2',ctypes.c_ushort)]
   header=ctypes.cast(acl,ctypes.POINTER(ACL)).contents;need(8<=header.size<=65535 and header.count==3,'ACTIVATION_ACL_REJECTED')
   control=ctypes.c_ushort();revision=ctypes.c_uint();need(self.advapi.GetSecurityDescriptorControl(descriptor,ctypes.byref(control),ctypes.byref(revision))!=0)
   rows=[]
   for index in range(header.count):
    ace=ctypes.c_void_p();need(self.advapi.GetAce(acl,index,ctypes.byref(ace))!=0)
    kind=ctypes.c_ubyte.from_address(ace.value).value;flags=ctypes.c_ubyte.from_address(ace.value+1).value;size=ctypes.c_ushort.from_address(ace.value+2).value
    need(kind==0 and 12<=size<=header.size,'ACTIVATION_ACL_REJECTED')
    rows.append((self._sid(ace.value+8),ctypes.c_uint.from_address(ace.value+4).value,flags))
   return self._sid(owner),bool(control.value&0x1000),rows
  finally:self.kernel.LocalFree(descriptor)
 def require_readonly(self,path,sid,anchor):
  path=local(path);anchor=local(anchor);need(path==anchor or anchor in path.parents or path==anchor.parent)
  paths=[anchor.parent,anchor]
  if path!=anchor.parent:
   relative=path.relative_to(anchor);cursor=anchor
   for part in relative.parts:cursor=cursor/part;paths.append(cursor)
  for item in dict.fromkeys(paths):
   owner,protected,rows=self._security(item);need(owner in ('S-1-5-18','S-1-5-32-544'),'ACTIVATION_ACL_REJECTED')
   need(protected==(item in (anchor.parent,anchor)),'ACTIVATION_ACL_REJECTED')
   expected={'S-1-5-18':0x1f01ff,'S-1-5-32-544':0x1f01ff,sid:0x1200a9};seen=set()
   for principal,rights,flags in rows:
    need(principal in expected and principal not in seen and rights==expected[principal],'ACTIVATION_ACL_REJECTED');seen.add(principal)
    expected_flags=(0 if item.is_file() else 3)|(16 if item not in (anchor.parent,anchor) else 0)
    need(flags==expected_flags,'ACTIVATION_ACL_REJECTED')
  return True

class ProtectedActivation:
 def __init__(self,root,kernel,identity,descriptor,profile,paths,identities,pointer_hash):
  self._root=root;self._kernel=kernel;self._identity=identity;self._descriptor=descriptor;self._profile=profile;self._paths=paths;self._identities=identities;self._pointer_hash=pointer_hash
 @property
 def descriptor(self):return copy.deepcopy(self._descriptor)
 @property
 def profile(self):return copy.deepcopy(self._profile)
 @property
 def auth_path(self):return self._paths['auth']
 @property
 def code_root(self):return Path(self._descriptor['service_plan']['code'])
 @property
 def manifest_sha256(self):return self._descriptor['service_plan']['manifest_sha256']
 @property
 def service_sid(self):return self._identity['service_sid']
 @property
 def computer_name(self):return self._identity['computer_name']
 def require_current(self):
  try:
   need(self._kernel.identity()==self._identity,'ACTIVATION_IDENTITY_CHANGED')
   raw,identity=read_file(self._paths['pointer'],8192,self._kernel,self.service_sid,self._root/'activation')
   need(identity==self._identities['pointer'] and hashlib.sha256(raw).hexdigest()==self._pointer_hash,'ACTIVATION_REVOKED')
   for name in ('descriptor','profile','auth'):
    self._kernel.require_readonly(self._paths[name],self.service_sid,self._root/'activation');need(stamp(self._paths[name])==self._identities[name],'ACTIVATION_REVISION_CHANGED')
   return True
  except ActivationBlocked:raise
  except Exception:raise ActivationBlocked('ACTIVATION_UNAVAILABLE') from None

def read_protected_activation(service_root,*,kernel=None):
 try:
  root=local(service_root);kernel=WindowsActivationKernel() if kernel is None else kernel;identity=kernel.identity()
  need(type(identity) is dict and set(identity)=={'computer_name','user_sid','service_sid'} and identity['user_sid']=='S-1-5-19','ACTIVATION_SERVICE_TOKEN_REQUIRED')
  sid=identity['service_sid'];need(re.fullmatch(r'S-1-5-80-(?:[0-9]+-){4}[0-9]+',sid) is not None)
  anchor=root/'activation';paths={'pointer':anchor/'current.json'};identities={}
  raw,identities['pointer']=read_file(paths['pointer'],8192,kernel,sid,anchor);pointer_hash=hashlib.sha256(raw).hexdigest();pointer=parse(raw)
  need(type(pointer) is dict and set(pointer)=={'schema','revision_id','descriptor_sha256'} and pointer['schema']==POINTER_SCHEMA,'ACTIVATION_REVOKED');label(pointer['revision_id']);digest(pointer['descriptor_sha256'])
  revision=anchor/'revisions'/pointer['revision_id'];paths.update(descriptor=revision/'descriptor.json',profile=revision/'profile.json',auth=revision/'credentials/auth.json')
  raw,identities['descriptor']=read_file(paths['descriptor'],262144,kernel,sid,anchor);need(hashlib.sha256(raw).hexdigest()==pointer['descriptor_sha256']);descriptor=parse(raw)
  need(type(descriptor) is dict and set(descriptor)=={'schema','activation_plan_sha256','revision_id','service_plan','resource_receipt_sha256','profile_sha256','auth_sha256','qualification_refs'} and descriptor['schema']==DESCRIPTOR_SCHEMA and descriptor['revision_id']==pointer['revision_id'])
  for field in ('activation_plan_sha256','resource_receipt_sha256','profile_sha256','auth_sha256'):digest(descriptor[field])
  plan=descriptor['service_plan'];need(type(plan) is dict and plan['service_sid']==sid and plan['computer_name'].casefold()==identity['computer_name'].casefold(),'ACTIVATION_IDENTITY_CHANGED')
  need(plan['root']==str(root) and plan['code']==str(root/'code') and plan['state']==str(root/'state') and plan['role'] in ('CONTROL','WORKER','SINGLE_PC'))
  digest(plan['manifest_sha256']);refs=descriptor['qualification_refs'];need(type(refs) is dict and set(refs)=={'phase_id','source_evidence_sha256','capacity_evidence_sha256','database_evidence_sha256'});label(refs['phase_id'])
  for field in ('source_evidence_sha256','capacity_evidence_sha256'):digest(refs[field])
  if plan['role']=='WORKER':need(refs['database_evidence_sha256'] is None)
  else:digest(refs['database_evidence_sha256'])
  raw,identities['profile']=read_file(paths['profile'],4*1024*1024,kernel,sid,anchor);need(hashlib.sha256(raw).hexdigest()==descriptor['profile_sha256']);profile=parse(raw)
  raw,identities['auth']=read_file(paths['auth'],8192,kernel,sid,anchor);need(hashlib.sha256(raw).hexdigest()==descriptor['auth_sha256'])
  config=profile['runtime_config'];context=profile['offline_context']
  need(context=={'scope':'OFFLINE_VALIDATION_ONLY','role':plan['role'],'node_id':plan['node_id'],'computer_name':plan['computer_name'],'credential_root':str(revision/'credentials')})
  need(config['node_id']==plan['node_id'] and config['state_root']==plan['state'] and config['release_sha256']==plan['manifest_sha256'])
  need(config['programs']['grid']['env']['GRID_LAB_AUTH_PATH']==str(paths['auth']) and config['programs']['grid']['env']['GRID_LAB_AUTH_SHA256']==descriptor['auth_sha256'])
  result=ProtectedActivation(root,kernel,identity,descriptor,profile,paths,identities,pointer_hash);result.require_current();return result
 except ActivationBlocked:raise
 except Exception:raise ActivationBlocked('ACTIVATION_UNAVAILABLE') from None


# Only these already pinned source bytes may be imported to obtain the existing
# capsule verifier. This is a small import admission, not a second verifier.
VERIFIER_IMPORTS=('__init__.py','module_catalog.py','runtime_process.py','lab_release.py')

def _import_verifier(grant,manifest):
 import importlib,importlib.abc,importlib.util,sys
 source=grant.code_root/'sources/unified-system'
 need(not any(name=='unified_system' or name.startswith('unified_system.') or name=='integration' or name.startswith('integration.') for name in sys.modules),'ACTIVATION_AMBIENT_IMPORT_REJECTED')
 admitted={'sources/unified-system/unified_system/'+name for name in VERIFIER_IMPORTS};runtime_enabled=False
 class OwnedSourceLoader(importlib.abc.MetaPathFinder,importlib.abc.Loader):
  def find_spec(self,fullname,path=None,target=None):
   if fullname.split('.')[0] not in ('unified_system','integration'):return None
   relative='sources/unified-system/'+fullname.replace('.','/')
   if fullname=='integration' and runtime_enabled and relative in manifest['directories']:
    grant._kernel.require_readonly(grant.code_root/relative,grant.service_sid,grant.code_root)
    spec=importlib.machinery.ModuleSpec(fullname,None,is_package=True);spec.submodule_search_locations=[str(grant.code_root/relative)];return spec
   package=relative+'/__init__.py' in manifest['files'];relative+=('/__init__.py' if package else '.py')
   need(relative in admitted,'ACTIVATION_CODE_REJECTED')
   return importlib.util.spec_from_loader(fullname,self,origin=str(grant.code_root/relative),is_package=package)
  def create_module(self,spec):return None
  def exec_module(self,module):
   name=module.__spec__.name;relative='sources/unified-system/'+name.replace('.','/')
   package=module.__spec__.submodule_search_locations is not None;relative+=('/__init__.py' if package else '.py')
   pin=manifest['files'][relative];need(type(pin) is dict and set(pin)=={'bytes','sha256'} and type(pin['bytes']) is int and 0<pin['bytes']<=1048576)
   digest(pin['sha256']);raw,_=read_file(grant.code_root/relative,1048576,grant._kernel,grant.service_sid,grant.code_root)
   need(len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],'ACTIVATION_CODE_REJECTED')
   module.__file__=str(grant.code_root/relative)
   if package:module.__path__=[str(Path(module.__file__).parent)]
   # Compile admitted source bytes directly: -B alone does not prevent reads
   # of a candidate's forged/stale bytecode cache.
   exec(compile(raw,module.__file__,'exec'),module.__dict__)
  def admit_runtime(self):
   nonlocal runtime_enabled
   runtime_enabled=True
   admitted.update(name for name in manifest['files'] if name.startswith(('sources/unified-system/unified_system/','sources/unified-system/integration/')) and name.endswith('.py'))
 loader=OwnedSourceLoader();sys.meta_path.insert(0,loader)
 try:verifier=importlib.import_module('unified_system.lab_release')
 except Exception:
  sys.meta_path.remove(loader);raise
 return verifier,loader

def _admit_capsule(grant):
 grant.require_current();root=grant.code_root
 raw,_=read_file(root/'lab-release.json',32*1024*1024,grant._kernel,grant.service_sid,root)
 need(hashlib.sha256(raw).hexdigest()==grant.manifest_sha256,'ACTIVATION_CODE_REJECTED');manifest=parse(raw)
 verifier,loader=_import_verifier(grant,manifest)
 report=verifier.verify_capsule(root,grant.manifest_sha256);manifest=report['manifest']
 # Per-service read-only code policy covers every closed file/directory, not
 # just the entry or .git root. No host-admin containment is claimed.
 for relative in [*manifest['directories'],*manifest['files'],'lab-release.json']:
  grant._kernel.require_readonly(root/relative,grant.service_sid,root)
 grant.require_current();loader.admit_runtime();return report

def _runtime_admission(grant,report):
 from unified_system import lab_runtime
 config=grant.profile['runtime_config'];context=grant.profile['offline_context'];manifest=report['manifest']
 config=lab_runtime.validate_config(config,manifest,grant.code_root,hostname=grant.computer_name,offline_context=context)
 lab_runtime.verify_sources(grant.code_root,manifest,owner_admitted_root=grant.code_root)
 auth=lab_runtime.read_grid_auth(grant.auth_path,grant.descriptor['auth_sha256'],node_id=config['node_id'],release_id=config['release_id'],source_commit=manifest['sources']['grid']['commit'],role_context=context)
 grant.require_current();return config,auth

def _repeat_admission(grant,verifier):
 grant.require_current();report=verifier.verify_capsule(grant.code_root,grant.manifest_sha256)
 for relative in [*report['manifest']['directories'],*report['manifest']['files'],'lab-release.json']:
  grant._kernel.require_readonly(grant.code_root/relative,grant.service_sid,grant.code_root)
 return _runtime_admission(grant,report)

def run_protected_runtime(grant,*,stop_event=None):
 """Existing runtime actuator after protected full admission; no readiness grant.

 CONTROL/SINGLE_PC start only the kernel/receipt-owned PostgreSQL boundary
 before constructing the existing runtime. WORKER readiness still requires functional
 coordinator/module evidence from the existing runtime, never this entry.
 """
 database=None
 try:
  grant.require_current()
  report=_admit_capsule(grant);config,auth=_runtime_admission(grant,report)
  if grant.descriptor['service_plan']['role'] in ('CONTROL','SINGLE_PC'):
   from unified_system.service_postgres import read_postgres_ownership
   database=read_postgres_ownership(grant)
  def continuation():
   grant.require_current()
   if database is not None:need(database.require_current() is True,'ACTIVATION_DATABASE_GATE_UNAVAILABLE')
   return True
  from unified_system import lab_release,lab_runtime
  from unified_system.module_catalog import MODULE_IDS
  import threading,signal
  def authorize(action,module):
   nonlocal auth
   if action!='start' or module not in MODULE_IDS:return False
   try:
    current,current_auth=_repeat_admission(grant,lab_release)
    need(current==config,'ACTIVATION_REVISION_CHANGED')
    if database is not None:
     # Re-read protected receipt and repeat full database admission for every
     # child start; the already owned live job remains the process authority.
     read_postgres_ownership(grant);need(database.require_current() is True,'ACTIVATION_DATABASE_GATE_UNAVAILABLE')
    auth=current_auth;return True
   except Exception:return False
  def environment(module):
   result=lab_runtime.child_environment()
   if module=='grid':result.update(auth)
   return result
  # All filesystem writes and runtime imports occur after the gates above.
  from unified_system.lab_privileges import remove_lab_write_bypass_privileges
  remove_lab_write_bypass_privileges();grant.require_current()
  if database is not None:database.start()
  for program in config['programs'].values():
   for key,value in program['env'].items():
    if key.upper() in ('TEMP','TMP','USERPROFILE','HOME','APPDATA','LOCALAPPDATA','PROGRAMDATA','PROGRAMFILES','ML_ARTIFACT_ROOT','ARCHIVE_ROOT','STRATEGY_CACHE_DIR','GRID_CONTROL_SNAPSHOTS'):
     target=local(value);need(Path(config['state_root'])==target or Path(config['state_root']) in target.parents);grant.require_current();target.mkdir(parents=True,exist_ok=True)
  from unified_system.service_module_runtime import protected_programs
  effective=protected_programs(config,grant,report['manifest'])
  if grant.profile.get('data_first') is not None and grant.descriptor['service_plan']['role']=='WORKER':
   from unified_system.data_first_service import worker_program
   effective=worker_program(effective,grant,report['manifest'])
  grant.require_current();runtime=lab_runtime.make_runtime(effective,authorize,child_environment=environment)
  stop=threading.Event() if stop_event is None else stop_event;previous={}
  try:
   if threading.current_thread() is threading.main_thread():
    for sig in (signal.SIGINT,signal.SIGTERM):previous[sig]=signal.signal(sig,lambda *_:stop.set())
   lab_runtime.run_runtime(config,runtime,stop_event=stop,continuation=continuation)
  finally:
   for sig,handler in previous.items():signal.signal(sig,handler)
  return 0
 except ActivationBlocked:raise
 except Exception:raise ActivationBlocked('ACTIVATION_RUNTIME_REJECTED') from None
 finally:
  if database is not None:
   try:database.close()
   except Exception:raise ActivationBlocked('ACTIVATION_DATABASE_GATE_UNAVAILABLE') from None


def run_protected_data_first(grant,*,worker=False):
 """One existing Grid-assigned research child; no database/controller startup.

 Fixed raw mode independently repeats kernel, capsule, source and workspace
 admission. Serialized job input never supplies construction authority.
 """
 try:
  need(grant.require_current() is True)
  report=_admit_capsule(grant);config,_auth=_runtime_admission(grant,report)
  from unified_system.data_first_policy import validate_data_first_grant
  cap=validate_data_first_grant(grant.profile.get('data_first'),report['manifest'])
  from unified_system.lab_privileges import remove_lab_write_bypass_privileges
  remove_lab_write_bypass_privileges();need(grant.require_current() is True)
  from unified_system.data_first_service import serve_research
  if worker:
   from unified_system.data_first_service import serve_worker
   return serve_worker(grant,config,report['manifest'],cap)
  return serve_research(grant,config,report['manifest'],cap)
 except ActivationBlocked:raise
 except Exception:raise ActivationBlocked('ACTIVATION_RUNTIME_REJECTED') from None


def run_protected_module(grant,module_id,*,verify_only=False):
 """Fixed Python module dispatch with independent live kernel readmission."""
 try:
  need(module_id in ('meta_analyse','strattester','terminan') and (not verify_only or module_id=='strattester'))
  need(grant.require_current() is True)
  report=_admit_capsule(grant);config,_auth=_runtime_admission(grant,report)
  from unified_system.lab_privileges import remove_lab_write_bypass_privileges
  remove_lab_write_bypass_privileges();need(grant.require_current() is True)
  from unified_system.service_module_runtime import serve_module
  return serve_module(grant,config,report['manifest'],module_id,verify_only=verify_only)
 except ActivationBlocked:raise
 except Exception:raise ActivationBlocked('ACTIVATION_RUNTIME_REJECTED') from None
