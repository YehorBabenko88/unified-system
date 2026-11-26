"""Single C-owned serialized isolated LAB PostgreSQL recovery state machine.

This is a disposable-LAB diagnostic, NOT Root/Consul authorization.
E supplies STOP/deny control-plane orchestration and A supplies independent
OS proof; neither caller booleans nor local SQL receipts authorize native
Grid restart. Never call arbitrary pg_terminate_backend(pid).
"""
import threading
import time
from datetime import datetime

from .lab_simulation_admission import LabAdmissionRejected, need
from .lab_postgres import LabPostgres
from .lab_pg_fence import _scope, fenced_lab_witness, observe_old_lab_backend
from .lab_pg_checkpoint import _stream, read_lab_pending, read_lab_checkpoint

# Per-object C ownership. A STOP timeout leaves the entry permanently
# poisoned for this Python process rather than releasing it for a second
# concurrent stop/start. A fresh supervisor must establish external proof.
_GUARD = threading.Lock()
_STATES = {}


def _require_pg(pg):
    need(type(pg) is LabPostgres, "LAB_RECOVERY_PG_TYPE_INVALID")
    need(type(pg.major) is int and pg.major == 18,
         "LAB_RECOVERY_PG18_REQUIRED")
    need(type(pg.port) is int and 0 < pg.port < 65536 and pg.port != 5432,
         "LAB_RECOVERY_PORT_REJECTED")
    pg._verify_owned()
    return pg


def _validate_old(old):
    need(type(old) is dict, "LAB_RECOVERY_OLD_IDENTITY_INVALID")
    required = ("owner", "namespace", "generation", "token",
                "backend_pid", "backend_start")
    need(set(old) == set(required), "LAB_RECOVERY_OLD_IDENTITY_INVALID")
    owner, namespace = _scope(old["owner"], old["namespace"])
    for field in ("generation", "token", "backend_pid"):
        need(type(old[field]) is int and 0 < old[field] < 2**63,
             "LAB_RECOVERY_OLD_IDENTITY_INVALID")
    need(old["backend_pid"] < 2**31, "LAB_RECOVERY_BACKEND_PID_INVALID")
    value = old["backend_start"]
    need(type(value) is str and len(value) <= 64,
         "LAB_RECOVERY_BACKEND_START_INVALID")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LabAdmissionRejected("LAB_RECOVERY_BACKEND_START_INVALID") from exc
    need(parsed.tzinfo is not None, "LAB_RECOVERY_BACKEND_START_INVALID")
    return dict(old, owner=owner, namespace=namespace)


def _remaining(deadline):
    seconds = deadline - time.monotonic()
    need(seconds >= 1, "LAB_RECOVERY_DEADLINE_EXCEEDED")
    return seconds


def _bounded_sql(pg, query, deadline):
    # subprocess.run is bounded by its own timeout; on failure no admission.
    return pg.sql(query, timeout=min(120, _remaining(deadline)))


def _fence_state(pg, old, deadline):
    start = datetime.fromisoformat(old["backend_start"].replace("Z", "+00:00"))
    return _bounded_sql(
        pg, "SELECT generation,token,active,backend_pid FROM public.lab_writer_fence"
        " WHERE resource_id='grid-market-data-primary'"
        f" AND owner='{old['owner']}' AND namespace='{old['namespace']}'"
        f" AND generation={old['generation']} AND token={old['token']}"
        f" AND backend_pid={old['backend_pid']}"
        f" AND backend_start='{start.isoformat()}'::timestamptz",
        deadline)


def _stop_started(pg, deadline):
    need(pg.started is True, "LAB_RECOVERY_NOT_STARTED")
    pg._verify_postmaster()
    pg.stop(timeout=min(120, _remaining(deadline)))
    need(pg.started is False, "LAB_RECOVERY_STOP_NOT_CONFIRMED")


def _restart_stopped(pg, deadline):
    need(pg.started is False, "LAB_RECOVERY_RESTART_NOT_STOPPED")
    pg._verify_owned()
    # If postmaster.pid remains, LabPostgres.start enforces its existing
    # verified-crash policy; never delete or replace a foreign PID file.
    pg.start(timeout=min(180, _remaining(deadline)))
    need(pg.started is True, "LAB_RECOVERY_RESTART_NOT_CONFIRMED")
    pg._verify_postmaster()


