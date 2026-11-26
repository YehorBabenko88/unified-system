"""Fail-closed structural checks for F Round14 source-qualification cohort.

This test does NOT execute PostgreSQL, inspect installed wheels, or mint Root grants.
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "docs" / "git-consolidation"
SHA40 = re.compile(r"^[0-9a-f]{40}$")

EXPECTED = {
    "grid/canonical_lab_fenced_writer.py": ("8b93466a79fa234468a3cdc44106bd5e153e81c4", 8543),
    "grid/canonical_lab_continuous_collector.py": ("52ed338cb5e1e5641fd9cf9f401b280fc3500a9b", 19554),
    "grid/c_lab_journal_adapter.py": ("ab93c6d421c3d3f0232060f6ded7ac01bf8eeda0", 6613),
    "grid/c_async_fenced_writer.py": ("98ed95029785413eb8fbc5687af39ff6bd0bf2cf", 2273),
}


class Round14CohortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "round14-cohort.json").read_text(encoding="utf-8"))

    def test_source_cohort_exact_four_bytes(self):
        rows = self.data["exact_b30_source_files"]
        self.assertEqual(len(rows), 4)
        self.assertEqual(set(v["path"] for v in rows), set(EXPECTED))
        for item in rows:
            with self.subTest(item=item["path"]):
                self.assertEqual((item["git_blob"], item["size_bytes"]), EXPECTED[item["path"]])

    def test_complete_component_head_registry(self):
        comps = self.data["components"]
        self.assertEqual({v["id"] for v in comps},
                         {"A", "B", "B_CUSTODY", "C", "D", "E", "F", "MATH", "META"})
        self.assertEqual(len(comps), len({v["id"] for v in comps}))
        for item in comps:
            pin = item.get("head_sha", item.get("head_sha_at_source_snapshot"))
            self.assertRegex(pin, SHA40)

    def test_release_denies_unqualified_runtime(self):
        self.assertEqual(self.data["release"]["code"], "NO_GO")
        self.assertEqual(self.data["release"]["production"], "NO_GO")
        self.assertIs(self.data["release"]["real_trading"], False)
        self.assertEqual(self.data["release"]["native_recovery"], "NOT_VERIFIED")
        self.assertEqual(self.data["release"]["full_system_e2e"], "NOT_VERIFIED")
        self.assertTrue(self.data["integration"]["immutable_until_master_authorizes"])
        self.assertIs(self.data["integration"]["new_runtime_included"], False)
        self.assertEqual(self.data["integration"]["head_sha"],
                         "9349d7f3ed93ef82d120976816b968e0b716b067")

    def test_no_false_package_or_native_attestation(self):
        a = self.data["build_provenance"]
        for key in ("wheel_sha256", "sdist_sha256", "installed_file_sha256",
                    "installed_imports", "runtime_entrypoint", "cross_os_dependency_lock"):
            self.assertIn("NOT_", a[key])
        self.assertEqual(self.data["published_checks"]["artifact_and_runtime"], "NOT_VERIFIED")
        self.assertEqual(self.data["published_checks"]["new_round14_tests"], "NOT_VERIFIED_ON_GITHUB_RUNNER")
        self.assertEqual({v["id"] for v in self.data["gates"]},
                         {"PROCESS_EXTINCTION", "BACKEND_EXTINCTION", "WRITER_ABI",
                          "JOURNAL_RECOVERY", "BUILD_INSTALL", "SECURITY", "DEDUPE",
                          "FULL_NATIVE"})
        self.assertTrue(all(v["status"] == "BLOCKED" for v in self.data["gates"]))

    def test_cross_owner_singletons_not_silently_removed(self):
        required = {"second supervisor", "second Bybit client", "second SQL writer",
                    "second PaperEngine", "second PostgreSQL owner", "second process observer"}
        self.assertEqual(set(self.data["prohibited_duplicates"]), required)

    def test_source_qualifications_have_pinned_blobs(self):
        self.assertEqual(len(self.data["source_qualifications"]), 4)
        for row in self.data["source_qualifications"]:
            with self.subTest(row=row["path"]):
                self.assertRegex(row["git_blob"], SHA40)
                self.assertRegex(row["commit"], SHA40)
                self.assertTrue(row["owner"] in ("A", "C", "E"))


    def test_round15_exact_pins_and_frozen_runtime_sha256(self):
        expected_heads = {
            "A": "f2a0245ae9edc2805e1e9be28e6c3a649ec401b4",
            "B": "2e5227e79023091a7481b540536f50a6b2e125fb",
            "B_CUSTODY": "39a6cf4d8c039ca99bbfc00ca7cc2359bef5c60c",
            "C": "bbdc4e87b64a2516528270eb0c7925ce97d24ee5",
            "D": "80da873c5251a0505519249325a4591f8bb003d9",
            "E": "c6bfff7e30d6b68bd23107edf3a9bf4098a00004",
            "META": "902db7e28571e851de09d127a9ebad6f120efecd",
        }
        rows = {row["id"]: row for row in self.data["components"]}
        for label, sha in expected_heads.items():
            with self.subTest(component=label):
                self.assertEqual(rows[label]["head_sha"], sha)
        hashes = self.data["round15"]["b30_source_sha256"]
        self.assertEqual(set(hashes), set(EXPECTED))
        for path, sha in hashes.items():
            with self.subTest(path=path):
                self.assertRegex(sha, re.compile(r"^[0-9a-f]{64}$"))
        self.assertTrue(self.data["round15"]["b30_frozen_runtime_verified_against_b_round14_test"])

    def test_round15_no_p0_release_promotion(self):
        r = self.data["round15"]
        self.assertIs(r["sole_integration_unchanged"], True)
        self.assertIs(r["source_only"], True)
        self.assertEqual(len(r["p0_defects"]), 4)
        self.assertEqual(r["native_recovery"], "NOT_VERIFIED")
        self.assertEqual(r["writer_abi"], "BLOCKED")
        self.assertEqual(r["wheel_sdist"], "NOT_VERIFIED")
        self.assertEqual(r["dedup_retirement"], "NOT_AUTHORIZED")
        self.assertEqual(r["ci_first_page"]["D"], {"success": 1, "queued": 1})

if __name__ == "__main__":
    unittest.main()
