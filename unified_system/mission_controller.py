"""Offline development context journal. Records confer no node authority.

Single local journal; caller protects its directory. No scheduler, execution,
GitHub client, authority issuance, migration, pruning, or repair is provided.
"""
import copy
import json
import re
import sqlite3
import stat
from contextlib import closing
from pathlib import Path

from .contracts import ContractError, canonical
from .journal import Journal

DEFAULT_MAX_BYTES = 16*1024*1024
DEFAULT_MAX_RECORDS = 1024
HARD_MAX_BYTES = 64*1024*1024
HARD_MAX_RECORDS = 100000
MARKER_VERSION = 2
FIELDS = frozenset(("schema_version", "task_id", "mission_id", "requirements", "owner", "repository",
                    "pr_reference", "base_sha", "allowed_files", "dependencies", "acceptance_tests",
                    "evidence_requirements", "completion_criteria", "next_actions", "blockers", "approvals",
                    "evidence", "ci", "axes"))
IDENTITY = ("task_id", "mission_id", "owner", "repository", "base_sha", "allowed_files")
AXES = frozenset(("source", "tested", "integrated", "windows", "physical"))
STATES = ("UNKNOWN", "PASS", "FAIL", "BLOCKED")
CI_STATES = ("QUEUED", "RUNNING", "SUCCESS", "FAILURE", "CANCELLED", "INFRA_BLOCKED", "UNKNOWN")
MAX_RECORD_BYTES = 65536
MAX_RECEIPT_BYTES = MAX_RECORD_BYTES+128
MAX_TASKS = 1024


def _text(value, limit=2048):
    if type(value) is not str or not 1 <= len(value) <= limit or value != value.strip() or any(ord(c)<32 for c in value):
        raise ContractError("invalid bounded text")


def _match(value, pattern):
    if type(value) is not str or re.fullmatch(pattern, value) is None:
        raise ContractError("invalid canonical identifier")


