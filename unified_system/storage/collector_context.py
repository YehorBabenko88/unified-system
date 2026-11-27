"""Local Collector lifetime over EXISTING ObjectStore/Journal; no authority.

Kernel file ownership is local only. Flags/checkpoints are UNKNOWN custody,
not leases, source continuity, committed datasets or physical durability proof.
"""
from dataclasses import dataclass, asdict
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import uuid

from ..journal import Journal
from .object_store import ObjectStore, _parents, _plain, _read, _write_new
from .raw_capture import RawCaptureAdapter, RawCaptureProfile


class CollectorBlocked(ValueError):
    pass


def _need(value, code='COLLECTOR_CONTEXT_REJECTED'):
    if not value: raise CollectorBlocked(code)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def _sha(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def _reason(value):
    _need(type(value) is str and re.fullmatch('[A-Za-z0-9_.:-]{1,128}', value) is not None)
    return value


@dataclass(frozen=True)
class CollectorContextProfile:
    raw_profile: RawCaptureProfile
    lifecycle_headroom_bytes: int
    max_lifecycle_records: int = 128
    max_context_bytes: int = 16777216

    def check(self):
        _need(type(self.raw_profile) is RawCaptureProfile)
        self.raw_profile.check()
        for value, ceiling, floor in ((self.lifecycle_headroom_bytes, 16777216, 1),
                (self.max_lifecycle_records, 128, 8), (self.max_context_bytes, 16777216, 1)):
            _need(type(value) is int and floor <= value <= ceiling)
        _need(self.lifecycle_headroom_bytes <= self.max_context_bytes)


@dataclass(frozen=True)
class LocalCollectorCheckpoint:
    context_id: str
    observation_sha256: str
    raw_journal_digest: str
    local_lifecycle_sequence: int
    native_outcome = property(lambda self: 'UNKNOWN')
    publication_confirmed = property(lambda self: False)


@dataclass(frozen=True)
class CollectorContextStatus:
    context_id: str
    state: str
    writer_owned: bool | None
    operation_active: bool
    pending_observation_sha256: str | None
    provider_continuity = property(lambda self: 'UNKNOWN')
    publication_confirmed = property(lambda self: False)


class CollectorContext:
    """One Root-owned LOCAL writer. No reopen/reset from UNKNOWN or TERMINAL."""
    @staticmethod
    def _inputs(root, context_id, store_id, binding_sha256, profile):
        root = Path(root)
        _need(root.is_absolute() and '..' not in root.parts)
        _need(type(context_id) is str and re.fullmatch('[0-9a-f]{32}', context_id) is not None)
        _need(type(store_id) is str and re.fullmatch(
            '[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}', store_id) is not None)
        _need(_sha(binding_sha256) and type(profile) is CollectorContextProfile)
        profile.check()
        return root

    @staticmethod
    def _kernel(fd, acquire):
        os.lseek(fd, 0, os.SEEK_SET)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(fd, msvcrt.LK_NBLCK if acquire else msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB if acquire else fcntl.LOCK_UN)

    @classmethod
    def _own(cls, root):
        path = root/'writer.lock'
        before = _plain(path, directory=False)
        _need(before.st_size == 1)
        fd = os.open(path, os.O_RDWR | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0))
        try:
            info = os.fstat(fd)
            _need((info.st_dev, info.st_ino, info.st_nlink) == (before.st_dev, before.st_ino, 1))
            try: cls._kernel(fd, True)
            except OSError: raise CollectorBlocked('COLLECTOR_WRITER_BUSY') from None
            return fd
        except BaseException:
            os.close(fd)
            raise

    @classmethod
    def create(cls, root, *, context_id, store_id, binding_sha256, profile):
        root = cls._inputs(root, context_id, store_id, binding_sha256, profile)
        _parents(root.parent)
        root.mkdir(exist_ok=False)
        _write_new(root/'writer.lock', b'D')
        fd = cls._own(root)
        try:
            (root/'raw').mkdir(exist_ok=False)
            store = ObjectStore.create(root/'raw'/'archive', store_id=store_id)
            for path in (root/'raw'/'capture.sqlite', root/'lifecycle.sqlite'):
                with path.open('xb'): pass
                Journal(path).initialize()
            context = cls(root, context_id, store_id, binding_sha256, profile, fd, store)
            _write_new(root/'collector-owned.json', context._marker)
            context._event('OPEN')
            context.require_ready()
            return context
        except BaseException as primary:
            try: os.close(fd)
            except BaseException as cleanup:
                raise BaseExceptionGroup('collector create/close uncertainty', [primary, cleanup]) from None
            raise

    @classmethod
    def open(cls, root, *, context_id, store_id, binding_sha256, profile):
        root = cls._inputs(root, context_id, store_id, binding_sha256, profile)
        _parents(root)
        fd = cls._own(root)
        try:
            store = ObjectStore.open(root/'raw'/'archive', store_id=store_id)
            context = cls(root, context_id, store_id, binding_sha256, profile, fd, store)
            context._check()
            rows = context._scan()
            flag = context._flag()
            if context._state == 'TERMINAL' or flag == b'T':
                context._memory_terminal, context._state = True, 'TERMINAL'
            elif context._state == 'UNKNOWN' or flag != b'S' or context._state != 'STOPPED':
                context._unknown('unclean_reopen')
            else:
                if len(rows)+4 > profile.max_lifecycle_records:
                    context._unknown('lifecycle_capacity_exhausted')
                    return context
                context._flag(b'D')
                context._event('OPEN')
                try: context.require_ready()
                except Exception: context._unknown('reopen_validation_failed')
            return context
        except BaseException as primary:
            try: os.close(fd)
            except BaseException as cleanup:
                raise BaseExceptionGroup('collector open/close uncertainty', [primary, cleanup]) from None
            raise

    def __init__(self, root, context_id, store_id, binding_sha256, profile, fd, store):
        self.root, self.context_id = root, context_id
        self._binding, self._profile, self._fd = binding_sha256, profile, fd
        self._busy, self._closed, self._memory_unknown = threading.Lock(), False, False
        self._memory_terminal = False
        self._incarnation = str(uuid.uuid4())
        self._life = Journal(root/'lifecycle.sqlite')
        self._adapter = RawCaptureAdapter(store, Journal(root/'raw'/'capture.sqlite'), profile.raw_profile)
        self._state, self._pending, self._checkpoint, self._completed = None, None, None, {}
        identity = lambda path: list((_plain(path, directory=True).st_dev, _plain(path, directory=True).st_ino))
        lock = os.fstat(fd)
        self._lock_identity = lock.st_dev, lock.st_ino
        self._marker = _canonical(dict(schema='unified.storage.collector-context.v1',
            context_id=context_id, store_id=store_id, binding_sha256=binding_sha256,
            root=str(root), root_identity=identity(root), raw_identity=identity(root/'raw'),
            writer_lock_identity=list(self._lock_identity), profile=asdict(profile)))

    def _flag(self, value=None):
        _need(self._fd is not None and not self._closed, 'COLLECTOR_CLOSED')
        info = os.fstat(self._fd)
        current = _plain(self.root/'writer.lock', directory=False)
        _need((info.st_dev, info.st_ino) == self._lock_identity == (current.st_dev, current.st_ino)
              and info.st_size == current.st_size == 1 and info.st_nlink == current.st_nlink == 1)
        os.lseek(self._fd, 0, os.SEEK_SET)
        if value is not None:
            _need(value in (b'D', b'S', b'U', b'T'))
            _need(os.write(self._fd, value) == 1)
            os.fsync(self._fd)
            os.lseek(self._fd, 0, os.SEEK_SET)
        flag = os.read(self._fd, 1)
        _need(flag in (b'D', b'S', b'U', b'T'))
        return flag

    def _check(self):
        _parents(self.root)
        _need(_read(self.root/'collector-owned.json', 8192)[0] == self._marker)
        self._flag()
        _plain(self._life.path, directory=False)
        for suffix in ('-wal', '-shm', '-journal'):
            sidecar = self._life.path.with_name(self._life.path.name+suffix)
            _need(not sidecar.exists() and not sidecar.is_symlink(), 'COLLECTOR_RECOVERY_REQUIRED')

    def _scan(self):
        self._check()
        rows = self._life.read()
        _need(len(rows) <= self._profile.max_lifecycle_records)
        state, pending, checkpoint, completed = None, None, None, {}
        fields = {'schema','context_id','binding_sha256','event','writer_incarnation_id',
                  'observation_sha256','raw_journal_digest','reason'}
        for row in rows:
            value = row['receipt']
            _need(row['state'] == 'OBSERVING' and type(value) is dict and set(value) == fields)
            _need(value['schema'] == 'unified.storage.collector-lifecycle.v1'
                  and value['context_id'] == self.context_id and value['binding_sha256'] == self._binding)
            _need(type(value['writer_incarnation_id']) is str and re.fullmatch(
                '[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}',
                value['writer_incarnation_id']) is not None)
            event, obs, digest, reason = (value[k] for k in ('event','observation_sha256','raw_journal_digest','reason'))
            _need(obs is None or _sha(obs)); _need(digest is None or _sha(digest))
            if reason is not None: _reason(reason)
            if event == 'OPEN':
                _need(state in (None,'STOPPED') and pending is None and obs is digest is reason is None)
                state = 'ACTIVE'
            elif event == 'INFLIGHT':
                _need(state == 'ACTIVE' and pending is None and obs is not None and digest is reason is None)
                pending = obs
            elif event == 'CHECKPOINT':
                _need(state == 'ACTIVE' and pending == obs and obs is not None and digest is not None and reason is None)
                checkpoint = LocalCollectorCheckpoint(self.context_id, obs, digest, row['sequence'])
                completed[obs] = checkpoint; pending = None
            elif event == 'STOPPED':
                _need(state == 'ACTIVE' and pending is None and obs is digest is None and reason is not None)
                state = 'STOPPED'
            elif event in ('UNKNOWN','TERMINAL'):
                _need(reason is not None and digest is None)
                _need(state not in ('UNKNOWN','TERMINAL') or event == state)
                state = event
            else: raise CollectorBlocked('COLLECTOR_RECOVERY_REQUIRED')
        self._state = 'UNKNOWN' if self._memory_unknown else 'TERMINAL' if self._memory_terminal else state
        self._pending, self._checkpoint, self._completed = pending, checkpoint, completed
        return rows

    def _event(self, event, obs=None, digest=None, reason=None):
        rows = self._scan()
        _need(len(rows) < self._profile.max_lifecycle_records, 'COLLECTOR_CAPACITY_EXCEEDED')
        receipt = dict(schema='unified.storage.collector-lifecycle.v1', context_id=self.context_id,
            binding_sha256=self._binding, event=event, writer_incarnation_id=self._incarnation,
            observation_sha256=obs, raw_journal_digest=digest, reason=reason)
        self._life.append('OBSERVING', receipt, expected_sequence=len(rows))
        self._scan()

    def _unknown(self, reason):
        prior = self._state
        self._flag(b'U')
        try:
            if prior not in ('UNKNOWN','TERMINAL') and len(self._scan()) < self._profile.max_lifecycle_records:
                self._event('UNKNOWN', obs=self._pending, reason=_reason(reason))
        finally:
            self._memory_unknown, self._state = True, 'UNKNOWN'

    def _footprint(self):
        store = self.root/'raw'/'archive'
        allowed = {self.root:{'collector-owned.json','writer.lock','lifecycle.sqlite','raw'},
                   self.root/'raw':{'archive','capture.sqlite'},
                   store:{'owned-root.json','objects','staging'}}
        size, count = 0, 0
        directories = {self.root/'raw',store,store/'objects',store/'staging'}
        for folder in (*allowed, store/'objects', store/'staging'):
            names = set()
            for path in folder.iterdir():
                _need(len(names) < self._profile.raw_profile.inventory_file_limit+4)
                names.add(path.name)
                if path in directories: _plain(path, directory=True); continue
                count += 1; _need(count <= self._profile.raw_profile.inventory_file_limit+3)
                size += _plain(path, directory=False).st_size
            if folder in allowed: _need(names == allowed[folder])
        _need(size <= self._profile.max_context_bytes, 'COLLECTOR_CAPACITY_EXCEEDED')
        return size

    def _ready(self, additional_bytes=0, records=0, payload_count=None):
        _need(not self._closed and self._fd is not None, 'COLLECTOR_CLOSED')
        rows = self._scan()
        _need(self._state == 'ACTIVE' and self._pending is None, 'COLLECTOR_READ_ONLY')
        _need(len(rows)+records <= self._profile.max_lifecycle_records, 'COLLECTOR_CAPACITY_EXCEEDED')
        links = self._adapter._records()
        self._adapter._inventory(links)
        if payload_count is not None:
            _need(len(links) < self._profile.raw_profile.max_observations
                  and sum(link['payload_byte_count'] for link, _ in links.values())+payload_count
                  <= self._profile.raw_profile.max_payload_occurrence_bytes, 'COLLECTOR_CAPACITY_EXCEEDED')
        size = self._footprint()
        _need(size+2*additional_bytes+self._profile.lifecycle_headroom_bytes
              +self._profile.raw_profile.sqlite_headroom_bytes <= self._profile.max_context_bytes,
              'COLLECTOR_CAPACITY_EXCEEDED')

    def require_ready(self):
        _need(self._busy.acquire(False), 'COLLECTOR_IO_INFLIGHT')
        try: self._ready(records=3, payload_count=0)
        finally: self._busy.release()

    def status(self):
        if not self._closed: self._scan()
        owned = None if self._closed and self._fd is not None else self._fd is not None
        return CollectorContextStatus(self.context_id, 'CLOSED' if self._closed else self._state,
            owned, self._busy.locked(), self._pending)

    async def store_capture(self, *, observation_bytes, payload_bytes):
        _need(type(observation_bytes) is bytes and 1 <= len(observation_bytes) <= 16384
              and (payload_bytes is None or type(payload_bytes) is bytes and len(payload_bytes) <= 1048576))
        _need(self._busy.acquire(False), 'COLLECTOR_IO_INFLIGHT')
        try:
            self._ready()
            obs = hashlib.sha256(observation_bytes).hexdigest()
            if obs in self._completed:
                try:
                    return await self._adapter.store_capture(observation_bytes=observation_bytes, payload_bytes=payload_bytes)
                except BaseException as primary:
                    try: self._unknown('capture_replay_outcome_unknown')
                    except BaseException as cleanup:
                        raise BaseExceptionGroup('collector replay/unknown persistence uncertainty', [primary, cleanup]) from None
                    raise
            payload_count = 0 if payload_bytes is None else len(payload_bytes)
            self._ready(len(observation_bytes)+payload_count, records=3, payload_count=payload_count)
            try:
                self._event('INFLIGHT', obs=obs)
                facts = await self._adapter.store_capture(observation_bytes=observation_bytes, payload_bytes=payload_bytes)
                _need(await self._adapter.read_capture(obs) == facts, 'COLLECTOR_RECOVERY_REQUIRED')
                self._event('CHECKPOINT', obs=obs, digest=facts.journal_record_digest)
                self._footprint()
                return facts
            except BaseException as primary:
                try: self._unknown('capture_outcome_unknown')
                except BaseException as cleanup:
                    raise BaseExceptionGroup('collector capture/unknown persistence uncertainty', [primary, cleanup]) from None
                raise
        finally: self._busy.release()

    async def read_capture(self, observation_sha256):
        _need(not self._closed and self._busy.acquire(False), 'COLLECTOR_IO_INFLIGHT')
        try:
            self._scan()
            return await self._adapter.read_capture(observation_sha256)
        finally: self._busy.release()

    async def read_history(self):
        _need(not self._closed and self._busy.acquire(False), 'COLLECTOR_IO_INFLIGHT')
        try:
            self._scan()
            return tuple([await self._adapter.read_capture(key) for key in self._adapter._records()])
        finally: self._busy.release()

    async def checkpoint(self):
        _need(not self._closed and self._busy.acquire(False), 'COLLECTOR_IO_INFLIGHT')
        try:
            self._scan(); value = self._checkpoint
            _need(value is not None, 'COLLECTOR_CHECKPOINT_UNAVAILABLE')
            facts = await self._adapter.read_capture(value.observation_sha256)
            _need(facts.journal_record_digest == value.raw_journal_digest, 'COLLECTOR_RECOVERY_REQUIRED')
            return value
        finally: self._busy.release()

    async def stop(self, reason='normal_stop'):
        _reason(reason)
        _need(not self._closed and self._busy.acquire(False), 'COLLECTOR_IO_INFLIGHT')
        try:
            self._scan()
            if self._state == 'ACTIVE':
                _need(self._pending is None, 'COLLECTOR_RECOVERY_REQUIRED')
                try:
                    self._event('STOPPED', reason=reason)
                    self._flag(b'S')
                except BaseException as primary:
                    try: self._unknown('stop_outcome_unknown')
                    except BaseException as cleanup:
                        raise BaseExceptionGroup('collector stop/unknown uncertainty', [primary, cleanup]) from None
                    raise
        finally: self._busy.release()
        return self.status()

    async def mark_terminal(self, reason):
        _reason(reason)
        _need(not self._closed and self._busy.acquire(False), 'COLLECTOR_IO_INFLIGHT')
        try:
            self._scan()
            if self._state not in ('UNKNOWN','TERMINAL'):
                self._flag(b'T')
                self._memory_terminal = True
                self._event('TERMINAL', obs=self._pending, reason=reason)
        finally: self._busy.release()
        return self.status()

    def close(self):
        if self._closed: return
        _need(self._busy.acquire(False), 'COLLECTOR_IO_INFLIGHT')
        errors = []
        try:
            try:
                self._scan()
                if self._state not in ('STOPPED','UNKNOWN','TERMINAL'):
                    self._unknown('close_without_clean_stop')
            except BaseException as error: errors.append(error)
            try: self._kernel(self._fd, False)
            except BaseException as error: errors.append(error)
            try:
                os.close(self._fd)
                self._fd = None
            except BaseException as error: errors.append(error)
            self._closed = True
        finally: self._busy.release()
        if errors: raise BaseExceptionGroup('collector close uncertainty; retained state', errors)
