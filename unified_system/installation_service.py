"""Receipt-owned manual/stopped Windows service adapter; default effect denial.

This is not a fleet controller or an activation/readiness authority. Private
parents and exact external owner phase-plan approval are caller prerequisites.
No start/stop/delete operation exists. Interrupted resources remain for review.
This service resource journal owns only this new service namespace; it is not a
second installer phase/progress authority or adoption of a prior staging root.
OS identity/hash checks do not attest the host or contain a malicious administrator.
"""
import base64,copy,hashlib,json,os,re,subprocess,tempfile,time,sqlite3,ctypes,stat
from contextlib import closing
from pathlib import Path
from . import lab_release
from .contracts import canonical,seal
from .installation_progress import identifier,safe as safe_journal
from .lab_capsule_acl import _safe
from .journal import Journal

MODULE=Path(__file__).resolve().parents[1]/'scripts/UnifiedOwnedService.psm1'
NSSM_PIN='eee9c44c29c2be011f1f1e43bb8c3fca888cb81053022ec5a0060035de16d848'
# Exact reviewed LF Git blobs, independent of operator checkout EOLs.
# Protected entry still needs kernel/revision/full runtime admission; these
# hashes are not publisher trust. Candidate bytes are never normalized.
SERVICE_ENTRY_SHA256='f67abf94e10f321492bc4a075c21cf5253a06487f27ef00ab6ce077af0fb2aa0'
SERVICE_BOOTSTRAP_SHA256='878e8cd0bf8a0e4049cecb09101f375a68a191949405bbe9be77ea56f3d40db3'
BLOCKED_ENTRY_SHA256=SERVICE_ENTRY_SHA256 # Legacy public constant; entry is now gated.
SCHEMA='unified.owned-stopped-service.v1'
ACTIONS={'BEGIN','SEAL','REGISTER','INSPECT'}
NATIVE_STAGES=frozenset(('UNAVAILABLE','SID_LOOKUP','ACL_PROOF','MEMBER_PINS','SCM_CREATE','SCM_READ','SCM_PROOF',
 'NSSM_SET_APPLICATION','NSSM_SET_PARAMETERS','NSSM_SET_DIRECTORY','NSSM_SET_APP_EXIT',
 'NSSM_GET_APPLICATION','NSSM_GET_PARAMETERS','NSSM_GET_DIRECTORY','NSSM_GET_APP_EXIT'))

class OwnedServiceRejected(ValueError):
 """A closed diagnostic stage, never raw native output or exception text."""
 def __init__(self,native_stage='UNAVAILABLE',native_exit_code=None):
  self.native_stage=native_stage if type(native_stage) is str and native_stage in NATIVE_STAGES else 'UNAVAILABLE'
  self.native_exit_code=native_exit_code if self.native_stage.startswith('NSSM_') and type(native_exit_code) is int and 0<=native_exit_code<2**32 else None
  super().__init__('OWNED_SERVICE_REJECTED')

def _native_result(output,status):
 try:result=json.loads(output)
 except (TypeError,ValueError):raise OwnedServiceRejected() from None
 if status!=0 or type(result) is not dict or 'error' in result:
  stage='UNAVAILABLE'
  exit_code=None
  if type(result) is dict and set(result) in ({'error','native_stage'},{'error','native_stage','native_exit_code'}) and result['error']=='OWNED_SERVICE_REJECTED':
   stage=result['native_stage'];exit_code=result.get('native_exit_code')
  raise OwnedServiceRejected(stage,exit_code)
 return result


def need(ok):
 if not ok:raise ValueError('OWNED_SERVICE_REJECTED')


def parse_service_sid(output,exit_code):
 need(type(exit_code) is int and exit_code==0 and type(output) is str and len(output.encode('utf8'))<=65536)
 found=re.findall(r'(?<![A-Za-z0-9_-])S-[0-9]+(?:-[0-9]+)+(?![A-Za-z0-9_-])',output)
 need(len(found)==1)
 sid=found[0];need(re.fullmatch(r'S-1-5-80-(?:[0-9]+-){4}[0-9]+',sid) is not None)
 parts=sid.split('-')[4:];need(len(parts)==5 and all(str(int(p))==p and 0<=int(p)<=4294967295 for p in parts))
 return sid


