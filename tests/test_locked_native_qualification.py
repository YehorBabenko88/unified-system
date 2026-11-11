"""Actual-helper/source controls. SOURCE PREPARED; execution requires allocation."""
import ast
import asyncio
import contextlib
import io
import stat
from types import SimpleNamespace
from unittest.mock import patch
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

    def test_mock_source_bounds_reads_and_observed_completion(self):
        tree = ast.parse((ROOT / 'scripts/run_atomic_read_mock_qualification.py').read_bytes())
        functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
        read = ast.unparse(functions['read_raw'])
        self.assertIn('stream.read(size + 1)', read)
        self.assertIn('before.st_size == size', read)
        self.assertIn('os.fstat', read)
        supervise = ast.unparse(functions['supervise'])
        self.assertLess(supervise.index('started = time.monotonic()'), supervise.index('subprocess.Popen'))
        self.assertLess(supervise.index('process.wait(timeout=5)'), supervise.index('observed_completion ='))
        self.assertIn('observed_completion > 90', supervise)
        self.assertIn('COMPLETION_OBSERVED_AFTER_CHILD_BUDGET', supervise)
        loader = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'exec_module')
        source = ast.unparse(loader)
        self.assertLess(source.index('digest(raw)'), source.index('compile(raw,'))

    def test_native_expected_inventories_and_mock_hash_stay_exact(self):
        import hashlib
        for rel, count in (('docs/intelligence/research-identity/native-profile-v2-20261109/EXPECTED-TESTS.json', 22), ('docs/intelligence/native-negative/EXPECTED-TESTS.json', 21)):
            ids = json.loads((ROOT / rel).read_bytes())
            self.assertEqual(len(ids), count)
            self.assertEqual(len(set(ids)), count)
        self.assertEqual(hashlib.sha256((ROOT / 'tests/test_research_identity_atomic_snapshot_unit.py').read_bytes()).hexdigest(), 'e9dfdc83b9dd10b0166bda588c0f2a328c0e1ff2142f9657565b3762d62360da')


