"""Pure proposed research permissions; no activation or network effects."""
import copy, unittest
from unified_system.data_first_policy import validate_data_first_grant

class PolicyTests(unittest.TestCase):
 def setUp(self):
  self.manifest={'sources':{'strattester':{'commit':'a'*40}}}
  self.value=dict(schema='unified.data-first-runtime.v1',source_commit='a'*40,
   strategy_fingerprints=['b'*64],categories=['linear'],network_scope='BYBIT_PUBLIC_GET_ONLY',
   workspace_relative='data-first',limits=dict(timeout_seconds=120,ram_limit_mb=1024,
    max_pages=5,max_observations=10000,requests_per_second=2))
 def test_detached_closed_policy_matches_exact_stratt_source(self):
  result=validate_data_first_grant(self.value,self.manifest)
  self.assertEqual(result,self.value);result['categories'].append('spot')
  self.assertEqual(self.value['categories'],['linear'])
 def test_missing_unknown_or_unsafe_permissions_reject_without_private_details(self):
  changes=[lambda x:x.update(source_commit='c'*40),lambda x:x.update(network_scope='ANY'),
   lambda x:x.update(workspace_relative='../foreign'),lambda x:x.update(extra='PRIVATE'),
   lambda x:x.update(strategy_fingerprints=[]),lambda x:x.update(strategy_fingerprints=['b'*64]*2),
   lambda x:x.update(categories=['linear','linear']),lambda x:x.update(categories=['options']),
   lambda x:x['limits'].update(timeout_seconds=True),lambda x:x['limits'].update(ram_limit_mb=63),
   lambda x:x['limits'].update(max_pages=101),lambda x:x['limits'].update(max_observations=1000001),
   lambda x:x['limits'].update(requests_per_second=float('nan')),
   lambda x:x['limits'].update(requests_per_second=True),lambda x:x['limits'].update(secret='PRIVATE')]
  for change in changes:
   value=copy.deepcopy(self.value);change(value)
   with self.subTest(value=value),self.assertRaises(ValueError) as error:
    validate_data_first_grant(value,self.manifest)
   self.assertEqual(str(error.exception),'DATA_FIRST_GRANT_REJECTED')
  with self.assertRaises(ValueError):validate_data_first_grant(None,self.manifest)

if __name__=='__main__':unittest.main()
