"""Pinned cross-repository installed-candidate acceptance, independent of unit CI.

Run only with the Stage 8 checkout workflow. These tests never contact Bybit,
PostgreSQL or a production host. Terminan's receipt tests use disposable loopback. Failures are release blockers,
not permission to weaken an existing safety limit.
"""
from __future__ import annotations

from contextlib import closing, nullcontext
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext
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

    def test_terminan_installed_full_suite(self):
        subprocess.run(
            [sys.executable, "-I", "-B", "-m", "unittest", "discover",
             "-s", str(EXTERNAL / "Terminan" / "tests"), "-v"],
            cwd=ROOT, check=True, timeout=60,
        )

    def test_meta_offline_delivery_uses_installed_terminan_journal(self):
        meta = EXTERNAL / "meta_analyse"
        with tempfile.TemporaryDirectory(prefix="meta-delivery-", dir=ROOT) as scratch:
            subprocess.run(
                [sys.executable, "-I", "-B", "-m", "pytest", "-q",
                 "--basetemp", str(Path(scratch) / "pytest"),
                 "-c", str(meta / "pyproject.toml"),
                 str(meta / "tests" / "test_offline_paper_delivery.py")],
                cwd=ROOT, check=True, timeout=60,
            )

    def test_unified_c3_requires_operational_admission(self):
        subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "discover",
             "-s", "tests", "-p", "test_ci_service_operational_admission.py", "-v"],
            cwd=EXTERNAL / "unified-system", check=True, timeout=60,
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

    def test_grid_installed_pinned_history_rollup(self):
        grid_tests = EXTERNAL / "bybit-cluster-grid" / "tests"
        subprocess.run(
            [sys.executable, "-I", "-B", "-m", "pytest", "-q",
             str(grid_tests / "test_terminan_gateway_contract.py"),
             "-k", "pinned_history_rollup or pinned_rollup_refuses or pinned_multipin"],
            cwd=ROOT, check=True, timeout=60,
        )

    def test_grid_multipin_candles_feed_installed_terminan_and_math(self):
        from grid import terminan_gateway
        from terminan.levels import grid_level_candles, untouched_levels

        grid_tests = EXTERNAL / "bybit-cluster-grid" / "tests"
        with patch.object(sys, "path", [str(grid_tests), *sys.path]):
            from test_history_snapshot import Connection
            from test_terminan_gateway_contract import _multipin_history

            for timeframe, start, pages in (
                ("1h", 0, [60]), ("4h", 0, [120, 120]), ("1d", 0, [1440]),
                ("1w", 4 * 86_400_000, [1680] * 6),
            ):
                with self.subTest(timeframe=timeframe):
                    request, catalog, rows = _multipin_history(timeframe, start, pages)
                    connection = Connection([])

                    def execute(sql, params=None):
                        connection.calls.append((sql, params))
                        if params:
                            connection.rows = rows[params[1]]

                    with patch.object(connection, "execute", side_effect=execute), \
                            patch.object(terminan_gateway, "_snapshot_catalog", return_value=catalog), \
                            patch.object(terminan_gateway, "_history_connection", return_value=connection):
                        response = terminan_gateway.pinned_history(request)

                    self.assertEqual(response["source_authentication"], "EXTERNAL_NOT_INDEPENDENTLY_VERIFIED")
                    self.assertFalse(response["trading_authorized"])
                    snapshot = response["snapshot"]
                    end = request["end_ms"]
                    selection = dict(symbol=request["symbol"], market_type=request["market_type"],
                                     timeframe=timeframe, start_ms=start, end_ms=end, as_of_ms=end)
                    # This fixture pin checks adapter compatibility. It conveys no production trust.
                    trusted_pin = snapshot["dataset_fingerprint"]
                    candles = grid_level_candles(snapshot, trusted_fingerprint=trusted_pin, **selection)
                    self.assertEqual(len(candles), 1)
                    self.assertEqual(candles[0]["t"], start)
                    self.assertEqual(untouched_levels(candles, timeframe, end - 1), [])
                    levels = untouched_levels(candles, timeframe, end)
                    self.assertEqual(
                        {level["side"]: level["price"] for level in levels},
                        {"high": snapshot["rows"][0]["high"], "low": snapshot["rows"][0]["low"]},
                    )
                    with self.assertRaises(ValueError):
                        grid_level_candles(snapshot, trusted_fingerprint="0" * 64, **selection)
                    changed = dict(snapshot, rows=[dict(snapshot["rows"][0], high=999)])
                    with self.assertRaises(ValueError):
                        grid_level_candles(changed, trusted_fingerprint=trusted_pin, **selection)

    def test_terminan_can_read_six_column_strattester_results_without_changes(self):
        from terminan.data import research
        from terminan.paper_ledger import PaperReplayLedger
        from terminan.research_archive import ResearchArchive, research_result_receipt

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "old-results.sqlite3"
            with closing(sqlite3.connect(source)) as db, db:
                db.execute(
                    "CREATE TABLE research_results (run_id TEXT, symbol TEXT, strategy_id TEXT, "
                    "strategy_version TEXT, created_at REAL, metrics TEXT)"
                )
                db.execute(
                    "INSERT INTO research_results VALUES (?, ?, ?, ?, ?, ?)",
                    ("legacy-1", "BTCUSDT", "research", "1", 123.5, '{"score": 1.2}'),
                )
            before = hashlib.sha256(source.read_bytes()).hexdigest()
            with patch.dict(os.environ, {"TERMINAN_RESULTS_DB": str(source)}):
                self.assertEqual(research("BTCUSDT"), [{
                    "run_id": "legacy-1", "strategy": "research", "version": "1",
                    "created_at": 123.5, "metrics": {"score": 1.2},
                }])
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)
            with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as db:
                rows = list(db.execute("SELECT * FROM research_results ORDER BY run_id"))
            tables = {"research_results": rows}
            receipt = research_result_receipt(before, tables)
            target = Path(directory) / "archive.sqlite3"
            archive = ResearchArchive(PaperReplayLedger(target))
            self.assertEqual(archive.import_snapshot("legacy", tables, receipt), receipt)
            backup = Path(directory) / "backup.sqlite3"
            with closing(sqlite3.connect(target)) as db, closing(sqlite3.connect(backup)) as copy:
                db.backup(copy)
            restored = ResearchArchive(PaperReplayLedger(backup))
            self.assertEqual(list(restored.read_snapshot("legacy")),
                             [("research_results", "LEGACY_UNFENCED", rows[0])])
            self.assertEqual(restored.import_snapshot("legacy", tables, receipt), receipt)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)
            self.assertEqual(list(source.parent.glob(source.name + "*")), [source])

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
        for module in sorted(installed):
            with self.subTest(module=module):
                name = "grid" if module == "__init__" else f"grid.{module}"
                location = Path(importlib.import_module(name).__file__).resolve()
                self.assertEqual(
                    location, Path(distribution.locate_file(f"grid/{module}.py")).resolve(),
                )

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

    def test_math_poc_nearest_close_is_independent_of_decimal_precision(self):
        from market_profile_math import volume_profile_poc

        profile = {Decimal("10"): Decimal("1"), Decimal("11"): Decimal("1")}
        with localcontext() as context:
            context.prec = 5
            self.assertEqual(volume_profile_poc(profile, close=Decimal("10.500001")), Decimal("11"))

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
