"""Offline receipt validation only; no Windows authentication is exercised."""
import unittest
import os
import subprocess
import tempfile
from pathlib import Path
from scripts.verify_operator_auth_source import validate_receipt,verify_source


class NativeReceiptTests(unittest.TestCase):
 def fixture(self):
  return dict(schema='unified.native-subject-negative.v1',compile='PASS',invalid_context='REJECTED',
              subject_extraction_positive='NOT_RUN',tls_cbt='NOT_QUALIFIED',
              runtime_factory='DENY',authentication='NOT_QUALIFIED',
              negative_cases=['ABSENT_OWNER','OUTBOUND_OWNER','EMPTY_CONTEXT','NATIVE_INVALID_CONTEXT','EMPTY_GENERATION'],
              native_invalid_handle_observed=True)
 def test_partial_evidence_is_explicit_and_closed(self):
  self.assertEqual(validate_receipt(self.fixture()),self.fixture())
  for patch in ({'authentication':'PASS'},{'tls_cbt':'PASS'},{'runtime_factory':'ALLOW'},
                {'secret':'private'},{'invalid_context':'PASS'},{'negative_cases':[]},{'native_invalid_handle_observed':False},{'native_invalid_handle_observed':1}):
   with self.assertRaises(ValueError):validate_receipt(dict(self.fixture(),**patch))
 def test_raw_source_rejects_changed_bytes_and_untracked_code(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder).resolve();env=os.environ.copy()
   env.update(GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull,GIT_CONFIG_COUNT='0')
   def git(*args):return subprocess.check_output(['git','-c','core.autocrlf=false','-c','core.hooksPath='+str(root/'no-hooks'),*args],cwd=root,env=env,stderr=subprocess.DEVNULL)
   git('init');(root/'inert.txt').write_bytes(b'inert\n');git('add','inert.txt')
   git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-m','inert')
   head=git('rev-parse','HEAD').decode().strip()
   self.assertEqual(verify_source(root,head)['raw_blobs'],1)
   (root/'inert.txt').write_bytes(b'inert\r\n')
   with self.assertRaises(ValueError):verify_source(root,head)
   (root/'inert.txt').write_bytes(b'inert\n');(root/'untracked.py').write_bytes(b'# inert')
   with self.assertRaises(ValueError):verify_source(root,head)
