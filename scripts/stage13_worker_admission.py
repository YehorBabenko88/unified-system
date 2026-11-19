"""Opt-in admission for a trusted connector. This module never runs a task."""
from contextlib import closing, contextmanager
from dataclasses import dataclass
import hashlib
import json
import re
import sqlite3

SHA = re.compile(r"[0-9a-f]{40}")
DIGEST = re.compile(r"[0-9a-f]{64}")
IDENTIFIER = re.compile(r"[A-Za-z0-9_-]{1,64}")
PATH = re.compile(r"[a-zA-Z0-9_./-]{1,240}")
FIELDS = {"schema", "id", "lane", "repository", "branch", "head", "manifest_sha256",
          "paths", "test", "expires"}
MAX_TICKETS = 256
MIN_CLAIM_INTERVAL = 60


class AdmissionDenied(ValueError):
    pass


@dataclass(frozen=True)
class WorkerScope:
    lane: str
    owner: str
    worker: str
    repository: str
    branch: str
    paths: frozenset
    tests: frozenset


def ticket_digest(ticket):
    data = json.dumps(ticket, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(data.encode("ascii")).hexdigest()


def safe_path(path):
    return (
        type(path) is str and PATH.fullmatch(path)
        and all(part and part not in (".", "..")
                and not part.startswith(".") and not part.endswith(".")
                for part in path.split("/"))
    )


class WorkerAdmission:
    """One private ledger per connector, with one active claim and no retries.

    Scope, approval, clock and repository state come from trusted callers.
    Keep this ledger in an operator-owned directory outside all checkouts.
    """

    def __init__(self, database, scope, *, enabled=False):
        self.database = database
        self.scope = scope
        self.enabled = enabled is True
        self.scope_digest = ticket_digest({
            "lane": scope.lane, "owner": scope.owner, "worker": scope.worker,
            "repository": scope.repository, "branch": scope.branch,
            "paths": sorted(scope.paths), "tests": sorted(scope.tests),
        })

    @contextmanager
    def transaction(self):
        with closing(sqlite3.connect(self.database, timeout=2)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY "
                       "CHECK(id=1), stopped INTEGER NOT NULL, scope TEXT NOT NULL)")
            db.execute("INSERT OR IGNORE INTO settings VALUES (1, 0, ?)", (self.scope_digest,))
            if db.execute("SELECT scope FROM settings WHERE id=1").fetchone() != (self.scope_digest,):
                raise AdmissionDenied("LEDGER_SCOPE_MISMATCH")
            db.execute("CREATE TABLE IF NOT EXISTS claims (id TEXT PRIMARY KEY, "
                       "digest TEXT NOT NULL UNIQUE, actor TEXT NOT NULL, "
                       "owner TEXT NOT NULL, claimed INTEGER NOT NULL, "
                       "evidence TEXT NOT NULL, outcome TEXT)")
            yield db

    def claim(self, ticket, *, worker, approval, current, now):
        scope = self.scope
        if not self.enabled or worker != scope.worker:
            raise AdmissionDenied("EXECUTOR_DISABLED_OR_UNKNOWN")
        if type(ticket) is not dict or set(ticket) != FIELDS:
            raise AdmissionDenied("INVALID_TICKET")
        if any(type(ticket[key]) is not str for key in FIELDS - {"paths", "expires"}):
            raise AdmissionDenied("INVALID_TICKET")
        paths = ticket["paths"]
        if (
            ticket["schema"] != "unified.worker-ticket.v1"
            or not IDENTIFIER.fullmatch(ticket["id"])
            or not SHA.fullmatch(ticket["head"])
            or not DIGEST.fullmatch(ticket["manifest_sha256"])
            or type(paths) is not list or not 1 <= len(paths) <= 32
            or not all(safe_path(path) for path in paths)
            or len(set(paths)) != len(paths)
            or type(now) is not int or not 0 <= now <= 2**53
            or type(ticket["expires"]) is not int or not now < ticket["expires"] <= now + 900
        ):
            raise AdmissionDenied("INVALID_TICKET")
        if (
            (ticket["lane"], ticket["repository"], ticket["branch"])
            != (scope.lane, scope.repository, scope.branch)
            or not set(paths) <= scope.paths or ticket["test"] not in scope.tests
        ):
            raise AdmissionDenied("OUT_OF_SCOPE")
        digest = ticket_digest(ticket)
        if approval != (scope.owner, digest):
            raise AdmissionDenied("APPROVAL_REQUIRED")
        if current != (scope.repository, scope.branch, ticket["head"], ticket["manifest_sha256"]):
            raise AdmissionDenied("STALE_SOURCE")
        evidence = json.dumps({
            "head": ticket["head"], "manifest_sha256": ticket["manifest_sha256"],
            "paths": paths, "test_digest": hashlib.sha256(ticket["test"].encode()).hexdigest(),
            "repository": scope.repository, "branch": scope.branch,
            "lane": scope.lane, "expires": ticket["expires"],
        }, sort_keys=True)
        with self.transaction() as db:
            if db.execute("SELECT stopped FROM settings").fetchone()[0] != 0:
                raise AdmissionDenied("STOPPED")
            if db.execute("SELECT 1 FROM claims WHERE id=? OR digest=?",
                          (ticket["id"], digest)).fetchone():
                raise AdmissionDenied("REPLAY")
            count, active, last = db.execute(
                "SELECT count(*), count(*) - count(outcome), max(claimed) FROM claims"
            ).fetchone()
            if count >= MAX_TICKETS or active or (last is not None and now - last < MIN_CLAIM_INTERVAL):
                raise AdmissionDenied("QUEUE_LIMIT")
            db.execute("INSERT INTO claims VALUES (?, ?, ?, ?, ?, ?, NULL)",
                       (ticket["id"], digest, worker, scope.owner, now, evidence))
        return digest

    def finish(self, digest, *, worker, outcome):
        if worker != self.scope.worker or outcome not in ("PASS", "FAIL", "STOPPED"):
            raise AdmissionDenied("INVALID_RECEIPT")
        with self.transaction() as db:
            saved = db.execute("SELECT outcome FROM claims WHERE digest=? AND actor=?",
                               (digest, worker)).fetchone()
            if saved is None or saved[0] not in (None, outcome):
                raise AdmissionDenied("INVALID_RECEIPT")
            db.execute("UPDATE claims SET outcome=? WHERE digest=? AND outcome IS NULL",
                       (outcome, digest))

    def stop(self, *, owner):
        if owner != self.scope.owner:
            raise AdmissionDenied("APPROVAL_REQUIRED")
        with self.transaction() as db:
            db.execute("UPDATE settings SET stopped=1 WHERE id=1")
