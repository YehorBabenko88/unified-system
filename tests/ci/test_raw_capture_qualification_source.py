"""Pure guard regressions; never import owner fixtures or launch a child."""
import hashlib
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import io
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('raw_qualification_guard', ROOT / 'tools/raw_capture/qualify.py')
Q = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(Q)


class SourceQualificationGuards(unittest.TestCase):
    def test_exact_owner_source_tuple(self):
        self.assertEqual(Q.GRID, ('53b842df817d37b006809d73f9b6195348d32cc2', '19a12a6b76f89ee6c170051bc34f50290295f406'))
        self.assertEqual(Q.STORAGE, ('01d7cf17f47a6bfa930a36808a4b0065c5f0f053', '599f39e91ea83fb1233b3bd5fb407755626b9468'))

    def test_exact_inventory_is_unique_58(self):
        self.assertEqual(len(Q.EXPECTED_IDS), 58)
        Q.require_ids(Q.EXPECTED_IDS)

    def test_missing_case_denied(self):
        with self.assertRaises(Q.Denied): Q.require_ids(Q.EXPECTED_IDS[:-1])

    def test_duplicate_case_denied(self):
        with self.assertRaises(Q.Denied): Q.require_ids(Q.EXPECTED_IDS[:-1] + Q.EXPECTED_IDS[:1])

    def test_extra_case_denied(self):
        with self.assertRaises(Q.Denied): Q.require_ids(Q.EXPECTED_IDS + ['foreign.test'])

    def test_git_object_hash_checks_content(self):
        raw = b'payload'; oid = hashlib.sha1(b'blob 7\0' + raw).hexdigest()
        self.assertEqual(Q.check_object(oid, 'blob', raw), raw)
        with self.assertRaises(Q.Denied): Q.check_object(oid, 'blob', raw + b'x')

    def test_batch_requires_size_and_lf(self):
        oid = hashlib.sha1(b'blob 1\0x').hexdigest()
        self.assertEqual(Q.parse_batch((oid + ' blob 1\nx\n').encode(), [oid])[oid], ('blob', b'x'))
        for suffix in (b'x', b'x!', b'xy\n'):
            with self.assertRaises(Q.Denied): Q.parse_batch((oid + ' blob 1\n').encode() + suffix, [oid])

    def test_batch_rejects_wrong_type_and_trailing_bytes(self):
        oid = hashlib.sha1(b'blob 1\0x').hexdigest()
        with self.assertRaises(Q.Denied): Q.parse_batch((oid + ' tree 1\nx\n').encode(), [oid])
        with self.assertRaises(Q.Denied): Q.parse_batch((oid + ' blob 1\nx\nextra').encode(), [oid])

    def test_path_aliases_and_unsafe_tree_modes_denied(self):
        for name in ('../x', 'a/b', 'A\\b', '', '.git', '..'):
            with self.assertRaises(Q.Denied): Q.safe_component(name)
        with self.assertRaises(Q.Denied): Q.parse_tree(b'120000 alias\0' + bytes(20))

    def test_missing_api_is_prerequisite_not_case_success(self):
        with self.assertRaises(Q.Prerequisite): Q.require_api(object(), 'make_suite')

    def test_foreign_cached_package_denied(self):
        with self.assertRaises(Q.Denied): Q.require_fresh_modules({'grid': object()})
        Q.require_fresh_modules({'unrelated': object()})

    def test_effect_guard_denies_network_and_process(self):
        for event in ('socket.connect', 'socket.__new__', 'subprocess.Popen', 'os.system', 'os.posix_spawn'):
            with self.assertRaises(Q.Denied): Q.effect_event(event, ())
        Q.effect_event('sqlite3.connect', ('owned-placeholder',))

    def test_owner_labels_and_data_only_worker(self):
        self.assertEqual(len(Q.GRID_PINS), 18)
        self.assertEqual(len(Q.STORAGE_PINS), 8)
        self.assertIn('grid/worker.py', Q.DATA_ONLY)
        with self.assertRaises(Q.Denied): Q.require_code_role('grid', 'grid/worker.py')

    def test_root_package_cannot_substitute_for_storage(self):
        with self.assertRaises(Q.Denied): Q.require_code_role('root', 'unified_system/journal.py')

    def test_owned_sqlite_allowed_foreign_write_denied(self):
        scratch = ROOT / 'hypothetical-owned-state'
        hook = Q.owned_effect_guard(scratch, ROOT / 'hypothetical-result.json')
        hook('sqlite3.connect', (str(scratch / 'capture.sqlite'),))
        hook('open', (str(scratch / 'staging.part'), 'x', 193))
        for event, args in (('sqlite3.connect', (str(ROOT / 'foreign.sqlite'),)), ('open', (str(ROOT / 'source.py'), 'w', 577)), ('os.remove', (str(ROOT / 'existing-data'), -1))):
            with self.assertRaises(Q.Denied): hook(event, args)

    def test_late_output_after_exit_is_sticky_failure(self):
        child = SimpleNamespace(stdout=io.BytesIO(b'x' * 9), stderr=io.BytesIO(), stdin=None, returncode=0, poll=lambda: 0, wait=lambda timeout: 0)
        class Thread:
            def __init__(self, target, args, daemon): self.target, self.args = target, args
            def start(self): self.target(*self.args)
            def join(self, timeout): pass
            def is_alive(self): return False
        with patch.object(Q.subprocess, 'Popen', return_value=child), patch.object(Q.threading, 'Thread', Thread):
            facts = Q.capture(['inert'], ROOT, {}, 30, 8)
        self.assertEqual(facts['reason'], 'OUTPUT_BOUND')
        self.assertEqual(facts['total_bytes'], 9)
        self.assertEqual(facts['stdout'], b'x' * 8)

    def test_unknown_start_does_not_close_pipe_or_become_success(self):
        killed = []
        child = SimpleNamespace(stdout=io.BytesIO(), stderr=io.BytesIO(), stdin=None, returncode=None, poll=lambda: None, kill=lambda: killed.append(True), wait=lambda timeout: 0)
        class Thread:
            ident = None
            def __init__(self, **kwargs): pass
            def start(self): raise RuntimeError('inert model')
            def is_alive(self): return False
        with patch.object(Q.subprocess, 'Popen', return_value=child), patch.object(Q.threading, 'Thread', Thread):
            facts = Q.capture(['inert'], ROOT, {}, 30, 8)
        self.assertTrue(killed)
        self.assertIn('START_UNKNOWN', facts['errors'])
        self.assertIsNotNone(facts['reason'])
        self.assertFalse(child.stdout.closed)

    def test_workflow_has_readonly_pins_and_consumer_step_context(self):
        text = (ROOT / '.github/workflows/raw-capture-offline-qualified.yml').read_text()
        self.assertIn('contents: read', text)
        self.assertIn('fail-fast: false', text)
        self.assertNotIn('workflow_dispatch:', text)
        self.assertEqual(text.count('persist-credentials: false'), 3)
        for pin in (Q.GRID[0], Q.STORAGE[0], '11d5960a326750d5838078e36cf38b85af677262', 'a26af69be951a213d495a4c3e4e4022e16d87065', 'ea165f8d65b6e75b540449e92b4886f43607fa02'):
            self.assertIn(pin, text)
        self.assertIn('if-no-files-found: error', text)

    def test_poll_error_still_attempts_own_kill_wait_and_readers(self):
        calls = []
        def poll(): calls.append('poll'); raise RuntimeError('inert poll fault')
        child = SimpleNamespace(stdout=io.BytesIO(), stderr=io.BytesIO(), stdin=None, returncode=0, poll=poll,
                                kill=lambda: calls.append('kill'), wait=lambda timeout: calls.append('wait'))
        class Thread:
            def __init__(self, target, args, daemon): self.target, self.args = target, args
            def start(self): self.target(*self.args)
            def join(self, timeout): calls.append('join')
            def is_alive(self): calls.append('alive'); return False
        with patch.object(Q.subprocess, 'Popen', return_value=child), patch.object(Q.threading, 'Thread', Thread):
            facts = Q.capture(['inert'], ROOT, {}, 30, 8)
        self.assertIn('kill', calls)
        self.assertIn('wait', calls)
        self.assertEqual(calls.count('join'), 2)
        self.assertEqual(calls.count('alive'), 2)
        self.assertIsNotNone(facts['reason'])

    def test_cleanup_clock_error_preserves_independent_retirement(self):
        calls = []; ticks = iter((0.0, 0.0))
        def clock():
            try: return next(ticks)
            except StopIteration: raise RuntimeError('inert persistent clock fault')
        child = SimpleNamespace(stdout=io.BytesIO(), stderr=io.BytesIO(), stdin=None, returncode=0,
                                poll=lambda: 0, kill=lambda: calls.append('kill'), wait=lambda timeout: calls.append(('wait', timeout)))
        class Thread:
            def __init__(self, target, args, daemon): self.target, self.args = target, args
            def start(self): self.target(*self.args)
            def join(self, timeout): calls.append(('join', timeout))
            def is_alive(self): calls.append('alive'); return False
        facts = None; escaped = None
        with patch.object(Q.subprocess, 'Popen', return_value=child), patch.object(Q.threading, 'Thread', Thread), patch.object(Q.time, 'monotonic', clock):
            try: facts = Q.capture(['inert'], ROOT, {}, 30, 8)
            except BaseException as exc: escaped = type(exc).__name__
        # Assertions occur after restoring every inert seam, even on old escape.
        self.assertTrue(any(isinstance(x, tuple) and x[0] == 'wait' for x in calls))
        self.assertEqual(sum(isinstance(x, tuple) and x[0] == 'join' for x in calls), 2)
        self.assertEqual(calls.count('alive'), 2)
        self.assertIsNone(escaped)
        self.assertIsNotNone(facts['reason'])
        self.assertIn('CLEANUP_CLOCK_UNKNOWN', facts['errors'])

    def test_exact_owned_readonly_sqlite_uri_uses_actual_hook_and_ordinary(self):
        scratch = ROOT / 'hypothetical-owned-state'
        database = scratch / 'capture.sqlite'
        hook = Q.owned_effect_guard(scratch, ROOT / 'hypothetical-result.json')
        caught = None
        with patch.object(Q, 'ordinary', return_value=database) as check:
            try: hook('sqlite3.connect', (database.as_uri() + '?mode=ro',))
            except BaseException as exc: caught = type(exc).__name__
        self.assertIsNone(caught)
        check.assert_called_once_with(database, True)

    def test_sqlite_uri_alias_query_remote_and_foreign_paths_denied(self):
        scratch = ROOT / 'hypothetical-owned-state'; uri = (scratch / 'capture.sqlite').as_uri()
        hook = Q.owned_effect_guard(scratch, ROOT / 'hypothetical-result.json')
        invalid = [uri, uri+'?mode=rw', uri+'?mode=ro&cache=shared', uri+'?mode=ro#x',
                   uri.replace('file:///', 'file://localhost/')+'?mode=ro',
                   uri.replace('file:///', 'file://remote.invalid/')+'?mode=ro',
                   uri.replace('capture.sqlite', '%63apture.sqlite')+'?mode=ro',
                   uri.replace('capture.sqlite', 'x/../capture.sqlite')+'?mode=ro',
                   uri.replace('capture.sqlite', 'x%2F..%2Fcapture.sqlite')+'?mode=ro',
                   ' '+uri+'?mode=ro', uri+'?mode=%72o', uri+'?mode=ro&mode=ro',
                   (ROOT/'foreign.sqlite').as_uri()+'?mode=ro']
        with patch.object(Q, 'ordinary') as check:
            for value in invalid:
                with self.subTest(value=value), self.assertRaises(Q.Denied): hook('sqlite3.connect', (value,))
        check.assert_not_called()

    def test_sqlite_readonly_uri_does_not_bypass_ordinary_alias_guard(self):
        scratch = ROOT / 'hypothetical-owned-state'; uri = (scratch / 'capture.sqlite').as_uri()+'?mode=ro'
        hook = Q.owned_effect_guard(scratch, ROOT/'hypothetical-result.json')
        with patch.object(Q, 'ordinary', side_effect=Q.Denied('PATH_ALIAS')):
            with self.assertRaises(Q.Denied) as denied: hook('sqlite3.connect', (uri,))
        self.assertEqual(str(denied.exception), 'PATH_ALIAS')

    def test_actual_primary_boundary_records_closed_facts_before_git(self):
        private = 'PRIVATE-PATH-TOKEN-MESSAGE-MUST-NOT-BE-LOGGED'
        for error, expected in ((FileNotFoundError(2, private), 'FileNotFoundError'),
                                (PermissionError(13, private), 'PermissionError'),
                                (RuntimeError(private), 'UNKNOWN')):
            caught = None
            with patch.object(Q, 'ordinary', side_effect=error), patch.object(Q.subprocess, 'Popen') as spawn:
                try: Q.primary(ROOT, '0'*40)
                except BaseException as exc: caught = exc
            spawn.assert_not_called()
            fact = getattr(caught, 'fact', {})
            self.assertEqual(fact.get('stage'), 'SOURCE_ROOT_ORDINARY')
            self.assertEqual(fact.get('role'), 'root')
            self.assertEqual(fact.get('exception_class'), expected)
            self.assertNotIn(private, repr(fact))

    def test_actual_git_role_precheck_fault_has_no_fallback_or_spawn(self):
        visited = []
        def ordinary(path, *args, **kwargs):
            visited.append(path)
            if str(path).endswith('git.exe') or path == Path('/usr/bin/git'):
                raise FileNotFoundError(2, 'PRIVATE-MESSAGE-NOT-FOR-REPORT')
            return path
        caught = None
        with patch.object(Q, 'ordinary', side_effect=ordinary), patch.object(Q.os.path, 'lexists', return_value=False), patch.object(Q.subprocess, 'Popen') as spawn:
            try: Q.primary(ROOT, '0'*40, role='grid')
            except BaseException as exc: caught = exc
        spawn.assert_not_called()
        self.assertEqual(len(visited), 3)
        self.assertEqual(getattr(caught, 'fact', {}).get('stage'), 'GIT_EXECUTABLE_ORDINARY')
        self.assertEqual(caught.fact['role'], 'grid')
        self.assertEqual(caught.fact['errno'], 2)

    def test_git_failure_prefix_cap_and_independent_stream_preservation(self):
        attempted = []; saved = {}
        class Sink:
            def __init__(self, name): self.name = name
            def open(self, mode):
                attempted.append(self.name)
                if 'stdout' in self.name: raise OSError('INERT-WRITE-FAULT')
                return self
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def write(self, raw): saved[self.name] = raw
        class Evidence:
            def __truediv__(self, name): return Sink(name)
        result = {'returncode': 1, 'reason': None, 'total_bytes': 140000,
                  'stdout': b'x'*70000, 'stderr': b'y'*70000}
        fact = Q.retain_git_failure(Evidence(), 'root', 'before', 'rev-parse', result)
        self.assertEqual(len(attempted), 2)
        self.assertEqual(len(next(iter(saved.values()))), 65536)
        self.assertTrue(fact['streams']['stdout']['truncated'])
        self.assertEqual(fact['evidence_errors'], ['STDOUT_PRESERVATION_UNKNOWN'])

    def test_windows_uses_reviewed_absolute_bin_when_old_binding_missing(self):
        old = Path('C:/Program Files/Git/mingw64/bin/git.exe')
        selected = Path('C:/Program Files/Git/bin/git.exe'); visited = []
        def ordinary(path, *args, **kwargs):
            visited.append(path)
            if path == old: raise FileNotFoundError(2, 'INERT_OLD_MISSING')
            if path == selected: raise Q.Denied('INERT_SELECTED_PRECHECK')
            return path
        proxy = SimpleNamespace(name='nt', path=SimpleNamespace(lexists=lambda path: False))
        caught = None
        with patch.object(Q, 'os', proxy), patch.object(Q, 'ordinary', side_effect=ordinary), patch.object(Q.subprocess, 'Popen') as spawn:
            try: Q.primary(ROOT, '0'*40)
            except BaseException as exc: caught = exc
        spawn.assert_not_called()
        self.assertEqual(visited, [ROOT, ROOT/'.git', selected])
        self.assertEqual(getattr(caught, 'fact', {}).get('exception_class'), 'Denied')

    def test_missing_reviewed_windows_bin_denies_without_fallback(self):
        selected = Path('C:/Program Files/Git/bin/git.exe'); visited = []
        def ordinary(path, *args, **kwargs):
            visited.append(path)
            if str(path).endswith('git.exe'): raise FileNotFoundError(2, 'INERT_SELECTED_MISSING')
            return path
        proxy = SimpleNamespace(name='nt', path=SimpleNamespace(lexists=lambda path: False))
        caught = None
        with patch.object(Q, 'os', proxy), patch.object(Q, 'ordinary', side_effect=ordinary), patch.object(Q.subprocess, 'Popen') as spawn:
            try: Q.primary(ROOT, '0'*40)
            except BaseException as exc: caught = exc
        spawn.assert_not_called()
        self.assertEqual(visited, [ROOT, ROOT/'.git', selected])
        self.assertEqual(getattr(caught, 'fact', {}).get('stage'), 'GIT_EXECUTABLE_ORDINARY')
        self.assertEqual(caught.fact['exception_class'], 'FileNotFoundError')

    def test_linux_fixed_usr_bin_binding_is_unchanged(self):
        visited = []
        def ordinary(path, *args, **kwargs):
            visited.append(path)
            if path == Path('/usr/bin/git'): raise Q.Denied('INERT_LINUX_PRECHECK')
            return path
        proxy = SimpleNamespace(name='posix', path=SimpleNamespace(lexists=lambda path: False))
        with patch.object(Q, 'os', proxy), patch.object(Q, 'ordinary', side_effect=ordinary), patch.object(Q.subprocess, 'Popen') as spawn:
            with self.assertRaises(Q.Denied): Q.primary(ROOT, '0'*40)
        spawn.assert_not_called()
        self.assertEqual(visited, [ROOT, ROOT/'.git', Path('/usr/bin/git')])


if __name__ == '__main__': unittest.main()
