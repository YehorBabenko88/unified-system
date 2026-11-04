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


class RawModuleDispatchTests(unittest.TestCase):
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
