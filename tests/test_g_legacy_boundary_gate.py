"""Synthetic fail-closed tests; no remote Git fetch, subprocess, DB or imports."""
import copy
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("g_boundary", ROOT / "tools/g_legacy_boundary_gate.py")
gate = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = gate
spec.loader.exec_module(gate)

FIXTURES = {
    "grid/strategy_runner.py": """from .strategy_executor import execute_job_subprocess
async def strategy_worker(db):
    await execute_job_subprocess(db, {})
""",
    "grid/strategy_executor.py": """from .ml_process_supervisor import run_supervised_process
async def execute_job_subprocess(db, job):
    await run_supervised_process([sys.executable, '-m', 'grid.strategy_runtime'], timeout_seconds=5)
""",
    "grid/strategy_runtime.py": """async def main():
    pool = await asyncpg.create_pool('fixture-only')
""",
    "grid/ml_process_supervisor.py": """async def run_supervised_process(argv, *, timeout_seconds): pass
""",
    "grid/strategy_jobs.py": """async def ensure_strategy_schema(pool): pass
""",
    "grid/strategy_plugins.py": """async def get_plugin(pool, name, version): pass
""",
}


class AgentGLegacyBoundaryGateTests(unittest.TestCase):
    def test_active_chain_is_recognized_but_deletion_stays_denied(self):
        decision = gate.assess_legacy_strategy_boundary(FIXTURES, source_head=gate.SOURCE_HEAD)
        self.assertEqual(decision.status, gate.DENY)
        self.assertIn("ACTIVE_LEGACY_CONSUMER_CHAIN", decision.reasons)
        self.assertFalse(decision.deletion_authorized)
        self.assertFalse(decision.release_authorized)

    def test_wrong_head_fails_closed(self):
        decision = gate.assess_legacy_strategy_boundary(FIXTURES, source_head="0" * 40)
        self.assertIn("SOURCE_PIN_MISMATCH", decision.reasons)
        self.assertFalse(decision.deletion_authorized)

    def test_each_missing_file_fails_closed(self):
        for path in gate.LEGACY:
            with self.subTest(path=path):
                sources = dict(FIXTURES)
                sources.pop(path)
                decision = gate.assess_legacy_strategy_boundary(sources, source_head=gate.SOURCE_HEAD)
                self.assertIn("MISSING_SOURCE:" + path, decision.reasons)
                self.assertFalse(decision.deletion_authorized)

    def test_mutated_launch_and_import_fail_closed(self):
        bad = dict(FIXTURES)
        bad["grid/strategy_executor.py"] = bad["grid/strategy_executor.py"].replace(
            "grid.strategy_runtime", "grid.other_runtime"
        )
        result = gate.assess_legacy_strategy_boundary(bad, source_head=gate.SOURCE_HEAD)
        self.assertIn("LEGACY_CHAIN_UNVERIFIED:EXECUTOR_MODULE_LAUNCH", result.reasons)
        bad2 = dict(FIXTURES)
        bad2["grid/strategy_runner.py"] = "async def strategy_worker(db): pass"
        result2 = gate.assess_legacy_strategy_boundary(bad2, source_head=gate.SOURCE_HEAD)
        self.assertIn("LEGACY_CHAIN_UNVERIFIED:RUNNER_EXECUTOR_IMPORT", result2.reasons)

    def test_syntax_failure_is_not_silent(self):
        bad = dict(FIXTURES)
        bad["grid/strategy_jobs.py"] = "async def broken("
        result = gate.assess_legacy_strategy_boundary(bad, source_head=gate.SOURCE_HEAD)
        self.assertIn("SYNTAX_INVALID:grid/strategy_jobs.py", result.reasons)
        self.assertFalse(result.deletion_authorized)

    def test_non_dict_source_map_cannot_be_trusted(self):
        result = gate.assess_legacy_strategy_boundary({}, source_head=gate.SOURCE_HEAD)
        self.assertEqual(result.status, gate.DENY)
        self.assertFalse(result.release_authorized)
        self.assertIn("MISSING_SOURCE:grid/strategy_runner.py", result.reasons)


if __name__ == "__main__":
    unittest.main()