def _run(argv,*,env,payload=None,timeout=30,limit=262144,encoding='utf8',errors='strict'):
 with tempfile.TemporaryFile() as source,tempfile.TemporaryFile() as out,tempfile.TemporaryFile() as error:
  if payload is not None:source.write(payload)
  source.seek(0)
  child=subprocess.Popen(argv,env=env,stdin=source,stdout=out,stderr=error)
  try:
   deadline=time.monotonic()+timeout
   while child.poll() is None:
    need(time.monotonic()<deadline and os.fstat(out.fileno()).st_size<=limit and os.fstat(error.fileno()).st_size<=limit)
    time.sleep(.01)
   need(os.fstat(out.fileno()).st_size<=limit and os.fstat(error.fileno()).st_size<=limit)
  finally:
   if child.poll() is None:child.kill()
   child.wait(timeout=2)
  out.seek(0);return out.read(limit+1).decode(encoding,errors=errors),child.returncode


def current_computer_name():
 """OS-derived accidental wrong-host protection, never host attestation."""
 need(os.name=='nt')
 kernel=ctypes.WinDLL('kernel32',use_last_error=True)
 function=kernel.GetComputerNameW;function.argtypes=[ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_uint)];function.restype=ctypes.c_int
 buffer=ctypes.create_unicode_buffer(256);count=ctypes.c_uint(len(buffer))
 need(function(buffer,ctypes.byref(count))!=0 and 0<count.value<len(buffer))
 return buffer.value


def _system_directory():
 need(os.name=='nt')
 kernel=ctypes.WinDLL('kernel32',use_last_error=True)
 function=kernel.GetSystemDirectoryW;function.argtypes=[ctypes.c_wchar_p,ctypes.c_uint];function.restype=ctypes.c_uint
 buffer=ctypes.create_unicode_buffer(32768);count=function(buffer,len(buffer));need(0<count<len(buffer))
 directory=_safe(buffer.value);need(directory.name.casefold()=='system32')
 for key in ('SYSTEMROOT','WINDIR'):
  value=next((v for k,v in os.environ.items() if k.upper()==key),None)
  if value is not None:need(value.rstrip('\\/').casefold()==str(directory.parent).casefold())
 return directory


def _native_hash(path):
 # Only WinAPI-derived OS leaves; servicing hardlinks are legitimate here.
 # Capsule/source leaves retain their independent single-link requirement.
 directory=_system_directory();path=_safe(path)
 need(path in (directory/'sc.exe',directory/'WindowsPowerShell/v1.0/powershell.exe'))
 before=path.lstat();need(stat.S_ISREG(before.st_mode) and before.st_nlink>=1 and 0<before.st_size<=64*1024*1024)
 fields=lambda value:(value.st_dev,value.st_ino,value.st_size,value.st_mtime_ns,value.st_nlink)
 h=hashlib.sha256();count=0
 with path.open('rb') as stream:
  initial=os.fstat(stream.fileno());need(fields(initial)==fields(before))
  for block in iter(lambda:stream.read(1048576),b''):
   count+=len(block);need(count<=64*1024*1024);h.update(block)
  after=os.fstat(stream.fileno());need(fields(after)==fields(initial) and after.st_ctime_ns==initial.st_ctime_ns)
 current=path.lstat();need(fields(current)==fields(before) and current.st_ctime_ns==before.st_ctime_ns and count==before.st_size)
 return h.hexdigest()


def _native_tools():
 directory=_system_directory()
 tools={}
 for key,relative in [('sc','sc.exe'),('powershell','WindowsPowerShell/v1.0/powershell.exe')]:
  path=directory/relative;tools[key]={'path':str(path),'sha256':_native_hash(path)}
 return tools


def _environment():
 directory=_system_directory()
 env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMDRIVE','PROGRAMDATA','TEMP','TMP','USERPROFILE','LOCALAPPDATA','APPDATA'}}
 env.update(SYSTEMROOT=str(directory.parent),WINDIR=str(directory.parent),PSModulePath=str(directory/'WindowsPowerShell/v1.0/Modules'))
 return env


