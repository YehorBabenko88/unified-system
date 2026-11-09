"""Explicit own SUSPENDED owner-loss fixture. No authority, Resume or CPU load.

Never imports qualify_windows_job or PR52. No caller PID/handle can be supplied.
"""
import ctypes
from ctypes import wintypes as w
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import types
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from unified_system import gateway_worker as gw

class SupervisorLossError(RuntimeError):
    def __init__(self,origin,cleanup,observation):
        super().__init__('OWNED_SUPERVISOR_LOSS_UNQUALIFIED')
        self.origin_diagnostic=origin
        self.cleanup_diagnostics=tuple(cleanup)
        self.observation=observation

def _need(ok,code):
    if not ok:raise ValueError(code)

def _json(raw):
    _need(type(raw) is bytes and 0<len(raw)<=16384,'BOUNDED_OWN_FRAME_REQUIRED')
    def pairs(items):
        result={}
        for key,value in items:
            _need(key not in result,'DUPLICATE_FRAME_KEY');result[key]=value
        return result
    return json.loads(raw.decode('ascii'),object_pairs_hook=pairs,
        parse_constant=lambda _:(_ for _ in ()).throw(ValueError('NONFINITE_FRAME')))

def decode_ready(raw,*,expected_original_sha256):
    value=_json(raw)
    fields={'schema','node_id','incarnation_id','attempt_id','original_sha256','process_handle','pid',
            'creation_filetime','image','directory_name','directory_device','directory_inode',
            'inner_kill_on_close','resource_admitted_fields'}
    _need(type(value) is dict and set(value)==fields,'CLOSED_READY_FIELDS')
    _need(value['schema']=='a5.local-owned-supervisor-ready.v1','READY_SCHEMA')
    for key in ('node_id','incarnation_id','attempt_id'):
        try:gw._worker_uuid(value[key])
        except gw.WorkerUnavailable:raise ValueError('READY_UUID') from None
    _need(value['original_sha256']==expected_original_sha256 and re.fullmatch('[0-9a-f]{64}',expected_original_sha256),'ORIGINAL_MISMATCH')
    for key in ('process_handle','pid'):
        _need(type(value[key]) is int and 0<value[key]<1<<64,'READY_INTEGER_ID')
    for key in ('directory_device','directory_inode'):
        _need(type(value[key]) is int and value[key]>=0,'READY_DIRECTORY_ID')
    _need(type(value['creation_filetime']) is str and re.fullmatch('[1-9][0-9]{0,19}',value['creation_filetime']),'READY_CREATION_TIME')
    _need(type(value['image']) is str and 0<len(value['image'])<=1024,'READY_IMAGE')
    _need(type(value['directory_name']) is str and re.fullmatch('a5-owned-suspended-[A-Za-z0-9_-]{1,64}',value['directory_name']),'READY_DIRECTORY_NAME')
    _need(value['inner_kill_on_close'] is True and value['resource_admitted_fields']==[],'READY_NOT_ADMITTED')
    return value

def rejoin_denials(ready):
    """Old metadata never reconstructs a process/attempt or native job state."""
    worker=gw.GatewayWorker(node_id=ready['node_id'])
    for old in (ready,json.dumps(ready,sort_keys=True).encode('ascii')):
        for method in (worker.inspect_attempt,worker.abort_attempt):
            try:method(old)
            except gw.WorkerUnavailable:pass
            else:raise ValueError('OLD_DATA_ADOPTED')
    try:worker.start()
    except gw.WorkerUnavailable:pass
    else:raise ValueError('REJOIN_START_NOT_DENIED')
    return dict(outcome='UNKNOWN',old_data_rejected=True,incarnation_id=gw._PROCESS_INCARNATION,
        node_id=ready['node_id'],resume_calls=0,dispatch_authorized=False,prepared_workers=0)

def _api():
    k=gw._attempt_api()
    signatures={
        'CreateJobObjectW':([ctypes.c_void_p,w.LPCWSTR],w.HANDLE),
        'SetInformationJobObject':([w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD],w.BOOL),
        'AssignProcessToJobObject':([w.HANDLE,w.HANDLE],w.BOOL),
        'TerminateJobObject':([w.HANDLE,w.UINT],w.BOOL),
        'DuplicateHandle':([w.HANDLE,w.HANDLE,w.HANDLE,ctypes.POINTER(w.HANDLE),w.DWORD,w.BOOL,w.DWORD],w.BOOL),
        'GetProcessId':([w.HANDLE],w.DWORD),
        'PeekNamedPipe':([w.HANDLE,ctypes.c_void_p,w.DWORD,ctypes.c_void_p,ctypes.POINTER(w.DWORD),ctypes.c_void_p],w.BOOL)}
    for name,(args,result) in signatures.items():
        fn=getattr(k,name);fn.argtypes=args;fn.restype=result
    return k

