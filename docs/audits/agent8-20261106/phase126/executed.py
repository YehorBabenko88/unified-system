import sys,unittest,json
sys.path[:0]=['.','tests/gateway_jobs']
import test_clock_source_prerequisites as t
suite=unittest.defaultTestLoader.loadTestsFromTestCase(t.ClockSourcePrerequisites);assert suite.countTestCases()==4
result=unittest.TextTestRunner(verbosity=2).run(suite);assert result.wasSuccessful() and result.testsRun==4 and not result.skipped
print(json.dumps(t.observe_clock_source_v1(),sort_keys=True))
