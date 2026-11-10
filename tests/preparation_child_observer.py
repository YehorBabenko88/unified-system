"""Bounded test-only observation; no process/pipe/cleanup/authority ownership.

Import/qualification and qualifier hooks require a separate Root allocation.
Only communicate_timeout may poll a retained object or query thread liveness.
"""
import hashlib
import json


_MISSING = object()


class PreparationChildObserver:
    MAX_CHILDREN = 1
    MAX_EVENTS = 8
    HASH_PREFIX_BYTES = 256
    MAX_EXPORT_BYTES = 16384
    _MAX_DROPPED = 2147483647

    def __init__(self):
        self._events = []
        self._child = None
        self._reserved = False
        self._constructor_start = None
        self._communicate_start = None
        self._last_ns = 0
        self._phase = 'NEW'
        self._dropped = 0
        self._incomplete = False

    def _when(self, at_ns):
        if type(at_ns) is not int or not 0 <= at_ns < 2**63 or at_ns < self._last_ns:
            raise ValueError('invalid observation counter')

    def _token(self, token):
        if type(token) is not int or token != 1 or not self._reserved:
            raise ValueError('unknown observation token')

    def _space(self):
        if len(self._events) < self.MAX_EVENTS:
            return True
        self._drop()
        return False

    def _drop(self):
        self._dropped = min(self._dropped + 1, self._MAX_DROPPED)
        self._incomplete = True

    def _append(self, kind, at_ns, **fields):
        self._events.append(dict(kind=kind, token=1, at_ns=at_ns, **fields))
        self._last_ns = at_ns

    def begin_constructor(self, *, at_ns):
        self._when(at_ns)
        if self._reserved:
            self._drop()
            return None
        if not self._space():
            return None
        self._reserved = True
        self._constructor_start = at_ns
        self._phase = 'CONSTRUCTOR'
        self._append('CONSTRUCTOR_BEGIN', at_ns)
        return 1

    def end_constructor(self, token, child, *, at_ns):
        self._when(at_ns)
        if token is None:
            self._incomplete = True
            return
        self._token(token)
        if self._phase != 'CONSTRUCTOR' or child is None:
            raise ValueError('invalid constructor observation')
        if not self._space():
            return
        # Preserve the original object; no wrapper, PID reopen or child method.
        self._child = child
        try:
            pid = getattr(child, 'pid', None)
        except Exception:
            pid = None
        if type(pid) is not int or not 0 < pid < 2**32:
            pid = None
            self._incomplete = True
        self._phase = 'CONSTRUCTED'
        self._append('CONSTRUCTOR_END', at_ns, pid=pid,
                     elapsed_ns=at_ns - self._constructor_start)

    def constructor_failed(self, token, *, at_ns):
        self._when(at_ns)
        self._token(token)
        if self._phase != 'CONSTRUCTOR':
            raise ValueError('invalid constructor observation')
        if not self._space():
            return
        self._phase = 'CONSTRUCTOR_ERROR'
        self._append('CONSTRUCTOR_ERROR', at_ns,
                     elapsed_ns=at_ns - self._constructor_start)

    def _communication(self, token, at_ns, *, started=False):
        self._when(at_ns)
        self._token(token)
        if self._phase != 'CONSTRUCTED' or self._child is None:
            raise ValueError('no retained observation child')
        if not started and self._communicate_start is None:
            raise ValueError('no communicate start observation')

    def begin_communicate(self, token, *, at_ns):
        self._communication(token, at_ns, started=True)
        if not self._space():
            return
        self._communicate_start = at_ns
        self._append('COMMUNICATE_BEGIN', at_ns)

    def end_communicate(self, token, *, at_ns):
        self._communication(token, at_ns)
        if not self._space():
            return
        self._append('COMMUNICATE_END', at_ns,
                     elapsed_ns=at_ns - self._communicate_start)
        self._communicate_start = None

    def _poll(self):
        try:
            code = self._child.poll()
        except Exception:
            self._incomplete = True
            return dict(state='ERROR', returncode=None)
        if code is None:
            return dict(state='RUNNING', returncode=None)
        if type(code) is int and -(2**63) <= code < 2**63:
            return dict(state='EXITED', returncode=code)
        self._incomplete = True
        return dict(state='UNSUPPORTED', returncode=None)

    def _thread(self, name):
        try:
            thread = getattr(self._child, name, _MISSING)
            if thread is _MISSING:
                self._incomplete = True
                return 'ABSENT'
            alive = thread.is_alive()
        except Exception:
            self._incomplete = True
            return 'ERROR'
        if type(alive) is not bool:
            self._incomplete = True
            return 'UNSUPPORTED'
        return 'ALIVE' if alive else 'STOPPED'

    def _buffer(self, name):
        def unknown(state):
            self._incomplete = True
            return dict(state=state, chunks=None, bytes=None,
                        prefix_bytes=None, prefix_sha256=None)
        try:
            buffer = getattr(self._child, name, _MISSING)
            if buffer is _MISSING:
                return unknown('ABSENT')
            if type(buffer) is not list:
                return unknown('UNSUPPORTED')
            if len(buffer) == 0:
                return dict(state='EMPTY', chunks=0, bytes=0,
                            prefix_bytes=0, prefix_sha256=None)
            if len(buffer) != 1 or type(buffer[0]) is not bytes:
                return unknown('UNSUPPORTED')
            value = buffer[0]
            count = min(self.HASH_PREFIX_BYTES, len(value))
            return dict(state='PRESENT', chunks=1, bytes=len(value),
                        prefix_bytes=count,
                        prefix_sha256=hashlib.sha256(value[:count]).hexdigest())
        except Exception:
            return unknown('ERROR')

    def communicate_timeout(self, token, *, at_ns):
        self._communication(token, at_ns)
        # Refuse extra observation before touching child/thread/buffer metadata.
        if not self._space():
            return
        poll = self._poll()
        stdout_thread = self._thread('stdout_thread')
        stderr_thread = self._thread('stderr_thread')
        stdout_buffer = self._buffer('_stdout_buff')
        stderr_buffer = self._buffer('_stderr_buff')
        self._append('COMMUNICATE_TIMEOUT', at_ns,
                     elapsed_ns=at_ns - self._communicate_start, poll=poll,
                     stdout_thread=stdout_thread, stderr_thread=stderr_thread,
                     stdout_buffer=stdout_buffer, stderr_buffer=stderr_buffer)

    def export_json(self):
        # No raw child/pipe references leave the helper; no filesystem output.
        value = dict(schema='preparation.child-observer.v1-review1',
                     events=self._events, retained_children=int(self._child is not None),
                     dropped_events=self._dropped, incomplete=self._incomplete)
        raw = json.dumps(value, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=True, allow_nan=False).encode('ascii')
        if len(raw) > self.MAX_EXPORT_BYTES:
            raise ValueError('observation export bound')
        return raw