def _grid(repository):
    raw=subprocess.check_output(['git','--no-replace-objects','-C',str(repository),'cat-file','blob',
        '40e9c8dc274a2746018bc1aa08d103cd0187cecc:grid/ml_windows_job.py'],timeout=10)
    _need(hashlib.sha256(raw).hexdigest()==gw._GRID_JOB_SHA,'GRID_PRIMARY_PIN')
    module=types.ModuleType('owned_loss_primary_grid');exec(compile(raw,'primary-grid-custody','exec'),module.__dict__)
    return module

def _outer_job(module,k,process_handle):
    # Fixed pinned Grid retirement method; direct retained assignment, no PID open.
    job=object.__new__(module.WindowsJob);job._kernel=k;job._job=k.CreateJobObjectW(None,None)
    _need(bool(job._job),'OUTER_JOB_CREATE')
    try:
        limits=gw._Extended();limits.basic.flags=0x2000
        _need(k.SetInformationJobObject(job._job,9,ctypes.byref(limits),ctypes.sizeof(limits)),'OUTER_KILL_ON_CLOSE_SET')
        readback=gw._Extended()
        _need(k.QueryInformationJobObject(job._job,9,ctypes.byref(readback),ctypes.sizeof(readback),None)
              and readback.basic.flags&0x2000,'OUTER_KILL_ON_CLOSE_QUERY')
        _need(k.AssignProcessToJobObject(job._job,process_handle),'OUTER_RETAINED_ASSIGN')
        member=w.BOOL()
        _need(k.IsProcessInJob(process_handle,job._job,ctypes.byref(member)) and member.value,'OUTER_MEMBERSHIP')
        return job
    except BaseException:
        job.close();raise

def _milliseconds(deadline,cap=5000):
    remaining=deadline-time.monotonic()
    if remaining<=0:raise TimeoutError('OWNED_MONOTONIC_DEADLINE')
    return max(1,min(cap,int(remaining*1000)))

def _frame(k,process,deadline):
    import msvcrt
    pipe=w.HANDLE(msvcrt.get_osfhandle(process.stdout.fileno()));raw=b''
    while True:
        _milliseconds(deadline)
        available=w.DWORD()
        _need(k.PeekNamedPipe(pipe,None,0,None,ctypes.byref(available),None),'OWN_PIPE_UNAVAILABLE')
        if available.value:
            raw+=os.read(process.stdout.fileno(),min(available.value,16385-len(raw)))
            _need(len(raw)<=16384,'OWN_FRAME_TOO_LARGE')
            if b'\n' in raw:
                body,rest=raw.split(b'\n',1);_need(not rest,'MULTIPLE_OWN_FRAMES');return body
        else:
            _need(k.WaitForSingleObject(int(process._handle),_milliseconds(deadline,10))==258,'OWN_PROCESS_EXITED_BEFORE_FRAME')

def _accounting(module,k,job):
    value=module._BasicAccounting()
    _need(k.QueryInformationJobObject(job._job,1,ctypes.byref(value),ctypes.sizeof(value),None),'OUTER_ACCOUNTING')
    return dict(active=int(value.ActiveProcesses),total=int(value.TotalProcesses),raw_hex=bytes(value).hex())

def _empty(module,k,job,deadline):
    while True:
        value=_accounting(module,k,job)
        if value['active']==0:return value
        k.WaitForSingleObject(k.GetCurrentProcess(),_milliseconds(deadline,10))

def _emit(value):
    raw=json.dumps(value,sort_keys=True,separators=(',',':')).encode('ascii')
    _need(len(raw)<16384,'OWN_CHILD_FRAME_TOO_LARGE')
    sys.stdout.buffer.write(raw+b'\n');sys.stdout.buffer.flush()

