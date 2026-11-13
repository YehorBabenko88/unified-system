"""Optional Collector software qualification; no service/provider/native grant.

Five immutable inputs, explicit staging provenance and separate UNIT, actual
E2E, modeled A5 AST and real software-process recovery axes. Reuses the frozen
raw-capture helper without changing its 58-case configuration. Source/runtime
DATA checks are outside the child-group observed budget. Cleanup is requested,
not a kernel/family/whole-lane deadline or a SourceGate/OS-DLL trust framework.
"""
import ast
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import stat
import sys
import sysconfig
import time
import types

HELPER_SHA256='b4fdd6cc2dea47a4fe8da0ce400004a20e36d4f401fb9bb37d20c0a597857df5'
INPUTS={
 'grid':('3bfddc3811e5f88a2b24b5026025f772814f3eb4','e91c410966ffccc6c87a56314fba3c94fc16ad1a'),
 'a5':('dec4ac619239f9c84982850be2bb6a7cb896e370','a9c13d90270d7cd924abe5fe08b780227e8925d6'),
 'a4':('602cb6a66cab820947ef6915479c4490ff101358','0d7e2f71384f7a9d14127bd0c74d9f21e073ce04'),
 'logger':('07eb13bef9099da750d50943120ac5fdc98db9c6','675e888bb7a5e8d1956fe68504795021fbf8906e'),
}
A5_OVERLAY='grid/owned_worker_service.py'
PINS={
 ('a5',A5_OVERLAY):'81e3637799f7e43ead0e0c637d2ac96a3a0fd443f469277cbc8a77c8db109a12',
 ('a5','tests/collector/owned_worker_lifecycle.py'):'1fb2f0327e89cb525e933d24e714d28674a33d55b80cf39d03a7428558756938',
 ('a4','unified_system/storage/raw_capture.py'):'8af7b96a57f0b84329e8914fe40b41f3804c12722d87f906cb4d25c70e6e2174',
 ('a4','unified_system/storage/collector_context.py'):'23525973fab305ad290c4120581b22767b1a00f5d344963130cf81fc7bf37aac',
 ('a4','tests/storage/collector_context/test_context.py'):'148e4321b762e3c5cc25a5ddee05fe7abac0da0664c313b7fee47fd4dd46c84f',
 ('a4','tests/storage/collector_context/test_postgres_source.py'):'61414e95e83b958f6c975fdeed11ecc65d4e310f235d8a93697fafddd87df129',
 ('a4','tests/storage/raw_capture/test_adapter.py'):'16d79ff4aca7de50f9379f115f7a12dfe4c6dc3f0c65ec4750e3c54d72381f21',
 ('a4','sql/collector/001_collector_metadata_v1.sql'):'9f9c25f36a86c68e05e3f486cf61eed622fdeeb65ef0da27c8d489ad00ebb65e',
 ('a4','sql/collector/readback_v1.sql'):'48e2af3f0667c3ac25c115d1ace8a197cd2a2b9707d9ff6e540629dc0aee350c',
 ('logger','unified_system/collector_logging.py'):'0fabda35f20eb9480d2c1565914fcaac041c5d9e91167b55d5d94ccc546f1c71',
 ('logger','tests/collector/test_logging.py'):'840511730ac1350c13218de9452b082d3b464b9cb1c7b7d911d8c07241091c24',
}
# Current Root production bytes are separate from the immutable historical A4
# supplier. The latter remains pinned/tested as its own source input below.
CURRENT_ROOT_SOURCES={
 'unified_system/storage/collector_context.py':{
  'bytes':27665,'sha256':'84b52f42298c157a146f4937a06ff3d618e81c4c3e8ef9eab1a6974b38374165',
  'oid':'198e77d9efb81e7217170ee8d9fb13e393bc460a',
  'source_owner_head':'e2e0adf0fd68ef5446913fda6f003c249d335a32',
  'source_owner_tree':'c3bc6b6826516835c181584d7f9dda5d7478cf34',
  'root_adoption_commit':'1e734fe9b9dfa04c1576a27cadd5837cbf8a1a4b',
  'root_adoption_tree':'f41f95b33feadd5a2d7a3bc148725445b92c0045'}}
ADOPTED={path:digest for (role,path),digest in PINS.items()
         if path.startswith('unified_system/') and path not in CURRENT_ROOT_SOURCES}
MANIFEST='integration/collector/v1/source-inputs.json'
PERMISSIONS={'real_provider_sends','service_creation','acl_changes','production_sql','training','trading','public_submit','authority_mutation'}
UNIT_MODULES=[('test_profile','tests/collector/test_profile.py'),('test_entry','tests/collector/test_entry.py'),
 ('test_logging','tests/collector/test_logging.py'),('test_context','tests/storage/collector_context/test_context.py'),
 ('test_adapter','tests/storage/raw_capture/test_adapter.py'),('test_postgres_source','tests/storage/collector_context/test_postgres_source.py')]
E2E_MODULES=[('test_e2e','tests/collector/test_e2e.py')]
AST_MODULES=[('owned_worker_lifecycle','tests/collector/owned_worker_lifecycle.py')]
PHASES=('UNITS','A5_AST','E2E','FIRST','RESUME','CRASH','CHECK_CRASH')
SOURCE_CAP=256*1024*1024
RUNTIME_CAP=256*1024*1024
OUTPUT_CAP=262144


