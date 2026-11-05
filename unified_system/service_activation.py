"""Protected immutable activation revisions over the existing owned service.

No new credential producer, database provisioner, controller or readiness claim.
Owner-phase and external qualification callbacks are mandatory trusted broker
interfaces; JSON hashes/statuses do not authorize writes by themselves.
"""
import copy,hashlib,json,os,secrets,stat
from pathlib import Path
from contextlib import contextmanager
from . import lab_release,lab_runtime
from .service_bootstrap import ActivationBlocked,need,digest,label,canonical,local,stamp,POINTER_SCHEMA,DESCRIPTOR_SCHEMA,REVOKED_SCHEMA


def _file(path,limit=8192):
 path=local(path);before=stamp(path);need(0<before[2]<=limit)
 with path.open('rb') as stream:
  info=os.fstat(stream.fileno());need((info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_nlink)==before)
  raw=stream.read(limit+1);info=os.fstat(stream.fileno());need((info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_nlink)==before)
 need(len(raw)==before[2] and stamp(path)==before);return raw


def _directory_identity(path):
 path=local(path);info=path.lstat();need(stat.S_ISDIR(info.st_mode),'ACTIVATION_PATH_REJECTED')
 return info.st_dev,info.st_ino

def _pin_directories(root,revision_id=None):
 paths=[root,root/'activation',root/'activation/revisions']
 if revision_id is not None:paths.extend([root/'activation/revisions'/revision_id,root/'activation/revisions'/revision_id/'credentials'])
 return {path:_directory_identity(path) for path in paths}

def _check_directories(pins):
 for path,identity in pins.items():need(_directory_identity(path)==identity,'ACTIVATION_PATH_REJECTED')


def _hash(raw):return hashlib.sha256(raw).hexdigest()
def _pointer_hash(root):
 path=local(root/'activation/current.json');return _hash(_file(path)) if path.exists() else None

def _permission(owner,boundary,action,plan):
 need(callable(owner),'ACTIVATION_OWNER_PHASE_REQUIRED')
 host=plan['service_plan']['computer_name'];need(boundary.computer_name().casefold()==host.casefold(),'ACTIVATION_HOST_REJECTED')
 try:allowed=owner(action,plan['activation_plan_sha256'])
 except Exception:raise ActivationBlocked('ACTIVATION_OWNER_PHASE_REJECTED') from None
 need(allowed is True,'ACTIVATION_OWNER_PHASE_REJECTED');need(boundary.computer_name().casefold()==host.casefold(),'ACTIVATION_HOST_REJECTED')

def _profile(resource,profile,revision_id,qualification_refs):
 record=resource.recorded();service=copy.deepcopy(record['plan']);profile=copy.deepcopy(profile);refs=copy.deepcopy(qualification_refs);label(revision_id)
 root=local(service['root']);revision=root/'activation/revisions'/revision_id;config=profile['runtime_config'];context=profile['offline_context'];receipt=profile['derivation_receipt']
 need(profile['status']=='DERIVED_PROFILE_ONLY' and profile['execution_authority'] is False and profile['activation']=='BLOCKED')
 need(config['node_id']==service['node_id'] and config['state_root']==service['state'] and config['release_sha256']==service['manifest_sha256'])
 need(context=={'scope':'OFFLINE_VALIDATION_ONLY','role':service['role'],'node_id':service['node_id'],'computer_name':service['computer_name'],'credential_root':str(revision/'credentials')})
 need(receipt['base_manifest_sha256']==service['manifest_sha256'] and receipt['profile_sha256']==_hash(canonical(config)) and receipt['installation_id']==service['installation_id'])
 if 'data_first' in profile:
  from .data_first_policy import validate_data_first_grant
  manifest=lab_release.verify_capsule(service['code'],service['manifest_sha256'])['manifest']
  validate_data_first_grant(profile['data_first'],manifest)
 need(config['programs']['grid']['env']['GRID_LAB_AUTH_PATH']==str(revision/'credentials/auth.json'))
 auth_hash=config['programs']['grid']['env']['GRID_LAB_AUTH_SHA256'];digest(auth_hash)
 need(type(refs) is dict and set(refs)=={'phase_id','source_evidence_sha256','capacity_evidence_sha256','database_evidence_sha256'});label(refs['phase_id'])
 for field in ('source_evidence_sha256','capacity_evidence_sha256'):digest(refs[field])
 if service['role']=='WORKER':need(refs['database_evidence_sha256'] is None)
 else:digest(refs['database_evidence_sha256'])
 body={'schema':DESCRIPTOR_SCHEMA,'revision_id':revision_id,'service_plan':service,'resource_receipt_sha256':record['receipt_sha256'],'profile_sha256':_hash(canonical(profile)),'auth_sha256':auth_hash,'qualification_refs':refs,'previous_pointer_sha256':_pointer_hash(root)}
 return {**body,'activation_plan_sha256':_hash(canonical(body))},profile

