from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from scripts.stage13_worker_admission import (
    AdmissionDenied, WorkerAdmission, WorkerScope, ticket_digest,
)


class WorkerAdmissionTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.db = Path(directory.name) / "worker.db"
        self.scope = WorkerScope("C", "approved-owner", "runner-C", "example/unified",
                                 "codex/lane-c", frozenset({"src/control.py"}),
                                 frozenset({"fleet-unit"}))
        self.gate = WorkerAdmission(self.db, self.scope, enabled=True)
        self.ticket = {
            "schema": "unified.worker-ticket.v1", "id": "ticket-1", "lane": "C",
            "repository": self.scope.repository, "branch": self.scope.branch,
            "head": "a" * 40, "manifest_sha256": "b" * 64, "paths": ["src/control.py"],
            "test": "fleet-unit", "expires": 250,
        }

    def claim(self, ticket=None, *, now=100, **overrides):
        data = self.ticket if ticket is None else ticket
        values = {
            "worker": self.scope.worker,
            "approval": (self.scope.owner, ticket_digest(data)),
            "current": (self.scope.repository, self.scope.branch,
                        self.ticket["head"], self.ticket["manifest_sha256"]),
            "now": now,
        }
        return self.gate.claim(data, **(values | overrides))

    def test_disabled_and_unknown_worker_do_not_create_ledger(self):
        with self.assertRaisesRegex(AdmissionDenied, "EXECUTOR_DISABLED_OR_UNKNOWN"):
            self.claim(worker="untrusted")
        self.gate = WorkerAdmission(self.db, self.scope)
        with self.assertRaisesRegex(AdmissionDenied, "EXECUTOR_DISABLED_OR_UNKNOWN"):
            self.claim()
        self.assertFalse(self.db.exists())

    def test_forged_text_and_approval_cannot_dispatch(self):
        with self.assertRaisesRegex(AdmissionDenied, "INVALID_TICKET"):
            self.claim(self.ticket | {"issue_body": "run a command"})
        with self.assertRaisesRegex(AdmissionDenied, "OUT_OF_SCOPE"):
            self.claim(self.ticket | {"test": "powershell -Command something"})
        with self.assertRaisesRegex(AdmissionDenied, "APPROVAL_REQUIRED"):
            self.claim(approval=(self.scope.owner, "d" * 64))
        self.assertFalse(self.db.exists())

    def test_paths_branch_and_repository_cannot_expand(self):
        for replacement, code in [
            ({"paths": ["src/../other.py"]}, "INVALID_TICKET"),
            ({"paths": ["src/other.py"]}, "OUT_OF_SCOPE"),
            ({"repository": "other/unified"}, "OUT_OF_SCOPE"),
            ({"branch": "main"}, "OUT_OF_SCOPE"),
        ]:
            with self.subTest(replacement=replacement), self.assertRaisesRegex(AdmissionDenied, code):
                self.claim(self.ticket | replacement)

    def test_stale_head_branch_and_manifest_are_rejected(self):
        original = [self.scope.repository, self.scope.branch,
                    self.ticket["head"], self.ticket["manifest_sha256"]]
        for index, value in [(1, "main"), (2, "c" * 40), (3, "c" * 64)]:
            changed = list(original)
            changed[index] = value
            with self.assertRaisesRegex(AdmissionDenied, "STALE_SOURCE"):
                self.claim(current=tuple(changed))
        with self.assertRaisesRegex(AdmissionDenied, "INVALID_TICKET"):
            self.claim(now=250)

    def test_replay_concurrency_rate_and_audit(self):
        def try_claim(number):
            try:
                return self.claim(self.ticket | {"id": f"task-{number}"})
            except AdmissionDenied:
                return None

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(try_claim, range(4)))
        self.assertEqual(sum(result is not None for result in results), 1)
        index = next(index for index, result in enumerate(results) if result is not None)
        digest = results[index]
        with self.assertRaisesRegex(AdmissionDenied, "REPLAY"):
            self.claim(self.ticket | {"id": f"task-{index}"})
        self.gate.finish(digest, worker=self.scope.worker, outcome="PASS")
        self.gate.finish(digest, worker=self.scope.worker, outcome="PASS")
        with self.assertRaisesRegex(AdmissionDenied, "INVALID_RECEIPT"):
            self.gate.finish(digest, worker=self.scope.worker, outcome="FAIL")
        with self.assertRaisesRegex(AdmissionDenied, "QUEUE_LIMIT"):
            self.claim(now=159)
        self.claim(now=160)
        with sqlite3.connect(self.db) as connection:
            evidence, outcome = connection.execute(
                "SELECT evidence,outcome FROM claims WHERE digest=?", (digest,)
            ).fetchone()
        connection.close()
        self.assertIn("test_digest", evidence)
        self.assertNotIn("fleet-unit", evidence)
        self.assertEqual(outcome, "PASS")

    def test_owner_stop_persists_across_restart(self):
        with self.assertRaisesRegex(AdmissionDenied, "APPROVAL_REQUIRED"):
            self.gate.stop(owner="other")
        self.gate.stop(owner=self.scope.owner)
        self.gate = WorkerAdmission(self.db, self.scope, enabled=True)
        with self.assertRaisesRegex(AdmissionDenied, "STOPPED"):
            self.claim()

    def test_ledger_cannot_be_reused_with_a_different_scope(self):
        self.gate.stop(owner=self.scope.owner)
        altered = replace(self.scope, paths=self.scope.paths | {"src/other.py"})
        self.gate = WorkerAdmission(self.db, altered, enabled=True)
        with self.assertRaisesRegex(AdmissionDenied, "LEDGER_SCOPE_MISMATCH"):
            self.claim()