class Denied(RuntimeError):pass


def need(value,code):
 if not value:raise Denied(code)


def ast_ids(raw,label):
 need(type(raw) is bytes and 0<len(raw)<=262144,'TEST_SOURCE_BOUND')
 tree=ast.parse(raw);ids=[]
 for node in tree.body:
  if isinstance(node,ast.ClassDef) and any(ast.unparse(base)=='unittest.TestCase' for base in node.bases):
   for method in node.body:
    if isinstance(method,ast.FunctionDef) and method.name.startswith('test_'):ids.append(label+'.'+node.name+'.'+method.name)
 need(0<len(ids)<=1024 and len(ids)==len(set(ids)),'AST_INVENTORY')
 return ids


def check_cases(expected,records,count,failures,errors,skipped,expected_failures,unexpected_successes):
 ids=[r['id'] for r in records]
 need(bool(expected) and count==len(expected)==len(ids)==len(set(ids)) and sorted(ids)==sorted(expected) and
      not any((failures,errors,skipped,expected_failures,unexpected_successes)) and
      all(r['outcome']=='PASS' for r in records),'CASE_OUTCOME')


def check_manifest(doc):
 need(type(doc) is dict and doc.get('schema')=='unified.collector.integration-manifest.v1' and
      doc.get('execution_scope')=='SYNTHETIC_OFFLINE','MANIFEST_SCOPE')
 permissions=doc.get('permissions')
 need(type(permissions) is dict and set(permissions)==PERMISSIONS and all(v is False for v in permissions.values()),'MANIFEST_PERMISSIONS')
 components=doc.get('new_components');need(type(components) is list and len(components)<=16,'MANIFEST_COMPONENTS')
 for owner,role in (('A3','grid'),('A5','a5')):
  selected=[x for x in components if type(x) is dict and x.get('owner')==owner]
  need(len(selected)==1 and (selected[0].get('head'),selected[0].get('tree'))==INPUTS[role],'MANIFEST_INPUT_PIN')


def check_adopted(files):
 for name,digest in ADOPTED.items():need(name in files and files[name]['sha256']==digest,'ROOT_OWNER_ADOPTION_MISMATCH')
 current=[]
 for name,pin in CURRENT_ROOT_SOURCES.items():
  need(name in files,'ROOT_CURRENT_SOURCE_MISMATCH');row=files[name]
  need(type(row) is dict and type(row.get('bytes')) is int and type(row.get('sha256')) is str and
       type(row.get('oid')) is str and (row['bytes'],row['sha256'],row['oid'])==
       (pin['bytes'],pin['sha256'],pin['oid']),'ROOT_CURRENT_SOURCE_MISMATCH')
  current.append(dict(path=name,**pin,origin_role='root',historical_supplier_role='a4',
      historical_supplier_head=INPUTS['a4'][0],historical_supplier_sha256=PINS[('a4',name)],replacement_in_stage=False))
 return current


def remaining_budget(start,now,used):
 need(type(start) in (int,float) and type(now) in (int,float) and math.isfinite(start) and
      math.isfinite(now) and now>=start and type(used) is int and 0<=used<=OUTPUT_CAP,'BUDGET_UNKNOWN')
 return 240-(now-start),OUTPUT_CAP-used


def check_capture(phase,result):
 need(phase in PHASES and result['returncode']==(77 if phase=='CRASH' else 0) and
      result['reason'] is None and result['retired'] is True and not result['errors'],'CHILD_FAILURE_OR_UNKNOWN')


def check_component_result(value):
 need(type(value) is dict and value.get('schema')=='unified.collector.offline-result.v1' and
      value.get('scope')=='SYNTHETIC_OFFLINE' and value.get('phase')=='STOPPED' and
      value.get('native_outcome')=='UNKNOWN' and value.get('publication_confirmed') is False and
      type(value.get('provider_sends')) is int and value['provider_sends']==0 and
      value.get('service_running') is False and value.get('physical_accepted') is False and
      value.get('postgresql')=='NOT_RUN' and value.get('writer_closed') is True,'COMPONENT_RESULT_SCOPE')


def bootstrap_helpers(root):
 path=root/'tools/raw_capture/qualify.py'
 for parent in reversed((path.parent,*path.parent.parents)):
  info=parent.lstat()
  need(stat.S_ISDIR(info.st_mode) and not(stat.S_ISLNK(info.st_mode) or getattr(info,'st_reparse_tag',0) or getattr(info,'st_file_attributes',0)&1024),'HELPER_ANCESTRY')
 before=path.lstat()
 need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<=65536 and
      not(getattr(before,'st_reparse_tag',0) or getattr(before,'st_file_attributes',0)&1024),'HELPER_KIND')
 with path.open('rb') as f:raw=f.read(65537)
 after=path.lstat()
 need((before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_ino,after.st_size,after.st_mtime_ns) and
      len(raw)==before.st_size and hashlib.sha256(raw).hexdigest()==HELPER_SHA256,'HELPER_PIN')
 module=types.ModuleType('_collector_raw_helpers');module.__file__=str(path);sys.modules[module.__name__]=module
 exec(compile(raw,str(path),'exec'),module.__dict__)
 return module


