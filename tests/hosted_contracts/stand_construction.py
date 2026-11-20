"""Hosted metadata/private-journal role, never source/workload execution."""
import hashlib
import pathlib
import shutil
import sys
import tempfile
import unittest

class StandConstructionTests(unittest.TestCase):
 def test_actual_canonical_constructor_preserves_private_stand_obligations(self):
  from unified_system.gateway_target_adapter import DisposableTargetStand,TargetRejected
  from tools.physical_dev.bootstrap import allocate_stand_root
  git=pathlib.Path(shutil.which('git')).resolve(strict=True)
  runtime=pathlib.Path(sys.executable).resolve(strict=True)
  with tempfile.TemporaryDirectory(prefix='owned-stand-metadata-',dir=pathlib.Path(sys.pycache_prefix).parent) as directory:
   root=pathlib.Path(directory).resolve(strict=True)
   terminan=root/'terminan-source';terminan.mkdir()
   math=root/'math-source';math.mkdir()
   args=dict(terminan_source_root=str(terminan),math_source_root=str(math),git_executable=str(git),git_sha256=hashlib.sha256(git.read_bytes()).hexdigest(),runtime_sha256=hashlib.sha256(runtime.read_bytes()).hexdigest())
   with self.assertRaises(TargetRejected):DisposableTargetStand(str(root/'direct-state'),**args)
   state=allocate_stand_root(root)
   stand=DisposableTargetStand(str(state),**args)
   try:
    self.assertEqual(stand.invocations,0)
    self.assertTrue((state/'canonical-target.v2.sqlite').is_file())
   finally:stand.close()
   with self.assertRaises(FileExistsError):allocate_stand_root(root)
