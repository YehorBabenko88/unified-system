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
    "math": "bb9cd1fac956620b0ab59482e8b7fd9e8b1f003b",
    "bybit-cluster-grid": "0615fbf9d3bc0919a817e391c150275462cb5143",
    "unified-system": "0b2aa679428dda7e0593a565b216b406533eb522",
    "Terminan": "5a3a752ae680b948979010101db2d5698ffa0aef",
    "meta_analyse": "707e0d0d1e42d1495cb2213d4dc0b23f09a7521a",
    "strattester": "9d8e27fdd31d66b50416308b097daf2dacfd46c3",
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

    def test_grid_wheel_excludes_science_and_strategy_engines(self):
        dist = importlib.metadata.distribution("unified-grid-market-data")
        files = {str(path).replace("\\", "/") for path in dist.files or ()}
        not_market_data = {
            "grid/strategy_executor.py",
            "grid/strategy_runtime.py",
            "grid/strategy_statistics.py",
            "grid/position_sizing_research.py",
            "grid/scientific_simulation.py",
            "grid/scientific_orchestrator.py",
        }
        self.assertFalse(not_market_data & files,
                         "Grid distribution still ships non-Grid scientific/trading "
                         "implementations; move consumers and code before release")

    def test_python_support_policy_is_explicit(self):
        for name in ("math", "Terminan"):
            config = tomllib.loads((EXTERNAL / name / "pyproject.toml")
                                   .read_text(encoding="utf-8"))
            self.assertEqual(config["project"]["requires-python"], ">=3.11",
                             f"{name} must explicitly qualify Python 3.11")
            dist_name = ("unified-math-kernels" if name == "math"
                         else "unified-terminan")
            dist = importlib.metadata.distribution(dist_name)
            self.assertEqual(dist.metadata["Requires-Python"], ">=3.11")
        self.assertGreaterEqual(sys.version_info[:2], (3, 11))

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

    def test_installed_grid_readonly_capabilities_are_not_live(self):
        from grid import terminan_gateway as source
        dist = importlib.metadata.distribution("unified-grid-market-data")
        self.assertEqual(Path(source.__file__).resolve(),
                         Path(dist.locate_file("grid/terminan_gateway.py")).resolve())
        response = source.snapshot("/internal/v1/capabilities")
        self.assertEqual(response["api_version"], {"major": 1, "minor": 0})
        self.assertEqual(response["producer"], "bybit-cluster-grid")
        self.assertTrue(response["read_only"])
        self.assertEqual(response["status"], "UNAVAILABLE")
        self.assertEqual(response["capabilities"]["candles"], "UNAVAILABLE")
        self.assertFalse(response["capabilities"]["live_l2"])
        self.assertFalse(response["meta_absorption"]["consumer_cutover"])
        self.assertFalse(response["meta_absorption"]["execution_authority"])
        self.assertFalse(response["meta_absorption"]["trading_authorized"])

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


class Stage17OwnerBoundaryGates(unittest.TestCase):
    """Negative acceptance tests; fail until canonical owners finish migration."""

    def test_grid_level_timeframes_and_dto_are_accepted_by_math(self):
        from grid.history_snapshot import TIMEFRAME_MINUTES, rollup_snapshot
        from market_compute_api import TIMEFRAME_LEVELS_ABI
        from market_profile_math import _LEVEL_PERIOD_MS
        self.assertEqual(TIMEFRAME_LEVELS_ABI, "math.market.levels.binary64.v1")
        required = {"1h", "4h", "1d", "1w"}
        self.assertTrue(required <= set(TIMEFRAME_MINUTES),
                        "Grid missing canonical Math/Terminan level timeframes")
        self.assertTrue(required <= set(_LEVEL_PERIOD_MS))
        # Grid is the sole rollup owner. The qualified envelope, not a guessed
        # time conversion, must provide explicit closed candle/availability data.
        import inspect
        text = inspect.getsource(rollup_snapshot)
        self.assertIn("available_at_ms", text)
        self.assertIn("watermark_ms", text)

    def test_strattester_legacy_six_column_rows_have_readonly_admission(self):
        """Verify old six-column rows without calling the mutating ResultStore.open."""
        import hashlib
        import sqlite3
        import tempfile
        from terminan.research_archive import ResearchArchive, research_result_receipt
        from terminan.paper_ledger import PaperReplayLedger

        old_row = ("run-1", "BTCUSDT", "POC", "v1", 1780000000.25,
                   '{"original": 1, "raw":"preserved"}')
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "strattester-original.db"
            with sqlite3.connect(source) as db:
                db.execute(
                    "CREATE TABLE research_results (run_id TEXT, symbol TEXT, "
                    "strategy_id TEXT, strategy_version TEXT, "
                    "created_at REAL, metrics TEXT)"
                )
                db.execute("INSERT INTO research_results VALUES (?,?,?,?,?,?)", old_row)
            before = hashlib.sha256(source.read_bytes()).hexdigest()
            # mode=ro; never invoke Strattester ResultStore.open (ALTER/CREATE/WAL).
            uri = source.resolve().as_uri() + "?mode=ro"
            with sqlite3.connect(uri, uri=True) as db:
                rows = db.execute(
                    "SELECT run_id,symbol,strategy_id,strategy_version,created_at,metrics "
                    "FROM research_results ORDER BY run_id,symbol,strategy_id,strategy_version"
                ).fetchall()
                staged = db.execute(
                    "SELECT 1 FROM sqlite_master WHERE name='staged_research_results'"
                ).fetchone()
            self.assertIsNone(staged)
            tables = {"research_results": rows}
            receipt = research_result_receipt(before, tables)
            target = ResearchArchive(PaperReplayLedger(Path(root) / "terminan.db"))
            self.assertEqual(
                target.import_snapshot("legacy-6", tables, receipt), receipt
            )
            self.assertEqual(
                list(target.read_snapshot("legacy-6")),
                [("research_results", "LEGACY_UNFENCED", old_row)],
            )
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)
            # Import again with the same immutable identity, not a second fill/row.
            self.assertEqual(target.import_snapshot("legacy-6", tables, receipt), receipt)

    def test_coordinator_never_trusts_worker_derived_approval(self):
        """Independent approval is a trusted HMAC, not (owner, digest(ticket))."""
        import subprocess
        source = (EXTERNAL / "unified-system" / "scripts" /
                  "stage13_worker_admission.py").read_text(encoding="utf-8")
        self.assertNotIn("approval != (scope.owner, digest)", source)
        self.assertIn("def _verify_review(", source)
        self.assertIn("hmac.compare_digest", source)
        self.assertIn("reviewer_key", source)
        self.assertIn("dispatcher.casefold() == scope.owner.casefold()", source)
        self.assertIn("if not callable(self._source)", source)
        # Execute the canonical owner's negative tests, rather than recreate
        # an independent signing implementation in the integration suite.
        subprocess.run(
            [sys.executable, "-B", "-m", "unittest",
             "tests.test_stage13_worker_admission", "-v"],
            cwd=EXTERNAL / "unified-system", check=True, timeout=45,
        )


if __name__ == "__main__":
    unittest.main()
