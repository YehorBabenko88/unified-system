"""E/A Root-owned tri-state OS process observation (NOT a grant).

ProcessDriver.alive() deliberately maps identity errors to False and is NOT
an extinction witness. A process can have disappeared, reused its PID or
be inaccessible; only an exact owned retained Popen handle, completion wait,
durable process identity and *separate* endpoint ownership census can later
qualify RootProcessExtinction. This observer returns UNKNOWN unless all
necessary local process-handle facts are available. No foreign PID is killed.
"""
from dataclasses import dataclass
import os
import subprocess

from .grid_writer_fence_model import _need
from .runtime_process import ProcessDriver, _identity

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
              and type(self.reason) is str,
              "LAB_PROCESS_OBSERVATION_INVALID")


def observe_owned_process_extinction(driver, handle):
    """Read OS state without treating errors or PID reuse as extinction.

    Root's retained Popen handles give a better result than PID existence.
    The returned EXTINCT is *local process-only*, never full listener/descendant
    proof or a RootProcessExtinction grant. That requires A owner review.
    """
    _need(type(driver) is ProcessDriver and
          type(handle) is str and handle in driver.children,
          "LAB_PROCESS_OBSERVATION_OWNER_REQUIRED")
    record=driver._load(handle)
    pid=record.get("pid")
    created=record.get("created")
    _need(type(pid) is int and pid>1 and created is not None,
          "LAB_PROCESS_OBSERVATION_RECORD_UNQUALIFIED")
    child=driver.children.get(handle)
    _need(type(child) is subprocess.Popen and child.pid==pid,
          "LAB_PROCESS_OBSERVATION_RETAINED_HANDLE_REQUIRED")
    try:
        # poll() consumes exactly the retained Popen process handle status.
        # A NULL process is not enough to infer listener-owner extinction.
        code=child.poll()
        if code is None:
            actual=_identity(pid)
            if actual is None:
                return RootProcessObservation(
                    "unified.root-process-observation.v1",UNKNOWN,handle,
                    pid,created,"RETAINED_RUNNING_BUT_IDENTITY_UNAVAILABLE")
            if actual!=created:
                return RootProcessObservation(
                    "unified.root-process-observation.v1",UNKNOWN,handle,
                    pid,created,"RETAINED_HANDLE_IDENTITY_MISMATCH")
            return RootProcessObservation(
                "unified.root-process-observation.v1",STILL_ALIVE,handle,
                pid,created,"RETAINED_HANDLE_RUNNING")
        # A retained handle has reached terminal wait. This does not prove
        # descendants, TCP listener owner, or C PostgreSQL backend extinction.
        child.wait(timeout=.5)
        return RootProcessObservation(
            "unified.root-process-observation.v1",EXTINCT,handle,
            pid,created,"RETAINED_HANDLE_EXITED_LISTENER_UNVERIFIED")
    except (PermissionError, OSError, subprocess.TimeoutExpired, ValueError):
        return RootProcessObservation(
            "unified.root-process-observation.v1",UNKNOWN,handle,
            pid,created,"OS_PROCESS_INSPECTION_UNCERTAIN")
