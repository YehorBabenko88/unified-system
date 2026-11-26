"""E Root-only dispatcher for independent C-owned LAB PostgreSQL recovery.

This actuator is separate from the potentially poisoned normal SQL worker.
It owns NO SQL connection, no new database, and cannot kill a PID. Only the
existing *same* C LabPostgres owner object may stop its own disposable PG18
cluster after verifying private root/postmaster ownership. Until C provides a
native old-backend/fence/WAL witness, the outcome is UNKNOWN and no successor
generation/epoch is authorized.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Lock

from .grid_writer_fence_model import ResourceFenceBlocked, _need


@dataclass(frozen=True)
class LabPgRecoveryObservation:
    schema: str
    state: str
    old_postmaster_pid: int
    isolated_cluster_stopped: bool
    old_backend_extinct: bool = False
    durable_fence_verified: bool = False
    wal_reconciled: bool = False
    native_admitted: bool = False

    def __post_init__(self):
        _need(self.schema=="unified.root-lab-pg-recovery-observation.v1"
              and self.state in ("UNKNOWN", "STILL_ALIVE", "EXTINCT")
              and type(self.old_postmaster_pid) is int
              and self.old_postmaster_pid>1
              and self.native_admitted is False,
              "LAB_PG_RECOVERY_OBSERVATION_INVALID")


class LabPgRecoveryLane:
    """Independent bounded stop actuator; no arbitrary backend PID kill."""

    __slots__=("_pg","_pool","_lock","_busy","_poisoned","_closed")

    def __init__(self, pg):
        # C module absent from standalone E branch. Resolve the exact C
        # owner CLASS only when it exists in the F-integrated source tree.
        from .lab_postgres import LabPostgres
        _need(type(pg) is LabPostgres and type(pg.major) is int and pg.major==18
              and type(pg.port) is int and pg.port!=5432
              and pg.started is True,
              "LAB_PG_RECOVERY_DEDICATED_OWNER_REQUIRED")
        pg._verify_owned()
        pg._verify_postmaster()
        self._pg=pg
        self._pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix="lab-root-pg-recovery")
        self._lock=Lock()
        self._busy=False
        self._poisoned=False
        self._closed=False

    @property
    def poisoned(self):
        with self._lock:return self._poisoned

    async def stop_dedicated_cluster(self, *, timeout=30.0):
        """Root must reconcile C-owned WAL/fence before any restart/admit.

        On partial stop / timeout, all later actions remain UNKNOWN. Never
        treat missing pidfile/port by itself as postmaster or backend proof.
        """
        _need(type(timeout) in (int,float) and 0<timeout<=30,
              "LAB_PG_RECOVERY_TIMEOUT_INVALID")
        with self._lock:
            _need(not self._closed and not self._poisoned and not self._busy,
                  "LAB_PG_RECOVERY_LANE_UNAVAILABLE")
            self._busy=True
        try:
            def stop_exact_owner():
                self._pg._verify_owned()
                old_pid=self._pg._verify_postmaster()
                self._pg.stop()
                # C stop already requires exact owned postgres root and
                # postmaster identity. Its return is NOT backend extinction.
                self._pg._verify_owned()
                return old_pid
            future=asyncio.get_running_loop().run_in_executor(
                self._pool,stop_exact_owner)
            old_pid=await asyncio.wait_for(asyncio.shield(future),timeout)
            return LabPgRecoveryObservation(
                "unified.root-lab-pg-recovery-observation.v1",
                "UNKNOWN",old_pid,isolated_cluster_stopped=True)
        except BaseException:
            with self._lock:self._poisoned=True
            raise
        finally:
            with self._lock:self._busy=False

    def close(self):
        with self._lock:
            self._closed=True
            self._poisoned=True
        self._pool.shutdown(wait=False,cancel_futures=True)
