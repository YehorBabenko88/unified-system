"""Single C-owned serialized isolated LAB PostgreSQL recovery state machine.

This is a disposable-LAB diagnostic, NOT Root/Consul authorization.
E supplies STOP/deny control-plane orchestration and A supplies independent
OS proof; neither caller booleans nor local SQL receipts authorize native
Grid restart. Never call arbitrary pg_terminate_backend(pid).
"""
import threading
import time
import os
import stat
import subprocess
from datetime import datetime
from dataclasses import dataclass
from types import MappingProxyType

from .lab_simulation_admission import LabAdmissionRejected, need
from .lab_postgres import LabPostgres
from .lab_pg_fence import _scope, fenced_lab_witness, observe_old_lab_backend
from .lab_pg_checkpoint import _stream, read_lab_pending, read_lab_checkpoint

# C solely arbitrates the *physical* private data root, not Python object id.
# Strong references deliberately prevent registry eviction after TIMEOUT or
# a poisoned worker. One C process, one exclusive LAB data root.
_GUARD = threading.Lock()
_STATES = {}
_ORIGINAL_C_PID = os.getpid()
# Also exclude distinct mount/path aliases that reference the SAME pgdata inode.
_DATA_OWNERS = {}


@dataclass(frozen=True)
class _OwnedRecovery:
    pg: object
    root: tuple
    data_identity: tuple
    marker: str
    old: tuple
    phase: str
    old_postmaster_pid: int = 0
    old_os_incarnation: tuple = ()
    wal_fault: str = "CLEAN"
    log_position: int = 0
    lock_fd: int = -1
    lock_witness_fd: int = -1
    worker_tid: int = 0


def _resource(pg):
    """Validate original C marker and bind one physically identical data root."""
    pg._verify_owned()
    root = pg.root.resolve(strict=True)
    data = pg.data.resolve(strict=True)
    need(data.parent == root and data.name == "pgdata",
         "LAB_RECOVERY_DATA_ROOT_MISMATCH")
    st = root.stat()
    ds = data.stat()
    need((st.st_dev, st.st_ino) == pg._root_identity,
         "LAB_RECOVERY_ROOT_CHANGED")
    return (st.st_dev, st.st_ino, str(root))


def _data_identity(pg):
    pg._verify_owned()
    data = pg.data.stat()
    return (data.st_dev, data.st_ino)


