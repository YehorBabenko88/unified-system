"""Bounded local owner-loss fixture; no distributed restart/resource qualification."""
import json
import hashlib
import os
from pathlib import Path
import sys
import time
import unittest
import uuid
from unittest.mock import patch, MagicMock
from owned_supervisor_loss import decode_ready, rejoin_denials, qualify_owner_loss
import owned_supervisor_loss as fixture

def ready():
    return dict(schema='a5.local-owned-supervisor-ready.v1',node_id=str(uuid.uuid4()),
        incarnation_id=str(uuid.uuid4()),attempt_id=str(uuid.uuid4()),original_sha256='0'*64,
        process_handle=123,pid=456,creation_filetime='123456',image='C:/test/python.exe',
        directory_name='a5-owned-suspended-test',directory_device=0,directory_inode=1,
        inner_kill_on_close=True,resource_admitted_fields=[])

class SupervisorBoundary(unittest.TestCase):
    def test_failed_identity_or_outer_assignment_never_sends_arm(self):
        # Inert process/API refusal assertions, not Windows custody evidence.
        executable=Path(sys.executable).resolve()
        for bad_image in (True,False):
            process=MagicMock();process.pid=1234;process._handle.__int__.return_value=123
            process.poll.return_value=0
            kernel=MagicMock();kernel.GetProcessId.return_value=1234
            image=str(executable)+'-wrong' if bad_image else str(executable)
            with self.subTest(bad_image=bad_image),patch.object(fixture,'_api',return_value=kernel),patch.object(fixture,'_grid',return_value=object()),patch.object(fixture.subprocess,'Popen',return_value=process),patch.object(fixture.gw,'_DIRECT_INTERPRETER',executable),patch.object(fixture.gw,'_DIRECT_INTERPRETER_SHA',hashlib.sha256(executable.read_bytes()).hexdigest()),patch.object(fixture.gw,'_attempt_identity',return_value=('123456',image)),patch.object(fixture,'_outer_job',side_effect=ValueError('nested assignment refused')) as outer:
                with self.assertRaises(fixture.SupervisorLossError) as error:fixture.qualify_owner_loss('unused')
                process.stdin.write.assert_not_called();process.stdin.flush.assert_not_called()
                self.assertEqual(error.exception.cleanup_diagnostics,())
                if bad_image:outer.assert_not_called()
                else:outer.assert_called_once()
    def test_expired_cleanup_deadline_still_closes_each_retained_handle(self):
        events=[]
        class Close:
            def __init__(self,name):self.name=name
            def close(self):events.append(self.name)
            Close=close
        class Process:
            stdin=Close('stdin');stdout=Close('stdout');_handle=Close('process')
            def poll(self):return 0
            def wait(self,**kwargs):raise AssertionError('expired deadline must not wait')
        errors=fixture._retire_owner(Process(),time.monotonic()-1)
        self.assertEqual(events,['stdin','stdout','process'])
        self.assertEqual([e[0] for e in errors],['own_owner_wait'])
    def test_termination_wait_and_close_faults_do_not_skip_other_closures(self):
        events=[]
        class Close:
            def __init__(self,name):self.name=name
            def close(self):
                events.append(self.name)
                if self.name=='stdout':raise OSError('close fault')
            Close=close
        class Process:
            stdin=Close('stdin');stdout=Close('stdout');_handle=Close('process')
            def poll(self):return None
            def terminate(self):raise OSError('termination fault')
            def wait(self,**kwargs):raise TimeoutError('wait fault')
        errors=fixture._retire_owner(Process(),time.monotonic()+1)
        self.assertEqual(events,['stdin','stdout','process'])
        self.assertEqual([e[0] for e in errors],['own_owner_terminate','own_owner_wait','own_stdout_close'])
    def test_ready_shape_is_bounded_untrusted_data(self):
        value=ready();raw=json.dumps(value).encode('ascii')
        self.assertEqual(decode_ready(raw,expected_original_sha256='0'*64),value)
        for b in (b'x'*16385,b'{"a":1,"a":2}',b'[]',b'{'):
            with self.assertRaises(ValueError):decode_ready(b,expected_original_sha256='0'*64)
        for field,bad in [('process_handle',True),('pid',-1),('inner_kill_on_close',False),
                          ('resource_admitted_fields',['cpu']),('directory_name','../outside')]:
            v={**value,field:bad}
            with self.subTest(field=field),self.assertRaises(ValueError):
                decode_ready(json.dumps(v).encode(),expected_original_sha256='0'*64)
        with self.assertRaises(ValueError):decode_ready(raw,expected_original_sha256='1'*64)
    def test_rejoin_rejects_old_data_without_preparation_or_start(self):
        with patch('unified_system.gateway_worker.GatewayWorker.prepare_attempt',side_effect=AssertionError('must not prepare')) as prepare:
            result=rejoin_denials(ready())
            prepare.assert_not_called()
        self.assertEqual(result['outcome'],'UNKNOWN')
        self.assertTrue(result['old_data_rejected'])
        self.assertFalse(result['dispatch_authorized'])
        self.assertEqual(result['resume_calls'],0)

class ActualOwnedSupervisorLoss(unittest.TestCase):
    def test_actual_owner_crash_and_fresh_rejoin_suspended_only(self):
        grid=os.environ.get('AGENT5_GRID_PRIMARY_REPOSITORY','C:/Users/LS-5/Documents/Codex/2026-11-06/codex-agent-2-high-availability-distributed/work/grid-assignment-native-20261107')
        result=qualify_owner_loss(grid)
        self.assertTrue(result['owner_exit_observed'])
        self.assertTrue(result['worker_exit_observed'])
        self.assertTrue(result['outer_job_empty_observed'])
        self.assertFalse(result['rescue_needed'])
        self.assertEqual(result['restart']['outcome'],'UNKNOWN')
        self.assertNotEqual(result['restart']['incarnation_id'],result['ready']['incarnation_id'])
        self.assertEqual(result['resume_calls'],0)
        self.assertEqual(result['resource_admitted_fields'],[])
        self.assertFalse(result['dispatch_authorized'])
        type(self).last_observation=result

def load_tests(loader,tests,pattern):
    suite=loader.loadTestsFromTestCase(SupervisorBoundary)
    if os.environ.get('AGENT5_RUN_OWNED_SUPERVISOR_LOSS')=='1':
        suite.addTests(loader.loadTestsFromTestCase(ActualOwnedSupervisorLoss))
    else:print('OWNED_SUPERVISOR_LOSS_NATIVE_NOT_RUN_EXPLICIT_SELECTION_REQUIRED')
    return suite
