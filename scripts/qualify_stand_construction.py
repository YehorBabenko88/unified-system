"""Mandatory hosted metadata/own-SQLite role; no workload/source invocation."""
import argparse,hashlib,importlib.util,json,os,pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--expected-head',required=True);p.add_argument('--out',required=True);args=p.parse_args()
 if not(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):raise ValueError('ISOLATED_METADATA_PROFILE_REQUIRED')
 if os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('RUNNER_ENVIRONMENT')!='github-hosted':raise ValueError('HOSTED_METADATA_ONLY')
 out=pathlib.Path(args.out).resolve(strict=True);cache=pathlib.Path(sys.pycache_prefix).resolve(strict=True)
 if out.is_relative_to(ROOT) or cache.parent!=out or next(cache.iterdir(),None) is not None:raise ValueError('FRESH_EXTERNAL_CACHE_REQUIRED')
 sys.path.insert(0,str(ROOT))
 from integration.source_guard import SourceFence
 fence=SourceFence(ROOT,args.expected_head,isolated_cache=cache);before=fence.check()
 paths=('scripts/qualify_stand_construction.py','tests/hosted_contracts/stand_construction.py','tests/physical_dev/test_bootstrap_contract.py','.github/workflows/ls5-physical-dev-source.yml')
 for name in paths:fence.file(ROOT/name,python=name.endswith('.py'))
 active=[True]
 def audit(event,arguments):
  if not active[0]:return
  if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.startfile','os.posix_spawn','os.exec'):raise RuntimeError('METADATA_CASE_EFFECT_DENIED')
  if event=='ctypes.dlopen' and arguments[0]!='kernel32':raise RuntimeError('METADATA_DLL_DENIED')
  if event=='ctypes.dlsym' and arguments[1]!='GetDriveTypeW':raise RuntimeError('METADATA_SYMBOL_DENIED')
  if event=='sqlite3.connect' and not pathlib.Path(arguments[0]).resolve().is_relative_to(out):raise RuntimeError('PRIVATE_JOURNAL_REQUIRED')
 sys.addaudithook(audit)
 result=None
 try:
  path=ROOT/'tests/hosted_contracts/stand_construction.py';spec=importlib.util.spec_from_file_location('hosted_stand_construction',path);module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
  suite=unittest.defaultTestLoader.loadTestsFromModule(module)
  expected='hosted_stand_construction.StandConstructionTests.test_actual_canonical_constructor_preserves_private_stand_obligations'
  if suite.countTestCases()!=1 or next(iter(next(iter(suite)))).id()!=expected:raise ValueError('EXACT_METADATA_ROLE_REQUIRED')
  with (out/'tests.log').open('w',encoding='utf8') as log:result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
  for name,loaded in tuple(sys.modules.items()):
   if name.split('.')[0] in ('unified_system','tools','integration') or name=='hosted_stand_construction':
    if getattr(loaded,'__file__',None):fence.module(loaded)
 finally:
  active[0]=False;after=fence.finish()
  passed=result is not None and result.testsRun==1 and result.wasSuccessful() and not(result.skipped or result.expectedFailures or result.unexpectedSuccesses)
  (out/'receipt.json').write_text(json.dumps(dict(schema='unified.stand-construction.metadata.v1',head=args.expected_head,source_before=before,source_after=after,tests=0 if result is None else result.testsRun,status='PASS_SCOPED' if passed else 'FAIL',source_workload='NOT_INVOKED',native_runtime='NOT_QUALIFIED',execution_authority=False,trading_authorized=False,production='NO_GO'),indent=2)+'\n')
 if not passed:raise ValueError('MANDATORY_METADATA_ROLE_FAILED')
if __name__=='__main__':main()
