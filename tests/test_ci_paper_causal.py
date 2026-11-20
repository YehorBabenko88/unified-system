"""Adversarial tests for the actual canonical causal builder/runner gates.
The real Git fixture remains mandatory hosted; local pure runs select other cases.
"""
import importlib.util,importlib,json,os,pathlib,subprocess,sys,tempfile,unittest,hashlib
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
def load(relative,name):
 spec=importlib.util.spec_from_file_location(name,ROOT/relative);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
class CausalGateTests(unittest.TestCase):
 def module(self):return load('scripts/ci_paper_causal.py','canonical_paper_gate')
 def test_closed_inventory_has_exact_sixteen_unique_cases(self):
  m=self.module();self.assertEqual(len(m.ROLE_IDS),16);self.assertEqual(len(set(m.ROLE_IDS)),16);self.assertEqual(len(m.EXPECTED_IDS),21);self.assertTrue(set(m.ROLE_IDS)<=set(m.EXPECTED_IDS))
  for bad in (list(m.EXPECTED_IDS)[:-1],list(m.EXPECTED_IDS)+[m.EXPECTED_IDS[0]]):
   with self.assertRaises(m.GateRejected):m.require_inventory(bad)
  m.require_inventory(list(reversed(m.EXPECTED_IDS)))
 def test_any_skip_or_missing_started_case_rejects_success(self):
  m=self.module()
  class Case(unittest.TestCase):
   def runTest(self):self.skipTest('mandatory dependency absent')
  result=m.CausalResult();Case().run(result)
  with self.assertRaises(m.GateRejected):m.require_success(result,('probe',))
  for field in ('expectedFailures','unexpectedSuccesses'):
   result=m.CausalResult();result.testsRun=1;result.started=['probe'];result.finished=['probe'];getattr(result,field).append(('probe','refusal'))
   with self.assertRaises(m.GateRejected):m.require_success(result,('probe',))
  result=m.CausalResult();result.testsRun=len(m.EXPECTED_IDS)
  with self.assertRaises(m.GateRejected):m.require_success(result,m.EXPECTED_IDS)
 def test_actual_failure_cannot_be_reported_as_pass(self):
  m=self.module()
  class Case(unittest.TestCase):
   def runTest(self):self.fail('negative assertion')
  case=Case();result=m.CausalResult();case.run(result)
  with self.assertRaises(m.GateRejected):m.require_success(result,(case.id(),))
 def test_source_snapshot_proves_origin_head_cleanliness_and_raw_bytes(self):
  from integration.source_guard import SourceFence
  q=self.module().builder()
  with tempfile.TemporaryDirectory() as tmp:
   base=pathlib.Path(tmp);root=base/'candidate';root.mkdir();cache=base/'cache';cache.mkdir()
   def git(*args):return subprocess.check_output(['git','--no-replace-objects','-c','core.hooksPath='+str(base/'no-hooks'),'-c','commit.gpgsign=false','-C',str(root),*args],text=True).strip()
   git('init');git('config','user.name','Synthetic');git('config','user.email','synthetic@example.invalid');git('config','core.autocrlf','false');git('remote','add','origin','https://github.com/YehorBabenko88/Terminan.git');(root/'tracked.py').write_bytes(b'first\n');git('add','tracked.py');git('commit','-m','synthetic');head=git('rev-parse','HEAD')
   old_cache=sys.pycache_prefix
   try:
    sys.pycache_prefix=str(cache);fence=SourceFence(root,head,isolated_cache=cache);one=fence.check();self.assertEqual(one['head'],head);q.require_source_origin(fence,'YehorBabenko88/Terminan')
    with self.assertRaises(ValueError):q.require_source_origin(fence,'YehorBabenko88/strattester')
    with self.assertRaises(ValueError):SourceFence(root,'a'*40,isolated_cache=cache).check()
    (root/'tracked.py').write_bytes(b'changed\n')
    with self.assertRaises(ValueError):fence.finish()
    git('checkout','--','tracked.py');(root/'injected.py').write_bytes(b'pass\n')
    with self.assertRaises(ValueError):SourceFence(root,head,isolated_cache=cache).check()
   finally:sys.pycache_prefix=old_cache
 def test_output_must_be_outside_every_source_checkout(self):
  q=self.module().builder()
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp)/'repo';root.mkdir()
   for out in (root,root/'evidence'):
    with self.assertRaises(ValueError):q.require_external_output(out,[root])
   q.require_external_output(pathlib.Path(tmp)/'evidence',[root])
 def test_source_change_after_tests_rejects_qualification(self):
  q=self.module().builder();finished=[]
  class Fence:
   def __init__(self,root,*a,**kw):self.root=root;self.before=None
   def check(self):self.before={};return self.before
   def module(self,*a,**kw):pass
   def file(self,*a,**kw):pass
   def finish(self):finished.append(self.root);raise ValueError('CHANGED_SOURCE')
  with tempfile.TemporaryDirectory() as tmp:
   base=pathlib.Path(tmp);root=base/'root';root.mkdir();out=base/'evidence';cohort=json.loads((ROOT/'integration/four_owner/cohort.json').read_bytes());(root/'cohort.json').write_text(json.dumps(cohort));cache=sys.pycache_prefix;paths=list(sys.path)
   try:
    q.ROOT=root
    with patch.dict(os.environ,{'GITHUB_ACTIONS':'true','RUNNER_ENVIRONMENT':'github-hosted'}),patch('integration.source_guard.SourceFence',Fence),patch.object(q.venv,'EnvBuilder') as builder,patch.object(q,'call',side_effect=ValueError('BEFORE_ANY_CHILD')):
     builder.return_value.create.return_value=None
     with self.assertRaisesRegex(ValueError,'SOURCE_POSTCHECK_FAILED'):q.main(['--root-head','a'*40,'--market-data',str(base/'data'),'--math',str(base/'math'),'--terminan',str(base/'term'),'--out',str(out)],cohort_file='cohort.json')
    report=json.loads((out/'evidence.json').read_bytes());self.assertEqual(report['qualification'],'FAIL');self.assertEqual(len(finished),4);self.assertEqual(len(report['source_post_errors']),4)
   finally:sys.pycache_prefix=cache;sys.path[:]=paths
 def test_isolated_test_dependencies_reject_missing_version_or_pth_preload(self):
  runner=load('integration/four_owner/run_causal_installed.py','causal_runner')
  from types import SimpleNamespace
  with self.assertRaises(ValueError):runner.require_interpreter(SimpleNamespace(isolated=1,no_site=0,dont_write_bytecode=1))
  with tempfile.TemporaryDirectory() as tmp:
   site=pathlib.Path(tmp);bindings={}
   for name,owner in (('market_math.py','math'),('market_data/__init__.py','market_data'),('terminan/__init__.py','terminan')):
    p=site/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'# inert metadata fixture\n');bindings[name]=dict(owner=owner,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
   runner.check_sdk_bindings(site,bindings)
   with self.assertRaises(ValueError):runner.check_sdk_metadata(site)
   bad=dict(bindings);bad['preload.pth']=dict(owner='math',sha256='a'*64)
   with self.assertRaises(ValueError):runner.check_sdk_bindings(site,bad)
   for name in ('market-data','unified-terminan','unified-math-kernels'):
    folder=site/(name.replace('-','_')+'-0.1.0.dist-info');folder.mkdir();(folder/'METADATA').write_text('Metadata-Version: 2.1\nName: '+name+'\nVersion: 0.1.0\n')
   old=list(sys.path)
   try:
    sys.path.insert(0,str(site));importlib.invalidate_caches();runner.check_sdk_metadata(site)
    (site/'market_data-0.1.0.dist-info/METADATA').write_text('Metadata-Version: 2.1\nName: wrong-owner\nVersion: 0.1.0\n');importlib.invalidate_caches()
    with self.assertRaises(ValueError):runner.check_sdk_metadata(site)
    (site/'market_data-0.1.0.dist-info/METADATA').write_text('Metadata-Version: 2.1\nName: market-data\nVersion: 0.1.0\n')
    (site/'unified_math_kernels-0.1.0.dist-info/METADATA').write_text('Metadata-Version: 2.1\nName: unified-math-kernels\nVersion: 9\n');importlib.invalidate_caches()
    with self.assertRaises(ValueError):runner.check_sdk_metadata(site)
   finally:sys.path[:]=old
if __name__=='__main__':unittest.main()