def _revoke(pg, old, deadline):
    # Single guarded SQL UPDATE; a timeout/unknown commit cannot be taken
    # as success until the durable readback is independently performed.
    query = (
        "UPDATE public.lab_writer_fence SET active=false"
        " WHERE resource_id='grid-market-data-primary'"
        f" AND owner='{old['owner']}' AND namespace='{old['namespace']}'"
        f" AND generation={old['generation']} AND token={old['token']}"
        " AND active=true RETURNING generation"
    )
    try:
        _bounded_sql(pg, query, deadline)
    except Exception:
        # Re-reading under a fresh owner-only connection is mandatory.
        pass
    need(_fence_state(pg, old, deadline) ==
         f"{old['generation']}|{old['token']}|f|{old['backend_pid']}",
         "LAB_RECOVERY_REVOCATION_UNVERIFIED")


def _pending_outcome(pg, pending, deadline):
    """Read-only exact immutable outcome after unknown COMMIT.

    Duplicate-key errors, cursor presence, and pending metadata alone are
    never delivery ACK. NO retry/INSERT occurs in this SQL recovery lane.
    """
    if pending is None:
        return "ABSENT"
    symbol = pending["symbol"]
    start_ms = pending["start_ms"]
    fingerprint = pending["fingerprint"]
    content_id = pending["content_id"]
    # All values are already checked by read_lab_pending's C-owned parser.
    query = (
        "SELECT CASE"
        " WHEN EXISTS (SELECT 1 FROM public.provenance_minutes p"
        f" WHERE p.symbol='{symbol}' AND p.start_ms={start_ms}"
        f" AND p.fingerprint='{fingerprint}'"
        f" AND p.content_id='{content_id}'"
        f" AND p.record->>'dataset_fingerprint'='{fingerprint}')"
        " AND NOT EXISTS (SELECT 1 FROM public.provenance_minutes q"
        f" WHERE q.symbol='{symbol}' AND q.start_ms={start_ms}"
        f" AND (q.fingerprint<>'{fingerprint}'"
        f" OR q.content_id<>'{content_id}'"
        f" OR q.record->>'dataset_fingerprint' IS DISTINCT FROM '{fingerprint}'))"
        " THEN 'MATCH'"
        " WHEN EXISTS (SELECT 1 FROM public.provenance_minutes p"
        f" WHERE p.symbol='{symbol}' AND p.start_ms={start_ms}"
        f" OR p.fingerprint='{fingerprint}') THEN 'CONFLICT'"
        " ELSE 'MISSING' END"
    )
    result = _bounded_sql(pg, query, deadline)
    need(result in ("MATCH", "CONFLICT", "MISSING"),
         "LAB_RECOVERY_IMMUTABLE_OUTCOME_UNVERIFIED")
    return result


def _snapshot(pg, streams, deadline):
    """Read durable SQL from separate C-owned subprocesses, never replay."""
    result = {}
    for stream in streams:
        _remaining(deadline)
        # Post-restart SQL remains diagnostic only. Keep the original C
        # read helpers intact; no dynamic override of the owner object.
        pending = read_lab_pending(pg, stream_id=stream,
                                   timeout=min(120, _remaining(deadline)))
        _remaining(deadline)
        checkpoint = read_lab_checkpoint(pg, stream_id=stream,
                                         timeout=min(120, _remaining(deadline)))
        _remaining(deadline)
        outcome = _pending_outcome(pg, pending, deadline)
        _remaining(deadline)
        result[stream] = {"pending": pending, "checkpoint": checkpoint,
                          "immutable_outcome": outcome}
    return result



def contain_exclusive_lab_cluster(pg, *, old, quiesced=False,
                                  max_seconds=120):
    """C-owned stop-only containment sharing the SAME serialization guard.

    E orchestrates this operation but must await termination of its own
    dispatch worker before any new call; a timeout does NOT imply extinction.
    A stopped cluster is not a verified backend/OS Root receipt.
    """
    need(type(pg) is LabPostgres, "LAB_RECOVERY_PG_TYPE_INVALID")
    need(quiesced is True, "LAB_RECOVERY_QUIESCENCE_REQUIRED")
    need(type(max_seconds) in (int, float) and 10 <= max_seconds <= 180,
         "LAB_RECOVERY_DEADLINE_INVALID")
    old = _validate_old(old)
    deadline = time.monotonic() + max_seconds
    with _GUARD:
        need(_STATES.get(pg) is None, "LAB_RECOVERY_REENTRY_OR_POISONED")
        _STATES[pg] = "IN_PROGRESS"
    try:
        _remaining(deadline)
        _require_pg(pg)
        need(pg.started is True, "LAB_RECOVERY_NOT_STARTED")
        need(observe_old_lab_backend(
            pg, **old, timeout=min(120, _remaining(deadline))) == "STILL_ALIVE",
            "LAB_RECOVERY_OLD_BACKEND_UNVERIFIED")
        need(_fence_state(pg, old, deadline) ==
             f"{old['generation']}|{old['token']}|t|{old['backend_pid']}",
             "LAB_RECOVERY_OLD_FENCE_MISMATCH")
        _stop_started(pg, deadline)
        _remaining(deadline)
        with _GUARD:
            _STATES[pg] = "STOPPED_UNVERIFIED"
        return {"schema": "c-isolated-pg18-containment.v1",
                "scope": "ISOLATED_LAB_ONLY",
                "state": "UNKNOWN",
                "old_backend_extinct": False,
                "durable_fence_verified": False,
                "native_admitted": False,
                "trading_authorized": False}
    except BaseException:
        with _GUARD:
            _STATES[pg] = "POISONED"
        raise