def _acquire_cluster_os_lock(pg):
    """OS-backed exclusive lock for this original C-owned physical LAB root.

    Nonblocking kernel lock, not a JSON/boolean grant. The FD remains pinned
    in C's one-shot state for its entire process lifetime, including failed,
    timed-out and cancelled recovery. No lock stealing, unlink or retry.
    Linux flock and Windows msvcrt.locking are advisory: *all C writers*
    must obey this same path; Root/Consul must additionally authorize epoch.
    """
    need(os.getpid() == _ORIGINAL_C_PID,
         "LAB_RECOVERY_FORKED_WORKER_DENIED")
    pg._verify_owned()
    path = pg.root / ".lab-postgres-recovery.lock"
    expected = ("C_PG18_LOCK_V1:" + pg._nonce + "\n").encode("ascii")
    flags = os.O_RDWR | getattr(os, "O_BINARY", 0)
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    cloexec = getattr(os, "O_CLOEXEC", 0)
    fd = None
    witness_fd = None
    created = False
    try:
        try:
            fd = os.open(path, flags | os.O_CREAT | os.O_EXCL
                         | nofollow | cloexec, 0o600)
            created = True
        except FileExistsError:
            fd = os.open(path, flags | nofollow | cloexec)
        info = os.fstat(fd)
        need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
             and not (getattr(info, "st_file_attributes", 0) & 0x400),
             "LAB_RECOVERY_OS_LOCK_UNSAFE_FILE")
        if os.name != "nt":
            need(info.st_uid == os.getuid()
                 and info.st_mode & 0o077 == 0,
                 "LAB_RECOVERY_OS_LOCK_BAD_PERMISSIONS")
        path_info = path.lstat()
        need(stat.S_ISREG(path_info.st_mode) and not path.is_symlink()
             and (path_info.st_dev, path_info.st_ino)
                 == (info.st_dev, info.st_ino)
             and not (getattr(path_info, "st_file_attributes", 0) & 0x400),
             "LAB_RECOVERY_OS_LOCK_PATH_CHANGED")
        # Python 3 file descriptors are noninheritable by default. Explicit
        # close-on-exec excludes accidental child ownership on POSIX/Windows.
        os.set_inheritable(fd, False)
        try:
            if os.name == "nt":
                import msvcrt
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise LabAdmissionRejected(
                "LAB_RECOVERY_CROSS_PROCESS_LOCK_BUSY") from exc
        if created:
            os.lseek(fd, 0, os.SEEK_SET)
            os.write(fd, expected)
            os.fsync(fd)
        else:
            os.lseek(fd, 0, os.SEEK_SET)
            actual = os.read(fd, 256)
            need(actual == expected, "LAB_RECOVERY_OS_LOCK_OWNER_MISMATCH")
        # A rename/replacement after opening does not transfer the OS lock.
        # Failure keeps this recovery DENIED, not a fabricated reservation.
        post = path.lstat()
        need((post.st_dev, post.st_ino) == (info.st_dev, info.st_ino),
             "LAB_RECOVERY_OS_LOCK_PATH_CHANGED")
        witness_fd = os.dup(fd)
        os.set_inheritable(witness_fd, False)
        return fd, witness_fd
    except BaseException:
        if witness_fd is not None:
            os.close(witness_fd)
        if fd is not None:
            os.close(fd)
        raise


def _verify_cluster_os_lock(pg, fd, witness_fd):
    # A forked child inherits the open file description/lock and must NEVER
    # be allowed to reuse the parent's C recovery capability.
    need(os.getpid() == _ORIGINAL_C_PID,
         "LAB_RECOVERY_FORKED_WORKER_DENIED")
    need(type(fd) is int and fd >= 0
         and type(witness_fd) is int and witness_fd >= 0
         and fd != witness_fd,
         "LAB_RECOVERY_OS_LOCK_NOT_RETAINED")
    try:
        info = os.fstat(fd)
        witness_info = os.fstat(witness_fd)
        path = pg.root / ".lab-postgres-recovery.lock"
        path_info = path.lstat()
        need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
             and stat.S_ISREG(path_info.st_mode)
             and not path.is_symlink()
             and (info.st_dev, info.st_ino)
                 == (path_info.st_dev, path_info.st_ino)
             and (witness_info.st_dev, witness_info.st_ino)
                 == (info.st_dev, info.st_ino)
             and not (getattr(path_info, "st_file_attributes", 0) & 0x400),
             "LAB_RECOVERY_OS_LOCK_LOST")
        # os.dup() retains the SAME kernel open-file description. An FD
        # closed and reopened on the same inode can pass fstat but cannot
        # share the retained witness's seek offset. No lock reacquisition.
        os.lseek(fd, 0, os.SEEK_SET)
        need(os.lseek(witness_fd, 0, os.SEEK_CUR) == 0,
             "LAB_RECOVERY_OS_LOCK_DESCRIPTION_CHANGED")
        expected = ("C_PG18_LOCK_V1:" + pg._nonce + "\n").encode("ascii")
        need(os.read(fd, len(expected) + 1) == expected,
             "LAB_RECOVERY_OS_LOCK_OWNER_MISMATCH")
        need(os.lseek(witness_fd, 0, os.SEEK_CUR) == len(expected),
             "LAB_RECOVERY_OS_LOCK_DESCRIPTION_CHANGED")
    except (OSError, ValueError) as exc:
        raise LabAdmissionRejected("LAB_RECOVERY_OS_LOCK_LOST") from exc


def _old_tuple(old):
    return tuple(old[field] for field in (
        "owner", "namespace", "generation", "token",
        "backend_pid", "backend_start"))


