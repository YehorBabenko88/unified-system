"""Exact hosted Root component rosters; no native product acceptance.

Import-safe pure calibrations are separate from main's hosted Git/process tests.
"""
import argparse,hashlib,json,os,pathlib,stat,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
MANIFEST='docs/qualification/root-components-20261120/groups.json'

def result_passed(result,count):
 return (result is not None and result.wasSuccessful() and result.testsRun==count
         and not result.skipped and not result.expectedFailures and not result.unexpectedSuccesses)

def require_ids(actual,expected):
 if (type(expected) is not list or not expected or any(type(x) is not str for x in expected)
     or len(set(expected))!=len(expected) or len(set(actual))!=len(actual) or sorted(actual)!=sorted(expected)):
  raise ValueError('EXACT_UNIQUE_COMPONENT_CASES_REQUIRED')
 return sorted(actual)

def compile_sources(root,files):
 count=0
 for name in files:
  path=root/name
  if path.suffix=='.py':compile(path.read_bytes(),str(path),'exec',dont_inherit=True);count+=1
 return count

def require_output(root,out):
 root=root.resolve();out=out.absolute()
 if str(out).startswith(('//',chr(92))) or os.name=='nt' and ':' in str(out)[2:]:raise ValueError('ORDINARY_LOCAL_EVIDENCE_REQUIRED')
 for parent in out.parents:
  info=parent.lstat()
  if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&1024:raise ValueError('EVIDENCE_PARENT_ALIAS')
 if out.exists() or out.resolve().is_relative_to(root):raise ValueError('FRESH_EXTERNAL_EVIDENCE_REQUIRED')
 return out

def load_groups(root):
 value=json.loads((root/MANIFEST).read_bytes())
 if value['schema']!='unified.root-component-workflows.v1' or value['release_status']!='NO_GO':raise ValueError('COMPONENT_SCOPE')
 groups=value['groups']
 if set(groups)!={'final','supervisor','combined','fleet'}:raise ValueError('CLOSED_COMPONENT_GROUPS')
 for config in groups.values():require_ids(config['expected_ids'],config['expected_ids'])
 if not set(groups['final']['preserved_prior_ids'])<=set(groups['final']['expected_ids']):raise ValueError('PRIOR_MANDATORY_CASE_REMOVED')
 return groups

def strict_repository(fence):
 allowed=set(fence.files);directories={''}
 for name in allowed:
  directories.update(p.as_posix() for p in pathlib.PurePosixPath(name).parents if p.as_posix()!='.')
 for path in fence.root.rglob('*'):
  relative=path.relative_to(fence.root)
  if relative.parts[0]=='.git':continue
  info=path.lstat()
  if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&1024:raise ValueError('COMPONENT_SOURCE_ALIAS')
  if path.is_dir():
   if relative.as_posix() not in directories:raise ValueError('UNTRACKED_SOURCE_DIRECTORY')
  elif not path.is_file() or relative.as_posix() not in allowed or path.suffix.lower() in ('.pyc','.pyo'):
   raise ValueError('UNTRACKED_OR_BYTECODE_SOURCE')
  elif path.read_bytes()!=fence.blobs[fence.files[relative.as_posix()]]:raise ValueError('RAW_COMPONENT_SOURCE_MISMATCH')

def case_ids(suite):
 for item in suite:
  if isinstance(item,unittest.TestSuite):yield from case_ids(item)
  else:yield item.id()

def main(argv=None):
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--group',choices=('final','supervisor','combined','fleet'),required=True)
 parser.add_argument('--expected-head',required=True);parser.add_argument('--out',required=True)
 args=parser.parse_args(argv)
 if not(sys.flags.isolated and sys.dont_write_bytecode and sys.pycache_prefix is None):raise ValueError('ISOLATED_NO_BYTECODE_COMPONENT_REQUIRED')
 if os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('RUNNER_ENVIRONMENT')!='github-hosted':raise ValueError('HOSTED_COMPONENT_EXECUTION_ONLY')
 if args.group=='supervisor' and (sys.version_info[:3]!=(3,12,10) or not sys.flags.no_site):raise ValueError('EXACT_STDLIB_SUPERVISOR_PROFILE')
 out=require_output(ROOT,pathlib.Path(args.out));out.mkdir();cache=out/'cache';sys.pycache_prefix=str(cache)
 sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
 from integration.source_guard import SourceFence
 fence=None
 report=dict(schema='unified.root-components.source-qualification.v1',head=args.expected_head,group=args.group,status='FAIL_INCOMPLETE',release_status='NO_GO',native_product_acceptance='NOT_QUALIFIED',physical='NOT_RUN',production='NO_GO',execution_authority=False,trading_authorized=False)
 try:
  fence=SourceFence(ROOT,args.expected_head,isolated_cache=cache)
  before=fence.check();strict_repository(fence);report['source_before']=before
  fence.file(__file__,python=True);fence.module(sys.modules['integration.source_guard']);fence.file(ROOT/MANIFEST)
  groups=load_groups(ROOT);config=groups[args.group];report['scope']=config['scope']
  calibration=unittest.defaultTestLoader.loadTestsFromName('test_root_component_qualification')
  calibration_ids=json.loads((ROOT/MANIFEST).read_bytes())['calibration_ids']
  require_ids(list(case_ids(calibration)),calibration_ids)
  with (out/'calibrations.log').open('w',encoding='utf8') as stream:calibration_result=unittest.TextTestRunner(stream=stream,verbosity=2).run(calibration)
  if not result_passed(calibration_result,len(calibration_ids)):raise ValueError('COMPONENT_CALIBRATION_FAILED')
  report['calibration_case_ids']=calibration_ids
  selected=[name for name in fence.files if any(name.startswith(prefix+'/') for prefix in config['compile_roots'])]
  report['semantic_compiled_python_files']=compile_sources(ROOT,selected)
  suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in config['modules'])
  expected=require_ids(list(case_ids(suite)),config['expected_ids']);report['expected_case_ids']=expected
  with (out/'component-tests.log').open('w',encoding='utf8') as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
  origins={}
  for name,module in tuple(sys.modules.items()):
   if name.split('.')[0] in ('unified_system','scheduler_components','tests','integration') or name.startswith('test_'):
    if getattr(module,'__file__',None):origins[name]=fence.module(module)
    elif any(not pathlib.Path(p).resolve().is_relative_to(ROOT) for p in getattr(module,'__path__',())):raise ValueError('COMPONENT_NAMESPACE_ORIGIN')
  report.update(status='PASS_SCOPED' if result_passed(result,len(expected)) else 'FAIL',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),expected_failures=len(result.expectedFailures),unexpected_successes=len(result.unexpectedSuccesses),module_origins=origins,test_log_sha256=hashlib.sha256((out/'component-tests.log').read_bytes()).hexdigest())
 except BaseException as exc:
  report['status']='FAIL';report['error_type']=type(exc).__name__;raise
 finally:
  try:
   if fence is not None and fence.before is not None:report['source_after']=fence.finish();strict_repository(fence)
  except BaseException as exc:
   report['status']='FAIL';report['source_post_error']=type(exc).__name__;raise
  finally:(out/'evidence.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n',encoding='utf8')
 if report['status']!='PASS_SCOPED':raise ValueError('MANDATORY_COMPONENT_CASE_FAILED_SKIPPED_OR_XFAILED')
 print(json.dumps(dict(status=report['status'],tests=report['tests'],head=args.expected_head,scope=report['scope'],release_status='NO_GO')))
 return 0
if __name__=='__main__':raise SystemExit(main())
