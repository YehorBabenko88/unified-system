"""Observe a reviewed PR cohort and generate an advisory Aâ€“F work queue."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess

SHA = re.compile(r"[a-f0-9]{40}")
LANE_ISSUES = dict(zip("ABCDEF", range(117, 123)))
ROOT = Path(__file__).resolve().parents[1]


class CohortMoved(ValueError):
    pass


def github(endpoint):
    result = subprocess.run(
        ["gh", "api", endpoint], capture_output=True, text=True,
        encoding="utf-8", timeout=25, check=False,
    )
    if result.returncode:
        raise RuntimeError("GitHub metadata unavailable")
    return json.loads(result.stdout)


def observe(api, repository, number):
    prefix = f"repos/{repository}/pulls/{number}"
    pull = api(prefix)
    head, base = pull["head"], pull["base"]
    if not SHA.fullmatch(head["sha"]) or not SHA.fullmatch(base["sha"]):
        raise ValueError("Invalid commit identity")
    if pull["changed_files"] > 300:
        raise ValueError("Pull request exceeds file inventory budget")
    paths = set()
    entries = []
    for page in range(1, 4):
        batch = api(f"{prefix}/files?per_page=100&page={page}")
        entries.extend(batch)
        if len(batch) < 100:
            break
    if len(entries) != pull["changed_files"]:
        raise ValueError("Incomplete file inventory")
    for item in entries:
        paths.add(item["filename"])
        if "previous_filename" in item:
            paths.add(item["previous_filename"])
    runs = api(f"repos/{repository}/actions/runs?head_sha={head['sha']}&per_page=100")
    if runs["total_count"] > 100:
        raise ValueError("Workflow inventory exceeds budget")
    checks = Counter(
        (run["conclusion"] or "unknown") if run["status"] == "completed" else run["status"]
        for run in runs["workflow_runs"] if run["head_sha"] == head["sha"]
    )
    return {
        "repository": repository, "pr": number, "head": head["sha"], "base": base["sha"],
        "head_repository": (head["repo"] or {}).get("full_name"),
        "head_ref": head["ref"], "base_ref": base["ref"], "state": pull["state"],
        "draft": pull["draft"], "mergeable": pull["mergeable"],
        "paths": sorted(paths), "workflows": dict(checks),
    }


def manifest(config, api=github):
    if config["schema"] != "unified.release-cohort.v1":
        raise ValueError("Unsupported cohort schema")
    sources = config["sources"]
    observed = {}
    blockers = defaultdict(list)
    for name, source in sources.items():
        repository = f"{config['owner']}/{source['repo']}"
        observed[name] = observe(api, repository, source["pr"])
    for name, pr in observed.items():
        current = api(f"repos/{pr['repository']}/pulls/{pr['pr']}")
        if (current["head"]["sha"], current["base"]["sha"]) != (pr["head"], pr["base"]):
            raise CohortMoved(f"Cohort moved during collection: {name}")
        if pr["state"] != "open" or pr["head_repository"] != pr["repository"]:
            blockers[name].append("SOURCE_NOT_ADMITTED")
        if pr["mergeable"] is not True:
            blockers[name].append("BASE_COMPATIBILITY_UNCONFIRMED")
        if not pr["workflows"] or set(pr["workflows"]) != {"success"}:
            blockers[name].append("CI_REQUIRES_REVIEW")
        for dependency in sources[name]["depends_on"]:
            other = observed[dependency]
            if (
                other["repository"] == pr["repository"]
                and pr["base_ref"] == other["head_ref"]
                and pr["base"] != other["head"]
            ):
                blockers[name].append(f"STACK_DRIFT:{dependency}")
    items = list(observed.items())
    conflicts = []
    for index, (name, pr) in enumerate(items):
        for other_name, other in items[index + 1:]:
            if pr["repository"] != other["repository"]:
                continue
            paths = sorted(set(pr["paths"]) & set(other["paths"]))
            if paths:
                conflicts.append({"sources": [name, other_name], "paths": paths})
                blockers[name].append(f"OVERLAP:{other_name}")
                blockers[other_name].append(f"OVERLAP:{name}")
    queue = {}
    for lane, issue in LANE_ISSUES.items():
        candidates = {
            name: blockers[name] for name, source in sources.items() if source["lane"] == lane
        }
        queue[lane] = {"issue": issue, "state": "AWAITING_OWNER_REVIEW", "candidates": candidates}
    return {
        "schema": "unified.integration-observation.v1", "release": "NO_GO",
        "executor": "NOT_CONNECTED", "compatibility": "REQUIRES_EXACT_COHORT_ACCEPTANCE",
        "master": config["master"], "sources": observed,
        "dependencies": {name: source["depends_on"] for name, source in sources.items()},
        "conflicts": conflicts, "queue": queue,
    }


def stable_manifest(config, api=github):
    for retry in range(3):
        try:
            return manifest(config, api)
        except CohortMoved:
            if retry == 2:
                raise


def reports(result, config, directory):
    payload = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
    digest = hashlib.sha256(payload.encode()).hexdigest()
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "manifest.json").write_bytes(payload.encode())
    provenance = [
        f"- {pr['repository']}#{pr['pr']} at `{pr['head']}` CI `{json.dumps(pr['workflows'], sort_keys=True)}`"
        for pr in result["sources"].values()
    ]
    for lane, task in [*result["queue"].items(), ("MASTER", {"issue": config["master"]})]:
        lines = [f"<!-- unified-stage13:{digest}:{lane} -->", "### Stage 13 integration observation",
                 "", "Release NO_GO. Advisory queue. Codex executor NOT_CONNECTED.",
                 f"Coordinator Windows/Linux matrix: {result['coordinator_tests']}.",
                 "", *provenance, "", "Accepted changes and module compatibility require independent exact-cohort review."]
        for key, entry in result["queue"].items():
            if lane in (key, "MASTER"):
                for source, reasons in entry["candidates"].items():
                    lines.append(f"- Lane {key}, #{entry['issue']}, {source} â€” " +
                                 (", ".join(reasons) or "Review exact-cohort compatibility"))
        (directory / f"issue-{task['issue']}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--coordinator-tests", choices=("success", "failure", "skipped", "cancelled"),
                        default="skipped")
    args = parser.parse_args()
    config = json.loads((ROOT / "release/stage13-cohort.json").read_text(encoding="utf-8"))
    result = stable_manifest(config)
    result["coordinator_tests"] = args.coordinator_tests
    reports(result, config, args.output)


if __name__ == "__main__":
    main()
