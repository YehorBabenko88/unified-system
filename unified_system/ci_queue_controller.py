"""Bounded offline CI observations; no network, execution, or authority surface.

Captured API data remains unverified evidence even when all pins match.
The existing Journal supplies atomic appends and integrity checking, not authority.
"""
from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
import os
import re
import sqlite3

from .journal import Journal

SCHEMA = 'unified.ci-queue.v1'
MAX_BODY = 262144
STATES = frozenset(('QUEUED', 'RUNNING', 'SUCCESS', 'FAILURE', 'CANCELLED', 'INFRA_BLOCKED', 'UNKNOWN'))
TERMINAL = frozenset(('SUCCESS', 'FAILURE', 'CANCELLED'))
PROTECTED = ('YehorBabenko88/math', 409676563, 42352374979, 1,
    '2446d04624469e34aa96ed766be7a4887d6d654c', 128343065197)


def need(condition):
    if not condition:
        raise ValueError('CI observation rejected')


@dataclass(frozen=True)
class Pin:
    repository: str
    workflow_id: int
    run_id: int
    attempt: int
    source_sha: str
    job_id: int

    def __post_init__(self):
        need(type(self.repository) is str and re.fullmatch(r'[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}', self.repository))
        need(type(self.source_sha) is str and re.fullmatch(r'[0-9a-f]{40}', self.source_sha))
        need(all(type(v) is int and v > 0 for v in (self.workflow_id, self.run_id, self.attempt, self.job_id)))
        if self.run_id == 42352374979:
            need(tuple(asdict(self).values()) == PROTECTED)


def authorization(pin):
    # This immutable local classification records the known historical consumed
    # authorization only for the exact original identity. It grants no operation.
    return 'CONSUMED' if tuple(asdict(pin).values()) == PROTECTED else 'NOT_APPLICABLE'


def timestamp(value):
    if value is None:
        return None
    need(type(value) is str and len(value) <= 40 and value.endswith('Z'))
    try:
        datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError('CI timestamp rejected') from None
    return value


def classify(run, job):
    def state(item):
        status, conclusion = item.get('status'), item.get('conclusion')
        if status == 'queued' and conclusion is None:
            return 'QUEUED'
        if status == 'in_progress' and conclusion is None:
            return 'RUNNING'
        if status == 'completed':
            return {'success':'SUCCESS', 'failure':'FAILURE', 'cancelled':'CANCELLED'}.get(conclusion, 'UNKNOWN')
        return 'UNKNOWN'
    a, b = state(run), state(job)
    # A running workflow may still have a queued job. A completed workflow may
    # not prove an incomplete or conflicting job successful.
    if a == b:
        return a
    return 'QUEUED' if a == 'RUNNING' and b == 'QUEUED' else 'UNKNOWN'


