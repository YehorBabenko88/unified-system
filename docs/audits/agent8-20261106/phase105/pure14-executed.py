import sys,unittest,json,importlib.metadata
sys.path.insert(0,'.');import jsonschema
blocked=[]
def audit(event,args):
 if event in ['subprocess.Popen','sqlite3.connect','socket.connect','socket.getaddrinfo','os.system']:blocked.append(event);raise AssertionError('A8_PURE_TEST_RUNTIME_EFFECT_FORBIDDEN')
 if event=='import' and any(args[0]==x or args[0].startswith(x+'.') for x in ['grid','meta_analyse','unified_system.gateway_research_identity','unified_system.gateway_worker','unified_system.gateway_target_adapter']):blocked.append('runtime_import');raise AssertionError('A8_RUNTIME_IMPORT_FORBIDDEN')
sys.addaudithook(audit)
class Result(unittest.TextTestResult):
 def __init__(self,*a,**k):super().__init__(*a,**k);self.subcases={}
 def addSubTest(self,test,subtest,err):
  self.subcases[test.id()]=self.subcases.get(test.id(),0)+1;super().addSubTest(test,subtest,err)
s=unittest.TestLoader().discover('tests/gateway_jobs',pattern='test_target_native_mapping_proposal.py')
def ids(s):return [x for item in s for x in (ids(item) if isinstance(item,unittest.TestSuite) else [item.id()])]
actual=ids(s);assert len(actual)==len(set(actual))==14
r=unittest.TextTestRunner(verbosity=2,resultclass=Result).run(s);assert r.wasSuccessful() and r.testsRun==14 and not r.skipped and not blocked
print(json.dumps({'tests':actual,'tests_run':14,'skips':0,'subcase_counts':r.subcases,'runtime_effect_or_import_attempts':blocked,'jsonschema':importlib.metadata.version('jsonschema'),'python':sys.version,'scope':'PURE_FORMAT_AND_HASH_SENSITIVITY_NOT_NATIVE_ADMISSION'},indent=2))
