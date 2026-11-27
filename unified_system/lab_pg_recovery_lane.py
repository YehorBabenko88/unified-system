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
from threading import Lock, Event
from .grid_writer_fence_model import ResourceFenceBlocked, _need

# One original C owner object => at most one E recovery dispatcher, including
# across timeouts and close(wait=False). A process restart/owner replacement
# requires fresh A/C evidence; there is deliberately no public registry reset.
_RECOVERY_OWNER_LOCK=Lock()
_RECOVERY_OWNERS=set()


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
               "_poisoned","_submitted","_last","_worker_done_event")

    def __init__(self, pg):
        # C class does not exist in E standalone: only integrated source may
        # construct this lane with a genuine C-owned LAB Postgres instance.
        from .lab_postgres import LabPostgres
        _need(type(pg) is LabPostgres and type(pg.major) is int
              and pg.major == 18 and type(pg.port) is int
              and pg.port != 5432, "LAB_PG_RECOVERY_OWNER_REQUIRED")
        pg._verify_owned()
        with _RECOVERY_OWNER_LOCK:
            _need(pg not in _RECOVERY_OWNERS,
                  "LAB_PG_RECOVERY_OWNER_ALREADY_REGISTERED")
            _RECOVERY_OWNERS.add(pg)
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
        self._worker_done_event=Event()

    @property
    def poisoned(self):
        with self._lock:return self._poisoned

    @property
    def worker_outcome_known(self):
        # A finished Python Future is not enough to prove OS, SQL, WAL,
        # source, lease or backend ownership. Do not expose as recovery GO.
        with self._lock:
            return self._submitted and self._worker_done_event.is_set()

    async def recover_once(self, *, old, streams=(), max_seconds=120,
                           root_process_evidence=None):
        """Submit canonical C recovery ONCE after Root prerequisite checks.

        A RootProcessObservation is deliberately insufficient: only future
        A-owned full descendant + TCP listener evidence can authorize a live
        cluster recovery. Until that exact type is integrated this fails closed.
        The C recovery diagnostic's caller quiesced flag is NOT a Root grant.
        """
        # ROUND16: no A-owned sealed, incarnation/descendant/listener-bound
        # RootProcessExtinction issuer has been integrated. A type match is
        # never authority. Refuse BEFORE _submitted, thread creation or C IO.
        # Only A/C/E-approved evidence verification may replace this gate.
        raise ResourceFenceBlocked("LAB_ROOT_BOUND_EXTINCTION_NOT_IMPLEMENTED")
        # This source is deliberately inert: no new worker is ever submitted
        # until A verifies the exact retired process tree and C verifies its
        # matching backend incarnation under a mutually authenticated Root
        # owner operation. Keep the original dispatcher contract for a
        # coordinated A/C/E replacement, not a speculative native bypass.

    def close(self):
        with self._lock:
            self._closed=True
            self._poisoned=True
        # The owner stays registered even after close(); a new dispatcher
        # for the SAME C owner is forbidden while OS/SQL state is uncertain.
        # shutdown(wait=False) is NOT proof that C finished or PG is safe.
        self._pool.shutdown(wait=False,cancel_futures=True)
