"""Structural and safety invariants for F's non-atomic Round-3 integration evidence."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "docs" / "git-consolidation"
SHA = re.compile(r"^[0-9a-f]{40}$")


class Round3IntegrationEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / "integration-manifest-round3.json").read_text(encoding="utf-8"))
        cls.dedup = json.loads((ROOT / "duplicate-count-reconciliation-round3.json").read_text(encoding="utf-8"))

    def test_every_owner_candidate_has_exact_version_and_source(self):
        rows = self.manifest["entries"]
        self.assertEqual({v["id"] for v in rows},
                         {"A", "B1", "B2", "C", "D1", "D2", "E", "F", "META_F"})
        self.assertEqual(len(rows), len({(v["repo"], v["pr"]) for v in rows}))
        for v in rows:
            with self.subTest(v=v["id"]):
                self.assertRegex(v["sha"], SHA)
                self.assertRegex(v["base"], SHA)
                self.assertNotEqual(v["sha"], v["base"])
                self.assertNotEqual(v["status"], "RELEASE_ACCEPTED")

    def test_readiness_fail_closed(self):
        gates = self.manifest["release"]
        self.assertEqual(gates["code"], "NO_GO")
        self.assertEqual(gates["production"], "NO_GO")
        self.assertIs(gates["real_trading_allowed"], False)
        self.assertIs(gates["paper_authorized_by_PARTIAL"], False)
        self.assertTrue(self.manifest["point_in_time_not_atomic"])
        self.assertTrue(all(item["code"] and item["fact"]
                            for item in self.manifest["blockers"]))

    def test_dedup_claims_do_not_authorize_retirement(self):
        d = self.dedup
        self.assertEqual(sum(x["claimed"] for x in d["category_claims"]), 174)
        self.assertEqual(d["claimed_total"] - d["category_claimed_sum"], 4)
        grid = d["grid_unified_detail"]
        self.assertEqual(sum(x["published_count"] for x in grid["families"]), 31)
        self.assertEqual(grid["claimed"] - grid["listed_family_sum"], 1)
        self.assertTrue(all(x["id"].startswith("GU-F") for x in grid["families"]))
        self.assertIs(d["no_deletion_authorized"], True)
        self.assertEqual(d["disposition"], "INVESTIGATION_REQUIRED")


if __name__ == "__main__":
    unittest.main()
