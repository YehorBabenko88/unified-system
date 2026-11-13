"""Optional PG inert89; two exact source inputs, no PG/native permission."""
import argparse,ast,hashlib,importlib.util,json,os,sys
from pathlib import Path
HELPER_HEAD='902a1704a16841d15d817ce17b48da1d3de19fda'
HELPER_TREE='132e85fc08ca447c1bfedbb4cdaa4db24505be7d'
RAW_SHA='b4fdd6cc2dea47a4fe8da0ce400004a20e36d4f401fb9bb37d20c0a597857df5'
COLLECTOR_SHA='bdca03c690c88537ed03275696e3152eec534ade0b2a4faef9259232a5be172f'
ACTIVE={'tools/collector/pg_private_writer.py': 'e14455f6fd1947646f848aaf2d867dc5fd01e50e7a3822d31a8201e3fffe4660', 'tools/collector/pg_protocol.py': 'e73811777525142fb340e994e9a68aee63806c296d264ac36390fbfa3440e884', 'tools/collector/pg_qualification.py': '23c109cdede68e39d51bbb27431d2bde49d08568a34dceb47227714bf2ddfd1b', 'unified_system/__init__.py': '68113e881a6bce0a682d3ebe1a3a1086c176c35b889d8c852b14e75645409610', 'unified_system/contracts.py': '935f946bcf9cf64f9c4b98a9cd6f391e92e03f6db5120ad910bb11f3e1dbc9fc', 'unified_system/journal.py': '648aca27a0c2eb3d092c4a3e64a9d8e69395bb6680c7da1b47fcfdc0cf3e3bf7', 'unified_system/lab_release.py': '204f8fe279f3db40c8d5b2091a0804663de62e4bfe746fcbf1667886fd384f28', 'unified_system/lab_runtime.py': '0e738d89491153896058c0971abcde0a65f52f3be2e2eac796339d433cc2c798', 'unified_system/module_catalog.py': '0bf8891040a482eb8758f103969bb5ada46cefcb3ede5754a6e275888a48efea', 'unified_system/runtime.py': '38cb470dd94b4900cc1d4a074212e82b643e0e0c705418491d02990c548ceb4d', 'unified_system/runtime_cli.py': '31a3036ed1cbc85d94d00904ab98ee9d47840d92e64d5c67563afbebed8671d9', 'unified_system/runtime_process.py': '7cdf208ac44d45dca5c0785719b846d28a52ae7754781450547d8a8ef81da7b2', 'unified_system/service_bootstrap.py': 'a8012a04c4a0507a72bd6ba38c63ad0af855d5f25efea7669ea11db1386d8d45', 'unified_system/service_postgres.py': '66355ded61d9d599d98e8a229a9733b2a6863d3a2e632e633e0d48e685dfbe63'}
GROUPS=[('pg_owned_custody', 'tests/collector/test_pg_qualification.py', 'PgCustodyTests', 37), ('pg_server_readiness', 'tests/collector/test_pg_qualification.py', 'ServerReadinessTests', 12), ('pg_supplier_pin', 'tests/collector/test_pg_qualification.py', 'IntegratedSupplierPinTests', 2), ('pg_protocol', 'tests/collector/test_pg_protocol.py', 'ProtocolTests', 19), ('pg_writer', 'tests/collector/test_pg_private_writer.py', 'PrivateWriterTests', 19)]
CODE=['tools/collector/pg_qualification.py','tools/collector/pg_protocol.py','tools/collector/pg_private_writer.py']
INERT_SOURCE="import sys,os,json,hashlib,types,unittest,ctypes,subprocess,socket,threading,_thread,asyncio,io\nfrom pathlib import Path\nimport dataclasses,math,time\nBASE=Path(__file__).parent\nROOT=BASE/'source'\nPINS={n:r['sha256'] for n,r in json.loads((BASE/'source-pins.json').read_bytes()).items()}\nraws={n:(ROOT/n).read_bytes() for n in PINS}\nassert all(hashlib.sha256(raws[n]).hexdigest()==h for n,h in PINS.items())\nforbidden=[]\ndef deny(kind):\n    forbidden.append(kind);raise RuntimeError('INERT_EFFECT_DENIED')\ndef audit(event,args):\n    if event.startswith(('socket.','subprocess.','ctypes.')) or event in ('os.system','os.posix_spawn','os.spawn','os.fork'):deny(event)\n    if event=='open':\n        p,mode,flags=args\n        if isinstance(mode,str) and any(x in mode for x in 'wax+') or isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):\n            if not isinstance(p,(str,bytes)) or not Path(os.fsdecode(p)).is_relative_to(BASE):deny('WRITE_OUTSIDE_OWN')\n    if event in ('os.mkdir','os.remove','os.rmdir','os.rename','os.replace','os.chmod','os.link','os.symlink'):deny(event)\nsys.addaudithook(audit)\ndef forbidden_thread(*a,**k):return deny('THREAD_OR_LOOP')\nthreading.Thread.start=forbidden_thread;_thread.start_new_thread=forbidden_thread\nasyncio.new_event_loop=forbidden_thread;asyncio.events.new_event_loop=forbidden_thread\nctypes.CDLL=forbidden_thread;ctypes.WinDLL=forbidden_thread;ctypes.OleDLL=forbidden_thread;ctypes.PyDLL=forbidden_thread\nfor name in ('tools','tools.collector'):\n    module=types.ModuleType(name);module.__path__=[];sys.modules[name]=module\nsubject=types.ModuleType('tools.collector.pg_qualification');subject.__file__=str(ROOT/'tools/collector/pg_qualification.py');sys.modules[subject.__name__]=subject\nexec(compile(raws['tools/collector/pg_qualification.py'],subject.__file__,'exec',dont_inherit=True),subject.__dict__)\nprotocol=types.ModuleType('tools.collector.pg_protocol');protocol.__file__=str(ROOT/'tools/collector/pg_protocol.py');sys.modules[protocol.__name__]=protocol\nexec(compile(raws['tools/collector/pg_protocol.py'],protocol.__file__,'exec',dont_inherit=True),protocol.__dict__)\nwriter=types.ModuleType('tools.collector.pg_private_writer');writer.__file__=str(ROOT/'tools/collector/pg_private_writer.py');sys.modules[writer.__name__]=writer\nexec(compile(raws['tools/collector/pg_private_writer.py'],writer.__file__,'exec',dont_inherit=True),writer.__dict__)\ngroups=[];suite=unittest.TestSuite()\nfor module_name,file,class_name,count in [('pg_owned_custody', 'tests/collector/test_pg_qualification.py', 'PgCustodyTests', 37), ('pg_server_readiness', 'tests/collector/test_pg_qualification.py', 'ServerReadinessTests', 12), ('pg_supplier_pin', 'tests/collector/test_pg_qualification.py', 'IntegratedSupplierPinTests', 2), ('pg_protocol', 'tests/collector/test_pg_protocol.py', 'ProtocolTests', 19), ('pg_writer', 'tests/collector/test_pg_private_writer.py', 'PrivateWriterTests', 19)]:\n    case=types.ModuleType(module_name);case.__file__=str(ROOT/file)\n    exec(compile(raws[file],case.__file__,'exec',dont_inherit=True),case.__dict__)\n    selected=unittest.defaultTestLoader.loadTestsFromTestCase(getattr(case,class_name));ids=[t.id() for t in selected];assert len(ids)==count and len(set(ids))==count\n    groups.append({'name':module_name,'ids':ids,'count':count});suite.addTests(selected)\nassert len({id for g in groups for id in g['ids']})==89\nresult=unittest.TextTestRunner(stream=sys.stderr,verbosity=2).run(suite)\npost={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in PINS}\nfacts={'scope':'INERT89_ONLY_NOT_PG_NATIVE_OR_SDK_CLOSURE','groups':groups,'testsRun':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'expectedFailures':len(result.expectedFailures),'unexpectedSuccesses':len(result.unexpectedSuccesses),'forbidden_attempts':forbidden,'source_equal':post==PINS,'pg_native_sql_executed':False}\nprint(json.dumps(facts,sort_keys=True))\nraise SystemExit(0 if result.wasSuccessful() and not forbidden and post==PINS else 1)\n"
def need(ok,code='PG_INERT_SOURCE_DENIED'):
 if not ok:raise ValueError(code)