def _begin(pg, root, old, *, mode):
    """No stop/start may overlap across distinct objects for one root."""
    with _GUARD:
        need(os.getpid() == _ORIGINAL_C_PID,
             "LAB_RECOVERY_FORKED_WORKER_DENIED")
        data = _data_identity(pg)
        previous_root = _DATA_OWNERS.get(data)
        need(previous_root is None or previous_root == root,
             "LAB_RECOVERY_PHYSICAL_DATA_ALREADY_OWNED")
        existing = _STATES.get(root)
        if mode == "STOP_ONLY":
            need(existing is None, "LAB_RECOVERY_RESOURCE_ALREADY_OWNED")
        elif existing is None:
            # A live backend may be recovered from an original owner; a
            # previously stopped object without our old retained proof may not.
            need(pg.started is True,
                 "LAB_RECOVERY_STOPPED_WITHOUT_C_EVIDENCE")
        else:
            need(existing.phase == "STOPPED_UNVERIFIED"
                 and existing.pg is pg and existing.root == root
                 and existing.data_identity == _data_identity(pg)
                 and existing.marker == pg._nonce
                 and existing.old == _old_tuple(old)
                 and existing.old_postmaster_pid > 1
                 and len(existing.old_os_incarnation) == 2
                 and pg.started is False,
                 "LAB_RECOVERY_STOPPED_OWNER_MISMATCH")
        if existing is not None:
            _verify_cluster_os_lock(pg, existing.lock_fd,
                                    existing.lock_witness_fd)
            preserved = existing
            fd = existing.lock_fd
            witness_fd = existing.lock_witness_fd
        else:
            # Open a real exclusive cross-process kernel lock BEFORE any
            # process, WAL or SQL side effect. A busy lock always DENIES.
            fd, witness_fd = _acquire_cluster_os_lock(pg)
            preserved = _OwnedRecovery(
                pg=pg, root=root, data_identity=data,
                marker=pg._nonce, old=_old_tuple(old),
                phase="IN_PROGRESS", lock_fd=fd,
                lock_witness_fd=witness_fd,
                worker_tid=threading.get_ident())
        _DATA_OWNERS[data] = root
        _STATES[root] = _OwnedRecovery(
            pg=pg, root=root, data_identity=data,
            marker=pg._nonce, old=_old_tuple(old),
            phase="IN_PROGRESS",
            old_postmaster_pid=preserved.old_postmaster_pid,
            old_os_incarnation=preserved.old_os_incarnation,
            wal_fault=preserved.wal_fault,
            log_position=preserved.log_position,
            lock_fd=fd,
            lock_witness_fd=witness_fd,
            worker_tid=threading.get_ident())
        return existing


def _state(root, pg, old, phase, *, pid=0, os_identity=(),
           wal_fault="CLEAN", log_position=0):
    with _GUARD:
        prior = _STATES.get(root)
        need(prior is not None and prior.pg is pg
             and prior.phase == "IN_PROGRESS"
             and prior.old == _old_tuple(old)
             and prior.root == root
             and prior.data_identity == _data_identity(pg)
             and prior.marker == pg._nonce
             and prior.worker_tid == threading.get_ident(),
             "LAB_RECOVERY_STATE_MISMATCH")
        _STATES[root] = _OwnedRecovery(
            pg=pg, root=root, data_identity=prior.data_identity,
            marker=pg._nonce, old=_old_tuple(old),
            phase=phase,
            old_postmaster_pid=pid or prior.old_postmaster_pid,
            old_os_incarnation=os_identity or prior.old_os_incarnation,
            wal_fault=wal_fault if wal_fault != "CLEAN" else prior.wal_fault,
            log_position=log_position or prior.log_position,
            lock_fd=prior.lock_fd,
            lock_witness_fd=prior.lock_witness_fd,
            worker_tid=prior.worker_tid)


