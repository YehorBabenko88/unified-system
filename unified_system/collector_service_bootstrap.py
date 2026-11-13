"""Stdlib initial gates and nonauthoritative Collector revision evidence.

No operational approval adapter, protected grant or runtime is implemented.
"""
import copy
import ctypes
import hashlib
import os
from pathlib import Path
import re
import stat

SECURITY_SHA256='a8012a04c4a0507a72bd6ba38c63ad0af855d5f25efea7669ea11db1386d8d45'
POINTER_SCHEMA='unified.collector-activation-pointer.v1'
DESCRIPTOR_SCHEMA='unified.collector-activation.v1'

class CollectorActivationBlocked(ValueError):pass
def _need(ok,code='COLLECTOR_ACTIVATION_REJECTED'):
 if not ok:raise CollectorActivationBlocked(code)
def _digest(value):_need(type(value) is str and re.fullmatch('[a-f0-9]{64}',value) is not None)
def _keys(value,keys):_need(type(value) is dict and all(type(k) is str for k in value) and set(value)==set(keys))
def _label(value):_need(type(value) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,63}',value) is not None)

def _load_security():
 # Hash and execute the held existing reviewed helper, never import it via sys.path.
 path=Path(__file__).absolute().with_name('service_bootstrap.py')
 for item in (*reversed(path.parents),path):
  info=item.lstat();_need(not stat.S_ISLNK(info.st_mode) and not getattr(info,'st_file_attributes',0)&1024)
 before=path.stat();_need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<before.st_size<=1048576)
 with path.open('rb') as stream:
  raw=stream.read(1048577);after=os.fstat(stream.fileno())
 fields=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink)
 _need(fields(before)==fields(after)==fields(path.stat()) and hashlib.sha256(raw).hexdigest()==SECURITY_SHA256)
 import types
 module=types.ModuleType('_collector_reviewed_security');module.__file__=str(path)
 exec(compile(raw,str(path),'exec'),module.__dict__);return module

class _WindowsCollectorKernel:
 def __init__(self,security):self.security=security.WindowsActivationKernel()
 def identity(self):return self.security.identity()
 def require_readonly(self,path,sid,anchor):return self.security.require_readonly(path,sid,anchor)
 def session_id(self):
  _need(os.name=='nt','COLLECTOR_PLATFORM_REJECTED')
  api=ctypes.WinDLL('kernel32',use_last_error=True)
  api.GetCurrentProcessId.argtypes=[];api.GetCurrentProcessId.restype=ctypes.c_uint
  api.ProcessIdToSessionId.argtypes=[ctypes.c_uint,ctypes.POINTER(ctypes.c_uint)];api.ProcessIdToSessionId.restype=ctypes.c_int
  session=ctypes.c_uint();_need(api.ProcessIdToSessionId(api.GetCurrentProcessId(),ctypes.byref(session))!=0)
  return session.value

def _identity(kernel):
 value=kernel.identity();_keys(value,('user_sid','service_sid','computer_name'))
 _need(value['user_sid']=='S-1-5-19','COLLECTOR_SERVICE_TOKEN_REQUIRED')
 _need(type(value['service_sid']) is str and re.fullmatch(r'S-1-5-80-(?:[0-9]+-){4}[0-9]+',value['service_sid']) is not None)
 _label(value['computer_name']);session=kernel.session_id()
 _need(type(session) is int and session==0,'COLLECTOR_SESSION0_REQUIRED');return copy.deepcopy(value)

class CollectorRevisionEvidence:
 """Observed protected bytes, deliberately not a ProtectedActivation or grant."""
 execution_authority=False
 def __init__(self,root,kernel,security,identity):
  self._root=root;self._kernel=kernel;self._security=security;self._identity=identity;self._files={};self._descriptor=None
 @property
 def service_sid(self):return self._identity['service_sid']
 @property
 def code_root(self):return self._root/'code'
 @property
 def manifest_sha256(self):return self._descriptor['service_plan']['manifest_sha256']
 @property
 def descriptor(self):return copy.deepcopy(self._descriptor)
 def _read(self,path,limit,anchor):
  raw,stamp=self._security.read_file(path,limit,self._kernel,self.service_sid,anchor)
  self._files[path]=(limit,anchor,stamp,hashlib.sha256(raw).hexdigest());return raw
 def require_current(self):
  try:
   _need(_identity(self._kernel)==self._identity,'COLLECTOR_IDENTITY_CHANGED')
   for path,(limit,anchor,before,digest) in self._files.items():
    raw,current=self._security.read_file(path,limit,self._kernel,self.service_sid,anchor)
    _need(current==before and hashlib.sha256(raw).hexdigest()==digest,'COLLECTOR_REVISION_CHANGED')
   for relative in getattr(self,'_inventory',()):self._kernel.require_readonly(self.code_root/relative,self.service_sid,self.code_root)
   if hasattr(self,'_verifier'):
    _need(self._verifier(self.code_root,self.manifest_sha256)['manifest']==self._manifest,'COLLECTOR_CAPSULE_CHANGED')
   return True
  except CollectorActivationBlocked:raise
  except Exception:raise CollectorActivationBlocked('COLLECTOR_READMISSION_REJECTED') from None

