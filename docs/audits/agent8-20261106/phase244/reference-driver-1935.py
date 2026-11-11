"""SOURCE PROPOSAL ONLY. Run only after a separate exact-source allocation."""
import os,sys,pathlib,stat,json,hashlib,time,subprocess,threading,importlib.util,importlib.machinery,unittest,tempfile,types,_imp
BASE=pathlib.Path('C:/Users/LS-5/.codex/hosted-stock24-modeled4-5fcac99-20261111')
SOURCE=BASE/'source'
BINDINGS_SHA='f767d60b2c9ac8da5f27ca7b990723f2444892cb79bb43d989763863a09b118f'
CONTROL_FILES=('test_bootstrap_custody_source_controls.py','test_origin_admission_source_controls.py')
TARGETS=('.github/workflows/native-output-cap-assertion.yml','tools/ci/qualify_native_output_cap_assertion.py')
AUDITS=[]
REAL=pathlib.Path('C:/Users/LS-5/AppData/Local/Python/pythoncore-3.12-64/python.exe')
OUT=BASE/'allocated-modeled4-evidence'
LIMIT=256*1024
CASE='FOUR_INERT_STOCK24_SOURCE_CONTROLS'
CASES=['owned_custody_controls.BootstrapCustodyControls.test_actual_git_poll_failure_still_kills_and_waits_owned_handle',
       'owned_origin_controls.OriginsControls.test_actual_origin_function_refuses_unknown_file_before_reader',
       'owned_origin_controls.OriginsControls.test_actual_origin_function_accepts_actual_builtin_spec_only',
       'owned_origin_controls.OriginsControls.test_actual_origin_function_refuses_cache_outside_fresh_prefix']

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
def preflight(buffers=None):
 ordinary(BASE)
 raw=bounded_bytes(BASE/'BINDINGS.json',cap=16384,pin=BINDINGS_SHA)
 manifest=json.loads(raw,object_pairs_hook=unique_pairs,parse_constant=invalid_constant)
 if manifest['head']!='5fcac999b1daec75707010573606f486f6dccf4d' or manifest['tree']!='4104c38700aea12eecfd2db85b92fa77d019e6f0' or manifest['source_root']!=SOURCE.as_posix():
  raise ValueError('EXACT_MODELED_SOURCE_BINDING')
 proof_raw=bounded_bytes(BASE/'input-primary-git-proof.json',cap=16384,pin=manifest['primary_git_proof_sha256'])
 proof=json.loads(proof_raw,object_pairs_hook=unique_pairs,parse_constant=invalid_constant)
 if proof['head']!=manifest['head'] or proof['tree']!=manifest['tree'] or proof['files']!=1875 or proof['ledger_sha256']!=manifest['source_ledger_sha256']:raise ValueError('PRIMARY_PROOF_BINDING')
 raw=bounded_bytes(BASE/'source-ledger.json',cap=2097152,pin=manifest['source_ledger_sha256'])
 ledger=json.loads(raw,object_pairs_hook=unique_pairs,parse_constant=invalid_constant)
 raw=bounded_bytes(BASE/'runtime-ledger.json',size=167973,cap=167973,pin='3625b1be9c8ac3309ba2c974ad35a6b62c7f53e07031a6b4bc3e75b86d4f0046')
 runtime=json.loads(raw,object_pairs_hook=unique_pairs,parse_constant=invalid_constant)
 if len(ledger)!=1875 or len(runtime['files'])!=841:raise ValueError('EXACT_INVENTORY_COUNTS')
 bounded_bytes(REAL,size=104952,cap=104952,pin='4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a')
 runtime_facts={}
 for name,entry in runtime['files'].items():
  path=pathlib.Path(name)
  if not path.is_absolute() or not path.is_relative_to(REAL.parent):raise ValueError('RUNTIME_ROOT')
  bounded_bytes(path,size=entry['bytes'],cap=entry['bytes'],pin=entry['sha256'])
  runtime_facts[str(path)]=entry['sha256']
 source_facts={};expected_dirs={p.as_posix() for name in ledger for p in pathlib.Path(name).parents if p.as_posix()!='.'}
 for name,entry in ledger.items():
  relative=pathlib.Path(name)
  if relative.is_absolute() or '..' in relative.parts:raise ValueError('SOURCE_RELATIVE_PATH')
  data=bounded_bytes(SOURCE/relative,size=entry['bytes'],cap=entry['bytes'],pin=entry['sha256'])
  if hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()!=entry['git_blob']:raise ValueError('PRIMARY_GIT_BLOB_BINDING')
  source_facts[name]={'bytes':len(data),'sha256':entry['sha256']}
  if buffers is not None and name in TARGETS:buffers[name]=data
 actual=set();directories=set()
 for parent,dirs,files in os.walk(ordinary(SOURCE),followlinks=False):
  for name in dirs:
   path=ordinary(pathlib.Path(parent)/name);directories.add(path.relative_to(SOURCE).as_posix())
  for name in files:actual.add(ordinary(pathlib.Path(parent)/name,True).relative_to(SOURCE).as_posix())
 if actual!=set(ledger) or directories!=expected_dirs:raise ValueError('SOURCE_EXTRA_OR_MISSING')
 packet_facts={}
 for name,entry in manifest['controls'].items():
  if name not in CONTROL_FILES:raise ValueError('CONTROL_FILENAME')
  data=bounded_bytes(BASE/name,size=entry['bytes'],cap=32768,pin=entry['sha256'])
  packet_facts[name]=entry['sha256']
  if buffers is not None:buffers[name]=data
 if set(packet_facts)!=set(CONTROL_FILES):raise ValueError('CONTROL_CLOSURE')
 bounded_bytes(BASE/'CHILD-FUNCTION-SOURCE.py',cap=16384,pin=manifest['child_function_source_sha256'])
 if (OUT/'pycache-parent').exists() or (OUT/'pycache-child').exists():raise ValueError('EXISTING_BYTECODE_PREFIX')
 # Fixed-role actual file origins; these observations grant no native authority.
 allowed_packet={str(BASE/name) for name in CONTROL_FILES}|{str(pathlib.Path(__file__))}
 roles={'__main__':str(pathlib.Path(__file__)),
        'owned_custody_controls':str(BASE/CONTROL_FILES[0]),
        'owned_origin_controls':str(BASE/CONTROL_FILES[1])}
 rows=[];typing_module=sys.modules.get('typing')
 for name,module in list(sys.modules.items()):
  if type(module) is not types.ModuleType:
   if not (name in ('typing.io','typing.re') and type(typing_module) is types.ModuleType and module is vars(typing_module).get(name.split('.')[1]) and type(module) is vars(typing_module).get('_DeprecatedType')):raise ValueError('UNKNOWN_FILELESS_MODULE')
   rows.append({'name':name,'kind':'EXACT_TYPING_PSEUDO'});continue
  spec=vars(module).get('__spec__');filename=vars(module).get('__file__');cached=vars(module).get('__cached__')
  if filename is not None:
   if type(filename) is not str:raise ValueError('INVALID_MODULE_FILE')
   path=str(pathlib.Path(filename))
   if path not in runtime_facts and not (name in roles and path==roles[name] and path in allowed_packet):raise ValueError('UNAPPROVED_MODULE_FILE')
  if name in roles:
   if type(filename) is not str or pathlib.Path(filename)!=pathlib.Path(roles[name]) or spec is not None:raise ValueError('SOURCE_MODULE_ROLE')
  elif spec is None:raise ValueError('UNKNOWN_FILELESS_MODULE')
  elif spec.origin=='built-in':
   if spec.loader is not importlib.machinery.BuiltinImporter or not _imp.is_builtin(spec.name):raise ValueError('BUILTIN_MODULE_IDENTITY')
  elif spec.origin=='frozen':
   if spec.loader is not importlib.machinery.FrozenImporter or not _imp.is_frozen(spec.name):raise ValueError('FROZEN_MODULE_IDENTITY')
  elif filename is None or spec.origin!=filename or type(spec.loader) not in (importlib.machinery.SourceFileLoader,importlib.machinery.ExtensionFileLoader):raise ValueError('MODULE_ORIGIN_IDENTITY')
  if cached is not None:
   prefix=OUT/('pycache-child' if sys.argv[1:]==['--child'] else 'pycache-parent')
   if type(cached) is not str or not pathlib.Path(cached).is_relative_to(prefix) or pathlib.Path(cached).suffix!='.pyc':raise ValueError('MODULE_CACHE_OUTSIDE_PREFIX')
  rows.append({'name':name,'file':filename,'origin':getattr(spec,'origin',None)})
 if len(rows)>512:raise ValueError('MODULE_ROWS_BOUND')
 AUDITS.append({'rows':rows,'count':len(rows)})
 return {'source':source_facts,'runtime':runtime_facts,'packet':packet_facts,
         'driver_sha256':digest(pathlib.Path(__file__)),'raw_source_count':1875,
         'source_head':manifest['head'],'source_tree':manifest['tree'],
         'origin_admission_observed':True,'source_kind':manifest['source_kind']}


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
 runtime_flags('child');buffers={};before=preflight(buffers)
 scratch=ordinary(OUT/'scratch');tempfile.tempdir=str(scratch)
 def owned(path):
  if isinstance(path,int):return
  p=pathlib.Path(os.fsdecode(path)).absolute()
  if not p.is_relative_to(scratch):raise PermissionError('WRITE_OUTSIDE_OWNED_TEMP')
  ordinary(p.parent)
  if p.exists():ordinary(p,not p.is_dir())
 def audit(event,args):
  if event.startswith('socket.') or event in ('subprocess.Popen','os.system','os.exec','os.posix_spawn','os.spawn','ctypes.dlopen','sqlite3.connect'):raise PermissionError('MODELED4_EFFECT_DENIED')
  if event=='open':
   mode=args[1];flags=args[2]
   if (isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)):owned(args[0])
  if event in ('os.mkdir','os.remove','os.rmdir'):owned(args[0])
  if event in ('os.rename','os.replace'):owned(args[0]);owned(args[1])
 sys.addaudithook(audit)
 class HeldSource:
  def __init__(self,raw):self.raw=raw
  def read_bytes(self):return self.raw
 def load_controls(name,filename,target):
  raw=buffers[filename]
  module=types.ModuleType(name);module.__file__=str(BASE/filename)
  exec(compile(raw,module.__file__,'exec',dont_inherit=True),module.__dict__)
  # Original test methods and target SHA assertions are unchanged. Their ONLY
  # source read is redirected to this already held/pinned SAME byte buffer.
  module.SOURCE=HeldSource(buffers[target]);sys.modules[name]=module
  return module
 custody=load_controls('owned_custody_controls','test_bootstrap_custody_source_controls.py','.github/workflows/native-output-cap-assertion.yml')
 origins=load_controls('owned_origin_controls','test_origin_admission_source_controls.py','tools/ci/qualify_native_output_cap_assertion.py')
 suite=unittest.TestSuite([
  custody.BootstrapCustodyControls('test_actual_git_poll_failure_still_kills_and_waits_owned_handle'),
  origins.OriginsControls('test_actual_origin_function_refuses_unknown_file_before_reader'),
  origins.OriginsControls('test_actual_origin_function_accepts_actual_builtin_spec_only'),
  origins.OriginsControls('test_actual_origin_function_refuses_cache_outside_fresh_prefix')])
 collected=[test.id() for test in suite]
 if collected!=CASES or suite.countTestCases()!=4:raise ValueError('EXACT_FOUR_CASE_IDS')
 class Result(unittest.TextTestResult):
  def __init__(self,*args,**kwargs):
   super().__init__(*args,**kwargs);self.started_ids=[];self.succeeded_ids=[]
  def startTest(self,test):self.started_ids.append(test.id());super().startTest(test)
  def addSuccess(self,test):self.succeeded_ids.append(test.id());super().addSuccess(test)
 baseline={id(thread) for thread in threading.enumerate()}
 real_start=threading.Thread.start
 thread_start_calls=[]
 def deny_start(*args,**kwargs):
  thread_start_calls.append(True);raise AssertionError('MODELED4_THREAD_START_DENIED')
 result=None
 try:
  threading.Thread.start=deny_start
  result=unittest.TextTestRunner(verbosity=2,resultclass=Result).run(suite)
 finally:
  threading.Thread.start=real_start
 if thread_start_calls or any(id(thread) not in baseline for thread in threading.enumerate()):raise ValueError('MODELED4_THREAD_DRIFT')
 after=preflight()
 if after!=before:raise ValueError('POST_SOURCE_RUNTIME_PACKET_DRIFT')
 if any(name=='unified_system' or name.startswith('unified_system.') for name in sys.modules):raise ValueError('PROJECT_MODULE_IMPORTED')
 cache=OUT/'pycache-child'
 if cache.exists():raise ValueError('CHILD_CACHE_CREATED')
 success=(result is not None and result.wasSuccessful() and result.testsRun==4
          and not result.skipped and result.started_ids==CASES and result.succeeded_ids==CASES)
 body=dict(schema='stock24.modeled4.child.v1',scope='INERT_FUNCTION_MODELS_ONLY_NOT_HOSTED_OR_NATIVE',
           collected=collected,started=result.started_ids if result else [],succeeded=result.succeeded_ids if result else [],
           tests=result.testsRun if result else 0,failures=len(result.failures) if result else None,
           errors=len(result.errors) if result else None,skips=len(result.skipped) if result else None,
           post_source_runtime_packet_equal=True,source_files=1875,runtime_files=841,
           actual_qualifier_module_imported=False,target_powershell_git_process_fixtures=0,
           fresh_child_prefix_absent=True,thread_start_calls=len(thread_start_calls),
           native_admission=False,physical_admission=False,public_submit=False)
 print(json.dumps(body,sort_keys=True))
 return 0 if success else 1