class MockQualificationInertFaultControls(unittest.TestCase):
    """Call actual functions with inert dependencies; never real children/Grid."""

    def test_post_popen_faults_still_retire_handle_and_attempt_failure_receipt(self):
        stages = ('lock', 'event', 'thread_constructor', 'first_start', 'second_start',
                  'poll', 'kill', 'clock', 'join')
        for stage in stages:
            with self.subTest(stage=stage):
                helper = actual('run_atomic_read_mock_qualification')
                calls = []; receipts = []; fired = set(); readers = []
                def fault(name):
                    if name == stage and name not in fired:
                        fired.add(name)
                        raise RuntimeError('INERT_INJECTED_' + name)
                class Pipe:
                    def close(self): calls.append('pipe_close')
                class Process:
                    stdout = Pipe(); stderr = Pipe(); returncode = None
                    def poll(self):
                        calls.append('poll'); fault('poll')
                        # After an injected failure the inert handle remains live
                        # until actual cleanup kills it; no wait-only fake retirement.
                        if fired and self.returncode is None: return None
                        # kill-stage forces the actual budget branch once.
                        if stage == 'kill' and 'kill' not in fired: return None
                        self.returncode = 0; return 0
                    def kill(self):
                        calls.append('kill'); fault('kill'); self.returncode = -9
                    def wait(self, timeout=None):
                        calls.append(('wait', timeout))
                        if fired and self.returncode is None:
                            raise helper.subprocess.TimeoutExpired('INERT_HANDLE_STILL_LIVE', timeout)
                        self.returncode = 0; return 0
                process = Process()
                class Event:
                    def is_set(self): return False
                    def set(self): pass
                def event(): fault('event'); return Event()
                def lock(): fault('lock'); return contextlib.nullcontext()
                class Reader:
                    def __init__(self, **kwargs):
                        # Deliberately NEVER call target: no thread, pipe read or file.
                        fault('thread_constructor'); self.index = len(readers); self.started = False; readers.append(self)
                    def start(self):
                        fault('first_start' if self.index == 0 else 'second_start'); self.started = True
                    def join(self, timeout=None): calls.append(('join', self.index, timeout)); fault('join')
                    def is_alive(self): return False
                ticks = [0]
                def clock():
                    ticks[0] += 1
                    if ticks[0] > 1: fault('clock')
                    return 91 if stage == 'kill' and ticks[0] > 1 else 0
                fake_threads = SimpleNamespace(Lock=lock, Event=event, Thread=Reader)
                fake_time = SimpleNamespace(monotonic=clock, sleep=lambda _: None)
                failure = None; returned = None
                with patch.object(helper.subprocess, 'Popen', return_value=process) as launch, \
                     patch.object(helper, 'threading', fake_threads), \
                     patch.object(helper, 'time', fake_time), \
                     patch.object(helper, 'write_json', side_effect=lambda path, value, **kw: receipts.append(value)):
                    try: returned = helper.supervise(['INERT_NOT_EXECUTED'], Path('INERT_NO_FILE'))
                    except BaseException as error: failure = type(error).__name__
                self.assertLessEqual(launch.call_count, 1)
                self.assertIn(stage, fired, 'control must reach its injected fault')
                if launch.call_count == 0:
                    # Moving fallible setup before launch is valid containment.
                    self.assertEqual(calls, [])
                    self.assertIsNotNone(failure)
                    continue
                self.assertTrue(any(isinstance(c, tuple) and c[0] == 'wait' for c in calls),
                                'held handle must receive bounded wait even after setup/poll/kill faults')
                self.assertTrue(receipts, 'failure evidence must be attempted independently')
                self.assertIs(receipts[-1].get('passed'), False)
                if stage not in ('clock', 'join'):
                    self.assertIn('kill', calls, 'inert live handle must receive kill before wait')
                for reader in readers:
                    if reader.started:
                        self.assertTrue(any(isinstance(c, tuple) and c[:2] == ('join', reader.index) for c in calls),
                                        'each successfully started reader needs an independent join attempt')
                self.assertNotEqual(returned, True)
                self.assertTrue(failure is not None or returned is False)

    def test_actual_child_entry_executes_checked_buffer_not_reopening_loader(self):
        helper = actual('run_atomic_read_mock_qualification')
        entry = b"MARKER = 'CHECKED_BUFFER'\n"
        manifest = dict(files={}, helper={}, cache='INERT_CACHE', unified='INERT_UNIFIED',
                        grid='INERT_GRID', deps='INERT_DEPS', stdlib_paths=[], output='INERT_OUTPUT')
        manifest['files']['INERT_UNIFIED/tests/test_research_identity_atomic_snapshot_unit.py'] = dict(bytes=len(entry), sha256=helper.digest(entry))
        raw_manifest = json.dumps(manifest).encode()
        unchecked = []; receipts = []
        class InertPath:
            def __init__(self, value): self.value = str(value)
            def __truediv__(self, part): return InertPath(self.value + '/' + part)
            def __str__(self): return self.value
            def absolute(self): return self
            def iterdir(self): return iter(())
        fake_sys = SimpleNamespace(flags=SimpleNamespace(isolated=True, no_site=True),
                                   dont_write_bytecode=True, pycache_prefix='INERT_CACHE', path=[],
                                   meta_path=[], modules={}, addaudithook=lambda hook: None,
                                   stderr=io.StringIO())
        class ReopeningLoader:
            def create_module(self, spec): return None
            def exec_module(self, module):
                unchecked.append('REOPENED_UNCHECKED_ENTRY')
                module.MARKER = 'UNCHECKED_LOADER'
        spec = importlib.util.spec_from_loader('atomic_read_mock', ReopeningLoader(), origin='INERT_ENTRY')
        def raw(path, **kwargs): return raw_manifest if str(path) == 'INERT_MANIFEST' else entry
        expected_sha = helper.digest(entry)
        with patch.object(helper, 'TEST_SHA', expected_sha), \
             patch.object(helper, 'sys', fake_sys), \
             patch.object(helper, 'Path', InertPath), \
             patch.object(helper, 'read_raw', side_effect=raw), \
             patch.object(helper, 'check_all'), patch.object(helper, 'exact_owned_tree'), \
             patch.object(helper, 'file_fact', return_value={}), \
             patch.object(helper, 'ordinary'), \
             patch.object(helper.importlib.util, 'spec_from_file_location', return_value=spec), \
             patch.object(helper, 'write_json', side_effect=lambda path, value, **kw: receipts.append(value)):
            # This is the ACTUAL child function; its I/O/audit/process dependencies
            # are inert. No ControlledBackend class exists in input bytes, hence
            # no test, native fixture, crypto constructor or Grid import can run.
            # file_fact has one helper binding call and one entry hash call.
            with patch.object(helper, 'file_fact', side_effect=[{}, {'sha256': expected_sha}]):
                try: helper.child(InertPath('INERT_MANIFEST'), helper.digest(raw_manifest))
                except BaseException:
                    # Missing class or final-origin observation may fail; the
                    # security assertion is which exact entry bytes were used.
                    pass
        self.assertEqual(unchecked, [], 'explicit entry must not delegate reopening exec_module')
        self.assertIn('atomic_read_mock', fake_sys.modules)
        self.assertEqual(fake_sys.modules['atomic_read_mock'].MARKER, 'CHECKED_BUFFER')

    def test_actual_ordinary_rejects_unsafe_ancestor_before_leaf_lookup(self):
        helper = actual('run_atomic_read_mock_qualification')
        observations = []
        class InertPath:
            def __init__(self, label, mode, parents=()): self.label=label; self.mode=mode; self.parents=parents
            def absolute(self): return self
            def lstat(self):
                observations.append(self.label)
                return SimpleNamespace(st_mode=self.mode, st_reparse_tag=0, st_file_attributes=0, st_nlink=1)
            def stat(self): return self.lstat()
            def is_file(self): return stat.S_ISREG(self.mode)
            def is_dir(self): return stat.S_ISDIR(self.mode)
        root = InertPath('root', stat.S_IFDIR)
        unsafe = InertPath('unsafe', stat.S_IFLNK, (root,))
        leaf = InertPath('leaf', stat.S_IFREG, (unsafe, root))
        with patch.object(helper, 'Path', side_effect=lambda value: value):
            with self.assertRaises(RuntimeError): helper.ordinary(leaf)
        self.assertTrue(observations)
        self.assertEqual(observations[0], 'root')
        self.assertIn('unsafe', observations)
        self.assertNotIn('leaf', observations)

    def test_actual_locked_output_checks_root_before_nearest_unsafe_ancestor(self):
        helper = actual('locked_native_qualification')
        observations = []; writes = []
        class InertPath:
            def __init__(self, label, unsafe=False, parents=()): self.label=label; self.unsafe=unsafe; self.parents=parents
            def absolute(self): return self
            def lstat(self):
                observations.append(self.label)
                return SimpleNamespace(st_mode=stat.S_IFLNK if self.unsafe else stat.S_IFDIR,
                                       st_reparse_tag=0, st_file_attributes=0)
            def stat(self): return self.lstat()
            def is_symlink(self): return self.unsafe
            def is_dir(self): return not self.unsafe
            def mkdir(self, **kwargs): writes.append('mkdir'); raise AssertionError('must not write')
        root=InertPath('root'); unsafe=InertPath('unsafe', True, (root,)); leaf=InertPath('leaf', parents=(unsafe,root))
        real_path = Path
        def path(value): return real_path(value) if str(value) == helper.__file__ else leaf
        with patch.object(helper, 'Path', side_effect=path), \
             patch.object(helper.sys, 'stdout', io.StringIO()), patch.object(helper.sys, 'stderr', io.StringIO()):
            code = helper.main(['--output', 'INERT_OUTPUT', '--expected-tests', '22'])
        self.assertEqual(code, 78)
        self.assertTrue(observations)
        self.assertEqual(observations[0], 'root')
        self.assertIn('unsafe', observations)
        self.assertNotIn('leaf', observations)
        self.assertEqual(writes, [])


if __name__ == '__main__':
    unittest.main()
