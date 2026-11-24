"""Owner-phase-bound SCM start/stop over an existing receipt-owned service.

SCM acceptance/state is never application readiness or installation proof. No
service adoption, creation, deletion, dependent-service control, process killing
or automatic rollback. A corrupt capsule blocks STOP too; separate owner manual
recovery is required. Private service roots and no hostile administrator are
preconditions, not claims of attestation or cross-process atomic configuration.
The 1..60 second deadline bounds post-request polling. Documented synchronous
SCM RPC calls and the bounded readonly helper have their own OS/helper latency;
this adapter does not claim a hard whole-operation deadline or cancel SCM work.
"""
import base64,copy,ctypes,hashlib,json,os,time
from contextlib import contextmanager
from pathlib import Path
from . import installation_service as service,lab_release
from .contracts import canonical,seal
from .installation_progress import identifier

SCHEMA='unified.owned-service-actuation.v1'
FIELDS=frozenset(('schema','action','phase_id','computer_name','service_name','service_sid','service_plan_sha256','service_receipt_sha256','actuator_sha256','timeout_seconds','plan_sha256'))
CODES=frozenset(('SERVICE_ACTUATION_REJECTED','SERVICE_ACTUATION_OWNER_REQUIRED','SERVICE_ACTUATION_IDENTITY_REJECTED','SERVICE_ACTUATION_BUSY','SERVICE_ACTUATION_UNAVAILABLE','SERVICE_ACTUATION_UNCERTAIN'))
class ActuationBlocked(ValueError):
 def __init__(self,code='SERVICE_ACTUATION_REJECTED',*,effect_accepted=False,effect_attempted=False):
  self.code=code if code in CODES else 'SERVICE_ACTUATION_REJECTED';self.effect_accepted=effect_accepted is True;self.effect_attempted=effect_attempted is True or self.effect_accepted;super().__init__(self.code)
def need(value,code='SERVICE_ACTUATION_REJECTED'):
 if not value:raise ActuationBlocked(code)
def source_pin():
 path=lab_release.regular(Path(__file__));need(0<path.stat().st_size<=1048576);return lab_release.hash_file(path)['sha256']
def service_actuation_plan(resource,action,phase_id,*,timeout_seconds=30):
 try:
  need(type(action) is str and action in ('START','STOP'));identifier(phase_id)
  need(type(timeout_seconds) is int and 1<=timeout_seconds<=60)
  record=resource.recorded();p=record['plan']
  body=dict(schema=SCHEMA,action=action,phase_id=phase_id,computer_name=p['computer_name'],service_name=p['service_name'],service_sid=p['service_sid'],service_plan_sha256=p['plan_sha256'],service_receipt_sha256=record['receipt_sha256'],actuator_sha256=source_pin(),timeout_seconds=timeout_seconds)
  return dict(body,plan_sha256=seal(body))
 except ActuationBlocked:raise
 except Exception:raise ActuationBlocked() from None

def check(plan,record):
 need(type(plan) is dict and set(plan)==FIELDS and plan['schema']==SCHEMA)
 need(plan['plan_sha256']==seal({k:v for k,v in plan.items() if k!='plan_sha256'}))
 expected=service_actuation_plan(_Recorded(record),plan['action'],plan['phase_id'],timeout_seconds=plan['timeout_seconds']);need(plan==expected)
 return service._check_plan(copy.deepcopy(record['plan']))
class _Recorded:
 def __init__(self,record):self.record=record
 def recorded(self):return copy.deepcopy(self.record)
def host(resource,p):need(resource.boundary.computer_name().casefold()==p['computer_name'].casefold(),'SERVICE_ACTUATION_IDENTITY_REJECTED')
def prove(p,record,proof):
 need(type(proof) is dict and type(proof.get('state')) is int and proof['state'] in (1,2,3,4),'SERVICE_ACTUATION_BUSY')
 immutable=copy.deepcopy(proof);immutable['state']=1
 need(service._proof(p,immutable)==record['proof'],'SERVICE_ACTUATION_IDENTITY_REJECTED')
 return proof['state']

