"""Local preparation journal only; never authority or worker dispatch.

SQLite serializes this file's provisional holds, not cluster capacity or leases.
Every returned view has execution_authorized=False. No network calls exist.
"""
from contextlib import contextmanager
from dataclasses import asdict, replace
import json
import re
import sqlite3
import uuid

from .placement import Resources, place

_SCOPE_KEYS = {'cluster_id', 'cluster_generation', 'job_id', 'dataset_id', 'source_id', 'partition_id'}
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z')
_HELD = ('PREPARED', 'SEALED', 'UNKNOWN')


def _identifier(value):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError('explicit opaque registry identifier required')
    return value


def _scope(scope):
    if not isinstance(scope, dict) or set(scope) != _SCOPE_KEYS:
        raise ValueError('exact local scope binding required')
    return json.dumps({k: _identifier(v) for k, v in scope.items()}, sort_keys=True, separators=(',', ':'))


def _spec(resources, benchmark_id, data):
    if not isinstance(resources, Resources):
        raise ValueError('typed resources required')
    values = asdict(resources)
    if any(type(v) is not int or not 0 <= v <= 9223372036854775807 for v in values.values()) or not any(values.values()):
        raise ValueError('nonempty nonnegative u63 resource vector required')
    if not isinstance(data, frozenset):
        raise ValueError('immutable data identities required')
    return json.dumps(dict(resources=values, benchmark_id=_identifier(benchmark_id),
                           data=sorted(_identifier(x) for x in data)), sort_keys=True, separators=(',', ':'))


class IntentConflict(ValueError):
    pass

class ReconciliationRequired(RuntimeError):
    pass

