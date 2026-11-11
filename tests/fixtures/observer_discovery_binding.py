"""SOURCE ONLY: one actual module-discovery binding regression.

Explicit source/hash/path binding; no fixture edit or actual run in preparation.
"""
import hashlib
import io
import linecache
from pathlib import Path
import sys
import types
import unittest

MODULE = 'test_preparation_observer_admission'
CODE_FILE = '<pinned-observer-admission-discovery-fixture>'
EXPECTED_IDS = [MODULE+'.PreparationObserverAdmissionControls.'+name for name in (
    'test_actual_observer_controls_accepts_normal_twelve_successes',
    'test_actual_observer_controls_rejects_expected_failure',
    'test_actual_observer_controls_rejects_unexpected_success')]


class BoundedLog(io.StringIO):
    def write(self, value):
        if self.tell()+len(value)>65536:
            raise RuntimeError('DISCOVERY_LOG_BOUND')
        return super().write(value)


class ObserverDiscoveryBindingControl(unittest.TestCase):
    def setUp(self):
        if not hasattr(self, 'binding'):
            raise RuntimeError('explicit hash-bound discovery make_suite required')

    def test_actual_module_discovery_runs_three_bound_successes(self):
        raw, source_pin, fixture_path = self.binding
        missing = object()
        previous = sys.modules.get(MODULE, missing)
        previous_lines = linecache.cache.get(CODE_FILE, missing)
        previous_path = list(sys.path)
        self.observed = dict(stage='BEFORE_MODULE_COMPILE', fixture_sha256=source_pin)
        try:
            module = types.ModuleType(MODULE)
            module.__file__ = fixture_path
            sys.modules[MODULE] = module
            linecache.cache[CODE_FILE] = (len(raw), None, raw.decode('utf-8').splitlines(True), CODE_FILE)
            # SAME verified buffer, non-main module. No make_suite call here:
            # the actual standard loader must invoke the module's load_tests.
            exec(compile(raw, CODE_FILE, 'exec'), module.__dict__)
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromModule(module)

            def ids(group):
                for case in group:
                    if isinstance(case, unittest.TestSuite):
                        yield from ids(case)
                    else:
                        yield case.id()

            actual_ids = list(ids(suite))
            if loader.errors or actual_ids != EXPECTED_IDS:
                raise RuntimeError('DISCOVERY_SETUP_OR_ID_ERROR_NOT_EXPECTED_RED')

            class Result(unittest.TextTestResult):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.started_ids, self.succeeded_ids, self.error_details = [], [], []

                def startTest(self, test):
                    self.started_ids.append(test.id())
                    super().startTest(test)

                def addSuccess(self, test):
                    self.succeeded_ids.append(test.id())
                    super().addSuccess(test)

                def addError(self, test, error):
                    self.error_details.append(dict(id=test.id(), type=error[0].__name__,
                                                   message=str(error[1])[:1024]))
                    super().addError(test, error)

            result = unittest.TextTestRunner(stream=BoundedLog(), verbosity=2, resultclass=Result).run(suite)
            self.observed.update(stage='ACTUAL_MODULE_DISCOVERY_EXECUTED', ids=actual_ids,
                started_ids=result.started_ids, succeeded_ids=result.succeeded_ids,
                tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                error_details=result.error_details, skips=len(result.skipped),
                expected_failures=len(result.expectedFailures),
                unexpected_successes=len(result.unexpectedSuccesses),
                was_successful=result.wasSuccessful())
            self.assertEqual((result.testsRun, result.started_ids, result.succeeded_ids,
                len(result.failures), len(result.errors), len(result.skipped),
                len(result.expectedFailures), len(result.unexpectedSuccesses), result.wasSuccessful()),
                (3, EXPECTED_IDS, EXPECTED_IDS, 0, 0, 0, 0, 0, True))
        finally:
            sys.path[:] = previous_path
            if previous is missing:
                sys.modules.pop(MODULE, None)
            else:
                sys.modules[MODULE] = previous
            if previous_lines is missing:
                linecache.cache.pop(CODE_FILE, None)
            else:
                linecache.cache[CODE_FILE] = previous_lines


def make_suite(fixture_source_bytes, *, expected_fixture_sha256, fixture_path):
    if type(fixture_source_bytes) is not bytes or len(fixture_source_bytes)>65536:
        raise ValueError('bounded fixture source bytes required')
    if hashlib.sha256(fixture_source_bytes).hexdigest()!=expected_fixture_sha256:
        raise ValueError('fixture source pin mismatch')
    if type(fixture_path) is not str or len(fixture_path)>4096 or not Path(fixture_path).is_absolute():
        raise ValueError('explicit absolute fixture source path required')
    case = ObserverDiscoveryBindingControl('test_actual_module_discovery_runs_three_bound_successes')
    case.binding = fixture_source_bytes, expected_fixture_sha256, fixture_path
    return unittest.TestSuite([case])
