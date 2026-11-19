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
CONFIG_SUFFIX = frozenset((".ps1", ".sh", ".bat", ".cmd", ".toml", ".ini", ".cfg", ".config", ".properties", ".yml", ".yaml", ".json", ".env", ".pem", ".key"))
SENSITIVE_NAMES = frozenset((".env", ".env.local", ".npmrc", ".pypirc", "id_rsa", "id_ed25519"))
GIT_HISTORY_NOTE = "Working trees do not include deleted commits, remote PR refs, tags or LFS content."
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
        seen = {"files_examined": 0, "workflows_examined": 0, "code_files_examined": 0,
                "oversize_files_unscanned": 0}
        for p in _files(root):
            rel = p.relative_to(root).as_posix()
            if p.stat().st_size > MAX_FILE_BYTES:
                seen["oversize_files_unscanned"] += 1
                findings.append({"repository": repo, "path": rel,
                                 "rule": "OVERSIZE_FILE_NOT_SCANNED", "level": "REVIEW"})
                continue
            raw = p.read_bytes()
            seen["files_examined"] += 1
            if p.suffix.lower() in CODE_SUFFIX:
                seen["code_files_examined"] += 1
                digest = git_blob_oid(raw)
                digest_map.setdefault(digest, []).append({"repository": repo, "path": rel, "git_blob_oid": digest})
            relevant = (rel.startswith(".github/workflows/") and p.suffix.lower() in (".yml", ".yaml"))
            relevant = (relevant or p.suffix.lower() in CODE_SUFFIX | CONFIG_SUFFIX
                        or p.name in SENSITIVE_NAMES or p.name.startswith(".env.")
                        or rel in ("requirements.txt", "requirements-ml.txt", "pyproject.toml", "package.json"))
            if p.name in SENSITIVE_NAMES or p.name.startswith(".env."):
                findings.append({"repository": repo, "path": rel,
                                 "rule": "SENSITIVE_CONFIG_PATH_REVIEW", "level": "REVIEW"})
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
        "scope_completeness": "WORKTREE_PARTIAL" if set(roots) != set(REPOS)
                              or any(row["oversize_files_unscanned"] for row in counters.values())
                              else "WORKTREE_ONLY_NOT_GIT_HISTORY",
        "full_history_scanned": False,
        "all_pr_heads_scanned": False,
        "lfs_objects_scanned": False,
        "archival_security_clearance": "NOT_ESTABLISHED",
        "security_clearance": "NOT_ESTABLISHED",
        "secrets_exposure_clearance": "NOT_ESTABLISHED",
    }



# Architecture ownership observations are intentionally separate from security
# clearance. These are AST/static findings, never execution or deletion grants.
import ast

ARCHITECTURE_OWNERSHIP_VERSION = "unified.architecture.static.v1"
EXCHANGE_MODULES = frozenset(("pybit", "ccxt", "bybit"))
EXCHANGE_HOST_PATTERN = re.compile(r"(?:api(?:-testnet)?\.bybit\.com|stream(?:-testnet)?\.bybit\.com)", re.I)
SQL_BOOTSTRAP_PATTERN = re.compile(
    r"\bCREATE\s+(?:DATABASE|ROLE|USER)\b|\binitdb\b|\bpg_ctl\s+init\b", re.I
)
DIRECT_MARKET_WRITE_PATTERN = re.compile(
    r"\b(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+"
    r"(?:[a-z_][\w]*\.)?(?:ohlcv(?:_1m)?|market_trades|orderbook|funding|open_interest)\b",
    re.I,
)
RUNTIME_SUFFIXES = frozenset((".py", ".js", ".ts", ".ps1", ".sh", ".sql"))
SSH_TRUST_BYPASS_PATTERN = re.compile(
    r"(?:StrictHostKeyChecking\s*[= ]\s*no\b|"
    r"UserKnownHostsFile\s*[= ]\s*/dev/null\b|"
    r"sshpass\s+-p(?:\s|$))", re.I,
)



