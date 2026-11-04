"""Protected entry tests; fake kernel/runtime never qualify native execution."""
import hashlib,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from unified_system import service_bootstrap as bootstrap

ROOT=Path(__file__).resolve().parents[1]
class ProtectedRuntimeTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
  self.checks=0;self.active=True
  def current():
   self.checks+=1
   if not self.active:raise bootstrap.ActivationBlocked('ACTIVATION_REVOKED')
   return True
  self.config={'state_root':str(self.root/'state'),'programs':{'grid':{'env':{}}}}
  self.grant=SimpleNamespace(require_current=current,descriptor={'service_plan':{'role':'WORKER'}},profile={'runtime_config':self.config})
 def test_control_and_single_pc_require_actual_owned_pg_before_runtime(self):
  for role in ('CONTROL','SINGLE_PC'):
   self.grant.descriptor['service_plan']['role']=role
   with patch.object(bootstrap,'_admit_capsule',return_value={}),patch.object(bootstrap,'_runtime_admission',return_value=(self.config,{})),patch('unified_system.service_postgres.read_postgres_ownership',side_effect=ValueError('missing-private-proof')) as read,patch('unified_system.lab_privileges.remove_lab_write_bypass_privileges') as privileges,patch('unified_system.lab_runtime.make_runtime') as make:
    with self.assertRaises(bootstrap.ActivationBlocked):bootstrap.run_protected_runtime(self.grant)
    read.assert_called_once_with(self.grant);privileges.assert_not_called();make.assert_not_called()
 def test_owned_postgres_ready_precedes_make_and_closes_after_runtime_failure(self):
  events=[];self.grant.descriptor['service_plan']['role']='CONTROL'
  pg=SimpleNamespace(start=lambda:events.append('sql-ready'),require_current=lambda:True,close=lambda:events.append('close'))
  def make(*args,**kwargs):events.append('make');raise ValueError('private-runtime-error')
  with patch.object(bootstrap,'_admit_capsule',return_value={}),patch.object(bootstrap,'_runtime_admission',return_value=(self.config,{})),patch('unified_system.service_postgres.read_postgres_ownership',side_effect=lambda grant:(events.append('read-receipt') or pg)),patch('unified_system.lab_privileges.remove_lab_write_bypass_privileges',side_effect=lambda:events.append('privilege-gate')),patch('unified_system.lab_runtime.make_runtime',side_effect=make):
   with self.assertRaises(bootstrap.ActivationBlocked):bootstrap.run_protected_runtime(self.grant)
  self.assertEqual(events,['read-receipt','privilege-gate','sql-ready','make','close'])
 def test_failed_privilege_removal_never_starts_owned_postgres(self):
  events=[];self.grant.descriptor['service_plan']['role']='CONTROL'
  pg=SimpleNamespace(start=lambda:events.append('PG-start'),close=lambda:events.append('close'))
  with patch.object(bootstrap,'_admit_capsule',return_value={}),patch.object(bootstrap,'_runtime_admission',return_value=(self.config,{})),patch('unified_system.service_postgres.read_postgres_ownership',side_effect=lambda grant:(events.append('read-receipt') or pg)),patch('unified_system.lab_privileges.remove_lab_write_bypass_privileges',side_effect=ValueError('private-token-failure')),patch('unified_system.lab_runtime.make_runtime') as make:
   with self.assertRaises(bootstrap.ActivationBlocked):bootstrap.run_protected_runtime(self.grant)
   make.assert_not_called()
  self.assertEqual(events,['read-receipt','close'])
 def test_control_restart_rechecks_receipt_and_revocation_closes_owned_pg(self):
  events=[];self.grant.descriptor['service_plan']['role']='SINGLE_PC'
  def pgcurrent():events.append('pg-current');return self.grant.require_current()
  pg=SimpleNamespace(start=lambda:events.append('sql-ready'),require_current=pgcurrent,close=lambda:events.append('close'))
  def make(config,authorize,**kwargs):
   self.assertTrue(authorize('start','grid'));return object()
  def run(config,runtime,*,stop_event,continuation):
   self.assertIs(continuation(),True);self.active=False;continuation()
  with patch.object(bootstrap,'_admit_capsule',return_value={}),patch.object(bootstrap,'_runtime_admission',return_value=(self.config,{})),patch.object(bootstrap,'_repeat_admission',return_value=(self.config,{})),patch('unified_system.service_postgres.read_postgres_ownership',return_value=pg) as read,patch('unified_system.lab_privileges.remove_lab_write_bypass_privileges'),patch('unified_system.lab_runtime.make_runtime',side_effect=make),patch('unified_system.lab_runtime.run_runtime',side_effect=run):
   with self.assertRaises(bootstrap.ActivationBlocked):bootstrap.run_protected_runtime(self.grant)
   self.assertEqual(read.call_count,2)
  self.assertEqual(events[0],'sql-ready');self.assertEqual(events[-1],'close');self.assertIn('pg-current',events)
 def test_worker_uses_existing_runtime_full_restart_gate_and_cheap_continuation(self):
  auth={'NODE_CREDENTIAL':'c'*64};events=[]
  def make(config,authorize,child_environment):
   events.append('make');self.assertFalse(authorize('stop','grid'));self.assertFalse(authorize('start','unknown'))
   self.assertTrue(authorize('start','grid'));self.assertEqual(child_environment('grid')['NODE_CREDENTIAL'],'c'*64)
   self.assertNotIn('NODE_CREDENTIAL',child_environment('math'));return object()
  def run(config,runtime,*,stop_event,continuation):
   events.append('run');self.assertIs(continuation(),True);self.active=False
   with self.assertRaises(bootstrap.ActivationBlocked):continuation()
  with patch.object(bootstrap,'_admit_capsule',return_value={}) as initial,patch.object(bootstrap,'_runtime_admission',return_value=(self.config,auth)),patch.object(bootstrap,'_repeat_admission',return_value=(self.config,auth)) as restart,patch('unified_system.lab_privileges.remove_lab_write_bypass_privileges'),patch('unified_system.lab_runtime.make_runtime',side_effect=make),patch('unified_system.lab_runtime.run_runtime',side_effect=run):
   self.assertEqual(bootstrap.run_protected_runtime(self.grant),0);initial.assert_called_once();restart.assert_called_once()
  self.assertEqual(events,['make','run']);self.assertFalse((self.root/'state').exists())
 def test_worker_never_reads_or_starts_postgres(self):
  with patch.object(bootstrap,'_admit_capsule',return_value={}),patch.object(bootstrap,'_runtime_admission',return_value=(self.config,{})),patch('unified_system.service_postgres.read_postgres_ownership') as read,patch('unified_system.lab_privileges.remove_lab_write_bypass_privileges'),patch('unified_system.lab_runtime.make_runtime'),patch('unified_system.lab_runtime.run_runtime'):
   self.assertEqual(bootstrap.run_protected_runtime(self.grant),0);read.assert_not_called()
 def test_failed_pg_start_precedes_make_and_closes_owned_boundary(self):
  self.grant.descriptor['service_plan']['role']='CONTROL';events=[]
  def start():events.append('start');raise ValueError('private-pg-failure')
  pg=SimpleNamespace(start=start,close=lambda:events.append('close'))
  with patch.object(bootstrap,'_admit_capsule',return_value={}),patch.object(bootstrap,'_runtime_admission',return_value=(self.config,{})),patch('unified_system.service_postgres.read_postgres_ownership',return_value=pg),patch('unified_system.lab_privileges.remove_lab_write_bypass_privileges'),patch('unified_system.lab_runtime.make_runtime') as make:
   with self.assertRaises(bootstrap.ActivationBlocked):bootstrap.run_protected_runtime(self.grant)
   make.assert_not_called()
  self.assertEqual(events,['start','close'])
 def test_failed_full_admission_precedes_state_or_runtime_effects(self):
  with patch.object(bootstrap,'_admit_capsule',side_effect=bootstrap.ActivationBlocked('ACTIVATION_CODE_REJECTED')),patch('unified_system.lab_runtime.make_runtime') as make:
   with self.assertRaises(bootstrap.ActivationBlocked):bootstrap.run_protected_runtime(self.grant)
   make.assert_not_called()
  self.assertFalse((self.root/'state').exists())
 def test_failed_restart_admission_denies_child_start(self):
  def make(config,authorize,**kwargs):
   self.assertFalse(authorize('start','grid'));return object()
  with patch.object(bootstrap,'_admit_capsule',return_value={}),patch.object(bootstrap,'_runtime_admission',return_value=(self.config,{})),patch.object(bootstrap,'_repeat_admission',side_effect=ValueError('private-error')),patch('unified_system.lab_privileges.remove_lab_write_bypass_privileges'),patch('unified_system.lab_runtime.make_runtime',side_effect=make),patch('unified_system.lab_runtime.run_runtime'):
   self.assertEqual(bootstrap.run_protected_runtime(self.grant),0)

