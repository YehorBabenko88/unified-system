"""E-owned ordered Root shutdown for ONE isolated LAB Grid writer.

This is an actuator for *revocation*, not a writer-admission issuer. It only
uses existing Root ProcessDriver, C PostgreSQL fence and Consul session APIs.
Immediately denies the local writer guard, then attempts all independent
revocations even after an earlier failure. It never authorizes a replacement,
releases a user database, starts a child, or marks partial cleanup successful.
"""
import asyncio
from dataclasses import dataclass

from .consul_authority import ConsulLease, ConsulSessionAuthority
from .grid_writer_fence_model import ResourceFenceBlocked, _need
from .lab_writer_authority import LabWriterAuthority
from .runtime_process import ProcessDriver
from .lab_owner_executor import LabOwnerExecutor

_SCHEMA = "unified.lab-root-writer-revocation.v1"


@dataclass(frozen=True)
class LabRevocationReport:
    schema: str
    result: str
    child_stopped: bool
    sql_fence_revoked: bool
    consul_released: bool
    child_extinct: bool
    old_backend_rejected: bool
    native_admitted: bool = False
    trading_authorized: bool = False


class LabWriterRevoker:
    """Only for the existing owner instance, never inferred from a JSON flag."""

    __slots__ = ("_guard", "_driver", "_handle", "_authority", "_lease",
                 "_pg", "_c", "_generation", "_token", "_backend_pid",
                 "_once", "_last", "_executor")

    def __init__(self, *, guard, driver, handle, authority, lease, pg, c_module, executor):
        _need(type(guard) is LabWriterAuthority and
              type(driver) is ProcessDriver and
              type(authority) is ConsulSessionAuthority and
              authority.config.isolated_lab is True and
              type(lease) is ConsulLease and
              guard._authority is authority and guard._lease == lease and
              guard._pg is pg and guard._c is c_module,
              "LAB_REVOCATION_OWNER_MISMATCH")
        _need(type(executor) is LabOwnerExecutor,
              "LAB_REVOCATION_ROOT_EXECUTOR_REQUIRED")
        _need(type(handle) is str and handle in driver.children,
              "LAB_REVOCATION_CHILD_NOT_OWNED")
        _need(callable(getattr(c_module, "revoke_lab_fence", None))
              and callable(getattr(c_module, "revalidate_lab_fence", None)),
              "LAB_REVOCATION_CANONICAL_C_REQUIRED")
        self._guard, self._driver, self._handle = guard, driver, handle
        self._authority, self._lease = authority, lease
        self._pg, self._c = pg, c_module
        self._generation = guard._generation
        self._token = guard._identity.token
        self._backend_pid = guard._backend_pid
        self._executor = executor
        self._once = False
        self._last = None

    async def revoke(self, *, blocking_timeout=10.0):
        """Always attempt every cleanup stage; never claim partial success.

        Order: deny local guard; stop owned child; revoke C SQL; release
        Consul; verify old child and fence rejection. If PostgreSQL is down,
        SQL revocation is UNKNOWN, not successful. On recovery the C fence
        must be checked/refused before any fresh lease/child is issued.
        """
        _need(type(blocking_timeout) in (int, float)
              and 0 < blocking_timeout <= 30,
              "LAB_REVOCATION_DEADLINE_INVALID")
        if self._once:
            _need(self._last is not None, "LAB_REVOCATION_RETRY_DENIED")
            return self._last
        self._once = True
        self._guard.revoke()
        stages = {"child_stopped": False, "sql_fence_revoked": False,
                  "consul_released": False, "child_extinct": False,
                  "old_backend_rejected": False}
        async def blocked(call):
            # C SQL and ProcessDriver are synchronous. Run on the Root-owned
            # serialized executor; do not hold the asyncio event loop.
            # Timeout means UNKNOWN, never assume the write/stop was cancelled.
            return await self._executor.call(call, timeout=blocking_timeout)

        try:
            await blocked(lambda: self._driver.stop(self._handle))
            stages["child_stopped"] = True
        except BaseException:
            pass
        try:
            stages["sql_fence_revoked"] = (
                await blocked(lambda: self._c.revoke_lab_fence(
                    self._pg, generation=self._generation,
                    token=self._token)) is True)
        except Exception:
            pass
        try:
            await self._authority.release(self._lease)
            stages["consul_released"] = (
                await self._authority.validate(self._lease) is False)
        except Exception:
            pass
        try:
            stages["child_extinct"] = (
                await blocked(lambda: self._driver.alive(self._handle))
                is False)
        except Exception:
            pass
        try:
            # Current generation must not be revalidated after revocation.
            # A live receipt is a failure; exceptions count as refusal only
            # when SQL revocation itself returned successfully.
            await blocked(lambda: self._c.revalidate_lab_fence(
                self._pg, identity=self._guard._identity,
                generation=self._generation, backend_pid=self._backend_pid))
        except BaseException as exc:
            # Bind the exception class to the exact injected C canonical
            # module. E standalone intentionally does NOT import C sources.
            # Only a C stale-fence denial (not network/timeout/cancellation)
            # after successful SQL revocation can be considered evidence.
            c_rejected = getattr(self._c, "LabAdmissionRejected", None)
            stages["old_backend_rejected"] = (
                stages["sql_fence_revoked"]
                and type(c_rejected) is type
                and type(exc) is c_rejected
                and str(exc) == "LAB_FENCE_REVALIDATION_DENIED")
        valid = all(stages.values())
        self._last = LabRevocationReport(
            _SCHEMA, "REVOKED_VERIFIED" if valid else "PARTIAL_DENIED",
            **stages)
        return self._last