def actuate_service(resource,actuation_plan,*,owner_phase=None,native=None):
 accepted=False;attempted=False
 try:
  need(callable(owner_phase),'SERVICE_ACTUATION_OWNER_REQUIRED')
  plan=copy.deepcopy(actuation_plan);record=resource.recorded();p=check(plan,record);host(resource,p)
  need(owner_phase('SERVICE_'+plan['action'],plan['plan_sha256']) is True,'SERVICE_ACTUATION_OWNER_REQUIRED')
  host(resource,p);need(resource.recorded()==record,'SERVICE_ACTUATION_IDENTITY_REJECTED');check(plan,record)
  lab_release.verify_capsule(p['code'],p['manifest_sha256'])
  native=WindowsServiceActuator() if native is None else native
  target=4 if plan['action']=='START' else 1;origin=1 if target==4 else 4
  with native.open(copy.deepcopy(p),plan['action']) as handle:
   state=prove(p,record,handle.metadata(copy.deepcopy(p)))
   need(state in (origin,target),'SERVICE_ACTUATION_BUSY')
   # The final SCM proof and native action use the exact same open handle.
   host(resource,p);need(resource.recorded()==record);check(plan,record)
   current=prove(p,record,handle.read());need(current==state,'SERVICE_ACTUATION_IDENTITY_REJECTED')
   if state!=target:
    need(owner_phase('SERVICE_'+plan['action'],plan['plan_sha256']) is True,'SERVICE_ACTUATION_OWNER_REQUIRED')
    attempted=True;handle.start() if target==4 else handle.stop();accepted=True
    deadline=time.monotonic()+plan['timeout_seconds']
    while True:
     host(resource,p);state=prove(p,record,handle.read())
     if state==target:break
     need(state==(2 if target==4 else 3),'SERVICE_ACTUATION_UNCERTAIN')
     need(time.monotonic()<deadline,'SERVICE_ACTUATION_UNCERTAIN');time.sleep(.05)
  return dict(schema=SCHEMA,phase_id=plan['phase_id'],actuation_plan_sha256=plan['plan_sha256'],service_receipt_sha256=record['receipt_sha256'],computer_name=p['computer_name'],service_name=p['service_name'],service_sid=p['service_sid'],action=plan['action'],outcome='ACCEPTED_TARGET_OBSERVED' if accepted else 'ALREADY_TARGET',service_state='RUNNING' if target==4 else 'STOPPED',readiness='NOT_PROVEN',installed='NOT_PROVEN',execution_authority=False)
 except ActuationBlocked as error:
  if attempted:raise ActuationBlocked('SERVICE_ACTUATION_UNCERTAIN',effect_accepted=accepted,effect_attempted=True) from None
  raise
 except Exception:raise ActuationBlocked('SERVICE_ACTUATION_UNCERTAIN' if attempted else 'SERVICE_ACTUATION_UNAVAILABLE',effect_accepted=accepted,effect_attempted=attempted) from None

# A fixed read-only module-scope bridge. Only the already pinned helper's private
# readonly proofs/NSSM getters are reused. Request JSON has no code/selectors.
READONLY_BRIDGE=r"""$ErrorActionPreference='Stop';[Console]::InputEncoding=[Text.UTF8Encoding]::new($false);[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);try{
$m=Import-Module -Name ([WildcardPattern]::Escape($env:UNIFIED_SERVICE_MODULE)) -Force -PassThru
$r=[Console]::In.ReadToEnd()|ConvertFrom-Json
& $m {param($p)
Assert-OwnedAdmin
if(-not [string]::Equals([string]$p.computer_name,[Environment]::MachineName,[StringComparison]::OrdinalIgnoreCase)){throw 'HOST_REJECTED'}
Assert-OwnedFile $p.nssm $p.nssm_sha256;Assert-OwnedFile $p.python $p.python_sha256;Assert-OwnedFile $p.bootstrap $p.bootstrap_sha256;Assert-OwnedFile $p.entry $p.entry_sha256
$sid=([Security.Principal.NTAccount]::new('NT SERVICE\'+$p.service_name)).Translate([Security.Principal.SecurityIdentifier]).Value
if($sid -cne $p.service_sid){throw 'SID_REJECTED'}
$acl=Get-OwnedProof $p
@{service_name=$p.service_name;service_sid=$sid;application=(Invoke-OwnedNative $p.nssm @('get',$p.service_name,'Application'));parameters=(Invoke-OwnedNative $p.nssm @('get',$p.service_name,'AppParameters'));directory=(Invoke-OwnedNative $p.nssm @('get',$p.service_name,'AppDirectory'));app_exit=(Invoke-OwnedNative $p.nssm @('get',$p.service_name,'AppExit','Default'));marker=$p.plan_sha256;acl_policy=$acl.acl_policy;code_acl_sha256=$acl.code_acl_sha256;state_acl_sha256=$acl.state_acl_sha256}
} $r.plan | ConvertTo-Json -Compress -Depth 8
}catch{[Console]::Out.Write('{"error":"SERVICE_ACTUATION_REJECTED"}');exit 1}"""