class ExistingAdmissionTests(unittest.TestCase):
 def test_actual_profile_source_failure_precedes_runtime_creation(self):
  from tests import test_service_activation as fixtures
  case=fixtures.ActivationTests('test_roundtrip_protected_artifacts_are_not_runtime_readiness');case.setUp();self.addCleanup(case.doCleanups)
  case.publish();grant=bootstrap.read_protected_activation(case.root,kernel=case.kernel)
  with patch.object(bootstrap,'_admit_capsule',return_value={'manifest':case.fixture.manifest}),patch('unified_system.lab_runtime.verify_sources',side_effect=ValueError('unqualified-source')) as source,patch('unified_system.lab_runtime.make_runtime') as make:
   with self.assertRaises(bootstrap.ActivationBlocked):bootstrap.run_protected_runtime(grant)
   make.assert_not_called();source.assert_called_once_with(grant.code_root,case.fixture.manifest,owner_admitted_root=grant.code_root)
  self.assertFalse((case.root/'state').exists())
 def test_protected_profile_consumes_validator_normalization_before_make(self):
  from tests import test_service_activation as fixtures
  from unified_system import lab_runtime,lab_release
  case=fixtures.ActivationTests('test_roundtrip_protected_artifacts_are_not_runtime_readiness');case.setUp();self.addCleanup(case.doCleanups)
  env=case.profile['runtime_config']['programs']['grid']['env']
  for key in ('ROLE','NODE_ID','NODE_ROLE','TEMP','TMP'):env.pop(key,None)
  case.profile['derivation_receipt']['profile_sha256']=hashlib.sha256(lab_release.canonical(case.profile['runtime_config'])).hexdigest()
  case.publish();grant=bootstrap.read_protected_activation(case.root,kernel=case.kernel)
  expected=lab_runtime.validate_config(grant.profile['runtime_config'],case.fixture.manifest,grant.code_root,hostname=grant.computer_name,offline_context=grant.profile['offline_context'])
  def make(config,authorize,**kwargs):
   self.assertEqual(config,expected);grid=config['programs']['grid']['env']
   self.assertEqual((grid['ROLE'],grid['NODE_ID'],grid['NODE_ROLE']),('worker','PC1','WORKER'));self.assertIn('TEMP',grid)
   return object()
  with patch('unified_system.lab_runtime.verify_sources',return_value={}):
   config,auth=bootstrap._runtime_admission(grant,{'manifest':case.fixture.manifest})
   self.assertEqual(config,expected);self.assertEqual(auth,{'NODE_CREDENTIAL':'C'*64})
   with patch.object(bootstrap,'_admit_capsule',return_value={'manifest':case.fixture.manifest}),patch('unified_system.lab_privileges.remove_lab_write_bypass_privileges'),patch('unified_system.lab_runtime.make_runtime',side_effect=make) as construct,patch('unified_system.lab_runtime.run_runtime'):
    self.assertEqual(bootstrap.run_protected_runtime(grant),0);construct.assert_called_once()

 def test_actual_provision_receipt_is_consumed_before_make_and_owned_close(self):
  from tests import test_service_postgres as fixtures
  case=fixtures.PostgresBoundaryTests('test_consumed_provision_receipt_runtime_start_and_owned_close');case.setUp();self.addCleanup(case.doCleanups)
  receipt=case.provision();grant=case.grant(receipt);config=grant.profile['runtime_config'];events=[]
  def make(config,authorize,**kwargs):
   self.assertTrue(case.boundary.servers[-1].alive());self.assertIn('ready',case.boundary.calls)
   self.assertTrue(authorize('start','grid'));events.append('make');return object()
  with patch.object(bootstrap,'_admit_capsule',return_value={}),patch.object(bootstrap,'_runtime_admission',return_value=(config,{})),patch.object(bootstrap,'_repeat_admission',return_value=(config,{})),patch('unified_system.service_postgres.WindowsPostgresBoundary',return_value=case.boundary),patch('unified_system.lab_privileges.remove_lab_write_bypass_privileges'),patch('unified_system.lab_runtime.make_runtime',side_effect=make),patch('unified_system.lab_runtime.run_runtime'):
   self.assertEqual(bootstrap.run_protected_runtime(grant),0)
  self.assertEqual(events,['make']);self.assertTrue(all(server.closed for server in case.boundary.servers));self.assertEqual(len(case.boundary.servers),2)

 def test_preloaded_candidate_package_is_refused_before_loader_or_metadata(self):
  grant=SimpleNamespace(code_root=Path('/unused'),service_sid='unused',_kernel=None)
  with self.assertRaises(bootstrap.ActivationBlocked) as error:bootstrap._import_verifier(grant,{})
  self.assertEqual(error.exception.code,'ACTIVATION_AMBIENT_IMPORT_REJECTED')

class RawEntryTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
 def test_raw_entry_rejects_unpinned_bootstrap_before_its_code_executes(self):
  entry=self.root/'service/code/sources/unified-system/unified_system/service_entry.py';entry.parent.mkdir(parents=True)
  entry.write_bytes((ROOT/'unified_system/service_entry.py').read_bytes())
  marker=self.root/'EXECUTED';entry.with_name('service_bootstrap.py').write_text('from pathlib import Path;Path('+repr(str(marker))+').touch()')
  result=subprocess.run([sys.executable,'-I','-S','-B',str(entry)],capture_output=True,timeout=10)
  self.assertEqual(result.returncode,78);self.assertEqual(result.stdout.replace(b'\r\n',b'\n'),b'BLOCKED_SERVICE_ACTIVATION\n');self.assertEqual(result.stderr,b'');self.assertFalse(marker.exists())
 def test_exact_reviewed_bootstrap_still_requires_actual_service_token_and_grant(self):
  entry=self.root/'service/code/sources/unified-system/unified_system/service_entry.py';entry.parent.mkdir(parents=True)
  entry.write_bytes((ROOT/'unified_system/service_entry.py').read_bytes().replace(b'\r\n',b'\n'))
  helper=entry.with_name('service_bootstrap.py');helper.write_bytes((ROOT/'unified_system/service_bootstrap.py').read_bytes().replace(b'\r\n',b'\n'))
  from unified_system import installation_service
  self.assertEqual(hashlib.sha256(helper.read_bytes()).hexdigest(),installation_service.SERVICE_BOOTSTRAP_SHA256)
  result=subprocess.run([sys.executable,'-I','-S','-B',str(entry)],capture_output=True,timeout=10)
  self.assertEqual(result.returncode,78);self.assertEqual(result.stdout.replace(b'\r\n',b'\n'),b'BLOCKED_SERVICE_ACTIVATION\n');self.assertEqual(result.stderr,b'')
  self.assertFalse((self.root/'service/activation').exists());self.assertFalse((self.root/'service/state').exists())

 def _source_only_loader_case(self,mode):
  source=self.root/'code/sources/unified-system/unified_system';source.mkdir(parents=True);files={}
  for name in bootstrap.VERIFIER_IMPORTS:
   raw=(ROOT/'unified_system'/name).read_bytes().replace(b'\r\n',b'\n');(source/name).write_bytes(raw)
   files['sources/unified-system/unified_system/'+name]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
  guard=self.root/'code/sources/unified-system/integration/source_guard.py';guard.parent.mkdir();raw=(ROOT/'integration/source_guard.py').read_bytes().replace(b'\r\n',b'\n');guard.write_bytes(raw);files['sources/unified-system/integration/source_guard.py']={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
  (self.root/'manifest.json').write_text(json.dumps({'files':files,'directories':['sources/unified-system/integration']}))
  # Cache matches source timestamp/size but would create a marker if imported.
  script="""import runpy,sys,json,types,py_compile,os,struct,marshal,importlib.util
from pathlib import Path
ns=runpy.run_path(sys.argv[1]);root=Path(sys.argv[2]);source=root/'code/sources/unified-system/unified_system/lab_release.py';marker=root/'CACHE_EXECUTED'
cache=Path(importlib.util.cache_from_source(str(source)));cache.parent.mkdir(exist_ok=True)
info=source.stat();raw=importlib.util.MAGIC_NUMBER+struct.pack('<III',0,int(info.st_mtime),info.st_size)+marshal.dumps(compile('from pathlib import Path;Path('+repr(str(marker))+').touch()',str(source),'exec'));cache.write_bytes(raw)
class Kernel:
 def require_readonly(self,*args):return True
grant=types.SimpleNamespace(code_root=root/'code',_kernel=Kernel(),service_sid='S-1-5-80-1-2-3-4-5')
if sys.argv[3]=='tampered':
 source.write_bytes(('from pathlib import Path;Path('+repr(str(marker))+').touch()'+chr(10)).encode()+source.read_bytes())
 try:ns['_import_verifier'](grant,json.loads((root/'manifest.json').read_text()))
 except ns['ActivationBlocked']:pass
 else:raise AssertionError('tampered verifier accepted')
else:
 verifier,loader=ns['_import_verifier'](grant,json.loads((root/'manifest.json').read_text()));assert callable(verifier.verify_capsule)
if sys.argv[3]=='namespace':
 try:__import__('integration.source_guard')
 except ns['ActivationBlocked']:pass
 else:raise AssertionError('namespace admitted before full closure')
 loader.admit_runtime();module=__import__('integration.source_guard',fromlist=['SourceFence']);assert callable(module.SourceFence)
assert not marker.exists()
"""
  result=subprocess.run([sys.executable,'-I','-S','-B','-c',script,str(ROOT/'unified_system/service_bootstrap.py'),str(self.root),mode],capture_output=True,timeout=10)
  self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'));self.assertFalse((self.root/'CACHE_EXECUTED').exists())

 def test_source_only_verifier_loader_ignores_forged_bytecode_cache(self):self._source_only_loader_case('cache')
 def test_exact_namespace_source_guard_import_requires_full_admission(self):self._source_only_loader_case('namespace')
 def test_verifier_hash_mismatch_never_executes_candidate_module(self):self._source_only_loader_case('tampered')
 def test_entry_and_adapter_pin_exact_lf_bootstrap_bytes(self):
  import re
  from unified_system import installation_service
  helper=(ROOT/'unified_system/service_bootstrap.py').read_bytes().replace(b'\r\n',b'\n')
  entry=(ROOT/'unified_system/service_entry.py').read_bytes().replace(b'\r\n',b'\n')
  pin=re.search(rb"BOOTSTRAP_SHA256='([a-f0-9]{64})'",entry).group(1).decode()
  self.assertEqual(hashlib.sha256(helper).hexdigest(),pin);self.assertEqual(pin,installation_service.SERVICE_BOOTSTRAP_SHA256)
  self.assertEqual(hashlib.sha256(entry).hexdigest(),installation_service.SERVICE_ENTRY_SHA256)

if __name__=='__main__':unittest.main()