def architecture_scan(roots: dict[str, Path]) -> dict[str, Any]:
    """Find cross-repo ownership violations without importing or executing code.

    Static matches are review candidates. A complete integration graph additionally
    needs exact-head checkout, dynamic import tracing, API tests and owner ACK.
    """
    if not roots or set(roots) - set(REPOS):
        raise ValueError("unknown repository scope")
    findings: list[dict[str, str]] = []
    reviewed: dict[str, dict[str, int]] = {}
    for repo in REPOS:
        if repo not in roots:
            continue
        root = Path(roots[repo])
        if not root.is_dir() or root.is_symlink():
            raise ValueError("repository path not a real directory")
        counts = {"runtime_files_examined": 0, "python_files_parsed": 0,
                  "oversize_files_unscanned": 0, "python_parse_errors": 0}
        for p in _files(root):
            if p.suffix.lower() not in RUNTIME_SUFFIXES:
                continue
            rel = p.relative_to(root).as_posix()
            if p.stat().st_size > MAX_FILE_BYTES:
                counts["oversize_files_unscanned"] += 1
                findings.append({"repository": repo, "path": rel,
                                 "rule": "ARCH_OVERSIZE_UNSCANNED", "level": "BLOCKED"})
                continue
            counts["runtime_files_examined"] += 1
            src = p.read_text(encoding="utf-8", errors="replace")
            if repo != "bybit-cluster-grid" and (
                EXCHANGE_HOST_PATTERN.search(src) or
                re.search(r"\b(?:from|import)\s+(?:pybit|ccxt)\b", src)
            ):
                findings.append({"repository": repo, "path": rel,
                                 "rule": "ARCH_EXCHANGE_CLIENT_OUTSIDE_GRID",
                                 "level": "REVIEW"})
            if repo != "unified-system" and SQL_BOOTSTRAP_PATTERN.search(src):
                findings.append({"repository": repo, "path": rel,
                                 "rule": "ARCH_DB_PROVISIONING_OUTSIDE_UNIFIED",
                                 "level": "REVIEW"})
            if repo != "bybit-cluster-grid" and DIRECT_MARKET_WRITE_PATTERN.search(src):
                findings.append({"repository": repo, "path": rel,
                                 "rule": "ARCH_MARKET_TABLE_WRITE_OUTSIDE_GRID",
                                 "level": "REVIEW"})
            if SSH_TRUST_BYPASS_PATTERN.search(src):
                findings.append({"repository": repo, "path": rel,
                                 "rule": "ARCH_SSH_HOST_TRUST_BYPASS_REVIEW",
                                 "level": "REVIEW"})
            if p.suffix.lower() == ".py":
                try:
                    tree = ast.parse(src, filename=rel)
                except SyntaxError:
                    counts["python_parse_errors"] += 1
                    findings.append({"repository": repo, "path": rel,
                                     "rule": "ARCH_PYTHON_PARSE_ERROR", "level": "REVIEW"})
                    continue
                counts["python_files_parsed"] += 1
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        modules = [alias.name for alias in node.names]
                    elif isinstance(node, ast.ImportFrom):
                        modules = [node.module or ""]
                    else:
                        modules = []
                    if repo != "bybit-cluster-grid" and any(
                        m == "pybit" or m.startswith("pybit.") or
                        m == "ccxt" or m.startswith("ccxt.")
                        for m in modules
                    ):
                        findings.append({"repository": repo, "path": rel,
                                         "rule": "ARCH_EXCHANGE_IMPORT_OUTSIDE_GRID",
                                         "level": "REVIEW"})
        reviewed[repo] = counts
    findings.sort(key=lambda x: (x["repository"], x["path"], x["rule"]))
    return {
        "schema": ARCHITECTURE_OWNERSHIP_VERSION,
        "mode": "READ_ONLY_STATIC_NOT_RUNTIME_PROOF",
        "observed_repositories": list(reviewed),
        "observed_files": reviewed,
        "ownership_findings": findings,
        "automatic_removals": 0,
        "cross_repo_runtime_imports_verified": False,
        "db_role_permissions_verified": False,
        "distributed_orchestrator_verified": False,
        "ready_to_merge": False,
        "release_status": "NO_GO",
    }


def meta_import_inventory(root: Path) -> dict[str, Any]:
    """Statically enumerate Meta imports, entrypoints and direct consumers.

    Never infer that a function is UNUSED merely because no edge is found.
    Dynamic imports, external projects, Windows scripts and deployed services
    require separate human and runtime qualification.
    """
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Meta repository path must be a real directory")
    package = root / "src" / "meta_analyse"
    if not package.is_dir():
        raise ValueError("Meta package source tree missing")
    modules: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, str]] = []
    pending: list[dict[str, str]] = []
    for path in _files(package):
        if path.suffix != ".py":
            continue
        rel = path.relative_to(root).as_posix()
        if path.stat().st_size > MAX_FILE_BYTES:
            pending.append({"path": rel, "reason": "OVERSIZE_UNSCANNED"})
            continue
        module = "meta_analyse." + ".".join(path.relative_to(package).with_suffix("").parts)
        raw = path.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(raw, filename=rel)
        except SyntaxError:
            pending.append({"path": rel, "reason": "PYTHON_PARSE_ERROR"})
            continue
        public = sorted({
            node.name for node in tree.body
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            and not node.name.startswith("_")
        })
        modules[module] = {"path": rel, "symbols": public}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.level:
                    prefix = module.rsplit(".", 1)[0]
                    parts = prefix.split(".")
                    up = node.level - 1
                    if up >= len(parts):
                        pending.append({"path": rel, "reason": "UNRESOLVED_RELATIVE_IMPORT"})
                        continue
                    target = ".".join(parts[:len(parts) - up] + ([node.module] if node.module else []))
                else:
                    target = node.module or ""
                if target.startswith("meta_analyse"):
                    for alias in node.names:
                        edges.append({"source": module, "target": target, "symbol": alias.name})
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("meta_analyse"):
                        edges.append({"source": module, "target": alias.name, "symbol": "*"})
            elif isinstance(node, ast.Call):
                fn = node.func
                name = fn.id if isinstance(fn, ast.Name) else (
                    fn.attr if isinstance(fn, ast.Attribute) else None
                )
                if name in ("__import__", "import_module", "exec", "eval"):
                    pending.append({"path": rel, "reason": "DYNAMIC_CALL_REVIEW"})
    script = root / "pyproject.toml"
    entrypoints: list[str] = []
    if script.is_file() and script.stat().st_size <= MAX_FILE_BYTES:
        body = script.read_text(encoding="utf-8", errors="replace")
        in_scripts = False
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                in_scripts = stripped == "[project.scripts]"
            elif in_scripts and "=" in stripped and not stripped.startswith("#"):
                entrypoints.append(stripped.split("#", 1)[0].strip())
    return {
        "schema": "unified.meta.import-inventory.v1",
        "mode": "STATIC_ONLY_NO_EXECUTION",
        "modules": {key: modules[key] for key in sorted(modules)},
        "edges": sorted(edges, key=lambda e: (e["source"], e["target"], e["symbol"])),
        "entrypoints": sorted(entrypoints),
        "pending": sorted(pending, key=lambda v: (v["path"], v["reason"])),
        "external_consumers_verified": False,
        "all_runtime_consumers_switched": False,
        "unused_symbols_proven": False,
        "archival_ready": False,
        "automatic_deletions": 0,
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
