"""SOURCE ONLY until explicit ROOT bounded review. Never job/runtime admission.

Fixed2 sequential cases, one VirtualAlloc per child; no retries/page touching.
Invoke only from an externally source-verified capsule after ROOT execution ACK.
"""
import ctypes as c
from ctypes import wintypes as w
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import types
from datetime import datetime, timezone

CASES = {'control': 8388608, 'overlimit': 335544320}
MAX_FRAME = 4096
MAX_TOTAL = 16384
WALL_SECONDS = 10
MIN_COMMIT = 2952790016
MIN_PHYSICAL = 1073741824
DIRECT_PYTHON = r'C:\Users\LS-5\AppData\Local\Python\pythoncore-3.12-64\python.exe'
DIRECT_PYTHON_SHA = '4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a'
DIRECT_DLL_SHA = '9a0e3435aaa680d868150f87ab3e388ad2eebc22f87e036155c7b4eda8cd2120'

def file_sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(65536),b''):digest.update(block)
    return digest.hexdigest()

class Refused(RuntimeError): pass
class DiagnosticFailure(Refused):
    def __init__(self,diagnostics):
        super().__init__('DIAGNOSTIC_FAILED_NO_QUALIFICATION')
        self.diagnostics=diagnostics
        self.completed_cases=[]

def error_record(error,stage):
    text=str(error)
    return dict(stage=stage,error_type=type(error).__name__,text=text[:512],text_truncated=len(text)>512,
                winerror=getattr(error,'winerror',None),errno=getattr(error,'errno',None),
                **stamp())

def origin_record(state,error,stage):
    if state['origin'] is None:
        state['origin']=error_record(error,stage);state['_origin_exception']=error
    elif error is not state.get('_origin_exception'):
        state['cleanup'].append(error_record(error,stage))

def public_diagnostics(state):
    return {key:value for key,value in state.items() if not key.startswith('_')}


def need(ok, code):
    if not ok: raise Refused(code)

def stamp():
    return {'utc_observation': datetime.now(timezone.utc).isoformat(),
            'monotonic_ns': str(time.monotonic_ns())}

class Startup(c.Structure):
    _fields_=[('cb',w.DWORD),('reserved',w.LPWSTR),('desktop',w.LPWSTR),('title',w.LPWSTR),
        ('x',w.DWORD),('y',w.DWORD),('xs',w.DWORD),('ys',w.DWORD),('xc',w.DWORD),('yc',w.DWORD),
        ('fill',w.DWORD),('flags',w.DWORD),('show',w.WORD),('reserved_size',w.WORD),
        ('reserved_bytes',c.c_void_p),('stdin',w.HANDLE),('stdout',w.HANDLE),('stderr',w.HANDLE)]
class StartupEx(c.Structure): _fields_=[('startup',Startup),('attributes',c.c_void_p)]
class Process(c.Structure):
    _fields_=[('process',w.HANDLE),('thread',w.HANDLE),('pid',w.DWORD),('tid',w.DWORD)]
class Security(c.Structure):
    _fields_=[('length',w.DWORD),('descriptor',c.c_void_p),('inherit',w.BOOL)]
class Performance(c.Structure):
    _fields_=[('cb',w.DWORD)]+[(n,c.c_size_t) for n in ('commit_total','commit_limit','commit_peak',
        'physical_total','physical_available','cache','kernel_total','kernel_paged','kernel_nonpaged','page_size')]+[
        ('handles',w.DWORD),('processes',w.DWORD),('threads',w.DWORD)]
class MemoryStatus(c.Structure):
    _fields_=[('length',w.DWORD),('load',w.DWORD)]+[(n,c.c_uint64) for n in
        ('total_physical','available_physical','total_pagefile','available_pagefile','total_virtual','available_virtual','available_extended_virtual')]
class ProcessMemory(c.Structure):
    _fields_=[('cb',w.DWORD),('faults',w.DWORD)]+[(n,c.c_size_t) for n in
        ('peak_working_set','working_set','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile','private_usage')]
class Pids(c.Structure):
    _fields_=[('assigned',w.DWORD),('count',w.DWORD),('ids',c.c_size_t*8)]

