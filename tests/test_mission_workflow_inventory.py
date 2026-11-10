"""Static CI admission regressions; never import or execute fixture tests."""
import ast
import hashlib
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def workflow_data():
    text = (ROOT / '.github/workflows/durable-mission-controller.yml').read_text()
    line = next(s.strip() for s in text.splitlines() if s.strip().startswith('required=['))
    required = ast.literal_eval(line.split('=', 1)[1])
    child = text.split('child="""', 1)[1].split('"""', 1)[0]
    child = '\n'.join(s[10:] if s.startswith('          ') else s for s in child.splitlines())
    gate = next(n for n in ast.parse(child).body if isinstance(n, ast.Assert) and 'ids' in ast.unparse(n.test))
    expression = compile(ast.Expression(gate.test), '<CI inventory predicate>', 'eval')
    return required, lambda ids, expected: eval(expression, {'__builtins__': {'len': len, 'set': set}}, {'ids': ids, 'required': expected})


def static_case_ids():
    result = []
    for name in ('test_mission_controller', 'test_journal'):
        tree = ast.parse((ROOT / 'tests' / (name + '.py')).read_text())
        for cls in tree.body:
            if isinstance(cls, ast.ClassDef):
                result.extend(name + '.' + cls.name + '.' + method.name for method in cls.body
                              if isinstance(method, ast.FunctionDef) and method.name.startswith('test_'))
    return sorted(result)


class MissionWorkflowInventoryTests(unittest.TestCase):
    def test_original_47_ids_are_preserved(self):
        required, _ = workflow_data()
        original = [name for name in required if '.ContinuationTests.' not in name
                    and not name.endswith('.test_owned_temp_alias_is_resolved_before_guarded_journal_creation')]
        self.assertEqual(len(original), 47)
        digest = hashlib.sha256(json.dumps(sorted(original), separators=(',', ':')).encode()).hexdigest()
        self.assertEqual(digest, '5b18c7e3128d1810aa67a66730732265ec66daff410aa7baa20553aa5bf75495')

    def test_workflow_admits_all_58_existing_cases(self):
        required, gate = workflow_data()
        actual = static_case_ids()
        self.assertEqual(len(actual), 58)
        self.assertEqual(sorted(required), actual)
        self.assertTrue(gate(actual, required))

    def test_duplicate_expected_id_is_denied_before_execution(self):
        required, gate = workflow_data()
        self.assertFalse(gate(required, required + [required[0]]))

    def test_missing_extra_or_duplicate_discovery_is_denied(self):
        required, gate = workflow_data()
        for ids in (required[:-1], required + ['unexpected.case'], required + [required[0]]):
            with self.subTest(ids=len(ids)):
                self.assertFalse(gate(ids, required))


if __name__ == '__main__':
    unittest.main()
