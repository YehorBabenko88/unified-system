"""Negative and controlled tests for exact-SHA GitHub inventory (no network)."""
import importlib.util
from pathlib import Path
from urllib.parse import parse_qs, urlparse

MODULE = Path(__file__).resolve().parents[1] / "tools" / "git_consolidation_snapshot.py"
spec = importlib.util.spec_from_file_location("git_consolidation_snapshot", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def sha(n):
    return format(n, "040x")


def test_paginated_full_page_then_final_page():
    calls = []
    def get(url):
        page = int(parse_qs(urlparse(url).query)["page"][0])
        calls.append(page)
        return list(range(100)) if page == 1 else [100]
    assert len(mod.paginated("math", "branches", get)) == 101
    assert calls == [1, 2]


def test_paginated_fails_closed_if_page_limit_hits():
    def get(_):
        return [None] * 100
    try:
        mod.paginated("math", "branches", get)
    except mod.InventoryError:
        pass
    else:
        raise AssertionError("truncated registry was accepted")


def test_paginated_rejects_malformed_response_and_untrusted_repo():
    for repo, resource, response in [("other", "branches", []),
                                    ("math", "issues", []),
                                    ("math", "branches", {"not": "a list"}),
                                    ("math", "branches", [None] * 101)]:
        try:
            mod.paginated(repo, resource, lambda _: response)
        except mod.InventoryError:
            pass
        else:
            raise AssertionError(f"accepted bad {repo}/{resource}")


def fixtures():
    branches = [{"name": "main", "commit": {"sha": sha(1)}},
                {"name": "feature", "commit": {"sha": sha(2)}}]
    pulls = [{"number": 10, "state": "open", "draft": True,
              "head": {"ref": "feature", "sha": sha(2),
                       "repo": {"full_name": "YehorBabenko88/math"}},
              "base": {"ref": "main", "sha": sha(1)},
              "html_url": "https://github.com/YehorBabenko88/math/pull/10"}]
    return branches, pulls


def test_collect_all_six_with_exact_shas_and_no_false_retirement():
    branches, pulls = fixtures()
    def get(url):
        return branches if "/branches?" in url else pulls
    inventory = mod.collect(get)
    assert inventory["counts"] == {"branches_including_main": 12, "open_pull_requests": 6}
    for record in inventory["repositories"]:
        matching = next(b for b in record["branches"] if b["name"] == "feature")
        assert matching["pull_request_numbers"] == [10] if record["repository"].endswith("/math") else matching["pull_request_numbers"] == []
        assert all(x["decision"] == "REVIEW_REQUIRED" for x in record["branches"])
        assert record["open_pull_requests"][0]["unique_changes"] == "NOT_EVALUATED"


def test_collect_refuses_stale_pr_head():
    branches, pulls = fixtures()
    pulls[0]["head"]["sha"] = sha(3)
    def get(url):
        return branches if "/branches?" in url else pulls
    try:
        mod.collect(get)
    except mod.InventoryError as exc:
        assert "HEAD mismatch" in str(exc)
    else:
        raise AssertionError("stale PR HEAD accepted")


def test_collect_refuses_duplicate_pr_or_branch():
    branches, pulls = fixtures()
    for malformed_branches, malformed_pulls in [(branches + branches[-1:], pulls),
                                                (branches, pulls + pulls)]:
        def get(url):
            return malformed_branches if "/branches?" in url else malformed_pulls
        try:
            mod.collect(get)
        except mod.InventoryError:
            pass
        else:
            raise AssertionError("duplicate inventory accepted")


def test_sha_validation_and_non_destructive_scope():
    assert mod.exact_sha("a" * 40)
    assert not mod.exact_sha("g" * 40)
    assert not mod.exact_sha("a" * 39)
    assert not mod.exact_sha("a" * 41)
    assert not mod.exact_sha(100)
    source = MODULE.read_text(encoding="utf-8")
    assert 'method="GET"' in source
    assert "requests.delete(" not in source.lower()
    assert "requests.post(" not in source.lower()
    assert "method=\"POST\"" not in source