def validate_nssm_registry(p,snapshot):
 need(type(snapshot) is dict and set(snapshot)=={'values','subkeys'})
 need(type(snapshot['values']) is dict and set(snapshot['values'])=={'Application','AppParameters','AppDirectory'})
 expected={'Application':p['python'],'AppParameters':p['parameters'],'AppDirectory':p['code']}
 for name,value in snapshot['values'].items():
  need(type(value) is list and len(value)==2 and type(value[0]) is str and value[0]==expected[name] and type(value[1]) is int and value[1] in (1,2))
 need(type(snapshot['subkeys']) is dict and set(snapshot['subkeys'])=={'AppExit'})
 exits=snapshot['subkeys']['AppExit'];need(type(exits) is dict and set(exits)=={'values','subkeys'} and exits['subkeys']=={} and type(exits['values']) is dict and set(exits['values'])=={''})
 value=exits['values'][''];need(type(value) is list and len(value)==2 and value[0]=='Exit' and type(value[1]) is int and value[1] in (1,2));return True

def nssm_registry_proof(p,*,api=None):
 if api is None:
  import winreg as api
 # Exact service namespace and finite direct keys only. No expansion or writes.
 path='SYSTEM\\CurrentControlSet\\Services\\'+p['service_name']+'\\Parameters'
 def read(key):
  subkeys,values,_=api.QueryInfoKey(key);need(0<=subkeys<=1 and 0<=values<=3)
  result={}
  for index in range(values):
   name,value,kind=api.EnumValue(key,index);need(type(name) is str and len(name)<=64 and name not in result and type(value) is str and len(value)<=32768)
   result[name]=[value,kind]
  names=[api.EnumKey(key,index) for index in range(subkeys)];need(all(type(name) is str and len(name)<=64 for name in names));return result,names
 with api.OpenKey(api.HKEY_LOCAL_MACHINE,path,0,api.KEY_READ) as key:
  values,names=read(key);need(names==['AppExit'])
  with api.OpenKey(key,'AppExit',0,api.KEY_READ) as exits:
   exit_values,exit_names=read(exits);need(not exit_names)
 snapshot={'values':values,'subkeys':{'AppExit':{'values':exit_values,'subkeys':{}}}}
 validate_nssm_registry(p,snapshot);return snapshot

