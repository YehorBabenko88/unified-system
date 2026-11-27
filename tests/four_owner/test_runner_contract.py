"""Pure calibration; no SourceFence/Git/process/native invocation."""
import importlib.util,json,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('four_contracts',ROOT/'integration/four_owner/contracts.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
class FourOwnerContractTests(unittest.TestCase):
 def manifest(self):return {'schema':c.SCHEMA,'sources':{name:{'commit':'ENCLOSING_HEAD' if name=='unified_system' else 'a'*40} for name in c.OWNERS},'release_status':'NO_GO','execution_authority':False,'trading_authorized':False}
 def test_exact_four_owner_roster_and_closed_denials(self):
  self.assertEqual(set(c.bind_heads(self.manifest(),'b'*40)),set(c.OWNERS))
  for mutate in (lambda x:x['sources'].update(grid={'commit':'a'*40}),lambda x:x['sources'].pop('market_data'),lambda x:x.update(release_status='PASS'),lambda x:x.update(execution_authority=0)):
   m=self.manifest();mutate(m)
   with self.assertRaises(ValueError):c.bind_heads(m,'b'*40)
 def test_exact_case_ids_refuse_missing_extra_duplicate_and_failed_import(self):
  expected=['test_sdk_contracts.CanonicalSdkTests.test_exact_data_trade_to_math_terminal']
  c.require_cases(expected,expected)
  for actual in ([],expected*2,['_FailedTest.test_missing'],expected+['other.Class.test_extra']):
   with self.assertRaises(ValueError):c.require_cases(actual,expected)
 def test_no_failure_skip_or_partial_result_can_qualify(self):
  from types import SimpleNamespace
  good=SimpleNamespace(wasSuccessful=lambda:True,testsRun=2,skipped=[],expectedFailures=[],unexpectedSuccesses=[])
  self.assertTrue(c.result_complete(good,2))
  for field,value in (('testsRun',1),('skipped',[1]),('expectedFailures',[1]),('unexpectedSuccesses',[1])):
   bad=SimpleNamespace(**vars(good));setattr(bad,field,value);self.assertFalse(c.result_complete(bad,2))
 def test_runtime_browser_obligations_remain_mandatory_fail_closed(self):
  report=c.runtime_gate('browser',{'qualification':'PASS_SCOPED'})
  self.assertEqual(report['status'],'BLOCKED');self.assertFalse(report['passed']);self.assertEqual(report['release_status'],'NO_GO')
  self.assertEqual(len(report['preserved_browser_cases']),4);self.assertIn('CANONICAL_STARTUP_ADMISSION_REQUIRED',report['missing_proofs'])
  self.assertIn('CANONICAL_MONITOR_SOURCE_ADAPTER_NOT_CONNECTED',report['missing_proofs'])
if __name__=='__main__':unittest.main()