@contextmanager
def _publication_lock(root):
 path=local(root/'activation/publication.lock')
 with path.open('a+b') as stream:
  need(path.stat().st_nlink==1)
  if os.name=='nt':
   import msvcrt
   stream.seek(0,2)
   if stream.tell()==0:stream.write(b'0');stream.flush()
   stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
   try:yield stamp(path)
   finally:stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
  else:
   import fcntl
   fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
   try:yield stamp(path)
   finally:fcntl.flock(stream,fcntl.LOCK_UN)

class WindowsRevisionBoundary:
 """Effect boundary: reviewed existing ACL functions, no SCM start/stop calls."""
 def computer_name(self):
  from .installation_service import current_computer_name
  return current_computer_name()
 def _assert_writer(self,plan):
  from . import installation_service as service
  import ctypes
  need(os.name=='nt' and service._native_tools()==plan['service_plan']['native_tools'],'ACTIVATION_NATIVE_REJECTED')
  check=ctypes.WinDLL('shell32',use_last_error=True).IsUserAnAdmin;check.argtypes=[];check.restype=ctypes.c_int
  need(check()!=0,'ACTIVATION_ELEVATED_WRITER_REQUIRED')
 def _acl(self,plan,directories=(),files=()):
  self._assert_writer(plan)
  from . import installation_service as service
  p=plan['service_plan'];need(service._native_tools()==p['native_tools'])
  need(_hash(lab_release.regular(service.MODULE).read_bytes())==p['executor_sha256'])
  code="$ErrorActionPreference='Stop';[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);try{$r=[Console]::In.ReadToEnd()|ConvertFrom-Json;$m=Import-Module -Name ([WildcardPattern]::Escape($env:UNIFIED_SERVICE_MODULE)) -PassThru;& $m {param($r) Assert-OwnedAdmin;Assert-OwnedMarker $r.plan;foreach($p in $r.directories){Assert-OwnedPath $p;Set-OwnedAcl $p $r.plan.service_sid 'ReadAndExecute'};foreach($p in $r.files){Assert-OwnedPath $p;$a=Get-Acl -LiteralPath $p;$a.SetOwner([Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'));(Get-Item -LiteralPath $p -Force).SetAccessControl($a)}} $r;[Console]::Out.Write('{\"ok\":true}')}catch{[Console]::Out.Write('{\"error\":\"ACTIVATION_NATIVE_REJECTED\"}');exit 1}"
  import base64
  encoded=base64.b64encode(code.encode('utf-16le')).decode('ascii');env=service._environment();env['UNIFIED_SERVICE_MODULE']=str(service.MODULE)
  output,status=service._run([p['native_tools']['powershell']['path'],'-NoProfile','-NonInteractive','-EncodedCommand',encoded],env=env,payload=canonical({'plan':p,'directories':[str(x) for x in directories],'files':[str(x) for x in files]}),timeout=60)
  need(status==0 and json.loads(output)=={'ok':True},'ACTIVATION_NATIVE_REJECTED')
 def prepare(self,plan):
  self._assert_writer(plan)
  root=local(Path(plan['service_plan']['root'])/'activation');marker=root/'namespace.json';expected=canonical({'service_plan_sha256':plan['service_plan']['plan_sha256']})
  if root.exists():
   from .service_bootstrap import WindowsActivationKernel
   WindowsActivationKernel().require_readonly(marker,plan['service_plan']['service_sid'],root);need(_file(marker)==expected,'ACTIVATION_NAMESPACE_REJECTED')
  else:
   root.mkdir(exist_ok=False);self._acl(plan,directories=[root]);marker.write_bytes(expected);self._acl(plan,files=[marker])
  revisions=local(root/'revisions');revisions.mkdir(exist_ok=True);self._acl(plan,files=[revisions]);revision=local(revisions/plan['revision_id']);revision.mkdir(exist_ok=False);(revision/'credentials').mkdir()
 def seal(self,plan):
  revision=Path(plan['service_plan']['root'])/'activation/revisions'/plan['revision_id']
  paths=[revision,revision/'credentials',*revision.rglob('*')];self._acl(plan,files=list(dict.fromkeys(paths)))
 def publish(self,plan,pointer):
  root=local(Path(plan['service_plan']['root'])/'activation');pins=_pin_directories(root.parent);
  from .service_bootstrap import WindowsActivationKernel
  WindowsActivationKernel().require_readonly(root,plan['service_plan']['service_sid'],root)
  _check_directories(pins);temporary=root/('.current-'+secrets.token_hex(12)+'.tmp')
  with temporary.open('xb') as stream:stream.write(pointer);stream.flush();os.fsync(stream.fileno())
  self._acl(plan,files=[temporary]);_check_directories(pins);local(temporary);local(root/'current.json');os.replace(temporary,root/'current.json')

