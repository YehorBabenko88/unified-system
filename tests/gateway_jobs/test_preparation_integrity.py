"""Local SQLite integrity regression; no authority/native/physical fixture."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from scheduler_components.durable import PreparationJournal
from scheduler_components.placement import Candidate, Policy, Resources


class PreparationIntegrity(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='a5-local-integrity-')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'preparation.sqlite'
        self.store = PreparationJournal(self.path)
        self.addCleanup(lambda: self.store.close())
        self.scope = dict(cluster_id='cluster', cluster_generation='generation',
                          job_id='pending', dataset_id='dataset',
                          source_id='source', partition_id='partition')
        self.request = Resources(60, 60, 60, 60, 60)
        self.node = Candidate('node', 'incarnation', 'incarnation', 100, 'bench',
                              Resources(100, 100, 100, 100, 100), Resources(0, 0, 0, 0, 0))
        self.policy = Policy(10, 800000, 1, 1)
        self.store.enqueue(self.scope, self.request, 'bench')
        self.store.prepare(self.scope, [self.node], 100, self.policy,
                           quorum_available=True, schedule_active=True)
        self.store.record_handoff(self.scope)
        self.store.record_unknown(self.scope)

    def rewrite(self, column, value):
        # Fixed test-owned DB/column, never caller SQL or another owner's file.
        assert column in ('spec', 'request_id')
        with closing(sqlite3.connect(self.path)) as db:
            db.execute('UPDATE jobs SET ' + column + '=? WHERE state=?', (value, 'UNKNOWN'))
            db.commit()

    def zero_unknown_spec(self):
        spec = self.store.view(self.scope)['spec']
        spec['resources'] = dict.fromkeys(spec['resources'], 0)
        self.rewrite('spec', json.dumps(spec, sort_keys=True, separators=(',', ':')))

    def test_reopen_rejects_corrupt_unknown_resources_without_repair(self):
        self.zero_unknown_spec()
        self.store.close()
        with self.assertRaisesRegex(ValueError, 'invalid persisted preparation'):
            reopened = PreparationJournal(self.path)
            reopened.close()
        with closing(sqlite3.connect(self.path)) as db:
            state, spec = db.execute('SELECT state,spec FROM jobs').fetchone()
        self.assertEqual(state, 'UNKNOWN')
        self.assertTrue(all(v == 0 for v in json.loads(spec)['resources'].values()))

    def test_live_corrupt_unknown_cannot_create_competing_preparation(self):
        self.zero_unknown_spec()
        second = dict(self.scope, job_id='competing')
        self.store.enqueue(second, self.request, 'bench')
        with self.assertRaisesRegex(ValueError, 'invalid persisted preparation'):
            self.store.prepare(second, [self.node], 100, self.policy,
                               quorum_available=True, schedule_active=True)
        self.assertEqual(self.store.view(second)['state'], 'QUEUED')

    def test_unknown_missing_hold_identity_is_not_a_valid_recovered_view(self):
        self.rewrite('request_id', None)
        with self.assertRaisesRegex(ValueError, 'invalid persisted preparation'):
            self.store.view(self.scope)

    def test_valid_unknown_roundtrip_preserves_exact_hold_and_events(self):
        before = self.store.view(self.scope)
        events = self.store.events()
        self.store.close()
        self.store = PreparationJournal(self.path)
        self.assertEqual(self.store.view(self.scope), before)
        self.assertEqual(self.store.events(), events)
        self.assertIs(before['execution_authorized'], False)

    def test_malformed_persisted_spec_variants_cannot_be_recovered_as_valid(self):
        original = self.store.view(self.scope)['spec']
        variants = []
        for change in ({'ram': True}, {'cpu': -1}, {'scratch': 9223372036854775808}):
            spec = dict(original, resources=dict(original['resources'], **change))
            variants.append(json.dumps(spec, sort_keys=True, separators=(',', ':')))
        variants.append(json.dumps(dict(original, data=['duplicate', 'duplicate']),
                                   sort_keys=True, separators=(',', ':')))
        variants.append(json.dumps(dict(original, extra='not-in-local-codec'),
                                   sort_keys=True, separators=(',', ':')))
        for raw in variants:
            with self.subTest(spec=raw):
                self.rewrite('spec', raw)
                with self.assertRaisesRegex(ValueError, 'invalid persisted preparation'):
                    self.store.view(self.scope)

    def test_failed_reopen_closes_its_owned_connection(self):
        self.zero_unknown_spec()
        connection = sqlite3.connect(self.path, isolation_level=None)
        with patch('scheduler_components.durable.sqlite3.connect', return_value=connection):
            with self.assertRaisesRegex(ValueError, 'invalid persisted preparation'):
                PreparationJournal(self.path)
        with self.assertRaises(sqlite3.ProgrammingError):
            connection.execute('SELECT 1')
