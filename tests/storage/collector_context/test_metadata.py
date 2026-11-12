"""Inert connection unit tests, NOT PostgreSQL behavior or admission evidence."""
import copy
import dataclasses
import hashlib
import importlib
import unittest

from unified_system.storage.raw_capture import LocalRawCaptureReadback
from unified_system.storage.collector_context import LocalCollectorCheckpoint


def complete(coro):
    try:
        try: coro.send(None)
        except StopIteration as done: return done.value
        raise AssertionError('unexpected unit coroutine suspension')
    finally: coro.close()


class InertConnection:
    """Scripted rows/recorded calls; no driver, sockets, SQL engine or auth."""
    def __init__(self):
        self.instrument = None
        self.context = None
        self.observations = {}
        self.checkpoint = None
        self.holds = []
        self.calls, self.transactions, self.outcomes = [], [], []
        self.fail_checkpoint = False
        self.extra_context = False

    def transaction(self, **options):
        outer = self
        class Transaction:
            async def __aenter__(self):
                outer.transactions.append(options)
                self.before = copy.deepcopy((outer.instrument, outer.context,
                    outer.observations, outer.checkpoint))
            async def __aexit__(self, kind, value, traceback):
                outer.outcomes.append('rollback_requested' if kind else 'commit_requested')
                if kind:
                    outer.instrument, outer.context, outer.observations, outer.checkpoint = self.before
        return Transaction()

    async def execute(self, sql, *args):
        self.calls.append((sql, args))
        if '/* instrument_insert */' in sql:
            if self.instrument is None:
                self.instrument = dict(zip(('instrument_id','identity_kind','identity_contract_sha256'), args))
        elif '/* context_insert */' in sql:
            if self.context is None:
                self.context = dict(zip(('context_id','instrument_id','binding_sha256','store_id','lifecycle_state'), args))
                self.context['custody'] = 'LOCAL_UNATTESTED'
        elif '/* observation_insert */' in sql:
            keys = ('context_id','observation_sha256','raw_journal_digest','payload_sha256',
                    'payload_byte_count','observation_kind')
            row = dict(zip(keys, args)); row['continuity'] = 'UNKNOWN'
            self.observations.setdefault(row['observation_sha256'], row)
        elif '/* checkpoint_upsert */' in sql:
            if self.fail_checkpoint: raise OSError('inert checkpoint fault')
            self.checkpoint = dict(zip(('context_id','observation_sha256','raw_journal_digest',
                                       'local_lifecycle_sequence'), args))
            self.checkpoint.update(native_outcome='UNKNOWN', publication_confirmed=False)
        elif '/* context_update */' in sql:
            self.context['lifecycle_state'] = args[2]
        else: raise AssertionError('unexpected mutation SQL')

    async def fetch(self, sql, *args):
        self.calls.append((sql, args))
        if '/* instrument_read */' in sql:
            return [copy.deepcopy(self.instrument)] if self.instrument else []
        if '/* context_read */' in sql:
            if not self.context: return []
            row = dict(self.context, **{k:v for k,v in self.instrument.items() if k != 'instrument_id'})
            return [row, row] if self.extra_context else [row]
        if '/* observations_read */' in sql: return copy.deepcopy(list(self.observations.values()))
        if '/* checkpoint_read */' in sql: return [copy.deepcopy(self.checkpoint)] if self.checkpoint else []
        if '/* holds_read */' in sql: return copy.deepcopy(self.holds)
        raise AssertionError('unexpected read SQL')


def facts(obs=b'first', raw=b'raw', digest='d'*64):
    sha = lambda value: hashlib.sha256(value).hexdigest()
    return LocalRawCaptureReadback(obs, raw, sha(obs), len(obs),
        None if raw is None else sha(raw), 0 if raw is None else len(raw), digest)


