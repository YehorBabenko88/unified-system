import importlib.util
from pathlib import Path
import sys,tempfile,unittest
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
class BootstrapTests(unittest.TestCase):
 def api(self):
  path=ROOT/'scripts/bootstrap_ci_unittest.py';self.assertTrue(path.is_file(),'isolated full-discovery launcher required');spec=importlib.util.spec_from_file_location('inert_ci_bootstrap_fixture',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 def test_command_uses_real_startup_flags_and_explicit_dependency_path(self):
  m=self.api()
  with tempfile.TemporaryDirectory() as d:
   base=Path(d);deps=base/'deps';deps.mkdir();cmd=m.build_command(sys.executable,ROOT/'scripts/ci_unittest.py',deps,base/'cache')
   self.assertEqual(cmd[1:5],['-I','-S','-B','-X']);self.assertEqual(cmd[5],'pycache_prefix='+str(base/'cache'));self.assertIn('sys.path.append',cmd[7]);self.assertEqual(cmd[-2:],[str(ROOT/'scripts/ci_unittest.py'),str(deps)])
 def test_existing_cache_and_source_dependency_paths_refuse_before_launch(self):
  m=self.api()
  with tempfile.TemporaryDirectory() as d:
   base=Path(d);deps=base/'deps';deps.mkdir();cache=base/'cache';cache.mkdir()
   with self.assertRaises(ValueError):m.build_command(sys.executable,ROOT/'scripts/ci_unittest.py',deps,cache)
   with self.assertRaises(ValueError):m.build_command(sys.executable,ROOT/'scripts/ci_unittest.py',ROOT,base/'unused')
 def test_launcher_preserves_child_status_and_owned_temporary_cleanup(self):
  m=self.api();commands=[]
  with tempfile.TemporaryDirectory() as d,patch.object(m.subprocess,'run',side_effect=lambda cmd,**kw:(commands.append((cmd,kw)) or SimpleNamespace(returncode=7))):
   self.assertEqual(m.run_suite(Path(d)),7)
  self.assertEqual(len(commands),1);self.assertNotIn('shell',commands[0][1]);cache=Path(commands[0][0][5].split('=',1)[1]);self.assertFalse(cache.parent.exists())
 def test_tests_package_has_real_file_origin_not_namespace_exception(self):
  p=ROOT/'tests/__init__.py';self.assertTrue(p.is_file());spec=importlib.util.spec_from_file_location('inert_root_tests_package',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);self.assertEqual(Path(m.__file__),p);self.assertEqual(Path(m.__spec__.origin),p)
 def test_all_workflow_full_discovery_callers_use_the_launcher(self):
  for name in ('owner-boundary','tests','lifecycle-evidence','installer-security'):
   text=(ROOT/'.github/workflows'/(name+'.yml')).read_text();self.assertIn('bootstrap_ci_unittest.py',text);self.assertNotIn('python scripts/ci_unittest.py',text);self.assertNotIn("[sys.executable,'scripts/ci_unittest.py']",text)
 def test_declared_lock_includes_pinned_missing_imports(self):
  text=(ROOT/'docs/ci/requirements-unittest.lock').read_text();self.assertIn('httpx==0.28.1',text);self.assertIn('pytest==9.0.3',text);self.assertIn('colorama==0.4.6',text);self.assertIn('sys_platform',text)
if __name__=='__main__':unittest.main()
