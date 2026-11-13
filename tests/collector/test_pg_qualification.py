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
    def test_projection_rejects_string_alias_values_without_callbacks_or_leaks(self):
        b,s,r=self.run_inert('poll');calls=[]
        class Alias(str):
            def __eq__(self,other):calls.append('eq');return True
            def __ne__(self,other):calls.append('ne');return False
            def __hash__(self):calls.append('hash');return str.__hash__(self)
        import copy
        for slot in ('scope','source_roles','error_code','error_type','entry_role','sql_name'):
            v=copy.deepcopy(r);alias=Alias('PRIVATE_SENTINEL')
            if slot=='scope':v['scope']=alias
            elif slot=='source_roles':v['source_roles']=[alias]
            elif slot=='error_code':v['errors'][0]['code']=alias
            elif slot=='error_type':v['errors'][0]['error_type']=alias
            elif slot=='entry_role':v['entries'][0]['role']=alias
            else:v['entries'][0]['sql_name']=alias
            calls.clear()
            with self.subTest(slot=slot):
                result=pg.public_denial_receipt(pg.CustodyDenied(v));self.assertIsNone(result);self.assertEqual(calls,[]);self.assertNotIn('PRIVATE_SENTINEL',str(result))
    def test_projection_rejects_nonbuiltin_keys_before_hash_or_equality(self):
        import copy
        b,s,r=self.run_inert('poll');calls=[]
        class Key(str):
            def __eq__(self,other):calls.append('eq');return str.__eq__(self,other)
            def __hash__(self):calls.append('hash');return str.__hash__(self)
        for slot in ('root','error','entry'):
            v=copy.deepcopy(r);row=v if slot=='root' else v['errors'][0] if slot=='error' else v['entries'][0]
            key=next(iter(row));value=row.pop(key);row[Key(key)]=value;calls.clear()
            with self.subTest(slot=slot):self.assertIsNone(pg.public_denial_receipt(pg.CustodyDenied(v)));self.assertEqual(calls,[])
    def test_fixed_native_attempt2_root_rejects_old_alias_and_foreign_profile(self):
        from pathlib import Path
        profile=Path(Path.cwd().anchor)/'INERT';root=profile/'AppData/Local/UnifiedCollectorTest/pg-attempt2'
        for wrong in (root,root.parent/'pg-attempt1',root/'..',Path('C:/Users/OTHER/AppData/Local/UnifiedCollectorTest/pg-attempt2'),str(root)):
            with self.subTest(wrong=type(wrong).__name__),self.assertRaises(ValueError):pg._require_native_root(wrong,profile)
    def test_fixed_native_attempt3_positive_consumed_roots_and_aliases_deny(self):
        from pathlib import Path
        profile=Path(Path.cwd().anchor)/'INERT';root=profile/'AppData/Local/UnifiedCollectorTest/pg-attempt3'
        pg._require_native_root(root,profile)
        for wrong in (root.parent/'pg-attempt1',root.parent/'pg-attempt2',root/'..',str(root),Path(Path.cwd().anchor)/'OTHER/AppData/Local/UnifiedCollectorTest/pg-attempt3'):
            with self.subTest(kind=type(wrong).__name__),self.assertRaises(ValueError):pg._require_native_root(wrong,profile)
    def test_receipt_tracks_actual_primary_and_pipe_close_acknowledgements(self):
        b,s,r=self.run_inert();e=r['entries'][0]
        self.assertIs(e['primary_closed'],True);self.assertEqual(e['pipes_closed'],[True,True])
        self.assertIs(r['primary_closed_all'],True);self.assertIs(r['pipes_closed_all'],True)
    def test_pipe_close_failure_is_sticky_not_family_retirement_proof(self):
        b=Backend();s=pg.PgCustodian(pg.Plan.model(),b,clock=b.clock)
        def bad(*args):raise RuntimeError('PRIVATE SQL PASSWORD')
        b.close_pipe=bad;s.run(pg.command_for(s.plan,'initdb'));r=s.close()
        self.assertTrue(r['family_retired']);self.assertFalse(r['pipes_closed_all']);self.assertFalse(r['transport_ok'])
    def test_denial_projection_detached_closed_and_private(self):
        b,s,r=self.run_inert('poll');e=pg.CustodyDenied(r);v=pg.public_denial_receipt(e)
        self.assertEqual(v['scope'],'OWNED_PG_TOOL_CUSTODY_ONLY');self.assertNotIn('inert',str(v))
        self.assertEqual(v['command_counts'],{'initdb':1,'server':0,'psql':0,'stop':0});self.assertEqual(v['sql_counts'],dict.fromkeys(pg.SQL_NAMES,0))
        r['errors'][0]['code']='PASSWORD_SECRET';self.assertNotIn('PASSWORD_SECRET',str(v))
        self.assertIsNone(pg.public_denial_receipt(RuntimeError('PRIVATE')))
        class Other(pg.CustodyDenied):pass
        self.assertIsNone(pg.public_denial_receipt(Other(r)))
    def test_denial_projection_rejects_type_alias_unknown_and_oversize(self):
        import copy
        b,s,r=self.run_inert('poll')
        for key,value in [('errors',[{'code':'PRIVATE_SECRET','error_type':'RuntimeError'}]),('output_observed',True),('source_roles',['PASSWORD']),('entries',[{}]*17)]:
            altered=copy.deepcopy(r);altered[key]=value
            with self.subTest(key=key):self.assertIsNone(pg.public_denial_receipt(pg.CustodyDenied(altered)))
    def test_pending_cleanup_projection_never_claims_closed_handles(self):
        b,s,r=self.run_inert('reader_start');v=pg.public_denial_receipt(pg.CustodyDenied(r))
        self.assertFalse(v['pipes_closed_all']);self.assertFalse(v['readers_retired']);self.assertFalse(v['transport_ok'])
    def test_projection_rejects_aliased_and_truncated_receipts(self):
        import copy
        b,s,r=self.run_inert('poll');r['errors'].append(r['errors'][0])
        self.assertIsNone(pg.public_denial_receipt(pg.CustodyDenied(r)))
        r=s.snapshot();del r['primary_closed_all']
        self.assertIsNone(pg.public_denial_receipt(pg.CustodyDenied(r)))
    def test_primary_close_failure_has_no_acknowledgement(self):
        b=Backend();s=pg.PgCustodian(pg.Plan.model(),b,clock=b.clock)
        b.close_primary=lambda *args:(_ for _ in ()).throw(RuntimeError('PRIVATE'))
        with self.assertRaises(pg.CustodyDenied):s.run(pg.command_for(s.plan,'initdb'))
        r=s.close();self.assertFalse(r['primary_closed_all']);self.assertFalse(r['transport_ok'])
        self.assertIsNotNone(pg.public_denial_receipt(pg.CustodyDenied(r)))
    def test_unknown_error_class_is_normalized_without_classname_disclosure(self):
        class PRIVATE_PASSWORD_CLASS(Exception):pass
        b=Backend();s=pg.PgCustodian(pg.Plan.model(),b,clock=b.clock)
        s._error('PRIMARY_FAILURE',PRIVATE_PASSWORD_CLASS('secret'));r=s.close()
        v=pg.public_denial_receipt(pg.CustodyDenied(r));self.assertIsNotNone(v)
        self.assertNotIn('PRIVATE_PASSWORD',str(v));self.assertEqual(v['errors'][0]['error_type'],'UNKNOWN')
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
        from unittest.mock import patch
        from pathlib import Path
        from types import SimpleNamespace
        calls=[]
        process=SimpleNamespace(_handle=123,pid=456)
        def popen(*args,**kwargs):calls.append((args,kwargs));return process
        backend=object.__new__(pg.WindowsBackend);backend.root=Path('C:/INERT/UnifiedCollectorTest/pg-attempt1');backend.secret_root=backend.root/'secrets'
        backend.c=SimpleNamespace(c_void_p=lambda n:n);backend.kernel=object();backend.w=object()
        command=pg.command_for(pg.Plan.model(),'initdb');backend.runtime=SimpleNamespace(_win_identity=lambda *args:['INERT',str(Path(command.argv[0]))])
        entry={}
        # Data-only Win32 flag exists only while Popen is the inert test double.
        with patch.object(subprocess,'Popen',popen),patch.object(subprocess,'CREATE_NO_WINDOW',0x08000000,create=True),patch.dict(pg.os.environ,{'SYSTEMROOT':'C:/INERT/Windows','WINDIR':'C:/INERT/Windows','COMSPEC':'C:/INERT/Windows/System32/cmd.exe'},clear=True):
            backend.create_suspended(entry,command)
        self.assertIs(entry['process'],process);self.assertEqual(len(calls),1)
        self.assertEqual(calls[0][1]['creationflags'],0x00000004|0x08000000)
        self.assertFalse(calls[0][1]['shell']);self.assertTrue(calls[0][1]['close_fds'])

    def test_actual_job_setter_closed_profiles_and_win32_flags(self):
        from types import SimpleNamespace
        for profile,processes,memory,cpu in [('INNER',32,1073741824,60),('OUTER',64,2147483648,120)]:
            k=LimitKernel();job=SimpleNamespace(_kernel=k,_job=123);r=pg._configure_job_limits(job,profile)
            self.assertEqual((r['active_processes'],r['process_memory_bytes'],r['job_memory_bytes'],r['job_user_seconds']),(processes,536870912,memory,cpu));self.assertEqual(k.saved[0],0x230c)
            self.assertTrue(r['kill_on_close']);self.assertFalse(r['breakaway']);self.assertEqual(k.calls,1)
            pg._configure_job_limits(job,profile);self.assertEqual(k.calls,1)
    def test_actual_job_setter_unknown_profile_never_calls_kernel(self):
        from types import SimpleNamespace
        k=LimitKernel()
        with self.assertRaises(ValueError):pg._configure_job_limits(SimpleNamespace(_kernel=k,_job=123),'ARBITRARY')
        self.assertEqual(k.calls,0)
    def test_actual_job_readback_mismatch_denies_all_critical_fields(self):
        from types import SimpleNamespace
        for field in range(5):
            k=LimitKernel(tamper=field)
            with self.subTest(field=field),self.assertRaises(ValueError):pg._configure_job_limits(SimpleNamespace(_kernel=k,_job=123),'INNER')
    def test_actual_job_query_failure_never_resets_applied_cpu_budget(self):
        from types import SimpleNamespace
        k=LimitKernel(query_failure=True);job=SimpleNamespace(_kernel=k,_job=123)
        with self.assertRaises(ValueError):pg._configure_job_limits(job,'INNER')
        k.query_failure=False;pg._configure_job_limits(job,'INNER');self.assertEqual(k.calls,1)
    def test_actual_job_profile_cannot_be_changed(self):
        from types import SimpleNamespace
        k=LimitKernel();job=SimpleNamespace(_kernel=k,_job=123);pg._configure_job_limits(job,'INNER')
        with self.assertRaises(ValueError):pg._configure_job_limits(job,'OUTER')
        self.assertEqual(k.calls,1)
