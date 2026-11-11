"""SOURCE PROPOSAL ONLY. Run only after a separate exact-source allocation."""
import os,sys,pathlib,stat,json,hashlib,time,subprocess,threading,importlib.util,importlib.machinery,unittest,tempfile
BASE=pathlib.Path(__file__).absolute().parent
PACKAGE=BASE/'gateway-canonical-one-case-inputs-review1-20261111'
SOURCE=BASE/'gateway-canonical-copy-source-20261111/raw816-clone';META=PACKAGE/'meta3-source'
REAL=pathlib.Path('C:/Users/LS-5/AppData/Local/Python/pythoncore-3.12-64/python.exe')
OUT=BASE/'gateway-canonical-one-case-review1-attempt1'
LIMIT=256*1024
CASE='_gateway_diag_case.GatewayAdapterTests.test_source_changed_after_calculation_refused'

def ordinary(path,file=False):
 path=path.absolute();parts=path.parts;current=pathlib.Path(parts[0])
 for i,part in enumerate(parts):
  if i:current=current/part
  s=current.lstat()
  if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&1024:raise ValueError('NONORDINARY_ANCESTRY')
  if not (stat.S_ISREG(s.st_mode) if file and i==len(parts)-1 else stat.S_ISDIR(s.st_mode)):raise ValueError('NONORDINARY_KIND')
  if file and i==len(parts)-1 and s.st_nlink!=1:raise ValueError('NONORDINARY_LINK_COUNT')
 return path
def bounded_bytes(path,size=None,cap=256*1024,pin=None):
 path=ordinary(path,True);before=path.lstat()
 if before.st_size>cap or (size is not None and before.st_size!=size):raise ValueError('BOUNDED_SIZE')
 with path.open('rb',buffering=0) as held:
  opened=os.fstat(held.fileno())
  if not metadata_matches(before,opened,False):raise ValueError('HELD_IDENTITY')
  chunks=[];count=0
  while count<=before.st_size:
   block=held.read(min(65536,before.st_size+1-count))
   if not block:break
   chunks.append(block);count+=len(block)
  raw=b''.join(chunks);after=os.fstat(held.fileno())
 if len(raw)!=before.st_size or not metadata_matches(opened,after,True) or not metadata_matches(before,ordinary(path,True).lstat(),True):raise ValueError('HELD_CHANGED')
 if pin is not None and hashlib.sha256(raw).hexdigest()!=pin:raise ValueError('RAW_PIN')
 return raw
def metadata_matches(left,right,same_api):
 for name in ('st_mode','st_dev','st_ino','st_size','st_mtime_ns','st_nlink')+(('st_ctime_ns',) if same_api else ()):
  a=getattr(left,name,None);b=getattr(right,name,None)
  if type(a) is not int or type(b) is not int:return False
  if name=='st_mode' and not same_api:
   if stat.S_IFMT(a)!=stat.S_IFMT(b):return False
  elif a!=b:return False
 a=getattr(left,'st_birthtime_ns',None);b=getattr(right,'st_birthtime_ns',None)
 if same_api and (a is None)!=(b is None):return False
 if (a is not None and type(a) is not int) or (b is not None and type(b) is not int):return False
 return a is None or b is None or a==b
def digest(path,cap=256*1024):return hashlib.sha256(bounded_bytes(path,cap=cap)).hexdigest()
def check_map(root,rows,buffers=None):
 ordinary(root);result={}
 for row in rows:
  p=ordinary(root/row['path'],True);raw=bounded_bytes(p,size=row['bytes'],cap=row['bytes'],pin=row['sha256'])
  if buffers is not None and row['path'] in ('tests/gateway_adapter/support.py','tests/gateway_adapter/test_gateway_adapter.py','strattester/research/gateway_adapter.py'):buffers[str(p)]=raw
  result[row['path']]={'bytes':len(raw),'sha256':row['sha256']}
 # Walk root-first: do not traverse reparse directories to establish extras.
 actual=set()
 for parent,dirs,files in os.walk(root,followlinks=False):
  for d in list(dirs):
   if d=='.git' and pathlib.Path(parent)==root:dirs.remove(d);continue
   ordinary(pathlib.Path(parent)/d)
  for f in files:actual.add(ordinary(pathlib.Path(parent)/f,True).relative_to(root).as_posix())
 if actual!=set(result):raise ValueError('SOURCE_EXTRAS')
 return result
