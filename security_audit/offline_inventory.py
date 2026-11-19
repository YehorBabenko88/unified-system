"""Read-only, offline security and cross-repository overlap inventory.

Observations are review candidates, not vulnerability confirmations.
No GitHub/network/SSH/SQL access, subprocesses, code import, file mutations
or automatic deletion of suspected duplicates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

REPOS = ("bybit-cluster-grid", "strattester", "math", "unified-system", "Terminan", "meta_analyse")
CODE_SUFFIX = frozenset((".py", ".js", ".mjs", ".cjs", ".ts", ".sql"))
MAX_FILE_BYTES = 2_000_000
MAX_FILES_PER_REPO = 15_000
ACTION = re.compile(r"^\s*-\s*uses:\s*['\"]?([^'\"\s#]+)", re.M)
COMMIT_PIN = re.compile(r"@[0-9a-f]{40}$", re.I)
SECRETS = {
    "GITHUB_CLASSIC_TOKEN_SHAPE": re.compile(r"\bghp_[A-Za-z0-9]{36}\b"),
    "GITHUB_FINEGRAINED_TOKEN_SHAPE": re.compile(r"\bgithub_pat_[A-Za-z0-9_]{60,}\b"),
    "AWS_ACCESS_KEY_ID_SHAPE": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "PRIVATE_KEY_PEM_HEADER": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"),
}
WORKFLOW_STRINGS = {
    "PR_TARGET_EVENT_REVIEW": re.compile(r"^\s*pull_request_target\s*:", re.M),
    "WRITE_ALL_TOKEN_REVIEW": re.compile(r"^\s*permissions\s*:\s*write-all\s*(?:#.*)?$", re.M),
    "REMOTE_SHELL_PIPE_REVIEW": re.compile(r"(?:curl|wget)\b[^\n]{0,300}\|\s*(?:sh|bash)\b", re.I),
}
REQUIREMENT = re.compile(r"^[A-Za-z][\w.-]*(?:\[[^\]]+\])?\s*(?:>=|~=|>)", re.M)


def git_blob_oid(payload: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(payload)).encode("ascii") + b"\x00" + payload).hexdigest()


def _files(root: Path):
    count = 0
    for parent, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in (".git", ".venv", "venv", "node_modules", "__pycache__")
                         and not (Path(parent) / d).is_symlink())
        for filename in sorted(files):
            p = Path(parent) / filename
            if p.is_symlink() or not p.is_file():
                continue
            count += 1
            if count > MAX_FILES_PER_REPO:
                raise ValueError("repository file cap exceeded")
            if p.stat().st_size > MAX_FILE_BYTES:
                continue
            yield p


def scan(roots: dict[str, Path]) -> dict[str, Any]:
    if not roots or set(roots) - set(REPOS):
        raise ValueError("unknown repository scope")
    findings: list[dict[str, str]] = []
    digest_map: dict[str, list[dict[str, str]]] = {}
    counters: dict[str, dict[str, int]] = {}
    for repo in REPOS:
        if repo not in roots:
            continue
        root = Path(roots[repo])
        if not root.is_dir() or root.is_symlink():
            raise ValueError("repository path not a real directory")
        seen = {"files_examined": 0, "workflows_examined": 0, "code_files_examined": 0}
        for p in _files(root):
            rel = p.relative_to(root).as_posix()
            raw = p.read_bytes()
            seen["files_examined"] += 1
            if p.suffix.lower() in CODE_SUFFIX:
                seen["code_files_examined"] += 1
                digest = git_blob_oid(raw)
                digest_map.setdefault(digest, []).append({"repository": repo, "path": rel, "git_blob_oid": digest})
            relevant = (rel.startswith(".github/workflows/") and p.suffix.lower() in (".yml", ".yaml"))
            relevant = relevant or p.suffix.lower() in CODE_SUFFIX or rel in ("requirements.txt", "requirements-ml.txt", "pyproject.toml", "package.json")
            if not relevant:
                continue
            text = raw.decode("utf-8", errors="replace")
            for code, regex in SECRETS.items():
                if regex.search(text):
                    findings.append({"repository": repo, "path": rel, "rule": code, "level": "REVIEW"})
            if rel.startswith(".github/workflows/") and p.suffix.lower() in (".yml", ".yaml"):
                seen["workflows_examined"] += 1
                # A minority of valid GitHub workflows use JSON, which is a YAML subset.
                # Parsing it avoids false "no permissions" and missed action uses.
                if text.lstrip().startswith("{"):
                    try:
                        workflow = json.loads(text)
                    except json.JSONDecodeError:
                        findings.append({"repository": repo, "path": rel, "rule": "INVALID_JSON_WORKFLOW", "level": "REVIEW"})
                        continue
                    jobs = workflow.get("jobs", {}) if isinstance(workflow, dict) else {}
                    if not isinstance(jobs, dict):
                        jobs = {}
                    actions = []
                    for job in jobs.values():
                        if isinstance(job, dict) and isinstance(job.get("steps", []), list):
                            actions.extend(
                                step["uses"] for step in job["steps"]
                                if isinstance(step, dict) and isinstance(step.get("uses"), str)
                            )
                    permissions_declared = isinstance(workflow, dict) and "permissions" in workflow
                    if not permissions_declared:
                        permissions_declared = bool(jobs) and all(
                            isinstance(job, dict) and "permissions" in job
                            for job in jobs.values()
                        )
                else:
                    actions = ACTION.findall(text)
                    permissions_declared = bool(re.search(r"^\s*permissions\s*:", text, re.M))
                for action in actions:
                    if action.startswith("./") or action.startswith("docker://"):
                        continue
                    if not COMMIT_PIN.search(action):
                        findings.append({"repository": repo, "path": rel, "rule": "ACTION_UNPINNED", "level": "REVIEW"})
                for code, regex in WORKFLOW_STRINGS.items():
                    if regex.search(text):
                        findings.append({"repository": repo, "path": rel, "rule": code, "level": "REVIEW"})
                if not permissions_declared:
                    findings.append({"repository": repo, "path": rel, "rule": "TOKEN_PERMISSIONS_UNDECLARED", "level": "REVIEW"})
            if rel in ("requirements.txt", "requirements-ml.txt") and REQUIREMENT.search(text):
                findings.append({"repository": repo, "path": rel, "rule": "OPEN_DEPENDENCY_RANGE", "level": "REVIEW"})
        counters[repo] = seen
    duplicated = []
    for digest, rows in sorted(digest_map.items()):
        if len(set(row["repository"] for row in rows)) > 1:
            duplicated.append({"git_blob_oid": digest, "occurrences": sorted(rows, key=lambda r: (r["repository"], r["path"]))})
    findings.sort(key=lambda x: (x["repository"], x["path"], x["rule"]))
    return {
        "schema": "unified.security.crossrepo-offline.v1",
        "scope": list(roots),
        "mode": "READ_ONLY_NO_EXECUTION",
        "observed_files": counters,
        "review_findings": findings,
        "exact_cross_repo_code_duplicates": duplicated,
        "automatic_removals": 0,
        "security_clearance": "NOT_ESTABLISHED",
        "secrets_exposure_clearance": "NOT_ESTABLISHED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only six-repo security and duplicate code audit")
    for name in REPOS:
        parser.add_argument("--" + name, dest=name.replace("-", "_"))
    args = parser.parse_args()
    roots = {name: Path(getattr(args, name.replace("-", "_"))) for name in REPOS
             if getattr(args, name.replace("-", "_")) is not None}
    if not roots:
        parser.error("At least one repository path is required")
    result = scan(roots)
    print(json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
