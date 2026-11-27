"""E/A Root-owned tri-state OS process observation (NOT a grant).

A's ProcessDriver owns BOTH canonical OS observations: owned_process_state()
for original Popen and owned_job_stop_state() for a real retained Windows Job.
alive() maps identity errors to False and is NOT an extinction witness. A process can have disappeared, reused its PID or
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
    A Windows Job EXTINCT requires both the original process and Job's zero
    active members. Non-Job Popen EXTINCT remains process-only.
    Neither observation supplies A's issuer-retained one-time Job receipt,
    historical SCM/TCP ownership, Consul or C backend proof; never a grant.
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
        from . import runtime_process as _a_runtime
        # E's standalone branch predates A's protected job launcher. Its
        # Windows child class must come from the actual integrated A module,
        # not a fabricated fallback, injected type name or caller object.
        owned_class = getattr(_a_runtime, "_OwnedWindowsChild", None)
        if owned_class is not None:
            _need(type(owned_class) is type,
                  "LAB_PROCESS_OBSERVATION_A_RUNTIME_UNQUALIFIED")
        is_windows_child = (owned_class is not None
                            and type(child) is owned_class)
        _need((type(child) is subprocess.Popen or is_windows_child)
              and child.pid==pid
              and (not is_windows_child
                   or (child._handle is not None
                       and child._job is not None
                       and child._job._handle is not None
                       and child._job._assigned is True)),
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
        # Crucial A ABI distinction: a signalled Windows process is NOT
        # evidence that the original Job has zero descendants. Only A's
        # owner-locked, original-handle owned_job_stop_state may say so.
        observer=getattr(driver,"owned_job_stop_state" if is_windows_child
                         else "owned_process_state",None)
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
                created,("A_ORIGINAL_JOB_ZERO_MEMBERS_LISTENER_UNVERIFIED"
                         if is_windows_child else
                         "A_RETAINED_HANDLE_EXITED_LISTENER_UNVERIFIED"))
        if state == STILL_ALIVE:
            return RootProcessObservation(
                "unified.root-process-observation.v1",STILL_ALIVE,handle,pid,
                created,("A_ORIGINAL_JOB_STILL_ALIVE" if is_windows_child
                         else "A_RETAINED_HANDLE_STILL_ALIVE"))
        return RootProcessObservation(
            "unified.root-process-observation.v1",UNKNOWN,handle,pid,
            created,"A_ROOT_OS_IDENTITY_UNKNOWN")
    except (PermissionError, OSError, subprocess.TimeoutExpired, ValueError):
        return RootProcessObservation(
            "unified.root-process-observation.v1",UNKNOWN,handle,
            pid,created,"OS_PROCESS_INSPECTION_UNCERTAIN")
