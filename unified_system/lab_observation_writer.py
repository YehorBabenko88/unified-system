"""Non-authorizing v2 producer; no market, execution or source-attestation logic.

The validator callable MUST come from the caller's admitted Terminan closure.
Neither a callback, a path nor the resulting JSON proves admission. A runtime
must supply require_current and an ACL-protected private parent. This module
does not set ACLs or defend a namespace writable by a hostile same-user process.

Each writer exclusively creates a fresh namespace and owns it for its lifetime.
Existing namespaces are NEVER adopted, including after a crash. Recovery and
protected-runtime/source wiring remain separate unimplemented integration work.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import threading
import uuid

LIMIT = 2097152
MAX_INT = 9007199254740991
NAMES = ('market', 'paper', 'fleet')


class ObservationRejected(ValueError):
    """Closed error: never include upstream errors, paths or secrets."""


class ExportBlocked(Exception):
    """A source may explicitly report its existing exporter is blocked."""


def _need(condition):
    if not condition:
        raise ObservationRejected('OBSERVATION_REJECTED')


def _label(value):
    _need(type(value) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,64}', value) is not None
          and 'ADMINIT' not in value.upper())
    return value


def _integer(value, positive=False):
    _need(type(value) is int and (1 if positive else 0) <= value <= MAX_INT)
    return value


def _raw(value):
    # Bound before json.dumps: cyclic or explosive caller objects cannot cause
    # unbounded recursion, allocations or custom serialization callbacks.
    stack = [(value, 0)]; count = 0
    while stack:
        item, depth = stack.pop(); count += 1
        _need(count <= 100000 and depth <= 16)
        if type(item) is dict:
            _need(len(item) <= 1024 and all(type(k) is str and len(k) <= 128 for k in item))
            stack.extend((child, depth+1) for child in item.values())
        elif type(item) is list:
            _need(len(item) <= 1024); stack.extend((child, depth+1) for child in item)
        elif type(item) is str:
            _need(len(item) <= 4096)
        elif type(item) is int:
            _need(abs(item) <= MAX_INT)
        else:
            _need(item is None or type(item) in (bool, float))
    try:
        raw = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                         allow_nan=False).encode('ascii')
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise ObservationRejected('OBSERVATION_REJECTED') from None
    _need(len(raw) <= LIMIT)
    return raw


def _unavailable(code):
    return dict(state='UNAVAILABLE', error_code=code, payload=None)


def assemble(*, release_id, run_id, sequence, generated_at_ms, validate, sources):
    """Call each configured exporter once and preserve its exact JSON values.

    ``sources`` contains zero to three no-argument export callables. Validation
    is delegated to the existing admitted Term v2 validator, never duplicated.
    No source error is copied to a report. SOURCE_NOT_CONFIGURED is different
    from an exporter returning a valid empty observation envelope.
    """
    _need(callable(validate) and type(sources) is dict and set(sources) <= set(NAMES))
    _need(all(callable(source) for source in sources.values()))
    value = dict(schema='unified.lab.market-paper.v2', mode='LAB_SIMULATION',
                 trading_authorized=False, authority='REPORTED_UNATTESTED',
                 release_id=_label(release_id), run_id=_label(run_id),
                 sequence=_integer(sequence, True), generated_at_ms=_integer(generated_at_ms, True),
                 sections={name: _unavailable('SOURCE_NOT_CONFIGURED') for name in NAMES})
    for name in NAMES:
        if name not in sources:
            continue
        try:
            payload = sources[name]()
        except ExportBlocked:
            value['sections'][name] = _unavailable('EXPORT_BLOCKED'); continue
        except Exception:
            value['sections'][name] = _unavailable('SOURCE_UNAVAILABLE'); continue
        try:
            payload = json.loads(_raw(payload))
            candidate = json.loads(_raw(value))
            candidate['sections'][name] = dict(state='AVAILABLE', error_code=None, payload=payload)
            # Validate a detached copy: even an accidentally mutating validator
            # cannot rewrite reported source fields or escape qualification flags.
            validate(json.loads(_raw(candidate)), generated_at_ms)
            value = candidate
        except Exception:
            value['sections'][name] = _unavailable('VALIDATION_FAILED')
    try:
        validate(json.loads(_raw(value)), generated_at_ms)
    except Exception:
        raise ObservationRejected('OBSERVATION_REJECTED') from None
    return value


def _identity(path, *, directory=False):
    info = path.lstat()
    _need(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400)
    _need(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode) and info.st_nlink == 1)
    return info.st_dev, info.st_ino


def _parents(path):
    _need(path.is_absolute() and '..' not in path.parts and not str(path).startswith(('\\\\', '//')))
    _need(':' not in str(path)[len(path.drive):])
    return tuple((parent, _identity(parent, directory=True)) for parent in reversed(path.parents))


def _file(path):
    initial = _identity(path)
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0))
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        _need((info.st_dev, info.st_ino) == initial and info.st_nlink == 1 and info.st_size <= LIMIT)
        raw = stream.read(LIMIT+1); after = os.fstat(stream.fileno())
        _need((info.st_size, info.st_mtime_ns, info.st_ino) == (after.st_size, after.st_mtime_ns, after.st_ino))
        _need(_identity(path) == initial and len(raw) <= LIMIT)
    return initial, hashlib.sha256(raw).hexdigest()


def _replace_snapshot(temporary,path,*,existing):
    if os.name!='nt' or not existing:
        os.replace(temporary,path);return
    import ctypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    replace=kernel.ReplaceFileW
    replace.argtypes=[ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_void_p]
    replace.restype=ctypes.c_int
    # ReplaceFile supports existing delete-shared readers and preserves ACLs.
    # No ignore-ACL flags, retries, copy fallback, or foreign path adoption.
    if not replace(str(path),str(temporary),None,0,None,None):
        raise ctypes.WinError(ctypes.get_last_error())


class SnapshotWriter:
    """Single lifetime writer: exclusive namespace + thread lock + sequence CAS.

    The persistent lock is deliberately not deleted/adopted after a crash. This
    is a display producer, not a durable consensus/recovery or admission broker.
    """
    @classmethod
    def create(cls, root, *, release_id, run_id, validate, require_current):
        _need(callable(validate) and callable(require_current))
        result = cls()
        result.release_id = _label(release_id); result.run_id = _label(run_id)
        result.validate = validate; result.require_current = require_current
        result.root = Path(root); result.path = result.root/'snapshot.json'
        result._parents = _parents(result.root)
        result._lock = threading.Lock(); result._fd = None
        result._sequence = 0; result._expected = None; result._closed = True
        result._admitted()
        try:
            # Never reuse or inspect an existing foreign namespace as ownership.
            result.root.mkdir(mode=0o700)
            result._root_identity = _identity(result.root, directory=True)
            lock = result.root/'.writer.lock'
            result._fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_RDWR | getattr(os, 'O_BINARY', 0), 0o600)
            os.write(result._fd, b'1'); os.fsync(result._fd)
            result._lock_identity = _identity(lock)
            result._closed = False
            result._check()
        except (OSError, ObservationRejected):
            if result._fd is not None: os.close(result._fd)
            result._fd = None
            # Retain failed fresh state; do not remove/adopt anything.
            raise ObservationRejected('OBSERVATION_REJECTED') from None
        return result

    def _admitted(self):
        try: _need(self.require_current() is True)
        except Exception: raise ObservationRejected('OBSERVATION_REJECTED') from None

    def _check(self):
        self._admitted(); _need(not self._closed)
        for path, identity in self._parents:
            _need(_identity(path, directory=True) == identity)
        _need(_identity(self.root, directory=True) == self._root_identity)
        _need(_identity(self.root/'.writer.lock') == self._lock_identity)
        _need((os.fstat(self._fd).st_dev, os.fstat(self._fd).st_ino) == self._lock_identity)
        if self._expected is None:
            _need(not self.path.exists() and not self.path.is_symlink())
        else:
            _need(_file(self.path) == self._expected)

    def publish(self, *, expected_sequence, generated_at_ms, sources):
        with self._lock:
            try:
                self._check(); _integer(expected_sequence)
                _need(expected_sequence == self._sequence)
                value = assemble(release_id=self.release_id, run_id=self.run_id,
                                 sequence=self._sequence+1, generated_at_ms=generated_at_ms,
                                 validate=self.validate, sources=sources)
                raw = _raw(value); self._check()
                temporary = self.root/('.snapshot-'+uuid.uuid4().hex+'.tmp')
                fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, 'O_BINARY', 0), 0o600)
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(raw); stream.flush(); os.fsync(stream.fileno())
                staged = _file(temporary)
                self._check(); _need(staged == _file(temporary))
                # Atomic visibility for the existing Term reader. Protected
                # parent admission excludes noncooperating path mutation races.
                _replace_snapshot(temporary,self.path,existing=self._expected is not None)
                _need(_file(self.path) == staged)
                self._expected = staged; self._sequence += 1
                return value
            except (OSError, ObservationRejected):
                raise ObservationRejected('OBSERVATION_REJECTED') from None

    def close(self):
        with self._lock:
            if self._fd is not None:
                os.close(self._fd); self._fd = None
            self._closed = True
