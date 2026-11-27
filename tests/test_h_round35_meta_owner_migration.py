"""H/R35 executable 17-family Meta migration/no-delete ownership contract.

Original 85-file crosswalk must remain byte-identical; every source family has
a concrete owner, destination and acceptance requirements. This is a plan
guard, NOT a claim that all equivalent installed consumers exist today.
"""
from hashlib import sha1
import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "docs/functional-coverage/round35-meta-unique-migration-plan.json"
CROSSWALK = "docs/functional-coverage/meta-stage6-crosswalk-round33.json"
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def git_bytes(path):
    return subprocess.check_output(
        ["git", "-C", str(ROOT), "show", "HEAD:" + path])


class MetaMigrationOwnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
        original = git_bytes(CROSSWALK)
        cls.original = json.loads(original)
        actual = sha1(b"blob " + str(len(original)).encode("ascii") +
                      b"\0" + original).hexdigest()
        if actual != cls.plan["original_85_file_crosswalk_git_blob"]:
            raise AssertionError("META_CROSSWALK_IMMUTABLE_BLOB_MISMATCH")

    def test_full_17_unique_family_coverage_without_deduplication(self):
        p = self.plan
        self.assertEqual(p["schema"], "unified.h.meta-unique-migration-plan.v1")
        self.assertEqual(p["family_count"], 17)
        self.assertEqual(p["original_files_count"], 85)
        left = {f["id"]: f for f in self.original["features"]}
        right = {f["id"]: f for f in p["features"]}
        self.assertEqual(set(left), set(right))
        self.assertEqual(len(p["features"]), 17)
        for name, actual in right.items():
            with self.subTest(family=name):
                previous = left[name]
                self.assertEqual(previous["source_symbols"],
                                 actual["meta_source_symbols"])
                self.assertEqual(previous["known_consumers"],
                                 actual["original_known_consumers"])
                self.assertEqual(previous["unique_behavior"],
                                 actual["unique_behavior"])

    def test_every_owner_has_testable_exit_gate_and_retirement_is_denied(self):
        p = self.plan
        self.assertEqual(p["release"], "CODE_NO_GO_PRODUCTION_NO_GO")
        self.assertFalse(p["retirement_allowed"])
        self.assertFalse(p["original_same_input_parity_proven"])
        self.assertFalse(p["full_six_repo_inventory"])
        allowed = {"Grid", "Math", "Terminan", "Unified"}
        for feature in p["features"]:
            with self.subTest(feature=feature["id"]):
                self.assertFalse(feature["source_removal_allowed"])
                self.assertEqual(feature["full_original_same_input_parity"],
                                 "NOT_RUN")
                self.assertEqual(feature["external_consumer_cutover"], "NOT_PROVEN")
                self.assertEqual(feature["owner_acceptance"], "NOT_PROVEN")
                self.assertEqual(feature["rollback_and_original_data_preserved"],
                                 "NOT_PROVEN")
                self.assertTrue(feature["proposed_canonical_destination"])
                self.assertGreaterEqual(len(feature["observable_acceptance_checks"]), 3)
                self.assertTrue(any(o in feature["mandatory_owner"] for o in allowed)
                                or feature["id"] == "meta.stage6.17")

    def test_unique_paper_receipts_cannot_be_lost_or_automatically_deleted(self):
        rows = {x["path"]: x for x in self.plan["previously_unlisted_source_files"]}
        self.assertEqual(set(rows), {
            "src/meta_analyse/offline_paper_delivery.py",
            "src/meta_analyse/retirement_receipt.py",
        })
        self.assertEqual(rows["src/meta_analyse/offline_paper_delivery.py"]["blob"],
                         "a537ca2d8d7abad42c67fcc179854e140b4b81c8")
        self.assertEqual(rows["src/meta_analyse/retirement_receipt.py"]["blob"],
                         "daeb22df272ef8cd04cf45f3fe316cc01bcb9a47")
        for row in rows.values():
            self.assertRegex(row["blob"], HEX40)
            self.assertTrue(row["destination"])
            self.assertTrue(row["gate"])
        self.assertFalse(self.plan["retirement_allowed"])

    def test_available_original_partial_tests_exist_but_do_not_prove_cutover(self):
        p = self.plan
        available = [x for x in p["features"]
                     if x["original_runnable_partial_test"] is not None]
        self.assertEqual({x["id"] for x in available},
                         {"meta.stage6.03", "meta.stage6.04", "meta.stage6.08"})
        for item in available:
            self.assertTrue((ROOT / item["original_runnable_partial_test"]).is_file())
            self.assertEqual(item["current_partial_test_scope"],
                             "ORIGINAL_SOURCE_WRAPPER_ONLY_NOT_FULL_MIGRATION")
        for name, sha in p["current_candidates"].items():
            self.assertRegex(sha, HEX40)
        self.assertEqual(p["current_candidates"]["Grid_epoch"],
                         "eee29d8fae7c52d5b489a86a5a9ec08718265f18")
        self.assertEqual(p["current_candidates"]["Terminan_D"],
                         "fe4316d7c1580b9799903b57d8471034b5281996")


if __name__ == "__main__":
    unittest.main()
