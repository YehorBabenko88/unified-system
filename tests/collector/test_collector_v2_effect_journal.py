"""Actual private Journal files, not capabilities or native operation tests."""
import ctypes
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).absolute().parents[2]
sys.path.insert(0,str(ROOT))
from unified_system.collector_service_phase_v2 import CollectorEffectJournal


class CollectorEffectJournalTests(unittest.TestCase):
 def setUp(self):
  native=patch.object(ctypes,'WinDLL',side_effect=AssertionError('NO_NATIVE_API'),create=True)
  native.start();self.addCleanup(native.stop)
  self.temp=tempfile.TemporaryDirectory(prefix='collector-effect-unit-');self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name).resolve()/'phase';self.phase='phase-unit';self.intent='a'*64
 def create(self):return CollectorEffectJournal.create(self.root,phase_id=self.phase,intent_sha256=self.intent)
 def open(self):return CollectorEffectJournal.open(self.root,phase_id=self.phase,intent_sha256=self.intent)
 def test_actual_attempt_confirm_and_reopen_never_grants_authority(self):
  journal=self.create();ticket=journal.attempt('register','REGISTER','b'*64)
  self.assertEqual(journal.status()['state'],'UNKNOWN')
  journal.confirm(ticket,'c'*64)
  current=self.open().status();self.assertEqual(current['state'],'READY');self.assertEqual(current['confirmed_effects'],1)
  self.assertIs(current['execution_authority'],False)
 def test_unconfirmed_attempt_survives_restart_and_blocks_new_work(self):
  journal=self.create();journal.attempt('register','REGISTER','b'*64)
  observed=self.open();self.assertEqual(observed.status()['state'],'UNKNOWN')
  with self.assertRaises(ValueError):observed.attempt('start','SERVICE_START','d'*64)
  with self.assertRaises(ValueError):observed.confirm(object(),'c'*64)
 def test_confirmed_effect_key_cannot_be_replayed_under_another_plan(self):
  journal=self.create();ticket=journal.attempt('register','REGISTER','b'*64);journal.confirm(ticket,'c'*64)
  with self.assertRaises(ValueError):journal.attempt('register','REGISTER','d'*64)
 def test_unknown_consumes_phase_and_preserves_reason(self):
  journal=self.create();ticket=journal.attempt('register','REGISTER','b'*64);journal.unknown(ticket,'NATIVE_OUTCOME_UNKNOWN')
  self.assertEqual(self.open().status()['state'],'UNKNOWN')
  with self.assertRaises(ValueError):journal.confirm(ticket,'c'*64)
  with self.assertRaises(ValueError):journal.attempt('next','STAGE','b'*64)
 def test_ticket_from_another_instance_is_not_a_completion_claim(self):
  journal=self.create();ticket=journal.attempt('register','REGISTER','b'*64)
  with self.assertRaises(ValueError):self.open().confirm(ticket,'c'*64)
  journal.confirm(ticket,'c'*64)
 def test_readonly_open_status_does_not_change_bytes(self):
  journal=self.create();ticket=journal.attempt('stage','STAGE','b'*64);journal.confirm(ticket,'c'*64)
  before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.iterdir()}
  self.open().status()
  after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.iterdir()}
  self.assertEqual(before,after)
 def test_wrong_binding_existing_namespace_and_alias_types_fail(self):
  journal=self.create()
  with self.assertRaises(ValueError):self.create()
  with self.assertRaises(ValueError):CollectorEffectJournal.open(self.root,phase_id=self.phase,intent_sha256='d'*64)
  class Text(str):pass
  for key,action,digest in [(Text('stage'),'STAGE','b'*64),('stage',True,'b'*64),('stage','STAGE',Text('b'*64))]:
   with self.subTest(key=key),self.assertRaises(ValueError):journal.attempt(key,action,digest)
 def test_replaced_marker_or_modified_journal_is_not_adopted(self):
  self.create();marker=self.root/'phase-owned.json';marker.write_bytes(b'{}\n')
  with self.assertRaises(ValueError):self.open()
 def test_competing_attempt_between_scan_and_append_cannot_return_ticket(self):
  first=self.create();second=self.open();append=second._append
  def compete(*args,**kwargs):
   first.attempt('first','REGISTER','b'*64)
   return append(*args,**kwargs)
  with patch.object(second,'_append',side_effect=compete),self.assertRaises(ValueError):second.attempt('second','STAGE','c'*64)
  self.assertEqual(first.status()['events'],1)
 def test_committed_append_error_leaves_unknown_without_retry(self):
  journal=self.create();append=journal._journal.append
  def fail_after_commit(*args,**kwargs):append(*args,**kwargs);raise OSError('INERT_COMMIT_UNCERTAINTY')
  with patch.object(journal._journal,'append',side_effect=fail_after_commit),self.assertRaises(OSError):journal.attempt('register','REGISTER','b'*64)
  self.assertEqual(self.open().status()['state'],'UNKNOWN')
  with self.assertRaises(ValueError):journal.attempt('register','REGISTER','b'*64)
 def test_wal_header_rejects_before_any_sqlite_open(self):
  self.create();path=self.root/'effects.sqlite';raw=bytearray(path.read_bytes());raw[18:20]=b'\x02\x02';path.write_bytes(raw)
  with patch('sqlite3.connect',side_effect=AssertionError('SQLITE_OPEN_MUST_NOT_RUN')) as connect:
   with self.assertRaises(ValueError):self.open()
   connect.assert_not_called()


if __name__=='__main__':unittest.main()
