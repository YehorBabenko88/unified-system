"""Bounded offline audit tests: no remote access and no imported project code."""
import json
from pathlib import Path
import tempfile
import unittest

from security_audit.offline_inventory import scan, git_blob_oid


class OfflineAuditTests(unittest.TestCase):
    def test_git_blob_oid_matches_git_known_example(self):
        self.assertEqual("ce013625030ba8dba906f756967f9e9ca394464a",
                         git_blob_oid(b"hello\n"))

    def test_exact_cross_repo_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "math", Path(tmp) / "bybit-cluster-grid"
            (a / "python").mkdir(parents=True)
            (b / "grid").mkdir(parents=True)
            (a / "python" / "kernel.py").write_bytes(b"def x(): return 2\n")
            (b / "grid" / "kernel.py").write_bytes(b"def x(): return 2\n")
            result = scan({"math": a, "bybit-cluster-grid": b})
            dups = result["exact_cross_repo_code_duplicates"]
            self.assertEqual(1, len(dups))
            self.assertEqual(2, len(dups[0]["occurrences"]))
            self.assertEqual(0, result["automatic_removals"])

    def test_different_bytes_not_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "math", Path(tmp) / "bybit-cluster-grid"
            a.mkdir()
            b.mkdir()
            (a / "x.py").write_bytes(b"a=1\n")
            (b / "x.py").write_bytes(b"a=2\n")
            self.assertEqual([], scan({"math": a, "bybit-cluster-grid": b})[
                "exact_cross_repo_code_duplicates"])

    def test_unpinned_and_permissions_flagged_without_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "strattester"
            wf = repo / ".github" / "workflows"
            wf.mkdir(parents=True)
            (wf / "test.yml").write_text(
                "name: insecure\non: [pull_request]\njobs:\n  test:\n"
                "    steps:\n      - uses: actions/checkout@v4\n", encoding="utf-8")
            result = scan({"strattester": repo})
            rules = {f["rule"] for f in result["review_findings"]}
            self.assertIn("ACTION_UNPINNED", rules)
            self.assertIn("TOKEN_PERMISSIONS_UNDECLARED", rules)
            self.assertEqual("NOT_ESTABLISHED", result["security_clearance"])

    def test_json_workflow_uses_and_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "strattester"
            wf = repo / ".github" / "workflows"
            wf.mkdir(parents=True)
            object_form = {
                "name": "JSON workflow",
                "on": {"pull_request": {}},
                "permissions": {"contents": "read"},
                "jobs": {"test": {"steps": [{"uses": "actions/checkout@" + "a"*40}]}}
            }
            (wf / "test.yml").write_text(json.dumps(object_form), encoding="utf-8")
            result = scan({"strattester": repo})
            rules = {f["rule"] for f in result["review_findings"]}
            self.assertNotIn("TOKEN_PERMISSIONS_UNDECLARED", rules)
            self.assertNotIn("ACTION_UNPINNED", rules)

    def test_pinned_workflow_unchallenged_by_two_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "strattester"
            wf = repo / ".github" / "workflows"
            wf.mkdir(parents=True)
            (wf / "test.yml").write_text(
                "permissions:\n  contents: read\njobs:\n  test:\n"
                "    steps:\n      - uses: actions/checkout@"
                + "a"*40 + "\n", encoding="utf-8")
            result = scan({"strattester": repo})
            rules = {f["rule"] for f in result["review_findings"]}
            self.assertNotIn("ACTION_UNPINNED", rules)
            self.assertNotIn("TOKEN_PERMISSIONS_UNDECLARED", rules)

    def test_secret_shape_reports_no_sensitive_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "math"
            repo.mkdir()
            secret = "ghp_" + "Z" * 36
            (repo / "example.py").write_text("token=" + repr(secret), encoding="utf-8")
            result = scan({"math": repo})
            report = json.dumps(result)
            self.assertIn("GITHUB_CLASSIC_TOKEN_SHAPE", report)
            self.assertNotIn(secret, report)

    def test_symlink_outside_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "math"
            root.mkdir()
            other = Path(tmp) / "outside.py"
            other.write_text("token='do-not-read'")
            try:
                (root / "link.py").symlink_to(other)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation unavailable")
            result = scan({"math": root})
            self.assertEqual(0, result["observed_files"]["math"]["files_examined"])

    def test_meta_analyse_supported_and_redacted(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "meta_analyse"
            repo.mkdir()
            secret = "ghp_" + "Z" * 36
            (repo / "analytics.py").write_text("token=" + repr(secret), encoding="utf-8")
            result = scan({"meta_analyse": repo})
            self.assertEqual(["meta_analyse"], result["scope"])
            self.assertEqual(1, result["observed_files"]["meta_analyse"]["code_files_examined"])
            report = json.dumps(result)
            self.assertIn("GITHUB_CLASSIC_TOKEN_SHAPE", report)
            self.assertNotIn(secret, report)
            self.assertEqual("NOT_ESTABLISHED", result["security_clearance"])

    def test_empty_scope_denied(self):
        with self.assertRaises(ValueError):
            scan({})

    def test_path_scope_rejected(self):
        with self.assertRaises(ValueError):
            scan({"unknown-repo": Path(".")})

    def test_oversize_file_does_not_execute(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "Terminan"
            repo.mkdir()
            (repo / "large.py").write_bytes(b"x" * 2_000_001)
            result = scan({"Terminan": repo})
            self.assertEqual(0, result["observed_files"]["Terminan"]["files_examined"])
            self.assertEqual(1, result["observed_files"]["Terminan"]["oversize_files_unscanned"])
            self.assertIn("OVERSIZE_FILE_NOT_SCANNED", {row["rule"] for row in result["review_findings"]})
            self.assertEqual("WORKTREE_PARTIAL", result["scope_completeness"])

    def test_sensitive_env_file_scanned_without_disclosure(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "meta_analyse"
            repo.mkdir()
            secret = "ghp_" + "X" * 36
            (repo / ".env").write_text("TOKEN=" + secret, encoding="utf-8")
            result = scan({"meta_analyse": repo})
            rules = {row["rule"] for row in result["review_findings"]}
            self.assertIn("SENSITIVE_CONFIG_PATH_REVIEW", rules)
            self.assertIn("GITHUB_CLASSIC_TOKEN_SHAPE", rules)
            self.assertNotIn(secret, json.dumps(result))
            self.assertFalse(result["full_history_scanned"])

    def test_six_worktrees_never_claim_history_clearance(self):
        with tempfile.TemporaryDirectory() as tmp:
            from security_audit.offline_inventory import REPOS
            paths = {}
            for name in REPOS:
                p = Path(tmp) / name
                p.mkdir()
                paths[name] = p
            result = scan(paths)
            self.assertEqual("WORKTREE_ONLY_NOT_GIT_HISTORY", result["scope_completeness"])
            self.assertFalse(result["full_history_scanned"])
            self.assertEqual("NOT_ESTABLISHED", result["security_clearance"])


if __name__ == "__main__":
    unittest.main()
