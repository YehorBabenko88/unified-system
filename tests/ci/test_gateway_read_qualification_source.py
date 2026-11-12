"""AST-only READ cohort checks. Never import selected Gateway/TLS test modules."""
import ast
import fnmatch
import hashlib
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
WRAPPER = 'docs/intelligence/runtime-integration/run_read_qualification.py'
HELPER = 'docs/intelligence/identity/run_qualification.py'
SELECTIONS = [('tests', 'test_intelligence_gateway.py', None),
              ('tests', 'test_gateway_identity.py', None),
              ('tests/gateway_runtime', 'test_*.py', None),
              ('tests/storage', 'test*.py', 'tests'),
              ('tests/storage/gateway_disclosure', 'test_*.py', None)]


def literal(tree, name):
    return ast.literal_eval(next(n.value for n in tree.body if isinstance(n, ast.Assign)
                                 and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)))


def selected_files(folder, pattern):
    # unittest discover recurses only into regular packages, not every subfolder.
    for path in sorted(folder.iterdir()):
        if path.is_file() and fnmatch.fnmatchcase(path.name, pattern):
            yield path
        elif path.is_dir() and (path/'__init__.py').is_file():
            init = ast.parse((path/'__init__.py').read_bytes())
            assert not any(isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.Assign)) for n in ast.walk(init)), 'PACKAGE_DISCOVERY_AMBIGUOUS'
            yield from selected_files(path, pattern)


def audit_import(node, source):
    # External imports in this reviewed cohort are explicit non-TestCase symbols.
    external = {'unittest.mock', 'datetime', 'pathlib', 'copy', 'concurrent.futures',
                'dataclasses', 'cryptography', 'cryptography.hazmat.primitives',
                'cryptography.hazmat.primitives.asymmetric', 'cryptography.x509.oid'}
    if node.module in external and not node.level:
        return
    assert source is not None, 'UNKNOWN_IMPORTED_CLASS'
    if node.level:
        assert node.level == 1, 'RELATIVE_IMPORT_AMBIGUOUS'
        path = source.parent/(node.module.replace('.', '/')+'.py')
    else:
        path = ROOT/(node.module.replace('.', '/')+'.py')
        if not path.is_file():
            path = source.parent/(node.module.replace('.', '/')+'.py')
    assert path.is_file(), 'UNKNOWN_IMPORTED_CLASS'
    tree = ast.parse(path.read_bytes())
    for imported in node.names:
        definitions = [n for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == imported.name]
        values = [n.value for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == imported.name for t in n.targets)]
        assert len(definitions)+len(values) == 1, 'IMPORTED_EXPORT_AMBIGUOUS'
        if definitions and isinstance(definitions[0], ast.ClassDef):
            cls = definitions[0]
            assert all(ast.unparse(b) in ('ValueError', 'RuntimeError', 'Exception', 'object') for b in cls.bases), 'FOREIGN_TESTCASE_OR_INHERITANCE'
            assert all(ast.unparse(d.func if isinstance(d, ast.Call) else d) == 'dataclass' for d in cls.decorator_list), 'FOREIGN_CLASS_DECORATOR'
        if values:
            assert not any(isinstance(n, (ast.Call, ast.Name, ast.Attribute)) for n in ast.walk(values[0])), 'DYNAMIC_IMPORTED_EXPORT'