class WindowsServiceBoundary:
 """Fixed reviewed backend. No listener, automatic elevation or policy override."""
 def computer_name(self):return current_computer_name()
 def native_tools(self):return _native_tools()
 def sid(self,name):
  need(os.name=='nt' and re.fullmatch(r'UnifiedLab_[A-Za-z0-9_]{1,80}',name) is not None)
  tool=_native_tools()['sc'];sc=Path(tool['path']);need(_native_hash(sc)==tool['sha256'])
  output,code=_run([str(sc),'showsid',name],env=_environment(),timeout=5,limit=65536,encoding='ascii',errors='replace')
  return parse_service_sid(output,code)
 def call(self,action,plan,guard):
  plan=_check_plan(copy.deepcopy(plan))
  need(action in ACTIONS and callable(guard) and guard(action,plan['plan_sha256']) is True and os.name=='nt')
  need(current_computer_name().casefold()==plan['computer_name'].casefold())
  need(_native_tools()==plan['native_tools'])
  need(hashlib.sha256(lab_release.regular(MODULE).read_bytes()).hexdigest()==plan['executor_sha256'])
  # Static bootstrap only. Paths/request data are never interpolated into code.
  code="$ErrorActionPreference='Stop';[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);[Console]::InputEncoding=[Text.UTF8Encoding]::new($false);try{Import-Module -Name ([WildcardPattern]::Escape($env:UNIFIED_SERVICE_MODULE)) -Force; $r=[Console]::In.ReadToEnd()|ConvertFrom-Json; Invoke-UnifiedOwnedService $r|ConvertTo-Json -Depth 12 -Compress}catch{$stage='UNAVAILABLE';$childCode=$null;try{$stage=Get-UnifiedOwnedServiceStage;$childCode=Get-UnifiedOwnedNativeExitCode}catch{};@{error='OWNED_SERVICE_REJECTED';native_stage=$stage;native_exit_code=$childCode}|ConvertTo-Json -Compress;exit 1}"
  encoded=base64.b64encode(code.encode('utf-16le')).decode('ascii')
  env=_environment();env['UNIFIED_SERVICE_MODULE']=str(MODULE)
  request={'action':action,'plan':plan}
  need(len(canonical(request))<=32768)
  ps=Path(plan['native_tools']['powershell']['path']);need(_native_hash(ps)==plan['native_tools']['powershell']['sha256'])
  output,status=_run([str(ps),'-NoProfile','-NonInteractive','-EncodedCommand',encoded],env=env,payload=canonical(request),timeout=60)
  result=_native_result(output,status)
  if action=='BEGIN':
   need(result=={'root_created':True});facts=_safe(plan['root']).stat();return {'root_device':facts.st_dev,'root_inode':facts.st_ino}
  return result


def service_plan(capsule_root,manifest_sha256,root,installation_id,node_id,role,boundary):
 report=lab_release.verify_capsule(capsule_root,manifest_sha256);m=report['manifest']
 for value in (installation_id,node_id):identifier(value)
 if role=='SINGLE-PC':role='SINGLE_PC'
 need(role in ('CONTROL','WORKER','SINGLE_PC'))
 source=_safe(capsule_root);root=_safe(root)
 need(root.parent.is_dir() and source!=root and root not in source.parents and source not in root.parents)
 name='UnifiedLab_'+seal({'installation_id':installation_id,'node_id':node_id})[:24]
 sid=boundary.sid(name);need(parse_service_sid(sid,0)==sid)
 code=root/'code';python='runtime/python/python.exe';nssm='runtime/nssm/nssm.exe';bootstrap='sources/unified-system/unified_system/owned_python.py';entry='sources/unified-system/unified_system/service_entry.py'
 need({python,nssm,bootstrap,entry}<=set(m['files']) and m['files'][nssm]['sha256']==NSSM_PIN)
 need(m['files'][entry]['sha256']==SERVICE_ENTRY_SHA256)
 need(m['files'].get('sources/unified-system/unified_system/service_bootstrap.py',{}).get('sha256')==SERVICE_BOOTSTRAP_SHA256)

 body=dict(schema=SCHEMA,installation_id=installation_id,node_id=node_id,computer_name=boundary.computer_name(),role=role,root=str(root),code=str(code),state=str(root/'state'),
  capsule_root=str(source),manifest_sha256=manifest_sha256,service_name=name,service_sid=sid,
  nssm=str(code/nssm),nssm_sha256=m['files'][nssm]['sha256'],python=str(code/python),python_sha256=m['files'][python]['sha256'],
  bootstrap=str(code/bootstrap),bootstrap_sha256=m['files'][bootstrap]['sha256'],entry=str(code/entry),entry_sha256=m['files'][entry]['sha256'],parameters='-I -S -B \"'+str(code/entry)+'\"',
  executor_sha256=hashlib.sha256(lab_release.regular(MODULE).read_bytes()).hexdigest(),native_tools=boundary.native_tools(),activation='BLOCKED')
 return _check_plan(dict(body,plan_sha256=seal(body)))


