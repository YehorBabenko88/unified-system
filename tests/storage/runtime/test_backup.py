import hashlib
from pathlib import Path
import tempfile
import unittest

from unified_system.storage.backup import copy_inventory, verify_restore
from unified_system.storage.contracts import StorageBlocked
from unified_system.storage.object_store import ObjectStore


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="storage-backup-owned-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stores = [ObjectStore.create(self.root/str(i), store_id=f"00000000-0000-4000-8000-{i:012d}") for i in (1, 2, 3)]
        self.raw = b"owned fixture bytes\x00\xff"
        self.ref = self.stores[0].put(self.raw)
        self.inventory = ((self.ref.sha256, len(self.raw)),)

    def test_copy_alone_is_not_restore_success(self):
        result = copy_inventory(self.stores[0], self.stores[1], self.inventory)
        self.assertFalse(result.restore_test_passed)
        self.assertFalse(result.publication_confirmed)
        self.assertEqual(self.stores[1].read(self.ref.sha256), self.raw)

    def test_actual_three_root_roundtrip_and_inventory_binding(self):
        copied = copy_inventory(self.stores[0], self.stores[1], self.inventory)
        result = verify_restore(self.stores[1], self.stores[2], self.inventory)
        self.assertTrue(result.restore_test_passed)
        self.assertEqual(copied.inventory_sha256, result.inventory_sha256)
        self.assertEqual(result.object_count, 1)
        self.assertFalse(result.publication_confirmed)
        self.assertEqual(self.stores[2].read(self.ref.sha256), self.raw)

    def test_corrupted_backup_cannot_pass_restore(self):
        copy_inventory(self.stores[0], self.stores[1], self.inventory)
        (self.root/"2"/"objects"/self.ref.sha256).write_bytes(b"bad fixture")
        with self.assertRaises(StorageBlocked):
            verify_restore(self.stores[1], self.stores[2], self.inventory)

    def test_missing_or_wrong_length_inventory_fails(self):
        for inventory in [(("a"*64, 3),), ((self.ref.sha256, 1),)]:
            with self.subTest(inventory=inventory), self.assertRaises(StorageBlocked):
                copy_inventory(self.stores[0], self.stores[1], inventory)

    def test_same_store_alias_empty_duplicate_and_unbounded_inventory_rejected(self):
        with self.assertRaises(StorageBlocked):
            verify_restore(self.stores[0], self.stores[0], self.inventory)
        for inventory in [(), self.inventory*2, ((self.ref.sha256, True),), ((self.ref.sha256, 1 << 40),)]:
            with self.subTest(inventory=inventory), self.assertRaises(StorageBlocked):
                copy_inventory(self.stores[0], self.stores[1], inventory)
