"""Stage 12 fail-closed four-module ABI qualification.

Pinned CodeX A-F source trees are supplied as local *data* by the test runner.
No live network or production host/database access. Tests describe whether the
four release owners are independently installable; they do not create another
Grid, Math, Terminan, or Unified implementation.
"""
from __future__ import annotations

import ast
import importlib.metadata
import importlib.util
from pathlib import Path
import re
import sys
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXTERNAL = ROOT / "external"
PINS = {
    "math": "3c5841573eee579331df7d8e992017b35b0d4ce7",
    "bybit-cluster-grid": "b4bd236d198b503001907d53a455a378659d5408",
    "unified-system": "79c2730b1d1c0d7aab69bab0523108039b5a3d85",
    "Terminan": "dec68f4f5fc8e0c4cc89f9ddd975d71eee60b527",
    "meta_analyse": "dc9b0789a8a56f0ad30ec74d5d3f4bb26464f910",
    "strattester": "a007968bd74987cf71852f8f82ba1c7e54c3742c",
}


class FourModuleIndependentABITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import subprocess
        for repo, head in PINS.items():
            folder = EXTERNAL / repo
            if not folder.is_dir():
                raise AssertionError(f"missing required exact-head checkout: {repo}")
            result = subprocess.check_output(
                ["git", "-C", str(folder), "rev-parse", "HEAD"],
                text=True, timeout=8,
            ).strip()
            if result != head:
                raise AssertionError(f"source HEAD mismatch: {repo}")

    def test_math_wheel_exports_observation_bootstrap_not_trade_policy(self):
        # This is red until Math owner exports its existing pure statistical
        # implementation. Do not copy this implementation into Unified/Grid.
        dist = importlib.metadata.distribution("unified-math-kernels")
        names = {p.name for p in dist.files or ()}
        self.assertIn("history_statistics.py", names,
                      "Math wheel missing canonical research observation bootstrap")
        self.assertNotIn("history_sizing.py", names)
        import history_statistics
        self.assertTrue(callable(history_statistics.paired_observation_bootstrap))
        self.assertTrue(callable(history_statistics.block_observation_bootstrap))
        self.assertFalse(hasattr(history_statistics, "paired_expectancy_bootstrap"))

    def test_grid_is_independently_packageable_no_source_checkout_import(self):
        folder = EXTERNAL / "bybit-cluster-grid"
        # Release requirement: pip wheel by this repository alone.
        # A missing pyproject.toml must remain a visible failure, not a skip.
        build = folder / "pyproject.toml"
        self.assertTrue(build.is_file(),
                        "Grid has no independent wheel metadata/SDK contract")
        config = tomllib.loads(build.read_text(encoding="utf-8"))
        self.assertEqual(config["project"]["name"], "unified-grid-market-data")
        self.assertEqual(config["project"]["requires-python"], ">=3.11")
        dist = importlib.metadata.distribution("unified-grid-market-data")
        self.assertEqual(dist.version, "0.1.0")
        self.assertTrue(dist.files, "installed Grid wheel manifest missing")
        installed = {str(path).replace("\\\\", "/") for path in dist.files}
        self.assertIn("grid/__init__.py", installed)
        self.assertIn("grid/terminan_gateway.py", installed)
        self.assertIn("grid/schema.sql", installed)
        spec = importlib.util.find_spec("grid")
        self.assertIsNotNone(spec)
        self.assertEqual(Path(spec.origin).resolve(),
                         Path(dist.locate_file("grid/__init__.py")).resolve())

    def test_python_support_policy_is_explicit(self):
        for name in ("math", "Terminan"):
            config = tomllib.loads((EXTERNAL / name / "pyproject.toml")
                                   .read_text(encoding="utf-8"))
            self.assertEqual(config["project"]["requires-python"], ">=3.12",
                             f"{name} must not be reported 3.11 compatible")
        self.assertGreaterEqual(sys.version_info[:2], (3, 12))

    def test_market_gateway_never_executes_strategy(self):
        grid = (EXTERNAL / "bybit-cluster-grid" /
                "grid" / "terminan_gateway.py").read_text(encoding="utf-8")
        ast.parse(grid)
        forbidden = (
            "from terminan.paper import",
            "from terminan.strategies import",
            "from strattester.research.runner import",
        )
        for pattern in forbidden:
            self.assertNotIn(pattern, grid)
        self.assertIn("/internal/v1/history/snapshots/read", grid)

    def test_unified_fleet_has_no_market_execution(self):
        source = (EXTERNAL / "unified-system" / "unified_system" /
                  "fleet_control.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        cls = next(x for x in tree.body
                   if isinstance(x, ast.ClassDef) and x.name == "FleetControl")
        names = {x.name for x in cls.body if isinstance(x, ast.FunctionDef)}
        self.assertTrue({"heartbeat", "place", "validate_lease", "restore"} <= names)
        self.assertFalse({"buy", "sell", "place_order", "simulate_fill"} & names)

    def test_terminan_owns_replay_receipts(self):
        source = (EXTERNAL / "Terminan" / "terminan" /
                  "paper.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        classes = {x.name for x in tree.body if isinstance(x, ast.ClassDef)}
        functions = {x.name for x in tree.body
                     if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertIn("PaperEngine", classes)
        self.assertIn("replay_paper", functions)
        self.assertTrue({"apply_sizing", "ruin_stats", "trade_net_pnl"} <= functions)


if __name__ == "__main__":
    unittest.main()
