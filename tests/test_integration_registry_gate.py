"""Calibrate the actual workflow result expression without executing its Git/native job."""
import ast
from pathlib import Path
import unittest

class RegistryResultGateTests(unittest.TestCase):
    def test_exact_success_gate_refuses_all_non_success_unittest_outcomes(self):
        raw=(Path(__file__).resolve().parents[1]/'.github/workflows/integration-registry.yml').read_text(encoding='utf8')
        lines=[line.strip() for line in raw.splitlines() if line.strip().startswith('assert result.testsRun==13 ')]
        self.assertEqual(len(lines),1)
        expression=ast.parse(lines[0]).body[0].test
        def accepted(result):
            return eval(compile(ast.Expression(expression),'<actual-registry-workflow-gate>','eval'),{'result':result})
        good=unittest.TestResult();good.testsRun=13
        self.assertTrue(accepted(good))
        for field in ('failures','errors','skipped','expectedFailures','unexpectedSuccesses'):
            result=unittest.TestResult();result.testsRun=13
            getattr(result,field).append((self,'calibration'))
            with self.subTest(field=field):self.assertFalse(accepted(result))
        for count in (0,12,14):
            result=unittest.TestResult();result.testsRun=count
            with self.subTest(count=count):self.assertFalse(accepted(result))
