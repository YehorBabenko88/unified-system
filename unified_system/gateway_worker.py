"""Owned Job limit/readback primitive; no worker admission or start authority.

Private helpers require an already-owned suspended process and exact pinned Grid
class. Caller handles/types are not native grants. GatewayWorker.start is closed.
"""
import ctypes
from ctypes import wintypes as w
import os
import time
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import types
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

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
    k=job._kernel;handle=job._job;calls=[]
    def observed(name,fn,*args):
        value=fn(*args)
        calls.append(dict(api=name,result=int(value),last_error=ctypes.get_last_error(),
                          monotonic_ns=str(time.monotonic_ns())))
        return value
    k.IsProcessInJob.argtypes=[w.HANDLE,w.HANDLE,ctypes.POINTER(w.BOOL)];k.IsProcessInJob.restype=w.BOOL
    k.GetProcessAffinityMask.argtypes=[w.HANDLE,ctypes.POINTER(ctypes.c_size_t),ctypes.POINTER(ctypes.c_size_t)];k.GetProcessAffinityMask.restype=w.BOOL
    k.GetActiveProcessorGroupCount.argtypes=[];k.GetActiveProcessorGroupCount.restype=w.WORD
    member=w.BOOL();process_mask=ctypes.c_size_t();system_mask=ctypes.c_size_t()
    if not observed("IsProcessInJob",k.IsProcessInJob,owned_process_handle,handle,ctypes.byref(member)) or not member.value:
        raise WorkerUnavailable('OWNED_JOB_MEMBERSHIP_UNVERIFIED')
    if (observed("GetActiveProcessorGroupCount",k.GetActiveProcessorGroupCount)!=1 or
            not observed("GetProcessAffinityMask",k.GetProcessAffinityMask,owned_process_handle,ctypes.byref(process_mask),ctypes.byref(system_mask))
            or not process_mask.value or process_mask.value & ~system_mask.value):
        raise WorkerUnavailable('PROCESSOR_TOPOLOGY_UNQUALIFIED')
    limits=_Extended();limits.basic.flags=0x2000|0x200|0x8
    limits.basic.active_limit=active_processes;limits.job_memory=committed_bytes
    if not observed("SetInformationJobObject:Extended9",k.SetInformationJobObject,handle,9,ctypes.byref(limits),ctypes.sizeof(limits)):
        raise WorkerUnavailable('JOB_MEMORY_PROCESS_LIMIT_FAILED')
    cpu=_CPU(5,cpu_rate)  # ENABLE|HARD_CAP, explicitly bounded native rate units.
    if not observed("SetInformationJobObject:CPU15",k.SetInformationJobObject,handle,15,ctypes.byref(cpu),ctypes.sizeof(cpu)):
        raise WorkerUnavailable('JOB_CPU_LIMIT_FAILED')
    actual=_Extended();actual_cpu=_CPU()
    if (not observed("QueryInformationJobObject:Extended9",k.QueryInformationJobObject,handle,9,ctypes.byref(actual),ctypes.sizeof(actual),None)
            or not observed("QueryInformationJobObject:CPU15",k.QueryInformationJobObject,handle,15,ctypes.byref(actual_cpu),ctypes.sizeof(actual_cpu),None)):
        raise WorkerUnavailable('JOB_LIMIT_READBACK_FAILED')
    if (actual.basic.flags & limits.basic.flags != limits.basic.flags or actual.job_memory!=committed_bytes
            or actual.basic.active_limit!=active_processes or actual_cpu.flags!=5 or actual_cpu.rate!=cpu_rate):
        raise WorkerUnavailable('JOB_LIMIT_READBACK_MISMATCH')
    return dict(native_calls=calls,job_membership_verified=bool(member.value),
                requested_limit_flags=limits.basic.flags,readback_limit_flags=actual.basic.flags,
                requested_job_memory_bytes=limits.job_memory,
                requested_cpu_flags=cpu.flags,readback_cpu_flags=actual_cpu.flags,
                extended_requested_hex=bytes(limits).hex(),extended_readback_hex=bytes(actual).hex(),
                cpu_requested_hex=bytes(cpu).hex(),cpu_readback_hex=bytes(actual_cpu).hex(),
                layouts={name:dict(size=ctypes.sizeof(cls),offsets={field:getattr(cls,field).offset for field,*_ in cls._fields_})
                         for name,cls in [('basic',_Basic),('io',_IO),('extended',_Extended),('cpu',_CPU)]},
                committed_memory_limit_bytes=actual.job_memory,active_process_limit=actual.basic.active_limit,
                cpu_hard_rate_units=actual_cpu.rate,affinity_processor_count=process_mask.value.bit_count(),
                system_affinity_processor_count=system_mask.value.bit_count(),processor_groups=1,
                inherited_job_capacity_qualified=False,cpu_millicore_mapping_qualified=False,
                resident_memory_mapping_qualified=False)