def api():
    need(os.name=='nt' and c.sizeof(c.c_void_p)==8 and c.sizeof(w.DWORD)==4,'WINDOWS_X64_REQUIRED')
    need(sys.version_info[:2]==(3,12) and sys.prefix==sys.base_prefix,'DIRECT_BASE_CP312_REQUIRED')
    need(Path(sys.executable).resolve()==Path(DIRECT_PYTHON).resolve(),'DIRECT_INTERPRETER_PATH_REQUIRED')
    need(not Path(DIRECT_PYTHON).with_name('pyvenv.cfg').exists(),'VENV_REFUSED')
    need(file_sha(DIRECT_PYTHON)==DIRECT_PYTHON_SHA,'DIRECT_INTERPRETER_HASH_MISMATCH')
    k=c.WinDLL('kernel32',use_last_error=True)
    signatures={
        'GetModuleHandleW':([w.LPCWSTR],w.HANDLE),
        'GetModuleFileNameW':([w.HANDLE,w.LPWSTR,w.DWORD],w.DWORD),
        'QueryFullProcessImageNameW':([w.HANDLE,w.DWORD,w.LPWSTR,c.POINTER(w.DWORD)],w.BOOL),
        'CreateProcessW':([w.LPCWSTR,w.LPWSTR,c.c_void_p,c.c_void_p,w.BOOL,w.DWORD,c.c_void_p,w.LPCWSTR,c.POINTER(StartupEx),c.POINTER(Process)],w.BOOL),
        'CreatePipe':([c.POINTER(w.HANDLE),c.POINTER(w.HANDLE),c.POINTER(Security),w.DWORD],w.BOOL),
        'SetHandleInformation':([w.HANDLE,w.DWORD,w.DWORD],w.BOOL),
        'InitializeProcThreadAttributeList':([c.c_void_p,w.DWORD,w.DWORD,c.POINTER(c.c_size_t)],w.BOOL),
        'UpdateProcThreadAttribute':([c.c_void_p,w.DWORD,c.c_size_t,c.c_void_p,c.c_size_t,c.c_void_p,c.c_void_p],w.BOOL),
        'DeleteProcThreadAttributeList':([c.c_void_p],None),
        'ReadFile':([w.HANDLE,c.c_void_p,w.DWORD,c.POINTER(w.DWORD),c.c_void_p],w.BOOL),
        'WriteFile':([w.HANDLE,c.c_void_p,w.DWORD,c.POINTER(w.DWORD),c.c_void_p],w.BOOL),
        'PeekNamedPipe':([w.HANDLE,c.c_void_p,w.DWORD,c.c_void_p,c.POINTER(w.DWORD),c.c_void_p],w.BOOL),
        'ResumeThread':([w.HANDLE],w.DWORD), 'CloseHandle':([w.HANDLE],w.BOOL),
        'WaitForSingleObject':([w.HANDLE,w.DWORD],w.DWORD),
        'TerminateProcess':([w.HANDLE,w.UINT],w.BOOL),
        'TerminateJobObject':([w.HANDLE,w.UINT],w.BOOL),
        'OpenProcess':([w.DWORD,w.BOOL,w.DWORD],w.HANDLE),
        'GetCurrentProcess':([],w.HANDLE),'GetCurrentProcessId':([],w.DWORD),
        'GetExitCodeProcess':([w.HANDLE,c.POINTER(w.DWORD)],w.BOOL),
        'GetProcessTimes':([w.HANDLE,*([c.POINTER(w.FILETIME)]*4)],w.BOOL),
        'K32GetProcessMemoryInfo':([w.HANDLE,c.POINTER(ProcessMemory),w.DWORD],w.BOOL),
        'K32GetPerformanceInfo':([c.POINTER(Performance),w.DWORD],w.BOOL),
        'GlobalMemoryStatusEx':([c.POINTER(MemoryStatus)],w.BOOL),
        'IsProcessInJob':([w.HANDLE,w.HANDLE,c.POINTER(w.BOOL)],w.BOOL),
        'VirtualAlloc':([c.c_void_p,c.c_size_t,w.DWORD,w.DWORD],c.c_void_p),
        'VirtualFree':([c.c_void_p,c.c_size_t,w.DWORD],w.BOOL),
    }
    for name,(args,result) in signatures.items():
        fn=getattr(k,name);fn.argtypes=args;fn.restype=result
    image=c.create_unicode_buffer(32768);length=w.DWORD(len(image))
    need(k.QueryFullProcessImageNameW(k.GetCurrentProcess(),0,image,c.byref(length)),'ACTUAL_IMAGE_QUERY_FAILED')
    need(Path(image.value).resolve()==Path(DIRECT_PYTHON).resolve(),'ACTUAL_IMAGE_NOT_DIRECT_CP312')
    dll=k.GetModuleHandleW('python312.dll');need(dll,'ACTUAL_PYTHON_DLL_MISSING')
    dll_path=c.create_unicode_buffer(32768);n=k.GetModuleFileNameW(dll,dll_path,len(dll_path))
    expected_dll=Path(DIRECT_PYTHON).with_name('python312.dll')
    need(0<n<len(dll_path) and Path(dll_path.value).resolve()==expected_dll.resolve(),'ACTUAL_DLL_PATH_MISMATCH')
    need(file_sha(expected_dll)==DIRECT_DLL_SHA,'ACTUAL_DLL_HASH_MISMATCH')
    return k

