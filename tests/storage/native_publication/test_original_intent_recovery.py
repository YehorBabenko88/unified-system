"""Actual owned SQLite/immutable-byte recovery, never a simulated native commit."""
import base64
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from unified_system.journal import Journal
from unified_system.storage.contracts import StorageBlocked
from unified_system.storage.object_store import ObjectStore
from unified_system.storage.publication_records import RetainedPublicationIntent
from unified_system.storage.publication_recovery import PendingPublicationJournal

PUBLICATION = '00000000-0000-4000-8000-000000000001'
STORE = '00000000-0000-4000-8000-000000000002'
RAW = b'{"opaque_candidate":1.25,"unknown":null}'


class OriginalIntentRecoveryTests(unittest.TestCase):
    def setup_owned(self, root):
        journal = Journal(root/'pending.sqlite')
        journal.initialize()
        store = ObjectStore.create(root/'objects', store_id=STORE)
        return journal, store, PendingPublicationJournal(journal, store)

    def test_exact_original_bytes_survive_journal_reopen_without_native_success(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);journal,store,pending=self.setup_owned(root)
            intent=RetainedPublicationIntent(PUBLICATION,RAW)
            observation=pending.retain(intent)
            self.assertEqual(observation.native_outcome,'UNKNOWN')
            self.assertFalse(observation.publication_confirmed)
            self.assertEqual(ObjectStore.read(store,intent.sha256),RAW)
            reopened=PendingPublicationJournal(Journal(journal.path),ObjectStore.open(store._root,store_id=STORE))
            recovered=reopened.recover_original(PUBLICATION)
            self.assertEqual(recovered.raw_bytes,RAW)
            self.assertEqual(recovered.publication_id,PUBLICATION)
            self.assertEqual(len(journal.read()),1)

    def test_exact_retry_does_not_duplicate_and_conflict_never_replaces(self):
        with tempfile.TemporaryDirectory() as temp:
            journal,_,pending=self.setup_owned(Path(temp))
            pending.retain(RetainedPublicationIntent(PUBLICATION,RAW))
            pending.retain(RetainedPublicationIntent(PUBLICATION,RAW))
            with self.assertRaises(StorageBlocked):pending.retain(RetainedPublicationIntent(PUBLICATION,b'different'))
            self.assertEqual(len(journal.read()),1)
            self.assertEqual(pending.recover_original(PUBLICATION).raw_bytes,RAW)

    def test_attempt_marker_remains_unknown_without_automatic_resend(self):
        with tempfile.TemporaryDirectory() as temp:
            journal,_,pending=self.setup_owned(Path(temp))
            pending.retain(RetainedPublicationIntent(PUBLICATION,RAW))
            for _ in range(2):
                observation=pending.mark_attempt_uncertain(PUBLICATION)
                self.assertEqual(observation.native_outcome,'UNKNOWN')
                self.assertFalse(observation.publication_confirmed)
            self.assertEqual(len(journal.read()),2)
            self.assertEqual(pending.recover_original(PUBLICATION).raw_bytes,RAW)

    def test_crash_after_durable_attempt_marker_retains_same_original(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);journal,_,pending=self.setup_owned(root)
            pending.retain(RetainedPublicationIntent(PUBLICATION,RAW))
            code='''import os,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from unified_system.journal import Journal
from unified_system.storage.object_store import ObjectStore
from unified_system.storage.publication_recovery import PendingPublicationJournal
root=Path(sys.argv[2])
p=PendingPublicationJournal(Journal(root/'pending.sqlite'),ObjectStore.open(root/'objects',store_id=sys.argv[3]))
p.mark_attempt_uncertain(sys.argv[4])
os._exit(23)
'''
            repo=Path(__file__).resolve().parents[3]
            result=subprocess.run([sys.executable,'-I','-S','-B','-c',code,str(repo),str(root),STORE,PUBLICATION],capture_output=True)
            self.assertEqual(result.returncode,23,result.stderr)
            fresh=PendingPublicationJournal(Journal(journal.path),ObjectStore.open(root/'objects',store_id=STORE))
            self.assertEqual(fresh.recover_original(PUBLICATION).raw_bytes,RAW)
            self.assertEqual(fresh.observation(PUBLICATION).native_outcome,'UNKNOWN')
            self.assertEqual(len(journal.read()),2)

    def test_missing_or_corrupt_staged_object_is_explicit_without_republication(self):
        with tempfile.TemporaryDirectory() as temp:
            journal,store,pending=self.setup_owned(Path(temp));intent=RetainedPublicationIntent(PUBLICATION,RAW)
            pending.retain(intent)
            path=store._root/'objects'/intent.sha256
            path.write_bytes(b'corrupted actual bytes')
            self.assertEqual(pending.recover_original(PUBLICATION).raw_bytes,RAW)
            with self.assertRaises(StorageBlocked):pending.verify_staged_original(PUBLICATION)
            self.assertEqual(len(journal.read()),1)
            self.assertEqual(path.read_bytes(),b'corrupted actual bytes')

    def test_original_byte_preflight_and_identifiers_reject_before_custom_methods(self):
        class Foreign(bytes):
            def __len__(self):raise AssertionError('foreign length')
        for identifier,raw in ((PUBLICATION+'\n',RAW),(True,RAW),(PUBLICATION,b''),
                              (PUBLICATION,b'x'*16385),(PUBLICATION,Foreign(RAW))):
            with self.subTest(identifier=identifier),self.assertRaises(StorageBlocked):RetainedPublicationIntent(identifier,raw)

    def test_foreign_journal_record_and_wrong_schema_are_not_adopted(self):
        with tempfile.TemporaryDirectory() as temp:
            journal,store,_=self.setup_owned(Path(temp))
            journal.append('OBSERVING',dict(schema='unrelated.own.journal.v1'))
            with self.assertRaises(StorageBlocked):PendingPublicationJournal(journal,store)

    def test_journal_tamper_fails_and_never_mints_committed_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            journal,_,pending=self.setup_owned(Path(temp));pending.retain(RetainedPublicationIntent(PUBLICATION,RAW))
            con=sqlite3.connect(journal.path)
            con.execute("UPDATE transitions SET receipt='{}'");con.commit();con.close()
            with self.assertRaises(StorageBlocked):pending.observation(PUBLICATION)

    def test_unknown_id_and_attempt_without_retained_original_do_not_create_state(self):
        with tempfile.TemporaryDirectory() as temp:
            journal,_,pending=self.setup_owned(Path(temp))
            for fn in (pending.recover_original,pending.mark_attempt_uncertain,pending.observation):
                with self.assertRaises(StorageBlocked):fn(PUBLICATION)
            self.assertEqual(journal.read(),[])

    def test_local_record_rejects_claimed_native_commit_or_result_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            journal,store,_=self.setup_owned(Path(temp))
            journal.append('OBSERVING',dict(schema='unified.storage.pending-original.v1',publication_id=PUBLICATION,
                intent_base64=base64.b64encode(RAW).decode(),intent_sha256='a'*64,
                intent_bytes=str(len(RAW)),phase='COMMITTED',native_receipt={'state':'COMMITTED'}))
            with self.assertRaises(StorageBlocked):PendingPublicationJournal(journal,store)

    def test_corrupt_actual_sqlite_has_closed_unavailable_result(self):
        with tempfile.TemporaryDirectory() as temp:
            journal,store,_=self.setup_owned(Path(temp))
            journal.path.write_bytes(b'not an actual SQLite database')
            with self.assertRaises(StorageBlocked):PendingPublicationJournal(journal,store)

    def test_append_response_loss_preserves_actual_committed_local_original(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temp:
            journal,store,pending=self.setup_owned(Path(temp));original=Journal.append
            def lose_response(instance,*args,**kwargs):
                original(instance,*args,**kwargs)
                raise OSError('local append response lost after actual SQLite commit')
            with patch.object(Journal,'append',lose_response):
                with self.assertRaises(StorageBlocked):pending.retain(RetainedPublicationIntent(PUBLICATION,RAW))
            fresh=PendingPublicationJournal(Journal(journal.path),store)
            self.assertEqual(fresh.recover_original(PUBLICATION).raw_bytes,RAW)
            self.assertEqual(fresh.observation(PUBLICATION).native_outcome,'UNKNOWN')
            self.assertEqual(len(journal.read()),1)

    def test_exhausted_journal_budget_rejects_before_new_staging_io(self):
        from unittest.mock import patch
        import unified_system.storage.publication_recovery as recovery
        with tempfile.TemporaryDirectory() as temp:
            journal,_,pending=self.setup_owned(Path(temp))
            with patch.object(recovery,'MAX_RECORDS',1):
                pending.retain(RetainedPublicationIntent(PUBLICATION,RAW))
                other=RetainedPublicationIntent('00000000-0000-4000-8000-000000000003',b'new bytes')
                with patch.object(ObjectStore,'put',side_effect=AssertionError('quota denial must precede IO')):
                    with self.assertRaises(StorageBlocked):pending.retain(other)
                self.assertEqual(len(journal.read()),1)