def module_ids(raw, module, source=None):
    tree = ast.parse(raw)
    assert not any(isinstance(n, ast.Name) and n.id == 'load_tests' for n in ast.walk(tree)), 'LOAD_TESTS_AMBIGUOUS'
    assert not any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == 'load_tests' for n in ast.walk(tree)), 'LOAD_TESTS_AMBIGUOUS'
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert not any(isinstance(child, ast.ClassDef) for node in tree.body
                   if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                   for child in ast.walk(node)), 'CONDITIONAL_OR_DYNAMIC_CLASS'
    names = {n.name for n in classes}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            assert all(n.name != '*' and n.name not in names for n in node.names), 'IMPORTED_TESTCASE_AMBIGUOUS'
            assert not any(n.name.endswith(('Tests', 'TestCase')) for n in node.names), 'IMPORTED_TESTCASE_AMBIGUOUS'
            audit_import(node, source)
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            assert all(isinstance(t, ast.Name) and t.id not in names for t in targets), 'DYNAMIC_CLASS_ALIAS'
            # Current module constants use literals and Path only, never test factories.
            for call in [n for n in ast.walk(node.value) if isinstance(n, ast.Call)]:
                assert ast.unparse(call.func) in ('Path', 'Path(__file__).resolve'), 'DYNAMIC_TEST_FACTORY'
        if isinstance(node, (ast.For, ast.While, ast.Try, ast.With)):
            raise AssertionError('DYNAMIC_MODULE_DEFINITION')
        if isinstance(node, ast.Expr) and not isinstance(node.value, ast.Constant):
            assert isinstance(node.value, ast.Call) and ast.unparse(node.value.func) == 'sys.path.insert', 'DYNAMIC_MODULE_MUTATION'
        if isinstance(node, ast.If):
            assert ast.unparse(node.test) == "__name__ == '__main__'", 'CONDITIONAL_MODULE_DEFINITION'
            assert len(node.body) == 1 and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Call) and ast.unparse(node.body[0].value.func) == 'unittest.main', 'DYNAMIC_MAIN'
    result = []
    for cls in classes:
        for node in cls.body:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                assert not any(isinstance(t, ast.Name) and t.id.startswith('test') for t in targets), 'DYNAMIC_METHOD_ALIAS'
        methods = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith('test')]
        nested = [n for node in cls.body if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                  for n in ast.walk(node) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith('test')]
        assert not nested, 'CONDITIONAL_OR_DYNAMIC_METHOD'
        if not methods:
            continue
        assert not cls.decorator_list and [ast.unparse(b) for b in cls.bases] in (['unittest.TestCase'], ['unittest.IsolatedAsyncioTestCase']), 'INHERITANCE_OR_DECORATOR_AMBIGUOUS'
        assert all(not n.decorator_list for n in methods), 'DYNAMIC_METHOD_DECORATOR'
        result.extend(module+'.'+cls.name+'.'+n.name for n in methods)
    return result


def selected_ids():
    result = []
    for folder, pattern, top in SELECTIONS:
        for path in selected_files(ROOT/folder, pattern):
            module = '.'.join(path.relative_to(ROOT/(top or folder)).with_suffix('').parts)
            result.extend(module_ids(path.read_bytes(), module, path))
    assert len(result) == len(set(result)), 'DUPLICATE_DISCOVERY_IDS'
    return sorted(result)


class ReadSourceCohortTests(unittest.TestCase):
    def test_exact_current_primary_helper_pin(self):
        wrapper = ast.parse((ROOT/WRAPPER).read_bytes())
        raw = subprocess.check_output(['git', '-C', str(ROOT), 'show', 'HEAD:'+HELPER])
        self.assertEqual(literal(wrapper, 'GUARD_SHA256'), hashlib.sha256(raw).hexdigest())

    def test_exact_selected_inventory_without_importing_or_executing_cases(self):
        wrapper = ast.parse((ROOT/WRAPPER).read_bytes())
        self.assertEqual(literal(wrapper, 'REQUIRED'), selected_ids())

    def test_reviewed_original_146_ids_are_preserved(self):
        ids = selected_ids()
        strict = 'test_gateway_identity.StrictTLSFixtureTests.test_generated_chain_handshakes_with_explicit_strict_verification'
        self.assertIn(strict, ids)
        prior = [name for name in ids if name != strict]
        self.assertEqual(len(prior), 146)
        self.assertEqual(hashlib.sha256(json.dumps(prior, separators=(',', ':')).encode()).hexdigest(),
                         '7aa5683c7463983bac2a473d86dd56b57e287a097d8d3e1b07c1a9accb995891')

    def test_all_five_discovery_selections_stay_exact(self):
        tree = ast.parse((ROOT/WRAPPER).read_bytes())
        loops = [n for n in ast.walk(tree) if isinstance(n, ast.For) and isinstance(n.target, ast.Tuple)
                 and [ast.unparse(t) for t in n.target.elts] == ['folder', 'pattern', 'top']]
        self.assertEqual(len(loops), 1)
        self.assertEqual(ast.literal_eval(loops[0].iter), SELECTIONS)

    def test_unmodelled_discovery_is_denied_instead_of_guessed(self):
        for raw in ['def load_tests(a,b,c): pass', 'if True:\n class A(unittest.TestCase):\n  def test_a(self):pass',
                    'class A(OtherBase):\n def test_a(self):pass', 'from foreign import ForeignTests',
                    'from foreign import Alternate', 'A=make_test_case()', 'setattr(A,"test_a",f)',
                    'class A(unittest.TestCase):\n test_alias=f',
                    'class A(unittest.TestCase):\n if True:\n  def test_a(self):pass']:
            with self.subTest(raw=raw), self.assertRaises(AssertionError):
                module_ids(raw, 'inert')


if __name__ == '__main__':
    unittest.main()
