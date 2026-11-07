"""Offline development context journal. Records confer no node authority.

Single local journal; caller protects its directory. No scheduler, execution,
GitHub client, authority issuance, migration, pruning, or repair is provided.
"""
import copy
import re
import sqlite3
from pathlib import Path

from .contracts import ContractError, canonical
from .journal import Journal

MARKER = {"kind": "development-mission", "schema_version": 1}
FIELDS = frozenset(("schema_version", "task_id", "mission_id", "requirements", "owner", "repository",
                    "pr_reference", "base_sha", "allowed_files", "dependencies", "acceptance_tests",
                    "evidence_requirements", "completion_criteria", "next_actions", "blockers", "approvals",
                    "evidence", "ci", "axes"))
IDENTITY = ("task_id", "mission_id", "owner", "repository", "base_sha", "allowed_files")
AXES = frozenset(("source", "tested", "integrated", "windows", "physical"))
STATES = ("UNKNOWN", "PASS", "FAIL", "BLOCKED")
CI_STATES = ("QUEUED", "RUNNING", "SUCCESS", "FAILURE", "CANCELLED", "INFRA_BLOCKED", "UNKNOWN")
MAX_RECORD_BYTES = 65536
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


def _graph(tasks):
    if len(tasks)>MAX_TASKS: raise ContractError("task capacity exceeded")
    # Iterative topological elimination avoids recursion limits on long DAGs.
    pending = {key:set(value["dependencies"]) for key,value in tasks.items()}
    if any(not deps <= tasks.keys() for deps in pending.values()): raise ContractError("unknown dependency")
    while pending:
        leaves={key for key,deps in pending.items() if not deps}
        if not leaves: raise ContractError("dependency cycle")
        pending={key:deps-leaves for key,deps in pending.items() if key not in leaves}


class MissionController:
    """Explicit create/open; journal replay is the only source of task state."""
    def __init__(self, path):
        self._journal = Journal(path)

    @classmethod
    def create(cls, path):
        # Exclusive reservation refuses all existing files, even empty databases.
        try:
            with Path(path).open("xb"):
                pass
        except FileExistsError as exc:
            raise ContractError("refusing existing journal adoption") from exc
        result=cls(path)
        result._journal.initialize()
        result._journal.append("OBSERVING", copy.deepcopy(MARKER), expected_sequence=0)
        return result

    @classmethod
    def open(cls, path):
        result=cls(path)
        result.projection()
        return result

    def _replay(self):
        try:
            records=self._journal.read()
        except (sqlite3.Error, OSError) as exc:
            raise ContractError("unreadable development journal") from exc
        if not records or records[0]["state"] != "OBSERVING" or records[0]["receipt"] != MARKER or type(records[0]["receipt"].get("schema_version")) is not int:
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
        tasks[task["task_id"]]=task
        _graph(tasks)

    def put(self, task, *, expected_sequence):
        task=validate_task(task)
        records,tasks=self._replay()
        if type(expected_sequence) is not int or expected_sequence != len(records):
            raise ContractError("stale development sequence")
        if tasks.get(task["task_id"]) == task: return self.projection()
        self._apply(tasks,task)
        self._journal.append("OBSERVING", dict(kind="development-task",schema_version=1,task=task), expected_sequence=expected_sequence)
        return self.projection()

    def projection(self):
        """Detached internal proposal for Root/UI. Claims remain unverified data."""
        records,tasks=self._replay()
        return dict(schema_version=1, sequence=len(records), tasks=copy.deepcopy(tasks),
                    grants_node_operations=False, native_authority=False)
