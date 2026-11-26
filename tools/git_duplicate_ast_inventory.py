#!/usr/bin/env python3
"""Reconstruct Grid <-> Unified duplicate function IDs from immutable Git source.

Usage:
  python tools/git_duplicate_ast_inventory.py --grid /path/to/grid.git \
    --unified /path/to/unified-system.git --grid-sha FULL40 \
    --unified-sha FULL40 --output out.json
No imports or execution of subject source. Files come from `git show SHA:path`;
a missing source or commit fails closed. An AST-body match is NOT proof of
runtime behavioral or consumer equivalence. The 2026-11-25 report claims 32
Grid/Unified groups, but its five file families itemize 31, not 32.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

FILES = (
    ("GU-F01", "grid/coordination.py", "unified_system/consul_authority.py", 10),
    ("GU-F02", "grid/coordination_commands.py", "unified_system/consul_command_store.py", 13),
    ("GU-F03", "grid/authority_runtime_v1.py", "unified_system/authority_codec.py", 3),
    ("GU-F04", "grid/authority_assignment_v1.py", "unified_system/research_authority.py", 3),
    ("GU-F05", "grid/ml_windows_job.py", "unified_system/windows_job.py", 2),
)
MIN_NORMALIZED_BYTES = 400
SHA = re.compile(r"[0-9a-f]{40}\Z")


class EvidenceUnavailable(RuntimeError):
    pass


def immutable_git_source(repo, commit, path):
    if not SHA.fullmatch(commit):
        raise EvidenceUnavailable("invalid exact commit SHA")
    repo = Path(repo).resolve(strict=True)
    try:
        resolved = subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "--verify", commit + "^{commit}"],
            stderr=subprocess.DEVNULL, timeout=15).decode().strip()
        if resolved != commit:
            raise EvidenceUnavailable("commit identity mismatch")
        return subprocess.check_output(
            ["git", "-C", str(repo), "show", commit + ":" + path],
            stderr=subprocess.DEVNULL, timeout=30).decode("utf-8")
    except (subprocess.CalledProcessError, UnicodeDecodeError,
            subprocess.TimeoutExpired, OSError) as exc:
        raise EvidenceUnavailable("pinned source unavailable") from exc


def fingerprint_functions(source, path):
    tree = ast.parse(source, filename=path)
    items = []
    def walk(body, parents):
        for node in body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                qualified = ".".join((*parents, node.name))
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Compare bodies, not names or declaration signature.
                    normalized = ast.dump(ast.Module(body=node.body, type_ignores=[]),
                                          include_attributes=False)
                    encoded = normalized.encode("utf-8")
                    if len(encoded) >= MIN_NORMALIZED_BYTES:
                        items.append({"qualname": qualified, "body_sha256": hashlib.sha256(encoded).hexdigest(),
                                      "ast_bytes": len(encoded), "lineno": node.lineno,
                                      "path": path})
                walk(node.body, (*parents, node.name))
            elif isinstance(node, (ast.If, ast.Try, ast.With, ast.For, ast.While, ast.AsyncFor,
                                   ast.AsyncWith, ast.Match)):
                for attr in ("body", "orelse", "finalbody"):
                    walk(getattr(node, attr, []), parents)
                for handler in getattr(node, "handlers", []):
                    walk(handler.body, parents)
                for case in getattr(node, "cases", []):
                    walk(case.body, parents)
    walk(tree.body, ())
    return items


def compare_file_pair(left, right, family):
    by_hash = {}
    for item in right:
        by_hash.setdefault(item["body_sha256"], []).append(item)
    matches = []
    for item in left:
        for candidate in by_hash.get(item["body_sha256"], []):
            digest = item["body_sha256"]
            matches.append({"id": "GU-" + digest[:20], "family_id": family,
                            "body_sha256": digest, "grid": item, "unified": candidate,
                            "semantic_equivalence": "NOT_PROVEN",
                            "consumer_cutover": "NOT_PROVEN",
                            "deletion_authorized": False})
    return sorted(matches, key=lambda item: (item["body_sha256"], item["grid"]["qualname"],
                                              item["unified"]["qualname"]))


def collect(grid, unified, grid_sha, unified_sha):
    rows = []
    families = []
    for family, left, right, historical_count in FILES:
        l = fingerprint_functions(immutable_git_source(grid, grid_sha, left), left)
        r = fingerprint_functions(immutable_git_source(unified, unified_sha, right), right)
        matches = compare_file_pair(l, r, family)
        families.append({"id": family, "grid_path": left, "unified_path": right,
                         "published_count": historical_count, "detected_pairs": len(matches),
                         "published_count_matched": len(matches) == historical_count})
        rows.extend(matches)
    ids = {}
    for row in rows:
        ids.setdefault(row["id"], set()).add(row["body_sha256"])
    if any(len(digests) != 1 for digests in ids.values()):
        raise EvidenceUnavailable("truncated digest ID collision")
    return {"schema": "unified.grid-root-ast-dedup.v1",
            "grid_sha": grid_sha, "unified_sha": unified_sha,
            "historical_claimed_groups": 32, "historical_family_sum": 31,
            "match_pair_count": len(rows), "unique_body_digest_count": len(ids),
            "status": "REVIEW_REQUIRED", "families": families, "matches": rows}


def main(argv=None):
    p = argparse.ArgumentParser()
    for flag in ("grid", "unified", "grid-sha", "unified-sha", "output"):
        p.add_argument("--" + flag, required=True)
    a = p.parse_args(argv)
    out = Path(a.output)
    if out.exists():
        raise SystemExit("REFUSED: output already exists")
    try:
        report = collect(a.grid, a.unified, a.grid_sha, a.unified_sha)
    except (EvidenceUnavailable, SyntaxError, ValueError) as exc:
        raise SystemExit("AST_EVIDENCE_UNAVAILABLE: " + type(exc).__name__) from None
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "pairs": report["match_pair_count"],
                      "unique_bodies": report["unique_body_digest_count"]}))


if __name__ == "__main__":
    main()
