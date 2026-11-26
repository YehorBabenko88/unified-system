"""E-owned ordered Root shutdown for ONE isolated LAB Grid writer.

This is an actuator for *revocation*, not a writer-admission issuer. It only
uses existing Root ProcessDriver, C PostgreSQL fence and Consul session APIs.
Immediately denies the local writer guard, then attempts all independent
revocations even after an earlier failure. It never authorizes a replacement,
releases a user database, starts a child, or marks partial cleanup successful.
"""
import asyncio
from dataclasses import dataclass
from inspect import signature, Parameter

from .consul_authority import ConsulLease, ConsulSessionAuthority
from .grid_writer_fence_model import ResourceFenceBlocked, _need
from .lab_writer_authority import LabWriterAuthority
from .runtime_process import ProcessDriver
from .lab_owner_executor import LabOwnerExecutor
from .lab_root_stop_lane import LabRootStopLane
from .lab_process_extinction import RootProcessObservation, EXTINCT

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
                 "_once", "_last", "_executor", "_stop_lane")

    def __init__(self, *, guard, driver, handle, authority, lease, pg, c_module, executor, stop_lane):
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
        _need(type(stop_lane) is LabRootStopLane and stop_lane._driver is driver,
              "LAB_REVOCATION_ROOT_OS_LANE_REQUIRED")
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
        self._stop_lane = stop_lane
        self._once = False
        self._last = None

    async def revoke(self, *, blocking_timeout=10.0):
        """Always attempt every cleanup stage; never claim partial success.

        Order: deny local guard; retain C live exact-backend identity on
        original SQL worker; stop OS child on independent Root lane; invoke
        C exact durable SQL revoke using the privately retained incarnation;
        verify old backend state. This is NOT owner transfer permission. Defer Consul release until independent old-backend and
        old-process extinction, WAL reconciliation and trusted Root finalize.
        If PostgreSQL is down,
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
        # Suspected remote lease loss, poisoned SQL or any shutdown attempt
        # irrevocably denies this Root epoch before OS or SQL side effects.
        self._guard.block_transfer()
        stages = {"child_stopped": False, "sql_fence_revoked": False,
                  "consul_released": False, "child_extinct": False,
                  "old_backend_rejected": False}
        async def blocked(call):
            # Only C SQL belongs on this Root-owned serial executor.
            # OS control uses an independent Root lane to survive SQL poison.
            # Timeout means UNKNOWN, never assume the write/stop was cancelled.
            return await self._executor.call(call, timeout=blocking_timeout)

        # If normal SQL is poisoned, never enqueue revoke on the uncertain
        # writer backend. Independent C-owned cluster recovery is required.
        # C's old exported short ABI (generation, token) cannot attest
        # exact original backend PID+start or committed inactive readback.
        # Never silently fall back to it. C owns the sole canonical SQL
        # implementation and will expose the reviewed backend-bound ABI;
        # until that source is integrated the stage is deliberately UNKNOWN.
        # Do not enqueue speculative SQL into a poisoned original executor.
        exact_revoke = getattr(self._c, "revoke_lab_fence", None)
        try:
            params = signature(exact_revoke).parameters
            exact_abi = (getattr(exact_revoke, "__module__", None)
                         == "unified_system.lab_pg_fence"
                         and {"owner", "namespace", "generation", "token",
                              "backend_pid", "backend_start"} <= set(params)
                         and all(params[k].kind is Parameter.KEYWORD_ONLY
                                 for k in ("owner", "namespace", "generation",
                                           "token", "backend_pid", "backend_start")))
        except (TypeError, ValueError):
            exact_abi = False
        # Snapshot the EXACT old active backend while it still exists.
        # The Root epoch is already irreversibly transfer-blocked above;
        # obtaining this C receipt cannot issue another operation permit.
        # No arbitrary/caller-provided backend_start is ever accepted.
        frozen_backend_start = None
        if exact_abi and not self._executor.poisoned:
            try:
                receipt = await blocked(lambda: self._c.revalidate_lab_fence(
                    self._pg, identity=self._guard._identity,
                    generation=self._generation, backend_pid=self._backend_pid))
                identity = self._guard._identity
                if (type(receipt) is dict
                        and receipt.get("schema") == "lab-postgres-fence-revalidation.v1"
                        and receipt.get("scope") == "ISOLATED_LAB_ONLY"
                        and receipt.get("resource_id") == "grid-market-data-primary"
                        and receipt.get("owner") == identity.owner
                        and receipt.get("namespace") == identity.namespace
                        and receipt.get("generation") == self._generation
                        and receipt.get("token") == self._token
                        and receipt.get("backend_pid") == self._backend_pid
                        and receipt.get("session_id") == identity.session_id
                        and receipt.get("instance_id") == identity.instance_id
                        and receipt.get("node_incarnation_id") == identity.node_incarnation_id
                        and receipt.get("source_sha256") == identity.source_sha256
                        and receipt.get("schema_sha256") == identity.schema_sha256
                        and receipt.get("db_backend_observed") is True
                        and receipt.get("db_fence_current_at_read") is True
                        and receipt.get("native_writer_admitted") is False
                        and receipt.get("trading_authorized") is False
                        and type(receipt.get("backend_start")) is str
                        and bool(receipt["backend_start"])):
                    frozen_backend_start = receipt["backend_start"]
            except BaseException:
                # Unknown, timeout, poisoned executor or stale backend:
                # do NOT infer the original identity from a missing PID.
                pass

        # Stop only AFTER capturing the original server-observed
        # incarnation. A successful stop may remove pg_stat_activity and
        # make live-only C revalidation impossible by design.
        try:
            await self._stop_lane.stop_owned(self._handle,timeout=blocking_timeout)
            stages["child_stopped"] = True
        except BaseException:
            pass
        if exact_abi and frozen_backend_start is not None:
            try:
                stages["sql_fence_revoked"] = (
                    await blocked(lambda: exact_revoke(
                        self._pg,
                        owner=self._guard._identity.owner,
                        namespace=self._guard._identity.namespace,
                        generation=self._generation,
                        token=self._token,
                        backend_pid=self._backend_pid,
                        backend_start=frozen_backend_start,
                        timeout=blocking_timeout)) is True)
            except BaseException:
                # C owns the original exact UPDATE and fresh durable readback.
                # Unknown COMMIT or lock timeout is never assumed successful.
                pass
        # The original Consul lease is deliberately NOT released here.
        # SQL revocation and local child stop do not prove old backend
        # extinction or irreversible COMMIT. A replacement Root lease must
        # wait for A/C full typed exit evidence and durable WAL reconciliation.
        # The lease may still expire externally; that cannot be treated as
        # safe owner transfer or as consent to a new writer generation.
        try:
            observation = await self._stop_lane.old_child_extinct(
                self._handle,timeout=blocking_timeout)
            # Retained-handle exit alone does not attest socket ownership
            # or descendants. Never mint a full RootProcessExtinction here.
            stages["child_extinct"] = (
                type(observation) is RootProcessObservation
                and observation.state == EXTINCT
                and observation.listener_owner_verified is True)
        except BaseException:
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
        # No RootBackendExtinction/RootProcessExtinction can currently be
        # issued. No positive full cleanup status or voluntary lease release.
        valid = all(stages.values())
        self._last = LabRevocationReport(
            _SCHEMA, "REVOKED_VERIFIED" if valid else "PARTIAL_DENIED",
            **stages)
        return self._last

    async def dispatch_owned_recovery_after_poison(
            self, recovery_lane, *, old, streams=(),
            root_process_evidence=None, max_seconds=120):
        """ONE C recovery operation after a PARTIAL poisoned SQL revoke.

        This method does not interpret local OS stop as extinction: the
        canonical RootProcessExtinction is mandatory and currently not
        issuable. No separate LabPostgres.stop/start code exists in E.
        """
        from .lab_pg_recovery_lane import LabPgRecoveryLane
        _need(self._once and self._last is not None
              and self._last.result == "PARTIAL_DENIED"
              and self._last.child_stopped is True
              and self._executor.poisoned is True,
              "LAB_PG_RECOVERY_NOT_REQUIRED")
        _need(type(recovery_lane) is LabPgRecoveryLane
              and recovery_lane._pg is self._pg,
              "LAB_PG_RECOVERY_FOREIGN_CLUSTER")
        return await recovery_lane.recover_once(
            old=old, streams=streams, max_seconds=max_seconds,
            root_process_evidence=root_process_evidence)
