"""Actual private SQLite/object read-only tests, no service/PG/TLS/authority."""
import dataclasses
import hashlib
import os
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from unified_system.journal import Journal
from unified_system.contracts import ContractError
from unified_system.storage import collector_context as api
from unified_system.storage.contracts import StorageBlocked
from unified_system.storage.object_store import ObjectStore
from unified_system.storage.raw_capture import RawCaptureProfile


def complete(coro):
    try:
        try: coro.send(None)
        except StopIteration as done: return done.value
        raise AssertionError('unexpected suspension')
    finally: coro.close()


def source_map(root):
    return tuple((str(path.relative_to(root)), path.stat().st_dev, path.stat().st_ino,
                  path.stat().st_size, path.stat().st_mtime_ns,
                  hashlib.sha256(path.read_bytes()).hexdigest())
                 for path in sorted(root.rglob('*')) if path.is_file())


class InspectionTests(unittest.TestCase):
    def setUp(self):
        self.parent = Path(os.environ['A4_INSPECTION_TEST_SCRATCH'])/self._testMethodName
        self.parent.mkdir(exist_ok=False)
        self.root = self.parent/'context'
        self.profile = api.CollectorContextProfile(RawCaptureProfile(
            sqlite_headroom_bytes=262144, inventory_file_limit=128), lifecycle_headroom_bytes=65536)
        self.kw = dict(context_id='1'*32, store_id='96dce424-a40b-4f25-8500-26738dd278e5',
                       binding_sha256='a'*64, profile=self.profile)
        self.ctx = api.CollectorContext.create(self.root, **self.kw)
        self.facts = complete(self.ctx.store_capture(observation_bytes=b'opaque observation',payload_bytes=b'raw'))
        self.cp = complete(self.ctx.checkpoint())
        complete(self.ctx.stop()); self.ctx.close()
        self.assertTrue(hasattr(api.CollectorContext, 'inspect'), 'read-only inspection API is missing')

    def tearDown(self):
        self.ctx.close()

    def inspect(self, **kwargs):
        self.assertTrue(hasattr(api.CollectorContext, 'inspect'), 'read-only inspection API is missing')
        return api.CollectorContext.inspect(self.root, **dict(self.kw, **kwargs))

    def test_clean_stopped_independent_checkpoint_and_history(self):
        result = self.inspect()
        self.assertEqual(result.state, 'STOPPED')
        self.assertEqual(result.writer_flag, 'S')
        self.assertEqual(result.checkpoint, self.cp)
        self.assertEqual(result.history, (self.facts,))
        self.assertEqual(result.context_id, self.kw['context_id'])
        self.assertEqual(result.binding_sha256, self.kw['binding_sha256'])
        self.assertEqual(result.classification, 'LOCAL_UNATTESTED')
        self.assertEqual(result.native_outcome, 'UNKNOWN')
        self.assertFalse(result.publication_confirmed)
        self.assertFalse(result.quiescence_verified)
        with self.assertRaises(dataclasses.FrozenInstanceError): result.state = 'ACTIVE'

    def test_no_bytes_names_identities_or_writer_operations_change(self):
        before = source_map(self.root)
        forbidden = AssertionError('mutating/writer operation called')
        with patch.object(api.CollectorContext, '__init__', side_effect=forbidden), \
             patch.object(api.CollectorContext, '_kernel', side_effect=forbidden), \
             patch.object(Journal, 'append', side_effect=forbidden), \
             patch.object(Journal, 'initialize', side_effect=forbidden), \
             patch.object(ObjectStore, 'create', side_effect=forbidden), \
             patch.object(ObjectStore, 'put', side_effect=forbidden), \
             patch.object(api.uuid, 'uuid4', side_effect=forbidden):
            self.inspect(); self.inspect()
        self.assertEqual(source_map(self.root), before)

    def test_sqlite_connections_are_true_readonly_not_immutable_shortcuts(self):
        original = sqlite3.connect
        calls = []
        def checked(database, *args, **kwargs):
            self.assertIs(type(database), str)
            self.assertIn('mode=ro', database)
            self.assertNotIn('immutable=', database)
            self.assertIs(kwargs.get('uri'), True)
            calls.append(database)
            return original(database, *args, **kwargs)
        with patch.object(sqlite3, 'connect', checked): self.inspect()
        self.assertTrue(calls)

    def test_actual_select_limits_and_readonly_descriptor_flags(self):
        connect, opening = sqlite3.connect, os.open
        selects = []
        def traced(*args, **kwargs):
            connection = connect(*args, **kwargs)
            connection.set_trace_callback(lambda sql: selects.append(sql))
            return connection
        def readonly(path, flags, *args, **kwargs):
            self.assertFalse(flags & (os.O_RDWR | os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
            return opening(path, flags, *args, **kwargs)
        with patch.object(sqlite3,'connect',traced), patch.object(os,'open',readonly):
            self.inspect()
        self.assertEqual(len(selects), 2)
        self.assertTrue(any(sql.endswith('LIMIT 129') for sql in selects))
        self.assertTrue(any(sql.endswith('LIMIT 17') for sql in selects))

    def test_dirty_context_retains_unknown_without_mutation(self):
        self.ctx = api.CollectorContext.open(self.root, **self.kw)
        self.ctx.close()
        before = source_map(self.root)
        result = self.inspect()
        self.assertEqual(result.state, 'UNKNOWN')
        self.assertEqual(result.checkpoint, self.cp)
        self.assertEqual(result.history, (self.facts,))
        self.assertEqual(source_map(self.root), before)

    def test_terminal_context_stays_terminal(self):
        self.ctx = api.CollectorContext.open(self.root, **self.kw)
        complete(self.ctx.mark_terminal('synthetic_failure')); self.ctx.close()
        before = source_map(self.root)
        self.assertEqual(self.inspect().state, 'TERMINAL')
        self.assertEqual(source_map(self.root), before)

    def test_linked_corruption_rejects_without_repair(self):
        path = self.root/'raw/archive/objects'/self.facts.payload_sha256
        path.write_bytes(b'bad')
        before = source_map(self.root)
        with self.assertRaises(StorageBlocked): self.inspect()
        self.assertEqual(source_map(self.root), before)

    def test_unlinked_partial_retained_and_reported_unknown(self):
        store = ObjectStore.open(self.root/'raw/archive', store_id=self.kw['store_id'])
        orphan = store.put(b'own incomplete orphan')
        path = self.root/'raw/archive/objects'/orphan.sha256
        path.write_bytes(b'partial')
        before = source_map(self.root)
        result = self.inspect()
        self.assertEqual(result.state, 'UNKNOWN')
        self.assertEqual(result.history, (self.facts,))
        self.assertEqual(result.checkpoint, self.cp)
        self.assertIn('raw/archive/objects/'+orphan.sha256, result.orphan_paths)
        self.assertEqual(source_map(self.root), before)

    def test_wrong_binding_profile_and_context_rejected(self):
        for changed in (dict(binding_sha256='b'*64),dict(context_id='2'*32),
                        dict(profile=dataclasses.replace(self.profile,max_lifecycle_records=64))):
            with self.assertRaises((api.CollectorBlocked, StorageBlocked)): self.inspect(**changed)

    def test_missing_root_cannot_create_anything(self):
        self.assertTrue(hasattr(api.CollectorContext, 'inspect'), 'read-only inspection API is missing')
        absent = self.parent/'absent'
        with self.assertRaises(Exception): api.CollectorContext.inspect(absent, **self.kw)
        self.assertFalse(absent.exists())

    def test_sidecar_and_wal_header_reject_before_sqlite_open(self):
        sidecar = self.root/'lifecycle.sqlite-wal'
        sidecar.write_bytes(b'own sidecar fixture')
        with patch.object(sqlite3, 'connect', side_effect=AssertionError('must not connect')) as blocked:
            with self.assertRaises((api.CollectorBlocked, StorageBlocked)): self.inspect()
            blocked.assert_not_called()

    def test_wal_header_rejects_before_sqlite_open(self):
        # Retained synthetic header; no WAL connection or cleanup is performed.
        path = self.root/'raw/capture.sqlite'
        value = bytearray(path.read_bytes()); value[18:20] = b'\x02\x02'; path.write_bytes(value)
        with patch.object(sqlite3, 'connect', side_effect=AssertionError('must not connect')) as blocked:
            with self.assertRaises((api.CollectorBlocked, StorageBlocked)): self.inspect()
            blocked.assert_not_called()

    def test_source_change_during_inspection_rejected(self):
        original = api._read
        changed = False
        def racing(path, limit):
            nonlocal changed
            result = original(path, limit)
            if path == self.root/'writer.lock' and not changed:
                changed = True
                path.write_bytes(b'U')
            return result
        with patch.object(api, '_read', racing):
            with self.assertRaises(api.CollectorBlocked): self.inspect()
        self.assertTrue(changed)

    def test_journal_record_bounds_are_enforced(self):
        for _ in range(16):
            Journal(self.root/'raw/capture.sqlite').append('OBSERVING', {'own':'overflow_fixture'})
        before = source_map(self.root)
        with self.assertRaises(ContractError): self.inspect()
        self.assertEqual(source_map(self.root), before)

    def test_empty_stopped_context_has_no_fabricated_checkpoint(self):
        root = self.parent/'empty'
        self.ctx = api.CollectorContext.create(root, **self.kw)
        complete(self.ctx.stop()); self.ctx.close()
        result = api.CollectorContext.inspect(root, **self.kw)
        self.assertEqual(result.state, 'STOPPED')
        self.assertIsNone(result.checkpoint)
        self.assertEqual(result.history, ())

    def test_inspection_does_not_change_clean_resume_semantics(self):
        self.inspect()
        self.ctx = api.CollectorContext.open(self.root, **self.kw)
        self.ctx.require_ready()
        self.assertEqual(complete(self.ctx.checkpoint()), self.cp)
        complete(self.ctx.stop()); self.ctx.close()

    def test_unexpected_source_file_denied_before_connect(self):
        (self.root/'own-unaccounted-file').write_bytes(b'retain')
        with patch.object(sqlite3,'connect',side_effect=AssertionError('unexpected connect')) as blocked:
            with self.assertRaises(api.CollectorBlocked): self.inspect()
            blocked.assert_not_called()

    def test_cumulative_logical_read_budget_exceeded_before_connect(self):
        root = self.parent/'small-budget'
        profile = dataclasses.replace(self.profile, max_context_bytes=524288)
        kw = dict(self.kw, profile=profile)
        self.ctx = api.CollectorContext.create(root, **kw)
        complete(self.ctx.stop()); self.ctx.close()
        (root/'raw/archive/staging/own-retained-partial').write_bytes(b'x'*524288)
        before = source_map(root)
        with patch.object(sqlite3,'connect',side_effect=AssertionError('unexpected connect')) as blocked:
            with self.assertRaises(api.CollectorBlocked): api.CollectorContext.inspect(root, **kw)
            blocked.assert_not_called()
        self.assertEqual(source_map(root), before)


class JournalBoundTests(unittest.TestCase):
    def test_actual_bound_default_chain_and_overflow(self):
        path = Path(os.environ['A4_INSPECTION_TEST_SCRATCH'])/'journal-bound.sqlite'
        with path.open('xb'): pass
        journal = Journal(path); journal.initialize()
        journal.append('OBSERVING', {'own':1}); journal.append('OBSERVING', {'own':2})
        before = path.read_bytes()
        self.assertEqual(journal.read(max_records=2), journal.read())
        with self.assertRaises(ContractError): journal.read(max_records=1)
        self.assertEqual(path.read_bytes(), before)

    def test_invalid_builtin_limits_reject_before_connect(self):
        journal = Journal(Path(os.environ['A4_INSPECTION_TEST_SCRATCH'])/'not-created.sqlite')
        with patch.object(sqlite3,'connect',side_effect=AssertionError('unexpected connect')) as blocked:
            for value in (True,0,100001,1.0,'16',None):
                with self.assertRaises(ContractError): journal.read(max_records=value)
            blocked.assert_not_called()


if __name__ == '__main__': unittest.main(verbosity=2)
