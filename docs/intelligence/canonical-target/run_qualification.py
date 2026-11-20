"""Finite canonical target source qualification; no native or public authority.
Run with -I -S -B -X pycache_prefix=NEW_OUT/cache. Only pinned read-only Git
may be spawned by default. Hosted --include-process-crash additionally admits
only the fixed disposable Python crash fixture; no native/service authority.
"""
import argparse,hashlib,json,os,pathlib,shlex,sys,tempfile,unittest

def fixed_crash_command(command,executable,*,enabled,root,terminan_root,math_root,cache):
 if not enabled or type(command) not in (list,tuple) or len(command)!=12:return False
 canonical=lambda value:os.path.normcase(os.path.realpath(value))
 if canonical(executable)!=canonical(sys.executable) or canonical(command[0])!=canonical(sys.executable):return False
 if list(command[1:6])!=['-I','-S','-B','-X','pycache_prefix='+str(cache)]:return False
 if canonical(command[6])!=canonical(root/'tests/gateway_target_adapter/crash_child.py'):return False
 if canonical(command[7])!=canonical(root) or canonical(command[9])!=canonical(terminan_root) or canonical(command[10])!=canonical(math_root) or command[11] not in ('BEFORE','AFTER'):return False
 stand=pathlib.Path(command[8])
 return stand.is_absolute() and not stand.is_symlink() and canonical(stand.parent)==canonical(tempfile.gettempdir()) and stand.name.startswith('target-own-crash-') and stand.is_dir() and not any(stand.iterdir())

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('root','root-head','terminan-root','math-root','git','git-sha256','runtime-sha256','out'):p.add_argument('--'+name,required=True)
 p.add_argument('--include-process-crash',action='store_true')
 a=p.parse_args(argv);root_lexical=pathlib.Path(a.root).absolute();root=root_lexical.resolve(strict=True);out_lexical=pathlib.Path(a.out).absolute()
 if '..' in out_lexical.parts:raise ValueError('ordinary output required')
 out=out_lexical.resolve();cache=out/'cache'
 if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode) or sys.pycache_prefix is None or pathlib.Path(sys.pycache_prefix).resolve()!=cache.resolve():raise ValueError('isolated runtime/cache required')
 if out.exists() or any(pathlib.Path(s).resolve()==out or pathlib.Path(s).resolve() in out.parents for s in (a.root,a.terminan_root,a.math_root)):raise ValueError('fresh separate output required')
 trusted=os.path.normcase(os.path.realpath(a.git))
 if hashlib.sha256(pathlib.Path(sys.executable).read_bytes()).hexdigest()!=a.runtime_sha256:raise ValueError('runtime digest mismatch')
 def audit(event,values):
  if event in ('os.system','socket.__new__'):raise RuntimeError('QUALIFICATION_EFFECT_FORBIDDEN')
  if event=='subprocess.Popen':
   command=[item[1:-1] if len(item)>1 and item[0]==item[-1]==chr(34) else item for item in shlex.split(values[1],posix=False)] if type(values[1]) is str else values[1];executable=values[0] or command[0]
   if fixed_crash_command(command,executable,enabled=a.include_process_crash,root=root,terminan_root=a.terminan_root,math_root=a.math_root,cache=cache):return
   if os.path.normcase(os.path.realpath(executable))!=trusted or '-C' not in command or command[command.index('-C')+2] not in ('show','rev-parse','for-each-ref','ls-tree','diff','cat-file','check-attr','ls-files','config'):raise RuntimeError('ONLY_PINNED_READONLY_GIT')
 sys.addaudithook(audit);sys.path[:0]=[str(root),str(root/'tests/gateway_target_adapter')]
 from integration.source_guard import SourceFence,_ordinary
 _ordinary(out_lexical.parent);fence=SourceFence(root_lexical,a.root_head,isolated_cache=cache,git_executable=a.git,git_sha256=a.git_sha256)
 before=fence.check()
 if any(item['comparison']!='RAW_IDENTICAL' for item in before['runtime_files'].values()):raise ValueError('raw Root source required')
 out.mkdir(mode=0o700);cache.mkdir(mode=0o700)
 os.environ.update(TARGET_TERMINAN_ROOT=a.terminan_root,TARGET_MATH_ROOT=a.math_root,TARGET_GIT=a.git,TARGET_GIT_SHA256=a.git_sha256,TARGET_RUNTIME_SHA256=a.runtime_sha256)
 import test_direct,test_canonical_contract,test_qualification_policy
 not_run='test_actual_owned_process_crash_before_and_after_calculation_stays_unknown'
 cases=[test_direct.DirectTests(name) for name in unittest.defaultTestLoader.getTestCaseNames(test_direct.DirectTests) if a.include_process_crash or name!=not_run]
 suite=unittest.TestSuite(cases);suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(test_canonical_contract));suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(test_qualification_policy));expected=suite.countTestCases()
 report=dict(schema='unified.canonical-target.qualification.v2',status='FAIL',root_sha=a.root_head,terminan_sha='a2f63228aeb7436721eaf3fe6251c94ab7e5e087',math_sha='7ed299b6480b2cb683ee91bd162ed9d76e99aa7f',scope='SYNTHETIC_LOCAL_UNATTESTED',native='NOT_RUN',actual_process_crash='NOT_RUN',network='PROHIBITED',execution_authority=False,release_status='NO_GO')
 try:
  result=unittest.TextTestRunner(verbosity=2).run(suite)
  if not (result.wasSuccessful() and result.testsRun==expected and not result.skipped and not result.expectedFailures and not result.unexpectedSuccesses):raise ValueError('all scoped cases must pass')
  for name,module in tuple(sys.modules.items()):
   if name=='unified_system' or name.startswith('unified_system.'):fence.module(module)
  report.update(status='PASS_SCOPED',tests=expected,actual_process_crash='PASS_OWNED_DISPOSABLE_PROCESS' if a.include_process_crash else 'NOT_RUN',not_run=[] if a.include_process_crash else [not_run])
 finally:
  try:fence.finish()
  except BaseException:report['status']='FAIL';raise
  finally:(out/'evidence.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n',encoding='utf8')
 print(json.dumps(report));return 0
if __name__=='__main__':raise SystemExit(main())
