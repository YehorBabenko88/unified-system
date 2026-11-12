"""Pure source contracts/private files; no Windows API/process/service calls."""
import copy
import contextlib
import ctypes
import hashlib
import io
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).absolute().parents[2]
sys.path.insert(0,str(ROOT))
from unified_system import collector_service_plan as policy
from unified_system import collector_service_bootstrap as boot
from unified_system import collector_service_entry as entry
from unified_system import lab_release as lab, service_bootstrap as security
spec=importlib.util.spec_from_file_location('capsule_fixture',ROOT/'tests/collector/test_collector_capsule.py')
fixture_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture_module)

def seal(value):return hashlib.sha256(lab.canonical(value)).hexdigest()

class Boundary:
 def __init__(self):self.calls=[]
 def sid(self,name):self.calls.append(name);return 'S-1-5-80-1-2-3-4-5'
 def computer_name(self):return 'UNIT-HOST'
 def native_tools(self):return {n:{'path':str(ROOT/(n+'.exe')),'sha256':'f'*64} for n in ('sc','powershell')}

class Kernel:
 def __init__(self):self.user='S-1-5-19';self.session=0;self.sid='S-1-5-80-1-2-3-4-5';self.reject=False;self.reads=[]
 def identity(self):return dict(user_sid=self.user,service_sid=self.sid,computer_name='UNIT-HOST')
 def session_id(self):return self.session
 def require_readonly(self,path,sid,anchor):
  if self.reject:raise ValueError('unit denied ACL')
  self.reads.append(str(path));return True