def parent():
 ordinary(BASE);runtime_flags('parent');before=preflight()
 if OUT.exists():raise ValueError('ATTEMPT_ALREADY_CLAIMED')
 OUT.mkdir();scratch=OUT/'scratch';scratch.mkdir()
 facts={'schema':'stock24.modeled4.parent.v1','scope':'INERT_FOUR_MODELS_ONLY_NOT_HOSTED_NATIVE','case':CASE,'cases':CASES,'pre':before,'errors':[],'limits':{'observed_process_seconds':15,'separate_cleanup_readers_seconds':5,'combined_log_bytes':LIMIT},'child':None,'timing':'Observed process phase begins before Popen; source pre/post outside phase. Backend creation cannot be forcibly bounded; no strict wall-clock/kernel claim','admission':False}
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
  cleanup_started=time.monotonic()
  deadline=cleanup_started+5
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
  # Observe after ALL held-child/readers/scratch cleanup attempts. Cooperative
  # waits/checks cannot preempt a late kernel call; record uncapped elapsed and
  # refuse rather than clamping an overrun to the advertised budget.
  cleanup_finished=time.monotonic()
  cleanup_elapsed=cleanup_finished-cleanup_started
  facts['cleanup_readers_observed_seconds']=cleanup_elapsed
  facts['cleanup_readers_within_budget']=(type(cleanup_elapsed) in (int,float) and float('-inf')<cleanup_elapsed<float('inf') and 0<=cleanup_elapsed<=5)
  if not facts['cleanup_readers_within_budget']:facts['errors'].append('CLEANUP_OBSERVED_DEADLINE')
  try:facts['post']=preflight();facts['source_equal']=facts['post']==before
  except BaseException:facts['source_equal']=False;facts['errors'].append('POST_SOURCE_CHECK_FAILURE')
  if not facts['source_equal']:facts['errors'].append('SOURCE_DRIFT')
  facts['logs']={}
  for n in ('stdout.log','stderr.log'):
   try:
    raw=bounded_bytes(OUT/n,cap=LIMIT);facts['logs'][n]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
   except BaseException:facts['errors'].append('LOG_FACTS_FAILURE_'+n)
  facts['origin_audits']=AUDITS
  facts['receipt_written']=False
  try:
   # Serialize a bounded receipt once. Source maps fit below the explicit2MiB cap.
   facts['receipt_written']=True;raw=(json.dumps(facts,indent=2)+'\n').encode()
   if len(raw)>2*1024*1024:raise ValueError('RECEIPT_SIZE')
   with (OUT/'receipt.json').open('xb') as f:f.write(raw)
  except BaseException:
   facts['origin_audits']=AUDITS
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

if __name__=='__main__':
 if sys.argv[1:]==['--child']:sys.exit(child())
 if sys.argv[1:]!=['--allocated-parent-model4']:raise SystemExit('EXPLICIT_ROOT_ALLOCATION_REQUIRED')
 sys.exit(parent())
