"""Inert canonical native DTO suite; cannot qualify native/PKI readiness."""
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'tests/gateway_research_identity')]
import httpx

def audit(event,args):
 if event in ('subprocess.Popen','os.system','socket.__new__','ctypes.dlopen'):raise RuntimeError('CANONICAL_BINDING_EFFECT_FORBIDDEN:'+event)

def main():
 sys.addaudithook(audit)
 import test_canonical_binding_data as proof
 suite=unittest.defaultTestLoader.loadTestsFromModule(proof);expected=9
 if suite.countTestCases()!=expected:raise ValueError('EXACT_CANONICAL_BINDING_CASES_REQUIRED')
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 return not(result.wasSuccessful() and result.testsRun==expected and not result.skipped and not result.expectedFailures and not result.unexpectedSuccesses)
if __name__=='__main__':raise SystemExit(main())
