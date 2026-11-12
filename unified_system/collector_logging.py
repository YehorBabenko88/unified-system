"""Versioned, bounded local application logs; no service or authority grant.

Only caller-selected NEW owned state is written. Code/state roots must be
disjoint. This module neither configures ACLs/NSSM nor changes the runtime.
The exclusive lock file is not reclaimed after a crash: interrupted writes,
partial lines, stale locks and cursor mismatches require owner recovery, not
automatic repair. Sequence and UTC time are logging metadata, not authority.

Rotation may remove ONLY verified oldest managed logs from this context. File
bounds are logical/application bounds, not hard disk quotas, hostile-writer
containment, cross-process qualification or power-loss durability guarantees.
No exception text, freeform messages, URLs or stdout/stderr fallback is emitted.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from threading import Lock

SCHEMA = 'unified.collector.logging.v1'
EVENTS = frozenset(('STARTUP','READY','CAPTURE','CHECKPOINT','SHUTDOWN','BLOCKED',
                    'SOURCE','RETRY','RECOVERY','RESOURCE','QUALITY','ERROR'))
STATES = frozenset(('STARTING','RUNNING','STOPPING','STOPPED','BLOCKED','UNKNOWN'))
ERROR_CODES = frozenset(('NONE','SOURCE_UNAVAILABLE','PROFILE_DENIED','SINK_UNAVAILABLE',
    'CAPTURE_STOPPED','LOG_IO_UNKNOWN','RECOVERY_DENIED','SHUTDOWN_UNKNOWN',
    'DATABASE_FAILED','QUALITY_GAP','RESOURCE_LIMIT','CHECKPOINT_UNKNOWN'))
_MAX = 2**63-1
_MARKER = 'context.json'
_CURSOR = 'cursor.json'
_PENDING = 'cursor.pending'
_LOCK = 'writer.lock'
_FIELDS = {'schema','sequence','at_utc','event','state','error_code','count','bytes','digest'}
BLOCK_CODES = frozenset(('INTERNAL_DENIED','PROFILE_DENIED','PATH_ALIAS','PATH_KIND','PATH_LINK_COUNT',
    'LOCAL_ABSOLUTE_PATH_REQUIRED','FILE_BOUND','FILE_IDENTITY','FILE_CHANGED','SHORT_WRITE',
    'NONCANONICAL_STATE','RECORD_DENIED','SEQUENCE_DENIED','TIMESTAMP_DENIED','CONTEXT_DENIED',
    'STATE_CODE_SEPARATION','CONTEXT_NOT_NEW','LOG_IO_UNKNOWN','RECOVERY_DENIED','CONTEXT_BUSY',
    'LOCK_IDENTITY','CONTEXT_CLOSED','PARTIAL_OR_OVERSIZED_RECORD','UNMANAGED_CONTEXT_ENTRY',
    'LOG_BUSY','CONTEXT_BLOCKED','RECORD_BOUND'))


class LogBlocked(RuntimeError):
    """A closed code only; never retains a formatted operating-system error."""
    def __init__(self, code):
        code = code if type(code) is str and code in BLOCK_CODES else 'INTERNAL_DENIED'
        self.code = code
        super().__init__(code)


def _need(value, code):
    if not value: raise LogBlocked(code)


@dataclass(frozen=True)
class LogLimits:
    """file_count caps JSONL files. Control bounds are fixed separately:
    marker <=1KiB, cursor/pending <=4KiB each, writer lock <256B. At most
    file_count+4 files exist during a write; unexpected leftovers deny recovery.
    """
    file_bytes: int = 65536
    file_count: int = 4
    record_bytes: int = 2048

    def __post_init__(self):
        _need(type(self.file_bytes) is int and 1024 <= self.file_bytes <= 1048576 and
              type(self.file_count) is int and 2 <= self.file_count <= 4 and
              type(self.record_bytes) is int and self.record_bytes == 2048, 'PROFILE_DENIED')


@dataclass(frozen=True)
class LogReceipt:
    sequence: int
    record_sha256: str


def _encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                       allow_nan=False)+'\n').encode('ascii')


def _plain(path, directory=False):
    info = path.lstat()
    _need(not (stat.S_ISLNK(info.st_mode) or getattr(info,'st_reparse_tag',0) or
               getattr(info,'st_file_attributes',0)&1024), 'PATH_ALIAS')
    _need(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode), 'PATH_KIND')
    if not directory: _need(info.st_nlink == 1, 'PATH_LINK_COUNT')
    return info


def _parents(path):
    _need(path.is_absolute() and '..' not in path.parts and
          not path.anchor.startswith(('\\\\','//')), 'LOCAL_ABSOLUTE_PATH_REQUIRED')
    for parent in reversed((path, *path.parents)): _plain(parent, True)


def _identity(info): return info.st_dev, info.st_ino


def _read(path, limit):
    _parents(path.parent); before = _plain(path)
    _need(before.st_size <= limit, 'FILE_BOUND')
    fd = os.open(path, os.O_RDONLY|getattr(os,'O_BINARY',0)|getattr(os,'O_NOFOLLOW',0))
    try:
        opened = os.fstat(fd)
        _need(_identity(opened) == _identity(before) and opened.st_nlink == 1, 'FILE_IDENTITY')
        chunks = []; total = 0
        while True:
            raw = os.read(fd, min(65536, limit-total+1))
            if not raw: break
            total += len(raw); _need(total <= limit, 'FILE_BOUND'); chunks.append(raw)
        after = os.fstat(fd); current = _plain(path)
        expected = (_identity(before), before.st_size, before.st_mtime_ns)
        _need((_identity(after),after.st_size,after.st_mtime_ns) == expected and
              (_identity(current),current.st_size,current.st_mtime_ns) == expected and
              total == before.st_size, 'FILE_CHANGED')
        return b''.join(chunks)
    finally: os.close(fd)


def _write(fd, raw):
    view = memoryview(raw)
    while view:
        written = os.write(fd, view)
        _need(type(written) is int and 0 < written <= len(view), 'SHORT_WRITE')
        view = view[written:]


def _new(path, raw):
    _parents(path.parent)
    fd = os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_BINARY',0)|getattr(os,'O_NOFOLLOW',0), 0o600)
    try:
        _write(fd, raw); os.fsync(fd)
        info = os.fstat(fd)
        _need(info.st_nlink == 1 and info.st_size == len(raw) and
              _identity(_plain(path)) == _identity(info), 'FILE_IDENTITY')
    finally: os.close(fd)


def _json(path, bound):
    raw = _read(path, bound)
    value = json.loads(raw)
    _need(_encode(value) == raw, 'NONCANONICAL_STATE')
    return value


def _valid_record(record):
    _need(type(record) is dict and set(record) == _FIELDS and record['schema'] == SCHEMA, 'RECORD_DENIED')
    for key, allowed in (('event',EVENTS),('state',STATES),('error_code',ERROR_CODES)):
        _need(type(record[key]) is str and record[key] in allowed, 'RECORD_DENIED')
    for key in ('count','bytes'):
        _need(type(record[key]) is int and 0 <= record[key] <= _MAX, 'RECORD_DENIED')
    _need(type(record['sequence']) is int and 1 <= record['sequence'] <= _MAX, 'SEQUENCE_DENIED')
    digest = record['digest']
    _need(digest is None or (type(digest) is str and re.fullmatch('[0-9a-f]{64}',digest)), 'RECORD_DENIED')
    at = record['at_utc']
    _need(type(at) is str and re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z',at), 'TIMESTAMP_DENIED')
    try:
        parsed = datetime.fromisoformat(at[:-1]+'+00:00')
        _need(parsed.isoformat(timespec='milliseconds').replace('+00:00','Z') == at, 'TIMESTAMP_DENIED')
    except (ValueError, OverflowError): raise LogBlocked('TIMESTAMP_DENIED') from None


class CollectorLog:
    """One nonblocking caller/writer and one exclusive owned context lock.

    create/open require a direct child of existing state_root, disjoint from
    code_root. context_id is a caller-pinned 32-hex ownership label, not a secret,
    signature or native privilege. Caller must separately admit state ACLs.
    clock, if supplied, returns an exact aware UTC datetime; no custom messages.
    """
    def __init__(self, root, state_root, code_root, context_id, limits, clock):
        self.root = Path(root); self._state_root = Path(state_root); self._code_root = Path(code_root)
        _need(type(limits) is LogLimits, 'PROFILE_DENIED')
        limits.__post_init__()
        self._limits = LogLimits(limits.file_bytes,limits.file_count,limits.record_bytes)
        _need(type(context_id) is str and re.fullmatch('[0-9a-f]{32}',context_id), 'CONTEXT_DENIED')
        _need(clock is None or callable(clock), 'PROFILE_DENIED')
        self._context_id = context_id; self._clock = clock or (lambda: datetime.now(timezone.utc))
        _parents(self._state_root); _parents(self._code_root)
        _need(self.root.is_absolute() and '..' not in self.root.parts and self.root.parent == self._state_root and
              not self._state_root.is_relative_to(self._code_root) and
              not self._code_root.is_relative_to(self._state_root), 'STATE_CODE_SEPARATION')
        self._gate = Lock(); self._fd = None; self._lock_identity = None
        self._closed = False; self._blocked = False; self._close_failed = False; self._next = 1

    @property
    def closed(self):
        """API refuses further writes; not proof of retirement after close error."""
        return self._closed

    @property
    def blocked(self): return self._blocked

    def _marker(self):
        return {'schema':'unified.collector.logging.context.v1','context_id':self._context_id,
                'limits':{'file_bytes':self._limits.file_bytes,'file_count':self._limits.file_count,'record_bytes':2048}}

    @staticmethod
    def _cursor(next_sequence, files):
        return {'schema':'unified.collector.logging.cursor.v1','next_sequence':next_sequence,'files':files}

    @classmethod
    def create(cls, root, *, state_root, code_root, context_id, limits=LogLimits(), clock=None):
        try:
            self = cls(root,state_root,code_root,context_id,limits,clock)
            self.root.mkdir(exist_ok=False)
            _new(self.root/_MARKER, _encode(self._marker()))
            _new(self.root/_CURSOR, _encode(self._cursor(1, [])))
            self._claim()
            return self
        except LogBlocked: raise
        except FileExistsError: raise LogBlocked('CONTEXT_NOT_NEW') from None
        except (OSError, ValueError): raise LogBlocked('LOG_IO_UNKNOWN') from None

    @classmethod
    def open(cls, root, *, state_root, code_root, context_id, limits=LogLimits(), clock=None):
        try:
            self = cls(root,state_root,code_root,context_id,limits,clock)
            self._recover()  # No lock file is created in a foreign context.
            self._claim()
            try: self._next, _ = self._recover()
            except BaseException:
                try: self.close()
                except LogBlocked: pass
                raise
            return self
        except LogBlocked: raise
        except (OSError, ValueError, TypeError, KeyError): raise LogBlocked('RECOVERY_DENIED') from None

    def _claim(self):
        _parents(self.root)
        try:
            fd = os.open(self.root/_LOCK, os.O_RDWR|os.O_CREAT|os.O_EXCL|getattr(os,'O_BINARY',0)|getattr(os,'O_NOFOLLOW',0), 0o600)
        except FileExistsError: raise LogBlocked('CONTEXT_BUSY') from None
        try:
            _write(fd, _encode({'schema':'unified.collector.logging.writer.v1','context_id':self._context_id}))
            os.fsync(fd); info = os.fstat(fd)
            _need(info.st_nlink == 1 and _identity(_plain(self.root/_LOCK)) == _identity(info), 'LOCK_IDENTITY')
        except BaseException:
            try: os.close(fd)
            except OSError: pass
            raise
        self._fd = fd; self._lock_identity = _identity(info)

    def _held(self):
        _parents(self.root)
        _need(self._fd is not None and not self._closed, 'CONTEXT_CLOSED')
        path_info = _plain(self.root/_LOCK); held = os.fstat(self._fd)
        _need(held.st_nlink == 1 and _identity(held) == self._lock_identity == _identity(path_info), 'LOCK_IDENTITY')

    def _recover(self):
        _parents(self.root)
        _need(_json(self.root/_MARKER,1024) == self._marker(), 'CONTEXT_DENIED')
        cursor = _json(self.root/_CURSOR,4096)
        _need(type(cursor) is dict and set(cursor) == {'schema','next_sequence','files'} and
              cursor['schema'] == 'unified.collector.logging.cursor.v1' and
              type(cursor['next_sequence']) is int and 1 <= cursor['next_sequence'] <= _MAX+1 and
              type(cursor['files']) is list and len(cursor['files']) <= self._limits.file_count, 'RECOVERY_DENIED')
        files = cursor['files']; names = {_MARKER,_CURSOR}; previous = None; scanned = 0
        for item in files:
            _need(type(item) is dict and set(item) == {'name','bytes','sha256','first','last'}, 'RECOVERY_DENIED')
            _need(type(item['first']) is int and type(item['last']) is int and 1 <= item['first'] <= item['last'] <= _MAX and
                  item['name'] == 'events-'+format(item['first'],'019d')+'.jsonl' and item['name'] not in names and
                  type(item['bytes']) is int and 1 <= item['bytes'] <= self._limits.file_bytes and
                  type(item['sha256']) is str and re.fullmatch('[0-9a-f]{64}',item['sha256']), 'RECOVERY_DENIED')
            names.add(item['name']); raw = _read(self.root/item['name'],self._limits.file_bytes)
            _need(len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256'], 'RECOVERY_DENIED')
            expected = item['first']
            _need(previous is None or expected == previous+1, 'SEQUENCE_DENIED')
            for line in raw.splitlines(keepends=True):
                scanned += 1; _need(scanned <= 32768 and line.endswith(b'\n') and len(line) <= 2048, 'PARTIAL_OR_OVERSIZED_RECORD')
                record = json.loads(line); _valid_record(record)
                _need(record['sequence'] == expected and _encode(record) == line, 'SEQUENCE_DENIED'); expected += 1
            _need(expected == item['last']+1, 'SEQUENCE_DENIED'); previous = item['last']
        _need(cursor['next_sequence'] == (1 if previous is None else previous+1), 'SEQUENCE_DENIED')
        actual = set()
        for path in self.root.iterdir():
            _plain(path); actual.add(path.name)
        _need(actual in (names, names|{_LOCK}), 'UNMANAGED_CONTEXT_ENTRY')
        return cursor['next_sequence'], files

    def emit(self, *, event, state, error_code='NONE', count=0, bytes_count=0, digest=None):
        _need(self._gate.acquire(blocking=False), 'LOG_BUSY')
        try:
            _need(not self._closed, 'CONTEXT_CLOSED'); _need(not self._blocked, 'CONTEXT_BLOCKED')
            try:
                now = self._clock()
                _need(type(now) is datetime and now.tzinfo is timezone.utc, 'TIMESTAMP_DENIED')
                at = now.isoformat(timespec='milliseconds').replace('+00:00','Z')
            except LogBlocked: raise
            except BaseException: raise LogBlocked('TIMESTAMP_DENIED') from None
            record = {'schema':SCHEMA,'sequence':self._next,'at_utc':at,'event':event,'state':state,
                      'error_code':error_code,'count':count,'bytes':bytes_count,'digest':digest}
            _valid_record(record); raw = _encode(record)
            _need(len(raw) <= min(self._limits.record_bytes,self._limits.file_bytes), 'RECORD_BOUND')
            try:
                self._held(); next_sequence, files = self._recover()
                _need(next_sequence == self._next, 'SEQUENCE_DENIED')
                files = [dict(item) for item in files]
                if not files or files[-1]['bytes']+len(raw) > self._limits.file_bytes:
                    if len(files) == self._limits.file_count:
                        oldest = files.pop(0)
                        _need(hashlib.sha256(_read(self.root/oldest['name'],self._limits.file_bytes)).hexdigest() == oldest['sha256'], 'FILE_CHANGED')
                        (self.root/oldest['name']).unlink()  # Verified oldest OWN managed log only.
                    item = {'name':'events-'+format(self._next,'019d')+'.jsonl','first':self._next,
                            'last':self._next,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
                    _new(self.root/item['name'],raw); files.append(item)
                else:
                    item = files[-1]; path = self.root/item['name']; before = _plain(path)
                    fd = os.open(path,os.O_WRONLY|os.O_APPEND|getattr(os,'O_BINARY',0)|getattr(os,'O_NOFOLLOW',0))
                    try:
                        held = os.fstat(fd)
                        _need(_identity(held) == _identity(before) and held.st_nlink == 1 and held.st_size == item['bytes'], 'FILE_IDENTITY')
                        _write(fd,raw); os.fsync(fd)
                    finally: os.close(fd)
                    content = _read(path,self._limits.file_bytes)
                    item.update(last=self._next,bytes=len(content),sha256=hashlib.sha256(content).hexdigest())
                _new(self.root/_PENDING,_encode(self._cursor(self._next+1,files)))
                _plain(self.root/_CURSOR); _plain(self.root/_PENDING)
                os.replace(self.root/_PENDING,self.root/_CURSOR)
                receipt = LogReceipt(self._next,hashlib.sha256(raw).hexdigest()); self._next += 1
                return receipt
            except BaseException:
                self._blocked = True
                raise LogBlocked('LOG_IO_UNKNOWN') from None
        finally: self._gate.release()

    def close(self):
        _need(self._gate.acquire(blocking=False), 'LOG_BUSY')
        try:
            if self._closed:
                _need(not self._close_failed, 'LOG_IO_UNKNOWN')
                return
            verified = False; failed = False; fd_closed = False
            try: self._held(); verified = True
            except BaseException: failed = True
            if self._fd is not None:
                try:
                    os.close(self._fd); self._fd = None; fd_closed = True
                except BaseException: failed = True
            if verified and fd_closed:
                try:
                    _need(_identity(_plain(self.root/_LOCK)) == self._lock_identity, 'LOCK_IDENTITY')
                    (self.root/_LOCK).unlink()
                except BaseException: failed = True
            self._closed = True
            if failed:
                self._blocked = True; self._close_failed = True
                raise LogBlocked('LOG_IO_UNKNOWN') from None
        finally: self._gate.release()

    def __enter__(self): return self

    def __exit__(self, kind, value, traceback):
        if kind is None: self.close()
        else:
            try: self.close()
            except LogBlocked: self._blocked = True  # Preserve the caller's original error.
        return False