def host_commit(k):
    p=Performance();p.cb=c.sizeof(p);m=MemoryStatus();m.length=c.sizeof(m)
    need(k.K32GetPerformanceInfo(c.byref(p),c.sizeof(p)) and k.GlobalMemoryStatusEx(c.byref(m)),'HOST_COMMIT_UNAVAILABLE')
    need(p.page_size>0 and p.commit_limit>=p.commit_total,'HOST_COMMIT_INVALID')
    available=(p.commit_limit-p.commit_total)*p.page_size
    result=dict(**stamp(),available_commit_bytes=str(available),available_physical_bytes=str(m.available_physical),
                commit_total_pages=str(p.commit_total),commit_limit_pages=str(p.commit_limit),page_size=str(p.page_size))
    need(available>=MIN_COMMIT and m.available_physical>=MIN_PHYSICAL,'HOST_COMMIT_MARGIN_REFUSED')
    return result

def process_snapshot(k,handle):
    memory=ProcessMemory();memory.cb=c.sizeof(memory)
    need(k.K32GetProcessMemoryInfo(handle,c.byref(memory),c.sizeof(memory)),'PRIVATE_COMMIT_QUERY_FAILED')
    times=[w.FILETIME() for _ in range(4)]
    need(k.GetProcessTimes(handle,*[c.byref(v) for v in times]),'PROCESS_TIME_QUERY_FAILED')
    return dict(**stamp(),creation_filetime=str((times[0].dwHighDateTime<<32)|times[0].dwLowDateTime),
                private_commit_bytes=str(memory.private_usage),working_set_bytes=str(memory.working_set),
                raw_memory_hex=bytes(memory).hex(),structure_size=c.sizeof(memory))

def emit(value):
    raw=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
    need(len(raw)+1<=MAX_FRAME,'CHILD_FRAME_CAP')
    sys.stdout.buffer.write(raw+b'\n');sys.stdout.buffer.flush()

def command(expected):
    raw=sys.stdin.buffer.readline(17)
    need(raw==expected+b'\n','CHILD_COMMAND_REFUSED')

