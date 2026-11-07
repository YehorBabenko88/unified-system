import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from unified_system.storage.contracts import StorageBlocked
from unified_system.storage.object_store import ObjectStore
from unified_system.storage.result_publication import (
    LocalByteClosure, build_local_closure, copy_local_closure, stage_local_closure,
    commit_result, reconcile_result,
)
from unified_system.storage.replica_evidence import LocalReplicaObservation, ReplicaClosureInventory


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode('ascii')


def fixture():
    raw = b'{"numeric":1.25,"unknown":null}'
    sha = hashlib.sha256(raw).hexdigest()
    entries = (('artifact', raw, ()), ('descriptor', b'{"kind":"synthetic"}', (sha,)),
               ('request', b'{"request":1}', ()))
    return entries, build_local_closure(entries)


class LocalClosureTests(unittest.TestCase):
    def stores(self, root):
        return (ObjectStore.create(root/'source', store_id='00000000-0000-4000-8000-000000000001'),
                ObjectStore.create(root/'copy', store_id='00000000-0000-4000-8000-000000000002'))

    def test_exact_numeric_payload_is_never_reencoded_and_claim_stays_untrusted(self):
        entries, claim = fixture()
        self.assertIsInstance(claim, LocalByteClosure)
        self.assertFalse(claim.publication_confirmed)
        self.assertFalse(claim.semantic_closure_verified)
        self.assertEqual(claim.value['objects'][0]['sha256'], hashlib.sha256(entries[0][1]).hexdigest())
        value = claim.value
        value['objects'].clear()
        self.assertEqual(len(claim.value['objects']), 3)

    def test_graph_missing_duplicate_unknown_cycle_and_role_requirements_reject(self):
        a, b = hashlib.sha256(b'a').hexdigest(), hashlib.sha256(b'b').hexdigest()
        entries, _ = fixture()
        invalid = [entries[:2], entries+(entries[0],),
                   (('artifact', b'a', (b,)), ('descriptor', b'b', (a,)), ('request', b'c', ())),
                   (('artifact', b'a', ('0'*64,)),)+entries[1:],
                   (('artifact\n', b'a', ()),)+entries[1:],
                   (('artifact', b'a', (a,)),)+entries[1:]]
        for item in invalid:
            with self.subTest(item=item), self.assertRaises(StorageBlocked):
                build_local_closure(item)

    def test_raw_types_empty_and_total_bounds_are_independent(self):
        entries, _ = fixture()
        for raw in (bytearray(b'a'), '', b'', b'a'*(1024*1024+1)):
            with self.subTest(raw_type=type(raw)), self.assertRaises(StorageBlocked):
                build_local_closure((('artifact', raw, ()),)+entries[1:])
        with self.assertRaises(StorageBlocked):
            build_local_closure((('artifact', b'a'*(1024*1024), ()),)+entries[1:])

    def test_strict_claim_rejects_unknown_noncanonical_duplicate_and_numeric_length(self):
        _, claim = fixture()
        for mutate in (lambda v: v.update(extra=True),
                       lambda v: v['objects'][0].update(bytes=10),
                       lambda v: v['objects'][0].update(bytes='9223372036854775808'),
                       lambda v: v['objects'][0].update(extra='field')):
            value=claim.value; mutate(value)
            with self.assertRaises(StorageBlocked): LocalByteClosure(canonical(value))
        for raw in (claim.canonical_bytes+b'\n', b'{"schema":"x","schema":"x"}', b'{'*20):
            with self.assertRaises(StorageBlocked): LocalByteClosure(raw)

    def test_actual_copy_reopen_readback_has_no_replica_or_domain_admission(self):
        entries, claim = fixture()
        with tempfile.TemporaryDirectory() as temp:
            source, destination = self.stores(Path(temp))
            stage_local_closure(source, claim, entries)
            observation = copy_local_closure(source, destination, claim)
            reopened = ObjectStore.open(destination._root, store_id=destination.store_id)
            for _, raw, _ in entries:
                self.assertEqual(ObjectStore.read(reopened, hashlib.sha256(raw).hexdigest()), raw)
            self.assertIsInstance(observation, LocalReplicaObservation)
            self.assertFalse(observation.replica_valid)
            self.assertFalse(observation.failure_domain_verified)
            self.assertFalse(observation.publication_confirmed)

    def test_wrong_payload_or_missing_source_is_rejected_before_copy(self):
        entries, claim = fixture()
        with tempfile.TemporaryDirectory() as temp:
            source, destination = self.stores(Path(temp))
            with self.assertRaises(StorageBlocked): stage_local_closure(source, claim, entries[1:])
            with patch.object(ObjectStore, 'put', side_effect=AssertionError('unexpected copy')):
                with self.assertRaises((StorageBlocked, OSError)): copy_local_closure(source, destination, claim)

    def test_same_instance_and_reopened_same_root_cannot_copy(self):
        entries, claim = fixture()
        with tempfile.TemporaryDirectory() as temp:
            source, _ = self.stores(Path(temp)); stage_local_closure(source, claim, entries)
            for dest in (source, ObjectStore.open(source._root, store_id=source.store_id)):
                with self.assertRaises(StorageBlocked): copy_local_closure(source, dest, claim)

    def test_corrupt_source_is_not_repaired_or_counted(self):
        entries, claim=fixture()
        with tempfile.TemporaryDirectory() as temp:
            source,destination=self.stores(Path(temp));stage_local_closure(source,claim,entries)
            sha=hashlib.sha256(entries[0][1]).hexdigest()
            object_path=source._root/'objects'/sha
            object_path.write_bytes(b'corrupt')
            with self.assertRaises((StorageBlocked,OSError)):copy_local_closure(source,destination,claim)

    def test_interrupted_copy_has_no_success_observation_and_keeps_prior_objects(self):
        entries,claim=fixture()
        with tempfile.TemporaryDirectory() as temp:
            source,destination=self.stores(Path(temp));stage_local_closure(source,claim,entries)
            original=ObjectStore.put; calls=[]
            def fail_second(store,raw,**kwargs):
                if store is destination:
                    calls.append(raw)
                    if len(calls)==2: raise OSError('simulated ENOSPC')
                return original(store,raw,**kwargs)
            with patch.object(ObjectStore,'put',fail_second):
                with self.assertRaises(OSError):copy_local_closure(source,destination,claim)
            self.assertEqual(ObjectStore.read(destination,hashlib.sha256(calls[0]).hexdigest()),calls[0])

    def test_local_observation_closed_schema_never_accepts_verified_flags(self):
        raw=canonical(dict(schema='unified.storage.local-copy-observation.v1',closure_sha256='a'*64,
            source_store_id='00000000-0000-4000-8000-000000000001',
            destination_store_id='00000000-0000-4000-8000-000000000002',object_count='4',byte_count='10'))
        obs=LocalReplicaObservation(raw)
        self.assertFalse(obs.replica_valid)
        for field in ('replica_valid','failure_domain_id','authority_verified'):
            value=json.loads(raw);value[field]=True
            with self.assertRaises(StorageBlocked):LocalReplicaObservation(canonical(value))

    def test_native_capture_commit_and_reconcile_remain_unconditionally_closed(self):
        class Poison:
            def __getattribute__(self,name):raise AssertionError('untrusted access')
        for value in (None,True,{},Poison(),lambda:True):
            with self.assertRaises(StorageBlocked):commit_result(value)
            with self.assertRaises(StorageBlocked):reconcile_result(value)
            with self.assertRaises(StorageBlocked):ReplicaClosureInventory().capture_result_closure(value,expected_authority=value)
