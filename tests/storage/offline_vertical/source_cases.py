"""SOURCE ONLY: explicit future suite factory; no discovery or path allocation.

Root must admit a new disposable absolute parent before calling make_suite.
All directories/evidence are retained. This is local byte custody, not publication.
"""
import hashlib
from pathlib import Path
import unittest

from unified_system.journal import Journal
from unified_system.storage.contracts import StorageBlocked
from unified_system.storage.object_store import ObjectStore
from unified_system.storage.publication_records import RetainedPublicationIntent
from unified_system.storage.publication_recovery import PendingPublicationJournal
from unified_system.storage.result_publication import (
    build_local_closure, stage_local_closure, readback_local_closure,
    commit_result, reconcile_result)


def make_suite(disposable_parent, entries):
    """Consume A3 exact bytes, without decoding, normalizing or schema conversion."""
    parent = Path(disposable_parent)
    if not parent.is_absolute() or '..' in parent.parts or parent.exists():
        raise ValueError('new absolute disposable parent required')
    expected_roles = {'artifact', 'descriptor', 'request', 'input_rows',
                      'input_coverage', 'producer_metadata'}
    if type(entries) is not tuple or len(entries) != 6:
        raise ValueError('exact six A3 local entries required')
    for item in entries:
        if (type(item) is not tuple or len(item) != 3 or type(item[0]) is not str
                or type(item[1]) is not bytes or not item[1] or item[2] != ()):
            raise ValueError('exact local byte entries with empty dependencies required')
    roles = {role: raw for role, raw, _ in entries}
    if (set(roles) != expected_roles or len(roles) != len(entries)
            or sum(len(raw) for raw in roles.values()) > 65536
            or len({hashlib.sha256(raw).digest() for raw in roles.values()}) != 6):
        raise ValueError('local entry roles, bounds or uniqueness invalid')
    raw_fixture_bytes = roles['input_rows']
    # Allocation happens only in the explicitly invoked, later-authorized cases.
    expected_sha = hashlib.sha256(raw_fixture_bytes).hexdigest()

    class LocalStorageCases(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            parent.mkdir(exist_ok=False)

        def _root(self, name):
            path = parent / name
            path.mkdir(exist_ok=False)
            return path

        def test_raw_exact_bytes_idempotent_reopen(self):
            root = self._root('raw-reopen') / 'store'
            identity = '96dce424-a40b-4f25-8500-26738dd278e5'
            store = ObjectStore.create(root, store_id=identity)
            store.put(raw_fixture_bytes, max_bytes=65536)
            before = sorted(p.name for p in (root / 'objects').iterdir())
            store.put(raw_fixture_bytes, max_bytes=65536)
            self.assertEqual(before, sorted(p.name for p in (root / 'objects').iterdir()))
            reopened = ObjectStore.open(root, store_id=identity)
            self.assertEqual(reopened.read(expected_sha, max_bytes=65536), raw_fixture_bytes)
            self.assertEqual(reopened.verify(expected_sha, max_bytes=65536).byte_length,
                             len(raw_fixture_bytes))

        def test_foreign_store_identity_rejected(self):
            root = self._root('wrong-identity') / 'store'
            ObjectStore.create(root, store_id='96dce424-a40b-4f25-8500-26738dd278e5')
            with self.assertRaises(StorageBlocked):
                ObjectStore.open(root, store_id='39e675b0-27c9-446b-ae15-4f919dfdbec4')

        def test_exact_local_closure_reopen_has_no_publication(self):
            root = self._root('closure-reopen') / 'store'
            identity = '96dce424-a40b-4f25-8500-26738dd278e5'
            store = ObjectStore.create(root, store_id=identity)
            claim = build_local_closure(entries)
            stage_local_closure(store, claim, entries)
            reopened = ObjectStore.open(root, store_id=identity)
            for _, raw, _ in entries:
                self.assertEqual(reopened.read(hashlib.sha256(raw).hexdigest(), max_bytes=65536), raw)
            self.assertEqual(reopened.read(claim.sha256, max_bytes=32768), claim.canonical_bytes)
            observed = readback_local_closure(reopened, claim)
            self.assertEqual(observed.closure_sha256, claim.sha256)
            self.assertEqual(len(observed.objects), 7)
            self.assertFalse(claim.publication_confirmed)
            self.assertFalse(claim.semantic_closure_verified)
            self.assertFalse(observed.native_replica_eligible)
            self.assertFalse(observed.failure_domain_qualified)
            self.assertFalse(observed.semantic_closure_verified)
            self.assertFalse(observed.publication_confirmed)

        def test_native_result_paths_remain_unavailable(self):
            for operation in (commit_result, reconcile_result):
                with self.subTest(operation=operation.__name__):
                    with self.assertRaises(StorageBlocked):
                        operation(b'opaque-local-test-not-native-intent')

        def test_original_reopen_retains_unknown(self):
            root = self._root('journal-reopen')
            identity = '96dce424-a40b-4f25-8500-26738dd278e5'
            store = ObjectStore.create(root / 'store', store_id=identity)
            journal_path = root / 'local.sqlite'
            # initialize() can adopt a database: refuse any pre-existing path first.
            with journal_path.open('xb'):
                pass
            journal = Journal(journal_path)
            journal.initialize()
            pending = PendingPublicationJournal(journal, store)
            original = RetainedPublicationIntent(
                '32f2c66d-6f40-4b11-95ca-c56f7bea37c2',
                b'opaque-local-custody-test-only:' + expected_sha.encode('ascii'))
            pending.retain(original)
            pending.retain(original)
            self.assertEqual(len(journal.read()), 1)
            recovered = PendingPublicationJournal(
                Journal(journal_path), ObjectStore.open(root / 'store', store_id=identity))
            self.assertEqual(recovered.verify_staged_original(original.publication_id), original)
            observation = recovered.observation(original.publication_id)
            self.assertEqual(observation.native_outcome, 'UNKNOWN')
            self.assertFalse(observation.publication_confirmed)
            self.assertFalse(observation.retry_authorized)
            self.assertFalse(observation.hold_release_authorized)

    return unittest.defaultTestLoader.loadTestsFromTestCase(LocalStorageCases)
