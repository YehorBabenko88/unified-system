"""Strict inert installed-SDK tests; never a native/SQL/process acceptance."""
import argparse,hashlib,importlib.metadata,importlib.util,json,pathlib,sys,types,unittest

def main():
 parser=argparse.ArgumentParser()
 for key in ('root','site','bindings','root-bindings','out'):parser.add_argument('--'+key,required=True)
 parser.add_argument('--suite',choices=('all','chain','history','handoff','provenance'),default='all')
 args=parser.parse_args();root=pathlib.Path(args.root).resolve();site=pathlib.Path(args.site).resolve();out=pathlib.Path(args.out).resolve()
 if not (sys.flags.isolated and sys.dont_write_bytecode):raise ValueError('ISOLATED_INSTALLED_PROFILE_REQUIRED')
 bindings=json.loads(pathlib.Path(args.bindings).read_bytes())
 root_bindings=json.loads(pathlib.Path(args.root_bindings).read_bytes())
 for relative,record in bindings.items():
  path=site/relative
  if not path.resolve().is_relative_to(site) or hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:raise ValueError('INSTALLED_SOURCE_BYTES_MISMATCH')
 def audit(event,values):
  if event.startswith(('socket.','subprocess.','ctypes.','os.exec','os.spawn')) or event in ('os.system','os.startfile','os.fork','os.kill','sqlite3.connect'):raise RuntimeError('PURE_COHORT_EFFECT_FORBIDDEN:'+event)
 sys.addaudithook(audit)
 # Root driver imports ctypes at module scope on Windows. This import-shape
 # substitute REFUSES every native attribute; it cannot prove PID/custody/PKI.
 shape=types.ModuleType('ctypes');shape.__file__='<REFUSING_IMPORT_SHAPE_ONLY>';shape.__path__=[]
 def refuse(name):raise RuntimeError('NATIVE_OPERATION_NOT_QUALIFIED:'+name)
 shape.__getattr__=refuse;sys.modules['ctypes']=shape
 sys.path[:0]=[str(site),str(root),str(root/'tests'),str(root/'tests/four_owner')]
 for old in ('grid','strattester','meta_analyse','market_profile_math'):
  if importlib.util.find_spec(old) is not None:raise ValueError('RETIRED_IMPORT_AVAILABLE')
 from integration.four_owner.contracts import require_cases,result_complete
 expected=json.loads((root/'integration/four_owner/EXPECTED-TESTS.json').read_bytes())
 if args.suite!='all':
  group={'chain':('test_exact_data_trade','test_data_first_seen','test_actual_data_profile','test_paper_owner','test_nonatomic_ledger','test_archive_'),'history':('test_actual_data_history','test_history_tamper'),'handoff':('test_canonical_handoff',),'provenance':('test_canonical_handoff','test_history_tamper')}[args.suite]
  expected=[name for name in expected if any(name.rsplit('.',1)[1].startswith(prefix) for prefix in group)]
 suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in expected)
 def ids(value):
  for item in value:
   if isinstance(item,unittest.TestSuite):yield from ids(item)
   else:yield item.id()
 actual=require_cases(list(ids(suite)),expected)
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 origins={}
 for name,module in tuple(sys.modules.items()):
  package=name.split('.')[0]
  if package in ('market_data','terminan','market_math','market_compute_api','history_statistics'):
   path=pathlib.Path(module.__file__).resolve();relative=path.relative_to(site).as_posix()
   if relative not in bindings or hashlib.sha256(path.read_bytes()).hexdigest()!=bindings[relative]['sha256']:raise ValueError('SDK_ORIGIN_CHANGED')
   origins[name]=dict(path=str(path),source=bindings[relative])
 for name,module in tuple(sys.modules.items()):
  if name.split('.')[0] in ('unified_system','integration') or name in {case.split('.')[0] for case in expected}:
   raw=getattr(module,'__file__',None)
   if raw is None:
    if name not in ('integration','integration.four_owner') or any(not pathlib.Path(p).resolve().is_relative_to(root) for p in module.__path__):raise ValueError('ROOT_NAMESPACE_ORIGIN')
    continue
   file=pathlib.Path(raw).resolve();relative=file.relative_to(root).as_posix()
   if relative not in root_bindings or hashlib.sha256(file.read_bytes()).hexdigest()!=root_bindings[relative]:raise ValueError('ROOT_MODULE_ORIGIN_MISMATCH')
   origins[name]=dict(path=str(file),owner='unified_system',runtime_sha256=root_bindings[relative])
 for relative,record in bindings.items():
  if hashlib.sha256((site/relative).read_bytes()).hexdigest()!=record['sha256']:raise ValueError('INSTALLED_SOURCE_CHANGED')
 for distribution,module in (('market-data','market_data'),('unified-terminan','terminan'),('unified-math-kernels','market_math')):
  dist=importlib.metadata.distribution(distribution);file=pathlib.Path(sys.modules[module].__file__).resolve()
  if file!=pathlib.Path(dist.locate_file(file.relative_to(site))).resolve():raise ValueError('METADATA_ORIGIN_MISMATCH')
 passed=result_complete(result,len(expected))
 report=dict(schema='unified.four-owner.installed-sdk-tests.v1',status='PASS_SCOPED' if passed else 'FAIL',scope='SYNTHETIC_INSTALLED_SDK_AND_FAKE_ROOT_DRIVER_ONLY',suite=args.suite,tests=result.testsRun,case_ids=actual,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),expected_failures=len(result.expectedFailures),unexpected_successes=len(result.unexpectedSuccesses),sdk_origins=origins,source_fences='PARENT_REQUIRED_NOT_EVALUATED_BY_CHILD',refusing_native_import_shape=True,actual_process=False,actual_sql=False,native_installation='NOT_RUN',physical='NOT_RUN',release_status='NO_GO',execution_authority=False,trading_authorized=False)
 (out/'installed-tests.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n',encoding='utf8')
 return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