def check_results(expected,records,count,failures,errors,skips,xfail,xpass):
 ids=[r['id'] for r in records]
 need(count==89 and not any((failures,errors,skips,xfail,xpass)) and len(expected)==len(set(expected))==89 and len(ids)==len(set(ids))==89 and sorted(ids)==sorted(expected) and all(r['outcome']=='PASS' for r in records),'CASE_IDS_OR_FLAGS')
def class_ids(ids,label,class_name,count):
 # The pinned helper inventories the whole file; select the exact test class.
 need(type(ids) is list and 0<len(ids)<=1024 and all(type(i) is str for i in ids),'CLASS_IDS')
 need(type(label) is str and type(class_name) is str and type(count) is int and 0<count<=1024,'CLASS_SELECTOR')
 need(len(ids)==len(set(ids)),'CLASS_IDS_DUPLICATE')
 prefix=label+'.'+class_name+'.';selected=[i for i in ids if i.startswith(prefix)]
 need(len(selected)==count,'CLASS_IDS_COUNT');return selected

def staged_paths():return list(dict.fromkeys(CODE+[row[1] for row in GROUPS]))

def check_capture(value):need(value['returncode']==0 and value['reason'] is None and not value['errors'] and value['retired'],'CAPTURE_UNKNOWN')

def retire_held(children):
 # Capture owns the shared requested cleanup budget. No new wait budget here.
 faults=[]
 for child in children:
  running=True
  try:running=child.poll() is None
  except BaseException:faults.append('HELD_POLL_UNKNOWN')
  if running:
   try:child.kill()
   except BaseException:faults.append('HELD_KILL_UNKNOWN')
  retired=False
  try:child.wait(timeout=0);retired=True
  except BaseException:faults.append('HELD_RETIREMENT_UNKNOWN')
  if retired and hasattr(child,'_handle'):
   try:child._handle.Close()
   except BaseException:faults.append('HELD_HANDLE_CLOSE_UNKNOWN')
 return faults
