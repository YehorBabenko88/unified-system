"""Pinned cross-repository installed-candidate acceptance, independent of unit CI.

Run only with the Stage 8 checkout workflow. These tests never contact Bybit,
PostgreSQL or a production host. Terminan's receipt tests use disposable loopback. Failures are release blockers,
not permission to weaken an existing safety limit.
"""
from __future__ import annotations

from contextlib import closing, nullcontext
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from importlib import metadata
from pathlib import Path
import hashlib
import importlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, call, patch


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

    @staticmethod
    def meta_packet(seconds, price):
        start = datetime(2026, 10, 19, 12, tzinfo=timezone.utc)
        return {
            "Type": "trade_update",
            "Data": {"ticker": "BTCUSDT", "trades": [{
                "time": (start + timedelta(seconds=seconds)).isoformat(),
                "price": price, "size": "1", "side": "Buy",
            }]},
        }

    def test_meta_refuses_storage_and_live_paper_before_mutation(self):
        from meta_analyse.runtime import DurableSinksRequired, Runtime

        store = Mock(spec=["profile", "paper_fill", "connect"])
        cases = ((store, False, False), (store, False, True), (None, True, True))
        for legacy_store, running, paper_enabled in cases:
            with self.subTest(legacy_store=legacy_store is not None, paper_enabled=paper_enabled):
                runtime = Runtime(metascalp=None, exchange=None, store=legacy_store)
                runtime.running = running
                runtime.paper.enabled = paper_enabled
                runtime.symbols = ["BTCUSDT"]
                with self.assertRaisesRegex(DurableSinksRequired, "^GRID_TERMINAN_DURABLE_SINKS_REQUIRED$"):
                    runtime.receive(self.meta_packet(0, "100"))
                self.assertEqual(runtime.minutes, {})
                self.assertEqual(runtime.flow, {})
                self.assertEqual(runtime.paper.reference, {})
                self.assertEqual(runtime.paper.positions, {})
                self.assertEqual(runtime.paper.fills, [])
        self.assertEqual(store.mock_calls, [])

    def test_meta_offline_fill_is_unpersisted(self):
        from meta_analyse.runtime import Runtime

        runtime = Runtime(metascalp=None, exchange=None, store=None)
        self.assertFalse(runtime.paper.enabled)
        runtime.paper.enabled = True
        runtime.symbols = ["BTCUSDT"]
        self.assertEqual(runtime.receive(self.meta_packet(0, "100")), [])
        runtime.receive(self.meta_packet(60, "102"))
        events = runtime.receive(self.meta_packet(61, "100"))
        self.assertEqual(len(runtime.paper.fills), 1)
        self.assertEqual(events, [("paper_fill", "BTCUSDT", runtime.paper.fills[0])])
        reopened = Runtime(metascalp=None, exchange=None, store=None)
        self.assertEqual(reopened.paper.fills, [], "Offline fill must be treated as UNPERSISTED")

    def test_meta_historical_digest_matches_terminan_archive_after_restore(self):
        from meta_analyse.retirement_receipt import persisted_state_receipt
        from terminan.paper_ledger import PaperReplayLedger

        row = [7, "BTCUSDT", "short", "102.0000", "100.00", "target",
               "1.23", "0.10", "1.13", "2026-11-19T00:00:00.123456+00:00"]
        typed_row = [*row[:3], Decimal(row[3]), Decimal(row[4]), row[5],
                     *(Decimal(value) for value in row[6:9]), datetime.fromisoformat(row[9])]
        cursor = Mock()
        cursor.fetchmany.side_effect = [[typed_row], []]
        connection = Mock()
        connection.transaction.return_value = nullcontext()
        connection.execute.side_effect = [None, cursor]
        store = Mock(expected_cluster="synthetic")
        store.connect.return_value = nullcontext(connection)
        receipt = persisted_state_receipt(store, "paper_fills")
        self.assertEqual(connection.mock_calls, [
            call.transaction(),
            call.execute("SET TRANSACTION READ ONLY"),
            call.execute("SELECT id,symbol,side,entry,exit,reason,gross,fees,net,exit_ts "
                         "FROM meta_analyse.paper_fills ORDER BY id"),
        ])
        self.assertEqual(receipt["row_count"], 1)
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / "original.db"
            backup = Path(directory) / "backup.db"
            ledger = PaperReplayLedger(original)
            self.assertEqual(ledger.import_meta_fills("meta-archive", [row], receipt), receipt)
            with closing(sqlite3.connect(original)) as source, closing(sqlite3.connect(backup)) as target:
                source.backup(target)
            restored = PaperReplayLedger(backup)
            self.assertEqual(list(restored.restore_meta_fills("meta-archive")), [row])
            self.assertEqual(restored.import_meta_fills("meta-archive", [row], receipt), receipt)
            with self.assertRaises(ValueError):
                restored.import_meta_fills("meta-archive", [[8, *row[1:]]], receipt)
            self.assertEqual(list(restored.restore_meta_fills("meta-archive")), [row])

    def test_terminan_installed_offline_replay_receipt_recovery(self):
        subprocess.run(
            [sys.executable, "-I", "-B", "-m", "unittest", "discover",
             "-s", "tests", "-p", "test_paper_ledger.py", "-v"],
            cwd=EXTERNAL / "Terminan", check=True, timeout=60,
        )

    def test_terminan_installed_paper_journal_ack_crash_and_restore(self):
        subprocess.run(
            [sys.executable, "-I", "-B", "-m", "unittest", "discover",
             "-s", str(EXTERNAL / "Terminan" / "tests"), "-p", "test_paper_journal.py", "-v"],
            cwd=ROOT, check=True, timeout=60,
        )

    def test_terminan_trade_dto_rejects_non_finite_values(self):
        from terminan.contracts import TradeEvent

        trade = {
            "run_id": "offline", "strategy_id": "paper", "symbol": "BTCUSDT",
            "trade_id": "fill-1", "entry_ms": 1000, "exit_ms": 2000,
            "side": "short", "entry_price": 102.0, "exit_price": 100.0,
            "quantity": 1.0, "pnl": 2.0,
        }
        self.assertEqual(TradeEvent.parse(trade).trade_id, "fill-1")
        for field in ("entry_price", "exit_price", "quantity", "pnl"):
            for value in (float("nan"), float("inf"), float("-inf")):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    TradeEvent.parse(dict(trade, **{field: value}))

    def test_grid_wheel_excludes_strategy_and_scientific_runtime(self):
        distribution = metadata.distribution("unified-grid-market-data")
        self.assertTrue(distribution.files, "Grid wheel file manifest missing")
        forbidden = {
            "scientific_service.py", "scientific_simulation.py",
            "strategy_runner.py", "strategy_runtime.py",
        }
        packaged = {path.name.casefold() for path in distribution.files}
        self.assertFalse(forbidden & packaged, "Grid wheel still packages another module's runtime")
        manifest = EXTERNAL / "bybit-cluster-grid" / "market-wheel-modules.txt"
        allowed = set(manifest.read_text(encoding="utf-8").split())
        installed = {
            item.stem for item in distribution.files
            if item.parts[0] == "grid" and item.suffix == ".py"
        }
        self.assertEqual(installed, allowed, "Grid installed Python modules differ from its allowlist")

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
