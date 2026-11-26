"""Root-owned serial execution lane for blocking C/PostgreSQL custody calls.

No DB connections or permissions are created here. A timed-out blocking
operation cannot be killed safely; the entire lane is poisoned and cannot
accept new SQL or stop operations until owner-led process/DB recovery.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Lock, Event
from .grid_writer_fence_model import ResourceFenceBlocked, _need


class LabOwnerExecutor:
    """One bounded serial worker; fail permanently closed after uncertainty."""

    __slots__ = ("_pool", "_lock", "_busy", "_poisoned", "_closed",
                 "_worker_done", "_ever_submitted")

    def __init__(self):
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="lab-root-sql")
        self._lock = Lock()
        self._busy = False
        self._poisoned = False
        self._closed = False
        self._worker_done = Event()
        self._ever_submitted = False

    @property
    def poisoned(self):
        with self._lock:
            return self._poisoned

    @property
    def local_worker_exited(self):
        """Only Python task completion, NOT SQL backend/COMMIT extinction.

        A shielded asyncio Future may appear cancelled while its underlying
        thread continues. This independent event is set in the worker's own
        finally block. Caller must separately obtain C-owned backend/WAL proof.
        """
        with self._lock:
            return self._ever_submitted and self._worker_done.is_set()

    async def call(self, operation, *, timeout=10.0):
        _need(callable(operation) and type(timeout) in (int, float)
              and 0 < timeout <= 30,
              "LAB_ROOT_EXECUTOR_OPERATION_REJECTED")
        with self._lock:
            _need(not self._poisoned and not self._closed and not self._busy,
                  "LAB_ROOT_EXECUTOR_NOT_AVAILABLE")
            self._busy = True
            self._ever_submitted = True
            self._worker_done.clear()
        def bounded_owner_operation():
            try:
                return operation()
            finally:
                self._worker_done.set()
        loop = asyncio.get_running_loop()
        try:
            future = loop.run_in_executor(self._pool, bounded_owner_operation)
            return await asyncio.wait_for(asyncio.shield(future), timeout)
        except BaseException:
            # Cancellation or timeout can leave an in-flight SQL COMMIT.
            # Do not requeue it and do not pretend it was rolled back.
            with self._lock:
                self._poisoned = True
            raise
        finally:
            with self._lock:
                self._busy = False

    def close(self):
        with self._lock:
            self._closed = True
            self._poisoned = True
        # Never wait forever for an uninterruptible backend syscall.
        self._pool.shutdown(wait=False, cancel_futures=True)
