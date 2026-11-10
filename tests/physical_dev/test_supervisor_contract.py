"""Pure ABI, framing and safety contracts; never start a child or touch a Job."""
import ctypes,json,unittest,tempfile
from pathlib import Path

class SupervisorContractTests(unittest.TestCase):
    def test_failed_owned_job_close_preserves_handle_for_diagnosis(self):
        from tools.physical_dev.supervisor import WindowsSmokeJob,SmokeBlocked
        from unittest.mock import Mock
        job=object.__new__(WindowsSmokeJob);job.api=Mock();job.handle=123;job.closed=False
        job.api.check.side_effect=SmokeBlocked('OWN_JOB_CLOSE')
        with self.assertRaises(SmokeBlocked):job.close()
        self.assertEqual(job.handle,123);self.assertFalse(job.closed)
        job.api.check.side_effect=None;job.close()
        self.assertIsNone(job.handle);self.assertTrue(job.closed)

    def test_external_target_watchdog_terminates_only_owned_job_on_expiry(self):
        from tools.physical_dev.supervisor import OwnWatchdog
        from unittest.mock import Mock,patch
        job=Mock();watch=OwnWatchdog(job,100)
        with patch.object(watch.stop,'wait',return_value=False) as wait,patch('time.perf_counter_ns',return_value=100):watch._run()
        wait.assert_called_once_with(20.0);job.terminate_own.assert_called_once_with()
        self.assertTrue(watch.expired.is_set());self.assertIsNone(watch.error)
        job.reset_mock();watch=OwnWatchdog(job,100)
        with patch.object(watch.stop,'wait',return_value=True):watch._run()
        job.terminate_own.assert_not_called();self.assertFalse(watch.expired.is_set())

    def test_external_watchdog_preserves_termination_failure(self):
        from tools.physical_dev.supervisor import OwnWatchdog
        from unittest.mock import Mock,patch
        job=Mock();job.terminate_own.side_effect=OSError('test')
        watch=OwnWatchdog(job,0)
        with patch.object(watch.stop,'wait',return_value=False):watch._run()
        self.assertTrue(watch.expired.is_set());self.assertEqual(watch.error,'OSError')

    def test_windows_x64_abi_and_fixed_test_limits(self):
        from tools.physical_dev.supervisor import BasicLimits,ExtendedLimits,Accounting,EndAction,limit_blueprint
        self.assertEqual((ctypes.sizeof(BasicLimits),ctypes.sizeof(ExtendedLimits),ctypes.sizeof(Accounting),ctypes.sizeof(EndAction)),(64,144,48,4))
        self.assertEqual((BasicLimits.flags.offset,BasicLimits.active.offset,ExtendedLimits.process_memory.offset,ExtendedLimits.job_memory.offset),(16,40,112,120))
        self.assertEqual(limit_blueprint(),dict(flags=0x230c,active=16,process_commit=536870912,job_commit=1073741824,user_time_100ns=100000000,end_action=0))

    def test_readback_requires_exact_typed_ceilings_and_no_breakaway(self):
        from tools.physical_dev.supervisor import validate_readback,limit_blueprint,SmokeBlocked
        expected=limit_blueprint();self.assertIsNone(validate_readback(expected))
        for key,value in [('flags',0x2b0c),('active',True),('process_commit',536870911),('job_commit',None),('user_time_100ns',100000001),('end_action',False),('end_action',1)]:
            with self.subTest(key=key,value=value),self.assertRaises(SmokeBlocked):validate_readback(dict(expected,**{key:value}))
        with self.assertRaises(SmokeBlocked):validate_readback(dict(expected,runtime_admission=True))

    def test_bootstrap_is_bounded_identity_join_not_authority(self):
        from tools.physical_dev.supervisor import validate_bootstrap,SmokeBlocked
        nonce='a'*32;raw=json.dumps(dict(pid=1234,nonce=nonce)).encode()+b'\n';self.assertIsNone(validate_bootstrap(raw,1234,nonce))
        for bad in [b'{}',raw+b'next',b'x'*257,json.dumps(dict(pid=True,nonce=nonce)).encode(),json.dumps(dict(pid=1235,nonce=nonce)).encode(),json.dumps(dict(pid=1234,nonce='b'*32)).encode(),b'{"pid":1234,"pid":1234,"nonce":"'+nonce.encode()+b'"}',json.dumps(dict(pid=1234,nonce=nonce,Root=True)).encode()]:
            with self.subTest(raw=bad[:80]),self.assertRaises(SmokeBlocked):validate_bootstrap(bad,1234,nonce)

    def test_child_environment_does_not_inherit_credentials_or_preloads(self):
        from tools.physical_dev.supervisor import child_environment
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(prefix='pure-smoke-env-') as tmp,patch.dict('os.environ',{'PGPASSWORD':'do-not-copy','NODE_OPTIONS':'--require injected','NODE_PATH':'unsafe','HTTP_PROXY':'unsafe','BYBIT_API_KEY':'do-not-copy','PYTHONPATH':'unsafe','SELENIUM_REMOTE_URL':'unsafe'}):
            root=Path(tmp).resolve();env=child_environment(root)
            for key in ('PGPASSWORD','NODE_OPTIONS','NODE_PATH','HTTP_PROXY','BYBIT_API_KEY','PYTHONPATH','SELENIUM_REMOTE_URL'):self.assertNotIn(key,env)
            self.assertEqual(env['TEMP'],str(root));self.assertEqual(env['PYTHONDONTWRITEBYTECODE'],'1')
            self.assertEqual(env['GIT_NO_LAZY_FETCH'],'1');self.assertEqual(env['GIT_ALLOW_PROTOCOL'],'')
            self.assertEqual(env['GIT_CONFIG_NOSYSTEM'],'1');self.assertEqual(env['GIT_CONFIG_GLOBAL'],'NUL')
            self.assertNotIn('.',env['PATH'].split(';'))

    def test_watchdog_work_deadline_keeps_cleanup_reserve(self):
        from tools.physical_dev.supervisor import stop_reason,SmokeBlocked
        self.assertIsNone(stop_reason(100,100+19999999999,16384))
        self.assertEqual(stop_reason(100,100+20000000000,0),'WORK_DEADLINE')
        self.assertEqual(stop_reason(100,101,16385),'OUTPUT_BOUND')
        with self.assertRaises(SmokeBlocked):stop_reason(100,99,0)
        with self.assertRaises(SmokeBlocked):stop_reason(100,101,True)

    def test_cleanup_data_cannot_hide_own_active_processes_or_failed_exit(self):
        from tools.physical_dev.supervisor import cleanup_summary,SmokeBlocked
        value=cleanup_summary(0,[0,0]);self.assertEqual(value['status'],'OWN_FAMILY_RETIRED');self.assertIs(value['runtime_admission'],False)
        for active,exits in [(1,[0]),(False,[0]),(0,[None]),(0,[False]),(0,[0,73]),(0,[])]:
            with self.subTest(active=active,exits=exits),self.assertRaises(SmokeBlocked):cleanup_summary(active,exits)

if __name__=='__main__':unittest.main()
