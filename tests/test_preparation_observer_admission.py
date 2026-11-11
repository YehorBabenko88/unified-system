"""Source-bound admission regressions; explicit make_suite binding required.

No qualifier import, filesystem backend, child process, or observer helper run.
AST execution is for trusted, hash-pinned source only, not a sandbox.
"""
import ast
import hashlib
import io
import json
import sys
import types
import unittest
from unittest.mock import patch


class MemoryPath:
    def __init__(self, records, name='memory'):
        self.records, self.name = records, name

    def __truediv__(self, name):
        return MemoryPath(self.records, self.name + '/' + name)

    def __str__(self):
        return '<' + self.name + '>'

    def write_text(self, value):
        if len(value.encode('utf-8')) > 65536:
            raise RuntimeError('bounded memory output exceeded')
        self.records[self.name] = value
        return len(value)

    def open(self, mode, encoding):
        if (mode, encoding) != ('w', 'utf-8'):
            raise RuntimeError('unsupported memory operation')
        destination = self

        class Log(io.StringIO):
            def write(self, value):
                if self.tell() + len(value) > 16384:
                    raise RuntimeError('bounded memory log exceeded')
                return super().write(value)

            def close(self):
                if not self.closed:
                    destination.write_text(self.getvalue())
                super().close()

        return Log()


def make_suite(qualifier_source_bytes, *, expected_source_sha256):
    if type(qualifier_source_bytes) is not bytes or len(qualifier_source_bytes) > 65536:
        raise ValueError('bounded qualifier bytes required')
    if hashlib.sha256(qualifier_source_bytes).hexdigest() != expected_source_sha256:
        raise ValueError('qualifier source pin mismatch')
    parsed = ast.parse(qualifier_source_bytes, filename='<pinned-qualifier>')
    selected = []
    for name in ('OBSERVER_IDS', 'case_ids', 'observer_controls'):
        matches = [node for node in parsed.body if
                   (isinstance(node, ast.FunctionDef) and node.name == name) or
                   (isinstance(node, ast.Assign) and any(
                       isinstance(target, ast.Name) and target.id == name
                       for target in node.targets))]
        if len(matches) != 1:
            raise ValueError('exact actual AST definition required: ' + name)
        selected.extend(matches)
    namespace = dict(unittest=unittest, sys=sys, json=json,
                     time=types.SimpleNamespace(perf_counter_ns=lambda: 1))
    exec(compile(ast.Module(body=selected, type_ignores=[]),
                 '<pinned-qualifier>', 'exec'), namespace)
    suite = unittest.TestSuite()
    for name in unittest.defaultTestLoader.getTestCaseNames(PreparationObserverAdmissionControls):
        case = PreparationObserverAdmissionControls(name)
        case.actual = namespace
        suite.addTest(case)
    return suite


class PreparationObserverAdmissionControls(unittest.TestCase):
    def setUp(self):
        if not hasattr(self, 'actual'):
            raise RuntimeError('explicit make_suite(source bytes, source pin) required')

    def invoke(self, scenario):
        ids = self.actual['OBSERVER_IDS']
        self.assertEqual(len(set(ids)), 12)
        module_name, class_name, _ = ids[0].rsplit('.', 2)
        self.assertEqual(module_name, 'test_preparation_child_observer')
        methods = {}
        for index, identity in enumerate(ids):
            prefix, name = identity.rsplit('.', 1)
            self.assertEqual(prefix, module_name + '.' + class_name)

            def body(case, fail=(index == 0 and scenario == 'expected_failure')):
                if fail:
                    case.fail('synthetic genuine expected failure')

            if index == 0 and scenario != 'success':
                body = unittest.expectedFailure(body)
            methods[name] = body
        synthetic = types.ModuleType(module_name)
        methods['__module__'] = module_name
        setattr(synthetic, class_name, type(class_name, (unittest.TestCase,), methods))
        actual_results = []
        original_runner = unittest.TextTestRunner

        class RecordingRunner(original_runner):
            def run(self, suite):
                result = super().run(suite)
                actual_results.append(result)
                return result

        records = {}
        denied = False
        with patch.dict(sys.modules, {module_name: synthetic}), patch.object(
                unittest, 'TextTestRunner', RecordingRunner):
            try:
                self.actual['observer_controls'](MemoryPath(records, 'root'),
                                                 MemoryPath(records, 'out'))
            except ValueError:
                denied = True
        self.assertEqual(len(actual_results), 1)
        result = actual_results[0]
        self.assertEqual((result.testsRun, len(result.skipped), len(result.failures),
                          len(result.errors)), (12, 0, 0, 0))
        self.assertEqual(len(result.expectedFailures), int(scenario == 'expected_failure'))
        self.assertEqual(len(result.unexpectedSuccesses), int(scenario == 'unexpected_success'))
        return denied

    def test_actual_observer_controls_accepts_normal_twelve_successes(self):
        self.assertFalse(self.invoke('success'))

    def test_actual_observer_controls_rejects_expected_failure(self):
        self.assertTrue(self.invoke('expected_failure'))

    def test_actual_observer_controls_rejects_unexpected_success(self):
        self.assertTrue(self.invoke('unexpected_success'))
