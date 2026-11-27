"""H R33 executable source-pinned retirement-gate tests. Offline and inert.

No provider import, network, database, installed-system or production admission.
Original Strattester functions are separately executed from pristine, named
source blocks (read from GitHub immutable blobs) in independent source probes.
"""
import json
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
GATE = HERE / "docs" / "functional-coverage" / "round33-retirement-gates.json"
SHA = re.compile(r"\A[0-9a-f]{40}\Z")


def gate():
    payload = GATE.read_bytes()
    if len(payload) > 65536:
        raise ValueError("unbounded gate")
    return json.loads(payload)


class HRound33RetirementGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = gate()

    def test_schema_no_release_and_all_original_pins(self):
        d = self.data
        self.assertEqual(d["schema"], "unified.functional-retirement-gate.v1")
        self.assertEqual(d["owner"], "H")
        self.assertEqual(d["release"], "CODE_NO_GO_PRODUCTION_NO_GO")
        for field in ("ancestry", "source_blobs"):
            self.assertTrue(d[field])
            for name, value in d[field].items():
                with self.subTest(field=field, name=name):
                    self.assertRegex(value, SHA)
        self.assertEqual(d["ancestry"]["h_root"],
                         "d47ef9e06b381f41108cff16016e133677b9697e")

    def test_inventory_is_not_six_repository_complete(self):
        inv = self.data["inventory_scope"]
        self.assertEqual(inv["original_h_ledger_families"], 27)
        self.assertEqual(inv["meta_inventory_feature_families"], 17)
        self.assertEqual(inv["meta_inventory_python_file_rows"], 83)
        self.assertTrue(inv["overlap_not_additive"])
        self.assertFalse(inv["full_six_repo_symbol_inventory_verified"])

    def test_g006_hard_denial_contains_required_unique_sources(self):
        g = next(g for g in self.data["groups"] if g["id"] == "G006")
        self.assertFalse(g["retirement_allowed"])
        self.assertIn("SQLiteMarketStore", g["unique_retained"])
        self.assertIn("SyncEngine", g["unique_retained"])
        self.assertIn("OI", g["unique_retained"])
        self.assertIn("funding", g["unique_retained"])
        self.assertTrue(any("Decimal turnover underflow" in x
                            for x in g["required_tests"]))
        self.assertTrue(any("equal-size universe replacement" in x
                            for x in g["required_tests"]))
        self.assertIn("strattester/marketdata/universe_sync.py",
                      g["original_paths"])

    def test_g012_refuses_unqualified_browser_fallback(self):
        g = next(g for g in self.data["groups"] if g["id"] == "G012")
        self.assertFalse(g["retirement_allowed"])
        self.assertIn("exact Decimal", g["unique_retained"])
        self.assertTrue(any("Chromium" in x for x in g["required_tests"]))
        self.assertTrue(any("no-lookahead" in x for x in g["required_tests"]))

    def test_meta_source_inventory_is_used_but_not_complete(self):
        g = next(g for g in self.data["groups"] if g["id"] == "META_STAGE6")
        self.assertFalse(g["retirement_allowed"])
        self.assertIn("tape velocity and wall tracking", g["unique_retained"])
        self.assertIn("MetaScalp foreign-level ownership", g["unique_retained"])
        self.assertIn("paper PnL fees stops and guards", g["unique_retained"])
        self.assertIn("docs/meta-stage6-feature-migration.csv",
                      g["original_paths"])

    def test_prior_ci_cannot_be_promoted_to_latest_heads(self):
        ev = self.data["evidence"]
        st = ev["original_strattester_ci_prior_head"]
        self.assertEqual(st["passed"], 2154)
        self.assertEqual(st["skipped"], 2)
        self.assertFalse(st["applies_to_current_head"])
        self.assertEqual(ev["current_strattester_ci"],
                         "NOT_RUN_VERIFIED_AT_EXACT_HEAD")
        self.assertEqual(ev["original_terminan_http"]["passed"], 72)
        self.assertEqual(ev["original_terminan_browser_prior"]["failed"], 1)
        self.assertEqual(ev["current_terminan_d135_browser_ci"],
                         "NOT_RUN_VERIFIED_AT_EXACT_HEAD")
        self.assertEqual(ev["native_installed_e2e"], "NOT_RUN")

    def test_release_and_deletion_gates_are_all_blocked(self):
        d = self.data["global_deletion_gate"]
        for field in ("owner_ack", "complete_original_symbol_inventory",
                      "dynamic_external_consumers_checked",
                      "same_input_differential_parity",
                      "exact_head_automated_ci_complete",
                      "installed_native_browser_e2e",
                      "user_data_backup_restore_proven",
                      "reversible_rollback_tested", "deletion_allowed"):
            with self.subTest(field=field):
                self.assertIs(d[field], False)
        self.assertTrue(d["original_git_blobs_preserved"])
        self.assertEqual(len(self.data["groups"]), 3)


if __name__ == "__main__":
    unittest.main()
