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
            _need(self._driver.alive(self._handle) is True
                  and _identity(self._pid) == self._created,
                  "LAB_ROOT_CHILD_OS_IDENTITY_LOST")
            return True
        except ResourceFenceBlocked:
            raise
        except Exception:
            raise ResourceFenceBlocked("LAB_ROOT_CHILD_OS_UNVERIFIED") from None

    def confirmed_single_child(self):
        self.require_current()
        try:
            active = []
            for handle in tuple(self._driver.children):
                record = self._driver._load(handle)
                if (record.get("module_id") == "market_data"
                        and self._driver.alive(handle)):
                    active.append(handle)
            _need(active == [self._handle],
                  "LAB_ROOT_MULTIPLE_GRID_CHILDREN")
            return True
        except ResourceFenceBlocked:
            raise
        except Exception:
            raise ResourceFenceBlocked("LAB_ROOT_CHILD_ROSTER_UNVERIFIED") from None
