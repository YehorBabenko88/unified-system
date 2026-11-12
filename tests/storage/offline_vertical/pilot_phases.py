"""Root-invoked DATA_ONLY phases; not a launcher, daemon or authority API.

SOURCE ONLY until Root admits exact imports/runtime/effects. No main/discovery.
Root pins six producer entries once and retains closure bytes outside the child.
"""
import hashlib
import json
from pathlib import Path
import sqlite3
import time
import re

from unified_system.journal import Journal
from unified_system.storage.object_store import ObjectStore, _parents, _plain, _read as _read_owned_file
from unified_system.storage.contracts import _UUID
from unified_system.storage.publication_records import RetainedPublicationIntent
from unified_system.storage.publication_recovery import PendingPublicationJournal
from unified_system.storage.result_publication import (
    LocalByteClosure, build_local_closure, stage_local_closure,
    readback_local_closure, copy_local_closure)

STORE_ID = '96dce424-a40b-4f25-8500-26738dd278e5'
BACKUP_ID = '39e675b0-27c9-446b-ae15-4f919dfdbec4'
RESTORE_ID = '489e5730-862a-4c15-94be-7aa6100b7153'
ORIGINAL_ID = '32f2c66d-6f40-4b11-95ca-c56f7bea37c2'
ROLES = frozenset(('artifact', 'descriptor', 'request', 'input_rows',
                   'input_coverage', 'producer_metadata'))


def _path(value):
    path = Path(value)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('admitted absolute private path required')
    return path


def _claim(raw):
    claim = LocalByteClosure(raw)
    objects = claim.value['objects']
    if (len(objects) != 6 or {x['role'] for x in objects} != ROLES
            or sum(int(x['bytes']) for x in objects) > 65536
            or any(x['dependencies'] != [] for x in objects)):
        raise ValueError('exact bounded six-role local fixture closure required')
    return claim


def _sql(journal):
    # Validate the actual chain before reporting decoded SQL rows.
    checked = journal.read()
    connection = sqlite3.connect(journal.path.absolute().as_uri() + '?mode=ro', uri=True)
    try:
        connection.execute('PRAGMA query_only = ON')
        integrity = connection.execute('PRAGMA integrity_check').fetchall()
        rows = connection.execute('SELECT sequence,state,previous_hash,digest,receipt '
                                  'FROM transitions ORDER BY sequence LIMIT 65').fetchall()
        count = connection.execute('SELECT COUNT(*) FROM transitions').fetchone()[0]
    finally:
        connection.close()
    if integrity != [('ok',)] or count != len(checked) or count != len(rows):
        raise ValueError('journal SQL/chain observation mismatch')
    return dict(row_count=count, integrity_check='ok', rows=[
        dict(sequence=s, state=state, previous_hash=previous, digest=digest,
             receipt=json.loads(receipt)) for s, state, previous, digest, receipt in rows])


def seed(new_root, entries):
    """M0: exclusively create own root; stage exact bytes, local uncertainty only."""
    root = _path(new_root)
    if root.exists():
        raise ValueError('pilot root must not exist')
    claim = _claim(build_local_closure(entries).canonical_bytes)
    root.mkdir(exist_ok=False)
    store = ObjectStore.create(root / 'archive', store_id=STORE_ID)
    stage_local_closure(store, claim, entries)
    database = root / 'local.sqlite'
    with database.open('xb'):
        pass
    journal = Journal(database)
    journal.initialize()
    pending = PendingPublicationJournal(journal, store)
    original = RetainedPublicationIntent(ORIGINAL_ID, claim.canonical_bytes)
    # Opaque local test bytes, never a native intent or historical checkpoint.
    pending.retain(original)
    pending.retain(original)
    pending.mark_attempt_uncertain(ORIGINAL_ID)
    pending.mark_attempt_uncertain(ORIGINAL_ID)
    return inspect(root, claim.canonical_bytes)