class MetadataTests(unittest.TestCase):
    def setUp(self):
        try: self.api = importlib.import_module('unified_system.storage.collector_metadata')
        except ModuleNotFoundError: self.fail('collector metadata adapter is missing')
        self.conn = InertConnection()
        self.adapter = self.api.CollectorMetadataAdapter(self.conn)
        self.binding = self.api.CollectorMetadataBinding('1'*32, 'a'*64,
            '96dce424-a40b-4f25-8500-26738dd278e5', 'synthetic-btcusdt-v1', 'SYNTHETIC', None)
        self.first = facts()
        self.cp = LocalCollectorCheckpoint('1'*32, self.first.observation_sha256, 'd'*64, 3)

    def project(self, history=None, checkpoint=None, **kwargs):
        history = (self.first,) if history is None else history
        values = dict(binding=self.binding, history=history,
            checkpoint=self.cp if checkpoint is None else checkpoint,
            lifecycle_state='STOPPED', observation_kinds={str(x.observation_sha256):'SYNTHETIC' for x in history})
        values.update(kwargs)
        return complete(self.adapter.project(**values))

    def test_projection_parameters_and_false_authority(self):
        result = self.project()
        self.assertEqual(result.binding, self.binding)
        self.assertEqual(result.checkpoint, self.cp)
        self.assertEqual(len(result.observations), 1)
        self.assertFalse(result.publication_confirmed)
        self.assertEqual(result.quality, 'UNKNOWN')
        self.assertEqual(result.coverage, 'UNKNOWN')
        self.assertEqual(self.conn.transactions, [dict(isolation='serializable')])
        for sql, args in self.conn.calls:
            self.assertNotIn(self.binding.context_id, sql)
            self.assertNotIn(self.binding.instrument_id, sql)
            self.assertNotIn(self.first.observation_bytes, args)

    def test_exact_replay_and_old_checkpoint_do_not_rewind(self):
        self.project()
        second = facts(b'second', b'b', 'e'*64)
        newer = LocalCollectorCheckpoint('1'*32, second.observation_sha256, 'e'*64, 5)
        self.project((self.first, second), newer)
        replay = self.project((self.first, second), self.cp)
        self.assertEqual(replay.checkpoint, newer)

    def test_conflicting_observation_rejected_and_rollback_requested(self):
        self.project()
        altered = dataclasses.replace(self.first, journal_record_digest='e'*64)
        cp = dataclasses.replace(self.cp, raw_journal_digest='e'*64)
        with self.assertRaises(self.api.MetadataBlocked): self.project((altered,), cp)
        self.assertEqual(self.conn.outcomes[-1], 'rollback_requested')
        self.assertEqual(self.conn.observations[self.first.observation_sha256]['raw_journal_digest'], 'd'*64)

    def test_existing_history_cannot_be_omitted(self):
        self.project()
        other = facts(b'second', b'b', 'e'*64)
        cp = LocalCollectorCheckpoint('1'*32, other.observation_sha256, 'e'*64, 5)
        with self.assertRaises(self.api.MetadataBlocked): self.project((other,), cp)

    def test_wrong_binding_or_instrument_rejected(self):
        self.project()
        for changed in (dataclasses.replace(self.binding, binding_sha256='b'*64),
                        dataclasses.replace(self.binding, identity_kind='UNKNOWN')):
            with self.assertRaises(self.api.MetadataBlocked): self.project(binding=changed)

    def test_public_readback_readonly_repeatable_transaction(self):
        expected = self.project()
        actual = complete(self.adapter.readback(binding=self.binding))
        self.assertEqual(actual, expected)
        self.assertEqual(self.conn.transactions[-1], dict(isolation='repeatable_read', readonly=True))

    def test_missing_or_duplicate_context_denied(self):
        with self.assertRaises(self.api.MetadataBlocked): complete(self.adapter.readback(binding=self.binding))
        self.project(); self.conn.extra_context = True
        with self.assertRaises(self.api.MetadataBlocked): complete(self.adapter.readback(binding=self.binding))

    def test_observation_and_hold_overflow_denied(self):
        self.project()
        saved = copy.deepcopy(self.conn.observations)
        row = next(iter(saved.values()))
        self.conn.observations = {str(i):dict(row, observation_sha256=f'{i:064x}') for i in range(17)}
        with self.assertRaises(self.api.MetadataBlocked): complete(self.adapter.readback(binding=self.binding))
        self.conn.observations = saved
        self.conn.holds = [dict(hold_id=str(i), reason='research') for i in range(129)]
        with self.assertRaises(self.api.MetadataBlocked): complete(self.adapter.readback(binding=self.binding))

    def test_bad_checkpoint_and_publication_claim_denied(self):
        self.project()
        self.conn.checkpoint['raw_journal_digest'] = 'e'*64
        with self.assertRaises(self.api.MetadataBlocked): complete(self.adapter.readback(binding=self.binding))
        self.conn.checkpoint['raw_journal_digest'] = 'd'*64
        self.conn.checkpoint['publication_confirmed'] = True
        with self.assertRaises(self.api.MetadataBlocked): complete(self.adapter.readback(binding=self.binding))

    def test_failure_propagates_and_requests_transaction_rollback(self):
        self.conn.fail_checkpoint = True
        with self.assertRaises(OSError): self.project()
        self.assertEqual(self.conn.outcomes, ['rollback_requested'])
        self.assertIsNone(self.conn.context)

    def test_hash_lengths_and_exact_types_before_any_db_effect(self):
        class Sneaky(str):
            def __hash__(self): raise AssertionError('must not hash subclass')
            def __eq__(self, other): raise AssertionError('must not compare subclass')
        for bad in (dataclasses.replace(self.first, observation_sha256='b'*64),
                    dataclasses.replace(self.first, payload_byte_count=True),
                    dataclasses.replace(self.first, observation_sha256=Sneaky('c'*64))):
            with self.assertRaises(self.api.MetadataBlocked): self.project((bad,))
        # Build without hashing hostile keys in test construction itself.
        with self.assertRaises(self.api.MetadataBlocked): self.project(lifecycle_state=Sneaky('STOPPED'))
        self.assertEqual(self.conn.calls, [])

    def test_gap_is_explicit_label_and_quality_remains_unknown(self):
        gap = facts(b'{"reason":"source_gap"}', None)
        cp = LocalCollectorCheckpoint('1'*32, gap.observation_sha256, 'd'*64, 3)
        result = self.project((gap,), cp, observation_kinds={gap.observation_sha256:'GAP'})
        self.assertEqual(result.observations[0].observation_kind, 'GAP')
        self.assertEqual(result.coverage, 'UNKNOWN')

    def test_same_checkpoint_sequence_cannot_change_pointer(self):
        self.project()
        other = facts(b'second', b'b', 'e'*64)
        cp = LocalCollectorCheckpoint('1'*32, other.observation_sha256, 'e'*64, 3)
        with self.assertRaises(self.api.MetadataBlocked): self.project((self.first, other), cp)

    def test_unknown_lifecycle_cannot_be_reset_by_projection(self):
        self.project(lifecycle_state='UNKNOWN')
        with self.assertRaises(self.api.MetadataBlocked): self.project(lifecycle_state='ACTIVE')

    def test_snapshot_bounds_and_inexact_binding_denied_before_db(self):
        for binding in (dataclasses.replace(self.binding, context_id=True),
                        dataclasses.replace(self.binding, identity_contract_sha256='invalid')):
            with self.assertRaises(self.api.MetadataBlocked): self.project(binding=binding)
        history = tuple(facts(str(i).encode()) for i in range(17))
        with self.assertRaises(self.api.MetadataBlocked): self.project(history)
        class Derived(LocalRawCaptureReadback): pass
        with self.assertRaises(self.api.MetadataBlocked): self.project((Derived(**dataclasses.asdict(self.first)),))
        self.assertEqual(self.conn.calls, [])

    def test_hostile_driver_keys_and_scalars_rejected_before_comparison(self):
        self.project()
        class Hostile(str):
            def __hash__(self): raise AssertionError('unsafe hash')
            def __eq__(self, other): raise AssertionError('unsafe comparison')
        self.conn.context['binding_sha256'] = Hostile('a'*64)
        with self.assertRaises(self.api.MetadataBlocked): complete(self.adapter.readback(binding=self.binding))

        self.conn.context['binding_sha256'] = 'a'*64
        class HostileRow:
            def keys(self): return [Hostile('context_id')]
            def __getitem__(self, key): raise AssertionError('unsafe key access')
        original = self.conn.fetch
        async def fetch(sql, *args):
            if '/* context_read */' in sql: return [HostileRow()]
            return await original(sql, *args)
        self.conn.fetch = fetch
        with self.assertRaises(self.api.MetadataBlocked): complete(self.adapter.readback(binding=self.binding))

    def test_uuid_projection_uses_text_without_driver_specific_objects(self):
        self.project()
        queries = [sql for sql, _ in self.conn.calls if '/* context_read */' in sql]
        self.assertTrue(queries)
        self.assertTrue(all('c.store_id::text AS store_id' in sql for sql in queries))

    def test_payload_occurrence_budget_counts_deduplicated_bytes(self):
        history = tuple(facts(str(i).encode(), b'x'*1048576) for i in range(5))
        with self.assertRaises(self.api.MetadataBlocked): self.project(history)
        self.assertEqual(self.conn.calls, [])


if __name__ == '__main__': unittest.main(verbosity=2)
