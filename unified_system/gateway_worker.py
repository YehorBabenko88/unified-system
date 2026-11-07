"""Owned Job limit/readback primitive; no worker admission or start authority.

Private helpers require an already-owned suspended process and exact pinned Grid
class. Caller handles/types are not native grants. GatewayWorker.start is closed.
"""
import ctypes
from ctypes import wintypes as w
import os

class WorkerUnavailable(RuntimeError):
    pass

class _Basic(ctypes.Structure):
    _fields_=[('process_time',ctypes.c_int64),('job_time',ctypes.c_int64),('flags',w.DWORD),
        ('min_working_set',ctypes.c_size_t),('max_working_set',ctypes.c_size_t),
        ('active_limit',w.DWORD),('affinity',ctypes.c_size_t),('priority',w.DWORD),('scheduling',w.DWORD)]
class _IO(ctypes.Structure):
    _fields_=[(x,ctypes.c_uint64) for x in ('reads','writes','others','read_bytes','write_bytes','other_bytes')]
class _Extended(ctypes.Structure):
    _fields_=[('basic',_Basic),('io',_IO),('process_memory',ctypes.c_size_t),
        ('job_memory',ctypes.c_size_t),('peak_process_memory',ctypes.c_size_t),('peak_job_memory',ctypes.c_size_t)]
class _CPU(ctypes.Structure):
    _fields_=[('flags',w.DWORD),('rate',w.DWORD)]

def _configure_retained_job(job,*,expected_job_type,owned_process_handle=None,
                            committed_bytes=268435456,active_processes=8,cpu_rate=1000):
    """Native setting/readback only. Does NOT map CPU share or committed bytes to RSS.

    expected_job_type is internal exact source-qualified Grid class identity;
    this helper is not a public arbitrary handle or authority-provider endpoint.
    CPU rate1000 is ten percent native Job CPU rate, NOT one logical CPU.
    """
    if (os.name!='nt' or expected_job_type is None or type(job) is not expected_job_type
            or not owned_process_handle or not getattr(job,'_job',None)):
        raise WorkerUnavailable('OWNED_JOB_REQUIRED')
    if (type(committed_bytes) is not int or committed_bytes!=268435456
            or type(active_processes) is not int or active_processes!=8
            or type(cpu_rate) is not int or cpu_rate!=1000):
        raise WorkerUnavailable('UNQUALIFIED_LIMIT_PROFILE')
    k=job._kernel;handle=job._job
    k.IsProcessInJob.argtypes=[w.HANDLE,w.HANDLE,ctypes.POINTER(w.BOOL)];k.IsProcessInJob.restype=w.BOOL
    k.GetProcessAffinityMask.argtypes=[w.HANDLE,ctypes.POINTER(ctypes.c_size_t),ctypes.POINTER(ctypes.c_size_t)];k.GetProcessAffinityMask.restype=w.BOOL
    k.GetActiveProcessorGroupCount.argtypes=[];k.GetActiveProcessorGroupCount.restype=w.WORD
    member=w.BOOL();process_mask=ctypes.c_size_t();system_mask=ctypes.c_size_t()
    if not k.IsProcessInJob(owned_process_handle,handle,ctypes.byref(member)) or not member.value:
        raise WorkerUnavailable('OWNED_JOB_MEMBERSHIP_UNVERIFIED')
    if (k.GetActiveProcessorGroupCount()!=1 or
            not k.GetProcessAffinityMask(owned_process_handle,ctypes.byref(process_mask),ctypes.byref(system_mask))
            or not process_mask.value or process_mask.value & ~system_mask.value):
        raise WorkerUnavailable('PROCESSOR_TOPOLOGY_UNQUALIFIED')
    limits=_Extended();limits.basic.flags=0x2000|0x200|0x8
    limits.basic.active_limit=active_processes;limits.job_memory=committed_bytes
    if not k.SetInformationJobObject(handle,9,ctypes.byref(limits),ctypes.sizeof(limits)):
        raise WorkerUnavailable('JOB_MEMORY_PROCESS_LIMIT_FAILED')
    cpu=_CPU(5,cpu_rate)  # ENABLE|HARD_CAP, explicitly bounded native rate units.
    if not k.SetInformationJobObject(handle,15,ctypes.byref(cpu),ctypes.sizeof(cpu)):
        raise WorkerUnavailable('JOB_CPU_LIMIT_FAILED')
    actual=_Extended();actual_cpu=_CPU()
    if (not k.QueryInformationJobObject(handle,9,ctypes.byref(actual),ctypes.sizeof(actual),None)
            or not k.QueryInformationJobObject(handle,15,ctypes.byref(actual_cpu),ctypes.sizeof(actual_cpu),None)):
        raise WorkerUnavailable('JOB_LIMIT_READBACK_FAILED')
    if (actual.basic.flags & limits.basic.flags != limits.basic.flags or actual.job_memory!=committed_bytes
            or actual.basic.active_limit!=active_processes or actual_cpu.flags!=5 or actual_cpu.rate!=cpu_rate):
        raise WorkerUnavailable('JOB_LIMIT_READBACK_MISMATCH')
    return dict(committed_memory_limit_bytes=actual.job_memory,active_process_limit=actual.basic.active_limit,
                cpu_hard_rate_units=actual_cpu.rate,affinity_processor_count=process_mask.value.bit_count(),
                system_affinity_processor_count=system_mask.value.bit_count(),processor_groups=1,
                inherited_job_capacity_qualified=False,cpu_millicore_mapping_qualified=False,
                resident_memory_mapping_qualified=False)

class GatewayWorker:
    def start(self,*args,**kwargs):
        raise WorkerUnavailable('ACTUAL_DISPATCH_PERMIT_AND_WORKER_PROFILE_UNAVAILABLE')


def _retire_owned(job,*,process_handle,thread_handle,kernel,created,quiescent):
    """Best-effort own-handle cleanup; NEVER converts unknown exit to success."""
    failure=None
    try:
        if job is not None and not quiescent:
            try:
                if job.terminate_and_wait(5) is not True:
                    raise WorkerUnavailable('OWNED_JOB_EMPTY_UNPROVEN')
            except BaseException as error:
                failure=error
            finally:
                try:job.close()
                except BaseException as error:
                    if failure is None:failure=error
            if created and kernel.WaitForSingleObject(process_handle,5000)!=0:
                failure=failure or WorkerUnavailable('OWNED_PROCESS_EXIT_UNPROVEN')
        elif created and job is None:
            if not kernel.TerminateProcess(process_handle,1):
                failure=WorkerUnavailable('OWNED_SUSPENDED_TERMINATE_FAILED')
            if kernel.WaitForSingleObject(process_handle,5000)!=0:
                failure=failure or WorkerUnavailable('OWNED_SUSPENDED_EXIT_UNPROVEN')
    except BaseException as error:
        failure=failure or error
    finally:
        for handle in (thread_handle,process_handle):
            if handle:
                try:
                    if not kernel.CloseHandle(handle):
                        failure=failure or WorkerUnavailable('OWNED_HANDLE_CLOSE_FAILED')
                except BaseException as error:
                    failure=failure or error
    if failure is not None:
        raise WorkerUnavailable('OWNED_CLEANUP_UNPROVEN_NO_RELEASE') from failure