class LimitKernel:
    def __init__(self,tamper=None,query_failure=False):self.saved=None;self.calls=0;self.tamper=tamper;self.query_failure=query_failure
    def SetInformationJobObject(self,handle,kind,pointer,size):
        self.calls+=1;x=pointer._obj;self.saved=[x.basic.flags,x.basic.processes,x.basic.job_time,x.process_memory,x.job_memory];return True
    def QueryInformationJobObject(self,handle,kind,pointer,size,outsize):
        if self.query_failure:return False
        values=list(self.saved)
        if self.tamper is not None:values[self.tamper]+=1
        x=pointer._obj;x.basic.flags,x.basic.processes,x.basic.job_time,x.process_memory,x.job_memory=values;outsize._obj.value=size;return True

class ServerReadinessTests(unittest.TestCase):
    """Actual helper predicates/parser; inert streams/entries, never a fake DB."""
    def entry(self,pid=17):
        from types import SimpleNamespace
        return dict(role='server',process=SimpleNamespace(pid=pid,_handle=1,stderr=object()),job=object(),identity=['INERT_CREATION','INERT_IMAGE'])
    def backend(self,entry):
        from types import SimpleNamespace
        b=object.__new__(pg.WindowsBackend);b.kernel=object();b.w=object();b.c=SimpleNamespace(c_void_p=lambda v:v)
        b.poll=lambda e:None;b.member=lambda e,j:True;b.pg=SimpleNamespace(_listener_pid=lambda port:entry['process'].pid)
        b.runtime=SimpleNamespace(_win_identity=lambda *args:list(entry['identity']));return b
    def bound(self,pid=17):
        e=self.entry(pid);c=pg.Capture();watch=c.bind_server(e,e['process'].stderr);return e,c,watch
    def marker(self,pid=17):return str(pid).encode()+b' LOG:  database system is ready to accept connections\n'
    def test_owned_tcp_listener_without_normal_marker_is_not_ready(self):
        e=self.entry();b=self.backend(e)
        self.assertFalse(b.server_ready(e,e['job']),'owned listening socket is not PostgreSQL accepting connections')
    def test_exact_server_stderr_marker_and_owned_transport_are_ready(self):
        e,c,w=self.bound();c.feed(1,self.marker(),server=w);self.assertTrue(self.backend(e).server_ready(e,e['job']))
    def test_marker_every_chunk_boundary_and_crlf_require_complete_record(self):
        raw=self.marker()
        for index in range(len(raw)):
            e,c,w=self.bound();c.feed(1,raw[:index],server=w);self.assertFalse(self.backend(e).server_ready(e,e['job']))
            c.feed(1,raw[index:],server=w);self.assertTrue(self.backend(e).server_ready(e,e['job']))
        e,c,w=self.bound();c.feed(1,raw[:-1]+b'\r\n',server=w);self.assertTrue(self.backend(e).server_ready(e,e['job']))
    def test_wrong_pid_substring_recovery_marker_and_extra_text_deny(self):
        for raw in (self.marker(18),b'PREFIX '+self.marker(),self.marker().replace(b'connections',b'read-only connections'),self.marker()[:-1]+b' EXTRA\n',self.marker()[:-1]):
            e,c,w=self.bound();c.feed(1,raw,server=w)
            with self.subTest(kind=len(raw)):self.assertFalse(self.backend(e).server_ready(e,e['job']))
    def test_shared_initdb_psql_and_stdout_bytes_cannot_mint_marker(self):
        e,c,w=self.bound();c.feed(1,self.marker());c.feed(0,self.marker());self.assertFalse(self.backend(e).server_ready(e,e['job']))
        c.feed(0,self.marker(),server=w);self.assertFalse(self.backend(e).server_ready(e,e['job']));self.assertTrue(c.failed)
        other=self.entry();other['role']='initdb'
        with self.assertRaises(ValueError):pg.Capture().bind_server(other,other['process'].stderr)
    def test_line_overflow_reader_error_and_combined_output_overflow_are_sticky(self):
        for fault in ('line','reader','combined'):
            e,c,w=self.bound()
            if fault=='line':c.feed(1,b'x'*4097+b'\n',server=w)
            elif fault=='reader':c.reader_error()
            else:c.feed(0,b'x'*(pg.CAP+1))
            c.feed(1,self.marker(),server=w)
            with self.subTest(fault=fault):self.assertTrue(c.failed);self.assertFalse(self.backend(e).server_ready(e,e['job']))
    def test_restart_entry_cannot_use_previous_marker_or_copied_state(self):
        e,c,w=self.bound();c.feed(1,self.marker(),server=w);e2=self.entry(18);w2=c.bind_server(e2,e2['process'].stderr)
        self.assertTrue(self.backend(e).server_ready(e,e['job']));self.assertFalse(self.backend(e2).server_ready(e2,e2['job']))
        e2['_server_marker']=w;self.assertFalse(self.backend(e2).server_ready(e2,e2['job']))
    def test_process_identity_job_or_pipe_rebinding_denies(self):
        from types import SimpleNamespace
        for field in ('identity','job','process','stderr'):
            e,c,w=self.bound();c.feed(1,self.marker(),server=w);b=self.backend(e)
            if field=='identity':e['identity']=['OTHER','INERT_IMAGE']
            elif field=='job':e['job']=object()
            elif field=='process':e['process']=SimpleNamespace(pid=17,_handle=1,stderr=object())
            else:e['process'].stderr=object()
            with self.subTest(field=field):self.assertFalse(b.server_ready(e,e['job']))
    def test_exited_process_foreign_listener_or_foreign_job_never_ready(self):
        e,c,w=self.bound();c.feed(1,self.marker(),server=w);b=self.backend(e);b.poll=lambda e:1
        with self.assertRaises(ValueError):b.server_ready(e,e['job'])
        b=self.backend(e);b.pg._listener_pid=lambda p:999
        with self.assertRaises(ValueError):b.server_ready(e,e['job'])
        b=self.backend(e);self.assertFalse(b.server_ready(e,object()))
    def test_only_actual_server_stderr_reader_binds_observer_before_start(self):
        from types import SimpleNamespace
        e=self.entry();e['process'].stdout=object();c=pg.Capture();b=self.backend(e);calls=[];old=pg._PipeReader
        def reader(pipe,which,capture,server=None):calls.append((pipe,which,server));return object()
        pg._PipeReader=reader
        try:b.reader(e,0,c);b.reader(e,1,c)
        finally:pg._PipeReader=old
        self.assertIsNone(calls[0][2]);self.assertIsNotNone(calls[1][2]);self.assertIs(calls[1][2],e['_server_marker'])
        self.assertFalse(calls[1][2].seen)
        late=self.entry();late['resumed']=True
        with self.assertRaises(ValueError):pg.Capture().bind_server(late,late['process'].stderr)
    def test_no_bootstrap_launch_while_ready_predicate_remains_false(self):
        b=Backend();s=pg.PgCustodian(pg.Plan.model(),b,clock=b.clock);s.run(pg.command_for(s.plan,'initdb'));s.start_server()
        b.server_ready=lambda *args:False
        with self.assertRaises(pg.CustodyDenied):s.wait_server_ready()
        self.assertNotIn('psql',s.snapshot()['source_roles']);self.assertIn('terminate_job',b.events)
    def test_server_command_closed_logging_and_existing_budgets_roles_preserved(self):
        args=pg.command_for(pg.Plan.model(),'server').argv
        for setting in ('lc_messages=C','log_line_prefix=%p ','log_min_messages=log','log_error_verbosity=terse','logging_collector=off','log_destination=stderr','log_statement=none','log_min_error_statement=panic'):
            with self.subTest(setting=setting):self.assertIn(setting,args)
        self.assertEqual(pg.SQL_NAMES,('bootstrap','migrate','verify','readback'));self.assertEqual(pg.CAPS['server'],15.);self.assertEqual(pg.CAP,262144)

