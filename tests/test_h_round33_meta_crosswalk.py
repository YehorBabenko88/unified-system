"""H ROUND33 source-pinned Meta migration inventory guards (offline, no imports).

The file is a historical source tree crosswalk, not a functional runtime pass.
It forbids deleting source files with unresolved ownership / consumer parity.
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "functional-coverage" / "meta-stage6-crosswalk-round33.json"
SHA = re.compile(r"\A[0-9a-f]{40}\Z")
DIFFERENT = frozenset({
    "src/meta_analyse/core.py",
    "src/meta_analyse/footprint.py",
    "src/meta_analyse/liquidity.py",
    "src/meta_analyse/orderflow_aggregation.py",
    "src/meta_analyse/orderflow_metrics.py",
    "src/meta_analyse/runtime.py",
    "src/meta_analyse/tape_velocity.py",
    "src/meta_analyse/wall_tracker.py",
})
UNLISTED = frozenset({
    "src/meta_analyse/offline_paper_delivery.py",
    "src/meta_analyse/retirement_receipt.py",
})


def read():
    raw = SOURCE.read_bytes()
    if not 10000 <= len(raw) <= 131072:
        raise ValueError("Meta preservation inventory outside bounded source size")
    return json.loads(raw)


class MetaStage6CrosswalkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = read()

    def test_meta_snapshot_is_source_only_no_release(self):
        d = self.data
        self.assertEqual(d["schema"],
                         "unified.h.meta-original-preservation-crosswalk.v1")
        self.assertEqual(d["status"],
                         "SOURCE_DIFF_CAPTURED_NOT_RETIREMENT_PROOF")
        self.assertEqual(d["release"], "CODE_NO_GO_PRODUCTION_NO_GO")
        self.assertFalse(d["deletion_allowed"])
        self.assertFalse(d["summary"]["full_symbol_coverage_proven"])

    def test_exact_original_source_pins_and_tree_completeness(self):
        s = self.data["summary"]
        self.assertEqual(s["snapshot_ref"],
                         "b1a4d6a41054f0040a88dc80b585380fb6b4f323")
        self.assertEqual(s["older_csv_source_blob"],
                         "31a1387707f7b88d22d9c8a2b2fde84e77cdc7d8")
        self.assertEqual(s["older_feature_source_blob"],
                         "56c239415eae9ee0445e624431140de188d59faf")
        for key in ("snapshot_ref", "older_csv_source_blob",
                    "older_feature_source_blob"):
            self.assertRegex(s[key], SHA)
        self.assertIs(s["source_tree_truncated"], False)

    def test_exact_85_meta_files_with_83_old_entries(self):
        s = self.data["summary"]
        files = self.data["files"]
        self.assertEqual(len(files), 85)
        self.assertEqual(s["csv_file_rows"], 83)
        self.assertEqual(s["current_source_python_files"], 85)
        self.assertEqual(s["match"], 75)
        self.assertEqual(s["changed"], 8)
        self.assertEqual(s["unlisted"], 2)
        self.assertEqual(s["missing"], 0)
        paths = [item["path"] for item in files]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertTrue(all(path.startswith("src/meta_analyse/")
                            and path.endswith(".py") for path in paths))

    def test_exact_git_blob_drift_and_old_source_custody(self):
        files = self.data["files"]
        changed = {x["path"] for x in files
                   if x["blob_status"] == "CHANGED_SINCE_INVENTORY"}
        added = {x["path"] for x in files
                 if x["blob_status"] == "UNLISTED_IN_OLD_INVENTORY"}
        self.assertEqual(changed, DIFFERENT)
        self.assertEqual(added, UNLISTED)
        for item in files:
            self.assertRegex(item["actual_head_blob"], SHA)
            if item["blob_status"] == "CHANGED_SINCE_INVENTORY":
                self.assertRegex(item["inventory_blob"], SHA)
                self.assertNotEqual(item["inventory_blob"],
                                    item["actual_head_blob"])
            if item["blob_status"] == "UNLISTED_IN_OLD_INVENTORY":
                self.assertIsNone(item["inventory_blob"])

    def test_all_unique_features_have_owner_consumer_and_hold(self):
        d = self.data
        self.assertEqual(len(d["features"]), 17)
        self.assertEqual(d["summary"]["family_rows"], 17)
        self.assertEqual(len({f["id"] for f in d["features"]}), 17)
        for feature in d["features"]:
            for k in ("source_symbols", "owner_candidate", "unique_behavior",
                      "known_consumers", "retirement_conditions"):
                self.assertTrue(feature[k].strip())
            self.assertEqual(feature["migration_status"],
                             "NOT_INDEPENDENTLY_ACCEPTED")
            self.assertEqual(feature["exact_original_test_status"],
                             "NOT_RUN_IN_H")
            self.assertFalse(feature["removal_allowed"])

    def test_no_meta_file_has_unverified_delete_authority(self):
        for row in self.data["files"]:
            self.assertFalse(row["consumers_checked"])
            self.assertFalse(row["original_tests_confirmed"])
            self.assertFalse(row["same_input_parity_confirmed"])
            self.assertFalse(row["removal_allowed"])
            self.assertIn("OWNER_ACK", row["retirement_conditions"])
            self.assertIn("ROLLBACK", row["retirement_conditions"])

    def test_canonical_four_owner_handoff_without_retirement(self):
        actions = self.data["cross_owner_actions"]
        self.assertEqual(set(actions),
                         {"Grid", "Math", "Terminan", "Unified", "H", "G", "J"})
        for message in actions.values():
            self.assertTrue(message.strip())
        self.assertIn("two newly unlisted files", actions["H"])
        self.assertIn("No Meta code removal", actions["G"])


if __name__ == "__main__":
    unittest.main()