class Controller:
    """Single-writer facade. Each call ingests at most one bounded capture.

    Protected original authorization is permanently CONSUMED; ordinary runs are
    NOT_APPLICABLE. Neither classification grants authority.
    Existing files are only opened explicitly and never implicitly initialized.
    """
    def __init__(self, path, pin):
        need(type(pin) is Pin)
        self.journal, self.pin = Journal(path), pin

    @classmethod
    def create(cls, path, pin, *, limit=16, initial=30, cap=900, seed=0):
        controller = cls(path, pin)
        need(type(limit) is int and 1 <= limit <= 256)
        need(type(initial) is int and type(cap) is int and 1 <= initial <= cap <= 86400)
        need(type(seed) is int and 0 <= seed <= 2**32-1)
        try:
            descriptor = os.open(controller.journal.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            raise ValueError('CI journal already exists; no adoption') from None
        os.close(descriptor)
        # Never delete a partial owned reservation following initialization or
        # append failure. An explicit restart must fail closed on that evidence.
        controller.journal.initialize()
        controller.journal.append('OBSERVING', dict(schema=SCHEMA, kind='IDENTITY', pin=asdict(pin),
            authorization_state=authorization(pin), limit=limit, initial=initial, cap=cap, seed=seed), expected_sequence=0)
        return controller

    @classmethod
    def open(cls, path, pin):
        controller = cls(path, pin)
        controller._records()
        return controller

    def _records(self):
        try:
            need(self.journal.path.is_file() and not self.journal.path.is_symlink())
            need(self.journal.path.stat().st_size <= 8*1024*1024)
            rows = self.journal.read()
            need(1 <= len(rows) <= 257)
            identity = rows[0]['receipt']
            need(set(identity) == {'schema','kind','pin','authorization_state','limit','initial','cap','seed'})
            need(identity['schema'] == SCHEMA and identity['kind'] == 'IDENTITY')
            need(identity['pin'] == asdict(self.pin) and identity['authorization_state'] == authorization(self.pin))
            need(type(identity['limit']) is int and 1 <= identity['limit'] <= 256)
            need(type(identity['initial']) is int and type(identity['cap']) is int and 1 <= identity['initial'] <= identity['cap'] <= 86400)
            need(type(identity['seed']) is int and 0 <= identity['seed'] <= 2**32-1)
            need(len(rows)-1 <= identity['limit'])
            previous = None
            for row in rows:
                need(row['state'] == 'OBSERVING')
            for row in rows[1:]:
                r = row['receipt']
                need(r['schema'] == SCHEMA and r['kind'] == 'OBSERVATION' and r['pin'] == asdict(self.pin))
                need(r['authorization_state'] == authorization(self.pin) and r['state'] in STATES)
                need(type(r['observed_at']) is int and type(r['next_at']) is int and r['next_at'] > r['observed_at'])
                need(previous is None or r['observed_at'] >= previous['next_at'])
                previous = r
            return rows
        except (sqlite3.Error, OSError, KeyError, TypeError, ValueError) as exc:
            raise ValueError('CI journal rejected; no adoption or recovery execution') from exc

    def history(self):
        return [r['receipt'] for r in self._records()[1:]]

    def observe(self, captured, *, now):
        need(type(now) is int and 0 <= now <= 2**53)
        need(type(captured) is bytes and len(captured) <= MAX_BODY)
        rows = self._records()
        identity, history = rows[0]['receipt'], [r['receipt'] for r in rows[1:]]
        need(len(history) < identity['limit'])
        need(not history or now >= history[-1]['next_at'])
        try:
            data = json.loads(captured)
            need(type(data) is dict and set(data) == {'run','job','artifacts'})
            run, job, artifacts = data['run'], data['job'], data['artifacts']
            need(type(run) is dict and type(job) is dict and type(artifacts) is list and len(artifacts) <= 100)
            p = self.pin
            need(all(type(run.get(key)) is int for key in ('id','workflow_id','run_attempt')))
            need(all(type(job.get(key)) is int for key in ('id','run_id','run_attempt')))
            need(run['id'] == p.run_id and run['workflow_id'] == p.workflow_id and run['run_attempt'] == p.attempt)
            need(run['head_sha'] == p.source_sha and run['repository']['full_name'] == p.repository)
            need(job['id'] == p.job_id and job['run_id'] == p.run_id and job['run_attempt'] == p.attempt and job['head_sha'] == p.source_sha)
            state = classify(run, job)
            terminals = {r['state'] for r in history if r['state'] in TERMINAL}
            conflict = any(r['terminal_conflict'] for r in history) or bool(terminals and state not in terminals)
            if conflict or (terminals and state not in terminals):
                state = 'UNKNOWN'
            refs = []
            for artifact in artifacts:
                need(type(artifact) is dict and type(artifact.get('id')) is int and artifact['id'] > 0)
                refs.append({'id':artifact['id']})
            runner = job.get('runner_id')
            need(runner is None or type(runner) is int and runner >= 0)
            conclusion = job.get('conclusion')
            conclusion = conclusion if conclusion in ('success','failure','cancelled','timed_out','neutral','skipped','action_required','stale',None) else 'UNKNOWN'
            delay = min(identity['cap'], identity['initial'] * 2**len(history))
            jitter = int(hashlib.sha256(f"{identity['seed']}:{len(history)}".encode()).hexdigest()[:8],16) % max(1, delay//4+1)
            receipt = dict(schema=SCHEMA, kind='OBSERVATION', pin=asdict(p), state=state,
                terminal_conflict=conflict, authorization_state=authorization(p), data_origin='UNVERIFIED_CAPTURE',
                raw_sha256=hashlib.sha256(captured).hexdigest(), raw_ref='sha256:'+hashlib.sha256(captured).hexdigest(),
                observed_at=now, next_at=now+min(identity['cap'],delay+jitter),
                queue_timestamp=timestamp(run.get('created_at')), runner_assignment=runner,
                runner_assignment_state='UNASSIGNED' if runner in (None,0) else 'ASSIGNED',
                started_timestamp=timestamp(job.get('started_at')), completed_timestamp=timestamp(job.get('completed_at')),
                conclusion=conclusion, artifacts=refs)
        except (ValueError, TypeError, KeyError, RecursionError) as exc:
            raise ValueError('CI capture rejected') from exc
        self.journal.append('OBSERVING', receipt, expected_sequence=len(rows))
        return receipt
