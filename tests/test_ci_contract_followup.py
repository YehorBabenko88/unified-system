import ast,copy,importlib.util,json,pathlib,sys,tempfile,textwrap,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
class ContractFollowupTests(unittest.TestCase):
 def test_shared_subset_uses_existing_cohort_emitter_not_fixed_sdk_refs(self):
  raw=(ROOT/'.github/workflows/owner-source-suite.yml').read_text()
  self.assertIn('scripts/emit_cohort_checkout_pins.py',raw)
  for owner in ('market_data','math','terminan'):self.assertIn('steps.sdk-pins.outputs.'+owner,raw)
 def test_final_roster_has_explicit_thirteen_id_translation_and_one_gate(self):
  value=json.loads((ROOT/'docs/qualification/root-components-20261120/groups.json').read_bytes());group=value['groups']['final']
  self.assertEqual(len(group['expected_ids']),162);self.assertEqual(len(group['preserved_prior_ids']),145)
  mapping=group['historical_registry_id_map'];self.assertEqual(len(mapping),13)
  self.assertEqual(set(mapping),{x for x in group['original_expected_ids'] if x.startswith('tests.test_integration_registry.')})
  for old,new in mapping.items():self.assertEqual(new,old.replace('tests.test_integration_registry.','tests.test_historical_registry.'));self.assertIn(new,group['expected_ids'])
  self.assertEqual(set(group['preserved_prior_ids']),{mapping.get(x,x) for x in group['original_preserved_prior_ids']})
  self.assertEqual(set(group['expected_ids'])-{mapping.get(x,x) for x in group['original_expected_ids']},{'tests.test_historical_registry_gate.RegistryResultGateTests.test_exact_success_gate_refuses_all_non_success_unittest_outcomes'})
  spec=importlib.util.spec_from_file_location('inert_component_gate',ROOT/'scripts/qualify_root_components.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
  for change in ('missing_prior','wrong_target','missing_gate'):
   altered=copy.deepcopy(value);item=altered['groups']['final']
   if change=='missing_prior':item['preserved_prior_ids'].pop()
   elif change=='wrong_target':item['historical_registry_id_map'][next(iter(mapping))]='foreign.Test.test_fake'
   else:item['expected_ids'].remove('tests.test_historical_registry_gate.RegistryResultGateTests.test_exact_success_gate_refuses_all_non_success_unittest_outcomes')
   with tempfile.TemporaryDirectory() as temporary:
    base=pathlib.Path(temporary);manifest=base/helper.MANIFEST;manifest.parent.mkdir(parents=True);manifest.write_text(json.dumps(altered))
    with self.assertRaises(ValueError):helper.load_groups(base)
 def test_control_inventory_source_root_is_added_after_source_receipt(self):
  raw=(ROOT/'.github/workflows/agent2-control-api.yml').read_text()
  self.assertIn('sys.path.insert(0, str(source_root))',raw)
  self.assertIn("'tests/__init__.py',",raw)
  self.assertLess(raw.index('before = source_receipt()'),raw.index('sys.path.insert(0, str(source_root))'))
  self.assertLess(raw.index('sys.path.insert(0, str(source_root))'),raw.index('suite = unittest.defaultTestLoader'))
  fragment=textwrap.dedent(raw[raw.index('          before = source_receipt()'):raw.index('          stream = io.StringIO()')])
  namespace=dict(pathlib=pathlib,sys=sys,unittest=unittest,source_receipt=lambda:{'fixture_only':True})
  with patch.object(pathlib.Path,'cwd',return_value=ROOT),patch.object(sys,'path',sys.path.copy()):exec(compile(fragment,'<actual-workflow-inventory-only>','exec'),namespace)
  self.assertEqual(len(namespace['test_ids']),16)
  qualifier=ast.parse((ROOT/'scripts/qualify_stand_construction.py').read_bytes())
  expression=next(node.value for node in ast.walk(qualifier) if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='passed' for target in node.targets))
  def accepted(result):return eval(compile(ast.Expression(expression),'<hosted-result-only>','eval'),{'result':result})
  good=unittest.TestResult();good.testsRun=1;self.assertTrue(accepted(good))
  for field in ('failures','errors','skipped','expectedFailures','unexpectedSuccesses'):
   bad=unittest.TestResult();bad.testsRun=1;getattr(bad,field).append(('fixture','refuse'));self.assertFalse(accepted(bad))
  self.assertFalse(accepted(None))
if __name__=='__main__':unittest.main()