def decoded(raw):
 def pairs(items):
  out={}
  for key,value in items:need(key not in out,'DUPLICATE_JSON');out[key]=value
  return out
 def nonfinite(_):raise Denied('NONFINITE_JSON')
 return json.loads(raw,object_pairs_hook=pairs,parse_constant=nonfinite)


def tree_dirs(files):
 return {str(parent).replace('\\','/') for name in files for parent in Path(name).parents if str(parent)!='.'}


def verify_tree(q,root,files):
 dirs=tree_dirs(files);seen=set();seen_dirs=set()
 def walk(directory,prefix=''):
  q.ordinary(directory)
  for path in directory.iterdir():
   name=prefix+path.name;info=path.lstat()
   if stat.S_ISDIR(info.st_mode):
    need(name in dirs,'STAGE_EXTRA_DIRECTORY');q.ordinary(path);seen_dirs.add(name);walk(path,name+'/')
   else:
    need(name in files,'STAGE_EXTRA_FILE');raw=q.raw_file(path,20*1024*1024)
    need(len(raw)==files[name]['bytes'] and hashlib.sha256(raw).hexdigest()==files[name]['sha256'],'STAGE_RAW_MISMATCH');seen.add(name)
 walk(root);need(seen==set(files) and seen_dirs==dirs,'STAGE_INVENTORY')


def stage_sources(q,paths,ledgers,out):
 current=check_adopted(ledgers['root']['files'])
 stage=out/'stage';stage.mkdir();result={};overlays=[]
 for role,origin in (('unified','root'),('grid','grid')):
  target=stage/role;target.mkdir();result[role]={'files':{}}
  for name,pin in ledgers[origin]['files'].items():
   raw=q.raw_file(paths[origin]/name,20*1024*1024)
   need(hashlib.sha256(raw).hexdigest()==pin['sha256'] and len(raw)==pin['bytes'],'COPY_SOURCE_CHANGED')
   dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True)
   with dest.open('xb') as f:f.write(raw)
   result[role]['files'][name]={**pin,'origin_role':origin,'origin_head':ledgers[origin]['head']}
 # Root's current implementation was already copied from the Root primary
 # tree. Record its provenance; never overwrite it with historical A4 bytes.
 current=[dict(binding,origin_head=ledgers['root']['head']) for binding in current]
 for binding in current:
  row=result['unified']['files'][binding['path']]
  row['kind']='ROOT_CURRENT_SOURCE_BINDING_NOT_OVERWRITE';row['root_current_source_binding']=binding
 def copy(role,name,target_role,kind,replace=False):
  pin=ledgers[role]['files'][name];need(pin['sha256']==PINS[(role,name)],'OWNER_SUPPORT_PIN')
  files=result[target_role]['files'];before=files.get(name)
  if before is not None and not replace:
   need(before['sha256']==pin['sha256'],'SUPPORT_ALREADY_DIFFERENT');return
  dest=stage/target_role/name;raw=q.raw_file(paths[role]/name,20*1024*1024)
  need(len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],'OVERLAY_SOURCE_CHANGED')
  dest.parent.mkdir(parents=True,exist_ok=True)
  if replace:q.ordinary(dest,True)
  with dest.open('wb' if replace else 'xb') as f:f.write(raw)
  files[name]={**pin,'origin_role':role,'origin_head':ledgers[role]['head'],'kind':kind}
  overlays.append({'target':target_role,'path':name,'kind':kind,'previous_sha256':None if before is None else before['sha256'],
                   'sha256':pin['sha256'],'origin_head':ledgers[role]['head']})
 copy('a5',A5_OVERLAY,'grid','EXPLICIT_A5_PRODUCTION_OVERLAY_NOT_MERGE',True)
 for (role,name) in PINS:
  if name.startswith('tests/') or name.startswith('sql/'):
   copy(role,name,'grid' if role=='a5' else 'unified','STATIC_SQL_ONLY' if name.startswith('sql/') else 'OWNER_TEST_SUPPORT')
 for role,entry in result.items():verify_tree(q,stage/role,entry['files'])
 return {'roles':result,'ordered_overlays':overlays,'root_current_source_bindings':current,'production_merge_claim':False}


