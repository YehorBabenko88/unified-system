"""Durable local command/dispatch outbox, never an authority ledger."""
import sqlite3
from contextlib import contextmanager

from .domain_v1 import decode_command


class IntentConflict(ValueError):
    pass


class AttemptRegistry:
    def __init__(self, path):
        self.db = sqlite3.connect(path, timeout=5, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('''CREATE TABLE IF NOT EXISTS scheduler_attempts (
            request_id TEXT PRIMARY KEY, idempotency_key TEXT UNIQUE NOT NULL,
            raw BLOB NOT NULL, state TEXT NOT NULL CHECK(state IN
            ('PREPARED','SUBMITTED','UNKNOWN','COMMITTED','REJECTED')),
            receipt BLOB, drain_requested INTEGER NOT NULL DEFAULT 0 CHECK(drain_requested IN (0,1)),
            dispatch_state TEXT NOT NULL DEFAULT 'NONE'
            CHECK(dispatch_state IN ('NONE','SENDING','STARTED')), worker_receipt BLOB)''')

    def close(self):
        if self.db is not None:
            self.db.close(); self.db = None

    @contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK'); raise

    def get(self, request_id):
        row = self.db.execute('SELECT * FROM scheduler_attempts WHERE request_id=?', (request_id,)).fetchone()
        if row is None: raise KeyError(request_id)
        return dict(row)

    def prepare(self, raw):
        value = decode_command(raw)
        with self.transaction():
            prior = self.db.execute('SELECT * FROM scheduler_attempts WHERE request_id=? OR idempotency_key=?',
                                    (value['request_id'], value['idempotency_key'])).fetchall()
            if prior:
                if len(prior) != 1 or prior[0]['raw'] != raw:
                    raise IntentConflict('original full intent and IDs are immutable')
            else:
                self.db.execute('INSERT INTO scheduler_attempts(request_id,idempotency_key,raw,state) VALUES (?,?,?,?)',
                                (value['request_id'], value['idempotency_key'], raw, 'PREPARED'))
        return self.get(value['request_id'])

    def seal(self, request_id):
        with self.transaction():
            result = self.db.execute("UPDATE scheduler_attempts SET state='SUBMITTED' WHERE request_id=? AND state='PREPARED' AND drain_requested=0", (request_id,))
        return result.rowcount == 1

    def resolve(self, request_id, state, receipt):
        if state not in ('UNKNOWN', 'COMMITTED', 'REJECTED'):
            raise ValueError('invalid outcome')
        if (state == 'UNKNOWN' and receipt is not None) or (state != 'UNKNOWN' and type(receipt) is not bytes):
            raise ValueError('exact terminal receipt required; UNKNOWN has no proof')
        with self.transaction():
            prior = self.get(request_id)
            if prior['state'] in ('COMMITTED', 'REJECTED'):
                if (prior['state'], prior['receipt']) != (state, receipt):
                    raise IntentConflict('terminal result immutable')
            elif prior['state'] in ('SUBMITTED', 'UNKNOWN'):
                self.db.execute('UPDATE scheduler_attempts SET state=?,receipt=? WHERE request_id=?', (state, receipt, request_id))
            else:
                raise IntentConflict('unsubmitted intent cannot have outcome')

    def claim_dispatch(self, request_id):
        with self.transaction():
            result = self.db.execute("UPDATE scheduler_attempts SET dispatch_state='SENDING' WHERE request_id=? AND state='COMMITTED' AND dispatch_state='NONE' AND drain_requested=0", (request_id,))
        return result.rowcount == 1

    def request_drain(self, request_id):
        with self.transaction():
            self.get(request_id)
            self.db.execute('UPDATE scheduler_attempts SET drain_requested=1 WHERE request_id=?', (request_id,))
        return self.get(request_id)

    def record_started(self, request_id, receipt):
        if type(receipt) is not bytes or not receipt:
            raise ValueError('worker response bytes required')
        with self.transaction():
            self.db.execute("UPDATE scheduler_attempts SET dispatch_state='STARTED',worker_receipt=? WHERE request_id=? AND state='COMMITTED' AND dispatch_state='SENDING'", (receipt, request_id))
