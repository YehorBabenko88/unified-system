import copy
from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from unified_system.node_task_journal import NodeTaskJournal, NodeOperation, NodeJournalError


def operation(**changes):
    data = dict(schema='unified.node-operation.v1', task_id='task1', cluster_id='cluster1', node_id='node1', node_incarnation='inc1', release_id='release1', artifact_sha256='a'*64, operation_type='REPORT_STATUS', approval_reference='approval1', authority_generation=1, lease_fencing_proof={'reference':'unverified'}, preconditions=[], expected_postconditions=[], timeout_seconds=5, rollback_policy='NONE', idempotency_key='key1', result_receipt=None)
    data.update(changes)
    return data


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/'operations.db'
        self.journal = NodeTaskJournal(self.path)

    def test_closed_schema_and_strict_types(self):
        for changes in ({'extra':1}, {'timeout_seconds':True}, {'operation_type':'SHELL'}, {'artifact_sha256':'x'}, {'preconditions':['secret']}, {'lease_fencing_proof':True}):
            with self.subTest(changes=changes), self.assertRaises(NodeJournalError):
                NodeOperation.parse(operation(**changes))

    def test_duplicate_retains_original_and_collision_refused(self):
        original=operation()
        first=self.journal.create(original)
        original['release_id']='mutated'
        self.assertEqual(self.journal.create(operation()),first)
        with self.assertRaises(NodeJournalError): self.journal.create(operation(release_id='different'))
        with self.assertRaises(NodeJournalError): self.journal.create(operation(task_id='other'))
        self.assertEqual(self.journal.get('task1')['intent']['release_id'],'release1')

    def test_invalid_transition_and_receipt_mutation(self):
        self.journal.create(operation())
        with self.assertRaises(NodeJournalError): self.journal.transition('task1','COMPLETED')
        self.journal.transition('task1','VERIFIED')
        receipt={'code':'CHECKED'}
        self.journal.transition('task1','BLOCKED',receipt)
        receipt['code']='modified'
        self.assertEqual(self.journal.get('task1')['receipt']['code'],'CHECKED')

    def test_restart_before_during_after(self):
        self.journal.create(operation())
        self.assertEqual(self.journal.reconcile()[0]['state'],'INTERRUPTED')
        self.journal.create(operation(task_id='task2',idempotency_key='key2'))
        for state in ('VERIFIED','AUTHORIZED','PREPARED','RUNNING'):
            self.journal.transition('task2',state)
        restarted=NodeTaskJournal(self.path)
        self.assertEqual(restarted.reconcile()[-1]['state'],'UNKNOWN_OUTCOME')
        self.assertEqual(restarted.reconcile()[-1]['state'],'UNKNOWN_OUTCOME')
        with self.assertRaises(NodeJournalError): restarted.transition('task2','RUNNING')

    def test_corrupt_chain_fails_closed(self):
        self.journal.create(operation())
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("UPDATE transitions SET digest='bad'"); db.commit()
        with self.assertRaises(NodeJournalError): self.journal.get('task1')

    def test_capacity_preserves_existing_receipts(self):
        small=NodeTaskJournal(self.path,max_records=1)
        small.create(operation())
        with self.assertRaises(NodeJournalError): small.transition('task1','VERIFIED')
        self.assertEqual(small.get('task1')['state'],'CREATED')

    def test_full_database_does_not_advance(self):
        self.journal.create(operation())
        with patch('unified_system.journal.sqlite3.connect',side_effect=sqlite3.OperationalError('database or disk is full')):
            with self.assertRaises(NodeJournalError): self.journal.transition('task1','VERIFIED')
        self.assertEqual(self.journal.get('task1')['state'],'CREATED')

    def test_legacy_receipt_cannot_be_adopted(self):
        from unified_system.journal import Journal
        legacy=Journal(self.path);legacy.initialize();legacy.append('OBSERVING',{'task_id':'task1'})
        with self.assertRaises(NodeJournalError): self.journal.get('task1')

    def test_foreign_database_untouched(self):
        with closing(sqlite3.connect(self.path)) as db:
            db.execute('CREATE TABLE foreign_data (value TEXT)'); db.commit()
        before=self.path.read_bytes()
        with self.assertRaises(NodeJournalError): self.journal.create(operation())
        self.assertEqual(before,self.path.read_bytes())

    def test_overlength_and_byte_capacity(self):
        for changes in ({'task_id':'x'*97},{'lease_fencing_proof':{'reference':'x'*97}},{'preconditions':[{'check':[], 'expected':'PASS'}]}):
            with self.assertRaises(NodeJournalError): self.journal.create(operation(**changes))
        small=NodeTaskJournal(self.path,max_bytes=4096)
        with self.assertRaises(NodeJournalError): small.create(operation())
        self.assertFalse(self.path.exists())

    def test_duplicate_after_restart_and_closed_receipts(self):
        first=self.journal.create(operation())
        restarted=NodeTaskJournal(self.path)
        self.assertEqual(first,restarted.create(operation()))
        for receipt in ({'effects_authorized':True},{'authority':'PASS'},{'command':'bad'},{'code':'x'*65}):
            with self.assertRaises(NodeJournalError): restarted.transition('task1','VERIFIED',receipt)
        self.assertEqual(restarted.get('task1')['state'],'CREATED')