def readonly_metadata(p):
 need(os.name=='nt');need(service.current_computer_name().casefold()==p['computer_name'].casefold())
 need(service._native_tools()==p['native_tools'])
 need(hashlib.sha256(lab_release.regular(service.MODULE).read_bytes()).hexdigest()==p['executor_sha256'])
 env=service._environment();env['UNIFIED_SERVICE_MODULE']=str(service.MODULE)
 ps=p['native_tools']['powershell'];need(service._native_hash(ps['path'])==ps['sha256'])
 payload=canonical({'plan':p});need(len(payload)<=32768)
 output,status=service._run([ps['path'],'-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(READONLY_BRIDGE.encode('utf-16le')).decode('ascii')],env=env,payload=payload,timeout=60,limit=65536)
 need(type(status) is int and status==0)
 nssm_registry_proof(p)
 value=json.loads(output);need(type(value) is dict and set(value)=={'service_name','service_sid','application','parameters','directory','app_exit','marker','acl_policy','code_acl_sha256','state_acl_sha256'})
 return value

class CONFIG(ctypes.Structure):
 _fields_=[('type',ctypes.c_uint32),('start',ctypes.c_uint32),('error',ctypes.c_uint32),('binary',ctypes.c_void_p),('group',ctypes.c_void_p),('tag',ctypes.c_uint32),('dependencies',ctypes.c_void_p),('account',ctypes.c_void_p),('display',ctypes.c_void_p)]
class STATUS(ctypes.Structure):
 _fields_=[(name,ctypes.c_uint32) for name in ('type','state','controls','winerror','specific','checkpoint','hint','pid','flags')]
class FAILURE_ACTIONS(ctypes.Structure):
 _fields_=[('reset_period',ctypes.c_uint32),('reboot_message',ctypes.c_void_p),('command',ctypes.c_void_p),('count',ctypes.c_uint32),('actions',ctypes.c_void_p)]
class TRIGGER_INFO(ctypes.Structure):
 _fields_=[('count',ctypes.c_uint32),('triggers',ctypes.c_void_p),('reserved',ctypes.c_void_p)]
class _WinSCM:
 def __init__(self):
  need(os.name=='nt');self.dll=ctypes.WinDLL(str(service._system_directory()/'advapi32.dll'),use_last_error=True)
  signatures={'OpenSCManagerW':([ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_uint32],ctypes.c_void_p),'OpenServiceW':([ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_uint32],ctypes.c_void_p),'CloseServiceHandle':([ctypes.c_void_p],ctypes.c_int),'QueryServiceConfigW':([ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint32,ctypes.POINTER(ctypes.c_uint32)],ctypes.c_int),'QueryServiceConfig2W':([ctypes.c_void_p,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_uint32,ctypes.POINTER(ctypes.c_uint32)],ctypes.c_int),'QueryServiceStatusEx':([ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_uint32,ctypes.POINTER(ctypes.c_uint32)],ctypes.c_int),'StartServiceW':([ctypes.c_void_p,ctypes.c_uint32,ctypes.c_void_p],ctypes.c_int),'ControlService':([ctypes.c_void_p,ctypes.c_uint32,ctypes.c_void_p],ctypes.c_int),'RegOpenKeyExW':([ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.POINTER(ctypes.c_void_p)],ctypes.c_long),'RegQueryValueExW':([ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint32),ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint32)],ctypes.c_long),'RegCloseKey':([ctypes.c_void_p],ctypes.c_long)}
  for name,(args,result) in signatures.items():function=getattr(self.dll,name);function.argtypes=args;function.restype=result
 def manager(self):value=self.dll.OpenSCManagerW(None,None,1);need(bool(value));return value
 def open(self,manager,name,action):
  value=self.dll.OpenServiceW(manager,name,1|4|(16 if action=='START' else 32));need(bool(value));return value
 def close(self,handle):need(bool(self.dll.CloseServiceHandle(handle)))
 def environment_absent(self,p):
  key=ctypes.c_void_p();path='SYSTEM\\CurrentControlSet\\Services\\'+p['service_name']
  # Only presence is probed: no unbounded Environment value is allocated/read.
  need(self.dll.RegOpenKeyExW(ctypes.c_void_p(-2147483646),path,0,1,ctypes.byref(key))==0 and bool(key.value))
  try:
   kind=ctypes.c_uint32();size=ctypes.c_uint32()
   result=self.dll.RegQueryValueExW(key,'Environment',None,ctypes.byref(kind),None,ctypes.byref(size));need(result==2)
   return True
  finally:need(self.dll.RegCloseKey(key)==0)
 def _optional_none(self,handle):
  def query(level,minimum):
   needed=ctypes.c_uint32();self.dll.QueryServiceConfig2W(handle,level,None,0,ctypes.byref(needed));need(minimum<=needed.value<=65536)
   allocated=needed.value;buffer=ctypes.create_string_buffer(allocated)
   # pcbBytesNeeded is specified for insufficient-buffer failure, not success.
   # All subsequent pointer/structure bounds use this admitted allocation.
   need(bool(self.dll.QueryServiceConfig2W(handle,level,buffer,allocated,ctypes.byref(needed))));return buffer
  def empty_string(buffer,pointer):
   if pointer is None:return True
   start=ctypes.addressof(buffer);need(start<=pointer<=start+len(buffer)-2 and (pointer-start)%2==0)
   return ctypes.string_at(pointer,2)==b'\0\0'
  def unused_array(buffer,pointer):
   return pointer is None or ctypes.addressof(buffer)<=pointer<ctypes.addressof(buffer)+len(buffer)
  buffer=query(2,ctypes.sizeof(FAILURE_ACTIONS));failure=FAILURE_ACTIONS.from_buffer(buffer)
  # No action array is traversed. Any entry (NONE/restart/reboot/run-command)
  # is outside the fresh service's default-none configuration.
  need(failure.count==0 and unused_array(buffer,failure.actions) and empty_string(buffer,failure.command) and empty_string(buffer,failure.reboot_message))
  for level in (3,4):
   buffer=query(level,4);need(ctypes.c_uint32.from_buffer(buffer).value==0)
  buffer=query(8,ctypes.sizeof(TRIGGER_INFO));trigger=TRIGGER_INFO.from_buffer(buffer)
  need(trigger.count==0 and trigger.reserved is None)
  # With zero triggers the pointer is unused; accept only NULL or a bounded
  # buffer pointer, never dereference an arbitrary address.
  need(unused_array(buffer,trigger.triggers))
  return True
 def read(self,handle):
  size=ctypes.c_uint32();self.dll.QueryServiceConfigW(handle,None,0,ctypes.byref(size));need(ctypes.sizeof(CONFIG)<=size.value<=65536)
  buffer=ctypes.create_string_buffer(size.value);need(bool(self.dll.QueryServiceConfigW(handle,buffer,len(buffer),ctypes.byref(size))))
  config=ctypes.cast(buffer,ctypes.POINTER(CONFIG)).contents
  def text(pointer):
   start=ctypes.addressof(buffer);need(pointer is not None and start<=pointer<start+len(buffer) and (pointer-start)%2==0)
   count=(start+len(buffer)-pointer)//2;need(count<=32768)
   raw=ctypes.string_at(pointer,count*2);end=next((i for i in range(0,len(raw),2) if raw[i:i+2]==b'\0\0'),None);need(end is not None);return raw[:end].decode('utf-16le')
  # This service was registered with no dependencies/load-order group. Never
  # let StartService implicitly bring up a foreign service or group.
  need(config.tag==0 and (not config.dependencies or text(config.dependencies)=='') and (not config.group or text(config.group)==''))
  sid=ctypes.c_uint32();need(bool(self.dll.QueryServiceConfig2W(handle,5,ctypes.byref(sid),4,ctypes.byref(size))))
  status=STATUS();need(bool(self.dll.QueryServiceStatusEx(handle,0,ctypes.byref(status),ctypes.sizeof(status),ctypes.byref(size))))
  need(config.type==16 and config.error==1 and status.type==16)
  self._optional_none(handle)
  account=text(config.account);need(account.casefold()=='nt authority\\localservice')
  return dict(binary_path=text(config.binary),account='NT AUTHORITY\\LocalService',start_type=config.start,sid_type=sid.value,state=status.state)
 def start(self,handle):need(bool(self.dll.StartServiceW(handle,0,None)))
 def stop(self,handle):
  status=STATUS();need(bool(self.dll.ControlService(handle,1,ctypes.byref(status))))

class _Handle:
 def __init__(self,api,handle):self.api=api;self.handle=handle;self.extra=None;self.plan=None
 def metadata(self,plan):
  self.plan=copy.deepcopy(plan);need(self.api.environment_absent(self.plan) is True);self.extra=readonly_metadata(plan);return self.read()
 def read(self):
  need(self.extra is not None and self.plan is not None and self.api.environment_absent(self.plan) is True);return dict(self.extra,**self.api.read(self.handle))
 def start(self):self.api.start(self.handle)
 def stop(self):self.api.stop(self.handle)
class WindowsServiceActuator:
 """Documented SCM APIs; exactly one admitted handle, never PID actuation."""
 def __init__(self,*,api=None):self.api=api
 @contextmanager
 def open(self,plan,action):
  need(action in ('START','STOP'));api=_WinSCM() if self.api is None else self.api;manager=api.manager();handle=None
  try:
   handle=api.open(manager,plan['service_name'],action);yield _Handle(api,handle)
  finally:
   try:
    if handle is not None:api.close(handle)
   finally:api.close(manager)
