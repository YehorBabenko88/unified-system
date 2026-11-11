"""Independent deterministic metadata-cache diagnosis; product gate unchanged."""
import hashlib,importlib,importlib.util,json,os,pathlib,subprocess,tempfile,unittest,io
r=pathlib.Path(__file__).resolve().parents[1];out=r/'outputs/phase32';out.mkdir(exist_ok=True);seed=r/'work/review-integration75';sha='b8922714b99169c22ae6c14fdbc1c5a5f6c1d0f7';p=r/'work/review-causal-fixture'
def git(*args):return subprocess.check_output(['git','--no-replace-objects','-C',str(seed),*args])
assert not p.exists();subprocess.run(['git','clone','--no-hardlinks','--no-checkout',str(seed),str(p)],check=True,capture_output=True);subprocess.run(['git','-C',str(p),'-c','core.autocrlf=false','-c','core.eol=lf','checkout','--detach',sha],check=True,capture_output=True)
assert git('show',sha+':scripts/ci_paper_causal.py')==git('show',sha+'^:scripts/ci_paper_causal.py')
spec=importlib.util.spec_from_file_location('_a8_causal_gate',p/'scripts/ci_paper_causal.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
results=[]
for i in range(10):
 with tempfile.TemporaryDirectory(dir=r/'work',prefix='a8-metadata-cache-') as temp:
  path=pathlib.Path(temp);s=path.stat()
  try:m.dependencies_snapshot(path)
  except m.GateRejected:pass
  else:raise AssertionError('missing dependencies admitted')
  for name,version in m.TEST_DEPENDENCIES.items():
   info=path/(name+'-'+version+'.dist-info');info.mkdir();(info/'METADATA').write_text('Metadata-Version: 2.1\nName: '+name+'\nVersion: '+version+'\n')
  os.utime(path,ns=(s.st_atime_ns,s.st_mtime_ns))
  try:m.dependencies_snapshot(path)
  except m.GateRejected as e:assert str(e)=='TEST_DEPENDENCY_VERSION_REJECTED'
  else:raise AssertionError('stale metadata RED did not reproduce')
  importlib.invalidate_caches();assert m.dependencies_snapshot(path)['versions']==m.TEST_DEPENDENCIES
  (path/'preload.pth').write_text('import forbidden')
  try:m.dependencies_snapshot(path)
  except m.GateRejected as e:assert str(e)=='TEST_DEPENDENCY_PRELOAD_REJECTED'
  else:raise AssertionError('pth preload admitted')
  results.append(dict(stale_mtime_red=True,invalidated_cache_green=True,pth_rejected=True))
spec=importlib.util.spec_from_file_location('_a8_causal_tests',p/'tests/test_ci_paper_causal.py');test=importlib.util.module_from_spec(spec);spec.loader.exec_module(test);suite=unittest.defaultTestLoader.loadTestsFromModule(test);stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite);(out/'corrected-module-tests.log').write_text(stream.getvalue());assert result.wasSuccessful() and result.testsRun==7 and not result.skipped
for item in filter(None,git('ls-tree','-rz',sha).split(b'\0')):
 meta,name=item.split(b'\t',1);raw=(p/name.decode()).read_bytes();assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==meta.split()[2].decode()
report=dict(head=sha,tree=git('rev-parse',sha+'^{tree}').decode().strip(),product_gate_unchanged=True,controlled_repeats=results,module_tests=7,skips=0,environment='Windows Python3.12 isolated test metadata',scope='FIXTURE_CACHE_INVALIDATION_ONLY_NOT_PR30_FULL_SUITE_PASS',overall='NO_GO');(out/'causal-fixture-review.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='controlled_repeats'}))
