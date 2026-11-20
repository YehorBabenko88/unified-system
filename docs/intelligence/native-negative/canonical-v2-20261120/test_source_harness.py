"""Pure calibration of source/selection/retirement gates; never native proof."""
import importlib.util,json,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('canonical_source_harness',ROOT/'source_harness.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
class SourceHarnessCalibrationTests(unittest.TestCase):
 def test_exact_case_ids_reject_duplicates_missing_extra_and_failure_ids(self):
  ids=['test_fixture.NativeTests.test_current_generation','test_fixture.NativeTests.test_unknown_no_job']
  self.assertEqual(h.validate_ids(ids,ids),ids)
  for actual in (ids[:1],ids+[ids[0]],ids+['test_fixture.NativeTests.test_extra'],['_FailedTest.test_fixture']):
   with self.assertRaises(ValueError):h.validate_ids(actual,ids)
 def test_literal_denials_and_every_raw_owner_pin_are_required(self):
  manifest={'schema':h.MANIFEST_SCHEMA,'public_submit':'DENY','public_http_endpoint':False,'full_scientific_e2e':False,'positive_job_or_worker_admission':False,'quota_or_assignment_issuer':False,'root_modules_sha256':{name:'a'*64 for name in h.OWNER_MODULES}}
  bindings={name:{'sha256':'a'*64} for name in h.OWNER_MODULES}
  h.validate_manifest(manifest,bindings)
  for key in ('public_http_endpoint','full_scientific_e2e','positive_job_or_worker_admission','quota_or_assignment_issuer'):
   bad=manifest.copy();bad[key]=0
   with self.assertRaises(ValueError):h.validate_manifest(bad,bindings)
  with self.assertRaises(ValueError):h.validate_manifest(manifest,{'unified_system/consul_authority.py':{'sha256':'b'*64}})
 def test_no_skip_failure_or_partial_native_execution_can_pass(self):
  from types import SimpleNamespace
  good=SimpleNamespace(wasSuccessful=lambda:True,testsRun=22,skipped=[],expectedFailures=[],unexpectedSuccesses=[])
  self.assertTrue(h.result_passed(good,22))
  for result in (None,SimpleNamespace(wasSuccessful=lambda:False,testsRun=22,skipped=[],expectedFailures=[],unexpectedSuccesses=[]),SimpleNamespace(wasSuccessful=lambda:True,testsRun=22,skipped=[('x','skip')],expectedFailures=[],unexpectedSuccesses=[]),SimpleNamespace(wasSuccessful=lambda:True,testsRun=21,skipped=[],expectedFailures=[],unexpectedSuccesses=[])):
   self.assertFalse(h.result_passed(result,22))
 def test_owned_process_retirement_refuses_missing_live_foreign_or_ambiguous_pid(self):
  rows=[{'pid':1,'returncode':0},{'pid':2,'returncode':-9},{'pid':3,'returncode':0}]
  h.validate_retirement(rows,3)
  for bad in (rows[:2],rows+[rows[0]],[{'pid':True,'returncode':0}]*3,[{'pid':1,'returncode':None}]*3):
   with self.assertRaises(ValueError):h.validate_retirement(bad,3)
 def test_original_native_case_sets_are_preserved_and_pure_guards_are_separate(self):
  repo=ROOT.parents[3]
  old_negative=json.loads((repo/'docs/intelligence/native-negative/EXPECTED-TESTS.json').read_bytes())
  new_negative=json.loads((ROOT/'EXPECTED-TESTS.json').read_bytes())
  old_research=json.loads((repo/'docs/intelligence/research-identity/native-profile-v2-20261109/EXPECTED-TESTS.json').read_bytes())
  new_research=json.loads((repo/'docs/intelligence/research-identity/native-profile-v3-20261120/EXPECTED-TESTS.json').read_bytes())
  self.assertEqual(old_negative,new_negative)
  mapping=json.loads((repo/'docs/intelligence/canonical-native-profile/case-cutover-map.json').read_bytes())
  self.assertEqual(mapping['old_ids'],old_research);self.assertEqual(mapping['new_ids'],new_research)
  self.assertEqual(len(mapping['old_ids']),len(set(mapping['new_ids'])))
  self.assertEqual([mapping['old_to_new'][name] for name in old_research],new_research)
  guards=json.loads((ROOT/'ROOT-GUARD-TESTS.json').read_bytes());self.assertEqual(len(guards),27)
  self.assertNotEqual(set(guards),set(new_research))

 def test_explicit_native_modules_match_every_retained_case_without_importing_them(self):
  repo=ROOT.parents[3]
  manifest=json.loads((repo/'release/integration/native-negative-v2/manifest.json').read_bytes())
  bindings={name:{'sha256':__import__('hashlib').sha256((repo/name).read_bytes()).hexdigest()} for name in h.OWNER_MODULES}
  h.validate_manifest(manifest,bindings)
  for profile in manifest['profiles'].values():
   expected=json.loads((repo/profile['expected_cases']).read_bytes())
   self.assertEqual(h.validate_ids(h.declared_ids(repo,profile['test_modules']),expected),sorted(expected))
 def test_active_workflows_have_no_retired_checkout_and_keep_native_jobs(self):
  repo=ROOT.parents[3]
  for file in ('gateway-native-negative.yml','gateway-research-identity.yml'):
   text=(repo/'.github/workflows'/file).read_text()
   self.assertNotIn('bybit-cluster-grid',text);self.assertNotIn('--grid-',text)
   self.assertIn('windows-latest',text);self.assertIn('ubuntu-24.04',text)
   self.assertIn('fetch_consul.py',text);self.assertIn('--consul-binary',text)
   self.assertIn('test_source_harness.py',text)


 def test_bootstraps_reject_git_override_before_any_process(self):
  import os,subprocess,types
  from unittest.mock import patch
  repo=ROOT.parents[3]
  for relative in ('docs/intelligence/native-negative/canonical-v2-20261120/run_qualification.py','docs/intelligence/research-identity/native-profile-v3-20261120/run_qualification.py'):
   file=repo/relative;module=types.ModuleType('inert_bootstrap');module.__file__=str(file)
   exec(compile(file.read_bytes(),str(file),'exec'),module.__dict__)
   with patch.dict(os.environ,{'GIT_DIR':'foreign-source'}),patch.object(subprocess,'check_output',side_effect=AssertionError('PROCESS_FORBIDDEN')):
    with self.assertRaisesRegex(ValueError,'GIT_ENV_OVERRIDE_REJECTED'):module.main()
 def test_bootstrap_head_mismatch_refuses_before_helper_execution(self):
  import os,subprocess,sys,types
  from unittest.mock import patch
  file=ROOT/'run_qualification.py';module=types.ModuleType('inert_bootstrap');module.__file__=str(file)
  exec(compile(file.read_bytes(),str(file),'exec'),module.__dict__)
  with patch.object(sys,'argv',[str(file),'--expected-head','a'*40]),patch.object(subprocess,'check_output',return_value=('b'*40).encode()) as mocked:
   with self.assertRaisesRegex(ValueError,'HEAD_MISMATCH'):module.main()
   self.assertEqual(mocked.call_count,1)
   self.assertEqual(mocked.call_args.args[0][-2:],['rev-parse','HEAD'])

 def test_expected_failure_and_unexpected_success_are_not_native_pass(self):
  result=unittest.TestResult();result.testsRun=21
  self.assertTrue(h.result_passed(result,21))
  result.expectedFailures=[('case','expected failure')]
  self.assertTrue(result.wasSuccessful())
  self.assertFalse(h.result_passed(result,21))
  result.expectedFailures=[];result.unexpectedSuccesses=['case']
  self.assertFalse(h.result_passed(result,21))

 def test_every_preserved_case_body_matches_declared_protocol_ast_proof(self):
  import ast,hashlib
  repo=ROOT.parents[3]
  proof=json.loads((repo/'docs/intelligence/canonical-native-profile/native-case-method-transform-proof.json').read_bytes())
  self.assertEqual(proof['baseline'],'b3abfb4542df7b28c7f3dd57d5ff34cda5f9746f')
  rows=proof['case_bodies_exact_except_declared_protocol_changes'];self.assertEqual(len(rows),43)
  actual=[]
  for row in rows:
   folder='gateway_native_negative' if row['new_module'] in ('test_actual.py','test_boundary.py') else 'gateway_research_identity'
   tree=ast.parse((repo/'tests'/folder/row['new_module']).read_bytes())
   cls=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name==row['new_class'])
   node=next(node for node in cls.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name==row['new_method'])
   for part in ast.walk(node):
    if hasattr(part,'type_params') and not part.type_params:del part.type_params
   self.assertEqual(hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest(),row['new_ast_sha256'])
   self.assertIs(row['exact_declared_transform'],True)
   actual.append(row['new_module'][:-3]+'.'+row['new_class']+'.'+row['new_method'])
  manifest=json.loads((repo/'release/integration/native-negative-v2/manifest.json').read_bytes())
  expected=[case for profile in manifest['profiles'].values() for case in json.loads((repo/profile['expected_cases']).read_bytes())]
  self.assertEqual(h.validate_ids(actual,expected),sorted(expected))

if __name__=='__main__':unittest.main()
