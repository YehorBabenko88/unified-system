"""SOURCE ONLY. Separate explicit suite; no import-time allocation or runner.

Future Root allocation must provide an isolated new parent. Retain all artifacts.
Corruption is restricted to a file created by the same case, never supplied data.
"""
import hashlib
import os
from pathlib import Path
import stat
import unittest

from unified_system.journal import Journal
from unified_system.storage.contracts import StorageBlocked
from unified_system.storage.object_store import MAX_OBJECT_BYTES, ObjectStore
from unified_system.storage.publication_records import RetainedPublicationIntent
from unified_system.storage.publication_recovery import PendingPublicationJournal

STORE_ID = '96dce424-a40b-4f25-8500-26738dd278e5'
ORIGINAL_ID = '32f2c66d-6f40-4b11-95ca-c56f7bea37c2'


def make_suite(disposable_parent):
    parent = Path(disposable_parent)
    if not parent.is_absolute() or '..' in parent.parts or parent.exists():
        raise ValueError('new absolute disposable parent required')

    class NegativeStorageCases(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            parent.mkdir(exist_ok=False)

        def _case(self, name):
            root = parent / name
            root.mkdir(exist_ok=False)
            store = ObjectStore.create(root / 'store', store_id=STORE_ID)
            return root, store

        def _journal(self, root, store):
            path = root / 'local.sqlite'
            with path.open('xb'):
                pass
            journal = Journal(path)
            journal.initialize()
            return journal, PendingPublicationJournal(journal, store)

        def _blocked(self, code, operation, *args, **kwargs):
            with self.assertRaises(StorageBlocked) as caught:
                operation(*args, **kwargs)
            self.assertEqual(str(caught.exception), code)

        def test_invalid_object_limits_reject_before_write(self):
            root, store = self._case('invalid-limits')
            for limit in (-1, True, MAX_OBJECT_BYTES + 1):
                with self.subTest(limit=limit):
                    self._blocked('OBJECT_LIMIT_INVALID', store.put, b'x', max_bytes=limit)
            self.assertEqual(list((root / 'store' / 'objects').iterdir()), [])
            self.assertEqual(list((root / 'store' / 'staging').iterdir()), [])

        def test_payload_over_caller_limit_rejects_before_write(self):
            root, store = self._case('oversized-payload')
            self._blocked('OBJECT_SIZE_EXCEEDED', store.put, b'abcd', max_bytes=3)
            self.assertEqual(list((root / 'store' / 'objects').iterdir()), [])
            self.assertEqual(list((root / 'store' / 'staging').iterdir()), [])

        def test_read_and_verify_enforce_caller_limit(self):
            _, store = self._case('read-limit')
            raw = b'abcd'
            sha = hashlib.sha256(raw).hexdigest()
            store.put(raw, max_bytes=4)
            for operation in (store.read, store.verify):
                self._blocked('OBJECT_SIZE_EXCEEDED', operation, sha, max_bytes=3)
            self.assertEqual(store.read(sha, max_bytes=4), raw)

        def test_missing_object_rejects_without_creating_it(self):
            root, store = self._case('missing-object')
            sha = hashlib.sha256(b'not-written').hexdigest()
            for operation in (store.read, store.verify):
                self._blocked('OBJECT_UNAVAILABLE', operation, sha, max_bytes=64)
            self.assertEqual(list((root / 'store' / 'objects').iterdir()), [])

        def test_corrupt_case_owned_object_is_not_verified(self):
            root, store = self._case('corrupt-object')
            raw = b'case-owned-original'
            sha = hashlib.sha256(raw).hexdigest()
            verified = store.put(raw, max_bytes=64)
            path = root / 'store' / 'objects' / sha
            before = path.lstat()
            self.assertEqual((before.st_dev, before.st_ino), verified.file_identity)
            self.assertEqual(before.st_nlink, 1)
            self.assertTrue(stat.S_ISREG(before.st_mode))
            self.assertFalse(path.is_symlink())
            self.assertFalse(getattr(before, 'st_file_attributes', 0) & 1024)
            fd = os.open(path, os.O_WRONLY | getattr(os, 'O_BINARY', 0)
                         | getattr(os, 'O_NOFOLLOW', 0))
            try:
                opened = os.fstat(fd)
                self.assertEqual((opened.st_dev, opened.st_ino), verified.file_identity)
                self.assertEqual(opened.st_nlink, 1)
                self.assertEqual(os.write(fd, b'X'), 1)
                os.fsync(fd)
            finally:
                os.close(fd)
            for operation in (store.read, store.verify):
                self._blocked('OBJECT_CORRUPT', operation, sha, max_bytes=64)
            self.assertTrue(path.exists())  # Corrupt artifact is preserved.

        def test_conflicting_original_id_preserves_first_bytes(self):
            root, store = self._case('conflicting-original')
            journal, pending = self._journal(root, store)
            original = RetainedPublicationIntent(ORIGINAL_ID, b'first-local-original')
            pending.retain(original)
            conflict = RetainedPublicationIntent(ORIGINAL_ID, b'conflicting-local-original')
            self._blocked('PENDING_ORIGINAL_CONFLICT', pending.retain, conflict)
            self.assertEqual(len(journal.read()), 1)
            self.assertEqual(pending.verify_staged_original(ORIGINAL_ID), original)
            self.assertFalse((root / 'store' / 'objects' / conflict.sha256).exists())

        def test_attempt_uncertain_reopen_keeps_unknown_without_retry(self):
            root, store = self._case('uncertain-reopen')
            journal, pending = self._journal(root, store)
            original = RetainedPublicationIntent(ORIGINAL_ID, b'opaque-local-attempt-test')
            pending.retain(original)
            pending.mark_attempt_uncertain(ORIGINAL_ID)
            pending.mark_attempt_uncertain(ORIGINAL_ID)
            self.assertEqual(len(journal.read()), 2)
            reopened = PendingPublicationJournal(
                Journal(journal.path), ObjectStore.open(root / 'store', store_id=STORE_ID))
            self.assertEqual(reopened.verify_staged_original(ORIGINAL_ID), original)
            observation = reopened.observation(ORIGINAL_ID)
            self.assertEqual(observation.local_phase, 'ATTEMPT_UNCERTAIN')
            self.assertEqual(observation.native_outcome, 'UNKNOWN')
            self.assertFalse(observation.publication_confirmed)
            self.assertFalse(observation.retry_authorized)
            self.assertFalse(observation.hold_release_authorized)

        def test_journal_bytes_do_not_prove_staged_copy_in_another_store(self):
            root, store = self._case('missing-staged-copy')
            journal, pending = self._journal(root, store)
            original = RetainedPublicationIntent(ORIGINAL_ID, b'original-only-in-first-store')
            pending.retain(original)
            other = ObjectStore.create(root / 'other-store',
                store_id='39e675b0-27c9-446b-ae15-4f919dfdbec4')
            reopened = PendingPublicationJournal(Journal(journal.path), other)
            self.assertEqual(reopened.recover_original(ORIGINAL_ID), original)
            self._blocked('OBJECT_UNAVAILABLE', reopened.verify_staged_original, ORIGINAL_ID)
            self.assertEqual(reopened.observation(ORIGINAL_ID).native_outcome, 'UNKNOWN')

    return unittest.defaultTestLoader.loadTestsFromTestCase(NegativeStorageCases)
