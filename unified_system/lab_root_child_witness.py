"""Root ProcessDriver owned GRID child identity, not a caller PID claim.

The existing ProcessDriver owns the OS child and pinned launch policy. This
witness re-reads the durable record, OS process creation identity and current
owned-child roster. It cannot attest foreign legacy listeners: that remains a
separate host quiescence precondition before any real native LAB admission.
"""
import re

from .runtime_process import ProcessDriver, _identity
from .grid_writer_fence_model import ResourceFenceBlocked, _need


class RootGridChildWitness:
    __slots__ = ("_driver", "_handle", "_created", "_pid", "_token",
                 "_release_id", "_source_commit")

    def __init__(self, driver, handle, *, release_id, source_commit):
        _need(type(driver) is ProcessDriver
              and type(handle) is str and handle in driver.children,
              "LAB_ROOT_CHILD_NOT_OWNED")
        _need(type(release_id) is str and len(release_id) <= 128
              and type(source_commit) is str
              and re.fullmatch(r"[0-9a-f]{40}", source_commit) is not None,
              "LAB_ROOT_CHILD_SOURCE_PIN_INVALID")
        try:
            record = driver._load(handle)
            _need(record.get("module_id") == "market_data"
                  and record.get("state") == "RUNNING"
                  and record.get("release_id") == release_id
                  and record.get("source_commit") == source_commit
                  and type(record.get("pid")) is int
                  and record["pid"] > 1
                  and type(record.get("token")) is str
                  and re.fullmatch(r"[0-9a-f]{64}", record["token"]) is not None
                  and record.get("created") is not None,
                  "LAB_ROOT_CHILD_RECORD_INVALID")
            self._driver, self._handle = driver, handle
            self._created, self._pid = record["created"], record["pid"]
            self._token, self._release_id = record["token"], release_id
            self._source_commit = source_commit
            _need(self.require_current() is True,
                  "LAB_ROOT_CHILD_NOT_CURRENT")
        except ResourceFenceBlocked:
            raise
        except Exception:
            raise ResourceFenceBlocked("LAB_ROOT_CHILD_ATTESTATION_FAILED") from None

    @property
    def epoch(self):
        # Root-created operation handle is a generation identity, not an
        # independent credential or HTTP bearer token.
        return self._handle

    def require_current(self):
        try:
            _need(self._handle in self._driver.children,
                  "LAB_ROOT_CHILD_NOT_OWNED")
            record = self._driver._load(self._handle)
            _need(record.get("module_id") == "market_data"
                  and record.get("state") == "RUNNING"
                  and record.get("created") == self._created
                  and record.get("pid") == self._pid
                  and record.get("token") == self._token
                  and record.get("source_commit") == self._source_commit
                  and record.get("release_id") == self._release_id,
                  "LAB_ROOT_CHILD_IDENTITY_CHANGED")
            # Use A's single canonical OS tri-state instead of alive().
            # A missing/incompatible A build is UNKNOWN and denies grant.
            observer=getattr(self._driver,"owned_process_state",None)
            _need(callable(observer)
                  and observer(self._handle)=="STILL_ALIVE"
                  and _identity(self._pid)==self._created,
                  "LAB_ROOT_CHILD_OS_IDENTITY_LOST")
            return True
        except ResourceFenceBlocked:
            raise
        except Exception:
            raise ResourceFenceBlocked("LAB_ROOT_CHILD_OS_UNVERIFIED") from None

    def confirmed_single_child(self):
        self.require_current()
        try:
            observer=getattr(self._driver,"owned_process_state",None)
            _need(callable(observer),"LAB_ROOT_CANONICAL_OS_OBSERVER_REQUIRED")
            active=[]
            for handle in tuple(self._driver.children):
                record=self._driver._load(handle)
                if record.get("module_id") != "market_data":
                    continue
                state=observer(handle)
                _need(state in ("EXTINCT","STILL_ALIVE","UNKNOWN"),
                      "LAB_ROOT_CHILD_OS_OBSERVER_INVALID")
                _need(state!="UNKNOWN","LAB_ROOT_OLD_GRID_OS_UNKNOWN")
                if state=="STILL_ALIVE":active.append(handle)
                if handle!=self._handle:
                    # No old child can be accepted on Popen-only extinction;
                    # independent descendant+TCP census is still missing.
                    raise ResourceFenceBlocked(
                        "LAB_ROOT_OLD_GRID_LISTENER_PROOF_REQUIRED")
            _need(active == [self._handle],
                  "LAB_ROOT_MULTIPLE_GRID_CHILDREN")
            return True
        except ResourceFenceBlocked:
            raise
        except Exception:
            raise ResourceFenceBlocked("LAB_ROOT_CHILD_ROSTER_UNVERIFIED") from None


