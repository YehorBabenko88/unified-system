"""Frozen A3 V3 claims are compatibility vectors, never actual commit evidence."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from unified_system.storage.contracts import StorageBlocked, decode_untrusted_claim, require_publication_authority
from unified_system.storage.segments import verify_segment_bytes
from .test_segments import ROW, claim

FIXTURES = Path(__file__).parent / "fixtures" / "checkpoint_v3"


class CheckpointVectorTests(unittest.TestCase):
    def test_exact_owner_schema_and_mapping_snapshots_are_bound(self):
        expected = {"schema.json": "4de720d9391e5a89c0577b5298c283e742fbfe490c4454c184e31c2348589ea4",
                    "producer-mapping-review4.json": "570437ac72c718b46d620db04e58b768dc962db34df856cc7ad25313462ac539"}
        for name, digest in expected.items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((FIXTURES/name).read_bytes()).hexdigest(), digest)

    def test_confirmed_unknown_time_is_still_only_an_untrusted_claim(self):
        raw = (FIXTURES/"confirmed-unknown-time.canonical.json").read_bytes()
        parsed = decode_untrusted_claim(raw)
        self.assertEqual(parsed.value["commit_status"], "COMMITTED")
        self.assertIsNone(parsed.value["publication_content"]["committed_at_utc"])
        self.assertEqual(parsed.value["publication_content"]["commit_time_status"], "UNKNOWN_COMMIT_INSTANT")
        self.assertFalse(parsed.authority_verified)
        with self.assertRaisesRegex(StorageBlocked, "PROOF_ADAPTER_UNAVAILABLE"):
            require_publication_authority(parsed)

    def test_observation_does_not_rewrite_content_or_enable_effect(self):
        values = [decode_untrusted_claim((FIXTURES/name).read_bytes()) for name in
                  ("confirmed-observed.canonical.json", "confirmed-unknown-time.canonical.json")]
        self.assertEqual(values[0].value["publication_content"], values[1].value["publication_content"])
        self.assertNotEqual(values[0].value["confirmed_observed_at_utc"], values[1].value["confirmed_observed_at_utc"])
        for value in values:
            with self.assertRaises(StorageBlocked):
                require_publication_authority(value)

    def test_unconfirmed_and_counterfeit_evidence_cannot_promote(self):
        value = decode_untrusted_claim((FIXTURES/"unconfirmed.canonical.json").read_bytes())
        self.assertEqual(value.value["commit_status"], "COMMIT_UNCONFIRMED")
        self.assertNotIn("publication_evidence", value.value)
        with self.assertRaises(StorageBlocked):
            require_publication_authority(value)
        forged = value.value
        forged.update(commit_status="COMMITTED", proof_verified=True)
        parsed = decode_untrusted_claim(json.dumps(forged, sort_keys=True, separators=(",", ":")).encode())
        with self.assertRaises(StorageBlocked):
            require_publication_authority(parsed)

    def test_disposable_file_corruption_is_checked_by_real_bytes(self):
        with tempfile.TemporaryDirectory(prefix="storage-stage1-test-") as directory:
            path = Path(directory)/"segment.fixture"
            path.write_bytes(ROW)
            self.assertFalse(verify_segment_bytes(path.read_bytes(), claim()).authority_verified)
            path.write_bytes(ROW[:-5])
            with self.assertRaises(StorageBlocked):
                verify_segment_bytes(path.read_bytes(), claim())
