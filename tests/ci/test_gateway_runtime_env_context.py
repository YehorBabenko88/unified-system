"""Source-only regression for the exact gateway READ workflow context repair.

This checks the small declared workflow contract without importing its qualifier
or executing any workflow run block, Git provisioning, network or fixture.
"""
import hashlib
from pathlib import Path
import re
import unittest

WORKFLOW = Path(__file__).absolute().parents[2] / '.github/workflows/gateway-runtime-integration.yml'
ROOT_VALUE = '${{ runner.temp }}/grid-gateway-f19'
CONSUMERS = (
    'Provision one exact public Grid source revision outside Unified checkout',
    'Exact unique READ and dependency regressions with primary object guards',
)
ORIGINAL_SHA256 = '038527fab9bb616e10572e9a5dd5e60e63bb3dbb0052b20d1be1c3dbab9dfd85'


class GatewayRuntimeEnvironmentContextTests(unittest.TestCase):
    def source(self):
        raw = WORKFLOW.read_bytes()
        self.assertLess(len(raw), 16384)
        self.assertNotIn(b'\r', raw)
        return raw.decode('utf-8')

    def test_job_environment_does_not_use_runner_context(self):
        text = self.source()
        self.assertEqual(len(re.findall(r'^    env:$', text, re.M)), 1)
        job_env = text.split('    env:\n', 1)[1].split('    steps:\n', 1)[0]
        self.assertNotRegex(job_env, r'\$\{\{\s*runner\.')
        self.assertNotIn('GRID_GATEWAY_SOURCE_ROOT:', job_env)

    def test_both_consumers_bind_the_exact_same_step_environment(self):
        text = self.source()
        for name in CONSUMERS:
            with self.subTest(consumer=name):
                marker = '      - name: ' + name + '\n'
                self.assertEqual(text.count(marker), 1)
                block = text.split(marker, 1)[1].split('\n      - ', 1)[0]
                bindings = re.findall(r'^        env:\n          GRID_GATEWAY_SOURCE_ROOT: (.+)$', block, re.M)
                self.assertEqual(bindings, [ROOT_VALUE])
        self.assertEqual(text.count('GRID_GATEWAY_SOURCE_ROOT: ' + ROOT_VALUE), 2)

    def test_only_the_reviewed_context_binding_changes_from_original(self):
        text = self.source()
        step_env = '        env:\n          GRID_GATEWAY_SOURCE_ROOT: ' + ROOT_VALUE + '\n'
        self.assertEqual(text.count(step_env), 2)
        restored = text.replace(step_env, '')
        self.assertNotIn('GRID_GATEWAY_SOURCE_ROOT:', restored)
        self.assertEqual(restored.count('    steps:\n'), 1)
        restored = restored.replace('    steps:\n', '      GRID_GATEWAY_SOURCE_ROOT: ' + ROOT_VALUE + '\n    steps:\n', 1)
        self.assertEqual(hashlib.sha256(restored.encode('utf-8')).hexdigest(), ORIGINAL_SHA256)


if __name__ == '__main__':
    unittest.main(verbosity=2)
