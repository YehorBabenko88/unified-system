"""Isolated staging fixtures; inert bytes are never an installed runtime."""
import copy,hashlib,os,sqlite3,tempfile,unittest
from pathlib import Path
from contextlib import closing
from unittest.mock import patch
from tests.test_lab_release import fixture
from unified_system import lab_release
from unified_system.journal import Journal
from unified_system.installation_transaction import InstallationTransaction, source_plan

class InstallationTransactionTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.source=self.root/'capsule';self.source.mkdir();self.manifest=fixture(self.source)
  raw=lab_release.canonical(self.manifest);(self.source/'lab-release.json').write_bytes(raw);self.pin=hashlib.sha256(raw).hexdigest()
 def plan(self,**changes):
  args=dict(capsule_root=self.source,install_root=self.root/'install',state_root=self.root/'state',installation_id='install1',node_id='node1',operation_id='op1',role='CONTROL',manifest_sha256=self.pin)
  args.update(changes);return source_plan(**args)
 def test_roles_and_closed_admission_not_execution(self):
  for role,wanted in [('CONTROL','CONTROL'),('WORKER','WORKER'),('SINGLE-PC','SINGLE_PC'),('SINGLE_PC','SINGLE_PC')]:
   plan=self.plan(role=role);self.assertEqual(plan['role'],wanted);self.assertEqual(plan['source_proof'],'NOT_EVALUATED');self.assertEqual(plan['activation'],'BLOCKED')
  with self.assertRaises(ValueError):self.plan(role='ADMIN')
  with self.assertRaises(ValueError):self.plan(manifest_sha256='f'*64)
  (self.source/'extra').write_bytes(b'unadmitted')
  with self.assertRaises(ValueError):self.plan()
 def test_real_stage_reopen_and_preserving_logical_rollback(self):
  plan=self.plan();tx=InstallationTransaction.create(plan);result=tx.stage()
  self.assertEqual(result['status'],'STAGED_INACTIVE');self.assertEqual(result['installed'],'NOT_PROVEN');self.assertFalse(result['execution_authority'])
  release=Path(plan['install_root'])/'release';self.assertEqual(lab_release.verify_capsule(release,self.pin)['manifest_sha256'],self.pin)
  other=InstallationTransaction.open(plan);self.assertEqual(other.resume()['status'],'STAGED_INACTIVE')
  before=(release/'lab-release.json').read_bytes();rolled=other.rollback()
  self.assertEqual(rolled['status'],'ROLLED_BACK_RETAINED');self.assertEqual((release/'lab-release.json').read_bytes(),before)
  self.assertEqual(other.rollback(),rolled)
  with self.assertRaises(ValueError):other.stage()
  self.assertTrue(all(r['state']=='OBSERVING' for r in Journal(tx.journal.path).read()))
 def test_existing_foreign_roots_and_wrong_identity_rejected(self):
  plan=self.plan();Path(plan['state_root']).mkdir()
  with self.assertRaises(ValueError):InstallationTransaction.create(plan)
  self.assertEqual(list(Path(plan['state_root']).iterdir()),[])
  Path(plan['state_root']).rmdir();tx=InstallationTransaction.create(plan)
  wrong=copy.deepcopy(plan);wrong['operation_id']='different'
  with self.assertRaises(ValueError):InstallationTransaction.open(wrong)
  Path(plan['install_root']).mkdir();(Path(plan['install_root'])/'foreign').write_text('preserve')
  with self.assertRaises(ValueError):tx.stage()
  with self.assertRaises(ValueError):tx.rollback()
  self.assertEqual((Path(plan['install_root'])/'foreign').read_text(),'preserve')
 def test_fault_before_child_creation_can_resume(self):
  plan=self.plan();tx=InstallationTransaction.create(plan)
  with patch.object(lab_release,'stage_capsule',side_effect=OSError('private failure')):
   with self.assertRaises(OSError):tx.stage()
  self.assertEqual(InstallationTransaction.open(plan).resume()['status'],'STAGED_INACTIVE')
 def test_partial_or_complete_unreceipted_child_never_adopted(self):
  for complete in (False,True):
   with self.subTest(complete=complete):
    plan=self.plan(install_root=self.root/('install'+str(complete)),state_root=self.root/('state'+str(complete)))
    tx=InstallationTransaction.create(plan);original=lab_release.stage_capsule
    def fail(source,target,pin):
     if complete:original(source,target,pin)
     else:Path(target).mkdir();(Path(target)/'partial').write_bytes(b'keep')
     raise OSError('interrupted receipt')
    with patch.object(lab_release,'stage_capsule',side_effect=fail):
     with self.assertRaises(OSError):tx.stage()
    with self.assertRaises(ValueError):InstallationTransaction.open(plan).resume()
    self.assertEqual(tx.rollback()['status'],'ROLLED_BACK_RETAINED');self.assertTrue((Path(plan['install_root'])/'release').exists())
 def test_changed_staged_bytes_and_root_identity_fail_closed(self):
  plan=self.plan();tx=InstallationTransaction.create(plan);tx.stage()
  (Path(plan['install_root'])/'release/runtime.json').write_bytes(b'changed')
  with self.assertRaises(ValueError):tx.resume()
  original=Path(plan['install_root']);original.rename(self.root/'retained');original.mkdir()
  with self.assertRaises(ValueError):tx.rollback()
 def test_journal_tamper_and_foreign_status_rejected(self):
  plan=self.plan();tx=InstallationTransaction.create(plan)
  Journal(tx.journal.path).append('INSTALLED',{})
  with self.assertRaises(ValueError):tx.resume()
 def test_no_closure_admission_from_receipt_only(self):
  plan=self.plan();tx=InstallationTransaction.create(plan)
  (self.source/'runtime.json').write_bytes(b'changed')
  with self.assertRaises(ValueError):tx.stage()
  self.assertFalse(Path(plan['install_root']).exists())
 def test_stale_receipt_cas_blocks_before_stage_effect(self):
  plan=self.plan();tx=InstallationTransaction.create(plan)
  original=Journal.append
  def stale(journal,state,receipt=None,**kw):
   if receipt and receipt.get('kind')=='STAGE_INTENT':raise ValueError('stale')
   return original(journal,state,receipt,**kw)
  with patch.object(Journal,'append',stale),patch.object(lab_release,'stage_capsule') as effect:
   with self.assertRaises(ValueError):tx.stage()
   effect.assert_not_called()
  self.assertEqual(tx.resume()['status'],'STAGED_INACTIVE')
 def test_actual_concurrent_rollback_fences_stage_intent(self):
  plan=self.plan();tx=InstallationTransaction.create(plan);original=Journal.append;injected=False
  def race(journal,state,receipt=None,**kw):
   nonlocal injected
   if receipt and receipt.get('kind')=='STAGE_INTENT' and not injected:
    injected=True;InstallationTransaction.open(plan).rollback()
   return original(journal,state,receipt,**kw)
  with patch.object(Journal,'append',race),patch.object(lab_release,'stage_capsule') as effect:
   with self.assertRaises(ValueError):tx.stage()
   effect.assert_not_called()
  self.assertEqual(tx.snapshot()['status'],'ROLLED_BACK_RETAINED')
 def test_plan_pins_overlap_and_metadata_are_closed(self):
  with self.assertRaises(ValueError):self.plan(install_root=self.source/'nested')
  plan=self.plan();plan['sources']['math']['commit']='f'*40
  with self.assertRaises(ValueError):InstallationTransaction.create(plan)
  self.assertFalse(Path(plan['state_root']).exists())
  plan=self.plan();plan['source_proof']='VERIFIED'
  with self.assertRaises(ValueError):InstallationTransaction.create(plan)
 def test_capacity_and_hash_tamper_fail_closed(self):
  import unified_system.installation_transaction as module
  plan=self.plan();tx=InstallationTransaction.create(plan)
  with patch.object(module,'MAX_RECORDS',0):
   with self.assertRaises(ValueError):tx.resume()
  with closing(sqlite3.connect(tx.journal.path)) as db,db:db.execute("UPDATE transitions SET digest='tampered'")
  with self.assertRaises(ValueError):tx.resume()

 def test_links_and_oversized_foreign_journal_rejected(self):
  plan=self.plan();tx=InstallationTransaction.create(plan)
  alias=self.root/'alias';os.link(tx.journal.path,alias)
  with self.assertRaises(ValueError):tx.resume()
  alias.unlink()
  with closing(sqlite3.connect(tx.journal.path)) as db,db:db.execute('UPDATE transitions SET receipt=?',('x'*65537,))
  with self.assertRaises(ValueError):tx.resume()

if __name__=='__main__':unittest.main()
