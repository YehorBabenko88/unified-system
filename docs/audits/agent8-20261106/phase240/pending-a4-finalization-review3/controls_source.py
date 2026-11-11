"""SOURCE PREPARATION ONLY: no imports/compilation/execution yet authorized.

Future make_suite receives exact source TEXT, selects actual AST, and runs only
the selected guard/finalization on inert data. Never imports the real inner.
"""
import ast
import hashlib
import io
import json
from types import SimpleNamespace
import unittest

SOURCE_SHA256 = 'a2fc13badb1354fa3aff63c188abda59aea0394f0d45b70a6ead34396c743d02'


def make_suite(actual_source_bytes):
    if type(actual_source_bytes) is not bytes or hashlib.sha256(actual_source_bytes).hexdigest() != SOURCE_SHA256:
        raise ValueError('EXACT_INNER_SOURCE_REQUIRED')
    tree = ast.parse(actual_source_bytes)
    ordinary = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'ordinary')
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    attempt = next(n for n in main.body if isinstance(n, ast.Try) and n.finalbody)
    tail = attempt.finalbody[-4:]
    # Exact original selection: cleanup assignment, state gate, receipt dict,
    # exclusive receipt write. No earlier main/import/loader/fixture execution.
    if not (len(tail) == 4 and isinstance(tail[0], ast.Assign)
            and isinstance(tail[0].targets[0], ast.Name) and tail[0].targets[0].id == 'cleanup'
            and isinstance(tail[1], ast.If) and isinstance(tail[2], ast.Assign)
            and isinstance(tail[3], ast.With)):
        raise ValueError('FINALIZATION_SELECTION_CHANGED_REVIEW_REQUIRED')
    function = ast.FunctionDef(name='selected_finalization', args=ast.arguments(
        posonlyargs=[], args=[ast.arg(arg='state')], kwonlyargs=[], kw_defaults=[], defaults=[]),
        body=tail, decorator_list=[])
    selected = ast.fix_missing_locations(ast.Module(body=[ordinary, function], type_ignores=[]))

    class FinalizationControls(unittest.TestCase):
        def evaluate(self, cache_kind):
            trace = []; writes = []; receipt_buffer = io.StringIO()

            class Node:
                def __init__(self, name, kind='DIR', parents=()):
                    self.name = name; self.kind = kind; self.parents = list(parents)

                def lstat(self):
                    trace.append(('lstat', self.name))
                    if self.kind == 'MISSING':
                        raise FileNotFoundError('INERT_MISSING')
                    return SimpleNamespace(st_mode=self.kind, st_reparse_tag=1 if self.kind == 'REPARSE' else 0,
                                           st_file_attributes=0, st_nlink=1)

                def iterdir(self):
                    trace.append(('enumerate', self.name))
                    # Inert backend never follows a path. The trace detects even
                    # attempted enumeration before the actual guard rejected it.
                    if cache_kind in ('unsafe_ancestor', 'missing', 'unavailable'):
                        raise OSError('INERT_ENUMERATION_UNAVAILABLE')
                    return iter(('item',) if cache_kind == 'nonempty' else ())

                def __truediv__(self, name):
                    if name != 'ACTUAL-RESULT.json':
                        raise AssertionError('UNEXPECTED_RECEIPT_NAME')
                    return self

                def open(self, mode, encoding):
                    if mode != 'x' or encoding != 'utf8' or writes:
                        raise AssertionError('EXCLUSIVE_RECEIPT_REQUIRED')
                    writes.append(mode)
                    class Sink:
                        def __enter__(self): return receipt_buffer
                        def __exit__(self, *args): return False
                    return Sink()

            ancestor = Node('ancestor', 'REPARSE' if cache_kind == 'unsafe_ancestor' else 'DIR')
            cache = Node('cache', 'MISSING' if cache_kind == 'missing' else 'DIR', [ancestor])
            root = Node('evidence')
            stat = SimpleNamespace(S_ISLNK=lambda mode: mode == 'LINK',
                                   S_ISDIR=lambda mode: mode in ('DIR', 'REPARSE'),
                                   S_ISREG=lambda mode: mode == 'FILE')
            namespace = dict(stat=stat, cache=cache, ROOT=root, json=json,
                threading=SimpleNamespace(enumerate=lambda: []), baseline=set(),
                boundary=[], state='NEW_FEATURE_PREREQUISITE_ABSENT_NOT_SIX_TEST_FAILURES',
                failure=None, result=None, actual_ids=[], before={}, after={}, loaded=[], special=[],
                effects={}, source={'head': 'MODEL_SOURCE', 'tree': 'MODEL_TREE'}, c={'expected_ids': []})
            # Future modeled execution only: actual selected AST, inert bindings.
            exec(compile(selected, '<actual-inner-finalization-ast>', 'exec'), namespace)
            exception = None
            try:
                namespace['selected_finalization'](namespace['state'])
            except BaseException as exc:
                exception = type(exc).__name__
            raw = receipt_buffer.getvalue()
            return trace, json.loads(raw) if raw else None, exception

        def test_empty_cache_preserves_prerequisite_receipt(self):
            trace, receipt, error = self.evaluate('empty')
            self.assertIsNone(error)
            self.assertTrue(receipt['cleanup']['cache_empty'])
            self.assertEqual(receipt['state'], 'NEW_FEATURE_PREREQUISITE_ABSENT_NOT_SIX_TEST_FAILURES')

        def test_nonempty_cache_denies(self):
            trace, receipt, error = self.evaluate('nonempty')
            self.assertIsNone(error)
            self.assertFalse(receipt['cleanup']['cache_empty'])
            self.assertEqual(receipt['state'], 'BOUNDARY_FAILURE_NOT_PRODUCT_RED')

        def test_unsafe_ancestry_never_enumerates_and_records_unknown(self):
            trace, receipt, error = self.evaluate('unsafe_ancestor')
            self.assertFalse(any(event == 'enumerate' for event, _ in trace))
            self.assertIsNone(error)
            self.assertIsNotNone(receipt)
            self.assertIsNone(receipt['cleanup']['cache_empty'])
            self.assertTrue(receipt['boundary_errors'])

        def test_missing_cache_never_enumerates_and_records_unknown(self):
            trace, receipt, error = self.evaluate('missing')
            self.assertFalse(any(event == 'enumerate' for event, _ in trace))
            self.assertIsNone(error)
            self.assertIsNotNone(receipt)
            self.assertIsNone(receipt['cleanup']['cache_empty'])
            self.assertTrue(receipt['boundary_errors'])

        def test_enumeration_unavailable_records_unknown_receipt(self):
            trace, receipt, error = self.evaluate('unavailable')
            self.assertIsNone(error)
            self.assertIsNotNone(receipt)
            self.assertIsNone(receipt['cleanup']['cache_empty'])
            self.assertTrue(receipt['boundary_errors'])

    return unittest.defaultTestLoader.loadTestsFromTestCase(FinalizationControls)
