"""Explicit builder15 qualification; source/runtime DATA, never native admission.

One cooperative unit child. Source/Git/runtime checks are outside its observed
120s budget; existing capture cleanup shares5 requested seconds, not an OS,
family or whole-lane deadline. No actual capsule/application is executed.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys

HELPER_SHA='b4fdd6cc2dea47a4fe8da0ce400004a20e36d4f401fb9bb37d20c0a597857df5'
COLLECTOR_HELPER_SHA='bdca03c690c88537ed03275696e3152eec534ade0b2a4faef9259232a5be172f'
BUILDER_SHA='7c45c96c71b6e7fc99524c7c99b4c928a90fa6bf60175ddbbfd6ee66b8e8f77e'
TEST_SHA='007cdcdb13c44158141d75e3d25e12d239e7dcb4f57cad938a5ee1481366f488'
CHILD_SECONDS=120
OUTPUT_CAP=262144
TEST_PATH='tests/collector/test_package_builder.py'
CODE_PATHS=('tools/collector/qualify_builder.py','tools/raw_capture/qualify.py',
 'tools/collector/qualify.py','tools/collector/build_package.py',TEST_PATH,
 'unified_system/__init__.py','unified_system/lab_release.py',
 'unified_system/module_catalog.py','unified_system/runtime_process.py',
 'docs/collector/package-builder-v1.md')
EXPECTED_IDS=tuple('builder_cases.PackageBuilderTests.'+name for name in (
 'test_actual_copy_inventory_manifest_and_non_admission_receipt',
 'test_designated_python_cannot_bypass_runtime_ledger',
 'test_ordered_overlay_bytes_must_match_existing_manifest_verifier',
 'test_rejects_budget_overflow_before_output','test_rejects_hardlinked_input',
 'test_rejects_input_hash_drift','test_rejects_reusing_completed_output',
 'test_rejects_role_scope_confusion','test_rejects_runtime_ledger_mismatch',
 'test_rejects_source_work_output_overlap','test_rejects_unknown_input_file_before_output',
 'test_reparse_stat_is_rejected_without_native_link_creation',
 'test_response_loss_after_stage_preserves_inactive_output_without_receipt_or_retry',
 'test_total_byte_budget_covers_retained_work_and_output_and_metadata',
 'test_total_input_count_includes_explicit_unused_members'))


def need(value,code):
 if not value:raise ValueError(code)


def load_pinned(path,name,digest):
 """Existing helper bootstrap shape with an actual file-backed ModuleSpec."""
 for item in (*reversed(path.parents),path):
  info=item.lstat()
  need(not stat.S_ISLNK(info.st_mode) and not getattr(info,'st_file_attributes',0)&1024,'HELPER_LINK')
 before=path.lstat();need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<=65536,'HELPER_KIND')
 with path.open('rb') as stream:raw=stream.read(65537)
 after=path.lstat()
 need((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==
      (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns) and len(raw)==before.st_size and
      hashlib.sha256(raw).hexdigest()==digest,'HELPER_PIN')
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
 need(name not in sys.modules,'HELPER_CACHE');sys.modules[name]=module
 exec(compile(raw,str(path),'exec'),module.__dict__)
 return module


def helpers(root):
 return (load_pinned(root/'tools/raw_capture/qualify.py','_builder_q',HELPER_SHA),
         load_pinned(root/'tools/collector/qualify.py','_builder_c',COLLECTOR_HELPER_SHA))


def hardlink_scope(scratch,source,target,source_fd,target_fd):
 if source_fd!=-1 or target_fd!=-1:return False
 try:
  source=Path(os.fsdecode(source));target=Path(os.fsdecode(target))
 except (TypeError,ValueError):return False
 return (source.is_absolute() and target.is_absolute() and '..' not in source.parts and '..' not in target.parts
  and str(source)==str(scratch/'test_rejects_hardlinked_input/input/sources/grid/module.txt')
  and str(target)==str(scratch/'test_rejects_hardlinked_input/alias.txt'))


def make_guard(q,scratch,result_path,blocked):
 delegate=q.owned_effect_guard(scratch,result_path)
 def audit(event,args):
  try:
   if event=='os.link':
    need(len(args)==4 and hardlink_scope(scratch,*args),'HARDLINK_SCOPE')
    source,target=Path(os.fsdecode(args[0])),Path(os.fsdecode(args[1]))
    q.ordinary(source,True);q.ordinary(target.parent)
    need(not os.path.lexists(target),'HARDLINK_DESTINATION_EXISTS')
   need(not event.startswith('sqlite3.'),'SQL_DENIED')
   delegate(event,args)
  except BaseException:
   if len(blocked)<16:blocked.append(event)
   raise
 return audit


def require_results(records,count,failures,errors,skips,xfail,xpass):
 need(count==15 and not any((failures,errors,skips,xfail,xpass)),'CASE_FLAGS')
 ids=[entry['id'] for entry in records]
 need(len(ids)==15 and len(set(ids))==15 and sorted(ids)==sorted(EXPECTED_IDS)
      and all(entry['outcome']=='PASS' for entry in records),'CASE_IDS')


def owned_data_links(q,state):
 pair=(state/'test_rejects_hardlinked_input/input/sources/grid/module.txt',
       state/'test_rejects_hardlinked_input/alias.txt')
 a,b=(path.lstat() for path in pair)
 need(a.st_nlink==b.st_nlink==2 and (a.st_dev,a.st_ino)==(b.st_dev,b.st_ino),'FIXTURE_HARDLINK_IDENTITY')
 for directory,dirs,names in os.walk(state,followlinks=False):
  q.ordinary(directory)
  for name in dirs:q.ordinary(Path(directory)/name)
  for name in names:
   path=Path(directory)/name;q.ordinary(path,True,single=path not in pair)
 return [{'path':str(path.relative_to(state)),'link_count':2,'role':'OWN_NEGATIVE_FIXTURE_DATA_ONLY'} for path in pair]


def origins(q,c,stage,ledger):
 import typing
 projects=c.project_origins(q,stage,ledger)
 facts={};base=Path(sys.base_prefix).absolute()
 for name,module in list(sys.modules.items()):
  if module is None:continue
  spec=getattr(module,'__spec__',None);origin=getattr(spec,'origin',None)
  if origin in ('built-in','frozen'):facts[name]={'role':origin};continue
  if name in ('typing.io','typing.re'):
   need(module is getattr(typing,name.split('.')[1],None),'PSEUDOMODULE_IDENTITY');facts[name]={'role':'EXACT_STDLIB_PSEUDO'};continue
  filename=getattr(module,'__file__',None);need(filename is not None,'FILELESS_ORIGIN')
  path=Path(filename).absolute()
  if name in projects:facts[name]=projects[name];continue
  need(path.is_relative_to(base) and 'site-packages' not in path.parts and 'dist-packages' not in path.parts,'INSTALLED_OR_FOREIGN_ORIGIN')
  q.ordinary(path,True,single=False);facts[name]={'role':'OBSERVED_STDLIB_DATA','path':str(path.relative_to(base))}
 return facts


def child(q,c,root,out):
 # Disclosed stock-stdlib initialization before the reviewed project audit.
 # This is not OS-DLL/vendor/native-effect attestation.
 import asyncio,ctypes,ssl,threading,tempfile,typing,unittest
 from unittest import mock
 stage=out/'stage';evidence=out/'evidence';state=evidence/'state';result_path=evidence/'builder15.result.json'
 ledger=json.loads(q.raw_file(evidence/'stage-ledger.json',2097152))
 files=ledger['roles']['unified']['files'];c.verify_tree(q,root,files)
 need(not any(name=='unified_system' or name.startswith('unified_system.') for name in sys.modules),'PROJECT_CACHE')
 sys.path[:0]=[str(root)]
 tempfile.tempdir=str(state/'temp');os.environ.update(TEMP=str(state/'temp'),TMP=str(state/'temp'),TMPDIR=str(state/'temp'))
 blocked=[];guard=make_guard(q,state,result_path,blocked)
 def no_thread_loop(*args,**kwargs):raise ValueError('THREAD_OR_LOOP_DENIED')
 threading.Thread.start=no_thread_loop;asyncio.BaseEventLoop.__init__=no_thread_loop
 sys.addaudithook(guard)
 result={'schema':'collector.builder15.child.v1','status':'FAILURE_OR_UNKNOWN','scope':'INERT_BUILDER_COPY_ONLY',
         'forbidden_attempts':blocked,'execution_authority':False,'service_admission':False,'native_admission':False}
 try:
  path=root/TEST_PATH;raw=q.raw_file(path,262144)
  need(hashlib.sha256(raw).hexdigest()==TEST_SHA,'TEST_PIN')
  need(sorted(c.ast_ids(raw,'builder_cases'))==sorted(EXPECTED_IDS),'AST_CASE_IDS')
  spec=importlib.util.spec_from_file_location('builder_cases',path);module=importlib.util.module_from_spec(spec)
  sys.modules[spec.name]=module;spec.loader.exec_module(module);module.PackageBuilderTests.scratch_parent=str(state)
  records=[];subjects=[]
  class Result(unittest.TextTestResult):
   def startTest(self,test):records.append({'id':test.id(),'outcome':'RUNNING'});super().startTest(test)
   def addSuccess(self,test):
    subject=test.builder;location=Path(subject.__spec__.origin).absolute()
    need(location==root/'tools/collector/build_package.py' and Path(subject.__file__).absolute()==location,'SUBJECT_ORIGIN')
    need(hashlib.sha256(q.raw_file(location,262144)).hexdigest()==BUILDER_SHA,'SUBJECT_PIN')
    subjects.append({'id':test.id(),'file':str(location),'sha256':BUILDER_SHA,'spec_origin':str(subject.__spec__.origin)})
    records[-1]['outcome']='PASS';super().addSuccess(test)
   def addFailure(self,test,error):records[-1]['outcome']='FAIL';super().addFailure(test,error)
   def addError(self,test,error):records[-1]['outcome']='ERROR';super().addError(test,error)
   def addSkip(self,test,reason):records[-1]['outcome']='SKIP';super().addSkip(test,reason)
  done=unittest.TextTestRunner(verbosity=2,resultclass=Result).run(unittest.defaultTestLoader.loadTestsFromTestCase(module.PackageBuilderTests))
  flags=(done.testsRun,len(done.failures),len(done.errors),len(done.skipped),len(done.expectedFailures),len(done.unexpectedSuccesses))
  result.update(records=records,tests=flags[0],failures=flags[1],errors=flags[2],skips=flags[3],xfail=flags[4],xpass=flags[5],subject_origins=subjects)
  require_results(records,*flags);c.check_cases(EXPECTED_IDS,records,*flags)
  result['hardlink_data']=owned_data_links(q,state)
  result['origins']=origins(q,c,stage,ledger);c.verify_tree(q,root,files)
  need(not blocked,'FORBIDDEN_EFFECT_ATTEMPT');result['status']='PASS'
 finally:q.save(result_path,result)


def parent(q,c,root,out):
 expected=os.environ.get('EXPECTED_HEAD','');q.ordinary(root);q.ordinary(out.parent)
 need(not out.exists() and root!=out and root not in out.parents and out not in root.parents,'OUTPUT_SCOPE')
 out.mkdir();evidence=out/'evidence';evidence.mkdir();state=evidence/'state';state.mkdir();(state/'temp').mkdir()
 stage=out/'stage';source=stage/'unified';source.mkdir(parents=True)
 faults=[];before=None;runtime_before=None;capture_result=None
 try:
  before=q.primary(root,expected,role='root',evidence=evidence,phase='before');q.save(evidence/'source-before.json',before)
  files={}
  for name in CODE_PATHS:
   need(name in before['files'],'SOURCE_MEMBER');raw=q.raw_file(root/name,262144)
   need(hashlib.sha256(raw).hexdigest()==before['files'][name]['sha256'],'SOURCE_PIN')
   fixed={'tools/raw_capture/qualify.py':HELPER_SHA,'tools/collector/qualify.py':COLLECTOR_HELPER_SHA,
          'tools/collector/build_package.py':BUILDER_SHA,TEST_PATH:TEST_SHA}.get(name)
   need(fixed is None or fixed==hashlib.sha256(raw).hexdigest(),'FROZEN_MEMBER_PIN')
   target=source/name;target.parent.mkdir(parents=True,exist_ok=True)
   with target.open('xb') as stream:stream.write(raw)
   target.chmod(0o444);files[name]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
  q.save(evidence/'stage-ledger.json',{'roles':{'unified':{'files':files}}});c.verify_tree(q,source,files)
  runtime_before=c.runtime_data(q);q.save(evidence/'runtime-before.json',runtime_before)
  cache=state/'cache';need(not cache.exists(),'CACHE_EXISTS');cache.mkdir()
  env={key:value for key,value in os.environ.items() if key.upper() in ('SYSTEMROOT','WINDIR','COMSPEC')}
  env.update(TEMP=str(state/'temp'),TMP=str(state/'temp'),TMPDIR=str(state/'temp'))
  argv=[sys.executable,'-I','-S','-B','-X','pycache_prefix='+str(cache),str(source/'tools/collector/qualify_builder.py'),'--child','--root',str(source),'--out',str(out)]
  held=[];original=q.subprocess.Popen
  def spawn(*args,**kwargs):
   process=original(*args,**kwargs);held.append(process);return process
  q.subprocess.Popen=spawn
  try:capture_result=q.capture(argv,state,env,CHILD_SECONDS,OUTPUT_CAP)
  finally:q.subprocess.Popen=original
  (evidence/'stdout.original').write_bytes(capture_result.pop('stdout'));(evidence/'stderr.original').write_bytes(capture_result.pop('stderr'))
  q.save(evidence/'capture.json',capture_result)
  need(len(held)==1 and capture_result['retired'] and held[0].poll() is not None,'CHILD_RETIREMENT')
  need(capture_result['reason'] is None and not capture_result['errors'] and capture_result['returncode']==0,'CHILD_CAPTURE')
  result=json.loads(q.raw_file(evidence/'builder15.result.json',2097152));need(result['status']=='PASS','CHILD_RESULT')
  require_results(result['records'],result['tests'],result['failures'],result['errors'],result['skips'],result['xfail'],result['xpass'])
 except BaseException as error:faults.append(type(error).__name__+':'+str(error))
 finally:
  try:
   after=q.primary(root,expected,role='root',evidence=evidence,phase='after');q.save(evidence/'source-after.json',after)
   need(before==after,'SOURCE_CHANGED')
  except BaseException as error:faults.append('SOURCE_POST:'+type(error).__name__+':'+str(error))
  try:
   runtime_after=c.runtime_data(q);q.save(evidence/'runtime-after.json',runtime_after)
   need(runtime_before==runtime_after,'RUNTIME_DATA_CHANGED')
  except BaseException as error:faults.append('RUNTIME_POST:'+type(error).__name__+':'+str(error))
  try:q.save(evidence/'evidence-index.json',c.evidence_index(q,evidence))
  except BaseException as error:faults.append('EVIDENCE:'+type(error).__name__+':'+str(error))
  q.save(evidence/'qualification.json',{'schema':'collector.builder15.qualification.v1','status':'PASS' if not faults else 'FAILURE_OR_UNKNOWN',
    'faults':faults,'head':expected,'capture':capture_result,'scope':'ONE_EXPLICIT_INERT_BUILDER15_ONLY',
    'runtime':'OBSERVED_DATA_NOT_VENDOR_OR_OS_DLL_ATTESTATION','execution_authority':False,'service_admission':False,'physical_acceptance':'NOT_RUN'})
 return 1 if faults else 0


def main():
 parser=argparse.ArgumentParser(description=__doc__);mode=parser.add_mutually_exclusive_group(required=True)
 mode.add_argument('--parent',action='store_true');mode.add_argument('--child',action='store_true')
 parser.add_argument('--root',required=True);parser.add_argument('--out',required=True);args=parser.parse_args()
 need(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode,'ISOLATED_FLAGS')
 root,out=Path(args.root),Path(args.out);need(root.is_absolute() and out.is_absolute(),'ABSOLUTE_PATHS')
 q,c=helpers(root)
 if args.parent:return parent(q,c,root,out)
 child(q,c,root,out);return 0


if __name__=='__main__':raise SystemExit(main())
