"""Prospective tests only: no entry point, imports/backup execution not admitted.

Root separately binds exact SAME6 bytes, phase source and exclusive scratch.
Synthetic test barrier references do not prove process retirement/admission.
"""
import hashlib
from pathlib import Path
import time
import unittest
from unittest.mock import patch


def make_suite(new_parent, entries, admitted_phases):
    parent = Path(new_parent)
    if not parent.is_absolute() or '..' in parent.parts or parent.exists():
        raise ValueError('new absolute private test parent required')

    class SnapshotSourceCases(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            parent.mkdir(exist_ok=False)

        def setUp(self):
            self.root = parent / self._testMethodName
            self.root.mkdir(exist_ok=False)
            self.source = self.root / 'source'
            self.original = admitted_phases.seed(self.source, entries)
            self.closure = self.original['closure_bytes'].encode('ascii')
            db = self.source / 'local.sqlite'
            info = db.stat()
            self.kwargs = dict(expected_source_store_id=admitted_phases.STORE_ID,
                expected_backup_store_id=admitted_phases.BACKUP_ID,
                expected_restored_store_id=admitted_phases.RESTORE_ID,
                source_database_sha256=hashlib.sha256(db.read_bytes()).hexdigest(),
                source_database_byte_count=info.st_size,
                source_database_file_identity=(info.st_dev, info.st_ino),
                stopped_writer_barrier_sha256=hashlib.sha256(
                    b'SYNTHETIC_UNIT_REFERENCE_NOT_ROOT_RETIREMENT_PROOF').hexdigest(),
                max_backup_pages=16, deadline_monotonic_ns=time.monotonic_ns()+30_000_000_000)

        def snapshot(self):
            return admitted_phases.snapshot_restore(self.source, self.closure,
                self.root/'backup', self.root/'restored', **self.kwargs)

        def assert_no_destination(self):
            self.assertFalse((self.root/'backup').exists())
            self.assertFalse((self.root/'restored').exists())

        def test_sqlite_and_closure_restore_preserve_logical_records(self):
            result = self.snapshot()
            self.assertEqual(result['scope'], 'LOCAL_SOFTWARE_IMMUTABLE_AND_SQLITE_SNAPSHOT')
            self.assertTrue(result['journal_restored'])
            self.assertEqual(result['journal_row_count'], 2)
            self.assertEqual(result['restored_object_count'], 7)
            self.assertTrue(result['logical_records_equal'])
            self.assertEqual(result['restored_readback'], self.original)
            self.assertFalse(result['physical_backup_verified'])
            self.assertFalse(result['process_restart_verified'])
            self.assertFalse(result['committed'])
            self.assertEqual(result['native_outcome'], 'UNKNOWN')
            self.assertEqual(result['source_database']['sha256'], self.kwargs['source_database_sha256'])

        def test_default_inspect_remains_unchanged(self):
            self.assertEqual(admitted_phases.inspect(self.source, self.closure), self.original)
            self.assert_no_destination()

        def test_wrong_source_database_seal_rejects_before_destinations(self):
            self.kwargs['source_database_sha256'] = '0'*64
            with self.assertRaises(ValueError):
                self.snapshot()
            self.assert_no_destination()

        def test_missing_barrier_reference_rejects_before_destinations(self):
            self.kwargs['stopped_writer_barrier_sha256'] = None
            with self.assertRaises(ValueError):
                self.snapshot()
            self.assert_no_destination()

        def test_expired_deadline_rejects_before_destinations(self):
            self.kwargs['deadline_monotonic_ns'] = 1
            with self.assertRaises(ValueError):
                self.snapshot()
            self.assert_no_destination()

        def test_boolean_page_bound_is_rejected(self):
            self.kwargs['max_backup_pages'] = True
            with self.assertRaises(ValueError):
                self.snapshot()
            self.assert_no_destination()

        def test_deadline_beyond_local_profile_is_rejected(self):
            self.kwargs['deadline_monotonic_ns'] = time.monotonic_ns()+60_000_000_000
            with self.assertRaises(ValueError):
                self.snapshot()
            self.assert_no_destination()

        def test_owned_sidecar_fixture_denies_snapshot(self):
            # A new own empty fixture, not a live SQLite corruption experiment.
            (self.source/'local.sqlite-wal').write_bytes(b'')
            with self.assertRaises(ValueError):
                self.snapshot()
            self.assert_no_destination()

        def test_orphan_object_is_not_adopted(self):
            from unified_system.storage.object_store import ObjectStore
            store = ObjectStore.open(self.source/'archive', store_id=admitted_phases.STORE_ID)
            store.put(b'own-orphan-test-data', max_bytes=64)
            with self.assertRaises(ValueError):
                self.snapshot()
            self.assert_no_destination()

        def test_existing_destination_is_preserved(self):
            restored = self.root/'restored'
            restored.mkdir(exist_ok=False)
            sentinel = restored/'sentinel'
            sentinel.write_bytes(b'own-existing-target-must-not-be-adopted')
            with self.assertRaises(ValueError):
                self.snapshot()
            self.assertEqual(sentinel.read_bytes(), b'own-existing-target-must-not-be-adopted')
            self.assertFalse((self.root/'backup').exists())

        def _mock_backup_abort(self, status):
            destination = self.root / ('mock-partial-%s.sqlite' % status)
            closed = []
            clock = [self.kwargs['deadline_monotonic_ns']-1]
            source_bytes = self.kwargs['source_database_byte_count']
            class Cursor:
                def __init__(self, value): self.value = value
                def fetchone(self): return (self.value,)
            class Connection:
                def execute(self, sql):
                    if sql == 'PRAGMA page_count': return Cursor(1)
                    if sql == 'PRAGMA page_size': return Cursor(source_bytes)
                def backup(self, _destination, *, pages, progress, sleep):
                    if status == 'expired':
                        # Synthetic partial bytes in an exclusive NEW fixture;
                        # no native SQLite backup/corruption/kill occurs here.
                        destination.write_bytes(b'partial-own-mock-fixture')
                        clock[0] = self_deadline+1
                        progress(0, 0, 1)
                    else:
                        progress(status, 1, 1)
                def close(self): closed.append(self)
            self_deadline = self.kwargs['deadline_monotonic_ns']
            seal = dict(sha256=self.kwargs['source_database_sha256'],
                        bytes=source_bytes, file_identity=self.kwargs['source_database_file_identity'])
            with patch.object(admitted_phases.sqlite3, 'connect', lambda *_a, **_k: Connection()), \
                 patch.object(admitted_phases.time, 'monotonic_ns', lambda: clock[0]):
                with self.assertRaises(ValueError):
                    admitted_phases._snapshot_copy_db(self.source/'local.sqlite', destination,
                        seal, 128, self_deadline)
            self.assertEqual(len(closed), 2)
            self.assertTrue(destination.exists())
            self.assertEqual(hashlib.sha256((self.source/'local.sqlite').read_bytes()).hexdigest(),
                             self.kwargs['source_database_sha256'])
            return destination

        def test_busy_and_locked_backup_callbacks_abort_without_retry(self):
            for status in (5, 6):
                with self.subTest(status=status):
                    destination = self._mock_backup_abort(status)
                    self.assertEqual(destination.stat().st_size, 0)

        def test_mid_backup_deadline_retains_mock_partial_destination(self):
            destination = self._mock_backup_abort('expired')
            self.assertEqual(destination.read_bytes(), b'partial-own-mock-fixture')

    return unittest.defaultTestLoader.loadTestsFromTestCase(SnapshotSourceCases)