class PreparationJournal:
    def __init__(self, path):
        self._db = sqlite3.connect(path, timeout=5, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        self._db.execute('PRAGMA synchronous=FULL')
        version = self._db.execute('PRAGMA user_version').fetchone()[0]
        if version not in (0, 1):
            self.close()
            raise ValueError('unsupported journal version')
        self._db.executescript('''
            CREATE TABLE IF NOT EXISTS jobs (
                scope TEXT PRIMARY KEY, spec TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('QUEUED','PREPARED','SEALED','UNKNOWN','CANCELLED')),
                request_id TEXT UNIQUE, local_hold_id TEXT UNIQUE,
                node_id TEXT, incarnation TEXT, reason TEXT);
            CREATE TABLE IF NOT EXISTS events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                scope TEXT NOT NULL, kind TEXT NOT NULL);
            PRAGMA user_version=1;
        ''')

    def close(self):
        if self._db is not None:
            self._db.close()
            self._db = None

    @contextmanager
    def _transaction(self):
        self._db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self._db.execute('COMMIT')
        except BaseException:
            self._db.execute('ROLLBACK')
            raise

    def _row(self, key):
        row = self._db.execute('SELECT * FROM jobs WHERE scope=?', (key,)).fetchone()
        if row is None:
            raise KeyError('unknown local job scope')
        return row

    def _event(self, key, kind):
        self._db.execute('INSERT INTO events(scope,kind) VALUES (?,?)', (key, kind))

    @staticmethod
    def _view(row):
        result = dict(row)
        result['scope'] = json.loads(result['scope'])
        result['spec'] = json.loads(result['spec'])
        result['execution_authorized'] = False
        return result

    def enqueue(self, scope, resources, benchmark_id, data=frozenset()):
        key, spec = _scope(scope), _spec(resources, benchmark_id, data)
        with self._transaction():
            row = self._db.execute('SELECT * FROM jobs WHERE scope=?', (key,)).fetchone()
            if row is not None:
                if row['spec'] != spec:
                    raise IntentConflict('job scope already binds a different immutable spec')
            else:
                self._db.execute("INSERT INTO jobs(scope,spec,state) VALUES (?,?,'QUEUED')", (key, spec))
                self._event(key, 'QUEUED')
            result = self._view(self._row(key))
        return result

    def view(self, scope):
        return self._view(self._row(_scope(scope)))

    def prepare(self, scope, candidates, now_ms, policy, *, quorum_available=False, schedule_active=False):
        if type(quorum_available) is not bool or type(schedule_active) is not bool:
            raise ValueError('explicit local observation/policy booleans required')
        key = _scope(scope)
        with self._transaction():
            row = self._row(key)
            if row['state'] != 'QUEUED':
                return self._view(row)  # same original intent, never a new grant
            reason = None
            decision = None
            if not quorum_available:
                reason = 'AUTHORITY_UNAVAILABLE'
            elif not schedule_active:
                reason = 'SCHEDULE_STANDBY'
            else:
                # Count all uncertain holds, including previous process/generation.
                # Observed upstream reservations may overlap these local holds;
                # double-counting is conservative, never a capacity credit.
                holds = {}
                held_cpu_scales = {}
                for held in self._db.execute("SELECT node_id,spec FROM jobs WHERE state IN ('PREPARED','SEALED','UNKNOWN')"):
                    held_spec = json.loads(held['spec'])
                    quantities = held_spec['resources']
                    if quantities['cpu']:
                        held_cpu_scales.setdefault(held['node_id'], set()).add(held_spec['benchmark_id'])
                    current = holds.setdefault(held['node_id'], dict.fromkeys(quantities, 0))
                    for name, amount in quantities.items():
                        current[name] += amount
                adjusted = []
                for candidate in candidates:
                    if any(scale != candidate.benchmark_id for scale in held_cpu_scales.get(candidate.node_id, ())):
                        continue  # no implicit conversion of uncertain CPU entitlement
                    if not isinstance(candidate.reserved, Resources):
                        raise ValueError('typed raw reservation observation required')
                    local = holds.get(candidate.node_id, {})
                    reserved = asdict(candidate.reserved)
                    if any(type(v) is not int or v < 0 for v in reserved.values()):
                        raise ValueError('invalid raw reservation observation')
                    adjusted.append(replace(candidate, reserved=Resources(**{k: v + local.get(k, 0) for k, v in reserved.items()})))
                spec = json.loads(row['spec'])
                decision = place(Resources(**spec['resources']), spec['benchmark_id'], frozenset(spec['data']), adjusted, now_ms, policy)
                if decision.candidate is None:
                    reason = 'NO_ELIGIBLE_CAPACITY'
            if reason is not None:
                if row['reason'] != reason:
                    self._db.execute('UPDATE jobs SET reason=? WHERE scope=?', (reason, key))
                    self._event(key, reason)
            else:
                selected = next(n for n in adjusted if n.node_id == decision.candidate)
                self._db.execute("UPDATE jobs SET state='PREPARED',request_id=?,local_hold_id=?,node_id=?,incarnation=?,reason=NULL WHERE scope=?",
                    (str(uuid.uuid4()), str(uuid.uuid4()), selected.node_id, selected.incarnation, key))
                self._event(key, 'PREPARED')
            result = self._view(self._row(key))
        return result

    def record_handoff(self, scope):
        key = _scope(scope)
        with self._transaction():
            row = self._row(key)
            if row['state'] == 'PREPARED':
                self._db.execute("UPDATE jobs SET state='SEALED' WHERE scope=?", (key,))
                self._event(key, 'SEALED')
            elif row['state'] not in ('SEALED', 'UNKNOWN'):
                raise ValueError('only prepared intent may be sealed')
            result = self._view(self._row(key))
        return result

    def record_unknown(self, scope):
        key = _scope(scope)
        with self._transaction():
            row = self._row(key)
            if row['state'] == 'SEALED':
                self._db.execute("UPDATE jobs SET state='UNKNOWN' WHERE scope=?", (key,))
                self._event(key, 'UNKNOWN')
            elif row['state'] != 'UNKNOWN':
                raise ValueError('unknown outcome requires a sealed original intent')
            result = self._view(self._row(key))
        return result

    def cancel(self, scope):
        key = _scope(scope)
        with self._transaction():
            row = self._row(key)
            if row['state'] in ('SEALED', 'UNKNOWN'):
                raise ReconciliationRequired('original outcome unknown; local hold cannot be refunded')
            if row['state'] != 'CANCELLED':
                self._db.execute("UPDATE jobs SET state='CANCELLED' WHERE scope=?", (key,))
                self._event(key, 'CANCELLED')
            result = self._view(self._row(key))
        return result

    def events(self):
        return [dict(r) for r in self._db.execute('SELECT sequence,scope,kind FROM events ORDER BY sequence')]
