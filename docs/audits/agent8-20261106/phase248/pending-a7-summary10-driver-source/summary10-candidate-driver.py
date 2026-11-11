"""UNEXECUTED SOURCE; separate Root allocation required for this lane."""
import os,sys,pathlib,stat,json,hashlib,time,subprocess,threading,importlib.util,importlib.machinery,unittest,tempfile,types,_imp,io
BASE=pathlib.Path('C:\\Users\\LS-5\\Documents\\Codex\\2026-11-06\\codex-agent-7-distributed-research-math\\outputs\\math572-summary10-bounded-driver-source-20261111')
PROFILE='candidate'
BINDINGS_SHA='8b3c717289b8a0cba6cdc6c50175f773f93a6f72bbbc1b2084e4e62c14c62fe2'
CONTROL_FILE="regression-actual-ast.py"
AUDITS=[]
REAL=pathlib.Path("C:/Users/LS-5/AppData/Local/Python/pythoncore-3.12-64/python.exe")
OUT=BASE/("allocated-summary10-"+PROFILE+"-attempt1")
LIMIT=256*1024
CASE="TEN_INERT_NEW_PUBLIC_SUMMARY_CONTRACT_CONTROLS"
CASES=['owned_compile7_controls.PublicSummaryV1Contract.test_empty_small_and_original_174_records', 'owned_compile7_controls.PublicSummaryV1Contract.test_arbitrary_paths_errors_and_symbols_stay_private', 'owned_compile7_controls.PublicSummaryV1Contract.test_256_257_event_boundary_honest_capping_and_deny', 'owned_compile7_controls.PublicSummaryV1Contract.test_failed_private_receipt_is_deny_without_fabricated_digest', 'owned_compile7_controls.PublicSummaryV1Contract.test_prior_deny_or_unknown_never_promotes', 'owned_compile7_controls.PublicSummaryV1Contract.test_combined_event_overflow_denies_without_fabricated_category_cap', 'owned_compile7_controls.PublicSummaryV1Contract.test_actual_projection_serialization_validation_faults_use_exact_fallback', 'owned_compile7_controls.PublicSummaryV1Contract.test_private_open_short_write_and_close_failure_exact_unavailable_fallback', 'owned_compile7_controls.PublicSummaryV1Contract.test_stdout_failure_has_one_attempt_nonzero_deny_no_delivery_claim', 'owned_compile7_controls.PublicSummaryV1Contract.test_actual_validator_refuses_promotion_types_digest_duplicate_or_framing']
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
def preflight(buffers=None):
 ordinary(BASE)
 raw=bounded_bytes(BASE/'BINDINGS.json',cap=16384,pin=BINDINGS_SHA)
 bindings=json.loads(raw,object_pairs_hook=unique_pairs,parse_constant=invalid_constant)
 if bindings['schema']!='math572.compile7.summary10.bindings.v1' or bindings['case_ids']!=CASES:raise ValueError('BINDINGS_PROFILE')
 if set(bindings['profiles'])!={'candidate'}:raise ValueError('PROFILE_SET')
 facts={}
 for role,entry in bindings['profiles'].items():
  path=pathlib.Path(entry['path']);data=bounded_bytes(path,size=entry['bytes'],cap=32768,pin=entry['sha256'])
  facts[role]={'path':str(path),'bytes':len(data),'sha256':entry['sha256']}
  if buffers is not None:buffers[role]=data
 entry=bindings['control'];data=bounded_bytes(pathlib.Path(entry['path']),size=entry['bytes'],cap=32768,pin=entry['sha256'])
 if pathlib.Path(entry['path'])!=BASE/CONTROL_FILE:raise ValueError('CONTROL_PATH')
 if buffers is not None:buffers['control']=data
 entry=bindings['runtime'];raw=bounded_bytes(pathlib.Path(entry['path']),size=entry['bytes'],cap=entry['bytes'],pin=entry['sha256'])
 runtime=json.loads(raw,object_pairs_hook=unique_pairs,parse_constant=invalid_constant)
 if len(runtime)!=841:raise ValueError('RUNTIME_COUNT')
 bounded_bytes(REAL,size=104952,cap=104952,pin='4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a')
 runtime_facts={}
 for row in runtime:
  path=REAL.parent/row['path'];bounded_bytes(path,size=row['bytes'],cap=row['bytes'],pin=row['sha256']);runtime_facts[str(path)]=row['sha256']
 if (OUT/'pycache-parent').exists() or (OUT/'pycache-child').exists():raise ValueError('EXISTING_BYTECODE_PREFIX')
 allowed_packet={str(BASE/CONTROL_FILE),str(pathlib.Path(__file__))}
 roles={'__main__':str(pathlib.Path(__file__)),'owned_compile7_controls':str(BASE/CONTROL_FILE)}
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
 return {'profiles':facts,'runtime':runtime_facts,'control_sha256':bindings['control']['sha256'],'driver_sha256':digest(pathlib.Path(__file__)),'origin_admission_observed':True,'profile':PROFILE}

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
  if event.startswith('socket.') or event in ('subprocess.Popen','os.system','os.exec','os.posix_spawn','os.spawn','ctypes.dlopen','sqlite3.connect'):raise PermissionError('SUMMARY10_EFFECT_DENIED')
  if event=='open':
   mode=args[1];flags=args[2]
   if (isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)):owned(args[0])
  if event in ('os.mkdir','os.remove','os.rmdir'):owned(args[0])
  if event in ('os.rename','os.replace'):owned(args[0]);owned(args[1])
 sys.addaudithook(audit)
 class HeldSource:
  def __init__(self,raw):self.raw=raw
  def open(self,mode):
   if mode!='rb':raise ValueError('HELD_READ_ONLY')
   return io.BytesIO(self.raw)
 module=types.ModuleType('owned_compile7_controls');module.__file__=str(BASE/CONTROL_FILE)
 exec(compile(buffers['control'],module.__file__,'exec',dont_inherit=True),module.__dict__)
 # Original frozen regression methods; only source-reader object rebound to held bytes.
 module.SOURCE=HeldSource(buffers['candidate']);module.SOURCE_SHA=before['profiles']['candidate']['sha256'];sys.modules[module.__name__]=module
 selected=[]
 for identity in CASES:
  prefix,classname,method=identity.split('.')
  if prefix!=module.__name__:raise ValueError('CASE_MODULE')
  selected.append(getattr(module,classname)(method))
 suite=unittest.TestSuite(selected);collected=[test.id() for test in suite]
 if collected!=CASES or suite.countTestCases()!=10:raise ValueError('EXACT_TEN_CASE_IDS')
 class Result(unittest.TextTestResult):
  def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.started_ids=[];self.succeeded_ids=[]
  def startTest(self,test):self.started_ids.append(test.id());super().startTest(test)
  def addSuccess(self,test):self.succeeded_ids.append(test.id());super().addSuccess(test)
 baseline={id(thread) for thread in threading.enumerate()};real_start=threading.Thread.start;thread_start_calls=[]
 def deny_start(*args,**kwargs):thread_start_calls.append(True);raise AssertionError('SUMMARY10_THREAD_START_DENIED')
 result=None
 try:
  threading.Thread.start=deny_start;result=unittest.TextTestRunner(verbosity=2,resultclass=Result).run(suite)
 finally:threading.Thread.start=real_start
 if thread_start_calls or any(id(thread) not in baseline for thread in threading.enumerate()):raise ValueError('SUMMARY10_THREAD_DRIFT')
 after=preflight()
 if after!=before:raise ValueError('POST_SOURCE_RUNTIME_PACKET_DRIFT')
 if (OUT/'pycache-child').exists():raise ValueError('CHILD_CACHE_CREATED')
 completed=(result is not None and result.testsRun==10 and result.started_ids==CASES and len(result.errors)==0 and not result.skipped and not result.expectedFailures and not result.unexpectedSuccesses)
 success=completed and result.wasSuccessful() and result.succeeded_ids==CASES
 body=dict(schema='math572.summary10.child.v1',scope='INERT_ACTUAL_FUNCTION_CONTROLS_NOT_COMPILER',profile=PROFILE,collected=collected,
           started=result.started_ids if result else [],succeeded=result.succeeded_ids if result else [],tests=result.testsRun if result else 0,
           failures=len(result.failures) if result else None,errors=len(result.errors) if result else None,skips=len(result.skipped) if result else None,expected_failures=len(result.expectedFailures) if result else None,unexpected_successes=len(result.unexpectedSuccesses) if result else None,
           exact_inventory_completed=completed,observed_success=success,post_source_runtime_packet_equal=True,runtime_files=841,
           full_controller_imported=False,compiler_processes=0,target_win32_calls=0,thread_start_calls=len(thread_start_calls),
           native_admission=False,physical_admission=False,public_submit=False)
 print(json.dumps(body,sort_keys=True));return 0 if success else 1

def parent():
 ordinary(BASE);runtime_flags('parent');before=preflight()
 if OUT.exists():raise ValueError('ATTEMPT_ALREADY_CLAIMED')
 OUT.mkdir();scratch=OUT/'scratch';scratch.mkdir()
 facts={'schema':'math572.summary10.parent.v1','scope':'INERT_TEN_NEW_CONTRACT_TESTS_NOT_COMPILER_OR_NATIVE','case':CASE,'cases':CASES,'pre':before,'errors':[],'limits':{'observed_process_seconds':15,'separate_cleanup_readers_seconds':5,'combined_log_bytes':LIMIT},'child':None,'timing':'Observed process phase begins before Popen; source pre/post outside phase. Backend creation cannot be forcibly bounded; no strict wall-clock/kernel claim','admission':False}
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

if __name__=="__main__":
 if sys.argv[1:]==["--child"]:sys.exit(child())
 if sys.argv[1:]!=["--allocated-parent-summary10"]:raise SystemExit("EXPLICIT_ROOT_ALLOCATION_REQUIRED")
 sys.exit(parent())
