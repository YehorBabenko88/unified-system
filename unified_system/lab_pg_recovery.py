"""C-only isolated PostgreSQL18 recovery control lane.

NO Root/Consul admission, no market writes, no arbitrary PID termination,
no second SQL writer, no positive RootBackendExtinction issuance.

The caller must first quiesce Grid and revoke its ability to enqueue SQL in
the independent E supervisor. This module controls only a verified disposable
LabPostgres instance through its original owner marker, data dir and postmaster.
"""
import time

from .lab_simulation_admission import LabAdmissionRejected, need
from .lab_pg_fence import (
    _scope, observe_old_lab_backend, revoke_lab_fence, fenced_lab_witness)
from .lab_pg_checkpoint import read_lab_cursor, read_lab_pending, read_lab_checkpoint


def _old_record(pg, *, owner, namespace, generation, token,
                backend_pid, backend_start):
    owner, namespace = _scope(owner, namespace)
    need(type(generation) is int and generation > 0
         and type(token) is int and token > 0
         and type(backend_pid) is int and backend_pid > 0,
         "LAB_RECOVERY_ARGUMENTS_INVALID")
    # Stable tuple comes from the old C-owned fence, not caller-supplied
    # diagnostic JSON. An unrelated or already advanced fence is denied.
    from datetime import datetime
    need(type(backend_start) is str and len(backend_start) <= 64,
         "LAB_RECOVERY_BACKEND_START_INVALID")
    try:
        dt = datetime.fromisoformat(backend_start.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LabAdmissionRejected("LAB_RECOVERY_BACKEND_START_INVALID") from exc
    need(dt.tzinfo is not None, "LAB_RECOVERY_BACKEND_START_INVALID")
    sql = (
        "SELECT count(*) FROM public.lab_writer_fence f"
        " WHERE f.resource_id='grid-market-data-primary'"
        f" AND f.owner='{owner}' AND f.namespace='{namespace}'"
        f" AND f.generation={generation} AND f.token={token}"
        f" AND f.backend_pid={backend_pid}"
        f" AND f.backend_start='{dt.isoformat()}'::timestamptz"
    )
    need(pg.sql(sql) == "1", "LAB_RECOVERY_OLD_FENCE_MISMATCH")
    return dict(owner=owner, namespace=namespace, generation=generation,
                token=token, backend_pid=backend_pid, backend_start=backend_start)


def _snapshot(pg, streams):
    """Protected owner-only diagnostic readback, not authorizing replay."""
    result = {}
    for stream in streams:
        from .lab_pg_checkpoint import _stream
        key = _stream(stream)
        # Reads are from the dedicated fresh owner connection, not poisoned
        # Grid's old SQL executor. Any mismatched immutable row fails closed.
        pending = read_lab_pending(pg, stream_id=key)
        cursor = read_lab_cursor(pg, stream_id=key)
        checkpoint = read_lab_checkpoint(pg, stream_id=key)
        result[key] = dict(pending=pending, cursor=cursor, checkpoint=checkpoint)
    return result


def recover_exclusive_lab_cluster(pg, *, old, streams=(), quiesced=False,
                                  max_seconds=120):
    """Bounded independent C recovery of an *exclusively owned* disposable LAB.

    This orchestrates a cluster fast stop/start, not termination of any
    arbitrary backend or issuance of a Root/Consul grant. If ownership,
    state or durable verification is uncertain the function raises DENIED.
    The old backend must remain fenced until its whole cluster is verified
    stopped, and a fresh SQL connection must independently revoke it.
    """
    # Caller-provided quiescence cannot prove E/Root process extinction.
    # This operation remains strictly a disposable LAB diagnostic.
    need(type(quiesced) is bool and quiesced is True,
         "LAB_RECOVERY_QUIESCENCE_REQUIRED")
    need(type(max_seconds) in (int, float) and 10 <= max_seconds <= 180,
         "LAB_RECOVERY_DEADLINE_INVALID")
    need(type(streams) in (tuple, list) and len(streams) <= 64,
         "LAB_RECOVERY_STREAMS_INVALID")
    from .lab_pg_checkpoint import _stream
    streams = tuple(_stream(s) for s in streams)
    need(len(set(streams)) == len(streams), "LAB_RECOVERY_DUPLICATE_STREAM")
    pg._verify_owned()
    need(pg.started, "LAB_PG_NOT_STARTED")
    initial_pid = pg._verify_postmaster()
    need(pg.port != 5432 and pg.port is not None,
         "LAB_RECOVERY_PORT_REJECTED")
    if not isinstance(old, dict):
        raise LabAdmissionRejected("LAB_RECOVERY_OLD_IDENTITY_INVALID")
    keys = ("owner", "namespace", "generation", "token",
            "backend_pid", "backend_start")
    need(set(old) == set(keys), "LAB_RECOVERY_OLD_IDENTITY_INVALID")
    old = _old_record(pg, **old)
    deadline = time.monotonic() + max_seconds
    # Verify the pre-stop active backend has not changed incarnation.
    need(observe_old_lab_backend(pg, **old) == "STILL_ALIVE",
         "LAB_RECOVERY_OLD_BACKEND_NOT_CURRENT")
    # The close request is targeted at the exact disposable postmaster,
    # reusing LabPostgres' verified PID/file/OS identity path. Normal fast
    # shutdown aborts old SQL transactions rather than relying on a poisoned
    # thread, and PG performs WAL-safe shutdown.
    pg.stop()
    need(not pg.started and not pg._pid_is_live(initial_pid),
         "LAB_RECOVERY_OLD_POSTMASTER_UNVERIFIED")
    need(time.monotonic() < deadline, "LAB_RECOVERY_TIMEOUT")
    pg.start()
    need(pg.started and pg._verify_postmaster() != initial_pid,
         "LAB_RECOVERY_POSTMASTER_IDENTITY_UNVERIFIED")
    # No positive RootBackendExtinction issued: this is only C SQL evidence.
    state = observe_old_lab_backend(pg, **old)
    need(state == "EXTINCT", "LAB_RECOVERY_BACKEND_NOT_EXTINCT")
    custody = fenced_lab_witness(pg)
    need(custody["direct_writer_insert"] is False,
         "LAB_RECOVERY_SQL_FENCE_BYPASS")
    before = pg.sql(
        "SELECT generation,token,active FROM public.lab_writer_fence"
        " WHERE resource_id='grid-market-data-primary'")
    expected = f"{old['generation']}|{old['token']}|t"
    need(before == expected, "LAB_RECOVERY_HIGH_WATER_CHANGED")
    # Revoke only after exclusive-cluster extinction and fresh owner readback.
    # An uncommitted old write was rolled back by fast shutdown; an old
    # successful commit must be resolved from immutable row/pending, never
    # blindly retried or inferred from a duplicate constraint.
    need(time.monotonic() < deadline, "LAB_RECOVERY_TIMEOUT")
    # Prevent any new writer claim during the transition by leaving the
    # old fence active until the durable revoke below.
    revoke_lab_fence(pg, generation=old["generation"], token=old["token"])
    need(pg.sql(
        "SELECT generation,token,active FROM public.lab_writer_fence"
        " WHERE resource_id='grid-market-data-primary'") ==
        f"{old['generation']}|{old['token']}|f",
        "LAB_RECOVERY_REVOCATION_UNVERIFIED")
    records = _snapshot(pg, streams)
    need(time.monotonic() < deadline, "LAB_RECOVERY_TIMEOUT")
    return {
        "schema": "c-isolated-pg18-recovery-diagnostic.v1",
        "scope": "ISOLATED_LAB_ONLY",
        "old_generation": old["generation"], "old_token": old["token"],
        "old_backend_pid": old["backend_pid"],
        "old_backend_start": old["backend_start"],
        "old_postmaster_pid": initial_pid,
        "new_postmaster_pid": pg._verify_postmaster(),
        "old_backend_observation": state,
        "durable_fence_active": False,
        "stream_snapshots": records,
        "native_admitted": False, "root_consul_admitted": False,
        "execution_authority": False, "paper_admitted": False,
        "trading_authorized": False,
    }
