"""Actual-helper/source controls. SOURCE PREPARED; execution requires allocation."""
import ast
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GUARDED = (
    'docs/intelligence/research-identity/fetch_consul.py',
    'docs/intelligence/research-identity/run_qualification.py',
    'docs/intelligence/research-identity/native-profile-v2-20261109/run_qualification.py',
    'docs/intelligence/native-negative/run_qualification.py',
    'tests/gateway_research_identity/test_native_broker.py',
    'tests/gateway_research_identity/test_native_profile_v2.py',
    'tests/gateway_native_negative/test_actual.py',
    'tests/gateway_research_identity/consul_lab.py',
)
REASON = 'NATIVE_QUALIFICATION_PREREQUISITES_LOCKED'


def actual(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LockedNativeQualificationControls(unittest.TestCase):
    def test_actual_helper_always_blocks_both_native_suites(self):
        helper = actual('locked_native_qualification')
        with tempfile.TemporaryDirectory() as folder:
            for count in (22, 21):
                path = Path(folder) / str(count)
                self.assertEqual(helper.main(['--output', str(path), '--expected-tests', str(count)]), 78)
                raw = (path / 'status.json').read_bytes()
                self.assertLessEqual(len(raw), 4096)
                status = json.loads(raw)
                self.assertEqual(status['state'], 'BLOCKED')
                self.assertEqual(status['result'], 'NOT_RUN')
                self.assertEqual(status['expected_tests'], count)
                for field in ('collected_tests', 'executed_tests', 'skipped_tests', 'native_processes_started'):
                    self.assertEqual(status[field], 0)
                self.assertFalse(status['enable_path_supported'])

    def test_actual_helper_rejects_enable_option(self):
        helper = actual('locked_native_qualification')
        with self.assertRaises(SystemExit) as error:
            helper.main(['--enable'])
        self.assertNotEqual(error.exception.code, 0)

    def test_actual_helper_output_failure_is_not_success(self):
        helper = actual('locked_native_qualification')
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'occupied'
            target.write_text('foreign')
            self.assertEqual(helper.main(['--output', str(target), '--expected-tests', '22']), 78)
            self.assertEqual(target.read_text(), 'foreign')

    def test_all_eight_native_entries_raise_before_any_import(self):
        for name in GUARDED:
            with self.subTest(path=name):
                body = ast.parse((ROOT / name).read_bytes()).body
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                    body = body[1:]
                while body and isinstance(body[0], ast.ImportFrom) and body[0].module == '__future__':
                    body = body[1:]
                first = body[0]
                self.assertIsInstance(first, ast.Raise)
                self.assertIsInstance(first.exc, ast.Call)
                self.assertEqual(first.exc.func.id, 'RuntimeError')
                self.assertEqual(first.exc.args[0].value, REASON)

    def test_workflows_lock_before_dependency_download_and_import(self):
        for name, count in (('gateway-research-identity.yml', 22), ('gateway-native-negative.yml', 21)):
            text = (ROOT / '.github/workflows' / name).read_text()
            self.assertLess(text.index('scripts/locked_native_qualification.py'), text.index('python -m pip install'))
            self.assertLess(text.index('scripts/locked_native_qualification.py'), text.index('fetch_consul.py'))
            self.assertIn('--expected-tests ' + str(count), text)
            self.assertNotIn('continue-on-error', text)
            self.assertIn('if-no-files-found: error', text)
            self.assertIn('if: always()', text)
            self.assertIn('ubuntu-24.04', text)
            self.assertIn('windows-latest', text)

    def test_mock_helper_is_separate_and_exact_inventory_is_ten(self):
        helper = actual('run_atomic_read_mock_qualification')
        self.assertEqual(len(helper.EXPECTED_METHODS), 10)
        self.assertEqual(len(set(helper.EXPECTED_METHODS)), 10)
        self.assertEqual(helper.TEST_SHA, 'e9dfdc83b9dd10b0166bda588c0f2a328c0e1ff2142f9657565b3762d62360da')
        text = (ROOT / 'scripts/run_atomic_read_mock_qualification.py').read_text()
        self.assertNotIn('import consul_lab', text)
        self.assertNotIn('import test_native_broker', text)
        self.assertNotIn('import test_native_profile_v2', text)
        self.assertNotIn(REASON, (ROOT / 'unified_system/gateway_research_identity.py').read_text())

    def test_actual_mock_inventory_checker_fails_extra_missing_skip_or_error(self):
        helper = actual('run_atomic_read_mock_qualification')
        ids = ['atomic_read_mock.ControlledBackendBrokerUnitTests.' + value for value in helper.EXPECTED_METHODS]
        self.assertTrue(helper.inventory_ok(ids))
        self.assertFalse(helper.inventory_ok(ids[:-1]))
        self.assertFalse(helper.inventory_ok(ids + ids[:1]))
        for changes in ({'skips': 1}, {'errors': 1}, {'failures': 1}, {'cleanup_ok': False}, {'boundary_errors': 1}):
            value = dict(ids=ids, tests=10, skips=0, errors=0, failures=0, cleanup_ok=True, boundary_errors=0)
            value.update(changes)
            self.assertFalse(helper.result_ok(**value))

    def test_native_expected_inventories_and_mock_hash_stay_exact(self):
        import hashlib
        for rel, count in (('docs/intelligence/research-identity/native-profile-v2-20261109/EXPECTED-TESTS.json', 22), ('docs/intelligence/native-negative/EXPECTED-TESTS.json', 21)):
            ids = json.loads((ROOT / rel).read_bytes())
            self.assertEqual(len(ids), count)
            self.assertEqual(len(set(ids)), count)
        self.assertEqual(hashlib.sha256((ROOT / 'tests/test_research_identity_atomic_snapshot_unit.py').read_bytes()).hexdigest(), 'e9dfdc83b9dd10b0166bda588c0f2a328c0e1ff2142f9657565b3762d62360da')


if __name__ == '__main__':
    unittest.main()
