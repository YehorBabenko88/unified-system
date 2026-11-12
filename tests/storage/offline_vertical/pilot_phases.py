"""Root-invoked DATA_ONLY phases; not a launcher, daemon or authority API.

SOURCE ONLY until Root admits exact imports/runtime/effects. No main/discovery.
Root pins six producer entries once and retains closure bytes outside the child.
"""
import hashlib
import json
from pathlib import Path
import sqlite3

from unified_system.journal import Journal
from unified_system.storage.object_store import ObjectStore
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


def inspect(owned_root, expected_closure_bytes):
    """M1: bounded read-only reopen. Root must prove prior child retirement."""
    root = _path(owned_root)
    claim = _claim(expected_closure_bytes)
    store = ObjectStore.open(root / 'archive', store_id=STORE_ID)
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