def _child(role,private_root,grid):
    if sys.stdin.buffer.read(1)!=b'A':return
    if role=='supervisor':
        try:_emit(dict(ok=True,observation=_qualify_owner_loss_core(grid)))
        except SupervisorLossError as error:
            _emit(dict(ok=False,origin=error.origin_diagnostic,cleanup=error.cleanup_diagnostics,observation=error.observation))
            raise SystemExit(1)
        return
    if role=='restart':
        with (Path(private_root)/'old-ready.json').open('rb') as stream:raw=stream.read(16385)
        ready=decode_ready(raw,expected_original_sha256=hashlib.sha256(_original()).hexdigest())
        _emit(rejoin_denials(ready));return
    worker=gw.GatewayWorker(node_id=str(uuid.uuid4()));attempt=worker.prepare_attempt(_original(),grid_source_root=grid)
    try:
        observation=worker.inspect_attempt(attempt);state=worker._record(attempt)
        directory=state['directory'];st=directory.stat()
        _need(directory.parent.resolve()==Path(private_root).resolve(),'OWN_TEMP_ROOT')
        _emit(dict(schema='a5.local-owned-supervisor-ready.v1',node_id=observation.declared_node_id,
            incarnation_id=observation.worker_incarnation_id,attempt_id=observation.attempt_id,
            original_sha256=observation.original_request_sha256,process_handle=int(state['proc'].process),
            pid=observation.child_pid,creation_filetime=observation.child_creation_filetime,image=observation.child_image,
            directory_name=directory.name,directory_device=st.st_dev,directory_inode=st.st_ino,
            inner_kill_on_close=bool(state['limits']['readback_limit_flags']&0x2000),resource_admitted_fields=[]))
        sys.stdin.buffer.read(1)  # Crash target blocks; never resumes the worker.
    finally:worker.abort_attempt(attempt)

def _original():
    with Path(__file__).with_name('target_native_mapping_fixtures').joinpath('a2-native13.FORMAT_ONLY.json').open('rb') as stream:
        raw=stream.read(16385)
    gw._worker_original(raw);return raw

def _retire_owner(process,deadline):
    """Never let failed termination/wait/close skip another retained closure."""
    errors=[]
    def attempt(stage,fn):
        try:fn()
        except BaseException as error:errors.append((stage,type(error).__name__,str(error)))
    def terminate_if_live():
        if process.poll() is None:process.terminate()
    attempt('own_owner_terminate',terminate_if_live)
    attempt('own_owner_wait',lambda:process.wait(timeout=_milliseconds(deadline)/1000))
    attempt('own_stdin_close',process.stdin.close)
    attempt('own_stdout_close',process.stdout.close)
    attempt('own_process_handle_close',process._handle.Close)
    return errors

