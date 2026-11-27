"""H/R35 immutable-source baseline: eight unique G SQLite dataset families.

Original Strattester modules are verified by Git SHA and imported only from
an isolated, read-only test checkout. Writes affect a disposable tmp database.
This is ORIGINAL SOURCE preservation, not Grid/Meta consumer cutover parity.
"""
from hashlib import sha1
import importlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
G = ROOT / ".source" / "strattester-g123"
HEAD = "fa9e0ff2235b35466a03c78781a80d42dbe1c4af"
FILES = {
    "strattester/marketdata/sqlite_store.py": "0c00d5c886c43f6cc938e6f3bf29c2964d8037bb",
    "strattester/marketdata/schema.py": "5b76e76f2f39db5d9a2bcfaa882b6c32db1de690",
    "strattester/marketdata/coverage.py": "106ac64ad39e16ec9be5c87e3cd802a15cad2fd9",
    "strattester/marketdata/storage_health.py": "45124edb092c4b8e16d59dd4a08154f284e0d6ea",
}
TABLES = ("candles", "mark_prices", "index_prices", "premium_index",
          "open_interest", "funding", "long_short_ratio",
          "public_trade_aggregates")


def verify_original_git_source():
    head = subprocess.check_output(
        ["git", "-C", str(G), "rev-parse", "HEAD"], text=True).strip()
    if head != HEAD:
        raise AssertionError("H_G35_HEAD_PIN_MISMATCH")
    for relative, expected in FILES.items():
        # Use canonical Git object bytes, not autocrlf-converted worktree bytes.
        raw = subprocess.check_output(
            ["git", "-C", str(G), "show", "HEAD:" + relative])
        oid = sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
        if oid != expected:
            raise AssertionError("H_G35_SOURCE_BLOB_MISMATCH:" + relative)


def snapshot(db):
    # Read-only SQLite URI, never use a user/installed PostgreSQL or DB.
    conn = sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)
    try:
        result = {
            name: conn.execute("SELECT * FROM " + name + " ORDER BY 1,2,3").fetchall()
            for name in TABLES
        }
        if conn.execute("PRAGMA quick_check").fetchone() != ("ok",):
            raise AssertionError("H_G35_SQLITE_INTEGRITY")
        return result
    finally:
        conn.close()


def seed(original, path):
    store = original.SQLiteMarketStore.open(path)
    try:
        assert store.upsert_candles([original.Candle(
            "BTCUSDT", "1m", 60000, 100, 101, 99, 100, 7, 700, True)]).accepted == 1
        for kind in ("mark_price", "index_price", "premium_index"):
            ohlc = ["60000", "100", "101", "99", "100"] if kind != "premium_index" else [
                "60000", "0.01", "0.02", "0.00", "0.01"]
            assert store.upsert_price_klines(kind, "BTCUSDT", [ohlc]).accepted == 1
        assert store.upsert_open_interest("BTCUSDT", [
            {"timestamp": "300000", "openInterest": "123.4"}]).accepted == 1
        assert store.upsert_funding("BTCUSDT", [
            {"fundingRateTimestamp": "60000", "fundingRate": "0.0001"}]).accepted == 1
        assert store.upsert_long_short_ratio("BTCUSDT", [
            {"timestamp": "300000", "buyRatio": "0.55", "sellRatio": "0.45"}]).accepted == 1
        assert store.upsert_public_trade_aggregates("BTCUSDT", [
            {"open_time": 60000, "buy_volume": 3, "sell_volume": 2,
             "turnover": 500, "trade_count": 5, "vwap": 100,
             "max_trade": 2}]).accepted == 1
    finally:
        store.close()


class HOriginalG35EightDatasetPreservation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        verify_original_git_source()
        # Imported ONLY after immutable Git SHA verification, in test runtime.
        sys.path.insert(0, str(G))
        cls.original = importlib.import_module("strattester.marketdata.sqlite_store")

    def test_eight_unique_original_datasets_survive_close_reopen(self):
        with tempfile.TemporaryDirectory(prefix="h_g35_disposable_") as tmp:
            db = Path(tmp) / "h-original-data.sqlite3"
            seed(self.original, db)
            original_rows = snapshot(db)
            self.assertEqual(set(original_rows), set(TABLES))
            self.assertTrue(all(len(rows) == 1 for rows in original_rows.values()))
            reopened = self.original.SQLiteMarketStore.open(db)
            self.assertTrue(reopened.integrity_check())
            reopened.close()
            self.assertEqual(snapshot(db), original_rows)

    def test_all_unique_datasets_block_retirement_without_grid_parity(self):
        ledger = json.loads((ROOT / "docs" / "functional-coverage"
            / "round35-market-dataset-parity-gates.json").read_text())
        by_id = {item["id"]: item for item in ledger["datasets"]}
        for label in ("ohlcv", "mark", "index", "premium", "oi",
                      "funding", "long_short", "trades"):
            with self.subTest(label=label):
                row = by_id[label]
                self.assertFalse(row["same_input_parity_proven"])
                self.assertFalse(row["consumer_cutover_proven"])
                self.assertFalse(row["retirement_allowed"])
        self.assertFalse(ledger["global_retirement_allowed"])


if __name__ == "__main__":
    unittest.main()
