"""Read-only, offline security and cross-repository overlap inventory.

Observations are review candidates, not vulnerability confirmations.
The worktree scanner never invokes subprocesses or imports target code.
The optional Git-history scanner invokes only read-only Git commands against
local repositories; neither mode performs network access, writes or deletion.
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

# Stage 9: trade-execution semantics do not belong to Math even when
# documented as "research only". These are review candidates, not auto-deletes.
MATH_TRADE_SEMANTICS = re.compile(
    r"(?:\b(?:paper(?:_trading)?|virtual[_ -]?(?:order|position)|"
    r"slippage|commission|pnl|position[_ -]?sizing|martingale|"
    r"trade[_ -]?execution|fill[_ -]?price)\b)",
    re.I,
)

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
            if repo == "math" and MATH_TRADE_SEMANTICS.search(src):
                findings.append({"repository": repo, "path": rel,
                                 "rule": "ARCH_MATH_TRADE_SEMANTICS_REVIEW",
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


def scan_git_history(repo_path: Path, *, max_blob_bytes: int = MAX_FILE_BYTES,
                     stream_large_blobs: bool = False,
                     max_stream_blob_bytes: int = 268_435_456) -> dict[str, Any]:
    """Read Git objects reachable from *local* refs, never execute repository code.

    The output is deliberately redacted. This does not verify remote ref
    completeness, deleted unreachable objects, Git LFS payloads or credential
    validity. It is independent of the existing worktree-only scan().
    """
    import subprocess
    import threading

    root = Path(repo_path)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("invalid Git repository directory")
    if not (0 < max_blob_bytes <= MAX_FILE_BYTES):
        raise ValueError("invalid scan byte cap")
    if type(stream_large_blobs) is not bool or not (
        max_blob_bytes <= max_stream_blob_bytes <= 268_435_456
    ):
        raise ValueError("invalid streaming scan bounds")

    def git(*args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(root), *args], stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, check=False, timeout=120,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0",
                 "GIT_OPTIONAL_LOCKS": "0"},
        )
        if result.returncode:
            raise ValueError("Git operation failed; history scan is incomplete")
        return result.stdout.decode("utf-8", errors="replace")

    shallow = git("rev-parse", "--is-shallow-repository").strip()
    refs = git("for-each-ref", "--format=%(refname)").splitlines()
    objects = git("rev-list", "--objects", "--all").splitlines()
    object_ids = list(dict.fromkeys(
        line.split(" ", 1)[0] for line in objects if line.strip()
    ))
    if not refs or not object_ids or len(object_ids) > 500_000:
        raise ValueError("missing refs or object inventory exceeds safety cap")
    if any(not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", x) for x in object_ids):
        raise ValueError("invalid Git object identifier")

    command = ["git", "-C", str(root), "cat-file", "--batch"]
    proc = subprocess.Popen(
        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0",
             "GIT_OPTIONAL_LOCKS": "0"},
    )
    writer_errors: list[str] = []

    def writer() -> None:
        try:
            assert proc.stdin is not None
            for oid in object_ids:
                proc.stdin.write((oid + "\n").encode("ascii"))
            proc.stdin.close()
        except (OSError, ValueError):
            writer_errors.append("git batch input failure")

    thread = threading.Thread(target=writer, daemon=True)
    thread.start()

    def read_exact(count: int, retain: bool) -> bytes:
        assert proc.stdout is not None
        chunks: list[bytes] = []
        while count:
            part = proc.stdout.read(min(count, 65536))
            if not part:
                raise ValueError("truncated Git object stream")
            count -= len(part)
            if retain:
                chunks.append(part)
        return b"".join(chunks) if retain else b""

    # All current token-shape rules are ASCII; scan bytes so a token split across
    # read boundaries is not missed, without retaining oversized blob contents.
    byte_rules = {
        name: re.compile(regex.pattern.encode("ascii"), regex.flags & re.IGNORECASE)
        for name, regex in SECRETS.items()
    }

    def scan_large_blob(count: int) -> tuple[set[str], bool]:
        assert proc.stdout is not None
        matches: set[str] = set()
        previous = b""
        first = True
        is_lfs_pointer = False
        while count:
            part = proc.stdout.read(min(count, 65536))
            if not part:
                raise ValueError("truncated oversized Git blob stream")
            count -= len(part)
            if first:
                is_lfs_pointer = part.startswith(b"version https://git-lfs.github.com/spec/v1\n")
                first = False
            window = previous + part
            for name, regex in byte_rules.items():
                if name not in matches and regex.search(window):
                    matches.add(name)
            # Longer than every bounded secret-shape rule; no full-blob retention.
            previous = window[-256:]
        return matches, is_lfs_pointer

    rule_counts = {name: 0 for name in SECRETS}
    blobs = 0
    skipped = 0
    streamed_blobs = 0
    lfs_pointers = 0
    try:
        assert proc.stdout is not None
        for expected in object_ids:
            header = proc.stdout.readline().decode("ascii", errors="replace").strip()
            parts = header.split()
            if len(parts) != 3 or parts[0] != expected or not parts[2].isdigit():
                raise ValueError("invalid Git object batch response")
            object_type, size = parts[1], int(parts[2])
            if size < 0:
                raise ValueError("invalid Git object length")
            retain = object_type == "blob" and size <= max_blob_bytes
            streaming = (object_type == "blob" and stream_large_blobs
                         and max_blob_bytes < size <= max_stream_blob_bytes)
            if streaming:
                matched_rules, lfs_pointer = scan_large_blob(size)
                payload = b""
            else:
                payload = read_exact(size, retain)
            if proc.stdout.read(1) != b"\n":
                raise ValueError("invalid Git object delimiter")
            if object_type != "blob":
                continue
            blobs += 1
            if streaming:
                streamed_blobs += 1
                lfs_pointers += int(lfs_pointer)
                for name in matched_rules:
                    rule_counts[name] += 1
                continue
            if not retain:
                skipped += 1
                continue
            if payload.startswith(b"version https://git-lfs.github.com/spec/v1\n"):
                lfs_pointers += 1
            decoded = payload.decode("utf-8", errors="replace")
            for name, pattern in SECRETS.items():
                if pattern.search(decoded):
                    rule_counts[name] += 1
        thread.join(timeout=30)
        if thread.is_alive() or writer_errors or proc.wait(timeout=30):
            raise ValueError("Git history scan did not complete")
    except Exception:
        proc.kill()
        proc.wait()
        raise

    return {
        "schema": "unified.security.local-git-history.v1",
        "mode": "READ_ONLY_GIT_OBJECTS_NO_REPOSITORY_EXECUTION",
        "local_refs": len(refs),
        "local_pr_head_refs": sum(x.startswith("refs/pull/") or
                                  x.startswith("refs/remotes/pr/") for x in refs),
        "local_tags": sum(x.startswith("refs/tags/") for x in refs),
        "reachable_git_objects": len(object_ids),
        "blob_objects_examined": blobs - skipped,
        "oversize_blob_objects_unscanned": skipped,
        "oversize_blob_objects_streamed": streamed_blobs,
        "git_lfs_pointers": lfs_pointers,
        "shallow_clone": shallow != "false",
        "local_ref_scan_complete": shallow == "false" and skipped == 0,
        "remote_ref_completeness_verified": False,
        "lfs_payloads_scanned": False,
        "redacted_secret_shape_counts": rule_counts,
        "candidate_object_count": sum(rule_counts.values()),
        "requires_private_triage": any(rule_counts.values()),
        "full_security_clearance": "NOT_ESTABLISHED",
        "repository_retirement_ready": False,
        "automatic_removals": 0,
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
