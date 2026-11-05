import hashlib,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unified_system.service_bootstrap import ActivationBlocked
from unified_system.service_source_admission import StartupSourceAdmission,MODULES

class SourceScopeTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
  self.live=True;self.sources={}
  for module in MODULES:
   relative='sources/'+module;(self.root/relative).mkdir(parents=True);self.sources[module]={'root':relative,'commit':'a'*40,'tree':'b'*40}
  self.files={}
  for relative in ('runtime/python.exe','runtime/git.exe','sources/unified-system/unified_system/service_entry.py'):
   path=self.root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'closed-test-fixture')
   self.files[relative]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
  self.grant=SimpleNamespace(code_root=self.root,require_current=lambda:self.live)
  self.manifest={'sources':self.sources,'git':'runtime/git.exe','files':self.files}
  self.config={'programs':{'strattester':{'argv':[str(self.root/'runtime/python.exe')]}}}
  self.scope=StartupSourceAdmission(self.grant,self.config,self.manifest)
 def test_private_program_copy_only_selects_closed_routes_with_exact_entry_pin(self):
  import copy
  from unified_system.service_module_runtime import protected_programs,ENTRIES
  config={'programs':{key:{'argv':[str(self.root/'runtime/python.exe'),'legacy'],'external_file_pins':{}} for key in (*ENTRIES,'math')}}
  before=copy.deepcopy(config);result=protected_programs(config,self.grant,self.manifest)
  self.assertEqual(config,before);self.assertEqual(result['programs']['math'],config['programs']['math'])
  for key in ENTRIES:
   program=result['programs'][key];self.assertEqual(program['argv'][-2:],['--module-source',key])
   self.assertEqual(program['argv'][1:4],['-I','-S','-B'])
   entry=program['argv'][4];self.assertEqual(program['external_file_pins'][entry],self.files['sources/unified-system/unified_system/service_entry.py']['sha256'])
  self.manifest['files'].clear()
  with self.assertRaises(ActivationBlocked):protected_programs(config,self.grant,self.manifest)

 def test_scope_binds_module_root_commit_and_live_revision(self):
  path=self.root/self.sources['strattester']['root']
  self.assertEqual(self.scope.source_scope('strattester',path,'a'*40),path)
  for module,root,head in (('missing',path,'a'*40),('grid',path,'a'*40),('strattester',self.root,'a'*40),('strattester',path,'c'*40)):
   with self.subTest(module=module,root=root,head=head),self.assertRaises(ActivationBlocked):self.scope.source_scope(module,root,head)
  self.live=False
  with self.assertRaises(ActivationBlocked):self.scope.source_scope('strattester',path,'a'*40)
 def test_source_record_and_constructor_inputs_cannot_mutate_admitted_copy(self):
  self.manifest['sources']['strattester']['commit']='c'*40
  record=self.scope.source_identity('strattester');record['commit']='d'*40
  self.assertEqual(self.scope.source_identity('strattester')['commit'],'a'*40)
 def test_fixed_verifier_launch_rechecks_bytes_and_has_no_factory_selector(self):
  command=self.scope.verification_launch('strattester')
  self.assertEqual(command[1:4],['-I','-S','-B']);self.assertEqual(command[-2:],['--verify-module-source','strattester'])
  with self.assertRaises(ActivationBlocked):self.scope.verification_launch('grid')
  (self.root/'runtime/python.exe').write_bytes(b'changed')
  with self.assertRaises(ActivationBlocked):self.scope.verification_launch('strattester')
 def test_replaced_source_namespace_and_nonliteral_grants_rejected(self):
  path=self.root/self.sources['math']['root'];path.rename(path.with_name('retained-original'));path.mkdir()
  with self.assertRaises(ActivationBlocked):self.scope.require_current()
  for grant in ({},SimpleNamespace(require_current=lambda:1)):
   with self.assertRaises(ActivationBlocked):StartupSourceAdmission(grant,self.config,self.manifest)

 def test_control_callback_uses_grid_source_fixed_main_and_original_dependency_root(self):
  import os,sys
  from unittest.mock import patch
  from unified_system import owned_python
  from unified_system.service_module_runtime import serve_module
  fixture,original=RawModuleDispatchTests().control_fixture(self.root)
  self.manifest['files'].update(fixture['files'])
  for value in self.manifest['sources'].values():value['version']='1.0.0'
  state=self.root/'state';cache=state/'cache';cache.mkdir(parents=True)
  self.grant.descriptor={'service_plan':{'role':'SINGLE_PC'}}
  config={'state_root':str(state),'release_id':'fixture','programs':{'grid':{'argv':original,'health_url':'http://127.0.0.1:8766/internal/v2/module/health'}}}
  calls=[]
  def main(argv,*,startup_admission):
   self.assertEqual(startup_admission.source_scope('grid',self.root/'sources/grid','a'*40),self.root/'sources/grid')
   calls.append(argv);return 0
  def owned(*,admitted_run):
   self.assertEqual(sys.argv,['owned-python','--source-root',str(self.root/'sources/grid'),'--dependency-root',str(self.root/'dependencies/site-packages'),'--module','grid.owned_control_service'])
   return admitted_run()
  with patch.dict(os.environ,UNIFIED_PRIVATE_CACHE_ROOT=str(cache),UNIFIED_MODULE_ID='grid',UNIFIED_MODULE_VERSION='1.0.0',UNIFIED_RELEASE_ID='fixture'),patch.object(owned_python,'main',side_effect=owned),patch('unified_system.service_module_runtime.importlib.import_module',side_effect=lambda name:SimpleNamespace(main=main) if name=='grid.owned_control_service' else self.fail('arbitrary import')):
   self.assertEqual(serve_module(self.grant,config,self.manifest,'grid'),0)
  self.assertEqual(calls,[['--execute','--port','8766']])


