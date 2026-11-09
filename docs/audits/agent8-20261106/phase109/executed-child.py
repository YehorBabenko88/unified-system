import sys,os,unittest,json,importlib.util;sys.path.insert(0,'.');os.environ['AGENT5_RUN_OWNED_ATTEMPT_NATIVE']='1'
def load(n):
 spec=importlib.util.spec_from_file_location(n,'tests/gateway_jobs/'+n+'.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=load('test_owned_attempt');m.GRID=sys.argv[1];n=load('test_worker_limits');s=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(m),unittest.defaultTestLoader.loadTestsFromModule(n)])
def ids(s):
 return [x for item in s for x in (ids(item) if isinstance(item,unittest.TestSuite) else [item.id()])]
names=ids(s);assert len(names)==len(set(names))==13;result=unittest.TextTestRunner(verbosity=2).run(s);assert result.testsRun==13 and result.wasSuccessful() and not result.skipped;print(json.dumps(dict(tests=names,count=13,skips=0,native_cases=2,GRID_override=sys.argv[1],resume_authorized=False,PR52_executed=False)))