def _child(mode,state):
    need(mode in CASES,'FIXED_CASE_REQUIRED');k=api();handle=k.GetCurrentProcess();pointer=None;free_attempted=False
    try:
        emit(dict(phase='BEFORE',pid=str(k.GetCurrentProcessId()),snapshot=process_snapshot(k,handle)))
        command(b'ALLOC')
        c.set_last_error(0)
        pointer=k.VirtualAlloc(None,CASES[mode],0x3000,0x04)
        allocation_error=c.get_last_error()  # IMMEDIATELY after this native call.
        emit(dict(phase='ALLOCATED',requested_bytes=str(CASES[mode]),pointer=str(int(pointer or 0)),
                  native_success=bool(pointer),last_error=str(allocation_error),
                  last_error_semantics='FAILURE_CODE_ONLY' if not pointer else 'UNDEFINED_ON_SUCCESS',
                  snapshot=process_snapshot(k,handle)))
        command(b'FREE')
        free_result=None;free_error=None
        if pointer:
            free_attempted=True;c.set_last_error(0);free_result=bool(k.VirtualFree(pointer,0,0x8000));free_error=c.get_last_error()
            if free_result:pointer=None
        emit(dict(phase='FREED',free_attempted=free_attempted,free_result=free_result,
                  last_error=None if free_error is None else str(free_error),
                  last_error_semantics=('FAILURE_CODE_ONLY' if free_result is False else
                                        'UNDEFINED_ON_SUCCESS' if free_attempted else 'NOT_CALLED'),
                  snapshot=process_snapshot(k,handle)))
        need(not pointer,'OWNED_VIRTUALFREE_FAILED_NO_RETRY')
        command(b'EXIT');emit(dict(phase='EXITING'));return 0
    except BaseException as error:
        origin_record(state,error,'child_body');raise
    finally:
        if pointer and not free_attempted:
            # This exact pointer came from our one allocation, never caller input.
            free_attempted=True
            try:
                c.set_last_error(0);released=k.VirtualFree(pointer,0,0x8000);release_error=c.get_last_error()
                if not released:
                    state['cleanup'].append(dict(stage='child_virtualfree',result=False,native_error=release_error,**stamp()))
            except BaseException as error:
                state['cleanup'].append(error_record(error,'child_virtualfree_exception'))

def child(mode):
    state=dict(origin=None,cleanup=[])
    try:result=_child(mode,state)
    except BaseException as error:
        origin_record(state,error,'child_prerequisite_or_propagated_error');result=3
    if state['origin'] is not None or state['cleanup']:
        emit(dict(phase='CHILD_ERROR',diagnostics=public_diagnostics(state)))
        return 3
    return result

def load_owners(grid_repository):
    source=subprocess.check_output(['git','--no-replace-objects','-C',str(grid_repository),'show',
        '40e9c8dc274a2746018bc1aa08d103cd0187cecc:grid/ml_windows_job.py'],timeout=10)
    need(hashlib.sha256(source).hexdigest()=='7fd6223de3e28052b1254fa9e33e638132c6db89388bbb2d994b35970802a25c','GRID_SOURCE_MISMATCH')
    grid=types.ModuleType('diagnostic_pinned_grid');exec(compile(source,'primary-grid-job','exec'),grid.__dict__)
    wrapper=Path(__file__).resolve().parents[2]/'unified_system/gateway_worker.py';raw=wrapper.read_bytes()
    need(hashlib.sha256(raw).hexdigest()=='5458dc5de7cfcdb9d9b77e904b6c1161fff375b3de3dc9bd759ae726e5290436','WRAPPER_SOURCE_MISMATCH')
    worker=types.ModuleType('diagnostic_pinned_worker');exec(compile(raw,'primary-worker-wrapper','exec'),worker.__dict__)
    return grid,worker

