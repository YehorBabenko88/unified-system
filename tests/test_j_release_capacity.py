"""J Round35 original deterministic capacity preflight; no installation."""
import hashlib
import unittest

from unified_system import j_release_capacity as cap, lab_release


class BudgetTests(unittest.TestCase):
    def test_exact_nested_parents_and_ancestors(self):
        m = {"files": {"a/b/c.py": {}, "a/d.py": {}},
             "directories": ["a", "a/b"]}
        r = cap.project_native_roster(m, install_ancestor_count=4)
        # 6 base + 4 install ancestors + 2 files + 2 directories + 2 parents.
        self.assertEqual(r["identity_count"], 16)
        self.assertTrue(r["admissible_by_conservative_preflight"])
        self.assertNotIn("actual_canonical_receipt_bytes", r)
    
    def test_512_boundary_not_guarantee_of_canonical_receipt(self):
        m = {"files": {f"leaf{i:04d}.py": {} for i in range(506)}, "directories": []}
        r = cap.project_native_roster(m, install_ancestor_count=0)
        self.assertEqual(r["identity_count"], 512)
        self.assertFalse(r["admissible_by_conservative_preflight"])
        self.assertEqual(r["max_canonical_receipt_bytes"], 60000)

    def test_513_entries_fail_closed(self):
        m = {"files": {f"leaf{i:04d}.py": {} for i in range(507)}, "directories": []}
        r = cap.project_native_roster(m, install_ancestor_count=0)
        self.assertEqual(r["identity_count"], 513)
        self.assertFalse(r["admissible_by_conservative_preflight"])

    def test_oversized_manifest_must_not_silently_truncate(self):
        m = {"files": {f"f{i:05d}.py": {} for i in range(1000)}, "directories": []}
        r = cap.project_native_roster(m, install_ancestor_count=4)
        self.assertEqual(r["identity_count"], 1010)
        self.assertFalse(r["admissible_by_conservative_preflight"])

    def test_invalid_or_unknown_ancestor_refused(self):
        m = {"files": {"good.py": {}}, "directories": []}
        for n in (-1, 65, None, True):
            with self.subTest(n=n), self.assertRaises(ValueError):
                cap.project_native_roster(m, install_ancestor_count=n)
        with self.assertRaises(ValueError):
            cap.project_native_roster({"files": {"../evil.py": {}}, "directories": []},
                                      install_ancestor_count=0)

    def test_manifest_requires_verified_sha_and_canonical_bytes(self):
        raw = b'{"schema":"unknown","files":{},"directories":{}}\n'
        with self.assertRaises(ValueError):
            cap.evaluate_manifest(raw, hashlib.sha256(raw).hexdigest(),
                                  install_ancestor_count=0)
        with self.assertRaises(ValueError):
            cap.evaluate_manifest(raw, "0" * 64, install_ancestor_count=0)

    def test_qualified_receipt_authority_never_granted(self):
        r = cap.project_native_roster({"files": {"one.py": {}}, "directories": []},
                                      install_ancestor_count=0)
        self.assertTrue(r["admissible_by_conservative_preflight"])
        self.assertNotIn("installer_authorized", r)
        self.assertNotIn("actual_canonical_receipt_bytes", r)


if __name__ == "__main__":
    unittest.main()
