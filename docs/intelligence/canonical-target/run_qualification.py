"""Finite canonical target source qualification; no native or public authority.
Run with -I -S -B -X pycache_prefix=NEW_OUT/cache. Only pinned read-only Git
may be spawned. Existing real-process crash fixture remains enabled/NOT_RUN.
"""
import argparse,hashlib,json,os,pathlib,shlex,sys,unittest

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('root','root-head','terminan-root','math-root','git','git-sha256','runtime-sha256','out'):p.add_argument('--'+name,required=True)
 a=p.parse_args(argv);root_lexical=pathlib.Path(a.root).absolute();root=root_lexical.resolve(strict=True);out_lexical=pathlib.Path(a.out).absolute()
 if '..' in out_lexical.parts:raise ValueError('ordinary output required')
 out=out_lexical.resolve();cache=out/'cache'
 if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode) or sys.pycache_prefix is None or pathlib.Path(sys.pycache_prefix).resolve()!=cache.resolve():raise ValueError('isolated runtime/cache required')
 if out.exists() or any(pathlib.Path(s).resolve()==out or pathlib.Path(s).resolve() in out.parents for s in (a.root,a.terminan_root,a.math_root)):raise ValueError('fresh separate output required')
 trusted=os.path.normcase(os.path.realpath(a.git))
 def audit(event,values):
  if event in ('os.system','socket.__new__'):raise RuntimeError('QUALIFICATION_EFFECT_FORBIDDEN')
  if event=='subprocess.Popen':
   command=shlex.split(values[1],posix=False) if type(values[1]) is str else values[1];executable=values[0] or command[0].strip(chr(34))
   if os.path.normcase(os.path.realpath(executable))!=trusted or command[command.index('-C')+2] not in ('show','rev-parse','for-each-ref','ls-tree','diff','cat-file','check-attr','ls-files','config'):raise RuntimeError('ONLY_PINNED_READONLY_GIT')
 sys.addaudithook(audit);sys.path[:0]=[str(root),str(root/'tests/gateway_target_adapter')]
 from integration.source_guard import SourceFence,_ordinary
 _ordinary(out_lexical.parent);fence=SourceFence(root_lexical,a.root_head,isolated_cache=cache,git_executable=a.git,git_sha256=a.git_sha256)
 before=fence.check()
 if any(item['comparison']!='RAW_IDENTICAL' for item in before['runtime_files'].values()):raise ValueError('raw Root source required')
 out.mkdir(mode=0o700);cache.mkdir(mode=0o700)
 os.environ.update(TARGET_TERMINAN_ROOT=a.terminan_root,TARGET_MATH_ROOT=a.math_root,TARGET_GIT=a.git,TARGET_GIT_SHA256=a.git_sha256,TARGET_RUNTIME_SHA256=a.runtime_sha256)
 import test_direct,test_canonical_contract
 not_run='test_actual_owned_process_crash_before_and_after_calculation_stays_unknown'
 cases=[test_direct.DirectTests(name) for name in unittest.defaultTestLoader.getTestCaseNames(test_direct.DirectTests) if name!=not_run]
 suite=unittest.TestSuite(cases);suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(test_canonical_contract));expected=suite.countTestCases()
 report=dict(schema='unified.canonical-target.qualification.v2',status='FAIL',root_sha=a.root_head,terminan_sha='b99913690ce29ce60e73414cc4d626ca989916ce',math_sha='de8194f71311a6d7dddb69be9de812030ed1f13f',scope='SYNTHETIC_LOCAL_UNATTESTED',native='NOT_RUN',actual_process_crash='NOT_RUN',network='PROHIBITED',execution_authority=False,release_status='NO_GO')
 try:
  result=unittest.TextTestRunner(verbosity=2).run(suite)
  if not (result.wasSuccessful() and result.testsRun==expected and not result.skipped and not result.expectedFailures and not result.unexpectedSuccesses):raise ValueError('all scoped cases must pass')
  for name,module in tuple(sys.modules.items()):
   if name=='unified_system' or name.startswith('unified_system.'):fence.module(module)
  report.update(status='PASS_SCOPED',tests=expected,not_run=[not_run])
 finally:
  try:fence.finish()
  except BaseException:report['status']='FAIL';raise
  finally:(out/'evidence.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n',encoding='utf8')
 print(json.dumps(report));return 0
if __name__=='__main__':raise SystemExit(main())