def _poison(root, pg):
    with _GUARD:
        prior = _STATES.get(root)
        if (prior is not None and prior.pg is pg
                and prior.worker_tid == threading.get_ident()
                and prior.phase == "IN_PROGRESS"):
            _STATES[root] = _OwnedRecovery(
                pg=prior.pg, root=prior.root, data_identity=prior.data_identity,
                marker=prior.marker,
                old=prior.old, phase="POISONED",
                old_postmaster_pid=prior.old_postmaster_pid,
                old_os_incarnation=prior.old_os_incarnation,
                wal_fault=prior.wal_fault, log_position=prior.log_position,
                lock_fd=prior.lock_fd,
            lock_witness_fd=prior.lock_witness_fd,
                worker_tid=prior.worker_tid)


def _require_held_recovery_lock(pg, root, old):
    with _GUARD:
        current = _STATES.get(root)
        need(current is not None and current.phase == "IN_PROGRESS"
             and current.pg is pg and current.old == _old_tuple(old)
             and current.marker == pg._nonce
             and current.worker_tid == threading.get_ident(),
             "LAB_RECOVERY_OS_LOCK_OWNER_MISMATCH")
        fd = current.lock_fd
        witness_fd = current.lock_witness_fd
    _verify_cluster_os_lock(pg, fd, witness_fd)


def _retain_owned_postmaster(pg, deadline):
    """A's *single* retained OS identity primitive, after C owner checks.

    Its live kernel object is held across C's original pg.stop(). A missing
    A implementation fails CLOSED; no alternate process observer is made.
    """
    try:
        from .runtime_process import RetainedOsProcessWait, _identity
    except ImportError as exc:
        raise LabAdmissionRejected(
            "LAB_RECOVERY_A_RETAINED_OS_SOURCE_REQUIRED") from exc
    pid = pg._verify_postmaster()
    created = _identity(pid)
    need(type(created) is list and len(created) == 2
         and all(type(v) is str and v for v in created),
         "LAB_RECOVERY_OS_IDENTITY_UNKNOWN")
    need(os.path.normcase(os.path.realpath(created[1])) ==
         os.path.normcase(os.path.realpath(str(pg.tools["postgres"]))),
         "LAB_RECOVERY_OS_IMAGE_MISMATCH")
    _remaining(deadline)
    try:
        wait = RetainedOsProcessWait(pid, created)
    except Exception as exc:
        raise LabAdmissionRejected(
            "LAB_RECOVERY_RETAINED_HANDLE_UNKNOWN") from exc
    return wait, pid, tuple(created)


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
    return MappingProxyType(dict(old, owner=owner, namespace=namespace))


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


def _crashed_control_attested(pg, deadline):
    """Independent PG18 pg_controldata check after test-only postmaster SIGKILL.

    A real dirty postmaster control state qualifies the process-crash branch;
    a graceful shutdown / missing control data never counts as WAL recovery.
    """
    pg._verify_owned()
    suffix = ".exe" if os.name == "nt" else ""
    tool = pg.bin / ("pg_controldata" + suffix)
    need(tool.is_file() and not tool.is_symlink()
         and tool.parent.resolve(strict=True) == pg.bin.resolve(strict=True),
         "LAB_RECOVERY_PG_CONTROL_TOOL_UNVERIFIED")
    result = subprocess.run(
        [str(tool), "-D", str(pg.data)],
        capture_output=True, text=True,
        timeout=min(30, _remaining(deadline)),
        env=pg._env("lab_owner"))
    need(result.returncode == 0
         and "Database cluster state:" in result.stdout
         and "in production" in result.stdout,
         "LAB_RECOVERY_PG_CONTROL_NOT_CRASHED")


