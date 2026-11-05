import json,os,subprocess,sys,tempfile,unittest
from pathlib import Path

class OwnedCallbackTests(unittest.TestCase):
 def test_callback_runs_after_same_isolation_without_executing_module(self):
  bootstrap=Path(__file__).resolve().parents[1]/'unified_system/owned_python.py'
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary).resolve();cache=root/'cache';cache.mkdir(mode=0o700)
   package=root/'demo';package.mkdir();(package/'__init__.py').write_text('')
   (package/'app.py').write_text("raise RuntimeError('module must not execute')")
   driver=root/'driver.py'
   driver.write_text("import sys,json,runpy;ns=runpy.run_path("+repr(str(bootstrap))+");sys.argv=['owned','--source-root',"+repr(str(root))+",'--module','demo.app'];result=ns['main'](admitted_run=lambda: (print(json.dumps(dict(cache=sys.pycache_prefix,flags=[sys.flags.isolated,sys.flags.no_site,sys.dont_write_bytecode]))),17)[1]);raise SystemExit(result)")
   env=dict(os.environ,UNIFIED_MODULE_ID='strattester',UNIFIED_MODULE_VERSION='1.0.0',UNIFIED_RELEASE_ID='lab',UNIFIED_INSTANCE_TOKEN='a'*64,UNIFIED_PRIVATE_CACHE_ROOT=str(cache))
   result=subprocess.run([sys.executable,'-I','-S','-B',str(driver)],env=env,capture_output=True,text=True,timeout=15)
   self.assertEqual(result.returncode,17,result.stderr);value=json.loads(result.stdout)
   self.assertEqual(value['flags'],[1,1,True]);self.assertTrue(Path(value['cache']).is_relative_to(cache))
