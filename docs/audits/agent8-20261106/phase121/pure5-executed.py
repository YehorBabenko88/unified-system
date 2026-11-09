import sys,unittest,json
sys.path[:0]=['.','tests/gateway_jobs'];import test_capacity_freshness as m
suite=unittest.defaultTestLoader.loadTestsFromTestCase(m.CapacityFreshness);assert suite.countTestCases()==5
result=unittest.TextTestRunner(verbosity=2).run(suite);assert result.wasSuccessful() and result.testsRun==5 and not result.skipped
print(json.dumps(dict(committed_pure_cases=5,skips=0)))
