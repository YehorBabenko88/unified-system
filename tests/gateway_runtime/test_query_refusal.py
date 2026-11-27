"""Root refusal boundaries with actual Data/Math source; no issuer grants."""
import json,unittest
from unittest.mock import patch
from pathlib import Path
from market_data import gateway_query as domain
class RootQueryRefusalTests(unittest.TestCase):
 def reader(self):
  from unified_system import market_data_query
  return market_data_query
 def request(self):
  return json.loads((Path(__file__).parent/'query_fixtures'/'actual-query.request.canonical.json').read_bytes())
 def raw(self):return json.dumps(self.request(),sort_keys=True,separators=(',',':')).encode('ascii')
 def test_missing_capability_or_authority_never_reads(self):
  class Store:
   def read(self,*a,**kw):raise AssertionError('OWNER_IO_WITHOUT_AUTHORITY')
  for cap,issuer in ((None,None),(object(),None),(None,object())):
   result=self.reader().read_market_data(self.raw(),owner_read_capability=cap,expected_identity_authority=issuer,pinned_owned_store=Store())
   self.assertEqual(result['status'],'NOT_EXECUTED');self.assertFalse(result['native_authenticated']);self.assertIsNone(result['capabilities'])
 def test_counterfeit_authority_and_capability_never_read(self):
  class Store:
   def read(self,*a,**kw):raise AssertionError('COUNTERFEIT_IO')
  class Pretend:
   def require_issued_read(self,*a,**kw):raise AssertionError('COUNTERFEIT_CALLBACK')
  result=self.reader().read_market_data(self.raw(),owner_read_capability=Pretend(),expected_identity_authority=Pretend(),pinned_owned_store=Store())
  self.assertEqual(result['status'],'NOT_EXECUTED');self.assertFalse(result['native_authenticated']);self.assertIsNone(result['capabilities'])
 def test_retired_grid_request_refuses_before_owner_io(self):
  value=self.request();value['schema']='grid.gateway.ohlcv-query.v1-review2'
  with self.assertRaises(domain.QueryFormatError):self.reader().read_market_data(json.dumps(value).encode(),owner_read_capability=None,expected_identity_authority=None,pinned_owned_store=None)
 def test_invalid_and_oversized_input_refuses_before_owner_io(self):
  for raw in (b'',b'{}',b'x'*32769):
   with self.assertRaises(domain.QueryFormatError):self.reader().read_market_data(raw,owner_read_capability=None,expected_identity_authority=None,pinned_owned_store=None)
 def test_preparation_never_implies_query_execution(self):
  result=self.reader().read_market_data(self.raw(),owner_read_capability=None,expected_identity_authority=None,pinned_owned_store=None)
  self.assertEqual(result,domain.prepare_query(self.raw()).not_executed())
 def test_reader_has_no_child_or_dynamic_source_loader(self):
  import ast
  tree=ast.parse(Path(self.reader().__file__).read_bytes())
  for node in ast.walk(tree):
   if isinstance(node,(ast.Import,ast.ImportFrom)):
    names=[node.module] if isinstance(node,ast.ImportFrom) else [a.name for a in node.names]
    self.assertFalse(any(name and name.split('.')[0] in ('subprocess','importlib','grid','strattester','meta_analyse') for name in names))
   if isinstance(node,ast.Call) and isinstance(node.func,ast.Name):self.assertNotIn(node.func.id,('exec','eval','compile'))
if __name__=='__main__':unittest.main()