def _check_plan(plan):
 need(type(plan) is dict and len(canonical(plan))<=32768)
 need(plan.get('schema')==SCHEMA and plan.get('activation')=='BLOCKED' and plan.get('plan_sha256')==seal({k:v for k,v in plan.items() if k!='plan_sha256'}))
 need(set(plan)=={'schema','installation_id','node_id','computer_name','role','root','code','state','capsule_root','manifest_sha256','service_name','service_sid','nssm','nssm_sha256','python','python_sha256','bootstrap','bootstrap_sha256','entry','entry_sha256','parameters','executor_sha256','native_tools','activation','plan_sha256'})
 need(type(plan['computer_name']) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,62}',plan['computer_name']) is not None)
 need(type(plan['native_tools']) is dict and set(plan['native_tools'])=={'sc','powershell'})
 for tool in plan['native_tools'].values():
  need(type(tool) is dict and set(tool)=={'path','sha256'});_safe(tool['path']);lab_release.digest(tool['sha256'])
 root=_safe(plan['root']);need(str(root/'code')==plan['code'] and str(root/'state')==plan['state'])
 for key in ('installation_id','node_id'):identifier(plan[key])
 name='UnifiedLab_'+seal({'installation_id':plan['installation_id'],'node_id':plan['node_id']})[:24];need(plan['service_name']==name)
 need(parse_service_sid(plan['service_sid'],0)==plan['service_sid'])
 need(plan['role'] in ('CONTROL','WORKER','SINGLE_PC'))
 source=_safe(plan['capsule_root']);need(source!=root and source not in root.parents and root not in source.parents)
 report=lab_release.verify_capsule(source,plan['manifest_sha256']);m=report['manifest']
 for key,relative in [('nssm','runtime/nssm/nssm.exe'),('python','runtime/python/python.exe'),('bootstrap','sources/unified-system/unified_system/owned_python.py'),('entry','sources/unified-system/unified_system/service_entry.py')]:
  need(relative in m['files'] and plan[key]==str(root/'code'/relative) and plan[key+'_sha256']==m['files'][relative]['sha256'])
 need(plan['nssm_sha256']==NSSM_PIN and plan['executor_sha256']==hashlib.sha256(lab_release.regular(MODULE).read_bytes()).hexdigest())
 need(plan['entry_sha256']==SERVICE_ENTRY_SHA256)
 need(m['files'].get('sources/unified-system/unified_system/service_bootstrap.py',{}).get('sha256')==SERVICE_BOOTSTRAP_SHA256)
 need(plan['parameters']=='-I -S -B \"'+plan['entry']+'\"')
 return copy.deepcopy(plan)


def _expected(plan):
 return dict(service_name=plan['service_name'],service_sid=plan['service_sid'],account='NT AUTHORITY\\LocalService',start_type=3,sid_type=1,state=1,
  binary_path='"'+plan['nssm']+'"',application=plan['python'],parameters=plan['parameters'],directory=plan['code'],app_exit='Exit',marker=plan['plan_sha256'],acl_policy='EXACT_SERVICE_SID_V1')


def _proof(plan,proof):
 expected=_expected(plan);need(type(proof) is dict and set(proof)==set(expected)|{'code_acl_sha256','state_acl_sha256'})
 need(all(proof[key]==value for key,value in expected.items()))
 for field in ('start_type','sid_type','state'):need(type(proof[field]) is int)
 for field in ('code_acl_sha256','state_acl_sha256'):lab_release.digest(proof[field])
 return proof


