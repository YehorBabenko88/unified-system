"""Installed offline causal tests; SQLite/writes only in fresh private cases.
No provider/socket/child/native/service grant; parent source fences still required.
"""
import argparse,hashlib,importlib.metadata,importlib.util,json,os,pathlib,re,sys,tempfile,unittest

def require_interpreter(flags):
 if not(flags.isolated and flags.no_site and flags.dont_write_bytecode):raise ValueError('ISOLATED_NO_SITE_CAUSAL_REQUIRED')

def check_sdk_bindings(site,bindings):
 owners=set()
 for relative,record in bindings.items():
  expected='math' if relative in ('market_math.py','market_compute_api.py','history_statistics.py') else 'market_data' if relative.startswith('market_data/') else 'terminan' if relative.startswith('terminan/') else None
  if expected is None or relative.endswith(('.pth','.pyc','.pyo')) or record['owner']!=expected:raise ValueError('SDK_PACKAGE_OWNER_OR_PRELOAD_REJECTED')
  file=(site/relative).resolve()
  if not file.is_relative_to(site) or hashlib.sha256(file.read_bytes()).hexdigest()!=record['sha256']:raise ValueError('SDK_BYTES_OR_ORIGIN_REJECTED')
  owners.add(expected)
 if owners!={'math','market_data','terminan'}:raise ValueError('THREE_DOMAIN_WHEELS_REQUIRED')

def check_sdk_metadata(site):
 for name in ('market-data','unified-terminan','unified-math-kernels'):
  try:dist=importlib.metadata.distribution(name)
  except importlib.metadata.PackageNotFoundError:raise ValueError('SDK_METADATA_UNAVAILABLE') from None
  if dist.metadata.get('Name')!=name or dist.version!='0.1.0' or pathlib.Path(dist.locate_file('')).resolve()!=site:raise ValueError('SDK_METADATA_VERSION_OR_ORIGIN_REJECTED')

