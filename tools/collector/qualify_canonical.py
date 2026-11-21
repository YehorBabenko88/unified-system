"""Exact-source, finite synthetic collector qualification; never native acceptance.

No provider, shell, service, child application or network socket may be started.
The reused SourceFence may invoke Git solely during before/after source checks.
"""
import argparse,hashlib,json,os,pathlib,sys,tempfile,unittest

MODULES=('test_profile','test_entry','test_logging','test_collector_capsule','test_source_manifest','test_e2e')
PERMISSIONS=('real_provider_sends','service_creation','acl_changes','production_sql','training','trading','public_submit','authority_mutation')

def manifest(data_head):
 return dict(schema='unified.collector.integration-manifest.v2',execution_scope='SYNTHETIC_OFFLINE',permissions=dict.fromkeys(PERMISSIONS,False),sources={'market_data':{'commit':data_head}})

class Cases(unittest.TextTestResult):
 def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.records=[]
 def addSuccess(self,test):super().addSuccess(test);self.records.append(dict(id=test.id(),outcome='PASS'))

def main(argv=None):
 parser=argparse.ArgumentParser(description=__doc__)
 for name in ('root','root-head','data','data-head','out'):parser.add_argument('--'+name,required=True)
 args=parser.parse_args(argv)
 root=pathlib.Path(args.root).resolve(strict=True);data=pathlib.Path(args.data).resolve(strict=True);out=pathlib.Path(args.out).absolute()
 if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):raise ValueError('isolated no-site no-bytecode invocation required')
 if out.exists() or root==data or root in out.parents or data in out.parents:raise ValueError('fresh output outside source roots required')
 cache=out/'cache'
 if sys.pycache_prefix is None or pathlib.Path(sys.pycache_prefix).resolve()!=cache.resolve():raise ValueError('isolated cache prefix required')
 sys.path[:0]=[str(root),str(root/'tests/collector'),str(data)]
 from integration.source_guard import SourceFence,_ordinary
 _ordinary(out.parent)
 fences={'unified_system':SourceFence(root,args.root_head,isolated_cache=cache),'market_data':SourceFence(data,args.data_head,isolated_cache=cache)}
 git_allowed=[True]
 def audit(event,values):
  if event in ('os.system','socket.__new__'):raise RuntimeError('QUALIFICATION_EFFECT_FORBIDDEN')
  if event=='subprocess.Popen' and not git_allowed[0]:raise RuntimeError('QUALIFICATION_CHILD_FORBIDDEN')
 sys.addaudithook(audit)
 before={key:fence.check() for key,fence in fences.items()}
 git_allowed[0]=False
 out.mkdir(exist_ok=False)
 report=dict(schema='unified.synthetic-collector.qualification.v2',status='FAIL',release_status='NO_GO',sources={'unified_system':args.root_head,'market_data':args.data_head},scope='SYNTHETIC_FIXTURE_SOURCE_ONLY',source_authenticity='UNATTESTED',native_installation='NOT_RUN',process_crash='NOT_RUN',postgresql='NOT_RUN',provider_sends=0)
 try:
  with tempfile.TemporaryDirectory(prefix='fixture-',dir=out) as temp:
   scratch=pathlib.Path(temp).resolve();source_manifest=scratch/'manifest.json';source_manifest.write_text(json.dumps(manifest(args.data_head)),encoding='utf8')
   os.environ.update(COLLECTOR_E2E_SCRATCH=str(scratch),COLLECTOR_INPUT_MANIFEST=str(source_manifest),COLLECTOR_CODE_ROOT=str(root))
   suite=unittest.defaultTestLoader.loadTestsFromNames(MODULES);expected=suite.countTestCases()
   result=unittest.TextTestRunner(verbosity=2,resultclass=Cases).run(suite)
   if not (expected>0 and result.testsRun==expected==len(result.records) and result.wasSuccessful() and not result.skipped and not result.expectedFailures and not result.unexpectedSuccesses):raise ValueError('complete non-skipped case inventory required')
   for name,module in tuple(sys.modules.items()):
    for owner,fence in fences.items():
     if name==owner or name.startswith(owner+'.'):fence.module(module)
   report.update(status='PASS_SCOPED',tests=expected,cases=result.records)
 except BaseException:
  report['status']='FAIL';raise
 finally:
  git_allowed[0]=True
  try:
   for fence in fences.values():fence.finish()
  except Exception:
   report['status']='FAIL';raise
  finally:
   (out/'evidence.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n',encoding='utf8')
 print(json.dumps({key:report[key] for key in ('status','release_status','sources','tests')}))
 return 0

if __name__=='__main__':raise SystemExit(main())
