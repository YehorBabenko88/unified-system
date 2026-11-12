"""Inert controls for the ACTUAL PG custodian; no process/thread/PG/SQL fixture."""
import unittest
from tools.collector import pg_qualification as pg

class Clock:
    def __init__(self):self.value=0.;self.broken=False
    def __call__(self):
        if self.broken:raise RuntimeError('inert clock')
        return self.value

class Process:
    def __init__(self):self.stdout=object();self.stderr=object();self.pid=123;self.code=0

class Reader:
    def __init__(self,owner,which,capture):self.owner=owner;self.which=which;self.capture=capture;self.ident=1
    def start(self):
        self.owner.events.append('reader_start')
        if self.owner.fault=='reader_start':self.ident=None;raise RuntimeError('inert start')
        self.capture.feed(self.which,self.owner.output[self.which])
    def join(self,timeout):self.owner.events.append('reader_join')
    def is_alive(self):return self.owner.fault=='reader_alive'

class Backend:
    def __init__(self,fault=None):self.events=[];self.fault=fault;self.output=[b'out',b'err'];self.clock=Clock();self.entries=[];self.server=None
    def admit(self,plan):self.events.append('admit')
    def create_suspended(self,entry,command):
        self.events.append('create_suspended')
        if self.fault=='creation_unknown':raise RuntimeError('inert creation')
        entry['process']=Process();self.entries.append(entry)
        if command.role=='server':entry['process'].code=None;self.server=entry
        if self.fault=='slow_create':self.clock.value=61.
    def attach(self,entry,job):
        self.events.append('attach');entry['job']=job or object()
        if self.fault=='attach':raise RuntimeError('inert attach')
        return entry['job']
    def configure_and_readback(self,job):
        self.events.append('limits_readback')
        if self.fault=='readback':raise RuntimeError('inert readback')
        return dict(pg.LIMITS)
    def member(self,entry,job):self.events.append('member');return True
    def reader(self,entry,which,capture):
        if self.fault=='reader_constructor':raise RuntimeError('inert constructor')
        return Reader(self,which,capture)
    def resume(self,entry):
        self.events.append('resume')
        if self.fault=='resume':raise RuntimeError('inert resume')
        if entry['role']=='stop':self.server['process'].code=0
        if self.fault=='late_exit':self.clock.value=61.
        if self.fault=='clock':self.clock.broken=True
    def poll(self,entry):
        self.events.append('poll')
        if self.fault in ('poll','poll_kill_wait'):raise RuntimeError('inert poll')
        return entry['process'].code
    def wait(self,entry,timeout):
        self.events.append('wait')
        if self.fault=='poll_kill_wait':raise RuntimeError('inert wait')
        return entry['process'].code
    def kill_primary(self,entry):
        self.events.append('kill_primary')
        if self.fault=='poll_kill_wait':raise RuntimeError('inert kill')
        entry['process'].code=1
    def active(self,job):return sum(e['process'].code is None for e in self.entries)
    def server_ready(self,entry,job):
        self.events.append('server_ready')
        if self.fault=='foreign_listener':raise RuntimeError('inert foreign listener')
        return True
    def terminate_and_wait(self,job,timeout):
        self.events.append('terminate_job')
        if self.fault=='job_kill':raise RuntimeError('inert job')
        for entry in self.entries:
            if entry['process'].code is None:entry['process'].code=1
        return True
    def close_pipe(self,entry,which):self.events.append('pipe_close')
    def close_primary(self,entry):self.events.append('primary_close')
    def sleep(self,seconds):self.clock.value+=seconds
    def before_command(self,command):self.events.append('command_check')
    def after(self):self.events.append('postcheck')

