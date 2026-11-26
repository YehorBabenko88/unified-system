"""Streaming Git secret-pattern triage negative regressions; no network/real credentials."""
import importlib.util
import json
import subprocess
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "tools" / "git_history_secret_triage.py"
spec = importlib.util.spec_from_file_location("git_history_secret_triage", MODULE)
scan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scan)


def test_long_line_spanning_chunks_and_binary_without_echovalues():
    fake = (b"gh" + b"p_" + b"z" * 25)
    payload = b"x" * 3990 + b"\x00" + fake + b"\n" + b"q" * 100
    result = scan.scan_blocks([payload[:3980], payload[3980:4000], payload[4000:]])
    assert result["binary"]
    assert result["line_over_4000"]
    assert result["bytes"] == len(payload)
    assert result["pattern_classes"] == ["github_classic_token"]
    assert fake.decode() not in str(result)


def test_ordinary_multiblock_lines_do_not_trigger_long_line():
    result = scan.scan_blocks([b"a" * 3000, b"b" * 900 + b"\n", b"c" * 3500])
    assert result["line_over_4000"] is False
    assert result["bytes"] == 7401


def test_marker_across_stream_boundary():
    sample = b"-" * 5 + b"BEGIN " + b"PRIVATE KEY" + b"-" * 5
    result = scan.scan_blocks([sample[:12], sample[12:]])
    assert result["pattern_classes"] == ["private_key_pem"]


def test_blob_audit_reports_classes_not_values(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    def git(*args):
        return subprocess.check_output(["git", "-C", str(repo), *args])
    git("init")
    git("config", "user.email", "test@example.invalid")
    git("config", "user.name", "Local Test")
    marker = b"gh" + b"p_" + b"a" * 30
    (repo / "sample.bin").write_bytes(b"\x00" + b"z" * 4099 + marker)
    git("add", ".")
    git("commit", "-m", "test blob")
    result = scan.scan_repository(repo)
    assert result["blobs_scanned"] >= 1
    assert result["binary_blobs"] >= 1
    assert result["long_line_blobs"] >= 1
    assert any("github_classic_token" in x["classes"] for x in result["findings"])
    assert marker.decode() not in json.dumps(result)


def test_invalid_oids_rejected():
    assert scan.exact_oid(b"f" * 40)
    assert scan.exact_oid(b"a" * 64)
    assert not scan.exact_oid(b"bad")
    assert not scan.exact_oid(b"g" * 40)
