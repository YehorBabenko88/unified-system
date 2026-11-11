import sys,json,unittest
from pathlib import Path
sys.path[:0]=sys.argv[1:3]
import test_local_invalidation as t
suite=unittest.defaultTestLoader.loadTestsFromTestCase(t.LocalInvalidationTests);assert suite.countTestCases()==3
result=unittest.TextTestRunner(verbosity=2).run(suite)
processes=t.LocalInvalidationTests.lab.processes;retired=[dict(pid=p.pid,returncode=p.poll()) for p in processes]
assert result.testsRun==3 and result.wasSuccessful() and not result.skipped
assert len(retired)==3 and all(x['returncode'] is not None for x in retired)
print(json.dumps(dict(unique_tests=3,skips=0,owned_retained_Consul_retired=retired,scope='NEW_THREE_ONLY_ACTUAL_LOCAL_LATCH_NOT_NATIVE_RETIREMENT',full26='NOT_RUN',jobs_workers='NOT_RUN')))