def _identifier(value):
    _match(value, r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")


def _items(value):
    if type(value) is not list or len(value)>128:
        raise ContractError("invalid bounded list")
    return value


def _closed(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        raise ContractError("invalid closed fields")


def validate_task(value):
    """Validate one closed versioned task; return an independent canonical copy."""
    _closed(value, FIELDS)
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise ContractError("unknown development task schema")
    for key in ("task_id", "mission_id", "owner"): _identifier(value[key])
    _match(value["repository"], r"[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}")
    _match(value["pr_reference"], re.escape(value["repository"])+r"#[1-9][0-9]{0,9}")
    _match(value["base_sha"], r"[0-9a-f]{40}")
    for key in ("requirements", "acceptance_tests", "evidence_requirements", "completion_criteria", "next_actions", "blockers"):
        for entry in _items(value[key]): _text(entry)
    for key in ("requirements", "acceptance_tests", "evidence_requirements", "completion_criteria", "allowed_files"):
        if not value[key]: raise ContractError("required list empty")
    for entry in _items(value["allowed_files"]):
        _text(entry, 256)
        if entry.startswith("/") or "\\" in entry or ":" in entry or any(p in ("", ".", "..") for p in entry.split("/")):
            raise ContractError("invalid repository relative file")
    for entry in _items(value["dependencies"]): _identifier(entry)
    for key in ("dependencies", "allowed_files"):
        if len(set(value[key])) != len(value[key]): raise ContractError("duplicate list identity")
    _closed(value["axes"], AXES)
    if any(type(s) is not str or s not in STATES for s in value["axes"].values()):
        raise ContractError("invalid observation axis")
    for entry in _items(value["approvals"]):
        _closed(entry, ("reference", "approved")); _text(entry["reference"])
        if type(entry["approved"]) is not bool: raise ContractError("invalid approval observation")
    for entry in _items(value["evidence"]):
        _closed(entry, ("reference", "sha256")); _text(entry["reference"])
        _match(entry["sha256"], r"[0-9a-f]{64}")
    for entry in _items(value["ci"]):
        _closed(entry, ("workflow_id", "run_id", "attempt", "job_id", "source_sha", "state", "artifact_references", "authorization_state"))
        _identifier(entry["workflow_id"])
        for key in ("run_id", "attempt", "job_id"):
            if type(entry[key]) is not int or not 1 <= entry[key] <= 2**63-1: raise ContractError("invalid CI identity")
        _match(entry["source_sha"], r"[0-9a-f]{40}")
        if type(entry["state"]) is not str or entry["state"] not in CI_STATES: raise ContractError("invalid CI observation")
        if entry["authorization_state"] not in ("UNKNOWN", "RECORDED", "CONSUMED", "REVOKED"): raise ContractError("invalid authorization observation")
        for ref in _items(entry["artifact_references"]): _text(ref)
    if len(canonical(value)) > MAX_RECORD_BYTES: raise ContractError("task byte capacity exceeded")
    return copy.deepcopy(value)


def _bounds(max_bytes, max_records):
    if type(max_bytes) is not int or not 1024*1024 <= max_bytes <= HARD_MAX_BYTES:
        raise ContractError("invalid byte capacity")
    if type(max_records) is not int or not 2 <= max_records <= HARD_MAX_RECORDS:
        raise ContractError("invalid record capacity")


def _safe_path(path, *, absent=False):
    path=Path(path)
    try:
        if not path.is_absolute() or path.anchor.startswith("\\\\") or path != path.resolve():
            raise ContractError("journal requires canonical absolute local path")
        for parent in path.parents:
            info=parent.lstat()
            if not stat.S_ISDIR(info.st_mode) or parent.is_symlink() or getattr(info,"st_file_attributes",0)&1024:
                raise ContractError("unsafe journal parent")
        if not absent:
            info=path.lstat()
            if not stat.S_ISREG(info.st_mode) or path.is_symlink() or getattr(info,"st_file_attributes",0)&1024 or info.st_nlink != 1:
                raise ContractError("unsafe journal file")
    except (OSError,RuntimeError) as exc:
        raise ContractError("unavailable journal path") from exc
    return path


class MissionController:
    """Explicit create/open; journal replay is the only source of task state."""
    def __init__(self, path):
        self._journal = Journal(_safe_path(path))

    @classmethod
    def create(cls, path, *, max_bytes=DEFAULT_MAX_BYTES, max_records=DEFAULT_MAX_RECORDS):
        _bounds(max_bytes,max_records)
        path=_safe_path(path,absent=True)
        if any(Path(str(path)+suffix).exists() or Path(str(path)+suffix).is_symlink() for suffix in ("-wal","-shm","-journal")):
            raise ContractError("refusing orphan journal sidecar adoption")
        # Exclusive reservation refuses all existing files, even empty databases.
        try:
            with Path(path).open("xb"):
                pass
        except FileExistsError as exc:
            raise ContractError("refusing existing journal adoption") from exc
        result=cls(path)
        result._journal.initialize()
        result._journal.append("OBSERVING", dict(kind="development-mission",schema_version=MARKER_VERSION,max_bytes=max_bytes,max_records=max_records), expected_sequence=0)
        return result

    @classmethod
    def open(cls, path):
        result=cls(path)
        result.projection()
        return result

    def _preflight(self):
        path=_safe_path(self._journal.path)
        size=path.stat().st_size
        for suffix in ("-wal","-shm","-journal"):
            sidecar=Path(str(path)+suffix)
            if sidecar.exists() or sidecar.is_symlink():
                _safe_path(sidecar)
                if suffix != "-journal": raise ContractError("unsupported WAL journal")
                size+=sidecar.stat().st_size
        if size>HARD_MAX_BYTES: raise ContractError("journal byte capacity exceeded")
        try:
            with closing(sqlite3.connect(path.as_uri()+"?mode=ro",uri=True,timeout=5)) as db:
                # Refuse foreign tables/views/triggers before selecting their data.
                objects=db.execute("SELECT type,name,sql FROM sqlite_master LIMIT 3").fetchall()
                expected="CREATE TABLE transitions (sequence INTEGER PRIMARY KEY, state TEXT NOT NULL, receipt TEXT, previous_hash TEXT NOT NULL, digest TEXT NOT NULL)"
                if objects != [("table","transitions",expected)]:
                    raise ContractError("foreign journal schema")
                count,total,payload,other=db.execute("SELECT COUNT(*),COALESCE(SUM(length(CAST(receipt AS BLOB))),0),COALESCE(MAX(length(CAST(receipt AS BLOB))),0),COALESCE(MAX(MAX(length(CAST(state AS BLOB)),length(CAST(previous_hash AS BLOB)),length(CAST(digest AS BLOB)))),0) FROM transitions").fetchone()
                if count>HARD_MAX_RECORDS or total>HARD_MAX_BYTES or payload>MAX_RECEIPT_BYTES or other>128:
                    raise ContractError("journal preflight capacity exceeded")
                row=db.execute("SELECT state,receipt FROM transitions WHERE sequence=1").fetchone()
                if row is None or row[0] != "OBSERVING" or type(row[1]) is not str or len(row[1])>1024:
                    raise ContractError("missing development marker")
                marker=json.loads(row[1])
                _closed(marker,("kind","schema_version","max_bytes","max_records"))
                if marker["kind"] != "development-mission" or type(marker["schema_version"]) is not int or marker["schema_version"] != MARKER_VERSION:
                    raise ContractError("unsupported development marker; migration unavailable")
                _bounds(marker["max_bytes"],marker["max_records"])
                if size>marker["max_bytes"] or total>marker["max_bytes"] or count>marker["max_records"]:
                    raise ContractError("persisted journal capacity exceeded")
        except (sqlite3.Error,OSError,ValueError,RecursionError) as exc:
            if isinstance(exc,ContractError): raise
            raise ContractError("unreadable bounded development journal") from exc
        return marker,size,count

    def _replay(self):
        marker,_,_=self._preflight()
        try:
            records=self._journal.read()
        except (sqlite3.Error, OSError, RecursionError) as exc:
            raise ContractError("unreadable development journal") from exc
        if not records or records[0]["state"] != "OBSERVING" or records[0]["receipt"] != marker:
            raise ContractError("missing or incompatible development marker")
        tasks={}
        for record in records[1:]:
            receipt=record["receipt"]
            if record["state"] != "OBSERVING": raise ContractError("unexpected development state")
            _closed(receipt, ("kind", "schema_version", "task"))
            if receipt["kind"] != "development-task" or type(receipt["schema_version"]) is not int or receipt["schema_version"] != 1:
                raise ContractError("unknown receipt schema")
            task=validate_task(receipt["task"])
            self._apply(tasks, task)
        return records,tasks

    @staticmethod
    def _apply(tasks, task):
        old=tasks.get(task["task_id"])
        if old is not None and any(old[key] != task[key] for key in IDENTITY):
            raise ContractError("immutable development identity collision")
        if any(dep not in tasks for dep in task["dependencies"]): raise ContractError("unknown dependency")
        if old is None and len(tasks)>=MAX_TASKS: raise ContractError("task capacity exceeded")
        # A new identity cannot be reachable in the already validated DAG.
        # Only revisions need a linear reachable-subgraph cycle check.
        if old is not None:
            pending=list(task["dependencies"]);seen=set()
            while pending:
                current=pending.pop()
                if current == task["task_id"]: raise ContractError("dependency cycle")
                if current not in seen:
                    seen.add(current);pending.extend(tasks[current]["dependencies"])
        tasks[task["task_id"]]=task

    def put(self, task, *, expected_sequence):
        task=validate_task(task)
        records,tasks=self._replay()
        if type(expected_sequence) is not int or expected_sequence != len(records):
            raise ContractError("stale development sequence")
        if tasks.get(task["task_id"]) == task: return self.projection()
        self._apply(tasks,task)
        receipt=dict(kind="development-task",schema_version=1,task=task)
        marker,size,count=self._preflight()
        # Reserve overflow pages, table growth and journal bookkeeping. This is
        # a conservative refusal, not a connection-local SQLite page-cap claim.
        reserve=2*len(canonical(receipt))+65536
        if count>=marker["max_records"] or size+reserve>marker["max_bytes"]:
            raise ContractError("journal append capacity reserve exceeded")
        self._journal.append("OBSERVING", receipt, expected_sequence=expected_sequence)
        return self.projection()

    def projection(self):
        """Detached internal proposal for Root/UI. Claims remain unverified data."""
        records,tasks=self._replay()
        return dict(schema_version=1, sequence=len(records), tasks=copy.deepcopy(tasks),
                    grants_node_operations=False, native_authority=False)
