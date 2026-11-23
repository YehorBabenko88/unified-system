"""Mandatory canonical four-owner installed offline causal qualification.
No provider/native/service admission or old-source compatibility CLI exists.
"""
import io,json,pathlib,sys,types,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
COHORT='integration/four_owner/cohort.json'
RUNNER='integration/four_owner/run_causal_installed.py'
EXPECTED_IDS=tuple(json.loads((ROOT/'docs/qualification/offline-causal-20261120/EXPECTED-TESTS.json').read_bytes()))
ROLE_IDS=tuple(row['replacement'] for row in json.loads((ROOT/'docs/qualification/offline-causal-20261120/preservation-map.json').read_bytes())['roles'])
class GateRejected(ValueError):pass

def require_inventory(ids):
 if len(ids)!=len(EXPECTED_IDS) or len(set(ids))!=len(ids) or set(ids)!=set(EXPECTED_IDS):raise GateRejected('EXACT_CAUSAL_CASE_INVENTORY_REQUIRED')

class CausalResult(unittest.TextTestResult):
 def __init__(self,stream=None,descriptions=True,verbosity=2):
  if stream is None:stream=unittest.runner._WritelnDecorator(io.StringIO())
  super().__init__(stream,descriptions,verbosity);self.started=[];self.finished=[]
 def startTest(self,test):self.started.append(test.id());super().startTest(test)
 def stopTest(self,test):self.finished.append(test.id());super().stopTest(test)

def require_success(result,expected):
 if not(result.wasSuccessful() and result.testsRun==len(expected) and not result.skipped and not result.expectedFailures and not result.unexpectedSuccesses and len(result.started)==len(set(result.started))==len(expected) and set(result.started)==set(expected) and len(result.finished)==len(set(result.finished))==len(expected) and set(result.finished)==set(expected)):
  raise GateRejected('MANDATORY_CAUSAL_CASE_NOT_PASSED')

def builder():
 path=ROOT/'scripts/qualify_four_owner.py';module=types.ModuleType('canonical_causal_raw_builder');module.__file__=str(path);exec(compile(path.read_bytes(),str(path),'exec',dont_inherit=True),module.__dict__);return module

def main(argv=None):
 return builder().main(argv,suite='causal',cohort_file=COHORT,runner_file=RUNNER)
if __name__=='__main__':raise SystemExit(main())
