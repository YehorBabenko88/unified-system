"""Bounded Observer-owned state/outbox. Never opens a source database."""
from dataclasses import asdict
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
import uuid

from .model import (AXES, NODES, EVENT_KINDS, Fact, ObserverError, label, need,
                    stamp, utc, version)

APP_ID = 0x554F4253
_connect = sqlite3.connect
MAX_FACTS = 512
MAX_EVENTS = 512
MAX_PENDING = 256


def ordinary(path, leaf_directory=True):
    need(path.is_absolute() and '..' not in path.parts and not str(path).startswith('\\\\'), 'LOCAL_ABSOLUTE_STATE_PATH')
    for item in (*reversed(path.parents), path):
        if not item.exists():
            need(item == path, 'STATE_PARENT_REQUIRED'); continue
        info = item.lstat()
        need(not item.is_symlink() and not getattr(info, 'st_file_attributes', 0) & 1024,
             'STATE_LINK_REJECTED')
        need(item.is_dir() if item != path or leaf_directory else item.is_file(), 'STATE_PATH_TYPE')
        if item == path and not leaf_directory:
            need(info.st_nlink == 1, 'STATE_FILE_LINKED')


class ObserverStore:
    def __init__(self, directory):
        self.directory = Path(directory)
        ordinary(self.directory)
        fresh = not self.directory.exists()
        if fresh:
            self.directory.mkdir()
        marker = self.directory / 'owner.json'; self.path = self.directory / 'observer.sqlite3'
        if fresh:
            state_id = str(uuid.uuid4())
            with marker.open('x', encoding='utf-8') as stream:
                json.dump({'schema':'unified.observer.owned-state.v1', 'state_id':state_id}, stream)
            with self.path.open('xb'):
                pass
        else:
            need(marker.is_file() and self.path.is_file(), 'FOREIGN_STATE_DIRECTORY')
            ordinary(marker, False); ordinary(self.path, False)
            need(marker.stat().st_size <= 4096, 'STATE_MARKER_BOUND')
            try:
                data = json.loads(marker.read_bytes())
                need(set(data) == {'schema', 'state_id'} and data['schema'] == 'unified.observer.owned-state.v1', 'STATE_MARKER')
                state_id = str(uuid.UUID(data['state_id']))
            except (ValueError, KeyError, TypeError):
                raise ObserverError('STATE_MARKER') from None
            need({p.name for p in self.directory.iterdir()} <=
                 {'owner.json', 'observer.sqlite3', 'observer.sqlite3-journal', 'dashboard.html'}, 'FOREIGN_STATE_FILES')
        ordinary(marker, False); ordinary(self.path, False)
        need(self.path.stat().st_size <= 8388608, 'STATE_DISK_BOUND')
        if not fresh:
            # Inspect only the fixed SQLite header BEFORE connect/configuration.
            # A foreign/WAL database must not be opened or given sidecar files.
            with self.path.open('rb') as stream: header = stream.read(100)
            need(len(header) == 100 and header[:16] == b'SQLite format 3\x00' and
                 int.from_bytes(header[68:72], 'big') == APP_ID and
                 int.from_bytes(header[60:64], 'big') == 1 and header[18:20] == b'\x01\x01',
                 'FOREIGN_STATE_DATABASE')
        self.lock = threading.RLock(); self.closed = False
        self.db = _connect(self.path, timeout=1, isolation_level=None, check_same_thread=False)
        try:
            if not fresh:
                need(self.db.execute('SELECT state_id FROM info').fetchall() == [(state_id,)], 'STATE_IDENTITY')
            self.db.execute('PRAGMA synchronous=FULL')
            self.db.execute('PRAGMA trusted_schema=OFF')
            self.db.execute('PRAGMA cache_size=-2048')
            self.db.execute('PRAGMA max_page_count=2048')
            if fresh:
                self.db.executescript('''
                    PRAGMA page_size=4096;
                    PRAGMA journal_mode=DELETE;
                    PRAGMA application_id=1431257683;
                    PRAGMA user_version=1;
                    CREATE TABLE info(state_id TEXT NOT NULL);
                    CREATE TABLE facts(key TEXT PRIMARY KEY, body TEXT NOT NULL, last_success TEXT);
                    CREATE TABLE sources(id TEXT PRIMARY KEY, status TEXT, at TEXT, version TEXT);
                    CREATE TABLE events(id TEXT PRIMARY KEY, kind TEXT, subject TEXT, status TEXT,
                        version TEXT, observed TEXT, delivery TEXT, not_before INTEGER, attempts INTEGER, message TEXT, transport TEXT);
                    CREATE TABLE attempts(id INTEGER PRIMARY KEY, at INTEGER NOT NULL);
                    CREATE TABLE dedupe(id TEXT PRIMARY KEY);
                ''')
                self.db.execute('INSERT INTO info VALUES(?)', (state_id,))
            need(self.db.execute('PRAGMA application_id').fetchone()[0] == APP_ID and
                 self.db.execute('PRAGMA user_version').fetchone()[0] == 1, 'FOREIGN_STATE_DATABASE')
            need(self.db.execute('SELECT state_id FROM info').fetchall() == [(state_id,)], 'STATE_IDENTITY')
            # Observer-owned GET accounting, never the cluster's Bybit limiter.
            self.db.execute('CREATE TABLE IF NOT EXISTS github_attempts(at INTEGER NOT NULL, source TEXT NOT NULL)')
            self.db.execute('CREATE TABLE IF NOT EXISTS github_cooldown(id INTEGER PRIMARY KEY CHECK(id=1), until_at INTEGER NOT NULL)')
            self.db.execute('CREATE TABLE IF NOT EXISTS source_episodes(id TEXT PRIMARY KEY, episode INTEGER NOT NULL)')
            self.db.execute("UPDATE events SET delivery='UNKNOWN' WHERE delivery='SENDING'")
        except BaseException:
            self.db.close(); self.closed = True; raise

    def _check(self):
        need(not self.closed, 'STATE_CLOSED'); ordinary(self.directory); ordinary(self.path, False)
        need(self.path.stat().st_size <= 8388608, 'STATE_DISK_BOUND')
        need(sum(p.stat().st_size for p in self.directory.iterdir() if p.is_file()) <= 18874368,
             'OWN_DIRECTORY_BUDGET')

    def close(self):
        with self.lock:
            if not self.closed:
                self.db.close(); self.closed = True

    def reserve_github(self, source, now):
        label(source); epoch = int(utc(now).timestamp())
        with self.lock:
            self._check(); self.db.execute('BEGIN IMMEDIATE')
            try:
                highwater = self.db.execute('SELECT MAX(at) FROM github_attempts').fetchone()[0]
                need(highwater is None or epoch >= highwater, 'GITHUB_CLOCK_ROLLBACK')
                cooldown = self.db.execute('SELECT until_at FROM github_cooldown WHERE id=1').fetchone()
                need(cooldown is None or epoch >= cooldown[0], 'GITHUB_COOLDOWN')
                last = self.db.execute('SELECT MAX(at) FROM github_attempts WHERE source=?', (source,)).fetchone()[0]
                need(last is None or epoch-last >= 900, 'GITHUB_SOURCE_INTERVAL')
                count = self.db.execute('SELECT COUNT(*) FROM github_attempts WHERE at>?', (epoch-3600,)).fetchone()[0]
                need(count < 50, 'GITHUB_GLOBAL_HOURLY_LIMIT')
                self.db.execute('DELETE FROM github_attempts WHERE at<=?', (epoch-3600,))
                self.db.execute('INSERT INTO github_attempts VALUES(?,?)', (epoch, source))
                self.db.execute('COMMIT')
            except BaseException:
                self.db.execute('ROLLBACK'); raise

    def cooldown_github(self, now, seconds):
        need(type(seconds) is int and 0 <= seconds <= 604800, 'GITHUB_COOLDOWN_BOUND')
        until = int(utc(now).timestamp()) + max(3600, seconds)
        with self.lock:
            self._check()
            self.db.execute('INSERT INTO github_cooldown VALUES(1,?) ON CONFLICT(id) DO UPDATE SET until_at=MAX(until_at,excluded.until_at)', (until,))

    def record_source(self, source, status, now, source_version):
        label(source); version(source_version); need(status in ('PASS', 'FAIL'), 'SOURCE_AVAILABILITY')
        with self.lock:
            self._check(); self.db.execute('BEGIN IMMEDIATE')
            try:
                prior = self.db.execute('SELECT status FROM sources WHERE id=?', (source,)).fetchone()
                row = self.db.execute('SELECT episode FROM source_episodes WHERE id=?', (source,)).fetchone()
                episode = row[0] if row else 0
                if status == 'FAIL' and (prior is None or prior[0] != 'FAIL'):
                    need(episode < 10**9, 'SOURCE_EPISODE_BOUND')
                    episode += 1
                    self._enqueue('SOURCE_UNAVAILABLE', source, 'FAIL', source_version, now,
                                  discriminator='source-episode:' + str(episode))
                self.db.execute('INSERT OR REPLACE INTO source_episodes VALUES(?,?)', (source, episode))
                self.db.execute('INSERT OR REPLACE INTO sources VALUES(?,?,?,?)',
                    (source, status, stamp(now), source_version))
                self.db.execute('COMMIT')
            except BaseException:
                self.db.execute('ROLLBACK'); raise

    def ingest(self, facts, now):
        need(type(facts) is list and len(facts) <= MAX_FACTS, 'FACT_BATCH_BOUND')
        with self.lock:
            self._check()
            self.db.execute('BEGIN IMMEDIATE')
            try:
                # CI pages are bounded observations, not an ever-growing run archive.
                # Prune only owned CI rows; never node axes, last-success or outbox.
                for source in {f.source for f in facts if type(f) is Fact and f.section == 'ci'}:
                    incoming = {f.key for f in facts if f.section == 'ci' and f.source == source}
                    need(len(incoming) <= 16, 'CI_SOURCE_WINDOW_BOUND')
                    prior_ci = []
                    for key, body in self.db.execute('SELECT key,body FROM facts'):
                        old = json.loads(body)
                        if old['section'] == 'ci' and old['source'] == source and key not in incoming:
                            prior_ci.append((utc(old['observed_at']), key))
                    keep = {key for _, key in sorted(prior_ci, reverse=True)[:16-len(incoming)]} | incoming
                    for _, key in prior_ci:
                        if key not in keep: self.db.execute('DELETE FROM facts WHERE key=?', (key,))
                for fact in facts:
                    need(type(fact) is Fact, 'PARSED_FACT_REQUIRED')
                    prior = self.db.execute('SELECT body,last_success FROM facts WHERE key=?', (fact.key,)).fetchone()
                    old = json.loads(prior[0]) if prior else None
                    if old and utc(old['observed_at']) >= utc(fact.observed_at):
                        continue
                    last_success = fact.observed_at if fact.status == 'PASS' else (prior[1] if prior else None)
                    body = json.dumps(asdict(fact), sort_keys=True, separators=(',', ':'))
                    need(len(body.encode()) <= 4096, 'FACT_ROW_BOUND')
                    if not prior:
                        need(self.db.execute('SELECT COUNT(*) FROM facts').fetchone()[0] < MAX_FACTS, 'FACT_COUNT_BOUND')
                    self.db.execute('INSERT OR REPLACE INTO facts VALUES(?,?,?)', (fact.key, body, last_success))
                    event = self._transition(fact, old)
                    if event:
                        self._enqueue(event, fact.subject, fact.status, fact.version, now,
                                      discriminator=fact.key + ':' + fact.observed_at + ':' + json.dumps(fact.value, sort_keys=True))
                self.db.execute('COMMIT')
            except BaseException:
                self.db.execute('ROLLBACK'); raise

    @staticmethod
    def _transition(fact, old):
        if old and (old['status'], old['value'], old['version']) == (fact.status, fact.value, fact.version):
            return None
        field, state = fact.field, fact.status
        if field == 'RUN_STATUS' and state == 'FAIL': return 'CI_FAILURE'
        if field == 'PHYSICAL_ACCEPTED' and state == 'PASS': return 'PHYSICAL_NODE_ADMITTED'
        if field == 'LAN_REACHABLE' and state == 'FAIL': return 'NODE_DISCONNECTED'
        if field == 'SERVICE_RUNNING' and state == 'FAIL': return 'SERVICE_STOPPED'
        if field == 'LIVE_COLLECTOR' and state == 'FAIL': return 'DATA_CAPTURE_STOPPED'
        if field == 'BLOCKER' and state in ('FAIL', 'BLOCKED'): return 'NEW_BLOCKER'
        if field == 'OPERATOR_DECISION' and state == 'BLOCKED': return 'OPERATOR_DECISION_REQUIRED'
        if field == 'MILESTONE' and state == 'PASS' and fact.mode == 'QUALIFIED': return 'MILESTONE_PASS'
        if field == 'DISK_USAGE' and type(fact.value) is dict and fact.value['total'] and fact.value['observed'] * 100 >= fact.value['total'] * 90:
            return 'RESOURCE_WARNING'
        return None

    def _enqueue(self, kind, subject, status, source_version, now, discriminator=''):
        need(kind in EVENT_KINDS, 'EVENT_KIND'); label(subject); version(source_version)
        need(status in ('PASS', 'FAIL', 'BLOCKED', 'UNKNOWN', 'STALE'), 'EVENT_STATUS')
        identity = hashlib.sha256(json.dumps([kind, subject, status, source_version, discriminator],
                                            separators=(',', ':')).encode()).hexdigest()
        if self.db.execute('SELECT 1 FROM dedupe WHERE id=?', (identity,)).fetchone(): return False
        need(self.db.execute('SELECT COUNT(*) FROM dedupe').fetchone()[0] < 8192, 'DEDUPE_CAPACITY_REQUIRES_OPERATOR_ARCHIVE')
        need(self.db.execute("SELECT COUNT(*) FROM events WHERE delivery IN ('PENDING','SENDING','UNKNOWN')").fetchone()[0] < MAX_PENDING, 'OUTBOX_FULL')
        if self.db.execute('SELECT COUNT(*) FROM events').fetchone()[0] >= MAX_EVENTS:
            self.db.execute("DELETE FROM events WHERE id IN (SELECT id FROM events WHERE delivery='SENT' ORDER BY observed LIMIT 64)")
        need(self.db.execute('SELECT COUNT(*) FROM events').fetchone()[0] < MAX_EVENTS, 'EVENT_RETENTION_FULL')
        # Closed template: no raw source values, evidence URIs, addresses or errors.
        message = f'Unified Observer: {kind} | {subject} | {status} | source {source_version[:7]}'
        self.db.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?)',
            (identity, kind, subject, status, source_version, stamp(now), 'PENDING', 0, 0, message, 'DISABLED'))
        self.db.execute('INSERT INTO dedupe VALUES(?)', (identity,))
        return True

    def enqueue(self, kind, subject, status, source_version, now):
        with self.lock:
            self._check(); self.db.execute('BEGIN IMMEDIATE')
            try:
                result = self._enqueue(kind, subject, status, source_version, now)
                self.db.execute('COMMIT'); return result
            except BaseException:
                self.db.execute('ROLLBACK'); raise

    def queue_counts(self):
        with self.lock:
            self._check(); result = dict.fromkeys(('PENDING', 'SENDING', 'SENT', 'UNKNOWN'), 0)
            result.update(dict(self.db.execute('SELECT delivery,COUNT(*) FROM events GROUP BY delivery')))
            return result

    def claim_for_delivery(self, now, minimum_interval=60, maximum_daily=60):
        need(type(minimum_interval) is int and 15 <= minimum_interval <= 3600, 'NOTIFICATION_INTERVAL')
        need(type(maximum_daily) is int and 1 <= maximum_daily <= 100, 'NOTIFICATION_DAILY_BOUND')
        epoch = int(utc(now).timestamp())
        with self.lock:
            self._check(); self.db.execute('BEGIN IMMEDIATE')
            try:
                pending = self.db.execute("SELECT id,message,attempts,not_before FROM events WHERE delivery='PENDING' ORDER BY observed,id LIMIT 1").fetchone()
                if pending is None: result = ('EMPTY', None)
                elif pending[3] > epoch: result = ('BACKOFF', None)
                else:
                    last = self.db.execute('SELECT MAX(at) FROM attempts').fetchone()[0]
                    count = self.db.execute('SELECT COUNT(*) FROM attempts WHERE at>?', (epoch - 86400,)).fetchone()[0]
                    if (last is not None and epoch - last < minimum_interval) or count >= maximum_daily:
                        result = ('RATE_LIMITED', None)
                    else:
                        self.db.execute('DELETE FROM attempts WHERE at<?', (epoch - 172800,))
                        self.db.execute('INSERT INTO attempts(at) VALUES(?)', (epoch,))
                        self.db.execute("UPDATE events SET delivery='SENDING', attempts=attempts+1 WHERE id=?", (pending[0],))
                        result = ('CLAIMED', pending)
                self.db.execute('COMMIT'); return result
            except BaseException:
                self.db.execute('ROLLBACK'); raise

    def deliver_one(self, transport, now, minimum_interval=60, maximum_daily=60):
        state, row = self.claim_for_delivery(now, minimum_interval, maximum_daily)
        if state != 'CLAIMED': return state
        mode = getattr(transport, 'mode', 'UNSPECIFIED')
        if mode not in ('MOCK', 'TELEGRAM_TEST'): mode = 'UNSPECIFIED'
        with self.lock:
            self.db.execute('UPDATE events SET transport=? WHERE id=?', (mode, row[0]))
        try:
            result = transport.send(row[1])
        except BaseException:
            result = 'UNKNOWN'  # Never infer failure-to-send from a lost response.
        if result not in ('SENT', 'NOT_SENT', 'UNKNOWN'): result = 'UNKNOWN'
        with self.lock:
            self._check()
            retry_at = int(utc(now).timestamp()) + min(3600, 60 * 2**min(row[2], 5))
            self.db.execute('UPDATE events SET delivery=?,not_before=? WHERE id=?',
                ('PENDING' if result == 'NOT_SENT' else result, retry_at if result == 'NOT_SENT' else 0, row[0]))
        return result

    def snapshot(self, now):
        now = utc(now)
        with self.lock:
            self._check()
            view = {'schema':'unified.observer.dashboard.v1', 'read_only':True,
                    'automatic_repair':False, 'trading_access':False, 'admission_authority':False,
                    'computers':{node:{axis:{'status':'UNKNOWN', 'last_status':'UNKNOWN',
                        'evidence':None, 'observed_at':None, 'source_version':None,
                        'last_successful_observation':None, 'value':None} for axis in AXES} for node in NODES},
                    'services':[], 'market_data':[], 'development':[], 'ci':[], 'acceptance':[],
                    'sources':{}, 'events':[], 'notifications':self.queue_counts(), 'updated_at':None}
            times = []
            for body, last_success in self.db.execute('SELECT body,last_success FROM facts ORDER BY key'):
                fact = json.loads(body); observed = utc(fact['observed_at']); times.append(observed)
                effective = ('UNKNOWN' if now + timedelta(seconds=5) < observed else
                             'STALE' if now > observed + timedelta(seconds=fact['ttl_seconds']) else fact['status'])
                item = {'subject':fact['subject'], 'field':fact['field'], 'status':effective,
                        'last_status':fact['status'], 'value':fact['value'], 'mode':fact['mode'],
                        'observed_at':fact['observed_at'], 'source_version':fact['version'],
                        'last_successful_observation':last_success,
                        'evidence':{'source':fact['source'], 'sha256':fact['digest'], 'scope':fact['scope']}}
                if fact['section'] == 'computers': view['computers'][fact['subject']][fact['field']] = item
                else: view[fact['section']].append(item)
            for source, status, at, source_version in self.db.execute('SELECT id,status,at,version FROM sources'):
                view['sources'][source] = {'status':status, 'observed_at':at, 'source_version':source_version}
            for row in self.db.execute('SELECT kind,subject,status,observed,delivery,transport FROM events ORDER BY observed DESC,id LIMIT 128'):
                view['events'].append(dict(zip(('kind', 'subject', 'status', 'observed_at', 'delivery', 'transport'), row)))
            if times: view['updated_at'] = stamp(max(times))
            return view
