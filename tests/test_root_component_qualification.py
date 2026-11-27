"""Pure result, compile and source-scope calibration; no hosted execution."""
import importlib.util,json,pathlib,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class ComponentQualificationTests(unittest.TestCase):
 def helper(self):
  path=ROOT/'scripts/qualify_root_components.py'
  self.assertTrue(path.is_file(),'missing component source qualifier')
  spec=importlib.util.spec_from_file_location('root_component_qualification',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
 def test_exact_success_and_all_non_success_result_categories(self):
  h=self.helper();result=unittest.TestResult();result.testsRun=1;self.assertTrue(h.result_passed(result,1))
  for field in ('skipped','expectedFailures','unexpectedSuccesses','failures','errors'):
   bad=unittest.TestResult();bad.testsRun=1;getattr(bad,field).append(('probe','refusal'));self.assertFalse(h.result_passed(bad,1),field)
  result.testsRun=2;self.assertFalse(h.result_passed(result,1))
 def test_case_inventory_refuses_missing_duplicate_extra_and_failed_loader(self):
  h=self.helper();ids=['test_fixture.Probe.test_case'];self.assertEqual(h.require_ids(ids,ids),ids)
  for actual in ([],ids+ids,ids+['test_fixture.Probe.test_extra'],['unittest.loader._FailedTest.test_fixture']):
   with self.assertRaises(ValueError):h.require_ids(actual,ids)
 def test_compile_preserves_semantic_checks_without_execution_or_bytecode(self):
  h=self.helper()
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp);valid=root/'valid.py';valid.write_text("raise AssertionError('MUST_NOT_EXECUTE')\n")
   self.assertEqual(h.compile_sources(root,('valid.py',)),1);self.assertEqual(list(root.iterdir()),[valid])
   for invalid in ('break\n','return 1\n','continue\n'):
    valid.write_text(invalid)
    with self.assertRaises(SyntaxError):h.compile_sources(root,('valid.py',))
 def test_fresh_evidence_must_be_outside_source_and_unoccupied(self):
  h=self.helper()
  with tempfile.TemporaryDirectory() as tmp:
   base=pathlib.Path(tmp);root=base/'source';root.mkdir()
   for out in (root,root/'nested',base):
    with self.assertRaises(ValueError):h.require_output(root,out)
   self.assertEqual(h.require_output(root,base/'fresh'),base/'fresh')
 def test_preserved_rosters_include_all_original_cases_and_physical_nodes(self):
  h=self.helper();groups=h.load_groups(ROOT)
  self.assertEqual({k:len(v['expected_ids']) for k,v in groups.items()},{'final':162,'supervisor':132,'combined':2,'fleet':15})
  self.assertEqual(len(groups['final']['preserved_prior_ids']),145)
  self.assertTrue(set(groups['final']['preserved_prior_ids'])<=set(groups['final']['expected_ids']))
  self.assertIn('test_combined_control_plane.CombinedControlPlaneTests.test_six_node_fleet_visible_to_lifecycle_without_execution_authority',groups['combined']['expected_ids'])

class ComponentWorkflowPreservationTests(unittest.TestCase):
 def test_push_main_only_preserves_every_prior_pull_path_and_python_axis(self):
  import ast
  folder=ROOT/'docs/qualification/root-components-20261120/original-source'
  names={'final-integration.yml':'final-integration.yml','combined-infrastructure.yml':'combined-infrastructure.yml','five-module-infra.yml':'four-owner-infra.yml','supervisor-local-integration.yml':'supervisor-local-integration.yml'}
  for old,new in names.items():
   original=(folder/(old+'.txt')).read_text();current=(ROOT/'.github/workflows'/new).read_text()
   self.assertIn('  pull_request:',current);self.assertIn('    branches: [main]',current)
   if old=='supervisor-local-integration.yml':
    before=next(x.strip() for x in original.splitlines() if x.strip().startswith('paths:'))
    after=next(x.strip() for x in current.splitlines() if x.strip().startswith('paths:'))
    self.assertTrue(set(ast.literal_eval(before.split(':',1)[1]))<=set(ast.literal_eval(after.split(':',1)[1])))
   for axis in ('3.11','3.12','3.13','3.12.10'):
    if "'"+axis+"'" in original:self.assertIn("'"+axis+"'",current)
  self.assertFalse((ROOT/'.github/workflows/five-module-infra.yml').exists())


if __name__=='__main__':
 import sys
 if unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]).countTestCases()!=6:raise ValueError('ALL_SIX_COMPONENT_CALIBRATIONS_REQUIRED')
 unittest.main()
