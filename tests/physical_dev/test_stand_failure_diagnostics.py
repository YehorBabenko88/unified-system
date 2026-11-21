"""Inert calibration; actual stand, journal and native code are never invoked."""
import sys
import unittest
from tests.hosted_contracts.stand_diagnostics import observe_constructor

class Rejected(ValueError):pass
class InertJournal:
 def initialize(self):pass
 def read(self):pass
class InertStand:
 def __init__(self):self._runtime_custody()
 def _runtime_custody(self):raise Rejected('RUNTIME_PIN_MISMATCH')
 def _records(self):pass
class StandFailureDiagnosticsTests(unittest.TestCase):
 def test_original_exception_identity_and_known_closed_code_retained(self):
  original=Rejected('RUNTIME_PIN_MISMATCH')
  class Stand(InertStand):
   def _runtime_custody(self):raise original
  with self.assertRaises(Rejected) as caught:
   with observe_constructor(Stand,InertJournal,Rejected):Stand()
  self.assertIs(caught.exception,original)
  self.assertIn('RUNTIME_CUSTODY:RUNTIME_PIN_MISMATCH',original.__notes__[0])
  self.assertIsNone(sys.gettrace())
 def test_foreign_exception_text_is_never_copied_to_note(self):
  class Stand(InertStand):
   def _runtime_custody(self):raise Rejected('SECRET_SENTINEL/path/token')
  with self.assertRaises(Rejected) as caught:
   with observe_constructor(Stand,InertJournal,Rejected):Stand()
  self.assertNotIn('SECRET_SENTINEL',caught.exception.__notes__[0])
  self.assertIn('RUNTIME_CUSTODY:TARGET_REJECTED',caught.exception.__notes__[0])
  self.assertIsNone(sys.gettrace())
 def test_success_restores_trace_without_calls_or_notes(self):
  class Stand(InertStand):
   def _runtime_custody(self):pass
  with observe_constructor(Stand,InertJournal,Rejected):Stand()
  self.assertIsNone(sys.gettrace())
