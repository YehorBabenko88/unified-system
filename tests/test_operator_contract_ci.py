import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.operator_contract_ci import HELPER_CASES, REQUIRED_CASES, validate_junit, require_pin, require_fixture_lock, receipt


class EvidenceTests(unittest.TestCase):
    def test_root_pin_is_required_and_fence_owns_exact_head_check(self):
        require_pin('a' * 40)
        for value in ('0' * 39, 'A' * 40, '', None):
            with self.assertRaises(ValueError): require_pin(value)

    def test_only_exact_root_fixture_lock_admitted(self):
        raw = (Path(__file__).resolve().parents[1] / 'docs/ci/operator-command/requirements-linux.lock').read_bytes()
        require_fixture_lock(raw)
        for changed in (raw + b'\n', raw[:-1], bytearray(raw)):
            with self.assertRaises(ValueError): require_fixture_lock(changed)

    def test_inventory_requires_every_unique_case_no_skip_or_failure(self):
        def xml(cases, extra=''):
            from xml.sax.saxutils import escape
            return '<testsuites><testsuite>' + ''.join(
                '<testcase classname="' + escape(c, {'"':'&quot;'}) + '" name="' +
                escape(n, {'"':'&quot;'}) + '">' + extra + '</testcase>' for c, n in cases
            ) + '</testsuite></testsuites>'
        self.assertEqual(len(REQUIRED_CASES), 86)
        self.assertEqual(len([c for c,n in REQUIRED_CASES if c == 'tests.test_operator_command_composition.CommandCompositionTests']), 3)
        self.assertEqual(len([c for c,n in REQUIRED_CASES if c == 'tests.test_consul_command_store']), 51)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'results.xml'
            path.write_text(xml(REQUIRED_CASES)); self.assertEqual(validate_junit(path), 86)
            for content in (xml(REQUIRED_CASES[:-1]), xml(REQUIRED_CASES + [REQUIRED_CASES[0]]),
                            xml(REQUIRED_CASES, '<skipped/>'), xml(REQUIRED_CASES, '<failure/>'),
                            xml(REQUIRED_CASES, '<error/>'),
                            xml([('foreign.Case', 'test_foreign')] + REQUIRED_CASES[1:]), xml([])):
                path.write_text(content)
                with self.assertRaises(ValueError): validate_junit(path)

        # The actual helper-mode inventory is distinct from the86 primary cases.
        self.assertEqual(len(HELPER_CASES),10)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'helpers.xml'
            path.write_text(xml(HELPER_CASES));self.assertEqual(validate_junit(path,expected=HELPER_CASES),10)
            # Lists from a JSON-shaped manifest must normalize identically.
            self.assertEqual(validate_junit(path,expected=[list(pair) for pair in HELPER_CASES]),10)
            for content in (xml(HELPER_CASES[:-1]),xml(HELPER_CASES+[HELPER_CASES[0]]),xml(HELPER_CASES,'<skipped/>'),xml(HELPER_CASES,'<failure/>'),xml(HELPER_CASES,'<error/>'),xml([('foreign.Case','unexpected')]+HELPER_CASES[1:])):
                path.write_text(content)
                with self.assertRaises(ValueError):validate_junit(path,expected=HELPER_CASES)

    def test_receipt_uses_existing_root_fence_before_and_after_and_no_grid(self):
        import integration.source_guard as source_guard
        root = Path(__file__).resolve().parents[1]
        events = []
        class Fence:
            def __init__(self, actual, head, *, isolated_cache):
                events.append(('init', actual, head, isolated_cache))
            def check(self): events.append('check'); return {'head': 'a' * 40}
            def module(self, module): events.append(('module', module.__name__))
            def file(self, file, **kwargs): events.append(('file', Path(file).name))
            def finish(self): events.append('finish')
        with patch.object(source_guard, 'SourceFence', Fence), patch('sys.pycache_prefix', str(root.parent / 'fixture-cache')):
            value = receipt(root, 'a' * 40)
        self.assertEqual(events[0][1:3], (root, 'a' * 40))
        self.assertEqual(events[1], 'check'); self.assertEqual(events[-1], 'finish')
        self.assertIn(('module', 'integration.source_guard'), events)
        self.assertIn(('file', 'operator_contract_ci.py'), events)
        self.assertIn(('file', 'requirements-linux.lock'), events)
        self.assertNotIn('grid', value)
        self.assertEqual(value['schema'], 'unified.operator-contract-ci.v2')
        self.assertEqual(value['production'], 'NO_GO')

    def test_execution_helper_refuses_unqualified_runtime_before_imports(self):
        from scripts.run_operator_command_contracts import run
        with patch("sys.pycache_prefix", None):
            with self.assertRaisesRegex(ValueError, "ISOLATED_NO_BYTECODE_CACHE_REQUIRED"):
                run("a" * 40, ".", "external-temp", "external-junit")

    def test_execution_helper_checks_foreign_cached_app_after_pytest(self):
        import sys, types
        import pytest
        import integration.source_guard as source_guard
        from scripts.run_operator_command_contracts import run
        root = Path(__file__).resolve().parents[1]
        class Fence:
            def __init__(self, *args, **kwargs): pass
            def check(self): pass
            def file(self, *args, **kwargs): pass
            def finish(self): pass
            def module(self, module):
                if getattr(module, "__file__", None) == "FOREIGN_APP.py":
                    raise ValueError("IMPORT_ORIGIN_OUTSIDE_TREE")
                return "fixture-module"
        foreign = types.SimpleNamespace(__file__="FOREIGN_APP.py")
        with tempfile.TemporaryDirectory() as folder, patch.object(source_guard, "SourceFence", Fence), patch.object(pytest, "main", return_value=0), patch.dict(sys.modules, {"unified_system.foreign_cached_test": foreign}), patch.object(sys, "path", sys.path.copy()), patch.object(sys, "pycache_prefix", str(Path(folder) / "cache")):
            with self.assertRaisesRegex(ValueError, "PRELOADED_APPLICATION_MODULE_REJECTED"):
                run("a" * 40, folder, Path(folder)/"temp", Path(folder)/"result.xml")

        # Separate post-test fake: preserve the original after-pytest obligation.
        # No SourceFence/Git/provider is executed; shared post-cache verifier is real.
        from scripts import run_operator_command_contracts as runner
        api = self.cache_api()
        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder) / 'post-cache';cache.mkdir()
            state = (cache, api['plain_directory'](cache))
            reflected = types.SimpleNamespace(__file__=str(root/'unified_system/operator_control_plane.py'), __cached__=str(Path(folder)/'foreign.pyc'))
            with patch.object(source_guard,'SourceFence',Fence), patch.object(pytest,'main',return_value=0) as executed, patch('scripts.operator_contract_ci.validate_junit',return_value=86), patch.object(runner,'cache_bootstrap',return_value=(api,state,root/'integration/four_owner/import_custody.py')), patch.dict(sys.modules,{'unified_system.reflected_cache_fixture':reflected}), patch.object(sys,'path',sys.path.copy()), patch.object(sys,'pycache_prefix',str(cache)):
                with self.assertRaisesRegex(ValueError,'APPLICATION_CACHED_PATH_REJECTED'):
                    run('a'*40,folder,Path(folder)/'temp',Path(folder)/'result.xml')
                executed.assert_called_once()

    @staticmethod
    def cache_api():
        root = Path(__file__).resolve().parents[1]
        helper = root / 'integration/four_owner/import_custody.py'
        api = {'__name__': 'constant_cache_fixture', '__file__': str(helper)}
        exec(compile(helper.read_bytes(), str(helper), 'exec', dont_inherit=True), api)
        return api

    def test_shared_cache_refuses_reused_and_polluted_prefix(self):
        import sys
        api = self.cache_api()
        # Only a harmless cache fixture: no app code is imported under this prefix.
        before = dict(sys.modules);prefix = sys.pycache_prefix
        try:
            for name in tuple(sys.modules):
                if api['application'](name): del sys.modules[name]
            with tempfile.TemporaryDirectory() as folder:
                cache = Path(folder) / 'fresh';sys.pycache_prefix = str(cache)
                state = api['begin'](cache, ())
                with self.assertRaisesRegex(ValueError, 'FRESH_IMPORT_CACHE_REQUIRED'):api['begin'](cache, ())
                (cache / 'poison.pyc').write_bytes(b'constant-only fixture')
                with self.assertRaisesRegex(ValueError, 'IMPORT_CACHE_NOT_EMPTY_OR_CHANGED'):api['empty'](state)
        finally:
            sys.pycache_prefix = prefix
            for name in tuple(sys.modules):
                if name not in before:del sys.modules[name]
            sys.modules.update(before)

    def test_shared_cache_rejects_preloaded_application(self):
        import sys,types
        api = self.cache_api()
        with tempfile.TemporaryDirectory() as folder, patch.dict(sys.modules, {'unified_system.constant_fixture': types.ModuleType('constant_fixture')}), patch.object(sys,'pycache_prefix',str(Path(folder)/'cache')):
            with self.assertRaisesRegex(ValueError,'PRELOADED_APPLICATION_MODULE_REJECTED'):api['begin'](Path(sys.pycache_prefix),())

    def test_shared_cache_rejects_reflected_cached_path(self):
        import sys,types
        api = self.cache_api();before = dict(sys.modules);prefix = sys.pycache_prefix
        try:
            for name in tuple(sys.modules):
                if api['application'](name):del sys.modules[name]
            with tempfile.TemporaryDirectory() as folder:
                base=Path(folder).resolve();cache=base/'cache';sys.pycache_prefix=str(cache);state=api['begin'](cache,())
                source=base/'constant.py';source.write_bytes(b'VALUE=1\n')
                fixture=types.ModuleType('unified_system.constant_fixture');fixture.__file__=str(source);fixture.__cached__=str(base/'foreign.pyc')
                sys.modules[fixture.__name__]=fixture
                with self.assertRaisesRegex(ValueError,'APPLICATION_CACHED_PATH_REJECTED'):api['verify_loaded'](state,base,base)
        finally:
            sys.pycache_prefix=prefix
            for name in tuple(sys.modules):
                if name not in before:del sys.modules[name]
            sys.modules.update(before)

    def test_shared_cache_cli_prefix_must_match(self):
        import sys
        api=self.cache_api()
        with tempfile.TemporaryDirectory() as folder,patch.object(sys,'pycache_prefix',str(Path(folder)/'declared')):
            with self.assertRaisesRegex(ValueError,'MATCHING_CLI_IMPORT_CACHE_PREFIX_REQUIRED'):api['begin'](Path(folder)/'other',())