def inspect(owned_root, expected_closure_bytes, *, expected_store_id=STORE_ID):
    """M1: bounded read-only reopen. Root must prove prior child retirement."""
    root = _path(owned_root)
    claim = _claim(expected_closure_bytes)
    store = ObjectStore.open(root / 'archive', store_id=expected_store_id)
    if store.read(claim.sha256, max_bytes=32768) != expected_closure_bytes:
        raise ValueError('expected closure bytes changed')
    observed = readback_local_closure(store, claim)
    journal = Journal(root / 'local.sqlite')
    pending = PendingPublicationJournal(journal, store)
    original = pending.verify_staged_original(ORIGINAL_ID)
    if original.raw_bytes != expected_closure_bytes:
        raise ValueError('opaque local recovery bytes changed')
    observation = pending.observation(ORIGINAL_ID)
    sql = _sql(journal)
    if (sql['row_count'] != 2 or observation.local_phase != 'ATTEMPT_UNCERTAIN'
            or observation.native_outcome != 'UNKNOWN'
            or observation.publication_confirmed or observation.retry_authorized
            or observation.hold_release_authorized or observed.publication_confirmed):
        raise ValueError('local custody/UNKNOWN invariant failed')
    payloads = {}
    for entry in claim.value['objects']:
        raw = store.read(entry['sha256'], max_bytes=int(entry['bytes']))
        payloads[entry['role']] = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                                     decoded=json.loads(raw))
    return dict(profile='SYNTHETIC_DATA_ONLY_LOCAL_UNATTESTED',
                closure_sha256=claim.sha256, closure_bytes=claim.canonical_bytes.decode('ascii'),
                native_outcome='UNKNOWN', committed=False, authority_cursor=None,
                sql=sql, payloads=payloads)


def restore(owned_root, expected_closure_bytes, new_restore_parent):
    """M2: copy owned immutable closure to new local backup/restore roots only.

    SQLite is inspected in place, NOT copied live or restored by this phase.
    There is no physical-backup success or failure-domain eligibility claim.
    """
    before = inspect(owned_root, expected_closure_bytes)
    parent = _path(new_restore_parent)
    if parent.exists():
        raise ValueError('restore parent must not exist')
    claim = _claim(expected_closure_bytes)
    parent.mkdir(exist_ok=False)
    source = ObjectStore.open(_path(owned_root) / 'archive', store_id=STORE_ID)
    backup = ObjectStore.create(parent / 'backup', store_id=BACKUP_ID)
    restored = ObjectStore.create(parent / 'restored', store_id=RESTORE_ID)
    first = copy_local_closure(source, backup, claim)
    second = copy_local_closure(backup, restored, claim)
    readback = readback_local_closure(restored, claim)
    for value in (first, second):
        if value.replica_valid or value.failure_domain_verified or value.publication_confirmed:
            raise ValueError('unexpected local copy authority flag')
    if readback.publication_confirmed or readback.native_replica_eligible:
        raise ValueError('unexpected restore authority flag')
    for entry in claim.value['objects']:
        raw = restored.read(entry['sha256'], max_bytes=int(entry['bytes']))
        if hashlib.sha256(raw).hexdigest() != before['payloads'][entry['role']]['sha256']:
            raise ValueError('restored payload mismatch')
    return dict(profile='LOCAL_BYTE_COPY_RESTORE_ONLY', closure_sha256=claim.sha256,
                restored_object_count=len(readback.objects), committed=False,
                native_outcome='UNKNOWN', journal_restored=False,
                physical_backup_verified=False)


def _snapshot_deadline(deadline):
    now = time.monotonic_ns()
    if type(deadline) is not int or not 0 < deadline-now <= 30_000_000_000:
        raise ValueError('local snapshot deadline expired or invalid')


def _snapshot_sha(value):
    return type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _snapshot_db_seal(path):
    _parents(path.parent)
    for suffix in ('-wal', '-shm', '-journal'):
        sidecar = path.with_name(path.name + suffix)
        if sidecar.exists() or sidecar.is_symlink():
            raise ValueError('sidecar present; stopped immutable snapshot not admitted')
    raw, identity = _read_owned_file(path, 65536)
    if not raw:
        raise ValueError('source database is empty')
    return dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), file_identity=identity)


