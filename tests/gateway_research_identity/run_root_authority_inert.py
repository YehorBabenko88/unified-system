"""Explicit no-network source suite. Crypto import shapes only, never PKI proof."""
from pathlib import Path
import json,sys,unittest

def main():
 root=Path(__file__).resolve().parents[2]
 sys.path[:0]=[str(root),str(root/'tests/gateway_research_identity'),str(root/'tests/gateway_native_negative')]
 import test_root_authority as proof
 with proof.inert_crypto_imports():
  import test_broker,test_boundary
  suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(proof),unittest.defaultTestLoader.loadTestsFromModule(test_broker),unittest.defaultTestLoader.loadTestsFromTestCase(test_boundary.NegativeDataTests)])
  def ids(value):
   for case in value:
    if isinstance(case,unittest.TestSuite):yield from ids(case)
    else:yield case.id()
  expected=json.loads((root/'docs/intelligence/native-negative/canonical-v2-20261120/ROOT-GUARD-TESTS.json').read_bytes())
  actual=list(ids(suite))
  if len(actual)!=len(set(actual)) or len(expected)!=len(set(expected)) or sorted(actual)!=sorted(expected):raise ValueError('EXACT_ROOT_GUARD_CASE_IDS_REQUIRED')
  with proof.audit:result=unittest.TextTestRunner(verbosity=2).run(suite)
 return not (result.wasSuccessful() and result.testsRun==len(expected) and not result.skipped and not result.expectedFailures and not result.unexpectedSuccesses)

if __name__=='__main__':raise SystemExit(main())
