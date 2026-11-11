"""UNEXECUTED single-purpose compiler diagnostic proposal; not runtime admission."""
import os,sys,pathlib,stat,json,hashlib,time,threading,subprocess,re,ctypes
from ctypes import wintypes as W
BASE=pathlib.Path(__file__).absolute().parent
PACKET=BASE/'math572-compile-only-source-packet-20261111'
OUT=BASE/'math572-compile7-review1-attempt1'
REAL=pathlib.Path('C:/Users/LS-5/AppData/Local/Python/pythoncore-3.12-64/python.exe')
CSC=pathlib.Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe')
CAP=8192
TOKEN='ROOT.A7.MATH572.COMPILE7.ONCE'

def ordinary(path,directory=False):
 if not path.is_absolute():raise ValueError('ABSOLUTE_REQUIRED')
 for p in (*reversed(path.parents),path):
  s=p.lstat();leaf=p==path
  if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&1024:raise ValueError('UNSAFE_PATH')
  if not (stat.S_ISDIR(s.st_mode) if not leaf or directory else stat.S_ISREG(s.st_mode)):raise ValueError('UNSAFE_TYPE')
 return s
def read_bound(path,size,sha):
 before=ordinary(path)
 if before.st_size!=size:raise ValueError('SIZE_PIN')
 with path.open('rb',buffering=0) as f:
  a=os.fstat(f.fileno())
  if (a.st_dev,a.st_ino,a.st_size)!=(before.st_dev,before.st_ino,before.st_size):raise ValueError('OPEN_IDENTITY')
  chunks=[];count=0
  while count<=size:
   block=f.read(min(65536,size+1-count))
   if not block:break
   count+=len(block);chunks.append(block)
  b=os.fstat(f.fileno())
 after=ordinary(path);raw=b''.join(chunks)
 if (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)!=(b.st_dev,b.st_ino,b.st_size,b.st_mtime_ns) or (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns):raise ValueError('READ_IDENTITY')
 if len(raw)!=size or hashlib.sha256(raw).hexdigest()!=sha:raise ValueError('RAW_PIN')
 return raw
def pinned(path,sha,cap=1024*1024):
 size=ordinary(path).st_size
 if size>cap:raise ValueError('INPUT_BOUND')
 return json.loads(read_bound(path,size,sha))
def snapshot():
 m=pinned(PACKET/'inputs-and-tool-manifest.json','371e17ca778f9f47ef69dacb3adbc1874054a924a7bbd615120e049f11bab54b')
 n=pinned(PACKET/'native-import-dependency-manifest.json','68ad65eb7310c4f1be34390de9b2c3cba51be3030f34ebec02ac12e739b96289')
 runtime=pinned(BASE/'gateway-one-case-runtime841-review1.json','cf6c3a323a56096bdbfbc6e4de91823cffa286d46ca410572067cabb632c99c1')
 if len(m['sources'])!=7 or len(runtime)!=841:raise ValueError('INPUT_COUNT')
 for row in m['sources']:read_bound(PACKET/'inputs'/row['compiler_name'],row['bytes'],row['sha256'])
 for row in m['selected_runtime_and_references']+n['native_selected']:read_bound(pathlib.Path(row['path']),row['bytes'],row['sha256'])
 for row in runtime:read_bound(REAL.parent/row['path'],row['bytes'],row['sha256'])
 return m,n,runtime

