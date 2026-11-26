#!/usr/bin/env python3
"""Read-only, fail-closed six-repository GitHub branches/open-PR inventory.

Use: python tools/git_consolidation_snapshot.py --output snapshot.json
Needs Python stdlib, Internet, and optionally GITHUB_TOKEN for API rate limits.
This does NOT classify unique functionality: all unproved retirement decisions
are explicitly REVIEW_REQUIRED. No credential values are ever written.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

OWNER = "YehorBabenko88"
REPOS = ("unified-system", "bybit-cluster-grid", "math", "Terminan", "strattester", "meta_analyse")
PAGE_SIZE = 100
MAX_PAGES = 20
API = "https://api.github.com"


class InventoryError(RuntimeError):
    pass


def fetch_json(url: str, opener=urllib.request.urlopen):
    if not url.startswith(API + "/repos/" + OWNER + "/"):
        raise InventoryError("unapproved GitHub endpoint")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "unified-f-readonly-registry"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with opener(req, timeout=30) as response:
            if response.status != 200:
                raise InventoryError(f"GitHub HTTP {response.status}")
            return json.load(response)
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError) as exc:
        raise InventoryError("GitHub inventory request unavailable") from exc


def paginated(repo, resource, get=fetch_json):
    if repo not in REPOS or resource not in ("branches", "pulls"):
        raise InventoryError("unsupported inventory selection")
    combined = []
    for page in range(1, MAX_PAGES + 1):
        url = f"{API}/repos/{OWNER}/{repo}/{resource}?per_page={PAGE_SIZE}&page={page}"
        if resource == "pulls":
            url += "&state=open"
        batch = get(url)
        if not isinstance(batch, list) or len(batch) > PAGE_SIZE:
            raise InventoryError("invalid GitHub pagination response")
        combined.extend(batch)
        if len(batch) < PAGE_SIZE:
            return combined
    raise InventoryError("page limit reached; completeness unknown")


def exact_sha(value):
    return isinstance(value, str) and len(value) == 40 and all(c in "0123456789abcdef" for c in value)


def collect(get=fetch_json):
    result = {"schema_version": 1, "source": "GitHub REST /branches, /pulls?state=open",
              "collected_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "repository_owner": OWNER, "repositories": [], "counts": {}}
    for repo in REPOS:
        branch_raw = paginated(repo, "branches", get)
        pull_raw = paginated(repo, "pulls", get)
        branches = {}
        for value in branch_raw:
            name, sha = value["name"], value["commit"]["sha"]
            if name in branches or not exact_sha(sha):
                raise InventoryError(f"{repo}: duplicate branch or invalid SHA")
            branches[name] = sha
        if "main" not in branches:
            raise InventoryError(f"{repo}: main branch absent")
        pulls = []
        seen_numbers = set()
        for value in pull_raw:
            number = value["number"]
            if number in seen_numbers or value["state"] != "open":
                raise InventoryError(f"{repo}: duplicate or non-open PR")
            seen_numbers.add(number)
            head = value["head"]
            head_name, head_sha = head["ref"], head["sha"]
            base = value["base"]
            base_name, base_sha = base["ref"], base["sha"]
            if not exact_sha(head_sha) or not exact_sha(base_sha):
                raise InventoryError(f"{repo}: malformed PR SHA")
            same_repo = head["repo"] is not None and head["repo"]["full_name"].lower() == f"{OWNER}/{repo}".lower()
            if same_repo and branches.get(head_name) != head_sha:
                raise InventoryError(f"{repo} PR #{number}: branch HEAD mismatch or unlisted")
            pulls.append({"number": number, "head_ref": head_name, "head_sha": head_sha,
                          "base_ref": base_name, "base_sha": base_sha, "draft": value["draft"],
                          "same_repository_head": same_repo, "html_url": value["html_url"],
                          "decision": "REVIEW_REQUIRED", "unique_changes": "NOT_EVALUATED",
                          "evidence": []})
        result["repositories"].append({
            "repository": f"{OWNER}/{repo}", "main_sha": branches["main"],
            "branches": [{"name": name, "head_sha": sha, "decision": "REVIEW_REQUIRED",
                          "unique_changes": "NOT_EVALUATED", "evidence": [],
                          "pull_request_numbers": sorted(p["number"] for p in pulls if p["same_repository_head"] and p["head_ref"] == name)}
                         for name, sha in sorted(branches.items())],
            "open_pull_requests": sorted(pulls, key=lambda p: p["number"]),
        })
    result["counts"] = {"branches_including_main": sum(len(r["branches"]) for r in result["repositories"]),
                         "open_pull_requests": sum(len(r["open_pull_requests"]) for r in result["repositories"])}
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        inventory = collect()
    except (InventoryError, KeyError, TypeError) as exc:
        raise SystemExit(f"INVENTORY_INCOMPLETE: {type(exc).__name__}: {exc}") from None
    dest = Path(args.output)
    if dest.exists():
        raise SystemExit("INVENTORY_REFUSED: output exists; supply a new snapshot filename")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "COMPLETE_PAGINATED_METADATA_ONLY", "counts": inventory["counts"],
                      "output": str(dest)}))


if __name__ == "__main__":
    main()
