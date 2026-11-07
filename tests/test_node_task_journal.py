import copy
from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from unified_system.node_task_journal import NodeTaskJournal, NodeOperation, NodeJournalError


def operation(**changes):
    data = dict(schema='unified.node-operation.v2', task_id='task1', cluster_id='cluster1', node_id='node1', node_incarnation='inc1', release_id='release1', artifact_sha256='a'*64, operation_type='REPORT_STATUS', approval_reference='approval1', authority_generation='12345678-1234-4234-8234-123456789abc', lease_fencing_proof={'reference':'unverified'}, preconditions=[], expected_postconditions=[], timeout_seconds=5, rollback_policy='NONE', idempotency_key='key1', result_receipt=None)
    data.update(changes)
    return data


def scoped_journal(path,**kwargs):
    config=dict(cluster_id='cluster1',node_id='node1',node_incarnation='inc1')
    config.update(kwargs)
    return NodeTaskJournal(path,**config)


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/'operations.db'
        self.journal = scoped_journal(self.path)

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
        restarted=scoped_journal(self.path)
        self.assertEqual(restarted.reconcile()[-1]['state'],'UNKNOWN_OUTCOME')
        self.assertEqual(restarted.reconcile()[-1]['state'],'UNKNOWN_OUTCOME')
        with self.assertRaises(NodeJournalError): restarted.transition('task2','RUNNING')

    def test_corrupt_chain_fails_closed(self):
        self.journal.create(operation())
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("UPDATE transitions SET digest='bad'"); db.commit()
        with self.assertRaises(NodeJournalError): self.journal.get('task1')

    def test_capacity_preserves_existing_receipts(self):
        small=scoped_journal(self.path,max_records=1)
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
        small=scoped_journal(self.path,max_bytes=4096)
        with self.assertRaises(NodeJournalError): small.create(operation())
        self.assertFalse(self.path.exists())

    def test_duplicate_after_restart_and_closed_receipts(self):
        first=self.journal.create(operation())
        restarted=scoped_journal(self.path)
        self.assertEqual(first,restarted.create(operation()))
        for receipt in ({'effects_authorized':True},{'authority':'PASS'},{'command':'bad'},{'code':'x'*65}):
            with self.assertRaises(NodeJournalError): restarted.transition('task1','VERIFIED',receipt)
        self.assertEqual(restarted.get('task1')['state'],'CREATED')

    def test_atomic_reservation_refuses_racing_file(self):
        original=self.journal._append
        def raced(record,count):
            with closing(sqlite3.connect(self.path)) as db:
                db.execute('CREATE TABLE foreign_data (value TEXT)');db.commit()
            before=self.path.read_bytes()
            try: return original(record,count)
            finally: self.assertEqual(self.path.read_bytes(),before)
        with patch.object(self.journal,'_append',side_effect=raced):
            with self.assertRaises(NodeJournalError): self.journal.create(operation())

    def test_replaced_inode_and_hardlink_refused(self):
        import os
        self.journal.create(operation())
        moved=self.path.with_name('original.db');self.path.rename(moved)
        self.path.write_bytes(moved.read_bytes())
        with self.assertRaises(NodeJournalError): self.journal.get('task1')
        alias=self.path.with_name('alias.db');os.link(self.path,alias)
        with self.assertRaises(NodeJournalError): scoped_journal(alias)

    def test_foreign_schema_in_valid_chain_untouched(self):
        self.journal.create(operation())
        with closing(sqlite3.connect(self.path)) as db:
            db.execute('CREATE TABLE foreign_data (value TEXT)');db.commit()
        before=self.path.read_bytes()
        with self.assertRaises(NodeJournalError): self.journal.transition('task1','VERIFIED')
        self.assertEqual(self.path.read_bytes(),before)

    def test_failed_reservation_is_retained(self):
        with patch.object(self.journal._journal,'initialize',side_effect=sqlite3.OperationalError('full')):
            with self.assertRaises(NodeJournalError): self.journal.create(operation())
        self.assertTrue(self.path.exists())
        with self.assertRaises(NodeJournalError): scoped_journal(self.path).create(operation())

    def test_generation_v2_reference_only_strict_uuid(self):
        valid='12345678-1234-4234-8234-123456789abc'
        parsed=NodeOperation.parse(operation(schema='unified.node-operation.v2',authority_generation=valid))
        self.assertEqual(parsed['authority_generation'],valid)
        for value in (1,True,0,'00000000-0000-0000-0000-000000000000',valid.upper(),'12345678-1234-1234-8234-123456789abc'):
            with self.assertRaises(NodeJournalError):
                NodeOperation.parse(operation(schema='unified.node-operation.v2',authority_generation=value))
        with self.assertRaises(NodeJournalError): NodeOperation.parse(operation(schema='unified.node-operation.v1',authority_generation=1))

    def test_generation_change_is_immutable_collision(self):
        self.journal.create(operation(schema='unified.node-operation.v2',authority_generation='12345678-1234-4234-8234-123456789abc'))
        with self.assertRaises(NodeJournalError):
            self.journal.create(operation(schema='unified.node-operation.v2',authority_generation='12345678-1234-4234-8234-123456789abd'))

    def test_symlink_not_adopted_where_available(self):
        import os
        self.journal.create(operation())
        alias=self.path.with_name('symbolic.db')
        try: os.symlink(self.path,alias)
        except OSError:
            # Host lacks privilege: record unsupported, never mark symlink acceptance.
            self.assertFalse(alias.exists())
            print('SYMLINK_CREATION_UNAVAILABLE: host privilege; no symlink qualification claimed')
            return
        with self.assertRaises(NodeJournalError): scoped_journal(alias)

    def test_empty_legacy_database_not_adopted(self):
        from unified_system.journal import Journal
        legacy=Journal(self.path);legacy.initialize()
        before=self.path.read_bytes()
        with self.assertRaises(NodeJournalError): scoped_journal(self.path).create(operation())
        self.assertEqual(before,self.path.read_bytes())

    def test_journal_rejects_mixed_node_cluster_incarnation(self):
        scope=dict(cluster_id='cluster1',node_id='node1',node_incarnation='inc1')
        journal=NodeTaskJournal(self.path,**scope)
        journal.create(operation())
        before=self.path.read_bytes()
        for changes in ({'node_id':'PC1'},{'cluster_id':'foreign'},{'node_incarnation':'inc2'}):
            with self.assertRaises(NodeJournalError): journal.create(operation(task_id='other',idempotency_key='other',**changes))
            self.assertEqual(before,self.path.read_bytes())
        for changes in ({'node_id':'PC1'},{'cluster_id':'foreign'},{'node_incarnation':'inc2'}):
            with self.assertRaises(NodeJournalError): NodeTaskJournal(self.path,**dict(scope,**changes)).reconcile()
            self.assertEqual(before,self.path.read_bytes())

    def test_concurrent_empty_scope_writers_one_scope_wins(self):
        import threading
        scope=dict(cluster_id='cluster1',node_id='node1',node_incarnation='inc1')
        left=NodeTaskJournal(self.path,**scope)
        right=NodeTaskJournal(self.path,**dict(scope,node_id='PC1'))
        barrier=threading.Barrier(2)
        results=[]
        def run(journal,intent):
            original=journal._append
            def synchronized(record,count):
                barrier.wait(timeout=10)
                return original(record,count)
            with patch.object(journal,'_append',side_effect=synchronized):
                try: journal.create(intent);results.append('CREATED')
                except NodeJournalError: results.append('REJECTED')
        first=threading.Thread(target=run,args=(left,operation()))
        second=threading.Thread(target=run,args=(right,operation(node_id='PC1')))
        first.start();second.start();first.join(15);second.join(15)
        self.assertFalse(first.is_alive() or second.is_alive())
        self.assertCountEqual(results,['CREATED','REJECTED'])
        from unified_system.journal import Journal
        self.assertEqual(len(Journal(self.path).read()),1)

    def test_scope_projections_cannot_rebind_and_old_receipts_refuse(self):
        self.journal.create(operation())
        projected=self.journal.scope;projected['node_id']='PC1'
        record=self.journal.get('task1');record['scope']['node_id']='PC1';record['intent']['node_id']='PC1'
        self.assertEqual(self.journal.scope['node_id'],'node1')
        self.assertEqual(self.journal.get('task1')['scope']['node_id'],'node1')
        with self.assertRaises(AttributeError): self.journal.scope={'node_id':'PC1'}
        from unified_system.journal import Journal
        oldpath=self.path.with_name('unbound.db')
        old=Journal(oldpath);old.initialize()
        old.append('OBSERVING',dict(schema='unified.node-task-journal.v1',intent=operation(),state='CREATED',receipt={}))
        before=oldpath.read_bytes()
        with self.assertRaises(NodeJournalError): scoped_journal(oldpath)
        self.assertEqual(before,oldpath.read_bytes())

    def test_mixed_scope_hashchain_rejected_before_replay(self):
        self.journal.create(operation())
        from unified_system.journal import Journal
        wrong=self.journal.get('task1')
        wrong['intent']=operation(task_id='foreign',idempotency_key='foreign',node_id='PC1')
        wrong['scope']['node_id']='PC1'
        Journal(self.path).append('OBSERVING',wrong,expected_sequence=1)
        before=self.path.read_bytes()
        with self.assertRaises(NodeJournalError): self.journal.reconcile()
        with self.assertRaises(NodeJournalError): scoped_journal(self.path)
        self.assertEqual(before,self.path.read_bytes())
