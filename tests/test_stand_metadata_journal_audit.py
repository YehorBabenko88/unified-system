"""Pure path parsing for the hosted metadata audit; no SQL or source admission."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
class StandJournalAuditTests(unittest.TestCase):
 def setUp(self):
  spec=importlib.util.spec_from_file_location('stand_metadata_audit',ROOT/'scripts/qualify_stand_construction.py');self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve();self.out=self.root/'owned';self.out.mkdir();self.path=self.out/'canonical-target.v2.sqlite'
 def test_owned_literal_path_is_accepted(self):
  self.assertEqual(self.module.private_journal_path(str(self.path),self.out),self.path)
 def test_actual_journal_readonly_uri_is_accepted(self):
  self.assertEqual(self.module.private_journal_path(self.path.as_uri()+'?mode=ro',self.out),self.path)
 def test_foreign_literal_and_uri_remain_denied(self):
  foreign=self.root/'foreign.sqlite'
  for value in (str(foreign),foreign.as_uri()+'?mode=ro'):
   with self.subTest(value=value),self.assertRaises(RuntimeError):self.module.private_journal_path(value,self.out)
 def test_uri_authority_fragment_and_mutating_modes_are_denied(self):
  for value in ('file://remote'+self.path.as_posix()+'?mode=ro',self.path.as_uri()+'?mode=rw',self.path.as_uri()+'?mode=ro&immutable=1',self.path.as_uri()+'?mode=ro#fragment'):
   with self.subTest(value=value),self.assertRaises(RuntimeError):self.module.private_journal_path(value,self.out)
 def test_encoded_escape_remains_denied(self):
  value=self.out.as_uri()+'/%2e%2e/foreign.sqlite?mode=ro'
  with self.assertRaises(RuntimeError):self.module.private_journal_path(value,self.out)
 def test_nonliteral_names_are_denied_without_callbacks(self):
  class Hostile(str):
   def startswith(self,*args):raise AssertionError('HOSTILE_CALLBACK')
  for value in (None,True,1,Hostile(str(self.path))):
   with self.subTest(kind=type(value).__name__),self.assertRaises(RuntimeError):self.module.private_journal_path(value,self.out)