def preflight(buffers=None):
 parsed=[]
 for p,size,h in [(PACKAGE/'receipt.json',2100,'2240d10b93bfb0dc957f5e501ee314c2c6e9d415512e602904666a8f673d0796'),(PACKAGE/'raw816-manifest.json',185062,'2fe093edb524377b8f5bc53bdeff28816dd74ec6d01c313ef18a950f0213ddd1'),(BASE/'gateway-one-case-runtime841-review1.json',129713,'cf6c3a323a56096bdbfbc6e4de91823cffa286d46ca410572067cabb632c99c1')]:
  raw=bounded_bytes(p,size=size,cap=size,pin=h);parsed.append(json.loads(raw,object_pairs_hook=unique_pairs,parse_constant=invalid_constant))
 receipt,rows,runtime=parsed
 if receipt['head']!='dfb5a2947070c8ebef0b22d9c97719b924909b39':raise ValueError('HEAD_PIN')
 if len(rows)!=816 or len(runtime)!=841:raise ValueError('INVENTORY_COUNT')
 # Runtime extras are not checked: this approved slice excludes site-packages,
 # caches, documentation and development headers. -I -S -B excludes site hooks.
 runtime_facts={}
 for row in runtime:
  p=ordinary(REAL.parent/row['path'],True)
  bounded_bytes(p,size=row['bytes'],cap=row['bytes'],pin=row['sha256'])
  runtime_facts[row['path']]=row['sha256']
 bounded_bytes(REAL,size=104952,cap=104952,pin='4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a')
 return {'source':check_map(SOURCE,rows,buffers),'meta':check_map(META,receipt['meta3']),'runtime':runtime_facts,'driver_sha256':digest(pathlib.Path(__file__))}

def unique_pairs(pairs):
 result={}
 for key,value in pairs:
  if key in result:raise ValueError('DUPLICATE_MANIFEST_KEY')
  result[key]=value
 return result
def invalid_constant(_):raise ValueError('INVALID_JSON_CONSTANT')

def runtime_flags(role):
 prefix=OUT/('pycache-'+role)
 if pathlib.Path(sys.executable).absolute()!=REAL or sys.version_info[:3]!=(3,12,10):raise ValueError('RUNTIME_VERSION')
 if not sys.flags.isolated or not sys.flags.no_site or not sys.flags.dont_write_bytecode:raise ValueError('RUNTIME_FLAGS')
 if sys.pycache_prefix!=str(prefix) or prefix.exists():raise ValueError('FRESH_PREFIX_REQUIRED')