def _snapshot_names(path, maximum):
    names = set()
    for child in path.iterdir():
        if len(names) >= maximum:
            raise ValueError('snapshot namespace inventory exceeds profile')
        names.add(child.name)
    return names


def _snapshot_namespace(root, claim, expected_id):
    _parents(root)
    if _snapshot_names(root, 2) != {'archive', 'local.sqlite'}:
        raise ValueError('unknown source context files; no adoption')
    store = ObjectStore.open(root/'archive', store_id=expected_id)
    if _snapshot_names(root/'archive', 3) != {'owned-root.json', 'objects', 'staging'}:
        raise ValueError('unknown store files; no adoption')
    if any((root/'archive'/'staging').iterdir()):
        raise ValueError('incomplete staging; no snapshot promotion')
    expected = {entry['sha256'] for entry in claim.value['objects']} | {claim.sha256}
    if len(expected) != 7 or _snapshot_names(root/'archive'/'objects', 7) != expected:
        raise ValueError('missing or orphan objects; no snapshot promotion')
    readback_local_closure(store, claim)
    return store


def _snapshot_copy_db(source, destination, expected_seal, max_pages, deadline):
    """SQLite backup API, no live directory copy; Root must retire all writers."""
    _snapshot_deadline(deadline)
    if _snapshot_db_seal(source) != expected_seal:
        raise ValueError('source DB seal changed before backup')
    _parents(destination.parent)
    with destination.open('xb'):
        pass
    initial = _plain(destination, directory=False)
    initial_identity = initial.st_dev, initial.st_ino
    src = dst = None
    try:
        src = sqlite3.connect(source.as_uri()+'?mode=ro&immutable=1', uri=True, timeout=1)
        src.execute('PRAGMA query_only = ON')
        src.execute('PRAGMA temp_store = MEMORY')
        page_count = src.execute('PRAGMA page_count').fetchone()[0]
        page_size = src.execute('PRAGMA page_size').fetchone()[0]
        if (type(page_count) is not int or not 1 <= page_count <= max_pages
                or type(page_size) is not int or not 512 <= page_size <= 65536
                or page_count*page_size != expected_seal['bytes']):
            raise ValueError('source database page profile mismatch')
        dst = sqlite3.connect(destination.as_uri()+'?mode=rw', uri=True, timeout=1)
        dst.execute('PRAGMA temp_store = MEMORY')

        def progress(status, remaining, total):
            _snapshot_deadline(deadline)
            if (status not in (sqlite3.SQLITE_OK, sqlite3.SQLITE_DONE)
                    or type(total) is not int or not 1 <= total <= max_pages
                    or type(remaining) is not int or not 0 <= remaining <= total):
                raise ValueError('backup busy/locked/status/page bound; no retry')

        src.backup(dst, pages=min(16, max_pages), progress=progress, sleep=0)
        _snapshot_deadline(deadline)
    finally:
        if dst is not None:
            dst.close()
        if src is not None:
            src.close()
    if _snapshot_db_seal(source) != expected_seal:
        raise ValueError('source DB seal changed during backup')
    destination_seal = _snapshot_db_seal(destination)
    if tuple(destination_seal['file_identity']) != initial_identity:
        raise ValueError('exclusive destination database identity changed')
    _snapshot_deadline(deadline)
    return destination_seal


