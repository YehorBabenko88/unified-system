import tempfile, unittest, sqlite3, os
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from unified_system.contracts import ContractError
from unified_system.journal import Journal
from unified_system.installation_progress import InstallationProgress

class InstallationProgressTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'progress.db'
        self.p=InstallationProgress.create(self.path,'install-1','node-1','a'*64)
    def event(self,**changes):
        value=dict(receipt_id='receipt-1',operation_id='operation-1',correlation_id='correlation-1',timestamp_ms=1000,phase='PREPARE',outcome='NOT_RUN',error_code='NONE')
        value.update(changes);return value
    def test_reopen_counts_and_honest_snapshot(self):
        self.p.append(**self.event(done=1,total=4))
        snapshot=InstallationProgress.open(self.path,'install-1','node-1','a'*64).snapshot()
        self.assertEqual(snapshot['events'][0]['percentage'],25)
        self.assertFalse(snapshot['authority']);self.assertEqual(snapshot['installed'],'NOT_PROVEN');self.assertEqual(snapshot['readiness'],'NOT_PROVEN')
        self.assertTrue(all(row['state']=='OBSERVING' for row in Journal(self.path).read()))
    def test_no_percentage_without_counts_or_handoff_authority(self):
        self.p.append(**self.event(phase='TERMINAN_HANDOFF',outcome='PASS'))
        snapshot=self.p.snapshot();self.assertNotIn('percentage',snapshot['events'][0]);self.assertEqual(snapshot['readiness'],'NOT_PROVEN')
    def test_duplicate_idempotency_and_conflicting_reuse(self):
        first=self.p.append(**self.event());self.assertEqual(first,self.p.append(**self.event()))
        with self.assertRaises(ContractError):self.p.append(**self.event(outcome='PASS'))
        self.assertEqual(len(self.p.snapshot()['events']),1)
    def test_fences_timestamp_phase_counts_and_operation(self):
        self.p.append(**self.event(phase='VERIFY',done=2,total=4))
        for changes in ({'timestamp_ms':999},{'phase':'PREPARE'},{'done':1,'total':4},{'done':3,'total':5},{'operation_id':'other'}):
            with self.subTest(changes=changes),self.assertRaises(ContractError):self.p.append(**self.event(**(dict(receipt_id='receipt-2',timestamp_ms=1001,phase='VERIFY',done=3,total=4)|changes)))
    def test_closed_public_fields_and_values(self):
        for changes in ({'message':'secret'},{'error_code':'password'},{'phase':'COMPLETE'},{'outcome':'RUNNING'},{'done':True,'total':2},{'done':1},{'timestamp_ms':True},{'operation_id':'https://secret'}):
            with self.subTest(changes=changes),self.assertRaises((ContractError,TypeError)):self.p.append(**self.event(**changes))
        self.assertEqual(len(self.p.snapshot()['events']),0)
    def test_wrong_identity_existing_foreign_and_missing(self):
        with self.assertRaises(ContractError):InstallationProgress.create(self.path,'install-1','node-1','a'*64)
        with self.assertRaises(ContractError):InstallationProgress.open(self.path,'wrong','node-1','a'*64)
        foreign=Path(self.tmp.name)/'foreign.db';j=Journal(foreign);j.initialize();j.append('OBSERVING',{'secret':'not-progress'})
        with self.assertRaises(ContractError):InstallationProgress.open(foreign,'install-1','node-1','a'*64)
        with self.assertRaises(ContractError):InstallationProgress.open(Path(self.tmp.name)/'missing','install-1','node-1','a'*64)
    def test_link_and_tamper_rejected(self):
        link=Path(self.tmp.name)/'hardlink';os.link(self.path,link)
        with self.assertRaises(ContractError):InstallationProgress.open(link,'install-1','node-1','a'*64)
        link.unlink()
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("UPDATE transitions SET receipt='{}'");db.commit()
        with self.assertRaises(ContractError):self.p.snapshot()
    def test_release_binding_unsafe_paths_and_foreign_status(self):
        with self.assertRaises(ContractError):InstallationProgress.open(self.path,'install-1','node-1','b'*64)
        with self.assertRaises(ContractError):InstallationProgress.create(Path('relative.db'),'install-1','node-1','a'*64)
        before=self.path.read_bytes()
        with self.assertRaises(ContractError):InstallationProgress.create(self.path,'install-1','node-1','a'*64)
        self.assertEqual(before,self.path.read_bytes())
        Journal(self.path).append('INSTALLED',{'schema':'foreign'})
        with self.assertRaises(ContractError):self.p.snapshot()
    def test_truncated_file_rejected(self):
        self.path.write_bytes(b'partial')
        with self.assertRaises(ContractError):InstallationProgress.open(self.path,'install-1','node-1','a'*64)

    def test_stale_validation_cannot_commit(self):
        original=Journal.append
        injected=False
        def race(journal,state,receipt=None,**kwargs):
            nonlocal injected
            if not injected:
                injected=True
                other=InstallationProgress.open(self.path,'install-1','node-1','a'*64)
                other.append(**self.event(receipt_id='other',timestamp_ms=2000,phase='VERIFY'))
            return original(journal,state,receipt,**kwargs)
        with patch.object(Journal,'append',race),self.assertRaises(ContractError):self.p.append(**self.event())
        self.assertEqual([e['receipt_id'] for e in self.p.snapshot()['events']],['other'])
    def test_partial_append_failure_does_not_publish(self):
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("CREATE TRIGGER fail_append BEFORE INSERT ON transitions BEGIN SELECT RAISE(ABORT, 'injected'); END");db.commit()
        with self.assertRaises(sqlite3.IntegrityError):self.p.append(**self.event())
        self.assertEqual(InstallationProgress.open(self.path,'install-1','node-1','a'*64).snapshot()['events'],[])
        with closing(sqlite3.connect(self.path)) as db:
            db.execute('DROP TRIGGER fail_append');db.commit()
        self.p.append(**self.event())
        self.assertEqual(len(self.p.snapshot()['events']),1)

if __name__=='__main__':unittest.main()
