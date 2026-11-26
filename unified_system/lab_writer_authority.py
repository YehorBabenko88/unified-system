"""E-owned fail-closed LAB writer authority lifecycle.

This module tracks one private process-local authority epoch. It is not a
serializable capability, a credential, a SQL executor, or an alternative Root
supervisor. Creating this object never authorizes a process by itself: the
Root caller must pass genuine ConsulSessionAuthority/ConsulLease,
StartupSourceAdmission, C-owned revalidation and host quiescence evidence.
A read-only successful check is not a PostgreSQL write grant. Native
service_module_runtime admission remains denied until the A/B/C runtime
integration and real-process acceptance are separately completed.
"""
from dataclasses import dataclass
import secrets
from .grid_writer_fence_model import (
    ResourceFenceBlocked, WriterLeaseIdentity, _need,
)
from .lab_owner_executor import LabOwnerExecutor
from .lab_root_child_witness import RootGridChildWitness

_SCHEMA = "unified.lab-root-writer-authority.v1"
_SCOPE = "ISOLATED_LAB_ONLY"


@dataclass(frozen=True)
class LabAuthorityStatus:
    schema: str
    scope: str
    epoch: str
    generation: int
    state: str
    native_admitted: bool = False
    trading_authorized: bool = False


class LabWriterAuthority:
    """One Root-owned revocable lifetime, never trusted based on caller flags.

    Constructed only from existing full owner objects; readiness checks are
    intentionally read-only and must run again before any protected action.
    Neither a positive status nor this instance can bypass the C SQL fence.
    """

    __slots__ = (
        "_authority", "_lease", "_source", "_identity", "_generation",
        "_pg", "_c", "_quiescence", "_backend_pid", "_postmaster",
        "_process", "_epoch", "_revoked", "_executor",
    )

    def __init__(self, *, authority, lease, source, identity, generation,
                 pg, c_module, quiescence, backend_pid, process, executor=None):
        from .consul_authority import ConsulLease, ConsulSessionAuthority
        from .service_source_admission import StartupSourceAdmission
        _need(type(authority) is ConsulSessionAuthority
              and authority.config.isolated_lab is True
              and type(lease) is ConsulLease,
              "LAB_ROOT_CONSUL_OWNER_REQUIRED")
        _need(type(source) is StartupSourceAdmission,
              "LAB_ROOT_SOURCE_OWNER_REQUIRED")
        _need(type(identity) is WriterLeaseIdentity
              and identity.owner == lease.owner
              and identity.namespace == authority.config.namespace
              and identity.session_id == lease.session_id
              and identity.token == lease.token,
              "LAB_ROOT_LEASE_IDENTITY_REJECTED")
        _need(type(generation) is int and 0 < generation < (1 << 63)
              and type(backend_pid) is int and 1 < backend_pid < (1 << 31),
              "LAB_ROOT_BACKEND_IDENTITY_REJECTED")
        _need(pg is not None and pg.started is True
              and callable(getattr(pg, "_verify_owned", None))
              and callable(getattr(pg, "_verify_postmaster", None)),
              "LAB_ROOT_OWNED_POSTGRES_REQUIRED")
        _need(c_module is not None
              and callable(getattr(c_module, "revalidate_lab_fence", None)),
              "LAB_ROOT_CANONICAL_SQL_REQUIRED")
        _need(type(executor) is LabOwnerExecutor,
              "LAB_ROOT_SERIAL_EXECUTOR_REQUIRED")
        _need(quiescence is not None
              and callable(getattr(quiescence, "require_current", None))
              and callable(getattr(quiescence, "confirmed_quiescent", None)),
              "LAB_ROOT_OS_QUIESCENCE_REQUIRED")
        # Process is a Root-controlled lifecycle witness; neither PID strings
        # nor caller-produced boolean values are accepted.
        _need(type(process) is RootGridChildWitness,
              "LAB_ROOT_PROCESS_WITNESS_REQUIRED")
        _need(process._source_commit == source.source_identity("market_data")["commit"],
              "LAB_ROOT_PROCESS_SOURCE_MISMATCH")
        self._authority, self._lease = authority, lease
        self._source, self._identity = source, identity
        self._generation, self._pg, self._c = generation, pg, c_module
        self._quiescence, self._backend_pid = quiescence, backend_pid
        self._process = process
        self._executor = executor
        self._epoch = secrets.token_hex(32)
        self._revoked = False
        try:
            _need(pg._verify_owned() is None,
                  "LAB_ROOT_PG_OWNERSHIP_REJECTED")
            self._postmaster = pg._verify_postmaster()
            _need(type(self._postmaster) is int and self._postmaster > 1,
                  "LAB_ROOT_POSTMASTER_REJECTED")
        except ResourceFenceBlocked:
            raise
        except Exception:
            raise ResourceFenceBlocked("LAB_ROOT_POSTMASTER_REJECTED") from None

    @property
    def epoch(self):
        return self._epoch

    async def require_current(self):
        """Typed async LAB read guard for B; no boolean admission conversion.

        Deliberately has no synchronous counterpart. B must await this method
        and inspect the returned LabAuthorityStatus; True is never returned.
        A positive read is not a service, exchange, or database write grant.
        """
        return await self.check()

    def revoke(self):
        # Local irrevocable refusal; C SQL ownership must ALSO be revoked by
        # its sole owner when the session changes. No SQL is issued here.
        self._revoked = True

    async def check(self):
        """Re-read owner state; refuse stale lease/backend/child or any outage."""
        try:
            _need(not self._revoked, "LAB_ROOT_AUTHORITY_REVOKED")
            _need(self._source.require_current() is True,
                  "LAB_ROOT_SOURCE_REVOKED")
            _need(await self._authority.validate(self._lease) is True,
                  "LAB_ROOT_CONSUL_LOST")
            def owner_revalidation():
                _need(self._quiescence.require_current() is True
                      and self._quiescence.confirmed_quiescent() is True,
                      "LAB_ROOT_OLD_PROCESS_UNVERIFIED")
                _need(self._process.require_current() is True
                      and self._process.confirmed_single_child() is True,
                      "LAB_ROOT_CHILD_NOT_UNIQUE")
                _need(self._pg.started is True
                      and self._pg._verify_owned() is None
                      and self._pg._verify_postmaster() == self._postmaster,
                      "LAB_ROOT_POSTMASTER_CHANGED")
                return self._c.revalidate_lab_fence(
                    self._pg, identity=self._identity,
                    generation=self._generation, backend_pid=self._backend_pid)
            # C calls synchronous PostgreSQL. A Root-owned single-worker lane
            # preserves one-at-a-time custody and keeps asyncio heartbeat live.
            # Timeout/cancellation poisons the executor; no COMMIT assumption.
            receipt = await self._executor.call(owner_revalidation, timeout=10.0)
            # The C owner ABI is intentionally strict; a synthetic positive
            # receipt does not elevate this LAB-only object to native authority.
            _need(type(receipt) is dict
                  and receipt.get("schema") == "lab-postgres-fence-revalidation.v1"
                  and receipt.get("scope") == _SCOPE
                  and receipt.get("generation") == self._generation
                  and receipt.get("token") == self._identity.token
                  and receipt.get("backend_pid") == self._backend_pid
                  and receipt.get("session_id") == self._identity.session_id
                  and receipt.get("source_sha256") == self._identity.source_sha256
                  and receipt.get("schema_sha256") == self._identity.schema_sha256
                  and receipt.get("db_backend_observed") is True
                  and receipt.get("db_fence_current_at_read") is True
                  and receipt.get("native_writer_admitted") is False
                  and receipt.get("trading_authorized") is False,
                  "LAB_ROOT_PG_RECEIPT_INVALID")
            _need(self._source.require_current() is True
                  and await self._authority.validate(self._lease) is True,
                  "LAB_ROOT_AUTHORITY_CHANGED")
            _need(not self._revoked, "LAB_ROOT_AUTHORITY_REVOKED")
            return LabAuthorityStatus(
                _SCHEMA, _SCOPE, self._epoch, self._generation,
                "READ_ONLY_REVALIDATED_NOT_NATIVE")
        except ResourceFenceBlocked:
            self.revoke()
            raise
        except Exception:
            self.revoke()
            raise ResourceFenceBlocked("LAB_ROOT_AUTHORITY_UNVERIFIED") from None