def snapshot_restore(owned_root, expected_closure_bytes, new_backup_root, new_restored_root,
        *, expected_source_store_id, expected_backup_store_id, expected_restored_store_id,
        source_database_sha256, source_database_byte_count, source_database_file_identity,
        stopped_writer_barrier_sha256, max_backup_pages, deadline_monotonic_ns):
    """Prospective local SQLite+immutable snapshot, NOT MASTER M2 acceptance.

    The barrier hash is a Root evidence reference, not proof of process retirement.
    Root must verify STOPPED_WRITER_BARRIER before admitting this call. Every
    partial artifact is retained on failure; source writes/cleanup never occur.
    """
    _snapshot_deadline(deadline_monotonic_ns)
    if (not _snapshot_sha(source_database_sha256)
            or not _snapshot_sha(stopped_writer_barrier_sha256)
            or type(source_database_byte_count) is not int
            or not 1 <= source_database_byte_count <= 65536
            or type(source_database_file_identity) is not tuple
            or len(source_database_file_identity) != 2
            or any(type(x) is not int or x < 0 for x in source_database_file_identity)
            or type(max_backup_pages) is not int or not 1 <= max_backup_pages <= 128):
        raise ValueError('invalid explicit snapshot source seal/barrier/bounds')
    ids = (expected_source_store_id, expected_backup_store_id, expected_restored_store_id)
    if any(type(x) is not str or _UUID.fullmatch(x) is None for x in ids) or len(set(ids)) != 3:
        raise ValueError('three distinct Root-pinned owned store IDs required')
    root, backup, restored = map(_path, (owned_root, new_backup_root, new_restored_root))
    paths = (root, backup, restored)
    if (len(set(paths)) != 3 or any(a in b.parents for a in paths for b in paths if a != b)
            or backup.exists() or backup.is_symlink() or restored.exists() or restored.is_symlink()):
        raise ValueError('new distinct nonnested destination roots required')
    _parents(backup.parent)
    _parents(restored.parent)
    claim = _claim(expected_closure_bytes)
    source_seal = dict(sha256=source_database_sha256, bytes=source_database_byte_count,
                       file_identity=source_database_file_identity)
    if _snapshot_db_seal(root/'local.sqlite') != source_seal:
        raise ValueError('exact stopped source database seal mismatch')
    source = _snapshot_namespace(root, claim, expected_source_store_id)
    before = inspect(root, expected_closure_bytes, expected_store_id=expected_source_store_id)
    _snapshot_deadline(deadline_monotonic_ns)
    backup.mkdir(exist_ok=False)
    backup_store = ObjectStore.create(backup/'archive', store_id=expected_backup_store_id)
    copy_local_closure(source, backup_store, claim)
    backup_seal = _snapshot_copy_db(root/'local.sqlite', backup/'local.sqlite', source_seal,
                                    max_backup_pages, deadline_monotonic_ns)
    _snapshot_namespace(backup, claim, expected_backup_store_id)
    backup_readback = inspect(backup, expected_closure_bytes, expected_store_id=expected_backup_store_id)
    if backup_readback != before:
        raise ValueError('backup logical records or payloads differ')
    _snapshot_deadline(deadline_monotonic_ns)
    restored.mkdir(exist_ok=False)
    restored_store = ObjectStore.create(restored/'archive', store_id=expected_restored_store_id)
    copy_local_closure(backup_store, restored_store, claim)
    restored_seal = _snapshot_copy_db(backup/'local.sqlite', restored/'local.sqlite', backup_seal,
                                      max_backup_pages, deadline_monotonic_ns)
    _snapshot_namespace(restored, claim, expected_restored_store_id)
    readback = inspect(restored, expected_closure_bytes, expected_store_id=expected_restored_store_id)
    if readback != before or _snapshot_db_seal(root/'local.sqlite') != source_seal:
        raise ValueError('restored records or original source changed')
    _snapshot_deadline(deadline_monotonic_ns)
    return dict(scope='LOCAL_SOFTWARE_IMMUTABLE_AND_SQLITE_SNAPSHOT',
        closure_sha256=claim.sha256, restored_object_count=7, journal_row_count=2,
        journal_restored=True, logical_records_equal=True, native_outcome='UNKNOWN',
        committed=False, physical_backup_verified=False, process_restart_verified=False,
        stopped_writer_barrier_sha256=stopped_writer_barrier_sha256,
        source_database=source_seal, backup_database=backup_seal,
        restored_database=restored_seal, restored_readback=readback)