def _wal_replay_readback(pg, *, fault, log_position, deadline):
    if fault != "PROCESS_CRASH_TEST":
        return "CLEAN_SHUTDOWN_ONLY"
    _remaining(deadline)
    pg._verify_owned()
    need(type(log_position) is int and log_position >= 0,
         "LAB_RECOVERY_LOG_POSITION_INVALID")
    need(pg.log.is_file() and not pg.log.is_symlink(),
         "LAB_RECOVERY_LOG_UNVERIFIED")
    with pg.log.open("rb") as log:
        log.seek(log_position)
        tail=log.read(4*1024*1024).decode("utf-8", errors="replace")
    _remaining(deadline)
    need("automatic recovery in progress" in tail
         and "redo starts at" in tail
         and "database system is ready to accept connections" in tail,
         "LAB_RECOVERY_WAL_REPLAY_NOT_ATTESTED")
    return "LAB_PROCESS_CRASH_WAL_REPLAY_LOG_VERIFIED"


def _stop_started(pg, deadline, *, fault="CLEAN"):
    need(pg.started is True, "LAB_RECOVERY_NOT_STARTED")
    need(fault in ("CLEAN", "PROCESS_CRASH_TEST"),
         "LAB_RECOVERY_FAULT_MODE_INVALID")
    wait, pid, created = _retain_owned_postmaster(pg, deadline)
    log_position = 0
    try:
        if fault == "PROCESS_CRASH_TEST":
            # A disposable LAB postmaster SIGKILL test (NOT power loss). Never
            # expose this from Root's production recovery dispatcher.
            need(os.environ.get("LAB_C_PG18_PROCESS_CRASH_TEST") == "1",
                 "LAB_RECOVERY_FAULT_INJECTION_NOT_ALLOWED")
            pg._verify_owned()
            if pg.log.exists():
                need(pg.log.is_file() and not pg.log.is_symlink(),
                     "LAB_RECOVERY_LOG_UNVERIFIED")
                log_position = pg.log.stat().st_size
            pg.crash(timeout=min(120, _remaining(deadline)))
        else:
            pg.stop(timeout=min(120, _remaining(deadline)))
        need(wait.wait_exited(min(60, _remaining(deadline))) is True,
             "LAB_RECOVERY_OLD_POSTMASTER_NOT_EXITED")
        need(pg.started is False, "LAB_RECOVERY_STOP_NOT_CONFIRMED")
        if fault == "PROCESS_CRASH_TEST":
            _crashed_control_attested(pg, deadline)
    finally:
        wait.close()
    return pid, created, log_position


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
                                  max_seconds=120, fault="CLEAN"):
    """C-owned stop-only containment sharing the SAME serialization guard.

    E orchestrates this operation but must await termination of its own
    dispatch worker before any new call; a timeout does NOT imply extinction.
    A stopped cluster is not a verified backend/OS Root receipt.
    """
    need(type(pg) is LabPostgres, "LAB_RECOVERY_PG_TYPE_INVALID")
    need(quiesced is True, "LAB_RECOVERY_QUIESCENCE_REQUIRED")
    need(type(max_seconds) in (int, float) and 10 <= max_seconds <= 180,
         "LAB_RECOVERY_DEADLINE_INVALID")
    need(type(fault) is str and fault in ("CLEAN", "PROCESS_CRASH_TEST"),
         "LAB_RECOVERY_FAULT_MODE_INVALID")
    need(fault == "CLEAN" or
         os.environ.get("LAB_C_PG18_PROCESS_CRASH_TEST") == "1",
         "LAB_RECOVERY_FAULT_INJECTION_NOT_ALLOWED")
    old = _validate_old(old)
    deadline = time.monotonic() + max_seconds
    root = None
    try:
        _remaining(deadline)
        _require_pg(pg)
        root = _resource(pg)
        _begin(pg, root, old, mode="STOP_ONLY")
        _require_held_recovery_lock(pg, root, old)
        pg._bind_recovery_lifecycle(_STATES[root].lock_fd)
        need(pg.started is True, "LAB_RECOVERY_NOT_STARTED")
        need(observe_old_lab_backend(
            pg, **old, timeout=min(120, _remaining(deadline))) == "STILL_ALIVE",
            "LAB_RECOVERY_OLD_BACKEND_UNVERIFIED")
        need(_fence_state(pg, old, deadline) ==
             f"{old['generation']}|{old['token']}|t|{old['backend_pid']}",
             "LAB_RECOVERY_OLD_FENCE_MISMATCH")
        _require_held_recovery_lock(pg, root, old)
        pid, created, log_position = _stop_started(
            pg, deadline, fault=fault)
        _remaining(deadline)
        _state(root, pg, old, "STOPPED_UNVERIFIED",
               pid=pid, os_identity=created,
               wal_fault=fault, log_position=log_position)
        return {"schema": "c-isolated-pg18-containment.v1",
                "scope": "ISOLATED_LAB_ONLY",
                "state": "UNKNOWN",
                "old_backend_extinct": False,
                "durable_fence_verified": False,
                "native_admitted": False,
                "trading_authorized": False}
    except BaseException:
        if root is not None:
            _poison(root, pg)
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
    root = None
    try:
        _remaining(deadline)
        _require_pg(pg)
        root = _resource(pg)
        previous = _begin(pg, root, old, mode="RECOVER")
        _require_held_recovery_lock(pg, root, old)
        pg._bind_recovery_lifecycle(_STATES[root].lock_fd)
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
            _require_held_recovery_lock(pg, root, old)
            pid, created, log_position = _stop_started(pg, deadline)
            _state(root, pg, old, "IN_PROGRESS",
                   pid=pid, os_identity=created)
        else:
            need(previous is not None
                 and previous.phase == "STOPPED_UNVERIFIED"
                 and previous.pg is pg
                 and previous.old == _old_tuple(old)
                 and previous.old_postmaster_pid > 1
                 and len(previous.old_os_incarnation) == 2
                 and pg.started is False,
                 "LAB_RECOVERY_STOPPED_WITHOUT_C_EVIDENCE")
        _remaining(deadline)
        _require_held_recovery_lock(pg, root, old)
        _restart_stopped(pg, deadline)
        with _GUARD:
            previous_state = _STATES.get(root)
            need(previous_state is not None and previous_state.pg is pg
                 and previous_state.phase == "IN_PROGRESS",
                 "LAB_RECOVERY_STALE_STATE")
            fault = previous_state.wal_fault
            log_position = previous_state.log_position
        wal_readback = _wal_replay_readback(
            pg, fault=fault, log_position=log_position, deadline=deadline)
        _remaining(deadline)
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
        _require_held_recovery_lock(pg, root, old)
        return {
            "schema": "c-isolated-pg18-recovery-diagnostic.v2",
            "scope": "ISOLATED_LAB_ONLY",
            "old_generation": old["generation"],
            "old_token": old["token"],
            "old_backend_pid": old["backend_pid"],
            "old_backend_start": old["backend_start"],
            "durable_fence_active": False,
            "wal_recovery": wal_readback,
            "stream_snapshots": snapshots,
            "native_admitted": False,
            "root_consul_admitted": False,
            "execution_authority": False,
            "paper_admitted": False,
            "trading_authorized": False,
        }
    except BaseException:
        # An uncertain worker stays quarantined across same physical root.
        if root is not None:
            _poison(root, pg)
        raise
    finally:
        if root is not None:
            with _GUARD:
                prior = _STATES.get(root)
                if (prior is not None and prior.pg is pg
                        and prior.phase == "IN_PROGRESS"
                        and prior.worker_tid == threading.get_ident()):
                    _STATES[root] = _OwnedRecovery(
                        pg=prior.pg, root=prior.root,
                        data_identity=prior.data_identity,
                        marker=prior.marker,
                        old=prior.old, phase="COMPLETE_DENIED",
                        old_postmaster_pid=prior.old_postmaster_pid,
                        old_os_incarnation=prior.old_os_incarnation,
                        wal_fault=prior.wal_fault, log_position=prior.log_position,
                        lock_fd=prior.lock_fd,
            lock_witness_fd=prior.lock_witness_fd,
                        worker_tid=prior.worker_tid)
