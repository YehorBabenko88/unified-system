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
