import sys,unittest,json,time
sys.path[:0]=['.','tests/gateway_jobs'];import test_owned_attempt as m
m.GRID=sys.argv[1];suite=unittest.defaultTestLoader.loadTestsFromTestCase(m.NativeOwnedAttempt);assert suite.countTestCases()==2
result=unittest.TextTestRunner(verbosity=2).run(suite);assert result.wasSuccessful() and result.testsRun==2 and not result.skipped
worker=m.worker_module;observations=[]
for inventory in worker.GatewayWorker._owners.values():
 for state in inventory._attempts.values():
  if state['phase']!='QUIESCENT':continue
  snap=state['snapshot'];details=json.loads(snap.os_observation_json);host=details['host_observation'];start=int(host['observation_started_monotonic_ns']);end=int(host['observation_completed_monotonic_ns'])
  assert start<=end and int(host['query_duration_ns'])==end-start and int(host['monotonic_ns'])==end and host['observation_incarnation_id']==worker._PROCESS_INCARNATION
  assert host['monotonic_ns_semantics']=='QUERY_COMPLETION_DIAGNOSTIC_ONLY_NOT_FRESHNESS' and host['qualified_for_native_admission'] is False
  value=worker.capacity_freshness_v1(observed_start_ns=start,observed_end_ns=end,now_ns=time.monotonic_ns(),observation_incarnation_id=host['observation_incarnation_id'],expected_incarnation_id=worker._PROCESS_INCARNATION,max_age_ns=None)
  assert value.state=='UNSUPPORTED' and not value.admission_supported and not value.resources_reserved
  assert details['job_empty_observed'] and details['retained_primary_exit_observed'] and details['resume_calls']==0
  observations.append(dict(pid=snap.child_pid,creation_filetime=snap.child_creation_filetime,attempt_id=snap.attempt_id,host_observation=host,age_policy='NONE_NO_OPERATIONAL_VALUE_INVENTED',freshness_state=value.state,job_empty_observed=True,retained_primary_exit_observed=True))
assert len(observations)==2
print(json.dumps(dict(committed_actual_suspended_cases=2,skips=0,observations=observations,admission_supported=False,resources_reserved=False)))