_PROCESS_INCARNATION=str(uuid.uuid4())
_DIRECT_INTERPRETER=Path(r'C:\Users\LS-5\AppData\Local\Python\pythoncore-3.12-64\python.exe')
_DIRECT_INTERPRETER_SHA='4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a'
_GRID_JOB_SHA='7fd6223de3e28052b1254fa9e33e638132c6db89388bbb2d994b35970802a25c'

class OwnedWorkerAttempt:
    """Inventory-only local OS object, never an Assignment or dispatch permit."""
    __slots__=()
    def __new__(cls):raise TypeError('OWNED_ATTEMPT_INVENTORY_ONLY')
    def __copy__(self):raise TypeError('OWNED_ATTEMPT_NOT_COPYABLE')
    def __deepcopy__(self,memo):raise TypeError('OWNED_ATTEMPT_NOT_COPYABLE')
    def __reduce__(self):raise TypeError('OWNED_ATTEMPT_NOT_SERIALIZABLE')

@dataclass(frozen=True)
class OwnedAttemptObservation:
    state: str
    original_request_id: str
    original_request_sha256: str
    planned_job_id: str
    declared_node_id: str
    worker_incarnation_id: str
    attempt_id: str
    child_pid: int
    child_creation_filetime: str
    child_image: str
    source_sha256: str
    os_observation_json: bytes
    native_authority: str='NOT_GRANTED'

class _AttemptStartup(ctypes.Structure):
    _fields_=[('cb',w.DWORD),('reserved',w.LPWSTR),('desktop',w.LPWSTR),('title',w.LPWSTR),
        ('x',w.DWORD),('y',w.DWORD),('xs',w.DWORD),('ys',w.DWORD),('xc',w.DWORD),('yc',w.DWORD),
        ('fill',w.DWORD),('flags',w.DWORD),('show',w.WORD),('reserved_size',w.WORD),
        ('reserved_bytes',ctypes.c_void_p),('stdin',w.HANDLE),('stdout',w.HANDLE),('stderr',w.HANDLE)]
class _AttemptProcess(ctypes.Structure):
    _fields_=[('process',w.HANDLE),('thread',w.HANDLE),('pid',w.DWORD),('tid',w.DWORD)]
class _AttemptPerformance(ctypes.Structure):
    _fields_=[('cb',w.DWORD)]+[(n,ctypes.c_size_t) for n in ('commit_total','commit_limit','commit_peak',
        'physical_total','physical_available','cache','kernel_total','kernel_paged','kernel_nonpaged','page_size')]+[
        ('handles',w.DWORD),('processes',w.DWORD),('threads',w.DWORD)]
class _AttemptProcessMemory(ctypes.Structure):
    _fields_=[('cb',w.DWORD),('faults',w.DWORD)]+[(n,ctypes.c_size_t) for n in
        ('peak_working_set','working_set','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile','private_usage')]

def _worker_need(ok,code):
    if not ok:raise WorkerUnavailable(code)
def _worker_uuid(value):
    _worker_need(type(value) is str and re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}',value) is not None,'OWNED_REQUEST_UUID')
