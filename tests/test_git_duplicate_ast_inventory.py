"""Unit tests for pinned-source function AST dedup inventory; fake local repos only."""
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "tools" / "git_duplicate_ast_inventory.py"
spec = importlib.util.spec_from_file_location("git_duplicate_ast_inventory", MODULE)
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


def fixture_body(name):
    statements = ["    a = value", "    for i in range(25):",
                  "        a = (a * 7 + i) % 101", "        if a > 51:",
                  "            a = a - 4", "        else:",
                  "            a = a + 2", "    return a"]
    return "def " + name + "(value):\n" + "\n".join(statements) + "\n"


class DuplicateASTTests(unittest.TestCase):
    def test_same_body_changed_function_name_has_stable_digest(self):
        first = inventory.fingerprint_functions(fixture_body("old"), "old.py")
        second = inventory.fingerprint_functions(fixture_body("new"), "new.py")
        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 1)
        matches = inventory.compare_file_pair(first, second, "GU-F01")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["id"], "GU-" + first[0]["body_sha256"][:20])
        self.assertEqual(matches[0]["semantic_equivalence"], "NOT_PROVEN")
        self.assertFalse(matches[0]["deletion_authorized"])

    def test_changed_function_body_does_not_match(self):
        first = inventory.fingerprint_functions(fixture_body("left"), "grid.py")
        changed = fixture_body("right").replace("a = a + 2", "a = a + 3")
        other = inventory.fingerprint_functions(changed, "root.py")
        self.assertEqual(inventory.compare_file_pair(first, other, "GU-F02"), [])

    def test_short_functions_excluded(self):
        self.assertEqual(inventory.fingerprint_functions("def trivial():\n    return 1\n", "x.py"), [])

    def test_exact_git_commit_read_and_dirty_worktree_is_ignored(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            def git(*args):
                return subprocess.check_output(["git", "-C", str(root), *args],
                                               stderr=subprocess.DEVNULL).decode().strip()
            git("init")
            git("config", "user.email", "test@example.invalid")
            git("config", "user.name", "Local Test")
            source = fixture_body("source")
            (root / "file.py").write_text(source)
            git("add", "file.py")
            git("commit", "-m", "fixture")
            head = git("rev-parse", "HEAD")
            (root / "file.py").write_text("raise RuntimeError('dirty')\n")
            self.assertEqual(inventory.immutable_git_source(root, head, "file.py"), source)
            with self.assertRaises(inventory.EvidenceUnavailable):
                inventory.immutable_git_source(root, "0" * 40, "file.py")
            with self.assertRaises(inventory.EvidenceUnavailable):
                inventory.immutable_git_source(root, head[:8], "file.py")

    def test_published_family_claim_sums_to_31_not_32(self):
        self.assertEqual(len(inventory.FILES), 5)
        self.assertEqual(sum(row[3] for row in inventory.FILES), 31)


if __name__ == "__main__":
    unittest.main()
