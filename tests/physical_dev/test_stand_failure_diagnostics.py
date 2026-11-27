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
 def test_foreign_exception_type_callbacks_cannot_replace_original(self):
  class Hostile(type):
   def __hash__(self):raise AssertionError('FOREIGN_HASH_CALLED')
   def __eq__(self,other):raise AssertionError('FOREIGN_EQUALITY_CALLED')
  class Foreign(RuntimeError,metaclass=Hostile):pass
  original=Foreign('SECRET_SENTINEL')
  class Stand(InertStand):
   def _runtime_custody(self):raise original
  try:
   with observe_constructor(Stand,InertJournal,Rejected):Stand()
  except BaseException as caught:self.assertIs(caught,original)
  else:self.fail('original exception missing')
  self.assertIsNone(sys.gettrace())


 def source_note(self,source):
  from integration.source_guard import SourceQualificationError
  outer=Rejected('DISPOSABLE_STAND_UNAVAILABLE')
  class Stand(InertStand):
   def __init__(self):
    try:self._runtime_custody()
    except SourceQualificationError:raise outer from None
   def _runtime_custody(self):raise source
  with self.assertRaises(Rejected) as caught:
   with observe_constructor(Stand,InertJournal,Rejected):Stand()
  self.assertIs(caught.exception,outer)
  self.assertIsNone(sys.gettrace())
  return outer.__notes__[0]
 def test_only_exact_two_source_namespace_codes_are_observed(self):
  from integration.source_guard import SourceQualificationError
  for code in ('EXTERNAL_SOURCE_NAMESPACE','LINKED_SOURCE_METADATA'):
   with self.subTest(code=code):
    original=SourceQualificationError(code);note=self.source_note(original)
    self.assertIn('RUNTIME_CUSTODY:'+code,note)
    self.assertTrue(note.isascii());self.assertLessEqual(len(note),1024)
 def test_source_error_args_are_closed_literal_bounded_and_never_coerced(self):
  from integration.source_guard import SourceQualificationError
  calls=[]
  class Text(str):
   def __hash__(self):calls.append('hash');raise AssertionError('SOURCE_SUBCLASS_HASH')
   def __eq__(self,other):calls.append('eq');raise AssertionError('SOURCE_SUBCLASS_EQ')
  class Object:
   def __str__(self):calls.append('str');raise AssertionError('SOURCE_ARG_COERCION')
  for args in (('SECRET_SENTINEL/path/token',),('SECRET_SENTINEL'*1000,),('EXTERNAL_SOURCE_NAMESPACE','SECRET_SENTINEL'),(Text('EXTERNAL_SOURCE_NAMESPACE'),),(Object(),),()):
   note=self.source_note(SourceQualificationError(*args))
   self.assertIn('RUNTIME_CUSTODY:OTHER_ERROR',note)
   self.assertNotIn('SECRET_SENTINEL',note)
   self.assertNotIn('EXTERNAL_SOURCE_NAMESPACE',note)
  self.assertEqual(calls,[])
 def test_source_exception_subclass_identity_is_not_accepted_or_inspected(self):
  from integration.source_guard import SourceQualificationError
  calls=[]
  class Hostile(type):
   def __hash__(self):calls.append('hash');raise AssertionError('SOURCE_TYPE_HASH')
   def __eq__(self,other):calls.append('eq');raise AssertionError('SOURCE_TYPE_EQ')
  class Subclass(SourceQualificationError,metaclass=Hostile):
   @property
   def args(self):calls.append('args');raise AssertionError('SOURCE_SUBCLASS_ARGS')
  note=self.source_note(Subclass('EXTERNAL_SOURCE_NAMESPACE'))
  self.assertIn('RUNTIME_CUSTODY:OTHER_ERROR',note)
  self.assertNotIn('EXTERNAL_SOURCE_NAMESPACE',note)
  self.assertEqual(calls,[])
