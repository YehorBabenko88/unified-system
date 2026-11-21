"""Pure canonical source-scope tests; fixtures are inert bytes, never executables."""
import copy,hashlib,os,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from unified_system.service_bootstrap import ActivationBlocked
from unified_system.service_source_admission import StartupSourceAdmission,MODULES
from unified_system.service_module_runtime import protected_programs,serve_module,ENTRIES

class SourceScopeTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
  self.live=True;self.sources={};self.files={}
  for module in MODULES:
   relative='sources/'+module;(self.root/relative).mkdir(parents=True)
   self.sources[module]=dict(root=relative,commit='a'*40,tree='b'*40,version='0.1.0')
  for relative in ('runtime/python.exe','runtime/git.exe','sources/unified_system/unified_system/service_entry.py','sources/unified_system/unified_system/owned_python.py'):
   file=self.root/relative;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(b'inert source fixture')
   self.files[relative]=dict(sha256=hashlib.sha256(file.read_bytes()).hexdigest())
  self.manifest=dict(sources=self.sources,git='runtime/git.exe',files=self.files)
  self.grant=SimpleNamespace(code_root=self.root,require_current=lambda:self.live)
  self.scope=StartupSourceAdmission(self.grant,{},self.manifest)
 def programs(self):
  result={}
  for module,entry in ENTRIES.items():
   port=8766 if module=='market_data' else 8767
   tail=['serve'] if module=='market_data' else ['--host','127.0.0.1','--port',str(port)]
   argv=[str(self.root/'runtime/python.exe'),'-I','-S','-B',str(self.root/'sources/unified_system/unified_system/owned_python.py'),
      '--source-root',str(self.root/'sources'/module),'--dependency-root',str(self.root/'dependencies/site-packages'),
      '--module',entry,'--',*tail]
   result[module]=dict(argv=argv,health_url=f'http://127.0.0.1:{port}/health',env={'MARKET_DATA_PORT':str(port)} if module=='market_data' else {})
  result['math']=dict(argv=['unchanged-math-profile'])
  return dict(programs=result)
 def test_private_program_copy_selects_only_canonical_routes_and_exact_entry_pin(self):
  config=self.programs();before=copy.deepcopy(config);result=protected_programs(config,self.grant,self.manifest)
  self.assertEqual(config,before);self.assertEqual(result['programs']['math'],config['programs']['math'])
  for module in ENTRIES:
   value=result['programs'][module];self.assertEqual(value['argv'][-2:],['--module-source',module])
   self.assertEqual(value['argv'][1:4],['-I','-S','-B'])
   self.assertEqual(value['external_file_pins'][value['argv'][4]],self.files['sources/unified_system/unified_system/service_entry.py']['sha256'])
  self.manifest['files'].clear()
  with self.assertRaises(ActivationBlocked):protected_programs(config,self.grant,self.manifest)
 def test_scope_binds_module_root_commit_and_live_revision(self):
  path=self.root/'sources/market_data'
  self.assertEqual(self.scope.source_scope('market_data',path,'a'*40),path)
  for module,root,sha in [('missing',path,'a'*40),('terminan',path,'a'*40),('market_data',self.root,'a'*40),('market_data',path,'c'*40)]:
   with self.subTest(module=module),self.assertRaises(ActivationBlocked):self.scope.source_scope(module,root,sha)
  self.live=False
  with self.assertRaises(ActivationBlocked):self.scope.source_scope('market_data',path,'a'*40)
 def test_constructor_and_source_records_cannot_mutate_admitted_copy(self):
  self.manifest['sources']['market_data']['commit']='c'*40
  record=self.scope.source_identity('market_data');record['commit']='d'*40
  self.assertEqual(self.scope.source_identity('market_data')['commit'],'a'*40)
 def test_retired_verifier_launch_api_is_absent(self):
  self.assertFalse(hasattr(self.scope,'verification_launch'))
  for module in ('grid','strattester','meta_analyse','unified-system'):
   with self.subTest(module=module),self.assertRaises(ActivationBlocked):self.scope.source_identity(module)
 def test_replaced_source_namespace_and_nonliteral_grants_rejected(self):
  path=self.root/'sources/math';path.rename(path.with_name('retained-original'));path.mkdir()
  with self.assertRaises(ActivationBlocked):self.scope.require_current()
  for grant in ({},SimpleNamespace(require_current=lambda:1)):
   with self.assertRaises(ActivationBlocked):StartupSourceAdmission(grant,{},self.manifest)
 def test_canonical_callback_uses_fixed_main_original_scope_and_admission(self):
  from unified_system import owned_python
  state=self.root/'state';cache=state/'cache';cache.mkdir(parents=True)
  for module in ENTRIES:
   config=self.programs();config.update(state_root=str(state),release_id='fixture');calls=[]
   def main(argv,*,startup_admission):
    self.assertEqual(startup_admission.source_scope(module,self.root/'sources'/module,'a'*40),self.root/'sources'/module)
    calls.append(argv);return 0
   original=config['programs'][module]['argv']
   def owned(*,admitted_run):
    self.assertEqual(sys.argv,original[4:]);return admitted_run()
   with patch.dict(os.environ,UNIFIED_PRIVATE_CACHE_ROOT=str(cache),UNIFIED_MODULE_ID=module,UNIFIED_MODULE_VERSION='0.1.0',UNIFIED_RELEASE_ID='fixture'),patch.object(owned_python,'main',side_effect=owned),patch('unified_system.service_module_runtime.importlib.import_module',side_effect=lambda name:SimpleNamespace(main=main) if name==ENTRIES[module] else self.fail('arbitrary module import')):
    self.assertEqual(serve_module(self.grant,config,self.manifest,module),0)
   self.assertEqual(calls,[['serve'] if module=='market_data' else ['--host','127.0.0.1','--port','8767']])
 def test_selector_drift_rejected_before_source_scope_or_application_import(self):
  for index,value in ((0,'other-python'),(4,'other-bootstrap'),(6,str(self.root/'outside')),(8,str(self.root/'outside')),(10,'foreign:app')):
   for module in ENTRIES:
    config=self.programs();config['programs'][module]['argv'][index]=value
    with self.subTest(index=index,module=module),patch('unified_system.service_module_runtime.StartupSourceAdmission',side_effect=AssertionError('selector refused before scope')):
     with self.assertRaises(ActivationBlocked):serve_module(self.grant,config,self.manifest,module)
 def test_nonloopback_health_or_extra_cli_switch_is_refused(self):
  for module in ENTRIES:
   for mutation in ('host','argv'):
    config=self.programs()
    if mutation=='host':config['programs'][module]['health_url']='http://0.0.0.0:8766/health'
    else:config['programs'][module]['argv'].append('--execute')
    with self.subTest(module=module,mutation=mutation),self.assertRaises(ActivationBlocked):protected_programs(config,self.grant,self.manifest)
 def test_unknown_or_retired_dispatch_never_reaches_capsule_admission(self):
  from unified_system import service_bootstrap as boot
  for module in ('grid','meta_analyse','strattester','missing'):
   with patch.object(boot,'_admit_capsule',side_effect=AssertionError('no retired admission')):
    with self.assertRaises(ActivationBlocked):boot.run_protected_module(self.grant,module)
 def test_admission_failure_precedes_application_constructor(self):
  from unified_system import service_bootstrap as boot
  with patch.object(boot,'_admit_capsule',side_effect=ActivationBlocked('ACTIVATION_CODE_REJECTED')),patch('unified_system.service_module_runtime.serve_module') as serve:
   with self.assertRaises(ActivationBlocked):boot.run_protected_module(self.grant,'terminan')
   serve.assert_not_called()