class RootManagedQuiescence:
    """Actually inspect every durable Root ProcessDriver market-data record.

    Tracks processes owned by this exact ProcessDriver root and the current
    token-checked loopback health listener. It does NOT claim to enumerate
    arbitrary foreign system services; A/Root must separately exclude those
    before adopting an existing host into the controlled LAB.
    """

    __slots__ = ("_current", "_driver", "_root", "_release_id")

    def __init__(self, current):
        _need(type(current) is RootGridChildWitness,
              "LAB_ROOT_QUIESCENCE_CHILD_REQUIRED")
        self._current = current
        self._driver = current._driver
        self._root = self._driver.root
        self._release_id = current._release_id
        _need(self.require_current() is True,
              "LAB_ROOT_QUIESCENCE_NOT_CURRENT")

    def require_current(self):
        from pathlib import Path
        from .runtime_process import _safe_path
        try:
            self._current.require_current()
            _need(_safe_path(self._driver.root) == self._root,
                  "LAB_ROOT_PROCESS_STATE_ROOT_CHANGED")
            records = tuple(sorted(Path(self._root).glob("*.json")))
            _need(len(records) <= 4096,
                  "LAB_ROOT_PROCESS_RECORD_BUDGET_EXCEEDED")
            found_current = False
            for path in records:
                handle = path.stem
                _need(re.fullmatch(r"[a-f0-9-]{32,36}", handle) is not None,
                      "LAB_ROOT_PROCESS_RECORD_UNRECOGNIZED")
                record = self._driver._load(handle)
                if record.get("module_id") != "market_data":
                    continue
                if handle == self._current._handle:
                    found_current = True
                    _need(record.get("state") == "RUNNING",
                          "LAB_ROOT_CURRENT_GRID_NOT_RUNNING")
                    continue
                # A STOPPED status alone is not extinction: re-read the
                # original OS incarnation even if the PID was later reused.
                _need(record.get("state") == "STOPPED",
                      "LAB_ROOT_OLD_GRID_NOT_STOPPED")
                pid = record.get("pid")
                created = record.get("created")
                if pid is not None:
                    _need(type(pid) is int and pid > 1 and created is not None,
                          "LAB_ROOT_OLD_GRID_OS_IDENTITY_MISSING")
                    # A positive mismatch can be PID reuse, not verified
                    # extinction. None can be a kernel race. Neither is a
                    # reliable Root-only old-owner extinction receipt.
                    raise ResourceFenceBlocked(
                        "LAB_ROOT_OLD_GRID_EXTINCTION_PROOF_REQUIRED")
            _need(found_current, "LAB_ROOT_CURRENT_GRID_RECORD_MISSING")
            return True
        except ResourceFenceBlocked:
            raise
        except Exception:
            raise ResourceFenceBlocked("LAB_ROOT_PROCESS_INVENTORY_UNVERIFIED") from None

    def confirmed_quiescent(self):
        from types import SimpleNamespace
        try:
            self.require_current()
            record = self._driver._load(self._current._handle)
            spec = SimpleNamespace(
                module_id="market_data", version=record["version"])
            # Root ProcessDriver.ready checks the actual loopback listener's
            # private token, release, module identity and executable hashes.
            ready = self._driver.ready(
                spec, self._current._handle, self._release_id)
            _need(type(ready) is dict and ready.get("ready") is True
                  and ready.get("module_id") == "market_data"
                  and ready.get("version") == record["version"]
                  and ready.get("release_id") == self._release_id,
                  "LAB_ROOT_CURRENT_GRID_LISTENER_UNVERIFIED")
            self.require_current()
            return True
        except ResourceFenceBlocked:
            raise
        except Exception:
            raise ResourceFenceBlocked("LAB_ROOT_LISTENER_QUIESCENCE_UNVERIFIED") from None
