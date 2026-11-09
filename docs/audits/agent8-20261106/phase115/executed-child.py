import sys,os,unittest,json,importlib.util;sys.path.insert(0,'.');os.environ['AGENT5_RUN_OWNED_ATTEMPT_NATIVE']='1'
def load(n):
 spec=importlib.util.spec_from_file_location(n,'tests/gateway_jobs/'+n+'.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=load('test_owned_attempt');m.GRID=sys.argv[1];n=load('test_worker_limits');c=load('test_closed_jobs');d=load('test_resource_capabilities');e=load('test_cpu_policy');f=load('test_target_native_mapping_proposal');s=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(m),unittest.defaultTestLoader.loadTestsFromModule(n),unittest.defaultTestLoader.loadTestsFromModule(c),unittest.defaultTestLoader.loadTestsFromModule(d),unittest.defaultTestLoader.loadTestsFromModule(e),unittest.defaultTestLoader.loadTestsFromModule(f)])
def ids(s):
 return [x for item in s for x in (ids(item) if isinstance(item,unittest.TestSuite) else [item.id()])]
names=ids(s);assert len(names)==len(set(names))==43;result=unittest.TextTestRunner(verbosity=2).run(s);assert result.testsRun==43 and result.wasSuccessful() and not result.skipped;retired=[]
for worker in m.worker_module.GatewayWorker._owners.values():
 for state in worker._attempts.values():
  if state['phase']=='QUIESCENT':
   snap=state['snapshot'];details=json.loads(snap.os_observation_json);assert details['job_empty_observed'] and details['retained_primary_exit_observed'] and details['resume_calls']==0;retired.append(dict(pid=snap.child_pid,attempt_id=snap.attempt_id,creation_filetime=snap.child_creation_filetime,state=snap.state,job_empty_observed=True,primary_exit_observed=True,inventory='ACTUAL_TEST_PROCESS_OWN_RETAINED_INVENTORY_NO_PID_REOPEN'))
assert len(retired)==2
print(json.dumps(dict(retired_owned_attempts=retired,tests=names,count=43,skips=0,native_cases=2,GRID_override=sys.argv[1],resume_authorized=False,PR52_executed=False)))
