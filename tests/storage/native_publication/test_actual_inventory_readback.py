"""Actual local readback evidence is not native replica/domain qualification."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from unified_system.storage.contracts import StorageBlocked
from unified_system.storage.object_store import ObjectStore
from unified_system.storage.replica_evidence import LocalInventoryReadback
from unified_system.storage.result_publication import (build_local_closure, stage_local_closure,
    copy_local_closure, readback_local_closure)


class ActualInventoryReadbackTests(unittest.TestCase):
    def fixture(self, root):
        source=ObjectStore.create(root/'a',store_id='00000000-0000-4000-8000-000000000001')
        destination=ObjectStore.create(root/'b',store_id='00000000-0000-4000-8000-000000000002')
        artifact=b'{"result":12.0}'
        entries=(('artifact',artifact,()),('descriptor',b'{"raw":"retained"}',(hashlib.sha256(artifact).hexdigest(),)),('request',b'{"input":1}',()))
        closure=build_local_closure(entries);stage_local_closure(source,closure,entries)
        return source,destination,closure,entries

    def test_actual_all_objects_and_metadata_root_readback_has_same_read_identities(self):
        with tempfile.TemporaryDirectory() as temp:
            source,_,closure,entries=self.fixture(Path(temp))
            fact=readback_local_closure(source,closure)
            self.assertIsInstance(fact,LocalInventoryReadback)
            self.assertEqual(fact.closure_sha256,closure.sha256)
            self.assertEqual(len(fact.objects),len(entries)+1)
            self.assertEqual({item.sha256 for item in fact.objects},
                             {hashlib.sha256(raw).hexdigest() for _,raw,_ in entries}|{closure.sha256})
            self.assertTrue(all(item.file_identity for item in fact.objects))
            self.assertFalse(fact.native_replica_eligible)
            self.assertFalse(fact.failure_domain_qualified)
            self.assertFalse(fact.semantic_closure_verified)
            self.assertFalse(fact.publication_confirmed)

    def test_two_actual_local_copies_never_become_two_qualified_domains(self):
        with tempfile.TemporaryDirectory() as temp:
            source,destination,closure,_=self.fixture(Path(temp))
            copy_local_closure(source,destination,closure)
            a,b=readback_local_closure(source,closure),readback_local_closure(destination,closure)
            self.assertNotEqual(a.store_id,b.store_id)
            self.assertEqual([o.sha256 for o in a.objects],[o.sha256 for o in b.objects])
            self.assertFalse(a.failure_domain_qualified or b.failure_domain_qualified)
            self.assertFalse(a.native_replica_eligible or b.native_replica_eligible)

    def test_destination_actual_corruption_and_root_corruption_refuse_observation(self):
        for kind in ('artifact','root'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as temp:
                source,destination,closure,entries=self.fixture(Path(temp));copy_local_closure(source,destination,closure)
                sha=closure.sha256 if kind=='root' else hashlib.sha256(entries[0][1]).hexdigest()
                path=destination._root/'objects'/sha;path.write_bytes(b'corrupt')
                with self.assertRaises(StorageBlocked):readback_local_closure(destination,closure)
                self.assertEqual(path.read_bytes(),b'corrupt')

    def test_no_public_constructor_copy_or_pickle_can_mint_native_proof(self):
        import copy,pickle
        with self.assertRaises(TypeError):LocalInventoryReadback()
        with tempfile.TemporaryDirectory() as temp:
            source,_,closure,_=self.fixture(Path(temp));fact=readback_local_closure(source,closure)
            for operation in (copy.copy,copy.deepcopy,pickle.dumps):
                with self.assertRaises(TypeError):operation(fact)