def _one_case(mode,grid,worker,state):
    need(mode in CASES,'FIXED_CASE_REQUIRED');k=api();host_before=host_commit(k)
    state['partial']['host_before']=host_before
    proc=Process();job=None;created=False;quiescent=False;extra_handles=[];attributes=None
    stop=threading.Event();watch=None;watch_result=[];deadline=time.monotonic()+WALL_SECONDS
    def check_deadline():need(time.monotonic()<deadline and not watch_result,'PARENT_WALL_DEADLINE')
    def close(handle):
        if handle:need(k.CloseHandle(handle),'PIPE_HANDLE_CLOSE_FAILED')
    try:
        security=Security(c.sizeof(Security),None,True)
        in_read=w.HANDLE();in_write=w.HANDLE();out_read=w.HANDLE();out_write=w.HANDLE()
        need(k.CreatePipe(c.byref(in_read),c.byref(in_write),c.byref(security),4096),'STDIN_PIPE_FAILED')
        extra_handles.extend([in_read.value,in_write.value])
        need(k.CreatePipe(c.byref(out_read),c.byref(out_write),c.byref(security),4096),'STDOUT_PIPE_FAILED')
        extra_handles.extend([out_read.value,out_write.value])
        need(k.SetHandleInformation(in_write,1,0) and k.SetHandleInformation(out_read,1,0),'PIPE_INHERITANCE_FAILED')
        size=c.c_size_t();k.InitializeProcThreadAttributeList(None,1,0,c.byref(size))
        need(0<size.value<=65536,'ATTRIBUTE_LIST_SIZE_REFUSED');buffer=c.create_string_buffer(size.value)
        need(k.InitializeProcThreadAttributeList(buffer,1,0,c.byref(size)),'ATTRIBUTE_LIST_INIT_FAILED');attributes=buffer
        inherited=(w.HANDLE*2)(in_read.value,out_write.value)
        need(k.UpdateProcThreadAttribute(buffer,0,0x00020002,inherited,c.sizeof(inherited),None,None),'HANDLE_LIST_FAILED')
        startup=StartupEx();startup.startup.cb=c.sizeof(startup);startup.attributes=c.cast(buffer,c.c_void_p)
        startup.startup.flags=0x100;startup.startup.stdin=in_read;startup.startup.stdout=out_write;startup.startup.stderr=out_write
        env={key:os.environ[key] for key in ('SYSTEMROOT','WINDIR','TEMP','TMP') if key in os.environ}
        env_block=c.create_unicode_buffer('\0'.join(key+'='+value for key,value in sorted(env.items()))+'\0\0')
        script=str(Path(__file__).resolve());argv=[sys.executable,'-I','-B',script,'--internal-child',mode]
        cmd=c.create_unicode_buffer(subprocess.list2cmdline(argv))
        with tempfile.TemporaryDirectory(prefix='a5-virtualalloc-reviewed-') as cwd:
            try:
                check_deadline()
                need(k.CreateProcessW(sys.executable,cmd,None,None,True,0x4|0x400|0x80000|0x08000000,
                                      env_block,cwd,c.byref(startup),c.byref(proc)),'SUSPENDED_CREATE_FAILED')
                created=True;job=grid.WindowsJob(proc.pid,resume_primary_thread=False)
                limits=worker._configure_retained_job(job,expected_job_type=grid.WindowsJob,owned_process_handle=proc.process)
                host_pre_resume=host_commit(k)
                state['partial']['limits']=limits;state['partial']['host_pre_resume']=host_pre_resume
                retained_watchdog_job_handle=job._job
                def watchdog():
                    if not stop.wait(max(0,deadline-time.monotonic())):
                        result=k.TerminateJobObject(retained_watchdog_job_handle,2)
                        watch_result.append(dict(result=bool(result),last_error=c.get_last_error(),**stamp()))
                watch=threading.Thread(target=watchdog,daemon=True);watch.start()
                need(k.ResumeThread(proc.thread)!=0xffffffff,'PRIMARY_RESUME_FAILED')
                close(in_read.value);extra_handles.remove(in_read.value)
                close(out_write.value);extra_handles.remove(out_write.value)
                received=0;pending=b''
                def send(data):
                    check_deadline();need(len(data)<=16,'PARENT_COMMAND_CAP');n=w.DWORD()
                    need(k.WriteFile(in_write,data,len(data),c.byref(n),None) and n.value==len(data),'PARENT_COMMAND_WRITE_FAILED')
                def frame():
                    nonlocal received,pending
                    while b'\n' not in pending:
                        check_deadline();available=w.DWORD()
                        need(k.PeekNamedPipe(out_read,None,0,None,c.byref(available),None),'CHILD_PIPE_QUERY_FAILED')
                        need(available.value<=MAX_TOTAL-received,'CHILD_TOTAL_CAP')
                        if available.value:
                            size=min(available.value,MAX_FRAME-len(pending));need(size>0,'CHILD_FRAME_CAP')
                            data=c.create_string_buffer(size);n=w.DWORD()
                            need(k.ReadFile(out_read,data,size,c.byref(n),None) and n.value>0,'CHILD_PIPE_READ_FAILED')
                            received+=n.value;pending+=data.raw[:n.value]
                            need(received<=MAX_TOTAL and len(pending)<=MAX_FRAME,'CHILD_IPC_CAP')
                        else:
                            need(k.WaitForSingleObject(proc.process,10)==258,'CHILD_EXITED_BEFORE_FRAME')
                    raw,pending=pending.split(b'\n',1);need(len(raw)+1<=MAX_FRAME,'CHILD_FRAME_CAP')
                    value=json.loads(raw.decode('ascii'))
                    state['partial'].setdefault('received_frames',[]).append(value)
                    return value
                def job_snapshot():
                    e=worker._Extended();a=grid._BasicAccounting();ids=Pids()
                    for kind,value in ((9,e),(1,a),(3,ids)):
                        need(job._kernel.QueryInformationJobObject(job._job,kind,c.byref(value),c.sizeof(value),None),'JOB_SNAPSHOT_FAILED')
                    need(ids.count<=8 and ids.assigned<=8,'JOB_PROCESS_CAP')
                    return dict(**stamp(),extended_hex=bytes(e).hex(),basic_accounting_hex=bytes(a).hex(),
                                pids=[str(ids.ids[i]) for i in range(ids.count)],
                                sizes=dict(extended=c.sizeof(e),basic=c.sizeof(a),pids=c.sizeof(ids)))
                before=frame();state['partial']['child_before']=before
                need(before.get('phase')=='BEFORE','BEFORE_PHASE_REQUIRED')
                inventory=job_snapshot();pid=int(before['pid']);need(str(pid) in inventory['pids'],'REPORTED_CHILD_NOT_OWNED')
                child_handle=k.OpenProcess(0x400|0x10,False,pid);need(child_handle,'OWNED_CHILD_HANDLE_FAILED');extra_handles.append(child_handle)
                member=w.BOOL();need(k.IsProcessInJob(child_handle,job._job,c.byref(member)) and member.value,'CHILD_JOB_MEMBERSHIP_FAILED')
                actual_before=process_snapshot(k,child_handle)
                need(actual_before['creation_filetime']==before['snapshot']['creation_filetime'],'CHILD_CREATION_MISMATCH')
                send(b'ALLOC\n');during=frame();need(during.get('phase')=='ALLOCATED','ALLOCATED_PHASE_REQUIRED')
                during_job=job_snapshot();during_process=process_snapshot(k,child_handle)
                state['partial'].update(child_during=during,job_during=during_job,parent_during=during_process)
                send(b'FREE\n');after=frame();need(after.get('phase')=='FREED','FREED_PHASE_REQUIRED')
                after_job=job_snapshot();after_process=process_snapshot(k,child_handle)
                state['partial'].update(child_after=after,job_after=after_job,parent_after=after_process)
                send(b'EXIT\n');exiting=frame();need(exiting=={'phase':'EXITING'},'EXIT_PHASE_REQUIRED')
                need(k.WaitForSingleObject(proc.process,1000)==0,'OWNED_PARENT_EXIT_UNPROVEN')
                need(k.WaitForSingleObject(child_handle,1000)==0,'OWNED_REPORTING_CHILD_EXIT_UNPROVEN')
                parent_exit=w.DWORD();child_exit=w.DWORD()
                need(k.GetExitCodeProcess(proc.process,c.byref(parent_exit)) and
                     k.GetExitCodeProcess(child_handle,c.byref(child_exit)),'OWNED_EXIT_CODE_UNAVAILABLE')
                need(parent_exit.value==child_exit.value==0,'OWNED_CHILD_NONZERO_EXIT')
                stop.set();watch.join(1)
                need(not watch.is_alive() and not watch_result,'WATCHDOG_FIRED_OR_UNCERTAIN_NO_RELEASE')
                quiescent=job.terminate_and_wait(5);need(quiescent is True,'JOB_EMPTY_UNPROVEN')
                return dict(mode=mode,requested_bytes=CASES[mode],host_before=host_before,host_pre_resume=host_pre_resume,
                            limit_readback=limits,child_before=before,parent_before=actual_before,job_before=inventory,
                            child_during=during,parent_during=during_process,job_during=during_job,
                            child_after=after,parent_after=after_process,job_after=after_job,ipc_bytes=received,
                            primary_exit_code=parent_exit.value,reporting_child_exit_code=child_exit.value,
                            job_empty_proved=True,admission=False,qualification='UNQUALIFIED_RAW_DIAGNOSTIC')
            except BaseException as error:
                # Capture the body cause BEFORE retirement/tempdir/handle cleanup.
                origin_record(state,error,'case_body');raise
            finally:
                stop.set();watch_uncertain=False
                try:
                    if watch:
                        watch.join(1);watch_uncertain=watch.is_alive()
                except BaseException as error:
                    watch_uncertain=True;state['cleanup'].append(error_record(error,'watchdog_join'))
                state['partial']['watchdog_calls']=list(watch_result)
                try:
                    # A live watchdog must never see a recycled Job HANDLE.
                    worker._retire_owned(None if watch_uncertain else job,
                                         process_handle=proc.process,thread_handle=proc.thread,
                                         kernel=k,created=created,quiescent=quiescent)
                except BaseException as error:
                    state['cleanup'].append(error_record(error,'owned_retirement'))
                if watch_uncertain:
                    state['cleanup'].append(error_record(Refused('WATCHDOG_OWNERSHIP_UNCERTAIN_NO_RELEASE'),'watchdog'))
    except BaseException as error:
        origin_record(state,error,'setup_or_tempdir_cleanup');raise
    finally:
        if attributes is not None:
            try:k.DeleteProcThreadAttributeList(attributes)
            except BaseException as error:state['cleanup'].append(error_record(error,'attribute_cleanup'))
        for handle in reversed(extra_handles):
            try:close(handle)
            except BaseException as error:state['cleanup'].append(error_record(error,'extra_handle_close'))


