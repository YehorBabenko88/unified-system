"""Injected Win32 API semantics plus actual local-reader regressions; not native proof."""
import copy
from pathlib import Path
import tempfile
import unittest

class Backend:
 def __init__(self):
  self.value=dict(file_type=1,volume=123,file_id=bytes(range(1,17)),links=1,size=42,creation=100,write=200,change=300,attributes=32,directory=False,delete_pending=False)
  self.closed=[];self.opened=[]
 def handle_from_fd(self,fd):return fd
 def open_path(self,path,access,sharing,flags):self.opened.append((path,access,sharing,flags));return 99
 def query(self,handle):return copy.deepcopy(self.value)
 def close(self,handle):self.closed.append(handle)

class FileIdentityTests(unittest.TestCase):
 def test_full_128bit_identity_and_change_times_are_preserved(self):
  from unified_system.file_identity import _windows_descriptor_identity
  backend=Backend();before=_windows_descriptor_identity(7,api=backend)
  for field,value in [('file_id',backend.value['file_id'][:8]+b'changed!'),('volume',124),('size',43),('creation',101),('write',201),('change',301)]:
   mutated=Backend();mutated.value[field]=value
   with self.subTest(field=field):self.assertNotEqual(before,_windows_descriptor_identity(7,api=mutated))
  self.assertEqual(backend.closed,[],'borrowed descriptor handle must not close')
 def test_fresh_path_handle_is_no_follow_and_closed_on_success_or_refusal(self):
  from unified_system.file_identity import _windows_path_identity,_windows_descriptor_identity
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'inert';path.write_bytes(b'owned')
   backend=Backend();self.assertEqual(_windows_path_identity(path,api=backend),_windows_descriptor_identity(7,api=backend))
   self.assertEqual(backend.closed,[99]);self.assertEqual(backend.opened[0][1:3],(0x80,7))
   self.assertTrue(backend.opened[0][3]&0x00200000)
   for field,value in [('links',2),('file_id',bytes(16)),('volume',0),('attributes',0x400),('directory',True),('delete_pending',True),('file_type',3)]:
    rejected=Backend();rejected.value[field]=value
    with self.subTest(field=field),self.assertRaises(ValueError):_windows_path_identity(path,api=rejected)
    self.assertEqual(rejected.closed,[99])
 def test_external_namespace_is_denied_before_any_path_or_handle_probe(self):
  from unified_system.file_identity import _windows_path_identity
  from unittest.mock import patch
  backend=Backend()
  with patch.object(Path,'lstat',side_effect=AssertionError('metadata probed')):
   with self.assertRaises(ValueError):_windows_path_identity('//office.invalid/data',api=backend)
  self.assertEqual(backend.opened,[])
 def test_actual_replaced_path_and_same_descriptor_are_distinguishable(self):
  from unified_system.file_identity import path_identity,descriptor_identity
  import os
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'inert';path.write_bytes(b'owned');fd=os.open(path,os.O_RDONLY)
   try:
    before=descriptor_identity(fd);self.assertEqual(before,path_identity(path))
    # Different existing path is a different identity; no unsafe native swap.
    other=Path(d)/'other';other.write_bytes(b'owned')
    self.assertNotEqual(before,path_identity(other))
    self.assertEqual(before,descriptor_identity(fd))
   finally:os.close(fd)
 def test_validators_use_authoritative_handles_not_mixed_ctime_representations(self):
  import os,stat
  from types import SimpleNamespace
  from unittest.mock import patch
  from unified_system import windows_wheels as wheels,windows_toolchain as tools
  from unified_system.file_identity import _windows_path_identity,_windows_descriptor_identity
  from tests import test_windows_wheels as wheel_tests,test_windows_toolchain as tool_tests
  class RealFilesBackend(Backend):
   def open_path(self,path,access,sharing,flags):
    self.opened.append((path,access,sharing,flags));return os.open(path,os.O_RDONLY)
   def close(self,handle):self.closed.append(handle);os.close(handle)
   def query(self,handle):
    facts=os.fstat(handle)
    return dict(file_type=1,volume=facts.st_dev or 1,file_id=facts.st_ino.to_bytes(16,'little'),links=facts.st_nlink,size=facts.st_size,creation=100,write=facts.st_mtime_ns,change=facts.st_ctime_ns,attributes=32,directory=stat.S_ISDIR(facts.st_mode),delete_pending=False)
  backend=RealFilesBackend();lstat=Path.lstat
  def creation_time_stat(path,*args,**kwargs):
   facts=lstat(path,*args,**kwargs);fields={key:getattr(facts,key) for key in dir(facts) if key.startswith('st_')}
   fields['st_ctime_ns']=facts.st_ctime_ns-100
   return SimpleNamespace(**fields)
  wheel=wheel_tests.WindowsWheelTests();tool=tool_tests.ToolchainTests()
  try:
   wheel.setUp();file=wheel.wheel();wheel.pin(file);tool.setUp();tool.populate()
   with patch.object(Path,'lstat',creation_time_stat), \
        patch.object(wheels,'path_identity',side_effect=lambda p:_windows_path_identity(p,api=backend)), \
        patch.object(wheels,'descriptor_identity',side_effect=lambda fd:_windows_descriptor_identity(fd,api=backend)), \
        patch.object(tools,'path_identity',side_effect=lambda p:_windows_path_identity(p,api=backend)), \
        patch.object(tools,'descriptor_identity',side_effect=lambda fd:_windows_descriptor_identity(fd,api=backend)):
    with file.open('rb') as stream:self.assertNotEqual(file.lstat().st_ctime_ns,os.fstat(stream.fileno()).st_ctime_ns)
    self.assertEqual(wheel.report()['result'],'CANDIDATE_BYTES_MATCH')
    self.assertTrue(tools.validate_artifact_directory(tool.root,catalog=tool.catalog)['all_locked_artifacts_match'])
   self.assertTrue(backend.opened);self.assertEqual(len(backend.opened),len(backend.closed))
   # Same bytes at another file ID cannot replace the pathname binding.
   replacement=wheel.root/'replacement.whl';replacement.write_bytes(file.read_bytes())
   class SwappedPathBackend(RealFilesBackend):
    wheel_opens=0
    def open_path(self,path,access,sharing,flags):
     if Path(path)==file:
      self.wheel_opens+=1
      if self.wheel_opens>=2:path=str(replacement)
     return super().open_path(path,access,sharing,flags)
   class ChangedHandleBackend(RealFilesBackend):
    observations=0
    def handle_from_fd(self,fd):return ('borrowed',fd)
    def query(self,handle):
     if isinstance(handle,tuple):
      result=super().query(handle[1]);self.observations+=1
      if self.observations>=2:result['change']+=1
      return result
     return super().query(handle)
   for kind in (SwappedPathBackend,ChangedHandleBackend):
    backend=kind()
    with self.subTest(native_case=kind.__name__),patch.object(wheels,'path_identity',side_effect=lambda p:_windows_path_identity(p,api=backend)),patch.object(wheels,'descriptor_identity',side_effect=lambda fd:_windows_descriptor_identity(fd,api=backend)):
     self.assertEqual(wheel.report()['result'],'BLOCKED')
    self.assertEqual(len(backend.opened),len(backend.closed))
  finally:wheel.doCleanups();tool.doCleanups()
 def test_hardlink_added_between_lstat_and_stamp_is_refused_by_both_readers(self):
  import os
  from unittest.mock import patch
  from unified_system import windows_wheels as wheels,windows_toolchain as tools
  from unified_system.file_identity import path_identity
  from tests import test_windows_wheels as wheel_tests,test_windows_toolchain as tool_tests
  wheel=wheel_tests.WindowsWheelTests();tool=tool_tests.ToolchainTests()
  try:
   wheel.setUp();file=wheel.wheel();wheel.pin(file);tool.setUp();tool.populate()
   for module,target in ((wheels,file),(tools,tool.root/tool.catalog['artifacts'][0]['filename'])):
    linked=target.parent/'link-race';done=[]
    def racing(path):
     if Path(path)==target and not done:os.link(target,linked);done.append(True)
     return path_identity(path)
    try:
     with self.subTest(reader=module.__name__),patch.object(module,'path_identity',side_effect=racing):
      if module is wheels:self.assertEqual(wheel.report()['result'],'BLOCKED')
      else:self.assertEqual(tools.validate_artifact_directory(tool.root,catalog=tool.catalog)['artifacts'][0]['status'],'UNVERIFIED')
     self.assertTrue(done)
    finally:linked.unlink(missing_ok=True)
  finally:wheel.doCleanups();tool.doCleanups()