def _worker_canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
def _worker_original(raw):
    try:
        _worker_need(type(raw) is bytes and 0<len(raw)<=16384,'OWNED_ORIGINAL_BYTES')
        def pairs(items):
            result={}
            for key,value in items:
                _worker_need(key not in result,'OWNED_DUPLICATE_KEY');result[key]=value
            return result
        def number(_):raise WorkerUnavailable('OWNED_NATIVE_METADATA_NUMBER')
        value=json.loads(raw.decode('ascii'),object_pairs_hook=pairs,parse_int=number,parse_float=number,parse_constant=number)
        fields={'schema','operation','cluster_id','cluster_generation','request_id','job_id','original_actor_principal_id',
                'quota_owner_id','idempotency_key','commissioned_profile_sha256','input_request_sha256','producer_head','resources'}
        _worker_need(type(value) is dict and set(value)==fields and _worker_canonical(value)==raw,'OWNED_ORIGINAL_CANONICAL')
        _worker_need(value['schema']=='unified.gateway.lab-job-submit.v1-review1' and value['operation']=='SUBMIT_RESEARCH','OWNED_ORIGINAL_PROFILE')
        for key in ('cluster_id','cluster_generation','request_id','job_id','original_actor_principal_id'):_worker_uuid(value[key])
        for key in ('quota_owner_id','idempotency_key'):
            _worker_need(type(value[key]) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,128}',value[key]) is not None,'OWNED_ORIGINAL_KEY')
        _worker_need(type(value['commissioned_profile_sha256']) is str and re.fullmatch(r'[0-9a-f]{64}',value['commissioned_profile_sha256']) is not None,'OWNED_ORIGINAL_PROFILE_HASH')
        _worker_need(value['input_request_sha256']=='c548e2ffcd542d5d741682303694b3c6d06507740f158a6e30089b2d5355f648','OWNED_ORIGINAL_INPUT')
        _worker_need(value['producer_head']=='aed8a7c8a952f96803c207d5e90b133969a47f04','OWNED_ORIGINAL_PRODUCER')
        _worker_need(type(value['resources']) is dict and value['resources']=={
            'cpu_millicores':'1000','resident_memory_bytes':'268435456','max_artifact_bytes':'1048576'},'OWNED_ORIGINAL_RESOURCES')
        return value
    except WorkerUnavailable:raise
    except (ValueError,UnicodeError,TypeError,KeyError,RecursionError):
        raise WorkerUnavailable('OWNED_ORIGINAL_INVALID') from None

def _attempt_api():
    _worker_need(os.name=='nt' and ctypes.sizeof(ctypes.c_void_p)==8,'OWNED_WINDOWS_X64_REQUIRED')
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    signatures={
        'CreateProcessW':([w.LPCWSTR,w.LPWSTR,ctypes.c_void_p,ctypes.c_void_p,w.BOOL,w.DWORD,ctypes.c_void_p,w.LPCWSTR,ctypes.POINTER(_AttemptStartup),ctypes.POINTER(_AttemptProcess)],w.BOOL),
        'WaitForSingleObject':([w.HANDLE,w.DWORD],w.DWORD),'TerminateProcess':([w.HANDLE,w.UINT],w.BOOL),
        'CloseHandle':([w.HANDLE],w.BOOL),'GetCurrentProcess':([],w.HANDLE),
        'GetProcessTimes':([w.HANDLE,*([ctypes.POINTER(w.FILETIME)]*4)],w.BOOL),
        'QueryFullProcessImageNameW':([w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)],w.BOOL),
        'IsProcessInJob':([w.HANDLE,w.HANDLE,ctypes.POINTER(w.BOOL)],w.BOOL),
        'K32GetProcessMemoryInfo':([w.HANDLE,ctypes.POINTER(_AttemptProcessMemory),w.DWORD],w.BOOL),
        'K32GetPerformanceInfo':([ctypes.POINTER(_AttemptPerformance),w.DWORD],w.BOOL)}
    for name,(args,result) in signatures.items():
        fn=getattr(k,name);fn.argtypes=args;fn.restype=result
    return k

def _attempt_identity(k,handle):
    times=[w.FILETIME() for _ in range(4)];image=ctypes.create_unicode_buffer(32768);length=w.DWORD(len(image))
    _worker_need(k.GetProcessTimes(handle,*[ctypes.byref(v) for v in times]),'OWNED_CREATION_TIME_UNAVAILABLE')
    _worker_need(k.QueryFullProcessImageNameW(handle,0,image,ctypes.byref(length)),'OWNED_IMAGE_UNAVAILABLE')
    return str((times[0].dwHighDateTime<<32)|times[0].dwLowDateTime),str(Path(image.value).resolve())