def child():
 runtime_flags('child');buffers={};before=preflight(buffers);scratch=ordinary(OUT/'scratch');tempfile.tempdir=str(scratch)
 def owned(path):
  if isinstance(path,int):return
  p=pathlib.Path(os.fsdecode(path)).absolute()
  if not p.is_relative_to(scratch):raise PermissionError('WRITE_OUTSIDE_OWNED_TEMP')
  ordinary(p.parent)
  if p.exists():ordinary(p,not p.is_dir())
 def audit(event,args):
  if event.startswith('socket.') or event in ('subprocess.Popen','os.system','os.exec','os.posix_spawn','os.spawn','ctypes.dlopen'):raise PermissionError('EFFECT_DENIED')
  if event=='open':
   mode=args[1];flags=args[2]
   if (isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)):owned(args[0])
  if event in ('os.mkdir','os.remove','os.rmdir'):owned(args[0])
  if event in ('os.rename','os.replace'):owned(args[0]);owned(args[1])
 sys.addaudithook(audit)
 os.environ['GATEWAY_META_SOURCE_ROOT']=str(META)
 os.environ['GATEWAY_FIXTURE_SOURCE_REVISION']='dfb5a2947070c8ebef0b22d9c97719b924909b39'
 original_get_code=importlib.machinery.SourceFileLoader.get_code
 admitted_names={'support':SOURCE/'tests/gateway_adapter/support.py','_gateway_diag_case':SOURCE/'tests/gateway_adapter/test_gateway_adapter.py','_gateway_adapter_under_test':SOURCE/'strattester/research/gateway_adapter.py'}
 def admitted_get_code(loader,fullname):
  path=pathlib.Path(loader.path).absolute()
  if fullname in admitted_names:
   if path!=admitted_names[fullname] or str(path) not in buffers:raise ValueError('PROJECT_LOADER_IDENTITY')
   return compile(buffers[str(path)],str(path),'exec',dont_inherit=True)
  if path.is_relative_to(SOURCE):raise ValueError('UNADMITTED_PROJECT_LOADER')
  return original_get_code(loader,fullname)
 def load(name,path):
  spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module
 importlib.machinery.SourceFileLoader.get_code=admitted_get_code
 try:
  support=load('support',SOURCE/'tests/gateway_adapter/support.py')
  module=load('_gateway_diag_case',SOURCE/'tests/gateway_adapter/test_gateway_adapter.py')
  suite=unittest.TestSuite([module.GatewayAdapterTests('test_source_changed_after_calculation_refused')])
  if suite.countTestCases()!=1 or next(iter(suite)).id()!=CASE:raise ValueError('CASE_ID')
  result=unittest.TextTestRunner(verbosity=2).run(suite)
 finally:importlib.machinery.SourceFileLoader.get_code=original_get_code
 if preflight()!=before:raise ValueError('POST_SOURCE_DRIFT')
 if any(n=='meta_analyse' or n.startswith(('meta_analyse.','_stratt_gateway_meta_','_gateway_reference_meta')) for n in sys.modules):raise ValueError('META_NAMESPACE_RETAINED')
 approved={str((SOURCE/p).absolute()) for p in ('tests/gateway_adapter/support.py','tests/gateway_adapter/test_gateway_adapter.py','strattester/research/gateway_adapter.py')}
 runtime_paths={str((REAL.parent/p).absolute()) for p in before['runtime']}
 origins=[]
 for loaded in tuple(sys.modules.values()):
  origin=getattr(loaded,'__file__',None)
  if not origin:continue
  path=str(pathlib.Path(origin).absolute())
  if path not in approved and path not in runtime_paths and path!=str(pathlib.Path(__file__).absolute()):raise ValueError('UNAPPROVED_IMPORT_ORIGIN')
  if path in approved:origins.append(pathlib.Path(path).relative_to(SOURCE).as_posix())
 if set(origins)!=set(p.relative_to(SOURCE).as_posix() for p in map(pathlib.Path,approved)):raise ValueError('MISSING_PROJECT_ORIGIN')
 print(json.dumps({'schema':'gateway.one-case.child.v1','case':CASE,'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),'post_source_equal':True,'native_admission':False,'provider_admission':False},sort_keys=True))
 return 0 if result.wasSuccessful() and result.testsRun==1 and not result.skipped else 1

def parent():
 runtime_flags('parent');before=preflight();ordinary(BASE)
 if OUT.exists():raise ValueError('ATTEMPT_ALREADY_CLAIMED')
 OUT.mkdir();scratch=OUT/'scratch';scratch.mkdir()
 facts={'schema':'gateway.one-case.parent.v1','scope':'LOCAL_DIAGNOSTIC_ONLY','case':CASE,'pre':before,'errors':[],'limits':{'observed_process_seconds':15,'separate_cleanup_readers_seconds':5,'combined_log_bytes':LIMIT},'child':None,'timing':'Observed process phase begins before Popen; source pre/post outside phase. Backend creation cannot be forcibly bounded; no strict wall-clock/kernel claim','admission':False}
 child_handle=None;readers=[];lock=threading.Lock();total=[0];exceeded=threading.Event();reader_errors=[]
 def reader(pipe,path):
  try:
   with path.open('xb') as output:
    while True:
     chunk=pipe.read(4096)
     if not chunk:break
     with lock:
      room=max(0,LIMIT-total[0]);total[0]+=len(chunk)
      if total[0]>LIMIT:exceeded.set()
     output.write(chunk[:room])
  except BaseException:reader_errors.append('READER_FAILURE');exceeded.set()
  finally:
   try:pipe.close()
   except BaseException:reader_errors.append('READER_CLOSE_FAILURE');exceeded.set()
 started=None
 try:
  clean_env={k:v for k,v in os.environ.items() if k.upper() in ('SYSTEMROOT','WINDIR','TEMP','TMP','COMSPEC')}
  clean_env['PYTHONIOENCODING']='utf-8'
  facts['creation_intent']=True
  started=time.monotonic()
  child_handle=subprocess.Popen([str(REAL),'-I','-S','-B','-X','pycache_prefix='+str(OUT/'pycache-child'),str(pathlib.Path(__file__).absolute()),'--child'],cwd=OUT,env=clean_env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0,creationflags=subprocess.CREATE_NO_WINDOW)
  facts['child']={'pid':child_handle.pid,'identity':'OWN_POPEN_HANDLE','retired':False}
  for pipe,name in [(child_handle.stdout,'stdout.log'),(child_handle.stderr,'stderr.log')]:
   t=threading.Thread(target=reader,args=(pipe,OUT/name),daemon=True);entry={'thread':t,'start_outcome':'UNKNOWN','pipe':pipe,'safe_to_close':False};readers.append(entry)
   try:t.start();entry['start_outcome']='STARTED'
   except BaseException:
    facts['errors'].append('READER_START_FAILURE');exceeded.set()
    try:
     if t.ident is not None:entry['start_outcome']='STARTED'
    except BaseException:facts['errors'].append('READER_START_IDENT_FAILURE')
    try:
     if t.is_alive():entry['start_outcome']='STARTED'
    except BaseException:facts['errors'].append('READER_START_ALIVE_FAILURE')
  while child_handle.poll() is None and not exceeded.is_set() and time.monotonic()-started<15:time.sleep(.01)
  facts['observed_process_seconds']=time.monotonic()-started
  if facts['observed_process_seconds']>=15:facts['errors'].append('OBSERVED_PROCESS_DEADLINE')
  if child_handle.poll() is None:facts['errors'].append('PROCESS_BUDGET_OR_OUTPUT_LIMIT')
 except BaseException:facts['errors'].append('CREATION_OR_MONITOR_FAILURE')
 finally:
  deadline=time.monotonic()+5
  if started is not None and 'observed_process_seconds' not in facts:
   facts['observed_process_seconds']=time.monotonic()-started
   if facts['observed_process_seconds']>=15:facts['errors'].append('OBSERVED_PROCESS_DEADLINE')
  if child_handle is not None:
   needs_retirement=True
   try:needs_retirement=child_handle.poll() is None
   except BaseException:facts['errors'].append('CLEANUP_POLL_FAILURE')
   if needs_retirement:
    facts['kill_required']=True
    try:child_handle.kill()
    except BaseException:facts['errors'].append('KILL_FAILURE')
   try:child_handle.wait(timeout=max(.001,deadline-time.monotonic()));facts['child'].update(retired=True,exit_code=child_handle.returncode)
   except BaseException:facts['errors'].append('RETIREMENT_UNKNOWN')
  else:facts['errors'].append('CREATION_OUTCOME_UNKNOWN')
  reader_uncertain=False
  for entry in readers:
   if entry['start_outcome']=='STARTED':
    try:entry['thread'].join(timeout=max(0,deadline-time.monotonic()))
    except BaseException:facts['errors'].append('READER_JOIN_FAILURE');reader_uncertain=True
    try:
     if entry['thread'].is_alive():facts['errors'].append('READER_RETIREMENT_UNKNOWN');reader_uncertain=True
     else:entry['safe_to_close']=True
    except BaseException:facts['errors'].append('READER_ALIVE_FAILURE');reader_uncertain=True
   else:
    facts['errors'].append('READER_START_OUTCOME_UNKNOWN');reader_uncertain=True
  if child_handle is not None:
   for pipe in (child_handle.stdout,child_handle.stderr):
    owners=[entry for entry in readers if entry['pipe'] is pipe]
    if owners and not all(entry['safe_to_close'] for entry in owners):continue
    try:
     if pipe is not None:pipe.close()
    except BaseException:facts['errors'].append('HELD_PIPE_CLOSE_FAILURE')
  facts['readers']=[{'start_outcome':entry['start_outcome'],'safe_to_close':entry['safe_to_close']} for entry in readers]
  facts['reader_cleanup_uncertain']=reader_uncertain
  facts['errors'].extend(reader_errors)
  if exceeded.is_set():facts['errors'].append('OUTPUT_LIMIT')
  # Delete only the exact owned scratch after verifying all descendants ordinary.
  try:
   if child_handle is None or not facts['child'].get('retired') or reader_uncertain:raise ValueError('CLEANUP_HELD_UNCERTAINTY')
   if scratch.parent!=OUT or scratch.name!='scratch':raise ValueError('CLEANUP_SCOPE')
   owned_files=[];owned_dirs=[]
   for p,dirs,files in os.walk(ordinary(scratch),followlinks=False):
    if time.monotonic()>=deadline:raise ValueError('CLEANUP_BUDGET')
    for n in dirs:ordinary(pathlib.Path(p)/n)
    owned_dirs.append(pathlib.Path(p))
    for n in files:owned_files.append(ordinary(pathlib.Path(p)/n,True))
   for p in owned_files:
    if time.monotonic()>=deadline:raise ValueError('CLEANUP_BUDGET')
    ordinary(p,True).unlink()
   for p in reversed(owned_dirs):
    if time.monotonic()>=deadline:raise ValueError('CLEANUP_BUDGET')
    ordinary(p).rmdir()
   facts['scratch_removed']=not scratch.exists()
  except BaseException:facts['errors'].append('SCRATCH_CLEANUP_UNCONFIRMED')
  facts['cleanup_readers_observed_seconds']=5-max(0,deadline-time.monotonic())
  try:facts['post']=preflight();facts['source_equal']=facts['post']==before
  except BaseException:facts['source_equal']=False;facts['errors'].append('POST_SOURCE_CHECK_FAILURE')
  if not facts['source_equal']:facts['errors'].append('SOURCE_DRIFT')
  facts['logs']={}
  for n in ('stdout.log','stderr.log'):
   try:
    raw=bounded_bytes(OUT/n,cap=LIMIT);facts['logs'][n]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
   except BaseException:facts['errors'].append('LOG_FACTS_FAILURE_'+n)
  facts['receipt_written']=False
  try:
   # Serialize a bounded receipt once. Source maps fit below the explicit2MiB cap.
   facts['receipt_written']=True;raw=(json.dumps(facts,indent=2)+'\n').encode()
   if len(raw)>2*1024*1024:raise ValueError('RECEIPT_SIZE')
   with (OUT/'receipt.json').open('xb') as f:f.write(raw)
  except BaseException:
   facts['receipt_written']=False;facts['errors'].append('RECEIPT_WRITE_FAILURE')
   try:
    with (OUT/'receipt-failure.json').open('x',encoding='utf-8') as f:json.dump({'child':facts['child'],'errors':facts['errors'],'receipt_written':False},f)
   except BaseException:facts['errors'].append('FALLBACK_RECEIPT_WRITE_FAILURE')
 summary={'child':facts['child'],'errors':facts['errors'],'receipt_written':facts['receipt_written']}
 if facts['receipt_written']:
  try:summary['receipt_sha256']=digest(OUT/'receipt.json',cap=2*1024*1024)
  except BaseException:facts['errors'].append('RECEIPT_READBACK_FAILURE')
 print(json.dumps(summary,sort_keys=True))
 return 0 if not facts['errors'] and facts['child'] and facts['child'].get('exit_code')==0 else 1

if __name__=='__main__':sys.exit(child() if sys.argv[1:]==['--child'] else parent())
