"""Offline deterministic regression suite; no network or service tests."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from autonomic_guardian.core import (
    EvidenceError, evaluate, load_snapshot, record_scan, verify_history,
)


NOW = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)
HASH = "a" * 64


def fixture():
    return {
        "schema": "unified.autonomic.snapshot.v1",
        "created_at_utc": "2026-11-18T12:00:00Z",
        "nodes": [{"id": "LS5", "status": "ONLINE", "last_seen_utc": "2026-11-18T12:00:00Z"}],
        "datasets": [{"dataset_id": "fixture", "expected_sha256": HASH, "reported_sha256": HASH,
                      "gap_count": 0, "provenance": "VERIFIED"}],
        "strategies": [{"strategy_id": "wait", "mode": "SIMULATION_ONLY",
                        "contract_valid": True, "test_result": "PASS"}],
        "statistics": [{"series_id": "fixture", "finite": True,
                        "reported_count": 3, "expected_count": 3}],
        "exchanges": [{"venue": "MOCK", "mode": "PUBLIC_DATA_ONLY",
                       "status": "CONNECTED", "rate_limited": False}],
        "workers": [{"worker_id": "worker", "lease_valid": True,
                     "cpu_percent": 15, "memory_percent": 20}],
        "mathematics": [{"check_id": "identity", "result": "PASS",
                         "residual": 0, "tolerance": 0}],
    }


class GuardianTests(unittest.TestCase):
    def test_clean_fixture(self):
        result = evaluate(fixture(), now=NOW)
        self.assertEqual(0, result["incident_count"])
        self.assertEqual(7, len(result["agents_evaluated"]))
        self.assertEqual(0, result["runtime_actions_executed"])

    def test_all_seven_agents_report(self):
        s = fixture()
        s["nodes"][0]["status"] = "OFFLINE"
        s["datasets"][0]["reported_sha256"] = "b" * 64
        s["strategies"][0]["test_result"] = "FAIL"
        s["statistics"][0]["reported_count"] = 2
        s["exchanges"][0]["status"] = "DISCONNECTED"
        s["workers"][0]["lease_valid"] = False
        s["mathematics"][0]["residual"] = 2
        result = evaluate(s, now=NOW)
        self.assertEqual(7, len(set(i["agent"] for i in result["incidents"])))
        self.assertTrue(all(i["action_state"] == "PROPOSAL_ONLY" for i in result["incidents"]))

    def test_no_automatic_repairs(self):
        s = fixture()
        s["datasets"][0]["gap_count"] = 4
        result = evaluate(s, now=NOW)
        self.assertEqual(0, result["runtime_actions_executed"])
        self.assertEqual(0, result["provider_requests_executed"])

    def test_stale_snapshot(self):
        s = fixture()
        s["created_at_utc"] = "2026-11-18T11:00:00Z"
        self.assertEqual("STALE", evaluate(s, now=NOW)["snapshot_freshness"])

    def test_missing_source_not_healthy(self):
        s = fixture()
        del s["workers"]
        incidents = evaluate(s, now=NOW)["incidents"]
        self.assertTrue(any(i["code"] == "SOURCE_MISSING" and i["agent"] == "load" for i in incidents))

    def test_duplicate_identity_denied(self):
        s = fixture()
        s["nodes"].append(dict(s["nodes"][0]))
        with self.assertRaises(EvidenceError):
            evaluate(s, now=NOW)

    def test_naive_time_denied(self):
        s = fixture()
        s["created_at_utc"] = "2026-11-18T12:00:00"
        with self.assertRaises(EvidenceError):
            evaluate(s, now=NOW)

    def test_bad_numeric_denied(self):
        s = fixture()
        s["workers"][0]["cpu_percent"] = float("nan")
        with self.assertRaises(EvidenceError):
            evaluate(s, now=NOW)

    def test_journal_chain_and_mutation_detection(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "guard.sqlite"
            r = evaluate(fixture(), now=NOW)
            self.assertEqual(1, record_scan(p, r))
            self.assertEqual(2, record_scan(p, r))
            self.assertTrue(verify_history(p))
            import sqlite3
            with sqlite3.connect(p) as db:
                db.execute("UPDATE scans SET report_json='tampered' WHERE seq=1")
            self.assertFalse(verify_history(p))

    def test_bounded_load_and_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "snapshot.json"
            p.write_text('{"schema":"a","schema":"b"}', encoding="utf-8")
            with self.assertRaises(EvidenceError):
                load_snapshot(p)
            p.write_bytes(b"x" * 1_048_577)
            with self.assertRaises(EvidenceError):
                load_snapshot(p)

    def test_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "snapshot.json"
            p.write_text(json.dumps(fixture()), encoding="utf-8")
            loaded, sha = load_snapshot(p)
            self.assertEqual(fixture(), loaded)
            self.assertEqual(64, len(sha))

    def test_repeatable_incident_ids(self):
        s = fixture()
        s["strategies"][0]["mode"] = "LIVE"
        r1 = evaluate(s, now=NOW)
        r2 = evaluate(s, now=NOW)
        self.assertEqual(r1, r2)
        self.assertTrue(any(i["code"] == "UNSAFE_STRATEGY_MODE" for i in r1["incidents"]))


if __name__ == "__main__":
    unittest.main()
