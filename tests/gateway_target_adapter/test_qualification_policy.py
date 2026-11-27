"""Pure negative calibration: never launches the approved process fixture."""
import importlib.util,pathlib,sys,tempfile,unittest
SOURCE=pathlib.Path(__file__).resolve().parents[2]/'docs/intelligence/canonical-target/run_qualification.py'
SPEC=importlib.util.spec_from_file_location('canonical_qualification_policy',SOURCE)
POLICY=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(POLICY)
class QualificationPolicyTests(unittest.TestCase):
 def test_only_closed_owned_crash_command_can_be_admitted(self):
  with tempfile.TemporaryDirectory(prefix='target-own-crash-') as owned:
   root=pathlib.Path(owned)/'source';term=pathlib.Path(owned)/'term';math=pathlib.Path(owned)/'math';cache=pathlib.Path(owned)/'cache'
   args=dict(enabled=True,root=root,terminan_root=term,math_root=math,cache=cache)
   command=[sys.executable,'-I','-S','-B','-X','pycache_prefix='+str(cache),str(root/'tests/gateway_target_adapter/crash_child.py'),str(root),owned,str(term),str(math),'BEFORE']
   self.assertTrue(POLICY.fixed_crash_command(command,sys.executable,**args))
   self.assertFalse(POLICY.fixed_crash_command(command,sys.executable,**dict(args,enabled=False)))
   for index,value in ((0,'foreign.exe'),(1,'-c'),(5,'pycache_prefix=foreign'),(6,str(root/'foreign.py')),(7,str(term)),(8,str(pathlib.Path(owned).parent)),(9,str(root)),(10,str(root)),(11,'OTHER')):
    with self.subTest(index=index):
     bad=list(command);bad[index]=value;self.assertFalse(POLICY.fixed_crash_command(bad,sys.executable,**args))
   self.assertFalse(POLICY.fixed_crash_command(command,'foreign.exe',**args))
   self.assertFalse(POLICY.fixed_crash_command(command+['extra'],sys.executable,**args))
   pathlib.Path(owned,'unapproved-payload').write_bytes(b'x')
   self.assertFalse(POLICY.fixed_crash_command(command,sys.executable,**args))
if __name__=='__main__':unittest.main()
