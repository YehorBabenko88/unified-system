"""Seven deterministic offline diagnostic agents.

No subprocess, sockets, SSH, provider requests, code mutation or remediation
execution is present. Input is a bounded, operator-provided observation JSON.
A reported observation is not a physical probe or authenticated measurement.
"""
from __future__ import annotations

import hashlib
import json
import math
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Any

SCHEMA = "unified.autonomic.snapshot.v1"
ROLES = (
    "infrastructure", "data_integrity", "strategy", "statistics",
    "exchange", "load", "mathematics",
)
SOURCES = {
    "infrastructure": "nodes",
    "data_integrity": "datasets",
    "strategy": "strategies",
    "statistics": "statistics",
    "exchange": "exchanges",
    "load": "workers",
    "mathematics": "mathematics",
}
MAX_SNAPSHOT_BYTES = 1_048_576
MAX_ITEMS_PER_SOURCE = 500
ZERO = "0" * 64


class EvidenceError(ValueError):
    """An observation is malformed or cannot support a decision."""


def _unique_object(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise EvidenceError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise EvidenceError(f"non-finite JSON literal: {value}")


def _time(value: Any, name: str) -> datetime:
    if not isinstance(value, str):
        raise EvidenceError(f"{name} must be an ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError(f"invalid {name}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EvidenceError(f"naive {name}")
    return parsed.astimezone(timezone.utc)


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvidenceError(f"{name} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise EvidenceError(f"non-finite {name}")
    return result


def _bool(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise EvidenceError(f"{name} must be a boolean")
    return value


def load_snapshot(path: str | Path) -> tuple[dict[str, Any], str]:
    """Read one bounded JSON snapshot. Does NOT inspect the real environment."""
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise EvidenceError("snapshot must be an ordinary file")
    if source.stat().st_size > MAX_SNAPSHOT_BYTES:
        raise EvidenceError("snapshot exceeds size cap")
    payload = source.read_bytes()
    if len(payload) > MAX_SNAPSHOT_BYTES:
        raise EvidenceError("snapshot exceeds size cap")
    try:
        snapshot = json.loads(
            payload.decode("utf-8"), object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError("invalid snapshot JSON") from exc
    if not isinstance(snapshot, dict) or snapshot.get("schema") != SCHEMA:
        raise EvidenceError("unsupported snapshot schema")
    return snapshot, hashlib.sha256(payload).hexdigest()


def evaluate(
    snapshot: dict[str, Any], *,
    now: datetime | None = None, source_sha256: str = "UNVERIFIED",
) -> dict[str, Any]:
    """Run seven independent diagnostic policies with zero side effects."""
    if not isinstance(snapshot, dict) or snapshot.get("schema") != SCHEMA:
        raise EvidenceError("unsupported snapshot schema")
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise EvidenceError("now must be timezone aware")
    current = current.astimezone(timezone.utc)
    observed = _time(snapshot.get("created_at_utc"), "created_at_utc")
    problems: list[dict[str, str]] = []

    def emit(role: str, subject: str, code: str, severity: str, recommendation: str) -> None:
        subject = str(subject)[:128]
        token = "\\x00".join((role, subject, code))
        issue_id = hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]
        problems.append({
            "incident_id": issue_id, "agent": role, "subject": subject,
            "code": code, "severity": severity,
            "recommendation": recommendation, "action_state": "PROPOSAL_ONLY",
        })

    age = (current - observed).total_seconds()
    stale = age > 120 or age < -30
    if stale:
        emit("infrastructure", "snapshot", "SNAPSHOT_STALE", "ERROR",
             "Obtain a fresh approved observation; do not perform recovery from stale evidence")

    for role in ROLES:
        key = SOURCES[role]
        if key not in snapshot:
            emit(role, key, "SOURCE_MISSING", "ERROR",
                 "Obtain an approved observation; status must remain UNKNOWN")
            continue
        values = snapshot[key]
        if not isinstance(values, list) or len(values) > MAX_ITEMS_PER_SOURCE:
            raise EvidenceError(f"{key} must be a bounded list")
        seen: set[str] = set()
        for idx, item in enumerate(values):
            if not isinstance(item, dict):
                raise EvidenceError(f"{key}[{idx}] must be an object")
            subject_key = {
                "nodes": "id", "datasets": "dataset_id",
                "strategies": "strategy_id", "statistics": "series_id",
                "exchanges": "venue", "workers": "worker_id",
                "mathematics": "check_id",
            }[key]
            subject = item.get(subject_key)
            if not isinstance(subject, str) or not subject or len(subject) > 128:
                raise EvidenceError(f"{key}[{idx}].{subject_key} invalid")
            if subject in seen:
                raise EvidenceError(f"duplicate {key} identity")
            seen.add(subject)

            if role == "infrastructure":
                status = item.get("status", "UNKNOWN")
                if status not in ("ONLINE", "OFFLINE", "UNKNOWN"):
                    raise EvidenceError("invalid node status")
                if status != "ONLINE":
                    emit(role, subject, "NODE_" + status, "ERROR",
                         "Investigate approved LAN/SSH path; do not change host access policies")
                elif "last_seen_utc" in item and (current - _time(item["last_seen_utc"], "last_seen_utc")).total_seconds() > 120:
                    emit(role, subject, "NODE_HEARTBEAT_STALE", "WARN",
                         "Request a new heartbeat before declaring node healthy")

            elif role == "data_integrity":
                expected = item.get("expected_sha256")
                actual = item.get("reported_sha256")
                if not isinstance(expected, str) or not isinstance(actual, str) or any(
                    len(d) != 64 or any(c not in "0123456789abcdef" for c in d)
                    for d in (expected, actual)
                ):
                    emit(role, subject, "HASH_EVIDENCE_MISSING", "ERROR",
                         "Request immutable source readback and owner authentication")
                elif expected != actual:
                    emit(role, subject, "REPORTED_HASH_MISMATCH", "CRITICAL",
                         "Fence the affected dataset candidate; request independent readback, never rewrite raw")
                if _number(item.get("gap_count", 0), "gap_count") > 0:
                    emit(role, subject, "REPORTED_GAPS", "ERROR",
                         "Request bounded gap audit/backfill proposal; do not invent missing data")
                if item.get("provenance", "UNKNOWN") != "VERIFIED":
                    emit(role, subject, "PROVENANCE_UNVERIFIED", "WARN",
                         "Keep dataset out of training admission")

            elif role == "strategy":
                if item.get("mode") != "SIMULATION_ONLY":
                    emit(role, subject, "UNSAFE_STRATEGY_MODE", "CRITICAL",
                         "Reject candidate before execution; real orders are prohibited")
                if not _bool(item.get("contract_valid", False), "contract_valid"):
                    emit(role, subject, "STRATEGY_CONTRACT_FAIL", "ERROR",
                         "Keep test candidate inactive; produce a versioned repair proposal")
                if item.get("test_result") == "FAIL":
                    emit(role, subject, "STRATEGY_TEST_FAIL", "ERROR",
                         "Retain failed evidence and use existing isolated simulator for regression")

            elif role == "statistics":
                if not _bool(item.get("finite", False), "finite"):
                    emit(role, subject, "NONFINITE_STATISTICS", "ERROR",
                         "Recompute derived metrics offline from immutable admitted inputs")
                reported = _number(item.get("reported_count", -1), "reported_count")
                expected = _number(item.get("expected_count", -1), "expected_count")
                if reported < 0 or expected < 0 or reported != expected:
                    emit(role, subject, "STATISTICS_COUNT_MISMATCH", "WARN",
                         "Request lineage-bound recomputation; never alter source records")

            elif role == "exchange":
                if item.get("mode") != "PUBLIC_DATA_ONLY":
                    emit(role, subject, "EXCHANGE_PROFILE_INVALID", "CRITICAL",
                         "Keep provider permissions DENY; do not send requests")
                if item.get("status", "UNKNOWN") != "CONNECTED":
                    emit(role, subject, "EXCHANGE_DISCONNECTED_OR_UNKNOWN", "ERROR",
                         "Propose approved bounded reconnect; never renew provider grants")
                if _bool(item.get("rate_limited", False), "rate_limited"):
                    emit(role, subject, "RATE_LIMIT_OBSERVED", "WARN",
                         "Honor documented cooldown; never issue blind retries")

            elif role == "load":
                if not _bool(item.get("lease_valid", False), "lease_valid"):
                    emit(role, subject, "WORKER_LEASE_INVALID", "CRITICAL",
                         "Fence this worker's new jobs; request Scheduler owner reconciliation")
                cpu = _number(item.get("cpu_percent", -1), "cpu_percent")
                memory = _number(item.get("memory_percent", -1), "memory_percent")
                if not (0 <= cpu <= 100 and 0 <= memory <= 100):
                    emit(role, subject, "WORKER_RESOURCE_UNKNOWN", "ERROR",
                         "Request accurate bounded resource sampling")
                elif cpu > 90 or memory > 90:
                    emit(role, subject, "WORKER_PRESSURE", "WARN",
                         "Propose bounded rebalance via existing Scheduler; never migrate jobs directly")

            elif role == "mathematics":
                result = item.get("result", "UNKNOWN")
                if result != "PASS":
                    emit(role, subject, "MATH_CHECK_" + str(result)[:32], "ERROR",
                         "Preserve counterexample; request Math owner review, no auto-proof claim")
                residual = _number(item.get("residual", -1), "residual")
                tolerance = _number(item.get("tolerance", -1), "tolerance")
                if residual < 0 or tolerance < 0 or residual > tolerance:
                    emit(role, subject, "MATH_NUMERIC_REGRESSION", "ERROR",
                         "Preserve numerical evidence and propose regression test")

    problems.sort(key=lambda p: (p["agent"], p["subject"], p["code"]))
    return {
        "schema": "unified.autonomic.scan.v1",
        "observed_at_utc": current.isoformat(),
        "snapshot_at_utc": observed.isoformat(),
        "snapshot_freshness": "STALE" if stale else "CURRENT_OBSERVATION_ONLY",
        "snapshot_sha256": source_sha256,
        "mode": "OFFLINE_PROPOSAL_ONLY",
        "agents_evaluated": list(ROLES),
        "incident_count": len(problems),
        "incidents": problems,
        "runtime_actions_executed": 0,
        "provider_requests_executed": 0,
    }


def _serialized(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def record_scan(db_path: str | Path, report: dict[str, Any]) -> int:
    """Append report with an internal SHA chain; no external authentication claim."""
    target = Path(db_path)
    if target.is_symlink():
        raise EvidenceError("journal path must not be a symlink")
    target.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(target, timeout=3)) as db, db:
        db.execute("PRAGMA busy_timeout=3000")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("CREATE TABLE IF NOT EXISTS scans ("
                   "seq INTEGER PRIMARY KEY, previous_sha TEXT NOT NULL,"
                   "record_sha TEXT NOT NULL, report_json TEXT NOT NULL)")
        db.execute("BEGIN IMMEDIATE")
        prev = db.execute("SELECT record_sha FROM scans ORDER BY seq DESC LIMIT 1").fetchone()
        previous = prev[0] if prev else ZERO
        payload = _serialized(report)
        digest = hashlib.sha256((previous + payload).encode("utf-8")).hexdigest()
        cursor = db.execute(
            "INSERT INTO scans(previous_sha,record_sha,report_json) VALUES (?,?,?)",
            (previous, digest, payload),
        )
        return int(cursor.lastrowid)


def verify_history(db_path: str | Path) -> bool:
    """Detect internal record corruption. Not a signed/tamper-proof ledger."""
    with closing(sqlite3.connect(f"file:{Path(db_path).resolve().as_posix()}?mode=ro", uri=True)) as db:
        previous = ZERO
        for prior, digest, payload in db.execute(
            "SELECT previous_sha,record_sha,report_json FROM scans ORDER BY seq"
        ):
            if prior != previous or hashlib.sha256((prior + payload).encode("utf-8")).hexdigest() != digest:
                return False
            previous = digest
    return True
