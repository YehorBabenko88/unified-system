"""H ROUND26 inert capability ledger regression checks.

No provider, process, trading, DB, socket, wallet or service side effects.
Source inventory is evidence metadata, never a readiness grant.
"""
from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs" / "functional-coverage" / "capability-ledger.v1.json"
EXPECTED = frozenset({
    "instrument_registry", "historical_ohlcv_1m", "timeframes_multi",
    "historical_trades", "live_trades", "volumes", "delta", "footprint",
    "poc", "open_interest", "funding", "orderbook_live", "orderbook_history",
    "volatility", "market_cap", "instrument_filters", "historical_archives",
    "download_progress", "history_completeness", "gap_detection",
    "provenance", "mathematics", "strategies", "backtesting",
    "paper_simulation", "analytics", "charts_ui",
})
OWNERS = {"Grid", "Math", "Terminan", "Grid+Math", "Grid+Terminan",
          "Math+Terminan", "Grid+Math+Terminan", "Grid+Unified",
          "Terminan+Math"}
STATUS = {"SOURCE_PRESENT", "CANDIDATE_MIGRATED", "PARTIAL_CONSUMER",
          "NOT_INDEPENDENTLY_VERIFIED", "UNKNOWN_SOURCE", "NOT_IMPLEMENTED"}


def load():
    raw = LEDGER.read_bytes()
    if len(raw) > 131072:
        raise ValueError("ledger size bound")
    return json.loads(raw)


class FunctionalCoverageLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = load()

    def test_exact_capability_roster(self):
        capabilities = self.ledger["capabilities"]
        ids = [row["id"] for row in capabilities]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), EXPECTED)

    def test_immutable_source_pins_and_schema(self):
        self.assertEqual(self.ledger["schema"], "unified.functional-capability-ledger.v1")
        self.assertEqual(set(self.ledger["pins"]),
                         {"Grid", "Math", "Terminan", "Strattester", "MetaAnalyse"})
        import re
        for sha in self.ledger["pins"].values():
            self.assertRegex(sha, r"\A[0-9a-f]{40}\Z")

    def test_no_unqualified_ready_or_implicit_test_pass(self):
        self.assertEqual(self.ledger["release"], "CODE_NO_GO_PRODUCTION_NO_GO")
        for item in self.ledger["capabilities"]:
            self.assertEqual(set(item),
                             {"id", "origin", "implementation", "owner",
                              "contract", "status", "tests", "missing"})
            self.assertIn(item["status"], STATUS)
            self.assertIn(item["owner"], OWNERS)
            self.assertEqual(item["tests"], "NOT_RUN_EXACT_PIN")
            for key in ("origin", "implementation", "contract", "missing"):
                self.assertIs(type(item[key]), str)
                self.assertTrue(item[key].strip())

    def test_unverified_source_cannot_claim_market_cap(self):
        item = next(x for x in self.ledger["capabilities"]
                    if x["id"] == "market_cap")
        self.assertEqual(item["status"], "UNKNOWN_SOURCE")
        self.assertEqual(item["contract"], "NOT_SPECIFIED")

    def test_completeness_and_native_admission_not_attested(self):
        for key in ("history_completeness", "provenance",
                    "historical_ohlcv_1m", "charts_ui", "open_interest"):
            item = next(x for x in self.ledger["capabilities"] if x["id"] == key)
            self.assertNotEqual(item["status"], "READY")
            self.assertEqual(item["tests"], "NOT_RUN_EXACT_PIN")
        handoffs = self.ledger["cross_owner_acceptance"]
        self.assertIn("no second Bybit client", handoffs["prohibitions"])
        self.assertIn("no second canonical raw writer", handoffs["prohibitions"])
        self.assertIn("no historical source fabrication", handoffs["prohibitions"])


if __name__ == "__main__":
    unittest.main()