def _qualify_owner_loss_core(grid_repository):
    """Only own processes; local observations never authorize distributed effects."""
    started=time.monotonic();deadline=started+30;k=_api();module=_grid(grid_repository)
    _need(hashlib.sha256(gw._DIRECT_INTERPRETER.read_bytes()).hexdigest()==gw._DIRECT_INTERPRETER_SHA,'OWNER_INTERPRETER_PIN')
    private=Path(tempfile.mkdtemp(prefix='a5-owner-loss-'));identity=private.stat();processes=[];jobs=[];duplicate=None;verified_duplicate=False
    result=dict(scope='LOCAL_OWN_OWNER_LOSS_NOT_NATIVE_RESTART',resume_calls=0,dispatch_authorized=False,
        resource_admitted_fields=[],rescue_needed=False,source_grid_sha256=gw._GRID_JOB_SHA,
        worker_source_sha256=hashlib.sha256(Path(gw.__file__).read_bytes()).hexdigest(),
        fixture_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    origin=None;cleanup=[]
    def spawn(role):
        env={key:os.environ[key] for key in ('SYSTEMROOT','WINDIR') if key in os.environ}
        env.update(TEMP=str(private),TMP=str(private))
        p=subprocess.Popen([str(gw._DIRECT_INTERPRETER),'-I','-B',str(Path(__file__).resolve()),'--fixture-child',role,str(private),str(grid_repository)],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,cwd=private,env=env,close_fds=True,creationflags=0x08000000)
        processes.append(p);_need(k.GetProcessId(int(p._handle))==p.pid,'OWN_RETAINED_OWNER_PID')
        owner_identity=gw._attempt_identity(k,int(p._handle))
        _need(Path(owner_identity[1])==gw._DIRECT_INTERPRETER.resolve(),'OWN_RETAINED_OWNER_IMAGE')
        result[role+'_process_identity']=dict(pid=p.pid,creation_filetime=owner_identity[0],image=owner_identity[1])
        job=_outer_job(module,k,int(p._handle));jobs.append(job)
        _need(k.WaitForSingleObject(int(p._handle),0)==258,'OWNER_NOT_LIVE_BEFORE_ARM')
        p.stdin.write(b'A');p.stdin.flush();return p,job
    try:
        owner,outer=spawn('owner');result['owner_pid']=owner.pid
        ready=decode_ready(_frame(k,owner,deadline),expected_original_sha256=hashlib.sha256(_original()).hexdigest());result['ready']=ready
        duplicate=w.HANDLE()
        _need(k.DuplicateHandle(int(owner._handle),ready['process_handle'],k.GetCurrentProcess(),ctypes.byref(duplicate),0x100000|0x1000|1,False,0),'DUPLICATE_OWN_PROCESS')
        actual=gw._attempt_identity(k,duplicate)
        _need(k.GetProcessId(duplicate)==ready['pid'] and actual==(ready['creation_filetime'],str(Path(ready['image']).resolve()))
            and Path(actual[1])==gw._DIRECT_INTERPRETER.resolve(),'OWN_DUPLICATE_IDENTITY')
        verified_duplicate=True
        _need(k.WaitForSingleObject(duplicate,0)==258,'WORKER_NOT_LIVE_BEFORE_OWNER_LOSS')
        owner.terminate();owner.wait(timeout=_milliseconds(deadline)/1000)
        result['owner_exit_observed']=True
        _need(k.WaitForSingleObject(duplicate,_milliseconds(deadline))==0,'OWNER_LOSS_DID_NOT_RETIRE_WORKER')
        result['worker_exit_observed']=True
        result['outer_accounting']=_empty(module,k,outer,deadline);result['outer_job_empty_observed']=True
        (private/'old-ready.json').write_text(json.dumps(ready,sort_keys=True,separators=(',',':')),encoding='ascii')
        restarted,restart_job=spawn('restart');result['restart_pid']=restarted.pid
        restart=_json(_frame(k,restarted,deadline))
        _need(type(restart) is dict and restart.get('outcome')=='UNKNOWN' and restart.get('old_data_rejected') is True
              and restart.get('prepared_workers')==0 and restart.get('dispatch_authorized') is False
              and restart.get('incarnation_id')!=ready['incarnation_id'],'RESTART_ADOPTED_OR_PREPARED')
        restarted.wait(timeout=_milliseconds(deadline)/1000);_need(restarted.returncode==0,'RESTART_PROCESS_FAILED')
        result['restart']=restart;result['restart_accounting']=_empty(module,k,restart_job,deadline)
    except BaseException as error:
        origin=(type(error).__name__,str(error));result['rescue_needed']=True
    finally:
        cleanup_deadline=time.monotonic()+10
        def record(stage,fn):
            try:fn()
            except BaseException as error:cleanup.append((stage,type(error).__name__,str(error)))
        for job in reversed(jobs):
            record('outer_retire',lambda job=job:job.terminate_and_wait(_milliseconds(cleanup_deadline)/1000))
            record('outer_close',job.close)
        for p in processes:
            cleanup.extend(_retire_owner(p,cleanup_deadline))
        if duplicate:
            def observe_duplicate_cleanup():
                if verified_duplicate and k.WaitForSingleObject(duplicate,0)!=0:
                    _need(k.TerminateProcess(duplicate,1),'OWN_DUPLICATE_RESCUE_TERMINATE')
                    _need(k.WaitForSingleObject(duplicate,_milliseconds(cleanup_deadline))==0,'OWN_DUPLICATE_EXIT_UNPROVEN')
            record('duplicate_exit_cleanup',observe_duplicate_cleanup)
            record('duplicate_close',lambda:_need(k.CloseHandle(duplicate),'OWN_DUPLICATE_CLOSE'))
        def clean_directory():
            st=private.lstat();_need((st.st_dev,st.st_ino)==(identity.st_dev,identity.st_ino) and not getattr(st,'st_file_attributes',0)&1024,'PRIVATE_ROOT_IDENTITY')
            for path in private.iterdir():
                ps=path.lstat();_need(path.parent==private and not getattr(ps,'st_file_attributes',0)&1024,'PRIVATE_CHILD_LINK')
                if path.name=='old-ready.json':path.unlink()
                else:
                    _need(path.name.startswith('a5-owned-suspended-') and path.is_dir(),'UNEXPECTED_PRIVATE_CHILD')
                    path.rmdir()  # Empty only; never recursive.
            private.rmdir()
        record('private_empty_cleanup',clean_directory)
    if origin or cleanup:raise SupervisorLossError(origin,cleanup,result)
    result['elapsed_seconds']=round(time.monotonic()-started,6);result['retained_handles_closed']=True
    return result

def qualify_owner_loss(grid_repository):
    """External watchdog retains outer custody of the qualification process.

    Child core has 30s plus 10s cleanup; watchdog reserves its last 10s of 50s
    for actual own termination/empty proof. No prepare can occur before ARM.
    """
    started=time.monotonic();hard_deadline=started+50;read_deadline=started+40
    k=_api();module=_grid(grid_repository)
    _need(hashlib.sha256(gw._DIRECT_INTERPRETER.read_bytes()).hexdigest()==gw._DIRECT_INTERPRETER_SHA,'WATCHDOG_INTERPRETER_PIN')
    private=Path(tempfile.mkdtemp(prefix='a5-loss-watchdog-'));private_id=private.stat()
    process=None;job=None;origin=None;cleanup=[];result={}
    try:
        env={key:os.environ[key] for key in ('SYSTEMROOT','WINDIR') if key in os.environ};env.update(TEMP=str(private),TMP=str(private))
        process=subprocess.Popen([str(gw._DIRECT_INTERPRETER),'-I','-B',str(Path(__file__).resolve()),'--fixture-child','supervisor',str(private),str(grid_repository)],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,cwd=private,env=env,close_fds=True,creationflags=0x08000000)
        identity=gw._attempt_identity(k,int(process._handle))
        _need(k.GetProcessId(int(process._handle))==process.pid and Path(identity[1])==gw._DIRECT_INTERPRETER.resolve(),'WATCHDOG_RETAINED_INTERPRETER_IDENTITY')
        job=_outer_job(module,k,int(process._handle))
        _need(k.WaitForSingleObject(int(process._handle),0)==258,'QUALIFIER_NOT_LIVE_BEFORE_ARM')
        process.stdin.write(b'A');process.stdin.flush()
        frame=_json(_frame(k,process,read_deadline))
        _need(type(frame) is dict and frame.get('ok') in (True,False),'QUALIFIER_RESULT_FRAME')
        if frame['ok'] is not True:
            result['qualifier_failure']=frame
            raise ValueError('QUALIFIER_REPORTED_ORIGINAL_FAILURE')
        result=frame['observation']
        _need(type(result) is dict,'QUALIFIER_OBSERVATION')
        process.wait(timeout=_milliseconds(read_deadline)/1000);_need(process.returncode==0,'QUALIFIER_PROCESS_FAILED')
        result['watchdog']=dict(qualification_pid=process.pid,creation_filetime=identity[0],image=identity[1],
            outer_job_assigned_before_arm=True,outer_accounting=_empty(module,k,job,read_deadline),
            total_budget_seconds=50,read_budget_seconds=40,cleanup_reserve_seconds=10)
    except BaseException as error:origin=(type(error).__name__,str(error))
    finally:
        def record(stage,fn):
            try:fn()
            except BaseException as error:cleanup.append((stage,type(error).__name__,str(error)))
        if job is not None:
            record('watchdog_outer_retire',lambda:job.terminate_and_wait(_milliseconds(hard_deadline)/1000))
            record('watchdog_outer_close',job.close)
        if process is not None:cleanup.extend(_retire_owner(process,hard_deadline))
        def clean_private():
            st=private.lstat()
            _need((st.st_dev,st.st_ino)==(private_id.st_dev,private_id.st_ino) and not getattr(st,'st_file_attributes',0)&1024,'WATCHDOG_PRIVATE_IDENTITY')
            private.rmdir()  # Failure artifacts remain; never recursively delete.
        record('watchdog_private_empty_cleanup',clean_private)
    if origin or cleanup:raise SupervisorLossError(origin,cleanup,result)
    result['watchdog']['elapsed_seconds']=round(time.monotonic()-started,6)
    return result

if __name__=='__main__':
    if len(sys.argv)!=5 or sys.argv[1]!='--fixture-child' or sys.argv[2] not in ('owner','restart','supervisor'):
        raise SystemExit('internal explicit own fixture child only')
    _child(sys.argv[2],sys.argv[3],sys.argv[4])
