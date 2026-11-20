"""Explicit no-network source suite. Crypto import shapes only, never PKI proof."""
from pathlib import Path
import sys,unittest

def main():
 root=Path(__file__).resolve().parents[2]
 sys.path[:0]=[str(root),str(root/'tests/gateway_research_identity'),str(root/'tests/gateway_native_negative')]
 import test_root_authority as proof
 with proof.inert_crypto_imports():
  import test_broker,test_boundary
  suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(proof),unittest.defaultTestLoader.loadTestsFromModule(test_broker),unittest.defaultTestLoader.loadTestsFromTestCase(test_boundary.NegativeDataTests)])
  with proof.audit:result=unittest.TextTestRunner(verbosity=2).run(suite)
 return not result.wasSuccessful()

if __name__=='__main__':raise SystemExit(main())