class RawModuleDispatchTests(unittest.TestCase):
 def test_grid_full_admission_failure_precedes_import_and_constructor(self):
  from unittest.mock import Mock,patch
  from unified_system import service_bootstrap as bootstrap
  with patch.object(bootstrap,'_admit_capsule',side_effect=ActivationBlocked('ACTIVATION_CODE_REJECTED')) as admit,patch('unified_system.service_module_runtime.serve_module') as serve:
   with self.assertRaises(ActivationBlocked) as error:bootstrap.run_protected_module(SimpleNamespace(require_current=lambda:True),'grid')
   self.assertEqual(error.exception.code,'ACTIVATION_CODE_REJECTED');admit.assert_called_once();serve.assert_not_called()

 def control_fixture(self,root):
  entry=root/'sources/unified-system/unified_system/service_entry.py';python=root/'runtime/python.exe'
  manifest={'sources':{'unified-system':{'root':'sources/unified-system'},'grid':{'root':'sources/grid'}},'files':{entry.relative_to(root).as_posix():{'sha256':'f'*64},python.relative_to(root).as_posix():{'sha256':'e'*64}}}
  original=[str(python),'-I','-S','-B',str(entry.with_name('owned_python.py')),'--source-root',str(root/'dependencies/site-packages'),'--dependency-root',str(root/'sources/grid'),'--module','uvicorn','--','grid.coordinator:app','--host','127.0.0.1','--port','8766','--no-access-log']
  return manifest,original

 def test_grid_control_rejects_bootstrap_source_dependency_and_interpreter_selector_drift(self):
  import tempfile
  from unified_system.service_module_runtime import serve_module
  from unittest.mock import Mock,patch
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp).resolve();manifest,original=self.control_fixture(root)
   grant=Mock(code_root=root);grant.descriptor={'service_plan':{'role':'CONTROL'}}
   for index,value in ((0,'arbitrary-python'),(4,str(root/'other.py')),(6,str(root/'sources/grid')),(8,str(root/'other-deps'))):
    bad=list(original);bad[index]=value
    config={'programs':{'grid':{'argv':bad,'health_url':'http://127.0.0.1:8766/internal/v2/module/health'}}}
    with self.subTest(index=index),patch('unified_system.service_module_runtime.StartupSourceAdmission',side_effect=AssertionError('must reject selector drift before scope/import')):
     with self.assertRaises(ActivationBlocked):serve_module(grant,config,manifest,'grid')

 def test_grid_control_original_argv_checked_before_application_import(self):
  from unittest.mock import Mock,patch
  from unified_system.service_module_runtime import serve_module
  for role,argv in (('WORKER',['x']),('CONTROL',['python','-I','-S','-B','legacy','--module','uvicorn','--','foreign:app','--host','127.0.0.1','--port','8766','--no-access-log']),('CONTROL',['python','-I','-S','-B','legacy','--module','uvicorn','--','grid.coordinator:app','--host','0.0.0.0','--port','8766','--no-access-log'])):
   grant=Mock();grant.descriptor={'service_plan':{'role':role}}
   config={'programs':{'grid':{'argv':argv,'health_url':'http://127.0.0.1:8766/internal/v2/module/health'}}}
   with self.subTest(role=role,argv=argv),patch('unified_system.service_module_runtime.StartupSourceAdmission',side_effect=AssertionError('must reject original before constructing source scope')):
    with self.assertRaises(ActivationBlocked):serve_module(grant,config,{},'grid')

 def test_private_program_copy_rewrites_control_but_preserves_generic_worker(self):
  import copy,tempfile
  from unified_system.service_module_runtime import protected_programs,ENTRIES
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp).resolve();entry=root/'sources/unified-system/unified_system/service_entry.py'
   manifest,original=self.control_fixture(root)
   config={'programs':{key:{'argv':['python','legacy']} for key in ENTRIES}}
   config['programs']['grid']={'argv':original,'health_url':'http://127.0.0.1:8766/internal/v2/module/health'}
   before=copy.deepcopy(config);grant=SimpleNamespace(code_root=root,descriptor={'service_plan':{'role':'CONTROL'}})
   rewritten=protected_programs(config,grant,manifest)
   self.assertEqual(config,before);self.assertEqual(rewritten['programs']['grid']['argv'][-2:],['--module-source','grid'])
   grant.descriptor['service_plan']['role']='WORKER'
   self.assertEqual(protected_programs(config,grant,manifest)['programs']['grid'],before['programs']['grid'])

 def test_unknown_module_is_rejected_before_capsule_or_application_import(self):
  from unittest.mock import Mock,patch
  from unified_system import service_bootstrap as bootstrap
  with patch.object(bootstrap,'_admit_capsule',side_effect=AssertionError('must not admit unknown selector')):
   with self.assertRaises(ActivationBlocked):bootstrap.run_protected_module(Mock(),'arbitrary.module')
 def test_admission_failure_precedes_application_constructor(self):
  from unittest.mock import Mock,patch
  from unified_system import service_bootstrap as bootstrap
  with patch.object(bootstrap,'_admit_capsule',side_effect=ActivationBlocked('ACTIVATION_CODE_REJECTED')):
   with self.assertRaises(ActivationBlocked):bootstrap.run_protected_module(Mock(),'terminan')