def runtime_data(q):
 """Stock interpreter DATA observation; no OS-DLL or execution attestation."""
 base=Path(sys.base_prefix).absolute();q.ordinary(base)
 roots={'stdlib':Path(sysconfig.get_path('stdlib')).absolute()}
 if (base/'DLLs').exists():roots['dlls']=base/'DLLs'
 entries={};total=0
 def add(path,key):
  nonlocal total
  info=path.lstat();need(len(entries)<4096,'RUNTIME_COUNT')
  if stat.S_ISLNK(info.st_mode):
   # Observe link DATA, never follow it in this scanner or claim its target.
   target=os.readlink(path);need(len(target)<=32768,'RUNTIME_LINK_BOUND')
   total+=len(target.encode('utf-8'));need(total<=RUNTIME_CAP,'RUNTIME_TOTAL')
   entries[key]={'kind':'symlink_data','target':target};return
  q.ordinary(path,True,single=False);need(info.st_size<=min(64*1024*1024,RUNTIME_CAP-total),'RUNTIME_FILE_BOUND')
  with path.open('rb') as f:raw=f.read(min(64*1024*1024,RUNTIME_CAP-total)+1)
  after=path.stat();need(len(raw)==info.st_size and (info.st_ino,info.st_size,info.st_mtime_ns)==(after.st_ino,after.st_size,after.st_mtime_ns),'RUNTIME_CHANGED')
  total+=len(raw);need(total<=RUNTIME_CAP,'RUNTIME_TOTAL')
  entries[key]={'kind':'raw_data','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
 def walk(directory,label):
  q.ordinary(directory)
  for path in directory.iterdir():
   if path.name.casefold() in ('site-packages','dist-packages','__pycache__') or path.suffix.casefold() in ('.pyc','.pyo'):continue
   key=label+'/'+path.name;info=path.lstat()
   if stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode):q.ordinary(path);walk(path,key)
   else:add(path,key)
 for label,path in roots.items():walk(path,label)
 for directory in (base,base/'bin',base/'lib'):
  if not directory.exists():continue
  q.ordinary(directory)
  for path in directory.iterdir():
   info=path.lstat()
   relevant=path.name.startswith(('python','libpython')) or path.suffix.casefold() in ('.dll','.pyd','.exe','.dylib') or '.so' in path.suffixes
   if relevant and not stat.S_ISDIR(info.st_mode):add(path,'runtime/'+path.relative_to(base).as_posix())
 return {'schema':'collector.stock-runtime-data.v1','python':sys.version,'platform':sys.platform,'files':entries,
         'cache_and_site_excluded':True,'OS_DLL_or_loaded_binary_trust':False}


def primary_snapshot(q,paths,role,expected,evidence,when):
 pins=(expected,None) if role=='root' else INPUTS[role]
 directory=evidence/('git-'+when+'-'+role);directory.mkdir()
 helper_role={'root':'root','grid':'grid','a5':'grid','a4':'storage','logger':'root'}[role]
 value=q.primary(paths[role],*pins,role=helper_role,evidence=directory,phase=when)
 q.save(evidence/('source-'+when+'-'+role+'.json'),value)
 return value


def evidence_index(q,evidence):
 # Retained UNIT negative fixtures intentionally include hardlinks. Read them
 # as bounded owned DATA, recording link count; never reuse this for code,
 # stage admission or the strict q.raw_file source checks.
 files={};total=0;directories=0
 def walk(directory,prefix='',depth=0):
  nonlocal total,directories
  directories+=1;need(directories<=4096 and depth<=32,'EVIDENCE_DIRECTORY_BOUND');q.ordinary(directory)
  for path in directory.iterdir():
   name=prefix+path.name;info=path.lstat()
   if stat.S_ISDIR(info.st_mode):q.ordinary(path);walk(path,name+'/',depth+1)
   else:
    need(len(files)<8192 and info.st_size<=32*1024*1024 and total+info.st_size<=128*1024*1024,'EVIDENCE_BOUND')
    before=q.ordinary(path,True,single=False)
    # ordinary() returns a path, so capture the checked leaf's own stat next.
    before=before.stat()
    with path.open('rb') as f:
     held=os.fstat(f.fileno());raw=f.read(min(32*1024*1024,128*1024*1024-total)+1);after=os.fstat(f.fileno())
    current=q.ordinary(path,True,single=False).stat()
    fields=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink)
    need(fields(before)==fields(held)==fields(after)==fields(current) and len(raw)==before.st_size,'EVIDENCE_CHANGED')
    total+=len(raw)
    files[name]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'link_count':before.st_nlink,'role':'OWN_DATA_NOT_CODE_ADMISSION'}
 walk(evidence)
 return {'schema':'collector.pre-final-evidence-index.v1','files':files,
         'exclusions':['artifact-inputs.json','qualification.json'],'provider_zip_digest':'FROM_ARTIFACT_API_AFTER_UPLOAD_ONLY'}


def project_origins(q,stage,ledger):
 result={}
 for name,module in list(sys.modules.items()):
  if module is None:continue
  filename=getattr(module,'__file__',None)
  if not filename:continue
  path=Path(filename).absolute()
  for role in ('unified','grid'):
   root=stage/role
   if path.is_relative_to(root):
    rel=path.relative_to(root).as_posix();need(rel in ledger['roles'][role]['files'],'MODULE_NOT_IN_STAGE')
    raw=q.raw_file(path,20*1024*1024);digest=hashlib.sha256(raw).hexdigest()
    need(digest==ledger['roles'][role]['files'][rel]['sha256'],'MODULE_SOURCE_MISMATCH')
    result[name]={'role':role,'path':rel,'sha256':digest}
 for name in ('aiohttp','websockets','numpy','scipy','grid.coordinator','grid.config','grid.resources',
              'grid.ml_runtime','grid.storage','grid.strategy_runner','grid.owned_worker_service'):
  need(name not in sys.modules,'FORBIDDEN_RUNTIME_IMPORT')
 return result


