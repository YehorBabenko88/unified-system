"""Framing/selection controls only; no subprocess or native Job qualification."""
import io,json,unittest
from pathlib import Path
from unittest.mock import patch

class LauncherContractTests(unittest.TestCase):
    def test_failed_child_keeps_before_go_identity_and_numeric_exit(self):
        from tools.physical_dev.ls5_smoke import launch,SmokeBlocked
        from unittest.mock import Mock
        import subprocess
        nonce='a'*32;process=Mock();process.pid=1234;process.returncode=71;process.poll.return_value=71
        capture=Mock();capture.ready.get.return_value=json.dumps({'pid':1234,'nonce':nonce}).encode()+b'\n';capture.count=0;capture.error=None
        job=Mock();job.attach_before_go.return_value={'pid':1234,'token':{'elevated':False},'own_job_membership_before_go':1}
        stages={}
        with patch('subprocess.Popen',return_value=process),patch('subprocess.CREATE_NO_WINDOW',0,create=True),patch('tools.physical_dev.ls5_smoke.Capture',return_value=capture),patch('secrets.token_hex',return_value=nonce),patch('time.perf_counter_ns',return_value=0):
            with self.assertRaises(SmokeBlocked):launch(job,['fixed','ROOT_NONCE'],Path('fixed'),{},Path('.'),'backend',0,[],[],stages)
        self.assertEqual(stages['backend']['identity']['pid'],1234)
        self.assertEqual(stages['backend']['identity']['own_job_membership_before_go'],1)
        self.assertEqual(stages['backend']['returncode'],71)
        self.assertEqual(stages['backend']['go_status'],'FLUSH_COMPLETED_NOT_EXECUTION_ACK')

    def test_one_cleanup_deadline_is_shared_by_all_waits(self):
        from tools.physical_dev.ls5_smoke import cleanup_seconds,SmokeBlocked
        with patch('time.perf_counter_ns',return_value=100):self.assertEqual(cleanup_seconds(1000000100,5),1)
        with patch('time.perf_counter_ns',return_value=1000000100):
            with self.assertRaises(SmokeBlocked):cleanup_seconds(1000000100,5)
        with patch('time.perf_counter_ns',return_value=100):self.assertEqual(cleanup_seconds(10000000100,2),2)

    def test_expired_cleanup_still_attempts_own_termination_without_another_wait_window(self):
        from tools.physical_dev.ls5_smoke import retire_unassigned
        from unittest.mock import Mock
        process=Mock();process.poll.return_value=None
        with patch('time.perf_counter_ns',return_value=100):errors=retire_unassigned([process],deadline=99)
        process.terminate.assert_called_once_with();process.wait.assert_called_once_with(timeout=0)
        self.assertTrue(errors)

    def test_offline_source_rejects_promisor_alternate_and_include_config(self):
        from tools.physical_dev.ls5_smoke import offline_repository,SmokeBlocked
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();git=root/'.git';(git/'objects/info').mkdir(parents=True);(git/'objects/pack').mkdir()
            config=git/'config';config.write_text('[core]\nrepositoryformatversion = 0\n')
            self.assertIsNone(offline_repository(root))
            config.write_text('[core]\nautocrlf = false\n[remote "origin"]\nurl = C:/pinned-local\nfetch = +refs/heads/*:refs/remotes/origin/*\n[branch "feature/smoke"]\nremote = origin\nmerge = refs/heads/feature/smoke\n')
            self.assertIsNone(offline_repository(root))
            for raw in ['[remote "origin"]\npromisor = true\n','[extensions]\npartialClone = origin\n','[include]\npath = C:/foreign\n',
                        '[includeIf\t"gitdir:**"]\npath = C:/foreign\n','[remote\t"origin"]\npromisor = true\n',
                        '[remote.origin]\npromisor = true\n','[core]\nsshCommand = arbitrary\n']:
                config.write_text(raw)
                with self.assertRaises(SmokeBlocked):offline_repository(root)
            config.write_text('[core]\nrepositoryformatversion = 0\n')
            for path in (git/'objects/info/alternates',git/'objects/pack/pack-inert.promisor',git/'commondir'):
                path.write_bytes(b'')
                with self.assertRaises(SmokeBlocked):offline_repository(root)
                path.unlink()

    def test_primary_source_deadline_denies_before_creating_process(self):
        from tools.physical_dev.ls5_smoke import PrimaryGit,SmokeBlocked
        root=Path('C:/qualified-source');gate=PrimaryGit(Path('C:/pinned/git.exe'),{}, {str(root)})
        gate.deadline=0
        with patch('subprocess.Popen',side_effect=AssertionError('must not launch after deadline')):
            with self.assertRaises(SmokeBlocked):gate.Popen(['git','--no-replace-objects','-C',str(root),'cat-file','--batch'],stdin=-1,stdout=-1)

    def test_primary_pipe_timeout_retires_only_its_retained_process(self):
        from tools.physical_dev.ls5_smoke import TimedPrimaryStream,SmokeBlocked
        from unittest.mock import Mock
        import threading,time,subprocess
        process=Mock();process.poll.return_value=None;process.terminate.side_effect=OSError('retirement failed')
        process.wait.side_effect=subprocess.TimeoutExpired('inert-owned-fixture',5)
        release=threading.Event();entered=threading.Event();stream=Mock()
        def blocked_read(size):entered.set();release.wait(1);return b'late'
        stream.read.side_effect=blocked_read
        bounded=TimedPrimaryStream(stream,process,lambda:.02);started=time.monotonic()
        try:
            with self.assertRaises(SmokeBlocked):bounded.read(4)
            self.assertTrue(entered.is_set());self.assertLess(time.monotonic()-started,.5)
        finally:release.set()
        process.terminate.assert_called_once_with();process.wait.assert_called_once_with(timeout=5)

    def test_cleanup_failure_is_retained_without_skipping_next_own_process(self):
        from tools.physical_dev.ls5_smoke import retire_unassigned
        from unittest.mock import Mock
        first=Mock();first.poll.return_value=None;first.terminate.side_effect=OSError('race')
        second=Mock();second.poll.return_value=None
        errors=retire_unassigned([first,second])
        self.assertEqual(errors,['OSError','PREASSIGN_BOOTSTRAP_ABORTED'])
        second.terminate.assert_called_once();second.wait.assert_called_once()

    def test_primary_guard_batch_uses_only_fixed_git_and_clean_environment(self):
        from tools.physical_dev.ls5_smoke import PrimaryGit,SmokeBlocked
        root=Path('C:/qualified-source');trusted=Path('C:/pinned/git.exe');env={'SystemRoot':'C:/Windows'}
        gate=PrimaryGit(trusted,env,{str(root)})
        with patch('subprocess.Popen') as popen:
            gate.Popen(['git','--no-replace-objects','-C',str(root),'cat-file','--batch'],stdin=-1,stdout=-1)
            argv=popen.call_args.args[0];options=popen.call_args.kwargs
            self.assertEqual(argv[0],str(trusted));self.assertIn('--no-replace-objects',argv)
            self.assertEqual(options['env'],env);self.assertIs(options['shell'],False)
            for bad in [['git','status'],['git','--no-replace-objects','-C','C:/foreign','cat-file','--batch']]:
                with self.assertRaises(SmokeBlocked):gate.Popen(bad)

    def test_late_capture_failure_cannot_become_success(self):
        from tools.physical_dev.ls5_smoke import validate_captures,SmokeBlocked
        from types import SimpleNamespace
        for items in [[('a',SimpleNamespace(count=1,error='CAPTURE_FAILED'))],
                      [('a',SimpleNamespace(count=10000,error=None)),('b',SimpleNamespace(count=10000,error=None))]]:
            with self.assertRaises(SmokeBlocked):validate_captures(items)
        self.assertIsNone(validate_captures([('a',SimpleNamespace(count=100,error=None))]))

    def test_descriptive_metadata_cannot_omit_fixed_sources(self):
        from tools.physical_dev.ls5_smoke import source_bindings,SmokeBlocked
        with patch('subprocess.check_output',side_effect=AssertionError('no Git process before source label validation')):
            with self.assertRaises(SmokeBlocked):source_bindings(Path('C:/not-executed'),{'source_metadata':{'sources':[]}})

    def test_capture_frame_and_combined_log_ceiling_without_any_child(self):
        from tools.physical_dev.ls5_smoke import Capture
        class Stream:
            def fileno(self):return 1
        capture=object.__new__(Capture)
        import threading,queue
        capture.ready=queue.Queue(maxsize=1);capture.lock=threading.Lock();capture.count=0;capture.error=None
        capture.logs={'stdout':bytearray(),'stderr':bytearray()};capture.threads=[]
        raw=b'{"pid":1234,"nonce":"'+b'a'*32+b'"}\n'
        with patch('os.read',side_effect=[raw,b'']):capture._read('stdout',Stream())
        self.assertEqual(capture.ready.get_nowait(),raw)
        with patch('os.read',side_effect=[b'x'*4096]*5+[b'']):capture._read('stderr',Stream())
        self.assertEqual(capture.error,'OUTPUT_BOUND');self.assertLessEqual(sum(map(len,capture.logs.values())),16384)

    def test_oversized_pre_go_frame_has_no_ready_signal(self):
        from tools.physical_dev.ls5_smoke import Capture
        import threading,queue
        capture=object.__new__(Capture);capture.ready=queue.Queue(maxsize=1);capture.lock=threading.Lock();capture.count=0;capture.error=None
        capture.logs={'stdout':bytearray(),'stderr':bytearray()};capture.threads=[]
        class Stream:
            def fileno(self):return 1
        with patch('os.read',side_effect=[b'x'*257,b'']):capture._read('stdout',Stream())
        self.assertEqual(capture.error,'BOOTSTRAP_BOUND');self.assertTrue(capture.ready.empty())

if __name__=='__main__':unittest.main()
