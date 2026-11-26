#!/usr/bin/env python3
"""Historical Git object secret-pattern triage without printing matched values.

Run from a full mirror (all branches and pull refs fetched) as:
python tools/git_history_secret_triage.py --repo PATH --output findings.json

Checks *every reachable blob byte*, including binaries, long lines and blob data
that cross buffer boundaries. Token-pattern detection is heuristic: a clean scan
never proves absence of credentials, and nested/encoded archives need additional
specialized scanners. No credentials or matched substrings are emitted.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

BUFFER = 65536
OVERLAP = 512
PATTERNS = {
    "private_key_pem": re.compile(rb"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"),
    "github_classic_token": re.compile(rb"gh[pousr]_[A-Za-z0-9_]{20,}"),
    "github_fine_grained_token": re.compile(rb"github_pat_[A-Za-z0-9_]{20,}"),
    "aws_access_key_id": re.compile(rb"(?:AKIA|ASIA)[A-Z0-9]{16}"),
}


class ScanUnavailable(RuntimeError):
    pass


def scan_blocks(blocks):
    """Return classes and sizes; raw values are never returned."""
    total = 0
    binary = False
    line_length = 0
    maximum_line = 0
    classes = set()
    trailing = b""
    for block in blocks:
        total += len(block)
        if b"\x00" in block:
            binary = True
        segments = block.split(b"\n")
        for segment in segments[:-1]:
            line_length += len(segment)
            maximum_line = max(maximum_line, line_length)
            line_length = 0
        line_length += len(segments[-1])
        maximum_line = max(maximum_line, line_length)
        window = trailing + block
        for kind, expression in PATTERNS.items():
            if expression.search(window):
                classes.add(kind)
        trailing = window[-OVERLAP:]
    return {"bytes": total, "binary": binary,
            "line_over_4000": maximum_line > 4000,
            "pattern_classes": sorted(classes)}


def exact_oid(value):
    return len(value) in (40, 64) and bool(re.fullmatch(rb"[0-9a-f]+", value))


def object_oids(repo):
    result = subprocess.run(["git", "-C", str(repo), "rev-list", "--objects", "--all"],
                            capture_output=True, check=True)
    oids = set()
    for line in result.stdout.splitlines():
        candidate = line.partition(b" ")[0]
        if not exact_oid(candidate):
            raise ScanUnavailable("invalid object identifier")
        oids.add(candidate)
    if not oids:
        raise ScanUnavailable("empty Git history")
    return sorted(oids)


def scan_repository(repo):
    repo = Path(repo).resolve(strict=True)
    oids = object_oids(repo)
    report = {"schema_version": 1, "scope": "git rev-list --objects --all",
              "reachable_objects": len(oids), "blobs_scanned": 0,
              "binary_blobs": 0, "long_line_blobs": 0,
              "bytes_scanned": 0, "findings": []}
    with subprocess.Popen(["git", "-C", str(repo), "cat-file", "--batch"],
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL) as process:
        for oid in oids:
            process.stdin.write(oid + b"\n")
            process.stdin.flush()
            header = process.stdout.readline().strip().split()
            if len(header) != 3 or header[0] != oid or not header[2].isdigit():
                raise ScanUnavailable("invalid cat-file response")
            kind, length = header[1], int(header[2])
            remaining = length
            def blocks():
                nonlocal remaining
                while remaining:
                    block = process.stdout.read(min(BUFFER, remaining))
                    if not block:
                        raise ScanUnavailable("truncated Git object")
                    remaining -= len(block)
                    yield block
            if kind == b"blob":
                observation = scan_blocks(blocks())
                if observation["bytes"] != length:
                    raise ScanUnavailable("incomplete blob")
                report["blobs_scanned"] += 1
                report["bytes_scanned"] += length
                report["binary_blobs"] += int(observation["binary"])
                report["long_line_blobs"] += int(observation["line_over_4000"])
                if observation["pattern_classes"]:
                    report["findings"].append({"blob_oid": oid.decode("ascii"),
                                               "classes": observation["pattern_classes"]})
            else:
                for _ in blocks():
                    pass
            if process.stdout.read(1) != b"\n":
                raise ScanUnavailable("malformed cat-file boundary")
        process.stdin.close()
        if process.wait() != 0:
            raise ScanUnavailable("git cat-file failed")
    return report


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args(argv)
    output = Path(a.output)
    if output.exists():
        raise SystemExit("REFUSED: output exists")
    try:
        report = scan_repository(a.repo)
    except (subprocess.CalledProcessError, OSError, ScanUnavailable) as exc:
        raise SystemExit(f"SCAN_INCOMPLETE: {type(exc).__name__}") from None
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PATTERN_TRIAGE_COMPLETE_NOT_SECRET_FREE",
                      "blobs": report["blobs_scanned"],
                      "findings_count": len(report["findings"])}))


if __name__ == "__main__":
    main()