def one_case(mode,grid,worker):
    state=dict(mode=mode,origin=None,cleanup=[],partial={})
    try:
        observation=_one_case(mode,grid,worker,state)
    except BaseException as error:
        origin_record(state,error,'prerequisite_or_propagated_cleanup')
        raise DiagnosticFailure(public_diagnostics(state)) from state.get('_origin_exception',error)
    if state['cleanup']:
        # Successful body is NOT successful diagnosis when retirement is unknown.
        raise DiagnosticFailure(public_diagnostics(state))
    observation['diagnostics']=public_diagnostics(state)
    return observation

def parent(grid_repository,expected_script_sha256):
    need(hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==expected_script_sha256,'DIAGNOSTIC_SOURCE_MISMATCH')
    grid,worker=load_owners(grid_repository)
    # EXACT2 sequential cases. No retry loop, callback or caller request size.
    control=one_case('control',grid,worker)
    if control['child_during']['native_success'] is not True or control['child_after']['free_result'] is not True:
        return dict(classification='CONTROL_REFUSED_OVERLIMIT_NOT_RUN',
                    source_sha256=expected_script_sha256,cases=[control])
    try:overlimit=one_case('overlimit',grid,worker)
    except DiagnosticFailure as error:
        error.completed_cases=[control];raise
    return dict(classification='OWNED_VIRTUALALLOC_DIAGNOSIS_NOT_ADMISSION',
                source_sha256=expected_script_sha256,cases=[control,overlimit])

if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--internal-child':
        raise SystemExit(child(sys.argv[2]))
    if len(sys.argv)==4 and sys.argv[1]=='--root-reviewed-parent':
        try:observation=parent(Path(sys.argv[2]),sys.argv[3])
        except DiagnosticFailure as error:
            observation=dict(classification='DIAGNOSTIC_FAILED_NO_QUALIFICATION',
                             diagnostics=error.diagnostics,completed_cases=error.completed_cases)
        except BaseException as error:
            observation=dict(classification='DIAGNOSTIC_PREREQUISITE_FAILED_NO_QUALIFICATION',
                             origin=error_record(error,'parent_prerequisite'),cleanup=[])
        result=json.dumps(observation,sort_keys=True)
        need(len(result.encode('ascii'))<=131072,'PARENT_REPORT_CAP')
        print(result)
        raise SystemExit(0 if observation['classification']=='OWNED_VIRTUALALLOC_DIAGNOSIS_NOT_ADMISSION' else 2)
    raise SystemExit('SOURCE_ONLY: explicit ROOT bounded source review/execution ACK required')
