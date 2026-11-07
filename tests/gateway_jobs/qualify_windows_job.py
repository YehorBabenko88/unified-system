"""Explicit owned disposable Windows Job probe; never native job admission.
Run directly only. No services, network, database, real job, policy or host changes.
"""
import ctypes
from ctypes import wintypes as w
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from unified_system.gateway_worker import _configure_retained_job, _Extended, WorkerUnavailable, _retire_owned


def qualify(grid_repository,mode="tree"):
    if mode not in ("tree","memory","bad_profile"):raise ValueError("UNKNOWN_QUALIFICATION_MODE")
    if os.name != 'nt':
        raise RuntimeError('WINDOWS_REQUIRED_NOT_QUALIFIED')
    raw = subprocess.check_output(['git','--no-replace-objects','-C',str(grid_repository),
        'show','40e9c8dc274a2746018bc1aa08d103cd0187cecc:grid/ml_windows_job.py'])
    # Exact source pinned by primary Git object, no working file/cache import.
    source_oid = hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    if source_oid != 'f30a09a3af647518d69f7787879defc4d5fa8ab5':
        raise RuntimeError('SOURCE_PIN_MISMATCH')
    module=types.ModuleType('a5_primary_grid_job');exec(compile(raw,'primary-grid-job','exec'),module.__dict__)
    class Startup(ctypes.Structure):
        _fields_=[('cb',w.DWORD),('reserved',w.LPWSTR),('desktop',w.LPWSTR),('title',w.LPWSTR),
            ('x',w.DWORD),('y',w.DWORD),('xs',w.DWORD),('ys',w.DWORD),('xc',w.DWORD),('yc',w.DWORD),
            ('fill',w.DWORD),('flags',w.DWORD),('show',w.WORD),('reserved_size',w.WORD),
            ('reserved_bytes',ctypes.c_void_p),('stdin',w.HANDLE),('stdout',w.HANDLE),('stderr',w.HANDLE)]
    class Process(ctypes.Structure):
        _fields_=[('process',w.HANDLE),('thread',w.HANDLE),('pid',w.DWORD),('tid',w.DWORD)]
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.CreateProcessW.argtypes=[w.LPCWSTR,w.LPWSTR,ctypes.c_void_p,ctypes.c_void_p,w.BOOL,w.DWORD,ctypes.c_void_p,w.LPCWSTR,ctypes.POINTER(Startup),ctypes.POINTER(Process)]
    k.CreateProcessW.restype=w.BOOL;k.ResumeThread.argtypes=[w.HANDLE];k.ResumeThread.restype=w.DWORD
    k.TerminateProcess.argtypes=[w.HANDLE,w.UINT];k.TerminateProcess.restype=w.BOOL
    k.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD];k.WaitForSingleObject.restype=w.DWORD
    k.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];k.GetExitCodeProcess.restype=w.BOOL
    k.CloseHandle.argtypes=[w.HANDLE];k.CloseHandle.restype=w.BOOL
    child="import os,subprocess,sys,time; memory=bytearray(4*1024*1024); subprocess.Popen([sys.executable,'-I','-B','-c','import time; time.sleep(30)'],env=dict(os.environ),creationflags=0x08000000); time.sleep(30)"
    if mode=='memory':
        child="import os\ntry:\n x=bytearray(512*1024*1024)\nexcept MemoryError:\n os._exit(42)\nos._exit(99)"
    proc=Process();startup=Startup();startup.cb=ctypes.sizeof(startup);job=None;created=False;quiescent=False
    environment={name:os.environ[name] for name in ('SYSTEMROOT','WINDIR','TEMP','TMP') if name in os.environ}
    block=ctypes.create_unicode_buffer('\0'.join(key+'='+value for key,value in sorted(environment.items()))+'\0\0')
    with tempfile.TemporaryDirectory(prefix='a5-job-qualification-') as directory:
        try:
            command=ctypes.create_unicode_buffer(subprocess.list2cmdline([sys.executable,'-I','-B','-c',child]))
            if not k.CreateProcessW(sys.executable,command,None,None,False,0x4|0x400|0x08000000,block,directory,ctypes.byref(startup),ctypes.byref(proc)):
                raise ctypes.WinError(ctypes.get_last_error())
            created=True
            job=module.WindowsJob(proc.pid,resume_primary_thread=False)
            if mode=='bad_profile':
                try:_configure_retained_job(job,expected_job_type=module.WindowsJob,owned_process_handle=proc.process,cpu_rate=999)
                except WorkerUnavailable as error:
                    if str(error)!='UNQUALIFIED_LIMIT_PROFILE':raise
                else:raise RuntimeError('INVALID_PROFILE_ACCEPTED')
                quiescent=job.terminate_and_wait(5)
                if quiescent is not True or k.WaitForSingleObject(proc.process,5000)!=0:raise RuntimeError('SETUP_FAILURE_NOT_QUIESCENT')
                return dict(classification='OWNED_SETUP_DENIAL_BEFORE_RESUME',mode=mode,resumed=False,
                            terminated_job_observed_empty=True,native_job_admission=False)
            limit_observation=_configure_retained_job(job,expected_job_type=module.WindowsJob,owned_process_handle=proc.process)
            if k.ResumeThread(proc.thread)==0xffffffff:raise ctypes.WinError(ctypes.get_last_error())
            if mode=='memory':
                if k.WaitForSingleObject(proc.process,5000)!=0:raise RuntimeError('MEMORY_PROBE_TIMEOUT')
                exit_code=w.DWORD()
                if not k.GetExitCodeProcess(proc.process,ctypes.byref(exit_code)) or exit_code.value!=42:raise RuntimeError('MEMORY_CAP_NOT_OBSERVED:'+str(exit_code.value))
                usage=_Extended()
                if not job._kernel.QueryInformationJobObject(job._job,9,ctypes.byref(usage),ctypes.sizeof(usage),None):raise RuntimeError('MEMORY_ACCOUNTING_UNAVAILABLE')
                quiescent=job.terminate_and_wait(5)
                if quiescent is not True:raise RuntimeError('MEMORY_PROBE_NOT_QUIESCENT')
                return dict(classification='OWNED_COMMITTED_MEMORY_LIMIT_PROBE_NOT_RSS',mode=mode,
                    rejected_allocation_bytes=512*1024*1024,exit_code=exit_code.value,
                    native_peak_job_committed_bytes=usage.peak_job_memory,
                    peak_exceeds_configured_limit=usage.peak_job_memory>268435456,
                    memory_limit_cause_and_peak_semantics_qualified=False,
                    limit_readback_before_resume=limit_observation,terminated_job_observed_empty=True,
                    rss_capacity_qualified=False,native_job_admission=False)
            info=module._BasicAccounting()
            # Bounded wait on owned process handle, not a PID or unowned worker.
            for _ in range(20):
                if k.WaitForSingleObject(proc.process,100)==0:raise RuntimeError('CHILD_EXITED_EARLY')
                if not job._kernel.QueryInformationJobObject(job._job,1,ctypes.byref(info),ctypes.sizeof(info),None):raise ctypes.WinError(ctypes.get_last_error())
                if info.ActiveProcesses>=2:break
            if info.ActiveProcesses<2:raise RuntimeError('DESCENDANT_NOT_OBSERVED:'+str((info.ActiveProcesses,info.TotalProcesses,info.TotalTerminatedProcesses)))
            before=int(info.ActiveProcesses);total=int(info.TotalProcesses)
            quiescent=job.terminate_and_wait(5)
            if quiescent is not True or k.WaitForSingleObject(proc.process,5000)!=0:raise RuntimeError('QUIESCENCE_NOT_PROVEN')
            return dict(classification='OWNED_DISPOSABLE_CONTAINMENT_PRIMITIVE_ONLY',
                grid_head='40e9c8dc274a2746018bc1aa08d103cd0187cecc',source_sha256=hashlib.sha256(raw).hexdigest(),
                assigned_before_resume=True,limit_readback_before_resume=limit_observation,active_processes_before_cancel=before,total_processes=total,
                terminated_job_observed_empty=True,primary_handle_signaled=True,
                cpu_memory_output_limits_qualified=False,capacity_qualified=False,native_job_admission=False)
        finally:
            _retire_owned(job,process_handle=proc.process,thread_handle=proc.thread,
                          kernel=k,created=created,quiescent=quiescent)



if __name__=='__main__':
    if len(sys.argv) not in (2,3):raise SystemExit('explicit Grid repository path and optional mode required')
    print(json.dumps(qualify(Path(sys.argv[1]),sys.argv[2] if len(sys.argv)==3 else "tree"),sort_keys=True))