class PgCustodyTests(unittest.TestCase):
    def run_inert(self,fault=None,output=None):
        backend=Backend(fault)
        if output is not None:backend.output=output
        session=pg.PgCustodian(pg.Plan.model(),backend,clock=backend.clock)
        command=pg.command_for(session.plan,'initdb')
        if fault is None and output is None:
            session.run(command);receipt=session.close();self.assertTrue(receipt['family_retired'])
        else:
            with self.assertRaises(pg.CustodyDenied):session.run(command)
            receipt=session.close()
            self.assertFalse(receipt['transport_ok'])
        return backend,session,receipt
    def test_suspended_attach_limits_membership_precede_resume(self):
        b,s,r=self.run_inert();self.assertEqual([e for e in b.events if e in ('create_suspended','attach','limits_readback','member','resume')],['create_suspended','attach','limits_readback','member','resume'])
        self.assertTrue(r['transport_ok']);self.assertFalse(r['database_qualified'])
    def test_assignment_failure_never_resumes(self):
        b,s,r=self.run_inert('attach');self.assertNotIn('resume',b.events);self.assertIn('terminate_job',b.events);self.assertIn('wait',b.events)
    def test_limit_readback_failure_never_resumes(self):
        b,s,r=self.run_inert('readback');self.assertNotIn('resume',b.events);self.assertIn('terminate_job',b.events)
    def test_resume_error_is_sticky_and_retired(self):
        b,s,r=self.run_inert('resume');self.assertIn('terminate_job',b.events);self.assertTrue(r['errors'])
    def test_poll_failure_still_attempts_owned_kill_and_wait(self):
        b,s,r=self.run_inert('poll');self.assertIn('kill_primary',b.events);self.assertIn('wait',b.events)
    def test_job_termination_failure_is_not_empty_job(self):
        b,s,r=self.run_inert('job_kill',[b'x'*(pg.CAP+1),b'']);self.assertFalse(r['family_retired']);self.assertIn('wait',b.events)
    def test_kill_and_wait_failures_are_independent(self):
        b,s,r=self.run_inert('poll_kill_wait');self.assertIn('kill_primary',b.events);self.assertIn('wait',b.events)
        self.assertIn('PRIMARY_KILL_UNCERTAIN',[e['code'] for e in r['errors']]);self.assertIn('PRIMARY_WAIT_UNCERTAIN',[e['code'] for e in r['errors']])
    def test_combined_output_overflow_is_sticky_on_zero_exit(self):
        b,s,r=self.run_inert(output=[b'x'*(pg.CAP//2+1),b'y'*(pg.CAP//2+1)]);self.assertGreater(r['output_observed'],pg.CAP);self.assertLessEqual(sum(map(len,s.private_output())),pg.CAP)
    def test_nonreturned_reader_start_never_blind_closes_pipe(self):
        b,s,r=self.run_inert('reader_start');self.assertNotIn('pipe_close',b.events);self.assertFalse(r['readers_retired'])
    def test_reader_constructor_uncertainty_retains_pipe(self):
        b,s,r=self.run_inert('reader_constructor');self.assertNotIn('pipe_close',b.events);self.assertFalse(r['readers_retired'])
    def test_unreturned_creation_is_unknown(self):
        b,s,r=self.run_inert('creation_unknown');self.assertFalse(r['family_retired']);self.assertNotIn('resume',b.events)
    def test_late_zero_exit_does_not_pass_phase_deadline(self):
        b,s,r=self.run_inert('late_exit');self.assertIn('PRIMARY_FAILURE',[e['code'] for e in r['errors']])
    def test_clock_failure_does_not_skip_cleanup(self):
        b,s,r=self.run_inert('clock');self.assertIn('terminate_job',b.events);self.assertIn('wait',b.events)
    def test_failed_session_cannot_launch_again(self):
        b,s,r=self.run_inert('poll');n=b.events.count('create_suspended')
        with self.assertRaises(pg.CustodyDenied):s.run(pg.command_for(s.plan,'initdb'))
        self.assertEqual(n,b.events.count('create_suspended'))
    def test_command_roles_have_no_arbitrary_executable_or_port(self):
        plan=pg.Plan.model();command=pg.command_for(plan,'stop');self.assertEqual(command.role,'stop');self.assertNotIn('kill',command.argv);self.assertIn('55483',pg.command_for(plan,'server').argv)
        with self.assertRaises(ValueError):pg.command_for(plan,'register')
        self.assertEqual(pg.SQL_NAMES,('bootstrap','migrate','verify','readback'))
        self.assertEqual(pg.command_for(plan,'psql','verify').sql_name,'verify')
        with self.assertRaises(ValueError):pg.command_for(plan,'psql','rollback')
    def test_model_plan_is_never_native_admission(self):
        self.assertFalse(pg.Plan.model().native)
        with self.assertRaises(ValueError):pg.WindowsBackend(pg.Plan.model(),None,None)

    def test_slow_creation_cannot_resume_after_phase_end(self):
        b,s,r=self.run_inert('slow_create');self.assertNotIn('resume',b.events);self.assertIn('wait',b.events)
    def test_owned_server_protocol_keeps_one_job_until_final_cleanup(self):
        b=Backend();s=pg.PgCustodian(pg.Plan.model(),b,clock=b.clock)
        s.run(pg.command_for(s.plan,'initdb'));s.start_server();s.wait_server_ready()
        s.run(pg.command_for(s.plan,'psql'));s.run(pg.command_for(s.plan,'stop'))
        self.assertNotIn('terminate_job',b.events)
        r=s.close();self.assertTrue(r['transport_ok']);self.assertTrue(r['protocol_complete']);self.assertFalse(r['database_qualified'])
        self.assertEqual(b.events.count('terminate_job'),1)
    def test_foreign_listener_denies_before_any_psql_launch(self):
        b=Backend();s=pg.PgCustodian(pg.Plan.model(),b,clock=b.clock)
        s.run(pg.command_for(s.plan,'initdb'));s.start_server();b.fault='foreign_listener'
        with self.assertRaises(pg.CustodyDenied):s.wait_server_ready()
        self.assertNotIn('psql',s.snapshot()['source_roles']);self.assertFalse(s.snapshot()['transport_ok']);self.assertIn('terminate_job',b.events)

    def test_actual_native_constructor_uses_documented_suspended_flag_with_inert_popen(self):
        import subprocess
        from pathlib import Path
        from types import SimpleNamespace
        calls=[];original=subprocess.Popen
        process=SimpleNamespace(_handle=123,pid=456)
        def popen(*args,**kwargs):calls.append((args,kwargs));return process
        backend=object.__new__(pg.WindowsBackend);backend.root=Path('C:/INERT/UnifiedCollectorTest/pg-attempt1');backend.secret_root=backend.root/'secrets'
        backend.c=SimpleNamespace(c_void_p=lambda n:n);backend.kernel=object();backend.w=object()
        command=pg.command_for(pg.Plan.model(),'initdb');backend.runtime=SimpleNamespace(_win_identity=lambda *args:['INERT',str(Path(command.argv[0]))])
        entry={}
        subprocess.Popen=popen
        try:backend.create_suspended(entry,command)
        finally:subprocess.Popen=original
        self.assertIs(entry['process'],process);self.assertEqual(len(calls),1)
        self.assertEqual(calls[0][1]['creationflags'],0x00000004|subprocess.CREATE_NO_WINDOW)
        self.assertFalse(calls[0][1]['shell']);self.assertTrue(calls[0][1]['close_fds'])
