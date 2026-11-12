"""SOURCE ONLY: local byte-copy restore tests, explicit future allocation only.

Not physical backup qualification, native replica eligibility or dataset commit.
"""
import gzip
import hashlib
import os
from pathlib import Path
import unittest

from unified_system.storage.contracts import StorageBlocked
from unified_system.storage.object_store import ObjectStore
from unified_system.storage.result_publication import (
    build_local_closure, stage_local_closure, copy_local_closure,
    readback_local_closure)


def make_suite(disposable_parent, entries):
    parent = Path(disposable_parent)
    if not parent.is_absolute() or '..' in parent.parts or parent.exists():
        raise ValueError('new absolute disposable parent required')
    if type(entries) is not tuple:
        raise ValueError('exact reviewed tuple entries required')
    claim = build_local_closure(entries)  # Pure validation before any allocation.
    roles = {role: raw for role, raw, _ in entries}
    if 'input_rows' not in roles or sum(map(len, roles.values())) > 65536:
        raise ValueError('bounded synthetic raw fixture required')

    class LocalRestoreCases(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            parent.mkdir(exist_ok=False)

        def _stores(self, name):
            root = parent / name
            root.mkdir(exist_ok=False)
            source = ObjectStore.create(root / 'source',
                store_id='96dce424-a40b-4f25-8500-26738dd278e5')
            backup = ObjectStore.create(root / 'backup',
                store_id='39e675b0-27c9-446b-ae15-4f919dfdbec4')
            restore = ObjectStore.create(root / 'restore',
                store_id='489e5730-862a-4c15-94be-7aa6100b7153')
            stage_local_closure(source, claim, entries)
            return root, source, backup, restore

        def test_copy_restore_exact_closure_and_compressed_raw(self):
            root, source, backup, restore = self._stores('copy-restore')
            first = copy_local_closure(source, backup, claim)
            second = copy_local_closure(backup, restore, claim)
            for observation in (first, second):
                self.assertFalse(observation.replica_valid)
                self.assertFalse(observation.failure_domain_verified)
                self.assertFalse(observation.publication_confirmed)
            reopened = ObjectStore.open(root / 'restore', store_id=restore.store_id)
            for _, raw, _ in entries:
                self.assertEqual(reopened.read(hashlib.sha256(raw).hexdigest(), max_bytes=65536), raw)
            inventory = readback_local_closure(reopened, claim)
            self.assertEqual(inventory.closure_sha256, claim.sha256)
            self.assertFalse(inventory.publication_confirmed)
            # Test data encoding only; no new archive/store format or migration.
            packed = gzip.compress(roles['input_rows'], mtime=0)
            packed_sha = hashlib.sha256(packed).hexdigest()
            source.put(packed, max_bytes=131072)
            backup.put(source.read(packed_sha, max_bytes=131072), max_bytes=131072)
            restore.put(backup.read(packed_sha, max_bytes=131072), max_bytes=131072)
            restored = reopened.read(packed_sha, max_bytes=131072)
            self.assertEqual(restored, packed)
            self.assertEqual(gzip.decompress(restored), roles['input_rows'])

        def test_corrupt_backup_aborts_before_destination_objects(self):
            root, source, backup, restore = self._stores('corrupt-backup')
            copy_local_closure(source, backup, claim)
            raw = roles['input_rows']
            sha = hashlib.sha256(raw).hexdigest()
            observation = backup.verify(sha, max_bytes=65536)
            path = root / 'backup' / 'objects' / sha
            # _check + verify already perform type/reparse/single-link checks.
            fd = os.open(path, os.O_WRONLY | getattr(os, 'O_BINARY', 0)
                         | getattr(os, 'O_NOFOLLOW', 0))
            try:
                opened = os.fstat(fd)
                self.assertEqual((opened.st_dev, opened.st_ino), observation.file_identity)
                self.assertEqual(opened.st_nlink, 1)
                self.assertEqual(os.write(fd, bytes([raw[0] ^ 1])), 1)
                os.fsync(fd)
            finally:
                os.close(fd)
            with self.assertRaises(StorageBlocked) as caught:
                copy_local_closure(backup, restore, claim)
            self.assertEqual(str(caught.exception), 'OBJECT_CORRUPT')
            self.assertEqual(list((root / 'restore' / 'objects').iterdir()), [])
            self.assertEqual(list((root / 'restore' / 'staging').iterdir()), [])
            self.assertEqual(source.read(sha, max_bytes=65536), raw)
            self.assertTrue(path.exists())

    return unittest.defaultTestLoader.loadTestsFromTestCase(LocalRestoreCases)
