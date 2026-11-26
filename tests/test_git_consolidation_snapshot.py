"""Fail-closed exact-SHA GitHub registry tests; no network or credentials."""
import importlib.util
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

MODULE = Path(__file__).resolve().parents[1] / "tools" / "git_consolidation_snapshot.py"
spec = importlib.util.spec_from_file_location("git_consolidation_snapshot", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def sha(number):
    return format(number, "040x")


def fixture():
    branches = [{"name": "main", "commit": {"sha": sha(1)}},
                {"name": "feature", "commit": {"sha": sha(2)}}]
    pulls = [{"number": 10, "state": "open", "draft": True,
              "head": {"ref": "feature", "sha": sha(2),
                       "repo": {"full_name": "YehorBabenko88/math"}},
              "base": {"ref": "main", "sha": sha(1)},
              "html_url": "https://github.com/YehorBabenko88/math/pull/10"}]
    return branches, pulls


class GitConsolidationSnapshotTests(unittest.TestCase):
    def test_full_page_then_terminal_page(self):
        calls = []
        def get(url):
            page = int(parse_qs(urlparse(url).query)["page"][0])
            calls.append(page)
            return list(range(100)) if page == 1 else [100]
        self.assertEqual(len(mod.paginated("math", "branches", get)), 101)
        self.assertEqual(calls, [1, 2])

    def test_page_limit_refuses_truncated_registry(self):
        with self.assertRaises(mod.InventoryError):
            mod.paginated("math", "branches", lambda _: [None] * 100)

    def test_bad_queries_and_response_shape_refused(self):
        for repo, resource, value in [("other", "branches", []), ("math", "issues", []),
                                      ("math", "branches", {}), ("math", "branches", [0] * 101)]:
            with self.subTest(repo=repo, resource=resource):
                with self.assertRaises(mod.InventoryError):
                    mod.paginated(repo, resource, lambda _: value)

    def test_all_six_have_conservative_dispositions(self):
        branches, pulls = fixture()
        def get(url):
            return branches if "/branches?" in url else pulls
        snapshot = mod.collect(get)
        self.assertEqual(snapshot["counts"], {"branches_including_main": 12, "open_pull_requests": 6})
        for record in snapshot["repositories"]:
            feature = next(b for b in record["branches"] if b["name"] == "feature")
            self.assertEqual(feature["pull_request_numbers"],
                             [10] if record["repository"].endswith("/math") else [])
            self.assertTrue(all(b["decision"] == "REVIEW_REQUIRED" for b in record["branches"]))
            self.assertEqual(record["open_pull_requests"][0]["unique_changes"], "NOT_EVALUATED")

    def test_stale_pr_head_rejected(self):
        branches, pulls = fixture()
        pulls[0]["head"]["sha"] = sha(3)
        with self.assertRaisesRegex(mod.InventoryError, "HEAD mismatch"):
            mod.collect(lambda url: branches if "/branches?" in url else pulls)

    def test_duplicate_branch_and_pr_rejected(self):
        branches, pulls = fixture()
        for bb, pp in [(branches + branches[-1:], pulls), (branches, pulls + pulls)]:
            with self.assertRaises(mod.InventoryError):
                mod.collect(lambda url: bb if "/branches?" in url else pp)

    def test_sha_format_and_no_mutating_client(self):
        self.assertTrue(mod.exact_sha("a" * 40))
        for value in ("g" * 40, "a" * 39, "a" * 41, 100):
            self.assertFalse(mod.exact_sha(value))
        source = MODULE.read_text(encoding="utf-8")
        self.assertIn('method="GET"', source)
        self.assertNotIn('method="POST"', source)
        self.assertNotIn("requests.delete(", source.lower())


if __name__ == "__main__":
    unittest.main()