def publish_activation(resource,profile,auth_source,*,revision_id,qualification_refs,owner_phase=None,qualify=None,boundary=None):
 try:
  plan,profile=_profile(resource,profile,revision_id,qualification_refs);root=Path(plan['service_plan']['root']);initial={root:_directory_identity(root)};boundary=WindowsRevisionBoundary() if boundary is None else boundary
  need(callable(qualify),'ACTIVATION_QUALIFICATION_REQUIRED')
  try:qualified=qualify(copy.deepcopy(plan),copy.deepcopy(plan['qualification_refs']))
  except Exception:raise ActivationBlocked('ACTIVATION_QUALIFICATION_REJECTED') from None
  need(qualified is True,'ACTIVATION_QUALIFICATION_REJECTED');_permission(owner_phase,boundary,'PUBLISH_SERVICE_ACTIVATION',plan)
  resource.inspect(lambda action,pin:(_permission(owner_phase,boundary,'VERIFY_SERVICE_RESOURCE',plan) or True))
  auth=_file(auth_source);need(_hash(auth)==plan['auth_sha256'],'ACTIVATION_AUTH_REJECTED')
  service=plan['service_plan'];grid=profile['derivation_receipt']['sources']['grid']
  context=copy.deepcopy(profile['offline_context']);context['credential_root']=str(local(auth_source).parent)
  lab_runtime.read_grid_auth(auth_source,plan['auth_sha256'],node_id=service['node_id'],release_id=profile['runtime_config']['release_id'],source_commit=grid['commit'],role_context=context)
  descriptor={key:value for key,value in plan.items() if key!='previous_pointer_sha256'}
  _check_directories(initial)
  _permission(owner_phase,boundary,'CREATE_ACTIVATION_REVISION',plan);_check_directories(initial);boundary.prepare(copy.deepcopy(plan))
  _check_directories(initial);pins=_pin_directories(root,revision_id)
  revision=Path(service['root'])/'activation/revisions'/revision_id
  for name,raw in [('profile.json',canonical(profile)),('credentials/auth.json',auth),('descriptor.json',canonical(descriptor))]:
   _permission(owner_phase,boundary,'WRITE_ACTIVATION_ARTIFACT',plan);_check_directories(pins);local(revision/name)
   with (revision/name).open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
  _permission(owner_phase,boundary,'SEAL_ACTIVATION_REVISION',plan);_check_directories(pins);boundary.seal(copy.deepcopy(plan))
  pointer=canonical({'schema':POINTER_SCHEMA,'revision_id':revision_id,'descriptor_sha256':_hash(canonical(descriptor))})
  _permission(owner_phase,boundary,'LOCK_ACTIVATION_PUBLICATION',plan);_check_directories(pins)
  with _publication_lock(Path(service['root'])) as locked:
   _permission(owner_phase,boundary,'COMMIT_ACTIVATION_POINTER',plan);_check_directories(pins);need(stamp(root/'activation/publication.lock')==locked,'ACTIVATION_CONCURRENT_UPDATE');need(_pointer_hash(Path(service['root']))==plan['previous_pointer_sha256'],'ACTIVATION_CONCURRENT_UPDATE')
   boundary.publish(copy.deepcopy(plan),pointer)
  return {'schema':DESCRIPTOR_SCHEMA,'status':'ACTIVATION_REVISION_PUBLISHED','activation_plan_sha256':plan['activation_plan_sha256'],'descriptor_sha256':_hash(canonical(descriptor)),'readiness':'NOT_PROVEN','physical_acceptance':'NOT_RUN'}
 except ActivationBlocked:raise
 except Exception:raise ActivationBlocked('ACTIVATION_REJECTED') from None

def revoke_activation(resource,*,owner_phase=None,boundary=None):
 try:
  record=resource.recorded();service=copy.deepcopy(record['plan']);boundary=WindowsRevisionBoundary() if boundary is None else boundary;root=Path(service['root']);previous=_pointer_hash(root);need(previous is not None)
  body={'service_plan':service,'previous_pointer_sha256':previous};plan={**body,'activation_plan_sha256':_hash(canonical(body))}
  pins=_pin_directories(root)
  _permission(owner_phase,boundary,'REVOKE_SERVICE_ACTIVATION',plan);_check_directories(pins)
  with _publication_lock(root) as locked:
   _permission(owner_phase,boundary,'REVOKE_SERVICE_ACTIVATION',plan);_check_directories(pins);need(stamp(root/'activation/publication.lock')==locked,'ACTIVATION_CONCURRENT_UPDATE');need(_pointer_hash(root)==previous,'ACTIVATION_CONCURRENT_UPDATE')
   boundary.publish(copy.deepcopy(plan),canonical({'schema':REVOKED_SCHEMA,'previous_pointer_sha256':previous}))
  return {'status':'ACTIVATION_REVOKED','data_deleted':False}
 except ActivationBlocked:raise
 except Exception:raise ActivationBlocked('ACTIVATION_REJECTED') from None
