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
                         "dfbfb657002275b7dd87cdcbb675014b7b3bf788")
        self.assertEqual(p["current_candidates"]["Terminan_D"],
                         "d71b29b194b40f32a2de8a4cfd0100041489fd94")


    def test_first_real_meta_wall_candidate_retained_until_owner_acceptance(self):
        migration = self.plan["first_concrete_migration"]
        self.assertEqual(migration["family_id"], "meta.stage6.07")
        self.assertEqual(migration["candidate_owner"], "Math")
        self.assertEqual(migration["candidate_head"],
                         "0c3a97aa3f76908c464298c345108bd355af4854")
        self.assertEqual(migration["original_blob"],
                         "faae6e3539c8b33e9d933fce4fd2a92b518c4ac5")
        self.assertEqual(migration["candidate_blob"],
                         "0e22810943294a8cf8163660b08b44a4cc54f9ed")
        self.assertEqual(migration["local_execution_scope"],
                         "EXACT_META_AND_MATH_WALL_CLASS_BYTES_WITH_CONTROLLED_WALL_NOTIONAL_STUB")
        self.assertEqual(migration["local_result"],
                         "8_PASS_0_FAIL_0_ERROR_0_SKIP")
        self.assertEqual(migration["github_original_e2e"], "NOT_RUN")
        self.assertEqual(migration["canonical_math_full_sdk_test"], "NOT_RUN")
        self.assertEqual(migration["original_consumer_cutover"], "NOT_PROVEN")
        self.assertFalse(migration["source_retirement_allowed"])
        row = next(x for x in self.plan["features"]
                   if x["id"] == migration["family_id"])
        self.assertEqual(row["first_subfeature_candidate"],
                         migration["candidate_file"])
        self.assertFalse(row["source_removal_allowed"])


if __name__ == "__main__":
    unittest.main()