def _attempt_host(k):
    info=_AttemptPerformance();info.cb=ctypes.sizeof(info)
    _worker_need(k.K32GetPerformanceInfo(ctypes.byref(info),ctypes.sizeof(info)),'OWNED_HOST_OBSERVATION_UNAVAILABLE')
    _worker_need(info.page_size>0 and info.commit_limit>=info.commit_total,'OWNED_HOST_OBSERVATION_INVALID')
    return dict(available_commit_bytes=str((info.commit_limit-info.commit_total)*info.page_size),
                available_physical_bytes=str(info.physical_available*info.page_size),
                observation_utc=datetime.now(timezone.utc).isoformat(),monotonic_ns=str(time.monotonic_ns()),
                qualified_for_native_admission=False)

class GatewayWorker:
    """Own process-local preparation inventory, NOT a scheduler or durable ledger.

    prepare_attempt creates only a suspended child. Source/OS observations do not
    qualify node identity, resource policy, native enrollment/session or a grant.
    """
    _owners={}
    _owners_lock=threading.RLock()
    _preparation_owner=None
    def __init__(self,*,node_id=None):
        if node_id is not None:_worker_uuid(node_id)
        self._node=node_id;self._lock=threading.RLock();self._attempts={};self._by_original={};self._keys={};self._originals={};self._active=None;self._poisoned=False
    def start(self,*args,**kwargs):
        raise WorkerUnavailable('ACTUAL_DISPATCH_PERMIT_AND_WORKER_PROFILE_UNAVAILABLE')
    def _record(self,attempt):
        _worker_need(type(self) is GatewayWorker and type(attempt) is OwnedWorkerAttempt and attempt in self._attempts,'FOREIGN_OWNED_ATTEMPT')
        return self._attempts[attempt]
    def prepare_attempt(self,original_lab13_bytes,*,grid_source_root):
        _worker_need(type(self) is GatewayWorker,'EXPECTED_WORKER_INVENTORY_REQUIRED')
        _worker_need(self._node is not None,'WORKER_NODE_LABEL_REQUIRED')
        value=_worker_original(original_lab13_bytes);rid=value['request_id'];digest=hashlib.sha256(original_lab13_bytes).hexdigest()
        key=tuple(value[n] for n in ('cluster_id','quota_owner_id','original_actor_principal_id','idempotency_key'))
        with self._lock:
            _worker_need(not self._poisoned,'OWNED_INVENTORY_POISONED_NO_RELEASE')
            if rid in self._originals:
                _worker_need(self._originals[rid]==original_lab13_bytes,'OWNED_ORIGINAL_CONFLICT')
                prior=self._by_original.get(rid)
                _worker_need(prior is not None and self._record(prior)['phase']=='PREPARED','OWNED_ORIGINAL_RETIRED_OR_FAILED_NO_AUTORETRY')
                return prior
            _worker_need(key not in self._keys,'OWNED_IDEMPOTENCY_CONFLICT')
            _worker_need(self._active is None and len(self._originals)<32,'OWNED_PREPARATION_CAPACITY')
            with self._owners_lock:
                _worker_need(GatewayWorker._preparation_owner is None,'OWNED_PROCESS_PREPARATION_CAPACITY')
                owner=self._owners.get(self._node)
                _worker_need(owner is None or owner is self,'FOREIGN_NODE_PREPARATION_INVENTORY')
                self._owners[self._node]=self
                GatewayWorker._preparation_owner=self
            self._originals[rid]=original_lab13_bytes;self._keys[key]=rid;self._by_original[rid]=None
            k=None;job=None;created=False;proc=_AttemptProcess();directory=None;attempt=None
            try:
                k=_attempt_api();host=_attempt_host(k)
                # Conservative local-preparation refusal margin, NOT admission.
                _worker_need(int(host['available_commit_bytes'])>=2952790016 and int(host['available_physical_bytes'])>=1073741824,'OWNED_PREPARATION_HEADROOM_REFUSED')
                for ancestor in reversed((_DIRECT_INTERPRETER,*_DIRECT_INTERPRETER.parents)):
                    st=ancestor.lstat();_worker_need(not ancestor.is_symlink() and not getattr(st,'st_file_attributes',0)&1024,'OWNED_INTERPRETER_LINK_REFUSED')
                _worker_need(hashlib.sha256(_DIRECT_INTERPRETER.read_bytes()).hexdigest()==_DIRECT_INTERPRETER_SHA,'OWNED_INTERPRETER_PIN_MISMATCH')
                source=subprocess.check_output(['git','--no-replace-objects','-C',str(grid_source_root),'cat-file','blob',
                    '40e9c8dc274a2746018bc1aa08d103cd0187cecc:grid/ml_windows_job.py'],timeout=10)
                _worker_need(hashlib.sha256(source).hexdigest()==_GRID_JOB_SHA,'OWNED_GRID_SOURCE_MISMATCH')
                module=types.ModuleType('owned_attempt_pinned_grid');exec(compile(source,'primary-owned-grid-job','exec'),module.__dict__)
                entry=Path(__file__).resolve();entry_sha=hashlib.sha256(entry.read_bytes()).hexdigest()
                directory=Path(tempfile.mkdtemp(prefix='a5-owned-suspended-'));ds=directory.stat();directory_identity=(ds.st_dev,ds.st_ino)
                startup=_AttemptStartup();startup.cb=ctypes.sizeof(startup)
                argv=[str(_DIRECT_INTERPRETER),'-I','-B',str(entry),'--owned-research-child-not-admitted']
                command=ctypes.create_unicode_buffer(subprocess.list2cmdline(argv))
                environment={key:os.environ[key] for key in ('SYSTEMROOT','WINDIR','TEMP','TMP') if key in os.environ}
                block=ctypes.create_unicode_buffer('\0'.join(key+'='+v for key,v in sorted(environment.items()))+'\0\0')
                _worker_need(k.CreateProcessW(str(_DIRECT_INTERPRETER),command,None,None,False,0x4|0x400|0x08000000,
                    block,str(directory),ctypes.byref(startup),ctypes.byref(proc)),'OWNED_SUSPENDED_CREATE_FAILED')
                created=True;identity=_attempt_identity(k,proc.process)
                _worker_need(Path(identity[1])==_DIRECT_INTERPRETER.resolve(),'OWNED_ACTUAL_IMAGE_MISMATCH')
                job=module.WindowsJob(proc.pid,resume_primary_thread=False)
                limits=_configure_retained_job(job,expected_job_type=module.WindowsJob,owned_process_handle=proc.process)
                _worker_need(k.WaitForSingleObject(proc.process,0)==258,'OWNED_PREPARED_CHILD_NOT_LIVE')
                attempt=object.__new__(OwnedWorkerAttempt)
                state=dict(phase='PREPARED',raw=original_lab13_bytes,rid=rid,digest=digest,job_label=value['job_id'],
                    attempt_id=str(uuid.uuid4()),kernel=k,proc=proc,job=job,identity=identity,limits=limits,
                    entry_sha=entry_sha,directory=directory,directory_identity=directory_identity,snapshot=None)
                self._attempts[attempt]=state;self._by_original[rid]=attempt;self._active=attempt
                self._inspect(state)
                return attempt
            except BaseException as origin:
                failures=[]
                if attempt is not None:
                    self._attempts[attempt]['phase']='POISONED'
                try:
                    if k is not None:_retire_owned(job,process_handle=proc.process,thread_handle=proc.thread,kernel=k,created=created,quiescent=False)
                except BaseException as error:failures.append(('owned_retirement',error))
                try:
                    if directory is not None:
                        st=directory.stat()
                        _worker_need((st.st_dev,st.st_ino)==directory_identity and not getattr(st,'st_file_attributes',0)&1024,'OWNED_DIRECTORY_IDENTITY_CHANGED')
                        directory.rmdir()
                except BaseException as error:failures.append(('directory_cleanup',error))
                if failures or attempt is not None:self._poisoned=True
                if not self._poisoned:
                    with self._owners_lock:GatewayWorker._preparation_owner=None
                error=WorkerUnavailable('OWNED_PREPARATION_FAILED_NO_AUTORETRY')
                error.origin_diagnostic=(type(origin).__name__,str(origin))
                error.cleanup_diagnostics=tuple((stage,type(e).__name__,str(e)) for stage,e in failures)
                raise error from origin
    def _inspect(self,state):
        if state['phase']=='QUIESCENT':return state['snapshot']
        _worker_need(state['phase']=='PREPARED','OWNED_ATTEMPT_NOT_PREPARED')
        k=state['kernel'];proc=state['proc'];member=w.BOOL()
        _worker_need(_attempt_identity(k,proc.process)==state['identity'],'OWNED_PROCESS_IDENTITY_CHANGED')
        _worker_need(k.WaitForSingleObject(proc.process,0)==258,'OWNED_PROCESS_NOT_LIVE')
        _worker_need(k.IsProcessInJob(proc.process,state['job']._job,ctypes.byref(member)) and member.value,'OWNED_JOB_MEMBERSHIP_LOST')
        memory=_AttemptProcessMemory();memory.cb=ctypes.sizeof(memory)
        _worker_need(k.K32GetProcessMemoryInfo(proc.process,ctypes.byref(memory),ctypes.sizeof(memory)),'OWNED_MEMORY_OBSERVATION_UNAVAILABLE')
        details=dict(job_membership=True,resume_calls=0,resource_profile_qualified=False,native_worker_enrollment='NOT_QUALIFIED',
                     native_lease_quota_utc='NOT_GRANTED',private_commit_bytes=str(memory.private_usage),working_set_bytes=str(memory.working_set),
                     limit_readback=state['limits'],host_observation=_attempt_host(k),grid_source_sha256=_GRID_JOB_SHA,
                     interpreter_sha256=_DIRECT_INTERPRETER_SHA,source_custody='NOT_QUALIFIED_FOR_RESUME')
        snapshot=OwnedAttemptObservation('PREPARED_SUSPENDED_LOCAL_ONLY',state['rid'],state['digest'],state['job_label'],self._node,
            _PROCESS_INCARNATION,state['attempt_id'],int(proc.pid),*state['identity'],state['entry_sha'],_worker_canonical(details))
        state['snapshot']=snapshot;return snapshot
    def inspect_attempt(self,attempt):
        with self._lock:return self._inspect(self._record(attempt))
    @staticmethod
    def require_owned_attempt(expected_worker,attempt,*,original_lab13_bytes):
        _worker_need(type(expected_worker) is GatewayWorker,'EXPECTED_WORKER_INVENTORY_REQUIRED')
        with expected_worker._lock:
            state=expected_worker._record(attempt)
            _worker_need(type(original_lab13_bytes) is bytes and state['raw']==original_lab13_bytes,'OWNED_ORIGINAL_CONFLICT')
            _worker_need(state['phase']=='PREPARED','OWNED_ATTEMPT_NOT_PREPARED')
            return expected_worker._inspect(state)
    def abort_attempt(self,attempt):
        with self._lock:
            state=self._record(attempt)
            if state['phase']=='QUIESCENT':return state['snapshot']
            _worker_need(state['phase']=='PREPARED','OWNED_ATTEMPT_POISONED_NO_RELEASE')
            state['phase']='ABORTING'
            try:
                _retire_owned(state['job'],process_handle=state['proc'].process,thread_handle=state['proc'].thread,
                              kernel=state['kernel'],created=True,quiescent=False)
                directory=state['directory'];st=directory.stat()
                _worker_need((st.st_dev,st.st_ino)==state['directory_identity'] and not getattr(st,'st_file_attributes',0)&1024,'OWNED_DIRECTORY_IDENTITY_CHANGED')
                directory.rmdir()
                previous=state['snapshot'];details=json.loads(previous.os_observation_json)
                details.update(job_empty_observed=True,retained_primary_exit_observed=True,observed_utc=datetime.now(timezone.utc).isoformat(),native_hold_release='NOT_AUTHORIZED')
                state['snapshot']=OwnedAttemptObservation('OWNED_QUIESCENCE_CONFIRMED',previous.original_request_id,previous.original_request_sha256,
                    previous.planned_job_id,previous.declared_node_id,previous.worker_incarnation_id,previous.attempt_id,previous.child_pid,
                    previous.child_creation_filetime,previous.child_image,previous.source_sha256,_worker_canonical(details))
                state['phase']='QUIESCENT';self._active=None
                with self._owners_lock:GatewayWorker._preparation_owner=None
                return state['snapshot']
            except BaseException:
                state['phase']='POISONED';self._poisoned=True;raise


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
