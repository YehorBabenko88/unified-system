"""Pinned cross-repository installed-candidate acceptance, independent of unit CI.

Run only with the Stage 8 checkout workflow. These tests never contact Bybit,
PostgreSQL, a production host, or start a service. Failures are release blockers,
not permission to weaken an existing safety limit.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from importlib import metadata
from pathlib import Path
import hashlib
import importlib
import json
import os
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
EXTERNAL = ROOT / "external"
COHORT_PATH = Path(__file__).with_name("crossrepo-cohort.json")
PINNED = json.loads(COHORT_PATH.read_text(encoding="utf-8"))["heads"]


class PinnedInstalledCandidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for name, pin in PINNED.items():
            root = EXTERNAL / name
            if not root.is_dir():
                raise AssertionError(f"required checkout missing: {name}")
            actual = subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                text=True, stderr=subprocess.DEVNULL, timeout=5,
            ).strip()
            if actual != pin:
                raise AssertionError(f"unreviewed checkout revision: {name}")
        if metadata.version("unified-math-kernels") != "0.1.0":
            raise AssertionError("required installed Math SDK missing")
        # The Math computation must resolve from a built/installed distribution,
        # not from a direct project checkout or an accidental PYTHONPATH fallback.
        sys.path.insert(0, str(EXTERNAL / "meta_analyse" / "src"))
        cls.math = importlib.import_module("market_profile_math")
        if Path(cls.math.__file__).resolve().is_relative_to((EXTERNAL / "math").resolve()):
            raise AssertionError("Math source checkout bypassed installed SDK")
        cls.meta = importlib.import_module("meta_analyse.orderflow_aggregation")
        cls.Trade = importlib.import_module("meta_analyse.orderflow_metrics").Trade

    @staticmethod
    def rows(n):
        # One-shot iterable. Preserves event order, precision and unknown side.
        for i in range(n):
            yield (i * 100, Decimal("100.00000001"), Decimal("1.25"),
                   ("buy", "sell", "unknown")[i % 3])

    def test_single_math_owner_and_legacy_batch_boundary(self):
        self.assertEqual(self.math.MAX_ORDERFLOW_BATCH, 20_000)
        compute_api = importlib.import_module("market_compute_api")
        self.assertEqual(compute_api.STREAM_ABI, "math.market.orderflow.stream.v1")
        self.assertIs(self.meta.aggregate_orderflow_stream,
                      compute_api.aggregate_orderflow_stream)
        self.assertTrue(callable(self.math.aggregate_orderflow_stream))
        self.assertEqual(
            self.math.aggregate_orderflow(list(self.rows(20_000)),
                                          mode="time", interval_ms=60_000)[0][0], 0
        )
        with self.assertRaisesRegex(ValueError, "INVALID_AGGREGATE_BATCH"):
            self.math.aggregate_orderflow(list(self.rows(20_001)),
                                          mode="time", interval_ms=60_000)

    def test_math_stream_cardinalities_and_decimal_parity(self):
        for n in (19_999, 20_000, 20_001, 100_000):
            with self.subTest(n=n):
                result = self.math.aggregate_orderflow_stream(
                    self.rows(n), mode="time", interval_ms=60_000,
                    initial_delta=Decimal("3.5"),
                )
                self.assertEqual(sum(m["trade_count"] for _, m in result), n)
                expected_buy = (n + 2) // 3
                expected_sell = (n + 1) // 3
                expected_unknown = n // 3
                self.assertEqual(
                    sum((m["buy_volume"] for _, m in result), Decimal(0)),
                    Decimal("1.25") * expected_buy,
                )
                self.assertEqual(
                    sum((m["sell_volume"] for _, m in result), Decimal(0)),
                    Decimal("1.25") * expected_sell,
                )
                self.assertEqual(
                    sum((m["unknown_volume"] for _, m in result), Decimal(0)),
                    Decimal("1.25") * expected_unknown,
                )
                self.assertEqual(result[-1][1]["cumulative_delta"],
                                 Decimal("3.5") + Decimal("1.25") *
                                 (expected_buy - expected_sell))
                self.assertEqual(list(key for key, _ in result),
                                 sorted(key for key, _ in result))

    def test_math_stream_late_price_buckets_and_one_shot(self):
        data = iter([
            (120_000, Decimal("101.1"), Decimal("2"), "buy"),
            (0, Decimal("100.2"), Decimal("3"), "unknown"),
            (60_000, Decimal("100.8"), Decimal("1"), "sell"),
        ])
        result = self.math.aggregate_orderflow_stream(
            data, mode="price", tick_size=Decimal("1"),
            initial_delta=Decimal("4"),
        )
        self.assertEqual([k for k, _ in result],
                         [Decimal("100"), Decimal("101")])
        self.assertEqual(result[0][1]["unknown_volume"], Decimal("3"))
        self.assertEqual(result[0][1]["cumulative_delta"], Decimal("3"))
        self.assertEqual(result[1][1]["cumulative_delta"], Decimal("5"))
        self.assertEqual(list(data), [], "input iterator must be consumed once")

    def test_meta_runtime_adapter_100k_uses_single_math_stream(self):
        self.assertIs(self.meta.aggregate_orderflow_stream,
                      self.math.aggregate_orderflow_stream)
        for n in (19_999, 20_000, 20_001, 100_000):
            with self.subTest(n=n):
                trades = (
                    self.Trade(ts, price, volume, side)
                    for ts, price, volume, side in self.rows(n)
                )
                output = self.meta.aggregate_by_time(trades, 60_000)
                self.assertEqual(sum(m.trade_count for _, m in output), n)
                self.assertEqual(output[-1][1].cumulative_delta,
                                 Decimal("1.25") * (((n + 2) // 3) -
                                                    ((n + 1) // 3)))

    def test_unified_two_node_recovery_and_data_rollback(self):
        subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "discover",
             "-s", "tests", "-p", "test_fleet_control.py", "-v"],
            cwd=EXTERNAL / "unified-system", check=True, timeout=60,
        )

    def test_meta_runtime_uses_installed_terminan_paper_engine(self):
        from meta_analyse.runtime import Runtime
        from terminan.paper import PaperEngine

        runtime = Runtime(metascalp=None, exchange=None)
        self.assertIs(type(runtime.paper), PaperEngine)
        distribution = metadata.distribution("unified-terminan")
        self.assertEqual(
            Path(sys.modules[PaperEngine.__module__].__file__).resolve(),
            Path(distribution.locate_file("terminan/paper.py")).resolve(),
        )

    def test_meta_forwards_paper_fill_to_storage(self):
        from meta_analyse.runtime import Runtime

        store = Mock(spec=["profile", "paper_fill"])
        runtime = Runtime(metascalp=None, exchange=None, store=store)
        self.assertFalse(runtime.paper.enabled)
        runtime.paper.enabled = True
        runtime.symbols = ["BTCUSDT"]
        start = datetime(2026, 10, 19, 12, tzinfo=timezone.utc)

        for seconds, price in ((0, "100"), (60, "102"), (61, "100")):
            events = runtime.receive({
                "Type": "trade_update",
                "Data": {"ticker": "BTCUSDT", "trades": [{
                    "time": (start + timedelta(seconds=seconds)).isoformat(),
                    "price": price, "size": "1", "side": "Buy",
                }]},
            })

        self.assertEqual(len(runtime.paper.fills), 1)
        fill = runtime.paper.fills[0]
        self.assertEqual(events, [("paper_fill", "BTCUSDT", fill)])
        store.paper_fill.assert_called_once_with(fill)

    def test_grid_wheel_excludes_strategy_and_scientific_runtime(self):
        distribution = metadata.distribution("unified-grid-market-data")
        self.assertTrue(distribution.files, "Grid wheel file manifest missing")
        forbidden = {
            "scientific_service.py", "scientific_simulation.py",
            "strategy_runner.py", "strategy_runtime.py",
        }
        packaged = {path.name.casefold() for path in distribution.files}
        self.assertFalse(forbidden & packaged, "Grid wheel still packages another module's runtime")

    def test_grid_and_terminan_owner_boundary(self):
        from grid import terminan_gateway
        from terminan import contracts, data

        grid_distribution = metadata.distribution("unified-grid-market-data")
        self.assertEqual(
            Path(terminan_gateway.__file__).resolve(),
            Path(grid_distribution.locate_file("grid/terminan_gateway.py")).resolve(),
        )
        self.assertEqual(contracts.StrategyRegistry.__module__,
                         "terminan.contracts")
        self.assertFalse((EXTERNAL / "Terminan" / "terminan" /
                          "strategies.py").exists())
        distribution = metadata.distribution("unified-terminan")
        self.assertEqual(
            Path(contracts.__file__).resolve(),
            Path(distribution.locate_file("terminan/contracts.py")).resolve(),
        )
        offline_env = {"TERMINAN_GRID_API_PORT": "", "TERMINAN_GRID_DSN": ""}
        with patch.dict(os.environ, offline_env):
            caps = terminan_gateway.snapshot("/internal/v1/capabilities")
            self.assertEqual(data.grid_candles("BTCUSDT"), [])
            self.assertEqual(data.footprint("BTCUSDT"), [])
        self.assertEqual(caps["producer"], "bybit-cluster-grid")
        self.assertEqual(caps["capabilities"]["candles"], "UNAVAILABLE")
        self.assertFalse(caps["meta_absorption"]["consumer_cutover"])
        self.assertNotIn("pybit", sys.modules)


class MathResearchVsTradingBoundaryTests(unittest.TestCase):
    """Check the installed research API and retirement of the sizing source."""

    def test_math_installed_sdk_is_not_trading_engine(self):
        distribution = metadata.distribution("unified-math-kernels")
        self.assertTrue(distribution.files, "Math wheel file manifest missing")
        exposed = {path.name.casefold() for path in distribution.files}
        forbidden = (
            "history_sizing.py", "paper.py", "backtest.py",
            "execution.py", "strategy_runner.py",
        )
        for filename in forbidden:
            self.assertNotIn(
                filename, exposed, f"Math wheel contains execution policy {filename}",
            )
        import market_compute_api
        self.assertFalse(market_compute_api.compute_batch({
            "schema": "math.market.compute.v1",
            "execution_authority": False,
            "source": {
                "snapshot_sha256": "0" * 64,
                "as_of_ms": 0,
                "units": {"price": "quote/base", "volume": "base"},
            },
            "operations": [{
                "operation": "executed_volume_delta",
                "input": {"buy": "1", "sell": "0"},
            }],
        })["execution_authority"])

    def test_no_active_trade_size_policy_in_math_source(self):
        math_root = EXTERNAL / "math"
        legacy = "python/history_sizing.py"
        git = ["git", "--no-replace-objects", "-C", str(math_root)]
        self.assertFalse(
            subprocess.check_output([*git, "ls-tree", "HEAD", "--", legacy], timeout=5),
            "Math still tracks the retired position-sizing module",
        )
        self.assertFalse((math_root / legacy).exists(), "Retired position-sizing module is importable")
        original = subprocess.check_output(
            [*git, "show", "3a9c542841e160f8b1924f155aaa2d1a676dfd04:" + legacy], timeout=5,
        )
        self.assertEqual(
            hashlib.sha256(original).hexdigest(),
            "ad050a83871842d9fa77559738dee7b71fd5ba75325bc3f633956729d460ef73",
            "Original Math sizing source must remain available for parity",
        )

    def test_runtime_api_has_no_trade_execution_verb(self):
        from market_compute_api import ALGORITHMS
        trading_ops = {
            "open_position", "close_position", "place_order",
            "simulate_fill", "execute_strategy", "apply_sizing",
            "calculate_trade_pnl", "paper_trade",
        }
        self.assertFalse(set(ALGORITHMS) & trading_ops)


if __name__ == "__main__":
    unittest.main()
