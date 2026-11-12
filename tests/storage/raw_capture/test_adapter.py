"""Bounded offline TDD; explicit retained scratch, no provider/event loop sockets."""
import dataclasses
import hashlib
import importlib
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from unified_system.journal import Journal
from unified_system.storage.contracts import StorageBlocked
from unified_system.storage.object_store import ObjectStore


def call(coroutine):
    # The approved adapter does direct local IO and must never suspend/queue.
    try:
        coroutine.send(None)
    except StopIteration as done:
        return done.value
    finally:
        coroutine.close()
    raise AssertionError('adapter unexpectedly suspended')


class RawCaptureTests(unittest.TestCase):
    def setUp(self):
        try:
            self.api = importlib.import_module('unified_system.storage.raw_capture')
        except ModuleNotFoundError:
            self.fail('approved raw_capture adapter is not implemented')
        self.root = Path(os.environ['A4_RAW_TEST_SCRATCH']) / self._testMethodName
        self.root.mkdir(exist_ok=False)
        self.store = ObjectStore.create(self.root / 'archive',
            store_id='96dce424-a40b-4f25-8500-26738dd278e5')
        self.journal = Journal(self.root / 'capture.sqlite')
        with self.journal.path.open('xb'):
            pass
        self.journal.initialize()
        self.profile = self.api.RawCaptureProfile(sqlite_headroom_bytes=262144,
                                                inventory_file_limit=128)
        self.adapter = self.api.RawCaptureAdapter(self.store, self.journal, self.profile)

    def put(self, obs=b'observation', raw=b'raw'):
        return call(self.adapter.store_capture(observation_bytes=obs, payload_bytes=raw))

    def test_bytes_roundtrip_reopen_false_authority(self):
        result = self.put()
        reopened = self.api.RawCaptureAdapter(
            ObjectStore.open(self.root / 'archive', store_id=self.store.store_id),
            Journal(self.journal.path), self.profile)
        read = call(reopened.read_capture(result.observation_sha256))
        self.assertEqual(read, result)
        self.assertEqual(read.observation_bytes, b'observation')
        self.assertEqual(read.payload_bytes, b'raw')
        verified_body = self.journal.read()[0]
        self.assertNotIn('digest', verified_body)
        self.assertEqual(read.journal_record_digest, hashlib.sha256(json.dumps(
            verified_body, sort_keys=True, separators=(',', ':')).encode('ascii')).hexdigest())
        for name in ('publication_confirmed', 'native_authority_verified', 'replica_eligible'):
            self.assertFalse(getattr(read, name))
        self.assertEqual(read.durability, 'UNKNOWN')

    def test_empty_frame_is_distinct_from_absent_payload(self):
        empty = self.put(b'empty-frame', b'')
        absent = self.put(b'control', None)
        self.assertEqual(empty.payload_sha256, hashlib.sha256(b'').hexdigest())
        self.assertIsNone(absent.payload_sha256)
        self.assertEqual(empty.payload_byte_count, absent.payload_byte_count)
        self.assertEqual(empty.payload_bytes, b'')
        self.assertIsNone(absent.payload_bytes)

    def test_idempotence_and_different_occurrence(self):
        first = self.put()
        self.assertEqual(first, self.put())
        self.put(b'another-observation', b'raw')
        self.assertEqual(len(self.journal.read()), 2)
        with self.assertRaisesRegex(StorageBlocked, 'RAW_CAPTURE_BINDING_CONFLICT'):
            self.put(b'observation', b'changed')
        self.assertEqual(len(self.journal.read()), 2)

    def test_input_limits_reject_before_mutation(self):
        for obs, raw in ((b'', b'x'), (b'x'*16385, None), (b'x', b'x'*1048577),
                         ('not-bytes', None), (b'x', bytearray(b'x'))):
            with self.subTest(obs_type=type(obs).__name__, raw_type=type(raw).__name__):
                with self.assertRaisesRegex(StorageBlocked, 'RAW_CAPTURE_INPUT_INVALID'):
                    self.put(obs, raw)
        self.assertEqual(self.journal.read(), [])
        self.assertEqual(list((self.root/'archive'/'objects').iterdir()), [])

    def test_headroom_and_inventory_required(self):
        for profile in (self.api.RawCaptureProfile(),
                        self.api.RawCaptureProfile(sqlite_headroom_bytes=True, inventory_file_limit=128)):
            adapter = self.api.RawCaptureAdapter(self.store, self.journal, profile)
            with self.assertRaisesRegex(StorageBlocked, 'RAW_CAPTURE_PROFILE_REQUIRED'):
                call(adapter.store_capture(observation_bytes=b'x', payload_bytes=None))

    def test_count_persists_across_adapter_reopen(self):
        for i in range(16):
            self.put(str(i).encode(), None)
        adapter = self.api.RawCaptureAdapter(self.store, Journal(self.journal.path), self.profile)
        with self.assertRaisesRegex(StorageBlocked, 'RAW_CAPTURE_CAPACITY_EXCEEDED'):
            call(adapter.store_capture(observation_bytes=b'17', payload_bytes=None))
        self.assertEqual(len(self.journal.read()), 16)

    def test_occurrence_budget_charges_deduplicated_payload(self):
        raw = b'x'*1048576
        for i in range(4):
            self.put(str(i).encode(), raw)
        with self.assertRaisesRegex(StorageBlocked, 'RAW_CAPTURE_CAPACITY_EXCEEDED'):
            self.put(b'fifth', raw)
        self.assertEqual(len(self.journal.read()), 4)

    def test_orphan_denies_write_but_not_linked_read(self):
        first = self.put()
        self.store.put(b'orphan', max_bytes=64)
        with self.assertRaisesRegex(StorageBlocked, 'RAW_CAPTURE_LINK_UNAVAILABLE'):
            self.put(b'next', b'raw')
        self.assertEqual(call(self.adapter.read_capture(first.observation_sha256)), first)

    def test_unknown_append_retained_and_read_reconciled(self):
        append = Journal.append
        def response_lost(journal, *args, **kwargs):
            append(journal, *args, **kwargs)
            raise OSError('simulated response loss, no physical fault')
        with patch.object(Journal, 'append', response_lost):
            with self.assertRaisesRegex(StorageBlocked, 'RAW_CAPTURE_WRITE_OUTCOME_UNKNOWN'):
                self.put()
        result = call(self.adapter.read_capture(hashlib.sha256(b'observation').hexdigest()))
        self.assertEqual(result.payload_bytes, b'raw')
        with self.assertRaisesRegex(StorageBlocked, 'RAW_CAPTURE_WRITE_OUTCOME_UNKNOWN'):
            self.put(b'next', None)

    def test_busy_does_not_queue(self):
        self.adapter._busy.acquire()
        try:
            with self.assertRaisesRegex(StorageBlocked, 'RAW_CAPTURE_BUSY'):
                self.put()
        finally:
            self.adapter._busy.release()
        self.assertEqual(self.journal.read(), [])

    def test_logical_state_and_inventory_limits(self):
        for profile in (dataclasses.replace(self.profile, max_state_bytes=1),
                        dataclasses.replace(self.profile, inventory_file_limit=1)):
            adapter = self.api.RawCaptureAdapter(self.store, self.journal, profile)
            with self.assertRaises(StorageBlocked):
                call(adapter.store_capture(observation_bytes=b'x', payload_bytes=None))
        self.assertEqual(self.journal.read(), [])

    def test_namespace_scan_stops_at_admitted_inventory_bound(self):
        profile = dataclasses.replace(self.profile, inventory_file_limit=8)
        adapter = self.api.RawCaptureAdapter(self.store, self.journal, profile)
        original = Path.iterdir
        yielded = []
        def oversized_namespace(path):
            if path != self.root:
                yield from original(path)
                return
            yield from original(path)
            for _ in range(1000):
                yielded.append(1)
                yield self.root / 'unaccounted'
        with patch.object(Path, 'iterdir', oversized_namespace):
            with self.assertRaises(StorageBlocked):
                call(adapter.store_capture(observation_bytes=b'x', payload_bytes=None))
        self.assertLessEqual(len(yielded), 12)

    def test_prospective_object_count_refuses_before_mutation(self):
        adapter = self.api.RawCaptureAdapter(self.store, self.journal,
            dataclasses.replace(self.profile, inventory_file_limit=2))
        with self.assertRaisesRegex(StorageBlocked, 'RAW_CAPTURE_CAPACITY_EXCEEDED'):
            call(adapter.store_capture(observation_bytes=b'x', payload_bytes=b''))
        self.assertEqual(self.journal.read(), [])
        self.assertEqual(list((self.root/'archive'/'objects').iterdir()), [])
        self.assertEqual(list((self.root/'archive'/'staging').iterdir()), [])

    def test_same_payload_observation_hash_uses_one_object_slot(self):
        adapter = self.api.RawCaptureAdapter(self.store, self.journal,
            dataclasses.replace(self.profile, inventory_file_limit=4))
        result = call(adapter.store_capture(observation_bytes=b'same', payload_bytes=b'same'))
        self.assertEqual(result.observation_sha256, result.payload_sha256)
        self.assertEqual(len(list((self.root/'archive'/'objects').iterdir())), 1)

    def test_link_codec_lexical_and_null_pair_rules(self):
        value = dict(schema='unified.storage.local-raw-capture-link.v1',
                     classification='LOCAL_UNATTESTED', observation_sha256='a'*64,
                     observation_byte_count=1, payload_sha256=None, payload_byte_count=0)
        canonical = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
        self.assertEqual(self.api.decode_local_link(canonical), value)
        bad = [canonical+b'\n', canonical.replace(b'"observation_byte_count":1',
                b'"observation_byte_count":true'), canonical.replace(b'"observation_byte_count":1',
                b'"observation_byte_count":1.0'), canonical.replace(b'"payload_byte_count":0',
                b'"payload_byte_count":-0'), canonical.replace(b'"payload_byte_count":0',
                b'"payload_byte_count":1'), canonical.replace(b'"payload_byte_count":0',
                b'"payload_byte_count":0,"payload_byte_count":0')]
        for raw in bad:
            with self.subTest(raw=raw):
                with self.assertRaises(StorageBlocked): self.api.decode_local_link(raw)


if __name__ == '__main__':
    unittest.main(verbosity=2)