def _verify_capsule(evidence,security):return security._admit_capsule(evidence)

def read_collector_revision(service_root,*,kernel=None):
 """Real read-only gates; injected unit kernel is never execution approval."""
 try:
  security=_load_security();root=security.local(service_root)
  kernel=_WindowsCollectorKernel(security) if kernel is None else kernel
  identity=_identity(kernel);ev=CollectorRevisionEvidence(root,kernel,security,identity)
  anchor=root/'activation';pointer=security.parse(ev._read(anchor/'current.json',8192,anchor))
  _keys(pointer,('schema','revision_id','descriptor_sha256'));_need(pointer['schema']==POINTER_SCHEMA)
  _label(pointer['revision_id']);_digest(pointer['descriptor_sha256'])
  revision=anchor/'revisions'/pointer['revision_id'];raw=ev._read(revision/'descriptor.json',262144,anchor)
  _need(hashlib.sha256(raw).hexdigest()==pointer['descriptor_sha256']);descriptor=security.parse(raw)
  _keys(descriptor,('schema','revision_id','activation_plan_sha256','service_plan','resource_receipt_sha256',
                   'collector_profile_sha256','source_manifest_sha256','qualification_refs'))
  _need(descriptor['schema']==DESCRIPTOR_SCHEMA and descriptor['revision_id']==pointer['revision_id'])
  for key in ('activation_plan_sha256','resource_receipt_sha256','collector_profile_sha256','source_manifest_sha256'):_digest(descriptor[key])
  refs=descriptor['qualification_refs'];_keys(refs,('phase_id','source_evidence_sha256','capacity_evidence_sha256','operational_admission_sha256'))
  _label(refs['phase_id'])
  for key in ('source_evidence_sha256','capacity_evidence_sha256','operational_admission_sha256'):_digest(refs[key])
  plan=descriptor['service_plan'];_need(type(plan) is dict)
  _need(plan['root']==str(root) and plan['code']==str(root/'code') and plan['state']==str(root/'state'))
  _need(plan['service_sid']==identity['service_sid'] and plan['computer_name'].casefold()==identity['computer_name'].casefold())
  _digest(plan['manifest_sha256']);ev._descriptor=copy.deepcopy(descriptor)
  raw=ev._read(revision/'profile.json',32768,anchor)
  _need(hashlib.sha256(raw).hexdigest()==descriptor['collector_profile_sha256']==plan['collector_profile_sha256'])
  report=_verify_capsule(ev,security);manifest=report['manifest']
  # These imports occur only after the existing admitted-byte verifier has
  # verified the closed capsule and enabled its pinned runtime source loader.
  from unified_system.collector_service_plan import _check_manifest,lab_release
  from unified_system.collector_profile import decode_collector_profile
  _check_manifest(plan,manifest)
  ev._manifest=copy.deepcopy(manifest);ev._verifier=lab_release.verify_capsule
  _need(manifest['schema']=='unified.lab-release.collector.v1')
  _need(descriptor['collector_profile_sha256']==manifest['files'][manifest['collector_profile']]['sha256'])
  source=ev._read(ev.code_root/manifest['source_manifest'],262144,ev.code_root)
  _need(hashlib.sha256(source).hexdigest()==descriptor['source_manifest_sha256']==plan['source_manifest_sha256'])
  decode_collector_profile(raw,manifest_sha256=descriptor['source_manifest_sha256'])
  ev._inventory=tuple([*manifest['directories'],*manifest['files'],'lab-release.json'])
  # Existing verifier streams every file, including zero-length members. Reuse
  # it on readmission rather than buffering each potentially 512-MiB runtime
  # member through the nonempty activation-document reader.
  ev._read(ev.code_root/'lab-release.json',32*1024*1024,ev.code_root)
  ev.require_current();return ev
 except CollectorActivationBlocked:raise
 except Exception:raise CollectorActivationBlocked('COLLECTOR_ACTIVATION_REJECTED') from None

def read_protected_collector_activation(service_root):
 read_collector_revision(service_root)
 # Hashes/qualification_refs/evidence alone cannot issue authority. No callback
 # injection is accepted as a substitute for the unreviewed operational adapter.
 raise CollectorActivationBlocked('OPERATIONAL_ADAPTER_NOT_AVAILABLE')

def run_protected_collector(grant,*,stop_event=None):
 # No neutral owned-process adapter, PSM1 parity or reviewed SCM STOP transport.
 raise CollectorActivationBlocked('COLLECTOR_RUNTIME_UNIMPLEMENTED')
