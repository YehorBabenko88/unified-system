"""Validation tests only; actual Windows qualifier is explicit and separate."""
import unittest
from unified_system.gateway_worker import WorkerUnavailable, _configure_retained_job, GatewayWorker, _retire_owned
class WorkerLimits(unittest.TestCase):
    def test_foreign_handle_rejected_before_native_access(self):
        with self.assertRaises(WorkerUnavailable):
            _configure_retained_job(object(),expected_job_type=None)
    def test_no_native_grant_no_dispatch(self):
        with self.assertRaises(WorkerUnavailable):GatewayWorker().start()

    def test_cleanup_error_still_closes_both_retained_handles(self):
        # Fault-injection assertion only: not native handles or qualification.
        closed=[]
        class Job:
            def terminate_and_wait(self,timeout):raise TimeoutError('unproven')
            def close(self):pass
        class Kernel:
            def WaitForSingleObject(self,handle,timeout):return 0
            def CloseHandle(self,handle):closed.append(handle);return True
        with self.assertRaises(WorkerUnavailable):
            _retire_owned(Job(),process_handle=10,thread_handle=20,kernel=Kernel(),created=True,quiescent=False)
        self.assertEqual(closed,[20,10])

    def test_failed_suspended_termination_not_reported_as_exit(self):
        closed=[]
        class Kernel:
            def TerminateProcess(self,handle,code):return False
            def WaitForSingleObject(self,handle,timeout):return 258
            def CloseHandle(self,handle):closed.append(handle);return True
        with self.assertRaises(WorkerUnavailable):
            _retire_owned(None,process_handle=10,thread_handle=20,kernel=Kernel(),created=True,quiescent=False)
        self.assertEqual(closed,[20,10])

    def test_native_setup_and_readback_fault_assertions(self):
        # Inert API fault injection ONLY, not native limit or worker evidence.
        import os
        if os.name!='nt':
            with self.assertRaises(WorkerUnavailable):_configure_retained_job(object(),expected_job_type=None)
            return
        class Call:
            def __init__(self,fn):self.fn=fn
            def __call__(self,*args):return self.fn(*args)
        for fault,code in [('set_memory','JOB_MEMORY_PROCESS_LIMIT_FAILED'),
                           ('set_cpu','JOB_CPU_LIMIT_FAILED'),
                           ('query','JOB_LIMIT_READBACK_FAILED'),
                           ('mismatch','JOB_LIMIT_READBACK_MISMATCH')]:
            class Kernel:
                pass
            kernel=Kernel()
            def member(process,job,out):out._obj.value=True;return True
            def affinity(process,a,b):a._obj.value=b._obj.value=0xffff;return True
            kernel.IsProcessInJob=Call(member);kernel.GetProcessAffinityMask=Call(affinity)
            kernel.GetActiveProcessorGroupCount=Call(lambda:1)
            kernel.SetInformationJobObject=Call(lambda handle,kind,out,size:not ((fault=='set_memory' and kind==9) or (fault=='set_cpu' and kind==15)))
            kernel.QueryInformationJobObject=Call(lambda *args:fault!='query')
            class Job:pass
            job=Job();job._kernel=kernel;job._job=123
            with self.subTest(fault=fault),self.assertRaisesRegex(WorkerUnavailable,code):
                _configure_retained_job(job,expected_job_type=Job,owned_process_handle=456)
