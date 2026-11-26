"""Independent Root-owned bounded OS control lane, never a SQL lane.

A poisoned or blocked SQL worker must not prevent stopping the exact owned
Grid child. This executor owns no connection and cannot issue PostgreSQL SQL.
Timeout/cancellation poisons the control lane; any in-flight OS stop remains
UNKNOWN until independent Root OS identity/listener verification.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from .grid_writer_fence_model import ResourceFenceBlocked, _need
from .runtime_process import ProcessDriver
from .lab_process_extinction import observe_owned_process_extinction


class LabRootStopLane:
    __slots__=("_driver","_pool","_lock","_busy","_poisoned","_closed")

    def __init__(self, driver):
        _need(type(driver) is ProcessDriver,
              "LAB_OS_STOP_OWNER_DRIVER_REQUIRED")
        self._driver=driver
        self._pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix="lab-root-stop")
        self._lock=Lock()
        self._busy=False
        self._poisoned=False
        self._closed=False

    @property
    def poisoned(self):
        with self._lock:
            return self._poisoned

    async def _run(self, fn, *, timeout):
        _need(type(timeout) in (int,float) and 0<timeout<=30,
              "LAB_OS_STOP_TIMEOUT_INVALID")
        with self._lock:
            _need(not self._poisoned and not self._closed and not self._busy,
                  "LAB_OS_STOP_LANE_UNAVAILABLE")
            self._busy=True
        try:
            future=asyncio.get_running_loop().run_in_executor(self._pool,fn)
            return await asyncio.wait_for(asyncio.shield(future),timeout)
        except BaseException:
            with self._lock:
                self._poisoned=True
            raise
        finally:
            with self._lock:
                self._busy=False

    async def stop_owned(self, handle, *, timeout=10.0):
        _need(type(handle) is str and handle in self._driver.children,
              "LAB_OS_STOP_UNKNOWN_CHILD")
        return await self._run(lambda: self._driver.stop(handle),timeout=timeout)

    async def old_child_extinct(self, handle, *, timeout=10.0):
        _need(type(handle) is str and handle in self._driver.children,
              "LAB_OS_STOP_UNKNOWN_CHILD")
        return await self._run(
            lambda: observe_owned_process_extinction(self._driver, handle),
            timeout=timeout)

    def close(self):
        with self._lock:
            self._closed=True
            self._poisoned=True
        # close() does NOT prove the stopped child or OS thread is extinct.
        self._pool.shutdown(wait=False,cancel_futures=True)
