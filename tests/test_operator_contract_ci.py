import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.operator_contract_ci import REQUIRED_CASES, validate_junit, require_pin, require_fixture_lock, receipt


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
            with self.assertRaisesRegex(ValueError, "IMPORT_ORIGIN_OUTSIDE_TREE"):
                run("a" * 40, folder, Path(folder)/"temp", Path(folder)/"result.xml")
