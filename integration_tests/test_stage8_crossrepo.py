"""Pinned cross-repository installed-candidate acceptance, independent of unit CI.

Run only with the Stage 8 checkout workflow. These tests never contact Bybit,
PostgreSQL, a production host, or start a service. Failures are release blockers,
not permission to weaken an existing safety limit.
"""
from __future__ import annotations

from decimal import Decimal
from importlib import metadata
from pathlib import Path
import importlib
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXTERNAL = ROOT / "external"
PINNED = {
    "math": "98d6783522aac7155cbb4635e5b29239746d88e0",
    "meta_analyse": "b9755d749e598ec3e063740dd099cd8d922299bc",
    "Terminan": "f1abc777a8da0c8748c1cb80b37a09a8464340db",
    "bybit-cluster-grid": "f4dc0409e8ace1628a0e307675505f3a7b626dce",
    "strattester": "1000dccd9ba85eafa4b72bc40a76afae73ca1cee",
}


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
        sys.path.insert(0, str(EXTERNAL / "Terminan"))
        sys.path.insert(0, str(EXTERNAL / "bybit-cluster-grid"))
        cls.math = importlib.import_module("market_profile_math")
        if Path(cls.math.__file__).resolve().is_relative_to((EXTERNAL / "math").resolve()):
            raise AssertionError("Math source checkout bypassed installed SDK")
        cls.meta = importlib.import_module("meta_analyse.orderflow_aggregation")
        cls.Trade = importlib.import_module("meta_analyse.orderflow_metrics").Trade

    @staticmethod
    def rows(n):
        from decimal import Decimal as D
        # One-shot iterable. Preserves event order, precision and unknown side.
        for i in range(n):
            yield (i * 100, D("100.00000001"), D("1.25"),
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
        # This is deliberately RED until Meta #81 switches its actual runtime
        # adapter from list+batch to Math's canonical streaming entrypoint.
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

    def test_grid_and_terminan_owner_boundary(self):
        from grid import terminan_gateway
        from terminan import contracts
        from terminan import data
        self.assertEqual(contracts.StrategyRegistry.__module__,
                         "terminan.contracts")
        self.assertFalse((EXTERNAL / "Terminan" / "terminan" /
                          "strategies.py").exists())
        caps = terminan_gateway.snapshot("/internal/v1/capabilities")
        self.assertEqual(caps["producer"], "bybit-cluster-grid")
        self.assertEqual(caps["capabilities"]["candles"], "UNAVAILABLE")
        self.assertFalse(caps["meta_absorption"]["consumer_cutover"])
        self.assertEqual(data.grid_candles("BTCUSDT"), [])
        self.assertEqual(data.footprint("BTCUSDT"), [])
        self.assertNotIn("pybit", sys.modules)


class MathResearchVsTradingBoundaryTests(unittest.TestCase):
    """Semantic contract: Math may research outcomes, never decide trade sizes.

    The immutable historical kernel is an acknowledged migration blocker.
    Until Terminan owns the policy and consumers switch, this test must stay
    RED instead of deleting the file or suppressing the check.
    """

    def test_math_installed_sdk_is_not_trading_engine(self):
        from importlib import metadata
        distribution = metadata.distribution("unified-math-kernels")
        exposed = {name.lower() for name in distribution.files or ()}
        forbidden = (
            "history_sizing.py", "paper.py", "backtest.py",
            "execution.py", "strategy_runner.py",
        )
        for suffix in forbidden:
            self.assertFalse(any(str(path).endswith(suffix) for path in exposed),
                             f"Math wheel contains execution policy {suffix}")
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
        import ast
        root = EXTERNAL / "math" / "python"
        legacy = root / "history_sizing.py"
        self.assertTrue(legacy.is_file(), "historical source must be preserved")
        source = ast.parse(legacy.read_text(encoding="utf-8"))
        functions = {n.name: n for n in source.body if isinstance(n, ast.FunctionDef)}
        # No change to historical evidence is authorized by this test. Instead,
        # keep the release gate red until apply_sizing policy is moved.
        active = functions.get("apply_sizing")
        if active:
            policy_literals = {
                n.value for n in ast.walk(active)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
            }
            forbidden = {"MARTINGALE", "ANTI_MARTINGALE", "size_multiplier"}
            self.assertFalse(
                forbidden & policy_literals,
                "Math history_sizing.apply_sizing remains an execution "
                "policy: move consumers/logic to Terminan, preserve old "
                "pinned historical profile and test rollback",
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