def run_cases(q,modules,source,state,result):
 import unittest
 expected=[];suite=unittest.TestSuite();records=[];scratch={}
 for label,name in modules:
  scratch[label]=state/label;scratch[label].mkdir()
  path=source/name;expected.extend(ast_ids(q.raw_file(path,262144),label))
  if label in sys.modules:module=sys.modules[label];need(Path(module.__file__)==path,'TEST_MODULE_SHADOW')
  else:
   spec=importlib.util.spec_from_file_location(label,path);module=importlib.util.module_from_spec(spec)
   sys.modules[label]=module;spec.loader.exec_module(module)
  suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
 class Result(unittest.TextTestResult):
  def startTest(self,test):
   target=scratch[test.id().split('.',1)[0]]
   os.environ.update(COLLECTOR_LOG_TEST_SCRATCH=str(target),A4_CONTEXT_TEST_SCRATCH=str(target),
                     A4_RAW_TEST_SCRATCH=str(target),COLLECTOR_E2E_SCRATCH=str(target))
   records.append({'id':test.id(),'outcome':'RUNNING'});super().startTest(test)
  def addSuccess(self,test):records[-1]['outcome']='PASS';super().addSuccess(test)
  def addFailure(self,test,err):records[-1]['outcome']='FAIL';super().addFailure(test,err)
  def addError(self,test,err):records[-1]['outcome']='ERROR';super().addError(test,err)
  def addSkip(self,test,reason):records[-1]['outcome']='SKIP';super().addSkip(test,reason)
 done=unittest.TextTestRunner(verbosity=2,resultclass=Result).run(suite)
 result.update(expected_ids=expected,records=records,tests=done.testsRun,failures=len(done.failures),errors=len(done.errors),skipped=len(done.skipped))
 check_cases(expected,records,done.testsRun,len(done.failures),len(done.errors),len(done.skipped),len(done.expectedFailures),len(done.unexpectedSuccesses))


def complete(coro):
 try:
  try:coro.send(None)
  except StopIteration as done:return done.value
  raise Denied('UNEXPECTED_ASYNC_SUSPENSION')
 finally:coro.close()