def recover_exclusive_lab_cluster(pg, *, old, streams=(), quiesced=False,
                                  max_seconds=180):
    """Serialize STOP/RESTART/REVOKE on one original C LabPostgres object.

    Supports already-stopped postmaster from E containment, but only when
    the same owner object persists and C can read the saved durable fence
    after starting. The caller's quiesced flag is for synthetic LAB only.
    """
    # Validate exact class BEFORE any method, including ownership checks.
    need(type(pg) is LabPostgres, "LAB_RECOVERY_PG_TYPE_INVALID")
    need(quiesced is True, "LAB_RECOVERY_QUIESCENCE_REQUIRED")
    need(type(max_seconds) in (int, float) and 10 <= max_seconds <= 300,
         "LAB_RECOVERY_DEADLINE_INVALID")
    need(type(streams) in (list, tuple) and len(streams) <= 64,
         "LAB_RECOVERY_STREAMS_INVALID")
    streams = tuple(_stream(s) for s in streams)
    need(len(set(streams)) == len(streams), "LAB_RECOVERY_DUPLICATE_STREAM")
    old = _validate_old(old)
    deadline = time.monotonic() + max_seconds
    with _GUARD:
        state = _STATES.get(pg)
        if state not in (None, "STOPPED_UNVERIFIED"):
            raise LabAdmissionRejected("LAB_RECOVERY_REENTRY_OR_POISONED")
        # Prior stop-only is a narrow C-contained state; NEVER trust it as
        # a Root/OS extinction receipt. It only allows SQL revalidation.
        _STATES[pg] = "IN_PROGRESS"
    try:
        _remaining(deadline)
        _require_pg(pg)
        _remaining(deadline)
        # If E stop-only already completed on this same owner object, do
        # not stop a second time; verify and restart through C only.
        if pg.started is True:
            need(observe_old_lab_backend(pg, **old,
                   timeout=min(120, _remaining(deadline))) == "STILL_ALIVE",
                 "LAB_RECOVERY_OLD_BACKEND_UNVERIFIED")
            need(_fence_state(pg, old, deadline) ==
                 f"{old['generation']}|{old['token']}|t|{old['backend_pid']}",
                 "LAB_RECOVERY_OLD_FENCE_MISMATCH")
            _stop_started(pg, deadline)
        else:
            need(pg.started is False, "LAB_RECOVERY_UNKNOWN_CLUSTER_STATE")
        _remaining(deadline)
        _restart_stopped(pg, deadline)
        need(observe_old_lab_backend(pg, **old,
             timeout=min(120, _remaining(deadline))) == "EXTINCT",
             "LAB_RECOVERY_BACKEND_NOT_EXTINCT")
        need(_fence_state(pg, old, deadline) in (
            f"{old['generation']}|{old['token']}|t|{old['backend_pid']}",
            f"{old['generation']}|{old['token']}|f|{old['backend_pid']}"),
            "LAB_RECOVERY_HIGH_WATER_CHANGED")
        custody = fenced_lab_witness(pg,
                                    timeout=min(120, _remaining(deadline)))
        need(custody["direct_writer_insert"] is False,
             "LAB_RECOVERY_SQL_FENCE_BYPASS")
        _revoke(pg, old, deadline)
        snapshots = _snapshot(pg, streams, deadline)
        _remaining(deadline)
        return {
            "schema": "c-isolated-pg18-recovery-diagnostic.v2",
            "scope": "ISOLATED_LAB_ONLY",
            "old_generation": old["generation"],
            "old_token": old["token"],
            "old_backend_pid": old["backend_pid"],
            "old_backend_start": old["backend_start"],
            "durable_fence_active": False,
            "stream_snapshots": snapshots,
            "native_admitted": False,
            "root_consul_admitted": False,
            "execution_authority": False,
            "paper_admitted": False,
            "trading_authorized": False,
        }
    except BaseException:
        # Keep the C-owned recovery object permanently quarantined after
        # an unknown outcome. No retry while a previous worker may be alive.
        with _GUARD:
            _STATES[pg] = "POISONED"
        raise
    finally:
        with _GUARD:
            if _STATES.get(pg) == "IN_PROGRESS":
                _STATES[pg] = "COMPLETE_DENIED"
