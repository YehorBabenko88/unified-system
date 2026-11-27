"""Binary/long-line historical Git scan tests; fake tokens only."""
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "tools" / "git_history_secret_triage.py"
spec = importlib.util.spec_from_file_location("git_history_secret_triage", MODULE)
scan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scan)


class HistoricalBlobSecretTriageTests(unittest.TestCase):
    def test_long_line_and_binary_across_boundaries(self):
        fake = b"gh" + b"p_" + b"z" * 25
        payload = b"x" * 3990 + b"\x00" + fake + b"\n" + b"q" * 100
        result = scan.scan_blocks([payload[:3980], payload[3980:4000], payload[4000:]])
        self.assertTrue(result["binary"])
        self.assertTrue(result["line_over_4000"])
        self.assertEqual(result["bytes"], len(payload))
        self.assertEqual(result["pattern_classes"], ["github_classic_token"])
        self.assertNotIn(fake.decode(), str(result))

    def test_short_multiblock_lines_are_not_misclassified(self):
        result = scan.scan_blocks([b"a" * 3000, b"b" * 900 + b"\n", b"c" * 3500])
        self.assertFalse(result["line_over_4000"])
        self.assertEqual(result["bytes"], 7401)

    def test_private_key_marker_across_buffer_boundary(self):
        marker = b"-" * 5 + b"BEGIN " + b"PRIVATE KEY" + b"-" * 5
        self.assertEqual(scan.scan_blocks([marker[:12], marker[12:]])["pattern_classes"],
                         ["private_key_pem"])

    def test_historical_git_blob_reports_classes_not_values(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            repo.mkdir()
            def git(*args):
                return subprocess.check_output(["git", "-C", str(repo), *args],
                                               stderr=subprocess.DEVNULL)
            git("init")
            git("config", "user.email", "test@example.invalid")
            git("config", "user.name", "Local Test")
            fake = b"gh" + b"p_" + b"a" * 30
            (repo / "sample.bin").write_bytes(b"\x00" + b"z" * 4099 + fake)
            git("add", ".")
            git("commit", "-m", "test blob")
            report = scan.scan_repository(repo)
            self.assertGreaterEqual(report["blobs_scanned"], 1)
            self.assertGreaterEqual(report["binary_blobs"], 1)
            self.assertGreaterEqual(report["long_line_blobs"], 1)
            self.assertTrue(any("github_classic_token" in item["classes"] for item in report["findings"]))
            self.assertNotIn(fake.decode(), json.dumps(report))

    def test_only_hex_git_ids_accepted(self):
        self.assertTrue(scan.exact_oid(b"f" * 40))
        self.assertTrue(scan.exact_oid(b"a" * 64))
        for value in (b"bad", b"g" * 40):
            self.assertFalse(scan.exact_oid(value))


if __name__ == "__main__":
    unittest.main()