class ServiceResource:
 def __init__(self,plan,boundary):
  self.plan=_check_plan(copy.deepcopy(plan));self.boundary=boundary;self.root=Path(self.plan['root']);self.journal=Journal(self.root/'ownership/service.sqlite')
 def _permit(self,action,guard):
  need(callable(guard) and guard(action,self.plan['plan_sha256']) is True)
  need(self.boundary.computer_name().casefold()==self.plan['computer_name'].casefold())
 def _call(self,action,guard):
  self._permit(action,guard)
  return self.boundary.call(action,copy.deepcopy(self.plan),guard)
 @classmethod
 def create(cls,plan,boundary,guard=None):
  resource=cls(plan,boundary);plan=resource.plan;need(not resource.root.exists())
  lab_release.verify_capsule(plan['capsule_root'],plan['manifest_sha256'])
  roots=resource._call('BEGIN',guard)
  actual=resource.root.stat();need(roots=={'root_device':actual.st_dev,'root_inode':actual.st_ino})
  resource._permit('WRITE_RECEIPT',guard)
  fd=os.open(resource.journal.path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd);resource.journal.initialize()
  resource.journal.append('OBSERVING',{'kind':'ROOTS','plan':plan,'fingerprint':roots},expected_sequence=0)
  resource._append('STAGE_INTENT',guard=guard)
  resource._permit('STAGE',guard)
  lab_release.stage_capsule(plan['capsule_root'],plan['code'],plan['manifest_sha256'])
  resource._append('CODE_STAGED',guard=guard)
  acl=resource._call('SEAL',guard)
  need(set(acl)=={'code_acl_sha256','state_acl_sha256','acl_policy'} and acl['acl_policy']=='EXACT_SERVICE_SID_V1')
  for key in ('code_acl_sha256','state_acl_sha256'):lab_release.digest(acl[key])
  resource._append('ACL_SEALED',acl,guard=guard)
  lab_release.verify_capsule(plan['code'],plan['manifest_sha256'])
  resource._append('REGISTER_INTENT',guard=guard)
  proof=_proof(plan,resource._call('REGISTER',guard));need(all(proof[key]==value for key,value in acl.items()))
  resource._append('REGISTERED',proof,guard=guard)
  return resource
 @classmethod
 def open(cls,plan,boundary):
  resource=cls(plan,boundary);resource._read();return resource
 def _read(self):
  safe_journal(self.journal.path);need(self.journal.path.stat().st_size<=2*1024*1024)
  with closing(sqlite3.connect(self.journal.path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
   need(1<=db.execute('SELECT COUNT(*) FROM transitions').fetchone()[0]<=6)
   need(db.execute("SELECT COUNT(*) FROM transitions WHERE typeof(receipt)!='text' OR length(CAST(receipt AS BLOB))>65536").fetchone()[0]==0)
  rows=self.journal.read();s=self.root.stat();need(rows[0]['state']=='OBSERVING' and rows[0]['receipt']=={'kind':'ROOTS','plan':self.plan,'fingerprint':{'root_device':s.st_dev,'root_inode':s.st_ino}})
  order=('STAGE_INTENT','CODE_STAGED','ACL_SEALED','REGISTER_INTENT','REGISTERED')
  for index,row in enumerate(rows[1:]):
   r=row['receipt'];need(row['state']=='OBSERVING' and set(r)=={'kind','plan_sha256','proof'} and r['kind']==order[index] and r['plan_sha256']==self.plan['plan_sha256'])
   if r['kind'] in ('STAGE_INTENT','CODE_STAGED','REGISTER_INTENT'):need(r['proof'] is None)
   elif r['kind']=='ACL_SEALED':
    proof=r['proof'];need(type(proof) is dict and set(proof)=={'code_acl_sha256','state_acl_sha256','acl_policy'} and proof['acl_policy']=='EXACT_SERVICE_SID_V1')
    for field in ('code_acl_sha256','state_acl_sha256'):lab_release.digest(proof[field])
   else:
    _proof(self.plan,r['proof']);need(all(r['proof'][k]==v for k,v in rows[3]['receipt']['proof'].items()))
  return rows
 def _append(self,kind,proof=None,*,guard=None):
  self._permit('WRITE_RECEIPT',guard)
  rows=self._read();self.journal.append('OBSERVING',{'kind':kind,'plan_sha256':self.plan['plan_sha256'],'proof':proof},expected_sequence=len(rows))
 def recorded(self):
  """Private immutable copy of recorded ownership, independent of code presence.

  This is evidence for a separately approved removal adapter, not live-resource
  admission. No filesystem deletion or SCM action is authorized by this record.
  """
  rows=self._read();need(len(rows)==6 and rows[-1]['receipt']['kind']=='REGISTERED')
  return copy.deepcopy({'schema':SCHEMA,'plan':self.plan,'proof':_proof(self.plan,rows[-1]['receipt']['proof']),
   'acl_proof':rows[3]['receipt']['proof'],'root_fingerprint':rows[0]['receipt']['fingerprint'],'receipt_sha256':seal(rows[-1])})
 def inspect(self,guard=None):
  rows=self._read();need(len(rows)==6 and rows[-1]['receipt']['kind']=='REGISTERED')
  lab_release.verify_capsule(self.plan['code'],self.plan['manifest_sha256'])
  recorded=_proof(self.plan,rows[-1]['receipt']['proof']);live=_proof(self.plan,self._call('INSPECT',guard));need(recorded==live)
  return dict(schema=SCHEMA,status='STOPPED_RESOURCE_RECORDED',computer_name=self.plan['computer_name'],service_name=self.plan['service_name'],service_sid=self.plan['service_sid'],plan_sha256=self.plan['plan_sha256'],
   receipt_sha256=seal(rows[-1]),activation='BLOCKED',readiness='NOT_PROVEN',installed='NOT_PROVEN',execution_authority=False,physical_acceptance='NOT_RUN',
   pending=['SCOPED_GIT_ADMISSION','RUNTIME_CONFIG_REBASE','RESOURCE_CAPACITY','OWNER_PHYSICAL_ACCEPTANCE'])