def main():
 p=argparse.ArgumentParser()
 for name in ('root','site','bindings','root-bindings','out','cache'):p.add_argument('--'+name,required=True)
 p.add_argument('--suite',choices=('causal',),required=True);args=p.parse_args()
 require_interpreter(sys.flags)
 root=pathlib.Path(args.root).resolve();site=pathlib.Path(args.site).resolve();out=pathlib.Path(args.out).resolve();cases=out/'cases'
 if out.is_relative_to(root) or out.is_relative_to(site) or cases.exists():raise ValueError('FRESH_EXTERNAL_CAUSAL_CASE_ROOT_REQUIRED')
 for parent in (out,*out.parents):
  if parent.is_symlink() or getattr(parent.lstat(),'st_file_attributes',0)&1024:raise ValueError('CAUSAL_EVIDENCE_ALIAS')
 cases.mkdir();tempfile.tempdir=str(cases)
 bindings=json.loads(pathlib.Path(args.bindings).read_bytes());root_bindings=json.loads(pathlib.Path(args.root_bindings).read_bytes())
 helper_path=root/'integration/four_owner/import_custody.py';helper_raw=helper_path.read_bytes()
 if hashlib.sha256(helper_raw).hexdigest()!=root_bindings['integration/four_owner/import_custody.py']:raise ValueError('IMPORT_CUSTODY_RAW_ROOT_BINDING_REJECTED')
 custody={'__name__':'raw_import_custody','__file__':str(helper_path)}
 exec(compile(helper_raw,str(helper_path),'exec',dont_inherit=True),custody)
 cache_state=custody['begin'](pathlib.Path(args.cache),(root,site,cases))
 check_sdk_bindings(site,bindings)
 def target(raw,dir_fd=None):
  path=pathlib.Path(raw)
  if not path.is_absolute() and dir_fd is not None and dir_fd!=-1:
   if os.name!='posix':raise RuntimeError('CAUSAL_UNRESOLVED_DIR_FD')
   path=pathlib.Path('/proc/self/fd/'+str(dir_fd)).resolve()/path
  return path.resolve()
 def private(raw,dir_fd=None):
  if type(raw) is int:return
  file=target(raw,dir_fd)
  if not file.is_relative_to(cases) and file!=out/'installed-tests.json':raise RuntimeError('CAUSAL_WRITE_OUTSIDE_PRIVATE_CASES')
 def audit(event,values):
  if event.startswith(('socket.','subprocess.','ctypes.','os.exec','os.spawn')) or event in ('os.system','os.startfile','os.fork','os.kill'):raise RuntimeError('CAUSAL_EFFECT_FORBIDDEN:'+event)
  if event=='sqlite3.connect':
   raw=str(values[0]);from urllib.parse import urlsplit,unquote
   parsed=urlsplit(raw) if raw.startswith('file:') else None
   if parsed is not None and parsed.netloc:raise RuntimeError('CAUSAL_NONPRIVATE_SQLITE')
   file=unquote(parsed.path) if parsed else raw
   if parsed and os.name=='nt':file=file.lstrip('/')
   if not target(file).is_relative_to(cases):raise RuntimeError('CAUSAL_NONPRIVATE_SQLITE')
  if event=='open':
   raw,mode,flags=values
   if isinstance(mode,str) and any(c in mode for c in 'wax+') or flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):private(raw)
  if event in ('os.mkdir','os.remove','os.rmdir'):private(values[0],values[2] if event=='os.mkdir' else values[1])
  if event in ('os.rename','os.link'):
   private(values[0],values[2]);private(values[1],values[3])
  if event=='shutil.rmtree':private(values[0],values[1] if len(values)>1 else None)
 sys.addaudithook(audit)
 cache_control=custody['controlled_probe'](cases/'bytecode-control',cache_state)
 sys.path[:0]=[str(site),str(root),str(root/'tests/causal_offline')]
 for old in ('grid','strattester','meta_analyse','market_profile_math'):
  if importlib.util.find_spec(old) is not None:raise ValueError('RETIRED_IMPORT_AVAILABLE')
 check_sdk_metadata(site)
 from scripts.ci_paper_causal import EXPECTED_IDS,CausalResult,require_inventory,require_success,GateRejected
 suite=unittest.defaultTestLoader.loadTestsFromName('test_offline_causal_pipeline')
 def ids(s):
  for test in s:
   if isinstance(test,unittest.TestSuite):yield from ids(test)
   else:yield test.id()
 actual=list(ids(suite));require_inventory(actual)
 result=unittest.TextTestRunner(verbosity=2,resultclass=CausalResult).run(suite)
 passed=True
 try:require_success(result,EXPECTED_IDS)
 except GateRejected:passed=False
 origins={}
 for name,module in tuple(sys.modules.items()):
  raw=getattr(module,'__file__',None);top=name.split('.')[0]
  if top in ('market_data','terminan','market_math','market_compute_api','history_statistics'):
   file=pathlib.Path(raw).resolve();relative=file.relative_to(site).as_posix()
   if relative not in bindings or hashlib.sha256(file.read_bytes()).hexdigest()!=bindings[relative]['sha256']:raise ValueError('SDK_LOADED_ORIGIN_REJECTED')
   origins[name]=dict(file=str(file),source=bindings[relative])
  elif top in ('unified_system','integration','scripts') or name=='test_offline_causal_pipeline':
   if raw is None:
    if any(not pathlib.Path(v).resolve().is_relative_to(root) for v in module.__path__):raise ValueError('ROOT_NAMESPACE_ORIGIN')
    continue
   file=pathlib.Path(raw).resolve();relative=file.relative_to(root).as_posix()
   if relative not in root_bindings or hashlib.sha256(file.read_bytes()).hexdigest()!=root_bindings[relative]:raise ValueError('ROOT_LOADED_ORIGIN_REJECTED')
   origins[name]=dict(file=str(file),root_runtime_sha256=root_bindings[relative])
 check_sdk_bindings(site,bindings);check_sdk_metadata(site)
 cache_origins=custody['verify_loaded'](cache_state,root,site)
 report=dict(schema='unified.offline-causal.installed-tests.v1',status='PASS_SCOPED' if passed else 'FAIL',scope='SYNTHETIC_INSTALLED_SDK_PRIVATE_SQLITE_STORE_JOURNAL_ONLY',tests=result.testsRun,case_ids=actual,started=result.started,finished=result.finished,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),expected_failures=len(result.expectedFailures),unexpected_successes=len(result.unexpectedSuccesses),module_origins=origins,unchecked_hash_control=cache_control,import_cache_origins=cache_origins,import_cache_policy='FRESH_EXTERNAL_CLI_PREFIX_NO_PRELOADED_APP_EMPTY_PRE_POST',private_case_root=str(cases),actual_private_sqlite=True,actual_process=False,source_fences='PARENT_REQUIRED_NOT_EVALUATED_BY_CHILD',source_authenticity='NOT_EVALUATED',point_in_time_availability='UNKNOWN',publication_confirmed=False,native_commit='NOT_ATTEMPTED',native_installation='NOT_RUN',physical='NOT_RUN',release_status='NO_GO',execution_authority=False,trading_authorized=False)
 (out/'installed-tests.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n',encoding='utf8');return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
