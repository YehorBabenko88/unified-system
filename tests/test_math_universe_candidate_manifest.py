"""Developer tests for the inert manifest contract (not qualification)."""
import copy
import json
from pathlib import Path
import unittest

from integration.math_universe.validate_candidate import validate_candidate

MANIFEST = Path(__file__).resolve().parents[1] / "integration/math_universe/candidate.v1.json"


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.value = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_shape(self):
        original = copy.deepcopy(self.value)
        self.assertIsNone(validate_candidate(self.value))
        self.assertEqual(self.value, original)

    def test_each_authority_flag(self):
        for key in ("independentQualification", "executionAuthority", "tradingAuthorized"):
            for invalid in (True, 0, None, "false"):
                with self.subTest(key=key, invalid=invalid):
                    value = copy.deepcopy(self.value)
                    value[key] = invalid
                    with self.assertRaises(ValueError):
                        validate_candidate(value)

    def test_duplicate_owner(self):
        self.value["repositories"][1]["owner"] = self.value["repositories"][0]["owner"]
        with self.assertRaises(ValueError):
            validate_candidate(self.value)

    def test_extra_fields(self):
        self.value["release"] = True
        with self.assertRaises(ValueError):
            validate_candidate(self.value)

    def test_bad_git_id(self):
        for invalid in ("main", "A" * 40, "a" * 39, "a" * 40 + "\n", 1):
            with self.subTest(invalid=invalid):
                value = copy.deepcopy(self.value)
                value["repositories"][0]["commit"] = invalid
                with self.assertRaises(ValueError):
                    validate_candidate(value)

    def test_missing_repository(self):
        self.value["repositories"].pop()
        with self.assertRaises(ValueError):
            validate_candidate(self.value)

    def test_release_schema_refused(self):
        self.value["schema"] = "unified.release.v4"
        with self.assertRaises(ValueError):
            validate_candidate(self.value)

    def test_unknown_owner(self):
        self.value["repositories"][0]["owner"] = "Other"
        with self.assertRaises(ValueError):
            validate_candidate(self.value)