def check_supplier(head,tree,digest):need((head,tree,digest)==(HELPER_HEAD,HELPER_TREE,COLLECTOR_SHA),'HELPER_INPUT_PIN')
def check_active(snapshot):
 for path,digest in ACTIVE.items():need(snapshot['files'][path]['sha256']==digest,'ACTIVE14_PIN')
def check_layout(root,helper,out):
 paths=[root,helper,out];need(len(set(paths))==3 and all(not a.is_relative_to(b) and not b.is_relative_to(a) for i,a in enumerate(paths) for b in paths[i+1:]),'INPUT_OUTPUT_OVERLAP')
def load(path,name,digest):
 # Existing fixed bootstrap pattern: raw hash before any helper execution.
 import stat
 for p in (*reversed(path.parents),path):
  s=p.lstat();need(not stat.S_ISLNK(s.st_mode) and not getattr(s,'st_reparse_tag',0) and not getattr(s,'st_file_attributes',0)&1024,'HELPER_ALIAS')
 before=path.stat();need(before.st_nlink==1 and before.st_size<=131072)
 with path.open('rb') as f:raw=f.read(131073)
 after=path.stat();need((before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_ino,after.st_size,after.st_mtime_ns) and len(raw)==before.st_size and hashlib.sha256(raw).hexdigest()==digest,'HELPER_RAW_PIN')
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);exec(compile(raw,str(path),'exec'),m.__dict__);return m
def parent(root,helper,out):
 check_layout(root,helper,out);q=load(root/'tools/raw_capture/qualify.py','source_raw_helper',RAW_SHA)
 q.ordinary(out.parent);need(not out.exists(),'NEW_OUT_REQUIRED');out.mkdir();evidence=out/'evidence';evidence.mkdir()
 before={};after={};runtime_before=None;c=None;faults=[];capture=None;held=[];ids=[]
 expected=os.environ.get('EXPECTED_HEAD','')
 try:
  for role,path,head,tree in [('source',root,expected,None),('helper_input',helper,HELPER_HEAD,HELPER_TREE)]:
   before[role]=q.primary(path,head,tree);q.save(evidence/(role+'-before.json'),before[role])
  check_active(before['source']);check_supplier(before['helper_input']['head'],before['helper_input']['tree'],before['helper_input']['files']['tools/collector/qualify.py']['sha256'])
  # HELPER_DATA_INPUT only: never add supplier to sys.path/import its SDK.
  c=load(helper/'tools/collector/qualify.py','supplier_data_helpers',COLLECTOR_SHA)
  runtime_before=c.runtime_data(q);q.save(evidence/'runtime-before.json',runtime_before)
  stage=out/'source';stage.mkdir();pins={}
  for name in staged_paths():
   raw=q.raw_file(root/name,262144);pin=before['source']['files'][name];need(len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],'STAGE_SOURCE_CHANGED')
   target=stage/name;target.parent.mkdir(parents=True,exist_ok=True)
   with target.open('xb') as f:f.write(raw)
   pins[name]={'bytes':len(raw),'sha256':pin['sha256'],'primary':str(root/name)}
  for label,name,cls,count in GROUPS:
   group=class_ids(c.ast_ids(q.raw_file(root/name,262144),label),label,cls,count);ids+=group
  need(len(ids)==len(set(ids))==89)
  q.save(out/'source-pins.json',pins);q.save(evidence/'stage-ledger.json',{'roles':{'unified':{'files':pins}},'helper_role':'DATA_HELPERS_ONLY_NO_SDK','helper_head':HELPER_HEAD})
  c.verify_tree(q,stage,pins)
  with (out/'child.py').open('xb') as f:f.write(INERT_SOURCE.encode())
  cwd=out/'cwd';cwd.mkdir();temp=out/'temp';temp.mkdir();cache=out/'child-cache';need(not cache.exists())
  env={k:v for k,v in os.environ.items() if k.upper() in ('SYSTEMROOT','WINDIR','COMSPEC')};env.update(TEMP=str(temp),TMP=str(temp),TMPDIR=str(temp),PYTHONIOENCODING='utf-8')
  argv=[sys.executable,'-I','-S','-B','-X','pycache_prefix='+str(cache),str(out/'child.py')]
  original=q.subprocess.Popen
  def spawn(*args,**kwargs):
   process=original(*args,**kwargs);held.append(process);return process
  q.subprocess.Popen=spawn
  try:capture=q.capture(argv,cwd,env,30,262144)
  finally:
   q.subprocess.Popen=original
   faults.extend(retire_held(held))
  for stream in ('stdout','stderr'):
   with (evidence/(stream+'.original')).open('xb') as f:f.write(capture[stream])
  q.save(evidence/'capture.json',{k:v for k,v in capture.items() if k not in ('stdout','stderr')})
  check_capture(capture);need(len(held)==1,'DIRECT_CHILD_RETIREMENT')
  result=json.loads(capture['stdout']);actual=[{'id':id,'outcome':'PASS'} for group in result['groups'] for id in group['ids']]
  check_results(ids,actual,result['testsRun'],result['failures'],result['errors'],result['skipped'],result['expectedFailures'],result['unexpectedSuccesses'])
  need(not result['forbidden_attempts'] and result['source_equal'] is True and result['pg_native_sql_executed'] is False,'CHILD_EFFECTS_OR_SOURCE')
 except BaseException as exc:faults.append(type(exc).__name__+':'+str(exc))
 finally:
  for role,path,head,tree in [('source',root,expected,None),('helper_input',helper,HELPER_HEAD,HELPER_TREE)]:
   try:after[role]=q.primary(path,head,tree);q.save(evidence/(role+'-after.json'),after[role])
   except BaseException:faults.append('PRIMARY_POST_'+role.upper())
  if before!=after:faults.append('SOURCE_OR_HELPER_CHANGED_UNKNOWN')
  if c is not None:
   try:
    runtime_after=c.runtime_data(q);q.save(evidence/'runtime-after.json',runtime_after);need(runtime_before==runtime_after,'RUNTIME_CHANGED')
    if (out/'source-pins.json').exists():c.verify_tree(q,out/'source',json.loads(q.raw_file(out/'source-pins.json',262144)))
   except BaseException:faults.append('RUNTIME_OR_STAGE_POST_UNKNOWN')
  if (out/'child-cache').exists() or (out/'parent-cache').exists():faults.append('CACHE_CREATED')
  try:
   if c is not None:q.save(evidence/'artifact-inputs.json',c.evidence_index(q,evidence))
  except BaseException:faults.append('EVIDENCE_INDEX_UNKNOWN')
  q.save(evidence/'qualification.json',{'schema':'collector.pg.inert89.qualification.v1','status':'PASS' if not faults else 'FAILURE_OR_UNKNOWN','faults':faults,'source_head':expected,'helper_head':HELPER_HEAD,'helper_role':'HELPER_DATA_INPUT_NO_SDK','expected_ids':ids,'child_pid':None if not held else held[0].pid,'scope':'INERT89_ONLY_NOT_NATIVE_PG_SQL_OR14_SDK_RUNTIME_CLOSURE','runtime':'OBSERVED_DATA_NOT_OS_DLL_TRUST','execution_authority':False,'service_admission':False,'physical_acceptance':'NOT_RUN'})
 return bool(faults)
def main():
 p=argparse.ArgumentParser();p.add_argument('--parent',action='store_true',required=True);p.add_argument('--root',required=True);p.add_argument('--helpers',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 root,helper,out=map(Path,(a.root,a.helpers,a.out));need(all(x.is_absolute() and '..' not in x.parts for x in (root,helper,out)))
 need(sys.version_info[:3]==(3,12,10) and sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode,'PYTHON_PROFILE')
 need(sys.pycache_prefix is not None and Path(sys.pycache_prefix)==out/'parent-cache' and not(out/'parent-cache').exists(),'FRESH_CACHE_PREFIX')
 need(Path(__file__).absolute()==root/'tools/collector/qualify_pg_inert.py','SOURCE_SCRIPT_IDENTITY')
 return parent(root,helper,out)
if __name__=='__main__':raise SystemExit(main())