class IntegratedSupplierPinTests(unittest.TestCase):
    """Actual constructor boundary only; inert held-byte provider, never native API."""
    ROOT_PINS={
        'unified_system.service_postgres':('66355ded61d9d599d98e8a229a9733b2a6863d3a2e632e633e0d48e685dfbe63',59422),
        'unified_system.runtime_process':('7cdf208ac44d45dca5c0785719b846d28a52ae7754781450547d8a8ef81da7b2',15974),
        'unified_system.service_bootstrap':('a8012a04c4a0507a72bd6ba38c63ad0af855d5f25efea7669ea11db1386d8d45',25050)}
    def fixture(self,old_postgres=False):
        from types import ModuleType,SimpleNamespace
        modules={};seen=[];native=[]
        for name in self.ROOT_PINS:
            module=ModuleType(name);module.__file__='C:/INERT/'+name.replace('.','/')+'.py';module.__spec__=SimpleNamespace(origin=module.__file__);modules[name]=module
        class BeforeNative(Exception):pass
        def win_api():native.append('BOUNDARY_REACHED');raise BeforeNative()
        modules['unified_system.runtime_process']._win_api=win_api
        def held(path,pin,size,*args,**kwargs):
            name=next(n for n,m in modules.items() if m.__file__==path)
            actual=self.ROOT_PINS[name]
            if old_postgres and name=='unified_system.service_postgres':actual=('58dc1ca96e57003922499ee6acd2ff49a5fabd27805878473ca45577145d5756',58115)
            seen.append((name,pin,size))
            if (pin,size)!=actual:raise ValueError('PG_CUSTODY_DENIED')
            return b''
        return modules,seen,native,held,BeforeNative
    def test_single_root_supplier_set_reaches_only_inert_native_boundary(self):
        from unittest.mock import patch
        from pathlib import PureWindowsPath
        modules,seen,native,held,stop=self.fixture()
        with patch.object(pg,'_held',held),patch.object(pg,'Path',PureWindowsPath),patch.object(pg.os,'name','nt'):
            with self.assertRaises(Exception) as caught:pg.WindowsBackend(pg.Plan('C:/INERT/attempt3',native=True),modules,'C:/INERT/job.py')
        self.assertIs(type(caught.exception),stop)
        self.assertEqual([(name,pin,size) for name,(pin,size) in self.ROOT_PINS.items()],seen)
        self.assertEqual(['BOUNDARY_REACHED'],native)
    def test_old_postgres_supplier_denied_before_native_boundary(self):
        from unittest.mock import patch
        from pathlib import PureWindowsPath
        modules,seen,native,held,stop=self.fixture(old_postgres=True)
        with patch.object(pg,'_held',held),patch.object(pg,'Path',PureWindowsPath),patch.object(pg.os,'name','nt'):
            with self.assertRaises(Exception) as caught:pg.WindowsBackend(pg.Plan('C:/INERT/attempt3',native=True),modules,'C:/INERT/job.py')
        self.assertIs(type(caught.exception),ValueError);self.assertEqual(('PG_CUSTODY_DENIED',),caught.exception.args)
        self.assertEqual(['unified_system.service_postgres'],[row[0] for row in seen]);self.assertEqual([],native)