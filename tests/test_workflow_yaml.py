"""Parse actual workflow documents; plain shell colons must not become YAML maps."""
from pathlib import Path
import unittest
import yaml

class WorkflowYamlTests(unittest.TestCase):
    def test_all_workflows_have_scalar_run_commands(self):
        paths=sorted((Path(__file__).resolve().parents[1]/'.github/workflows').glob('*.yml'))
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(workflow=path.name):
                document=yaml.safe_load(path.read_bytes())
                self.assertIsInstance(document,dict)
                for job in document['jobs'].values():
                    for step in job.get('steps',[]):
                        if 'run' in step:self.assertIsInstance(step['run'],str)

    def test_shell_colon_requires_a_yaml_scalar(self):
        with self.assertRaises(yaml.YAMLError):
            yaml.safe_load('run: python -m pip install --only-binary=:all: --require-hashes\n')
        parsed=yaml.safe_load('run: |\n  python -m pip install --only-binary=:all: --require-hashes\n')
        self.assertEqual(parsed['run'],'python -m pip install --only-binary=:all: --require-hashes\n')
