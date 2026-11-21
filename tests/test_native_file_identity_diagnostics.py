"""Bounded metadata compatibility observations from owned inert files only.

This reports field equality, never identifiers/paths. It does not change or
replace the validators' existing strict identity, swap or hardlink assertions.
"""
import json
import os
from pathlib import Path
import platform
import tempfile
import unittest

FIELDS=('st_dev','st_ino','st_nlink','st_size','st_mtime_ns','st_ctime_ns')

def equality(left,right):
 return {field:getattr(left,field)==getattr(right,field) for field in FIELDS}

class NativeFileIdentityDiagnostics(unittest.TestCase):
 def test_inert_fixture_path_handle_field_equality_is_observed_without_identifiers(self):
  from tests import test_windows_toolchain as toolchain_tests
  from tests import test_windows_wheels as wheel_tests
  observations={}
  with tempfile.TemporaryDirectory(prefix='identity-observation-') as directory:
   path=Path(directory)/'inert.bin';raw=b'owned inert fixture\r\n';path.write_bytes(raw)
   before=path.lstat();fd=os.open(path,os.O_RDONLY|getattr(os,'O_NONBLOCK',0)|getattr(os,'O_NOFOLLOW',0))
   immediate=os.fstat(fd)
   with os.fdopen(fd,'rb') as stream:
    opened=os.fstat(stream.fileno());self.assertEqual(stream.read(),raw);after=os.fstat(stream.fileno())
   observations['path_vs_open']=equality(before,immediate)
   observations['path_vs_binary_stream']=equality(before,opened)
   observations['same_handle_after_read']=equality(opened,after)
   observations['same_path_after_close']=equality(before,path.lstat())
  tool=toolchain_tests.ToolchainTests('test_same_bytes_are_integrity_only_even_if_every_locked_artifact_present')
  wheel=wheel_tests.WindowsWheelTests('test_normal_candidate_matches_without_any_install_or_dependency_authority')
  try:
   tool.setUp();tool.populate();report=toolchain_tests.validate_artifact_directory(tool.root,catalog=tool.catalog)
   allowed={'BYTES_MATCH','UNVERIFIED','MISSING','SIZE_MISMATCH','DIGEST_MISMATCH'}
   statuses=[item['status'] for item in report['artifacts']];self.assertTrue(all(value in allowed for value in statuses))
   observations['toolchain_statuses']=statuses
   wheel.setUp();file=wheel.wheel();wheel.pin(file);report=wheel.report()
   reason=report.get('reason','NONE')
   # Only known public validator enums, no exception text or filenames.
   allowed_reasons={'NONE','LOCAL_FILE_CHANGED','LOCAL_FILE_UNVERIFIED','LOCAL_INPUT_UNVERIFIED','WHEEL_METADATA_INVALID','WHEEL_TAG_INVALID','ZIP_DIRECTORY_INVALID','ZIP_PATH_INVALID','ZIP_ENTRY_INVALID','WHEEL_HASH_MISMATCH','LOCK_INVALID'}
   observations['wheel_reason']=reason if reason in allowed_reasons else 'OTHER_PUBLIC_VALIDATION_REFUSAL'
  finally:tool.doCleanups();wheel.doCleanups()
  payload={'schema':'unified.ci-file-identity-observation.v1','python':platform.python_version(),'platform':os.name,'observation':observations,'qualification':'NOT_EVALUATED'}
  encoded=json.dumps(payload,sort_keys=True,separators=(',',':'))
  self.assertLess(len(encoded),1800)
  self.assertNotIn('identity-observation-',encoded)
  if os.environ.get('GITHUB_ACTIONS')=='true':print('::notice::NATIVE_FILE_IDENTITY '+encoded,flush=True)
