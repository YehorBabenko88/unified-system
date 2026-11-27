"""H R35: bounded cross-owner retirement contract for unique market datasets.

This is a preservation guard, not a claim that parity or provider completeness
has been proved. Zero external imports, network, DB or side effects.
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "docs" / "functional-coverage" / "round35-market-dataset-parity-gates.json"


def load():
    raw = FILE.read_bytes()
    if not 1024 <= len(raw) <= 32768:
        raise ValueError("bounded market parity manifest")
    return json.loads(raw)


class HMarketDatasetParityGates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load()

    def test_exact_dataset_matrix_with_no_unproved_release(self):
        d = self.data
        self.assertEqual(d["schema"], "unified.h.market-dataset-retention-gates.v1")
        self.assertEqual(d["release"], "CODE_NO_GO_PRODUCTION_NO_GO")
        self.assertFalse(d["global_retirement_allowed"])
        required = {"ohlcv", "trades", "ticks", "delta", "oi", "funding",
                    "mark", "index", "premium", "long_short", "archives"}
        self.assertEqual({x["id"] for x in d["datasets"]}, required)

    def test_all_datasets_have_owner_and_original_equivalence_gates(self):
        for d in self.data["datasets"]:
            with self.subTest(dataset=d["id"]):
                self.assertIn(d["candidate_owner"], ("Grid", "Grid+Math"))
                self.assertTrue(d["original_retained"])
                self.assertFalse(d["same_input_parity_proven"])
                self.assertFalse(d["source_completeness_proven"])
                self.assertFalse(d["consumer_cutover_proven"])
                self.assertFalse(d["retirement_allowed"])
                self.assertTrue(d["original_source"])
                self.assertTrue(d["acceptance_command"])
                self.assertEqual(d["acceptance_status"], "NOT_RUN")

    def test_data_loss_controls_are_separate_from_ohlcv_aggregation(self):
        entries = {x["id"]: x for x in self.data["datasets"]}
        for k in ("oi", "funding", "mark", "index", "premium", "archives"):
            with self.subTest(dataset=k):
                self.assertNotEqual(entries[k]["original_source"], "G012")
                self.assertIn("source lineage", entries[k]["acceptance_checks"])
                self.assertIn("gap and ordering", entries[k]["acceptance_checks"])
        self.assertIn("SHA256 archive integrity", entries["archives"]["acceptance_checks"])
        self.assertIn("checkpoint/resume", entries["archives"]["acceptance_checks"])
        self.assertIn("no fabricated delisting", entries["oi"]["acceptance_checks"])

    def test_g012_and_meta_retain_independent_no_delete_gates(self):
        self.assertEqual(self.data["g012_original_legacy"], "D129_68_LINE")
        self.assertFalse(self.data["g012_retirement_allowed"])
        self.assertFalse(self.data["meta_85_file_retirement_allowed"])
        self.assertEqual(self.data["meta_source_file_count"], 85)


if __name__ == "__main__":
    unittest.main()