def main():
 if sys.argv[1:]!=['--allocation',TOKEN]:raise ValueError('EXPLICIT_NEW_ALLOCATION_REQUIRED')
 if sys.platform!='win32' or pathlib.Path(sys.executable).absolute()!=REAL or sys.version_info[:3]!=(3,12,10):raise ValueError('FIXED_RUNTIME')
 if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode) or sys.pycache_prefix!=str(OUT/'pycache-parent'):raise ValueError('RUNTIME_FLAGS')
 if OUT.exists() or OUT.is_symlink():raise ValueError('ATTEMPT_ALREADY_CLAIMED')
 before=snapshot();ordinary(BASE,True);OUT.mkdir();scratch=OUT/'scratch';scratch.mkdir();inputs=scratch/'inputs';inputs.mkdir()
 m=before[0]
 for row in m['sources']:
  raw=read_bound(PACKET/'inputs'/row['compiler_name'],row['bytes'],row['sha256'])
  with (inputs/row['compiler_name']).open('xb') as f:f.write(raw)
 refs=[r['path'] for r in m['selected_runtime_and_references'] if r['role']=='reference']
 target=scratch/'original7.dll'
 argv=[str(CSC),'/nologo','/noconfig','/nostdlib+','/target:library','/utf8output','/debug-','/warn:4','/out:'+str(target)]+['/reference:'+p for p in refs]+[r['compiler_name'] for r in m['sources']]
 # Custody APIs only. No generated assembly or source entrypoint is loaded.
 import _winapi,msvcrt
 k=ctypes.WinDLL('kernel32',use_last_error=True)
 class BASIC(ctypes.Structure):
  _fields_=[('PerProcessUserTimeLimit',ctypes.c_longlong),('PerJobUserTimeLimit',ctypes.c_longlong),('LimitFlags',W.DWORD),('MinimumWorkingSetSize',ctypes.c_size_t),('MaximumWorkingSetSize',ctypes.c_size_t),('ActiveProcessLimit',W.DWORD),('Affinity',ctypes.c_size_t),('PriorityClass',W.DWORD),('SchedulingClass',W.DWORD)]
 class IO(ctypes.Structure):_fields_=[(name,ctypes.c_ulonglong) for name in ('ReadOperationCount','WriteOperationCount','OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount')]
 class EXTENDED(ctypes.Structure):_fields_=[('BasicLimitInformation',BASIC),('IoInfo',IO),('ProcessMemoryLimit',ctypes.c_size_t),('JobMemoryLimit',ctypes.c_size_t),('PeakProcessMemoryUsed',ctypes.c_size_t),('PeakJobMemoryUsed',ctypes.c_size_t)]
 if (ctypes.sizeof(ctypes.c_void_p),ctypes.sizeof(BASIC),ctypes.sizeof(IO),ctypes.sizeof(EXTENDED))!=(8,64,48,144):raise ValueError('JOB_ABI_MISMATCH')
 k.CreateJobObjectW.argtypes=[ctypes.c_void_p,W.LPCWSTR];k.CreateJobObjectW.restype=W.HANDLE
 k.SetInformationJobObject.argtypes=[W.HANDLE,ctypes.c_int,ctypes.c_void_p,W.DWORD];k.SetInformationJobObject.restype=W.BOOL
 k.AssignProcessToJobObject.argtypes=[W.HANDLE,W.HANDLE];k.AssignProcessToJobObject.restype=W.BOOL
 k.TerminateJobObject.argtypes=[W.HANDLE,W.UINT];k.TerminateJobObject.restype=W.BOOL
 k.ResumeThread.argtypes=[W.HANDLE];k.ResumeThread.restype=W.DWORD
 record={'schema':'math572.compile7.proposal.v1','result':'DENY','errors':[],'source_head':m['head'],'source_tree':m['tree'],'native_runtime_admission':False,'output_cap':CAP,'observed_process_seconds_bound':10,'separate_cleanup_seconds_bound':5,'creation_intent':False,'child':None,'job_assigned_before_resume':False,'descendant_limit':1,'compiler_argv':argv,'startup_class':'UNKNOWN','source_post_equal':False}
 job=None;hp=None;ht=None;nul=None;read_handles=[];write_handles=[];threads=[];reader_attempts=set();write_attempts=set();writes_closed=set()
 stopped=threading.Event();overflow=threading.Event();watch_done=threading.Event();lock=threading.Lock();buffers={'stdout':bytearray(),'stderr':bytearray()};total=[0];start=None;exit_code=None;uncertain=False
 reader_state={name:{'started':False,'eof':False,'read_failed':False,'close_ok':False,'close_failed':False,'retired':False,'log_written':False} for name in buffers}
 def error(code):
  with lock:record['errors'].append(code)
 def terminate_owned():
  if job:
   try:
    if not k.TerminateJobObject(job,197):error('JOB_TERMINATE_FAILURE')
   except BaseException:error('JOB_TERMINATE_EXCEPTION')
  if hp is not None:
   needs_termination=True
   try:
    status=_winapi.WaitForSingleObject(hp,0)
    if status==0:needs_termination=False
    elif status!=258:error('PROCESS_POLL_UNKNOWN')
   except BaseException:error('PROCESS_POLL_FAILURE')
   if needs_termination:
    try:_winapi.TerminateProcess(hp,198)
    except BaseException:error('PROCESS_TERMINATE_FAILURE')
 def watchdog():
  try:
   if not watch_done.wait(max(0,10-(time.monotonic()-start))):error('WATCHDOG_DEADLINE');terminate_owned()
  except BaseException:error('WATCHDOG_FAILURE');terminate_owned()
 def reader(handle,name):
  stream=None
  with lock:reader_state[name]['started']=True
  try:
   stream=os.fdopen(msvcrt.open_osfhandle(handle,os.O_RDONLY|os.O_BINARY),'rb',buffering=0)
   while True:
    block=stream.read(1024)
    if not block:
     with lock:reader_state[name]['eof']=True
     break
    with lock:
     room=max(0,CAP-total[0]);total[0]+=len(block);buffers[name].extend(block[:room])
     if total[0]>CAP:overflow.set()
  except BaseException:
   with lock:reader_state[name]['read_failed']=True
   error('READER_FAILURE');overflow.set()
  finally:
   try:
    if stream is not None:stream.close()
    else:_winapi.CloseHandle(handle)
    with lock:reader_state[name]['close_ok']=True
   except BaseException:
    with lock:reader_state[name]['close_failed']=True
    error('READER_CLOSE_FAILURE')
 def start_thread(function,args=()):
  entry={'thread':threading.Thread(target=function,args=args,daemon=True),'outcome':'UNKNOWN','reader_name':args[1] if function is reader else None};threads.append(entry)
  try:entry['thread'].start();entry['outcome']='STARTED'
  except BaseException:
   error('THREAD_START_FAILURE')
   try:
    if entry['thread'].ident is not None:entry['outcome']='STARTED'
   except BaseException:error('THREAD_IDENT_FAILURE')
   try:
    if entry['thread'].is_alive():entry['outcome']='STARTED'
   except BaseException:error('THREAD_ALIVE_FAILURE')
   raise
 try:
  job=k.CreateJobObjectW(None,None)
  if not job:raise ValueError('JOB_CREATE')
  limits=EXTENDED();limits.BasicLimitInformation.LimitFlags=0x2000|0x8;limits.BasicLimitInformation.ActiveProcessLimit=1
  if not k.SetInformationJobObject(job,9,ctypes.byref(limits),ctypes.sizeof(limits)):raise ValueError('JOB_LIMITS')
  for name in ('stdout','stderr'):
   r,w=_winapi.CreatePipe(None,0);read_handles.append((r,name));write_handles.append(w);os.set_handle_inheritable(w,True)
  nul=os.open(os.devnull,os.O_RDONLY);stdin=msvcrt.get_osfhandle(nul);os.set_handle_inheritable(stdin,True)
  si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESTDHANDLES;si.hStdInput=stdin;si.hStdOutput=write_handles[0];si.hStdError=write_handles[1];si.lpAttributeList={'handle_list':[stdin,*write_handles]}
  env={'SystemRoot':'C:\\Windows','WINDIR':'C:\\Windows','TEMP':str(scratch),'TMP':str(scratch)}
  start=time.monotonic();start_thread(watchdog);record['creation_intent']=True
  hp,ht,pid,tid=_winapi.CreateProcess(str(CSC),subprocess.list2cmdline(argv),None,None,True,4|0x400|0x08000000,env,str(inputs),si)
  record['child']={'pid':pid,'identity':'OWN_RETURNED_PROCESS_HANDLE','retired':False}
  if time.monotonic()-start>=10:raise ValueError('LATE_CREATION')
  if not k.AssignProcessToJobObject(job,hp):raise ValueError('JOB_ASSIGN_DENIED')
  record['job_assigned_before_resume']=True
  for r,name in read_handles:
   reader_attempts.add(r);start_thread(reader,(r,name))
  for w in write_handles:
   write_attempts.add(w);_winapi.CloseHandle(w);writes_closed.add(w)
  fd=nul;nul=None
  try:os.close(fd)
  except BaseException:error('STDIN_CLOSE_UNKNOWN');uncertain=True;raise
  if time.monotonic()-start>=10:raise ValueError('LATE_RESUME_DENIED')
  if k.ResumeThread(ht)!=1:raise ValueError('RESUME_DENIED')
  while _winapi.WaitForSingleObject(hp,10)!=0 and not overflow.is_set() and time.monotonic()-start<10:pass
  record['observed_process_seconds']=time.monotonic()-start
  if record['observed_process_seconds']>=10:raise ValueError('PROCESS_DEADLINE')
  if overflow.is_set():raise ValueError('OUTPUT_CAP')
  if _winapi.WaitForSingleObject(hp,0)!=0:raise ValueError('PROCESS_NOT_RETIRED')
  exit_code=_winapi.GetExitCodeProcess(hp)
 except BaseException:error('COMPILE_OWNER_BODY_FAILURE')
 finally:
  cleanup_started=time.monotonic()
  deadline=cleanup_started+5;watch_done.set()
  if hp is not None:
   try:
    if _winapi.WaitForSingleObject(hp,0)!=0:terminate_owned()
   except BaseException:error('RETIREMENT_POLL_FAILURE');terminate_owned()
   try:
    if _winapi.WaitForSingleObject(hp,max(0,int((deadline-time.monotonic())*1000)))!=0:raise ValueError('WAIT_TIMEOUT')
    exit_code=_winapi.GetExitCodeProcess(hp);record['child'].update(retired=True,exit_code=exit_code)
   except BaseException:error('RETIREMENT_UNKNOWN');uncertain=True
  elif record['creation_intent']:error('CREATION_OUTCOME_UNKNOWN');uncertain=True
  for w in write_handles:
   if w in writes_closed:continue
   if w in write_attempts:error('WRITE_PIPE_CLOSE_UNKNOWN');uncertain=True;continue
   write_attempts.add(w)
   try:_winapi.CloseHandle(w);writes_closed.add(w)
   except BaseException:error('WRITE_PIPE_CLOSE_FAILURE');uncertain=True
  for r,name in read_handles:
   if r not in reader_attempts:
    try:_winapi.CloseHandle(r)
    except BaseException:error('UNSTARTED_READ_PIPE_CLOSE_FAILURE')
  if nul is not None:
   try:os.close(nul)
   except BaseException:error('STDIN_CLOSE_FAILURE')
  for entry in threads:
   if entry['outcome']!='STARTED':error('THREAD_START_UNKNOWN');uncertain=True;continue
   try:entry['thread'].join(timeout=max(0,deadline-time.monotonic()))
   except BaseException:error('THREAD_JOIN_FAILURE');uncertain=True
   try:
    if entry['thread'].is_alive():error('THREAD_RETIREMENT_UNKNOWN');uncertain=True
    elif entry['reader_name'] is not None:reader_state[entry['reader_name']]['retired']=True
   except BaseException:error('THREAD_STATE_UNKNOWN');uncertain=True
  record['cleanup_uncertain']=uncertain
  if not uncertain:
   for handle in (ht,hp,job):
    if handle is not None:
     try:_winapi.CloseHandle(handle)
     except BaseException:error('HELD_HANDLE_CLOSE_FAILURE')
  cleanup_finished=time.monotonic()
  cleanup_elapsed=cleanup_finished-cleanup_started
  record['cleanup_observed_seconds']=cleanup_elapsed
  record['cleanup_within_budget']=(type(cleanup_elapsed) in (int,float) and float('-inf')<cleanup_elapsed<float('inf') and 0<=cleanup_elapsed<=5)
  if not record['cleanup_within_budget']:error('CLEANUP_OBSERVED_DEADLINE')
  if time.monotonic()>=deadline:error('CLEANUP_DEADLINE')
  record['logs']={}
  with lock:captured={name:bytes(data) for name,data in buffers.items()}
  for name,data in captured.items():
   try:
    with (OUT/(name+'.original.bin')).open('xb') as f:f.write(data)
    record['logs'][name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    reader_state[name]['log_written']=True
   except BaseException:error('ORIGINAL_LOG_WRITE_FAILURE')
  record['generated_output_present']=False
  if not uncertain:
   try:
    if target.exists():
     size=ordinary(target).st_size
     if size>4*1024*1024:raise ValueError('OUTPUT_LIBRARY_BOUND')
     with target.open('rb') as f:raw=f.read(size+1)
     if len(raw)!=size:raise ValueError('OUTPUT_LIBRARY_CHANGED')
     record['generated_output_present']=True;record['generated_output_data']={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'execution':'NEVER_LOADED_OR_INVOKED'}
   except BaseException:error('OUTPUT_LIBRARY_DATA_FAILURE')
  try:record['source_post_equal']=snapshot()==before
  except BaseException:error('POST_SOURCE_FAILURE')
  if not record['source_post_equal']:error('SOURCE_DRIFT')
  try:
   for row in m['sources']:read_bound(inputs/row['compiler_name'],row['bytes'],row['sha256'])
   record['actual_compiler_input_copies_post_equal']=True
  except BaseException:error('COMPILER_INPUT_COPY_DRIFT')
  if overflow.is_set():error('OUTPUT_CAP')
  try:text=(captured['stdout']+b'\n'+captured['stderr']).decode('utf-8',errors='strict')
  except UnicodeDecodeError:error('COMPILER_OUTPUT_ENCODING');text=''
  diagnostics=[];allowed_output=True;expected_missing=False;unadmitted_lines=0
  allowed_pairs={('CS0246','OwnedPrivateDesktop'),('CS0246','PrivateDesktopException'),('CS0103','HostedPrivateDesktop')}
  for line in text.splitlines():
   if not line.strip():continue
   match=re.fullmatch(r'(?:.*[\\/])?S(\d{2})\.cs\((\d+),(\d+)\):\s*(error|warning)\s*(CS\d{4}):\s*(.*)',line)
   if match is None:allowed_output=False;unadmitted_lines+=1;continue
   ordinal,lineno,column,kind,code,message=match.groups();ordinal=int(ordinal)
   diagnostics.append({'source_ordinal':ordinal,'line':int(lineno),'column':int(column),'kind':kind,'code':code})
   pairs=[pair for pair in allowed_pairs if pair[0]==code and re.search(r'\b'+pair[1]+r'\b',message)]
   admitted=ordinal==3 and kind=='error' and len(pairs)==1
   if not admitted:allowed_output=False;unadmitted_lines+=1
   if admitted and code=='CS0246':expected_missing=True
  record['closed_diagnostics']=diagnostics
  record['unadmitted_nonempty_output_lines']=unadmitted_lines
  record['diagnostic_set_admitted']=bool(diagnostics) and allowed_output and expected_missing
  with lock:record['reader_states']={name:dict(state) for name,state in reader_state.items()}
  record['original_logs_complete']=not overflow.is_set() and not uncertain and len(record['logs'])==2 and all(state['started'] and state['eof'] and state['close_ok'] and state['retired'] and state['log_written'] and not state['read_failed'] and not state['close_failed'] for state in record['reader_states'].values())
  if exit_code in (0xC0000142,0xC0000135,0xC000007B):record['startup_class']='NATIVE_STARTUP_FAILURE_UNKNOWN_CAUSE'
  elif exit_code==1 and record['diagnostic_set_admitted']:record['startup_class']='COMPILER_MISSING_TYPE_DIAGNOSTIC_OBSERVED'
  elif expected_missing:record['startup_class']='UNKNOWN_MIXED_OR_UNADMITTED_COMPILER_OUTPUT'
  elif exit_code==0:record['startup_class']='UNEXPECTED_COMPILE_SUCCESS'
  else:record['startup_class']='UNKNOWN_OTHER_COMPILER_OR_STARTUP_FAILURE'
  if not record['errors'] and not uncertain and record['original_logs_complete'] and record['job_assigned_before_resume'] and record['startup_class']=='COMPILER_MISSING_TYPE_DIAGNOSTIC_OBSERVED':record['result']='EXPECTED_COMPILE_DIAGNOSTIC_OBSERVED_NOT_RUNTIME_PASS'
  record['whole_wallclock_claim']=False
  try:
   with (OUT/'receipt.json').open('x',encoding='utf-8') as f:json.dump(record,f,indent=2);f.write('\n')
  except BaseException:error('RECEIPT_WRITE_FAILURE');record['result']='DENY'
 print(json.dumps({'result':record['result'],'errors':record['errors'],'closed_diagnostics':record.get('closed_diagnostics',[]),'runtime_admission':False},sort_keys=True))
 return 0 if record['result'].startswith('EXPECTED_COMPILE_') else 1

if __name__=='__main__':sys.exit(main())
