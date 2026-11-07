import errno
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from unified_system.storage.contracts import StorageBlocked
from unified_system.storage.object_store import ObjectStore


STORE_ID = "00000000-0000-4000-8000-000000000041"
RAW = b"immutable owned object\x00\xff\n"


class ObjectStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="storage-runtime-owned-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/"objects"
        self.store = ObjectStore.create(self.root, store_id=STORE_ID)

    def test_actual_bytes_are_content_addressed_and_survive_reopen(self):
        result = self.store.put(RAW)
        self.assertEqual(result.sha256, hashlib.sha256(RAW).hexdigest())
        self.assertEqual(result.byte_length, len(RAW))
        self.assertFalse(result.publication_confirmed)
        reopened = ObjectStore.open(self.root, store_id=STORE_ID)
        self.assertEqual(reopened.read(result.sha256), RAW)
        self.assertEqual(reopened.verify(result.sha256).sha256, result.sha256)

    def test_duplicate_and_concurrent_publication_do_not_replace_bytes(self):
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(self.store.put, [RAW]*12))
        self.assertEqual({result.sha256 for result in results}, {hashlib.sha256(RAW).hexdigest()})
        self.assertEqual(len(list((self.root/"objects").iterdir())), 1)
        self.assertEqual(self.store.read(results[0].sha256), RAW)

    def test_corruption_is_not_repaired_by_duplicate_put(self):
        result = self.store.put(RAW)
        path = self.root/"objects"/result.sha256
        path.write_bytes(b"corrupted fixture")
        with self.assertRaises(StorageBlocked):
            self.store.verify(result.sha256)
        with self.assertRaises(StorageBlocked):
            self.store.put(RAW)
        self.assertEqual(path.read_bytes(), b"corrupted fixture")

    def test_missing_object_is_explicit_not_empty_data(self):
        with self.assertRaisesRegex(StorageBlocked, "OBJECT_UNAVAILABLE"):
            self.store.read("a"*64)

    def test_verification_identity_comes_from_same_verified_read(self):
        result = self.store.put(RAW)
        path = self.root/"objects"/result.sha256
        from unified_system.storage import object_store
        original_read = object_store._read
        def replace_after_read(*args, **kwargs):
            raw = original_read(*args, **kwargs)
            if args[0] == path:
                path.unlink()
                path.write_bytes(b"corrupt replacement fixture")
            return raw
        with patch("unified_system.storage.object_store._read", side_effect=replace_after_read):
            observed = self.store.verify(result.sha256)
        self.assertEqual(observed.file_identity, result.file_identity)

    def test_failed_fsync_never_returns_an_object_receipt(self):
        with patch("unified_system.storage.object_store.os.fsync", side_effect=OSError(errno.ENOSPC, "fixture flush full")):
            with self.assertRaises(StorageBlocked):
                self.store.put(RAW)
        self.assertFalse((self.root/"objects"/hashlib.sha256(RAW).hexdigest()).exists())

    def test_short_writes_are_completed_and_zero_write_fails(self):
        original_write = os.write
        def short_write(fd, data):
            return original_write(fd, data[:max(1, len(data)//2)])
        with patch("unified_system.storage.object_store.os.write", side_effect=short_write):
            result = self.store.put(RAW)
        self.assertEqual(self.store.read(result.sha256), RAW)
        with patch("unified_system.storage.object_store.os.write", return_value=0):
            with self.assertRaises(StorageBlocked):
                self.store.put(b"new fixture")

    def test_interrupted_link_leaves_only_invisible_staging(self):
        with patch("unified_system.storage.object_store.os.link", side_effect=OSError(errno.EIO, "fixture interrupted")):
            with self.assertRaises(StorageBlocked):
                self.store.put(RAW)
        self.assertFalse((self.root/"objects"/hashlib.sha256(RAW).hexdigest()).exists())
        self.assertTrue(list((self.root/"staging").iterdir()))

    def test_existing_directory_is_not_implicitly_adopted(self):
        existing = Path(self.temp.name)/"foreign"
        existing.mkdir()
        (existing/"user.txt").write_bytes(b"preserve")
        with self.assertRaises(StorageBlocked):
            ObjectStore.create(existing, store_id=STORE_ID)
        with self.assertRaises(StorageBlocked):
            ObjectStore.open(existing, store_id=STORE_ID)
        self.assertEqual((existing/"user.txt").read_bytes(), b"preserve")

    def test_wrong_store_identity_and_changed_root_are_rejected(self):
        with self.assertRaises(StorageBlocked):
            ObjectStore.open(self.root, store_id="00000000-0000-4000-8000-000000000099")
        original = self.root.with_name("original-owned")
        self.root.rename(original)
        self.root.mkdir()
        with self.assertRaises(StorageBlocked):
            self.store.put(RAW)

    def test_hardlinked_object_and_request_paths_are_rejected(self):
        result = self.store.put(RAW)
        os.link(self.root/"objects"/result.sha256, Path(self.temp.name)/"alias")
        with self.assertRaises(StorageBlocked):
            self.store.read(result.sha256)
        for value in ("../escape", "A"*64, "a"*63, Path("a"*64)):
            with self.subTest(value=value), self.assertRaises(StorageBlocked):
                self.store.read(value)

    def test_local_size_limit_never_bypasses_full_object_verification(self):
        with self.assertRaises(StorageBlocked):
            self.store.put(RAW, max_bytes=len(RAW)-1)
        result = self.store.put(RAW)
        with self.assertRaises(StorageBlocked):
            self.store.read(result.sha256, max_bytes=len(RAW)-1)
