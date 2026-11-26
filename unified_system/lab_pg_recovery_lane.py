"""Root supervisor dispatch for the ONE C-owned PostgreSQL recovery lifecycle.

This module NEVER calls LabPostgres.stop/start or directly executes SQL. C is
the sole owner of PostgreSQL recovery, WAL, fences and durable checkpoints.
One retained worker is used for the lifetime of this dispatcher. Timeout or
cancellation poisons it permanently; the underlying worker may continue.
No new recovery, writer grant, epoch or generation is permitted on UNKNOWN.
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
    worker_done: bool
    native_admitted: bool = False

    def __post_init__(self):
        _need(self.schema == "unified.root-pg-recovery-dispatch.v2"
              and self.state in ("UNKNOWN", "C_DIAGNOSTIC_COMPLETE")
              and type(self.worker_done) is bool
              and self.native_admitted is False,
              "LAB_PG_RECOVERY_OBSERVATION_INVALID")


class LabPgRecoveryLane:
    """E dispatches one C-owned canonical recovery and never duplicates it."""

    __slots__=("_pg","_pool","_lock","_future","_busy","_closed",
               "_poisoned","_submitted","_last")

    def __init__(self, pg):
        # C class does not exist in E standalone: only integrated source may
        # construct this lane with a genuine C-owned LAB Postgres instance.
        from .lab_postgres import LabPostgres
        _need(type(pg) is LabPostgres and type(pg.major) is int
              and pg.major == 18 and type(pg.port) is int
              and pg.port != 5432, "LAB_PG_RECOVERY_OWNER_REQUIRED")
        pg._verify_owned()
        self._pg=pg
        self._pool=ThreadPoolExecutor(max_workers=1,
                                      thread_name_prefix="c-lab-pg-recovery")
        self._lock=Lock()
        self._future=None
        self._busy=False
        self._closed=False
        self._poisoned=False
        self._submitted=False
        self._last=None

    @property
    def poisoned(self):
        with self._lock:return self._poisoned

    @property
    def worker_outcome_known(self):
        with self._lock:
            return self._future is not None and self._future.done()

    async def recover_once(self, *, old, streams=(), max_seconds=120,
                           root_process_evidence=None):
        """Submit canonical C recovery ONCE after Root prerequisite checks.

        A RootProcessObservation is deliberately insufficient: only future
        A-owned full descendant + TCP listener evidence can authorize a live
        cluster recovery. Until that exact type is integrated this fails closed.
        The C recovery diagnostic's caller quiesced flag is NOT a Root grant.
        """
        from .lab_writer_revoke import RootProcessExtinction
        _need(type(root_process_evidence) is RootProcessExtinction,
              "LAB_ROOT_PROCESS_EXTINCTION_REQUIRED")
        # Further binding to actual old/new owner is required before release.
        _need(type(old) is dict and type(streams) in (tuple,list),
              "LAB_PG_RECOVERY_ARGUMENTS_INVALID")
        with self._lock:
            _need(not self._busy and not self._submitted
                  and not self._poisoned and not self._closed,
                  "LAB_PG_RECOVERY_ALREADY_SUBMITTED")
            self._busy=True
            self._submitted=True
        try:
            from .lab_pg_recovery import recover_exclusive_lab_cluster
            def c_recovery():
                return recover_exclusive_lab_cluster(
                    self._pg,old=old,streams=streams,quiesced=True,
                    max_seconds=max_seconds)
            future=asyncio.get_running_loop().run_in_executor(
                self._pool,c_recovery)
            with self._lock:self._future=future
            result=await asyncio.wait_for(asyncio.shield(future),
                                          timeout=max_seconds)
            _need(type(result) is dict
                  and result.get("schema") ==
                  "c-isolated-pg18-recovery-diagnostic.v1"
                  and result.get("native_admitted") is False
                  and result.get("root_consul_admitted") is False,
                  "LAB_C_RECOVERY_RESULT_UNVERIFIED")
            self._last=result
            return LabPgRecoveryObservation(
                "unified.root-pg-recovery-dispatch.v2",
                "C_DIAGNOSTIC_COMPLETE",worker_done=True)
        except BaseException:
            with self._lock:self._poisoned=True
            raise
        finally:
            with self._lock:self._busy=False

    def close(self):
        with self._lock:
            self._closed=True
            self._poisoned=True
        # shutdown(wait=False) is NOT proof that C finished or PG is safe.
        self._pool.shutdown(wait=False,cancel_futures=True)
