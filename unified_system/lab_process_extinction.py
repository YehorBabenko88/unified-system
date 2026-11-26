"""E/A Root-owned tri-state OS process observation (NOT a grant).

A ProcessDriver.owned_process_state() is the sole tri-state authority; alive() maps identity errors to False and is NOT
an extinction witness. A process can have disappeared, reused its PID or
be inaccessible; only A's original retained process object, completion wait,
durable process identity and *separate* endpoint ownership census can later
qualify RootProcessExtinction. This observer returns UNKNOWN unless all
necessary local process-handle facts are available. No foreign PID is killed.
"""
from dataclasses import dataclass
import subprocess

from .grid_writer_fence_model import ResourceFenceBlocked, _need
from .runtime_process import ProcessDriver

EXTINCT="EXTINCT"
STILL_ALIVE="STILL_ALIVE"
UNKNOWN="UNKNOWN"


@dataclass(frozen=True)
class RootProcessObservation:
    schema: str
    state: str
    handle: str
    pid: int
    created: object
    reason: str
    listener_owner_verified: bool = False
    native_admitted: bool = False

    def __post_init__(self):
        _need(self.schema=="unified.root-process-observation.v1"
              and self.state in (EXTINCT,STILL_ALIVE,UNKNOWN)
              and type(self.handle) is str and bool(self.handle)
              and type(self.pid) is int and self.pid>1
              and type(self.reason) is str
              and self.listener_owner_verified is False
              and self.native_admitted is False,
              "LAB_PROCESS_OBSERVATION_INVALID")


def observe_owned_process_extinction(driver, handle):
    """Read OS state without treating errors or PID reuse as extinction.

    Root's original A-owned retained process handles improve on PID existence.
    The returned EXTINCT is *local process-only*, never full listener/descendant
    proof or a RootProcessExtinction grant. That requires A owner review.
    """
    _need(type(driver) is ProcessDriver and
          type(handle) is str and handle in driver.children,
          "LAB_PROCESS_OBSERVATION_OWNER_REQUIRED")
    # A record read/access failure must never turn into a positive exit.
    # Without trusted PID and creation identity we cannot issue a receipt.
    try:
        record=driver._load(handle)
        pid=record.get("pid")
        created=record.get("created")
        _need(type(pid) is int and pid>1 and created is not None,
              "LAB_PROCESS_OBSERVATION_RECORD_UNQUALIFIED")
        child=driver.children.get(handle)
        # A's protected disposable Windows Job launcher retains the genuine
        # _OwnedWindowsChild, NOT a subprocess.Popen subclass. Accept only
        # that exact A-owned class from A's canonical module; never accept an
        # arbitrary duck-typed lookalike or caller-provided PID.
        from .runtime_process import _OwnedWindowsChild
        _need(type(child) in (subprocess.Popen, _OwnedWindowsChild)
              and child.pid==pid,
              "LAB_PROCESS_OBSERVATION_RETAINED_HANDLE_REQUIRED")
    except Exception:
        raise ResourceFenceBlocked(
            "LAB_PROCESS_OBSERVATION_OWNER_UNVERIFIED") from None
    try:
        # Canonical OS tri-state logic is A-owned ProcessDriver. E never
        # creates a parallel PID/identity interpretation. Recheck the
        # retained exact operation record on each call and refuse mismatch.
        _need(record.get("state") in ("RUNNING", "STOPPED"),
              "LAB_PROCESS_OBSERVATION_STATE_INVALID")
        observer=getattr(driver,"owned_process_state",None)
        if not callable(observer):
            return RootProcessObservation(
                "unified.root-process-observation.v1",UNKNOWN,handle,pid,
                created,"A_CANONICAL_OBSERVER_NOT_INTEGRATED")
        state=observer(handle)
        _need(state in (EXTINCT,STILL_ALIVE,UNKNOWN),
              "LAB_PROCESS_OBSERVATION_UNEXPECTED_OS_STATE")
        if state == EXTINCT:
            return RootProcessObservation(
                "unified.root-process-observation.v1",EXTINCT,handle,pid,
                created,"A_RETAINED_HANDLE_EXITED_LISTENER_UNVERIFIED")
        if state == STILL_ALIVE:
            return RootProcessObservation(
                "unified.root-process-observation.v1",STILL_ALIVE,handle,pid,
                created,"A_RETAINED_HANDLE_STILL_ALIVE")
        return RootProcessObservation(
            "unified.root-process-observation.v1",UNKNOWN,handle,pid,
            created,"A_ROOT_OS_IDENTITY_UNKNOWN")
    except (PermissionError, OSError, subprocess.TimeoutExpired, ValueError):
        return RootProcessObservation(
            "unified.root-process-observation.v1",UNKNOWN,handle,
            pid,created,"OS_PROCESS_INSPECTION_UNCERTAIN")
