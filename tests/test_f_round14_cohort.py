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
            "A": "5bcaed7d916d72837064da9ab938e28c35695624",
            "B": "20656417e61d26a294809cf649c37a37906b6dcf",
            "B_CUSTODY": "39a6cf4d8c039ca99bbfc00ca7cc2359bef5c60c",
            "C": "3bbd846dff646164903aeec2e2ef5cca7de1b9b0",
            "D": "4fd05211f10aa69108b598b0849abc842ec91899",
            "E": "d231a0ad657b7e12f89ddc9cde2ef6b5b028a125",
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


    def test_round16_snapshot_without_false_native_release(self):
        r = self.data["round16"]
        self.assertEqual(r["schema"], "unified.f.round16-executable-native-cohort.v1")
        self.assertEqual(r["release_status"], "NO_GO")
        self.assertIs(r["integration_admitted"], False)
        self.assertIs(r["protected_b30_runtime_unchanged"], True)
        self.assertEqual(r["sole_integrated_pr"]["head_sha"],
                         "9349d7f3ed93ef82d120976816b968e0b716b067")
        self.assertEqual(len(r["verified_source_blobs"]), 6)
        for item in r["verified_source_blobs"]:
            with self.subTest(path=item["path"]):
                self.assertRegex(item["blob"], SHA40)
                self.assertRegex(item["head"], SHA40)
        self.assertEqual({i["id"] for i in r["source_findings"]},
                         {"C_STOPPED_NULL", "C_RESOURCE_CUSTODY", "A_POSTMASTER_WITNESS",
                          "E_PROCESS_BIND", "E_OLD_MUTABLE", "B_NATIVE_ABI",
                          "NATIVE_PG18", "BUILD_SECURITY"})
        self.assertTrue(all(i["status"] == "OPEN" for i in r["source_findings"]))
        for key in ("installed_package", "wheel_sha256", "sdist_sha256",
                    "entrypoint", "sql_schema", "dependency_lock",
                    "postgres_e2e", "full_e2e"):
            self.assertEqual(r["qualification"][key], "NOT_VERIFIED")
        self.assertEqual(r["qualification"]["writer_abi"], "BLOCKED")
        self.assertEqual(r["ci_pr_first_page"]["D"], {"in_progress": 2})

    def test_round16_native_contract_exists_and_is_fail_closed(self):
        document = (ROOT / "round16-native-cohort-gates.md").read_text(encoding="utf-8")
        for required in ("STOPPED", "RetainedOsProcessWait", "RootProcessExtinction",
                         "RootBackendExtinction", "owner-thread", "content_id",
                         "wheel", "sdist", "Git", "NO_GO"):
            with self.subTest(required=required):
                self.assertIn(required, document)


    def test_round17_source_provenance_current_heads(self):
        r = self.data["round17"]
        self.assertEqual(r["schema"], "unified.f.round17-source-cohort.v1")
        self.assertIs(r["integration"]["runtime_changed"], False)
        self.assertEqual(r["integration"]["head_sha"], "9349d7f3ed93ef82d120976816b968e0b716b067")
        current = {row["id"]: row.get("head_sha") for row in self.data["components"]}
        for owner, pin in r["exact_heads"].items():
            with self.subTest(owner=owner):
                self.assertEqual(current[owner], pin)
        self.assertEqual(len(r["source_blobs"]), 7)
        for row in r["source_blobs"]:
            with self.subTest(path=row["path"]):
                self.assertRegex(row["blob"], SHA40)
                self.assertRegex(row["head"], SHA40)
        self.assertEqual(r["workflow_first_page"]["D"], {"success": 2})

    def test_round17_native_blockers_not_promoted(self):
        r = self.data["round17"]
        flags = r["source_capabilities"]
        self.assertEqual(flags["A_create_suspended"], "NOT_IMPLEMENTED")
        self.assertEqual(flags["A_complete_extinction"], "ALWAYS_DENIED")
        self.assertEqual(flags["C_cross_process_lock"], "NOT_IMPLEMENTED")
        self.assertEqual(flags["E_pg_dispatch"], "UNCONDITIONAL_DENY_LAB_ROOT_BOUND_EXTINCTION_NOT_IMPLEMENTED")
        self.assertEqual(flags["B_protected_writer_abi"], "NOT_IMPLEMENTED")
        self.assertEqual(r["release_evidence"]["native_pg18"], "NOT_VERIFIED")
        self.assertEqual(r["release_evidence"]["full_e2e"], "NOT_VERIFIED")
        self.assertEqual(len(r["blocking_gates"]), 7)
        self.assertEqual(self.data["release"]["code"], "NO_GO")
        self.assertEqual(self.data["release"]["production"], "NO_GO")

    def test_round17_gate_document_contains_current_pins(self):
        doc = (ROOT / "round16-native-cohort-gates.md").read_text(encoding="utf-8")
        for pin in (self.data["round17"]["exact_heads"]["A"],
                    self.data["round17"]["exact_heads"]["B"],
                    self.data["round17"]["exact_heads"]["C"],
                    self.data["round17"]["exact_heads"]["D"],
                    self.data["round17"]["exact_heads"]["E"]):
            with self.subTest(pin=pin):
                self.assertIn(pin, doc)
        self.assertIn("LAB_ROOT_BOUND_EXTINCTION_NOT_IMPLEMENTED", doc)
        self.assertIn("CODE NO_GO / PRODUCTION NO_GO", doc)

if __name__ == "__main__":
    unittest.main()