class ProtectedCollectorTests(unittest.TestCase):
 def setUp(self):
  # The reused security.local() queries drive type independently of the injected
  # identity/ACL kernel. Intercept that readonly API too; never open a real DLL.
  self.drive_queries=0
  owner=self
  class DriveQuery:
   def __call__(self,path):owner.drive_queries+=1;return 3
  class DriveOnly:
   GetDriveTypeW=DriveQuery()
  def inert_dll(name,**kwargs):
   if name!='kernel32':raise AssertionError('REAL_DLL_REJECTED')
   return DriveOnly()
  native=patch.object(ctypes,'WinDLL',side_effect=inert_dll,create=True);native.start();self.addCleanup(native.stop)
  self.temp=tempfile.TemporaryDirectory(prefix='collector-protected-unit-');self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name).resolve();self.capsule=self.root/'capsule';self.capsule.mkdir()
  self.manifest=fixture_module.fixture(self.capsule)
  profile=dict(schema='unified.data-only-collector.profile.v1',mode='SYNTHETIC_OFFLINE',
   grid_launch_profile='grid.data-only-collector.v1',context_id='1'*32,store_id='12345678-1234-4123-8123-123456789abc',
   source_manifest_sha256=self.manifest['files']['source-manifest.json']['sha256'],
   instrument_identity='synthetic-btcusdt-v1',limits=dict(frames=1,frame_bytes=1048576,raw_bytes=4194304,duration_seconds=10),
   network=dict(rest=False,websocket=False),features=dict(trading=False,training=False,math=False,public_submit=False,authority_mutation=False),
   logging=dict(schema='unified.collector.logging.v1',max_file_bytes=16384,file_count=2))
  self.put('collector.json',lab.canonical(profile))
  # Explicit fixture construction of canonical primary LF source, never product
  # normalization of candidate bytes or executable invocation.
  for name,source in policy.REVIEWED_FILES.items():self.put(name,source.read_bytes().replace(b'\r\n',b'\n'))
  self.put('sources/grid/grid/ml_windows_job.py',b'# INERT unit metadata, no Job execution\n')
  self.put('runtime/nssm/nssm.exe',b'INERT NSSM')
  # The test never claims these inert bytes are the actual reviewed NSSM vendor.
  self.nssm_patch=patch.object(policy,'NSSM_PIN',self.manifest['files']['runtime/nssm/nssm.exe']['sha256']);self.nssm_patch.start();self.addCleanup(self.nssm_patch.stop)
  self.write_manifest();self.boundary=Boundary()
 def put(self,name,raw):
  path=self.capsule/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
  self.manifest['files'][name]=fixture_module.pin(raw)
  if name.startswith('sources/'):
   _,source,relative=name.split('/',2);self.manifest['sources'][source]['file_pins'][relative]=fixture_module.source_pin(raw)
  self.manifest['directories']=sorted({p.as_posix() for f in self.manifest['files'] for p in Path(f).parents if str(p)!='.'})
 def write_manifest(self):
  raw=lab.canonical(self.manifest);(self.capsule/'lab-release.json').write_bytes(raw);self.digest=hashlib.sha256(raw).hexdigest()
 def plan(self):return policy.collector_service_plan(self.capsule,self.digest,self.root/'service','install1','node1',self.boundary)
 def revision(self):
  self.plan_value=self.plan();service_root=Path(self.plan_value['root']);service_root.mkdir()
  import shutil
  shutil.copytree(self.capsule,service_root/'code')
  revision=service_root/'activation/revisions/r1';revision.mkdir(parents=True)
  raw=(self.capsule/'collector.json').read_bytes();(revision/'profile.json').write_bytes(raw)
  self.descriptor=dict(schema=boot.DESCRIPTOR_SCHEMA,revision_id='r1',activation_plan_sha256='a'*64,
   service_plan=self.plan_value,resource_receipt_sha256='b'*64,collector_profile_sha256=seal(json.loads(raw)),
   source_manifest_sha256=self.manifest['files']['source-manifest.json']['sha256'],
   qualification_refs=dict(phase_id='unit-phase',source_evidence_sha256='c'*64,capacity_evidence_sha256='d'*64,operational_admission_sha256='e'*64))
  (revision/'descriptor.json').write_bytes(lab.canonical(self.descriptor))
  (service_root/'activation/current.json').write_bytes(lab.canonical(dict(schema=boot.POINTER_SCHEMA,revision_id='r1',descriptor_sha256=seal(self.descriptor))))
  self.kernel=Kernel();return service_root
 def read(self,root):
  with patch.object(boot,'_load_security',return_value=security),patch.object(boot,'_verify_capsule',side_effect=lambda ev,s:lab.verify_capsule(ev.code_root,ev.manifest_sha256)):
   return boot.read_collector_revision(root,kernel=self.kernel)
 def test_actual_plan_and_exact_argv(self):
  plan=self.plan();self.assertEqual(plan['schema'],policy.SCHEMA);self.assertEqual(policy.check_collector_service_plan(plan),self.manifest)
  proof=policy.expected_collector_service(plan)
  self.assertEqual(proof['parameters'],'-I -S -B "'+plan['entry']+'"');self.assertEqual(proof['account'],'NT AUTHORITY\\LocalService')
  self.assertEqual(plan['role'],'COLLECTOR');self.assertFalse(proof['execution_authority'])
 def test_raw_entry_and_policy_pins_match_exact_owned_source_bytes(self):
  self.assertEqual(hashlib.sha256((ROOT/'unified_system/collector_service_bootstrap.py').read_bytes()).hexdigest(),entry.BOOTSTRAP_SHA256)
  self.assertEqual(entry.BOOTSTRAP_SHA256,policy.BOOTSTRAP_PIN)
  self.assertEqual(hashlib.sha256((ROOT/'unified_system/collector_service_entry.py').read_bytes()).hexdigest(),policy.ENTRY_PIN)
  self.assertEqual(boot.SECURITY_SHA256,policy.SECURITY_PIN)
 def test_v1_schema_and_extra_fields_rejected(self):
  for change in ({'schema':'unified.owned-stopped-service.v1'},{'extra':False},{'role':'WORKER'},{'parameters':'-m unified_system.collector_entry'}):
   plan=self.plan();plan.update(change);plan['plan_sha256']=seal({k:v for k,v in plan.items() if k!='plan_sha256'})
   with self.subTest(change=change),self.assertRaises(policy.CollectorServiceBlocked):policy.check_collector_service_plan(plan)
 def test_enum_string_subclass_cannot_spoof_canonical_value(self):
  class Spoof(str):
   def __eq__(self,other):return True
   __hash__=str.__hash__
  for field in ('schema','role','activation'):
   plan=self.plan();plan[field]=Spoof('WRONG');plan['plan_sha256']=seal({k:v for k,v in plan.items() if k!='plan_sha256'})
   with self.subTest(field=field),self.assertRaises(policy.CollectorServiceBlocked):policy.check_collector_service_plan(plan)
 def test_plan_rejects_key_subclass_before_equality_or_verifier(self):
  touched=[]
  class Key(str):
   def __eq__(self,other):touched.append('equality');return super().__eq__(other)
   __hash__=str.__hash__
  plan=self.plan();value=plan.pop('schema');plan[Key('schema')]=value;touched.clear()
  with patch.object(policy.lab_release,'verify_capsule',side_effect=AssertionError('verifier reached')) as verifier:
   with self.assertRaises(policy.CollectorServiceBlocked):policy.check_collector_service_plan(plan)
  self.assertEqual(touched,[]);verifier.assert_not_called()
 def test_all_scalar_subclasses_and_nested_keys_deny_before_verifier(self):
  class Sub(str):pass
  original=self.plan()
  for field in policy.FIELDS-{'native_tools'}:
   plan=copy.deepcopy(original);plan[field]=Sub(plan[field])
   with self.subTest(field=field),patch.object(policy.lab_release,'verify_capsule',side_effect=AssertionError('verifier reached')) as verifier:
    with self.assertRaises(policy.CollectorServiceBlocked):policy.check_collector_service_plan(plan)
    verifier.assert_not_called()
  for depth in (0,1):
   plan=copy.deepcopy(original);target=plan['native_tools'] if depth==0 else plan['native_tools']['sc']
   key=next(iter(target));target[Sub(key)]=target.pop(key)
   with self.subTest(depth=depth),patch.object(policy.lab_release,'verify_capsule',side_effect=AssertionError('verifier reached')) as verifier:
    with self.assertRaises(policy.CollectorServiceBlocked):policy.check_collector_service_plan(plan)
    verifier.assert_not_called()
 def test_source_tamper_denies_before_sid(self):
  self.put('sources/unified-system/unified_system/collector_service_entry.py',b'evil');self.write_manifest()
  with self.assertRaises(policy.CollectorServiceBlocked):self.plan()
  self.assertEqual(self.boundary.calls,[])
 def test_plan_paths_seal_and_native_tools_are_closed(self):
  for change in ({'state':str(self.root/'outside')},{'service_sid':'S-1-5-18'},{'plan_sha256':'0'*64},{'native_tools':{}},{'node_id':True}):
   plan=self.plan();plan.update(change)
   if 'plan_sha256' not in change:plan['plan_sha256']=seal({k:v for k,v in plan.items() if k!='plan_sha256'})
   with self.subTest(change=change),self.assertRaises(policy.CollectorServiceBlocked):policy.check_collector_service_plan(plan)
 def test_actual_revision_reader_returns_evidence_not_authority(self):
  evidence=self.read(self.revision());self.assertFalse(evidence.execution_authority);self.assertTrue(evidence.require_current());self.assertGreater(len(self.kernel.reads),10)
  self.assertGreater(self.drive_queries,0) # Inert boundary was actually reached.
 def test_identity_session_and_acl_denied(self):
  root=self.revision()
  for field,value in [('user','S-1-5-18'),('session',1),('session',False),('sid','S-1-5-80-9-9-9-9-9'),('reject',True)]:
   old=getattr(self.kernel,field);setattr(self.kernel,field,value)
   with self.subTest(field=field,value=value),self.assertRaises(boot.CollectorActivationBlocked):self.read(root)
   setattr(self.kernel,field,old)
 def test_revision_rechecks_mutation_and_identity(self):
  root=self.revision();evidence=self.read(root);self.kernel.session=1
  with self.assertRaises(boot.CollectorActivationBlocked):evidence.require_current()
  self.kernel.session=0;(root/'activation/revisions/r1/profile.json').write_bytes(b'{}\n')
  with self.assertRaises(boot.CollectorActivationBlocked):evidence.require_current()
 def test_readmission_checks_whole_inventory_and_acl(self):
  root=self.revision();evidence=self.read(root)
  (root/'code/extra.txt').write_bytes(b'extra')
  with self.assertRaises(boot.CollectorActivationBlocked):evidence.require_current()
  (root/'code/extra.txt').unlink();self.kernel.reject=True
  with self.assertRaises(boot.CollectorActivationBlocked):evidence.require_current()
 def test_raw_entry_never_runs_without_operational_adapter(self):
  calls=[]
  def deny(root):calls.append(root);raise boot.CollectorActivationBlocked('OPERATIONAL_ADAPTER_NOT_AVAILABLE')
  namespace={'read_protected_collector_activation':deny,'run_protected_collector':lambda *_:self.fail('runtime reached')}
  flags=type('Flags',(),dict(isolated=1,no_site=1,dont_write_bytecode=1))()
  with patch.object(entry.sys,'flags',flags),patch.object(entry,'_load_bootstrap',return_value=(namespace,self.root)),contextlib.redirect_stdout(io.StringIO()):
   self.assertEqual(entry.main([]),78);self.assertEqual(entry.main(['--collector-worker']),78)
  self.assertEqual(calls,[self.root,self.root])
 def test_duplicate_pointer_and_descriptor_substitution_rejected(self):
  root=self.revision();pointer=root/'activation/current.json';original=pointer.read_bytes()
  pointer.write_bytes(b'{"schema":"x","schema":"x"}\n')
  with self.assertRaises(boot.CollectorActivationBlocked):self.read(root)
  pointer.write_bytes(original);path=root/'activation/revisions/r1/descriptor.json'
  changed=copy.deepcopy(self.descriptor);changed['service_plan']['service_sid']='S-1-5-80-9-9-9-9-9'
  path.write_bytes(lab.canonical(changed));p=json.loads(original);p['descriptor_sha256']=seal(changed);pointer.write_bytes(lab.canonical(p))
  with self.assertRaises(boot.CollectorActivationBlocked):self.read(root)
 def test_repeated_empty_pinned_member_is_supported(self):
  # Existing capsule format permits empty files; admission must preserve that
  # accepted byte-integrity behavior instead of using read_file's nonempty rule.
  self.put('sources/grid/empty.txt',b'');self.write_manifest()
  evidence=self.read(self.revision());self.assertTrue(evidence.require_current())
 def test_actual_profile_policy_is_checked(self):
  raw=json.loads((self.capsule/'collector.json').read_bytes());raw['context_id']='not-a-context-id'
  self.put('collector.json',lab.canonical(raw));self.write_manifest()
  with self.assertRaises(boot.CollectorActivationBlocked):self.read(self.revision())
 def test_runtime_and_hash_only_approval_always_deny(self):
  root=self.revision()
  with patch.object(boot,'read_collector_revision',return_value=self.read(root)):
   with self.assertRaisesRegex(boot.CollectorActivationBlocked,'OPERATIONAL_ADAPTER_NOT_AVAILABLE'):boot.read_protected_collector_activation(root)
  for value in (None,True,object()):
   with self.assertRaisesRegex(boot.CollectorActivationBlocked,'COLLECTOR_RUNTIME_UNIMPLEMENTED'):boot.run_protected_collector(value)
 def test_raw_entry_rejects_args_before_loading_helper(self):
  with patch.object(entry,'_load_bootstrap',side_effect=AssertionError('must not load')):
   with contextlib.redirect_stdout(io.StringIO()):
    for args in (['--synthetic-offline'],['--state','x'],['--collector-worker','extra']):self.assertEqual(entry.main(args),78)
 def test_raw_entry_rejects_missing_flags(self):
  with patch.object(entry.sys,'flags',type('Flags',(),dict(isolated=0,no_site=0,dont_write_bytecode=0))()),patch.object(entry,'_load_bootstrap',side_effect=AssertionError('must not load')),contextlib.redirect_stdout(io.StringIO()):self.assertEqual(entry.main([]),78)

if __name__=='__main__':unittest.main()
