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
    "math": "8de3858cd5ca9a63dc3cd10f5f5cdec870ef4440",
    "bybit-cluster-grid": "beed235e6883aeee808eb1b80fc80a2a35057202",
    "unified-system": "04f32a12c0f3b58c0bebe402f2d9057cf4671cf3",
    "Terminan": "4035647edb332260859850ad2a3ffc1044a4c818",
    "meta_analyse": "f4880de89a59ea2e557b47daaa74ae491ac240fb",
    "strattester": "55e652295882220303506cc18ce6c99027b6ca35",
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
        """Synthetic v4 multi-candle Grid→Terminan→Math, never LIVE authentication."""
        from unittest.mock import patch
        from grid.history_snapshot import (MULTIPIN_MINUTES, plan_multipin,
                                           read_multipin_rollup)
        from grid.provenance import digest
        from terminan.levels import grid_level_candles, levels_from_grid_series
        from market_compute_api import TIMEFRAME_LEVELS_ABI

        self.assertEqual(TIMEFRAME_LEVELS_ABI, "math.market.levels.binary64.v1")
        day = 86_400_000
        for timeframe in ("1h", "4h", "1d", "1w"):
            with self.subTest(timeframe=timeframe):
                width = MULTIPIN_MINUTES[timeframe] * 60_000
                start = 4 * day if timeframe == "1w" else 0
                end, as_of = start + 2 * width, start + 2 * width + 60_000
                catalog, envelopes, pins = {}, {}, []
                cursor = start
                while cursor < end:
                    page_end = min(end, cursor + 1_800 * 60_000)
                    entry = {
                        "request": {
                            "venue": "bybit", "market_type": "linear",
                            "symbol": "BTCUSDT", "start_ms": cursor,
                            "end_ms": page_end, "as_of_ms": as_of,
                            "units": {"price": "quote/base", "volume": "base"},
                        },
                        "trust": {
                            "evidence_class": "HISTORICAL", "identity": "fixture",
                            "source_revision": "fixture-v1", "epoch": "fixture",
                        },
                    }
                    pin = digest(entry)
                    catalog[pin] = entry
                    pins.append(pin)
                    minute_rows = [
                        {"event_start_ms": t, "event_end_ms": t + 60_000,
                         "open": 10.0, "close": 10.0,
                         "high": 12.0, "low": 8.0, "volume": 1.0,
                         "available_at_ms": t + 60_000,
                         "watermark_ms": t + 60_000}
                        for t in range(cursor, page_end, 60_000)
                    ]
                    envelopes[pin] = {
                        "rows": minute_rows,
                        "dataset_id": "fixture-" + str(len(pins)),
                        "dataset_fingerprint": digest(minute_rows),
                        "source": {"identity": "fixture",
                                   "source_revision": "fixture-v1",
                                   "epoch": "fixture"},
                        "request": entry["request"],
                    }
                    cursor = page_end
                selection = {
                    "schema": "grid.history.selection.v4",
                    "timeframe": timeframe, "snapshot_ids": pins,
                    "start_ms": start, "end_ms": end,
                    "venue": "bybit", "market_type": "linear",
                    "symbol": "BTCUSDT",
                }
                pages = plan_multipin(selection, catalog)
                self.assertEqual(len(pages), len(pins))
                def load(_conn, page, _catalog, *, continuing):
                    self.assertEqual(continuing, page["snapshot_id"] != pins[0])
                    return envelopes[page["snapshot_id"]]
                with patch("grid.history_snapshot.select_snapshot", side_effect=load):
                    result = read_multipin_rollup(None, selection, pages, catalog)
                self.assertEqual(result["schema"], "grid.history.rollup.v3")
                self.assertEqual(len(result["rows"]), 2)
                candles = grid_level_candles(
                    result, trusted_fingerprint=result["dataset_fingerprint"],
                    symbol="BTCUSDT", market_type="linear",
                    timeframe=timeframe, start_ms=start, end_ms=end, as_of_ms=as_of)
                self.assertEqual(candles, [
                    {"t": start, "h": 12.0, "l": 8.0, "complete": True},
                    {"t": start + width, "h": 12.0, "l": 8.0, "complete": True},
                ])
                self.assertTrue(levels_from_grid_series(
                    result, trusted_fingerprint=result["dataset_fingerprint"],
                    symbol="BTCUSDT", market_type="linear",
                    timeframe=timeframe, start_ms=start, end_ms=end, as_of_ms=as_of))
                altered = dict(result, rows=[dict(result["rows"][0], high=999.0),
                                             result["rows"][1]])
                with self.assertRaises(ValueError):
                    grid_level_candles(
                        altered, trusted_fingerprint=result["dataset_fingerprint"],
                        symbol="BTCUSDT", market_type="linear", timeframe=timeframe,
                        start_ms=start, end_ms=end, as_of_ms=as_of)

    def test_strattester_legacy_six_column_rows_have_readonly_admission(self):
        """Real frozen exporter→Terminan archive; original bytes remain unchanged."""
        import hashlib
        import sqlite3
        import tempfile
        from contextlib import closing
        from strattester.persistence.frozen_results import import_frozen_results
        from terminan.research_archive import ResearchArchive
        from terminan.paper_ledger import PaperReplayLedger
        from importlib import metadata

        installed = metadata.distribution("strattester")
        import strattester.persistence.frozen_results as frozen
        self.assertEqual(
            Path(frozen.__file__).resolve(),
            Path(installed.locate_file("strattester/persistence/frozen_results.py")).resolve()
        )
        old_row = ("run-1", "BTCUSDT", "POC", "v1", 1780000000.25,
                   '{"original": 1, "raw":"preserved"}')
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "strattester-original.db"
            with closing(sqlite3.connect(source)) as db, db:
                db.execute(
                    "CREATE TABLE research_results ("
                    "run_id TEXT NOT NULL, symbol TEXT NOT NULL, "
                    "strategy_id TEXT NOT NULL, strategy_version TEXT NOT NULL, "
                    "created_at REAL NOT NULL, metrics TEXT NOT NULL, "
                    "PRIMARY KEY(run_id,symbol,strategy_id,strategy_version))"
                )
                db.execute("INSERT INTO research_results VALUES (?,?,?,?,?,?)", old_row)
            before = hashlib.sha256(source.read_bytes()).hexdigest()
            dest = Path(root) / "terminan.db"
            receipt = import_frozen_results(source, before, "legacy-6", dest)
            self.assertEqual(receipt["tables"]["research_results"]["row_count"], 1)
            target = ResearchArchive(PaperReplayLedger(dest))
            self.assertEqual(
                list(target.read_snapshot("legacy-6")),
                [("research_results", "LEGACY_UNFENCED", old_row)],
            )
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)
            self.assertEqual(import_frozen_results(source, before, "legacy-6", dest),
                             receipt)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)

            # A table with the SAME column names but no declared constraints
            # is not the pinned historical six-column schema.
            malformed = Path(root) / "spoofed.db"
            with closing(sqlite3.connect(malformed)) as db, db:
                db.execute("CREATE TABLE research_results ("
                           "run_id TEXT, symbol TEXT, strategy_id TEXT, "
                           "strategy_version TEXT, created_at REAL, metrics TEXT)")
                db.execute("INSERT INTO research_results VALUES (?,?,?,?,?,?)", old_row)
            wrong_before = hashlib.sha256(malformed.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, "unrecognized published result schema"):
                import_frozen_results(malformed, wrong_before, "spoofed", dest)
            self.assertEqual(hashlib.sha256(malformed.read_bytes()).hexdigest(),
                             wrong_before)
            with self.assertRaises(KeyError):
                list(target.read_snapshot("spoofed"))

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