def recovery_phase(q,phase,source,state,result_path,result):
 import sqlite3
 from test_profile import fixture
 from unified_system.collector_profile import validate_collector_profile
 from unified_system.collector_offline import collect_synthetic,synthetic_frames
 from unified_system.storage.collector_context import CollectorContext,CollectorContextProfile,CollectorBlocked
 from unified_system.storage.raw_capture import RawCaptureProfile
 from unified_system.storage.object_store import ObjectStore
 from unified_system.journal import Journal
 manifest=q.raw_file(source/MANIFEST,262144);binding=hashlib.sha256(manifest).hexdigest()
 value=fixture();value['source_manifest_sha256']=binding
 profile=validate_collector_profile(value,manifest_sha256=binding)
 kw=dict(context_id=value['context_id'],store_id=value['store_id'],binding_sha256=binding,
   profile=CollectorContextProfile(raw_profile=RawCaptureProfile(sqlite_headroom_bytes=262144,inventory_file_limit=128),lifecycle_headroom_bytes=65536))
 if phase in ('FIRST','RESUME'):
  result['collector_result']=complete(collect_synthetic(profile,manifest_bytes=manifest,frames=synthetic_frames(),state_root=state,
     code_root=source,observed_at_ms=1794441600000,resume=phase=='RESUME'))
  check_component_result(result['collector_result'])
  databases=('context/raw/capture.sqlite','context/lifecycle.sqlite')
 elif phase=='CRASH':
  from grid.worker import Worker,COLLECTOR_PROFILE
  from grid.raw_capture import RawCaptureRecorder,RawCaptureProfile as GridProfile
  ctx=CollectorContext.create(state,**kw);original=ObjectStore.put
  def interrupted(store,raw,**options):
   receipt=original(store,raw,**options);path=store._root/'objects'/hashlib.sha256(raw).hexdigest()
   with path.open('wb') as stream:stream.write(raw[:max(1,len(raw)//2)]);stream.flush();os.fsync(stream.fileno())
   result.update(fault='AFTER_OWN_PUT_TRUNCATE_BEFORE_RAW_LINK',partial_bytes=path.stat().st_size,
      expected_payload_sha256=hashlib.sha256(raw).hexdigest(),raw_links=len(Journal(state/'raw/capture.sqlite').read()),
      lifecycle_rows=len(Journal(state/'lifecycle.sqlite').read()),writer_flag=ctx._flag().decode(),intentional_exit=77)
   q.save(result_path,result);os._exit(77)  # ONLY this new synthetic owned child/context.
  ObjectStore.put=interrupted
  def factory(symbol,endpoint):
   return RawCaptureRecorder(ctx,instrument=dict(exchange='bybit',category='linear',symbol='BTCUSDT',instrument_version='1'),
     producer_source_revision=INPUTS['grid'][0],source_kind='SYNTHETIC',endpoint=endpoint,
     profile=GridProfile(16,4194304,1048576,16384,2))
  worker=Worker(launch_profile=COLLECTOR_PROFILE,raw_capture_factory=factory)
  complete(worker.receive_offline(synthetic_frames(),symbol='BTCUSDT',endpoint='synthetic://bybit/linear',observed_at_ms=1794441600000))
  raise Denied('INTERRUPTION_NOT_REACHED')
 else:
  objects=state/'raw/archive/objects';before={p.name:hashlib.sha256(q.raw_file(p,1048576)).hexdigest() for p in objects.iterdir()}
  ctx=CollectorContext.open(state,**kw)
  try:
   need(ctx.status().state=='UNKNOWN' and complete(ctx.read_history())==(),'DIRTY_CONTEXT_NOT_UNKNOWN')
   try:ctx.require_ready()
   except CollectorBlocked:pass
   else:raise Denied('DIRTY_WRITER_ADMITTED')
   try:complete(ctx.store_capture(observation_bytes=b'forbidden-retry',payload_bytes=b'must-not-write'))
   except CollectorBlocked:pass
   else:raise Denied('UNKNOWN_RETRIED')
   store=ObjectStore.open(state/'raw/archive',store_id=value['store_id']);rejected=0
   for name in before:
    try:store.read(name,max_bytes=1048576)
    except ValueError:rejected+=1
   need(rejected==1,'PARTIAL_OBJECT_NOT_REJECTED')
  finally:ctx.close()
  need({p.name:hashlib.sha256(q.raw_file(p,1048576)).hexdigest() for p in objects.iterdir()}==before,'ORPHAN_CHANGED')
  result.update(reopened_state='UNKNOWN',raw_links=0,partial_object_hash_rejected=rejected,orphan_bytes_preserved=True,
                retry_denied=True,native_outcome='UNKNOWN',publication_confirmed=False)
  databases=('raw/capture.sqlite','lifecycle.sqlite')
 integrity={}
 for name in databases:
  path=state/name;before=hashlib.sha256(q.raw_file(path,1048576)).hexdigest()
  db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
  try:integrity[name]=db.execute('PRAGMA integrity_check').fetchone()[0]
  finally:db.close()
  need(integrity[name]=='ok' and hashlib.sha256(q.raw_file(path,1048576)).hexdigest()==before,'OWN_SQLITE_INTEGRITY')
 result['sqlite_readonly_integrity']=integrity


def child(q,phase,paths,out):
 # Disclosed stock-stdlib initialization, like the reviewed working prototype
 # (ctypes may initialize the interpreter's own library handle). No explicit
 # token/service/native-control API is invoked. Audit applies before projects;
 # this is not loaded OS-DLL attestation or an all-native-effects denial.
 import ctypes,asyncio,threading,tempfile
 from unittest import mock
 evidence=out/'evidence';stage=out/'stage';source=stage/'unified';grid=stage/'grid'
 ledger=decoded(q.raw_file(evidence/'stage-ledger.json',2097152))
 for role,entry in ledger['roles'].items():verify_tree(q,stage/role,entry['files'])
 need(not (out/(phase+'-cache')).exists(),'CHILD_CACHE_EXISTS')
 state=evidence/'state'/('restart' if phase in ('FIRST','RESUME') else 'interrupted' if phase in ('CRASH','CHECK_CRASH') else phase.lower())
 result_path=evidence/(phase+'.result.json');blocked=[]
 if phase in ('UNITS','A5_AST','E2E'):state.mkdir()
 temp=evidence/'state'/('tmp-'+phase);temp.mkdir();tempfile.tempdir=str(temp)
 os.environ.update(TEMP=str(temp),TMP=str(temp),TMPDIR=str(temp),COLLECTOR_LOG_TEST_SCRATCH=str(state),
   A4_CONTEXT_TEST_SCRATCH=str(state),A4_RAW_TEST_SCRATCH=str(state),COLLECTOR_E2E_SCRATCH=str(state),
   COLLECTOR_INPUT_MANIFEST=str(source/MANIFEST),COLLECTOR_CODE_ROOT=str(source))
 sys.path[:0]=[str(source),str(grid),str(source/'tests/collector')]
 filesystem_strict=phase not in ('UNITS','A5_AST')
 guard=q.owned_effect_guard(state,result_path) if filesystem_strict else q.effect_event
 def audit(event,args):
  try:guard(event,args)
  except BaseException:
   if len(blocked)<16:blocked.append(event)
   raise
 def no_thread_loop(*args,**kwargs):raise Denied('THREAD_OR_LOOP_DENIED')
 threading.Thread.start=no_thread_loop;asyncio.BaseEventLoop.__init__=no_thread_loop
 sys.addaudithook(audit)
 result={'schema':'collector.phase-result.v1','phase':phase,'child_pid':os.getpid(),'status':'FAILURE_OR_UNKNOWN',
         'scope':'MODELED_A5_AST_ONLY' if phase=='A5_AST' else 'SOURCE_UNIT_ONLY' if phase=='UNITS' else 'ACTUAL_SYNTHETIC_SOFTWARE_ONLY',
         'filesystem_audit':'STRICT_OWNED_STATE' if filesystem_strict else 'REVIEWED_UNIT_SOURCES_NEW_TEMP_DIRFD_CLEANUP_NOT_OS_SANDBOX',
         'forbidden_effect_attempts':blocked,'provider_sends':0,'service_running':False,'postgresql':'NOT_RUN',
         'physical_acceptance':False,'authority_granted':False}
 primary_error=None
 try:
  if phase in ('UNITS','E2E','A5_AST'):
   modules=UNIT_MODULES if phase=='UNITS' else E2E_MODULES if phase=='E2E' else AST_MODULES
   run_cases(q,modules,grid if phase=='A5_AST' else source,state,result)
  else:
   # Shared fixture is loaded from the same selected immutable test source.
   spec=importlib.util.spec_from_file_location('test_profile',source/'tests/collector/test_profile.py')
   module=importlib.util.module_from_spec(spec);sys.modules['test_profile']=module;spec.loader.exec_module(module)
   recovery_phase(q,phase,source,state,result_path,result)
  result['project_module_origins']=project_origins(q,stage,ledger)
  need(not blocked,'FORBIDDEN_EFFECT_ATTEMPT');result['status']='PASS'
 except BaseException as exc:
  primary_error=exc;raise
 finally:
  try:q.save(result_path,result)
  except BaseException:
   if primary_error is None:raise
   print('RESULT_PRESERVATION_UNKNOWN',file=sys.stderr)


def cli(args):
 need(args and args[0] in ('--parent','--child'),'ENTRY')
 mode=args[0];phase=None;rest=args[1:]
 if mode=='--child':need(rest and rest[0] in PHASES,'PHASE');phase=rest[0];rest=rest[1:]
 include='--include-a5-ast' in rest
 if include:need(rest.count('--include-a5-ast')==1,'OPTION');rest=[x for x in rest if x!='--include-a5-ast']
 need(len(rest)==12,'ARGUMENTS');paths={}
 for index in range(0,len(rest),2):
  key=rest[index];need(key in ('--root','--grid','--a5','--a4','--logger','--out') and key[2:] not in paths,'ARGUMENTS')
  path=Path(rest[index+1]);need(path.is_absolute() and '..'not in path.parts and not path.anchor.startswith(('\\\\','//')),'LOCAL_PATH_ARGUMENT')
  paths[key[2:]]=path
 need(set(paths)=={'root','grid','a5','a4','logger','out'},'ARGUMENTS')
 sources=[paths[name] for name in ('root',*INPUTS)]
 need(len(set(sources))==5 and all(not a.is_relative_to(b) and not b.is_relative_to(a)
      for index,a in enumerate(sources) for b in sources[index+1:]),'SOURCE_LAYOUT')
 need(all(not paths['out'].is_relative_to(path) and not path.is_relative_to(paths['out']) for path in sources),'OUTPUT_SOURCE_OVERLAP')
 return mode,phase,paths,include


def parent(q,paths,include):
 out=paths['out'];q.ordinary(out.parent);out.mkdir();evidence=out/'evidence';evidence.mkdir();(evidence/'state').mkdir()
 before={};after={};results=[];faults=[];details=[];runtime_before=None;staged=None;position='PRIMARY_BEFORE'
 expected=os.environ.get('EXPECTED_HEAD','');stage=out/'stage'
 phases=[x for x in PHASES if x!='A5_AST' or include]
 try:
  for role in ('root',*INPUTS):
   before[role]=primary_snapshot(q,paths,role,expected,evidence,'before')
   need(sum(v['bytes'] for value in before.values() for v in value['files'].values())<=SOURCE_CAP,'SOURCE_TOTAL')
  for (role,name),pin in PINS.items():need(before[role]['files'][name]['sha256']==pin,'OWNER_PIN')
  check_adopted(before['root']['files'])
  manifest=q.raw_file(paths['root']/MANIFEST,262144);check_manifest(decoded(manifest))
  position='STAGING'
  staged=stage_sources(q,paths,before,out);q.save(evidence/'stage-ledger.json',staged)
  position='RUNTIME_BEFORE'
  runtime_before=runtime_data(q);q.save(evidence/'runtime-before.json',runtime_before)
  started=time.monotonic();used=0
  for phase in phases:
   position='PHASE_'+phase
   seconds,cap=remaining_budget(started,time.monotonic(),used);need(seconds>=30 and cap>0,'GROUP_BUDGET')
   held=[];original=q.subprocess.Popen
   def spawn(*args,**kwargs):
    process=original(*args,**kwargs);held.append(process);return process
   env={k:v for k,v in os.environ.items() if k.upper() in ('SYSTEMROOT','WINDIR','COMSPEC')}
   temp=evidence/'state'/('parent-tmp-'+phase);temp.mkdir();env.update(TEMP=str(temp),TMP=str(temp),TMPDIR=str(temp))
   argv=[sys.executable,'-I','-S','-B','-X','pycache_prefix='+str(out/(phase+'-cache')),str(paths['root']/'tools/collector/qualify.py'),'--child',phase]
   for key in ('root','grid','a5','a4','logger','out'):argv.extend(['--'+key,str(paths[key])])
   q.subprocess.Popen=spawn
   try:captured=q.capture(argv,evidence,env,30,cap)
   finally:q.subprocess.Popen=original
   used+=captured['total_bytes']
   for stream in ('stdout','stderr'):
    with (evidence/(phase+'.'+stream+'.original.log')).open('xb') as f:f.write(captured.pop(stream))
   fact={'phase':phase,'capture':captured,'pid':None if not held else held[0].pid};results.append(fact)
   q.save(evidence/('phase-progress-'+phase+'.json'),{'phases':results,'complete':False})
   need(len(held)==1,'OWNED_CHILD_IDENTITY')
   # Independently retire the retained process handle even when the capture
   # reports an unsuccessful child. Never infer cleanup from exit code alone.
   fact['retained_handle_closed']=False
   if captured['retired']:
    try:
     need(held[0].wait(timeout=0)==captured['returncode'],'OWNED_CHILD_EXIT')
     if hasattr(held[0],'_handle'):held[0]._handle.Close()
     fact['retained_handle_closed']=True
    except BaseException:fact['handle_retirement_unknown']=True
   check_capture(phase,captured);need(fact['retained_handle_closed'],'OWNED_HANDLE_UNKNOWN')
   actual=decoded(q.raw_file(evidence/(phase+'.result.json'),2097152))
   need(actual['schema']=='collector.phase-result.v1' and actual['phase']==phase and actual['child_pid']==fact['pid'] and
        not actual['forbidden_effect_attempts'] and type(actual['provider_sends']) is int and actual['provider_sends']==0 and
        actual['service_running'] is False and actual['physical_acceptance'] is False and
        actual['authority_granted'] is False and actual['postgresql']=='NOT_RUN','CHILD_RESULT_IDENTITY')
   need(actual.get('status')=='PASS' if phase!='CRASH' else actual.get('intentional_exit')==77 and actual.get('writer_flag')=='D' and actual.get('raw_links')==0,'CHILD_RESULT')
  first=decoded(q.raw_file(evidence/'FIRST.result.json',2097152));resume=decoded(q.raw_file(evidence/'RESUME.result.json',2097152))
  check=decoded(q.raw_file(evidence/'CHECK_CRASH.result.json',2097152))
  first_data=first['collector_result'];resume_data=resume['collector_result']
  need(first['child_pid']!=resume['child_pid'] and first_data['raw_observations_stored']==3 and resume_data['raw_observations_stored']==6 and
       resume_data['previous_checkpoint']==first_data['checkpoint'] and first_data['counter_epoch']==resume_data['counter_epoch'] and
       check['reopened_state']=='UNKNOWN' and check['partial_object_hash_rejected']==1 and check['retry_denied'] and check['orphan_bytes_preserved'],'PROCESS_RECOVERY_AXIS')
  need(remaining_budget(started,time.monotonic(),used)[0]>=0,'OBSERVED_GROUP_BUDGET')
 except BaseException as exc:
  faults.append(str(exc) if type(exc) is Denied else 'BOUNDARY_UNKNOWN')
  details.append({'position':position,'primary_git_fact':exc.fact if isinstance(exc,q.BoundaryFault) else None})
 finally:
  for role in ('root',*INPUTS):
   try:
    after[role]=primary_snapshot(q,paths,role,expected,evidence,'after')
   except BaseException as exc:
    faults.append('SOURCE_POST_'+role.upper())
    details.append({'position':'PRIMARY_AFTER_'+role,'primary_git_fact':exc.fact if isinstance(exc,q.BoundaryFault) else None})
  if before!=after:faults.append('SOURCE_CHANGED_OR_UNKNOWN')
  if staged is not None:
   try:
    for role,entry in staged['roles'].items():verify_tree(q,stage/role,entry['files'])
   except BaseException:faults.append('STAGE_POST_UNKNOWN')
  try:
   runtime_after=runtime_data(q);q.save(evidence/'runtime-after.json',runtime_after)
   if runtime_before!=runtime_after:faults.append('RUNTIME_DATA_CHANGED_OR_UNKNOWN')
  except BaseException:faults.append('RUNTIME_POST_UNKNOWN')
  if any((out/(phase+'-cache')).exists() for phase in phases) or (out/'parent-cache').exists():faults.append('CACHE_CREATED')
  try:q.save(evidence/'artifact-inputs.json',evidence_index(q,evidence))
  except BaseException:faults.append('EVIDENCE_INDEX_UNKNOWN')
  q.save(evidence/'qualification.json',{'schema':'collector.optional-qualification.v1','status':'PASS' if not faults else 'FAILURE_OR_UNKNOWN',
    'faults':faults,'failure_details':details,'phases':results,'planned_phases':phases,'scope':'SOFTWARE_SYNTHETIC_ONLY_NOT_SERVICE_PG_NATIVE_PROVIDER_OR_AUTHORITY',
    'unit_and_modeled_axes_not_C1':True,'runtime_data_not_OS_DLL_trust':True,'cleanup':'5S_SHARED_REQUESTED_NOT_ENFORCED','old58_configuration':'UNCHANGED',
    'mandatory_and_authority_gates':'UNCHANGED_NO_WAIVER'})
 return bool(faults)


def main():
 mode,phase,paths,include=cli(sys.argv[1:]);q=bootstrap_helpers(paths['root'])
 need(sys.version_info[:3]==(3,12,10) and sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode,'PYTHON_PROFILE')
 prefix=paths['out']/('parent-cache' if mode=='--parent' else phase+'-cache')
 need(sys.pycache_prefix is not None and Path(sys.pycache_prefix)==prefix and not prefix.exists(),'FRESH_CACHE_PREFIX')
 need(Path(__file__).absolute()==paths['root']/'tools/collector/qualify.py','ROOT_SCRIPT_IDENTITY')
 for role in ('root',*INPUTS):q.ordinary(paths[role])
 if mode=='--child':child(q,phase,paths,paths['out']);return 0
 return parent(q,paths,include)


if __name__=='__main__':sys.exit(main())
