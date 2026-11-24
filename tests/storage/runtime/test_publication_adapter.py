import unittest

from unified_system.storage.contracts import StorageBlocked
from unified_system.storage.publication import PublicationAdapter


class PublicationAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_native_backend_never_accepts_a_claim(self):
        adapter = PublicationAdapter()
        for claim in (b'{}', b'false', b'null', b'{"quorum":true}', b'{"state":"COMMITTED"}'):
            with self.subTest(claim=claim), self.assertRaisesRegex(StorageBlocked, "ACTUAL_PUBLICATION_BACKEND_UNAVAILABLE"):
                await adapter.commit_storage(claim)

    async def test_reconciliation_cannot_rekey_or_infer_absence(self):
        with self.assertRaisesRegex(StorageBlocked, "ACTUAL_PUBLICATION_BACKEND_UNAVAILABLE"):
            await PublicationAdapter().reconcile_storage(b'original immutable intent')

    async def test_no_caller_callback_or_boolean_can_admit_backend(self):
        for fake in (True, lambda: None, lambda: True):
            with self.subTest(fake=type(fake).__name__), self.assertRaises(TypeError):
                PublicationAdapter(fake)
