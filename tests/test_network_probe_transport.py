"""Modeled transport/lifecycle controls; never an SSH or office qualification."""
import json
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import base64
import gzip
import re
import hashlib
import io
import subprocess

from unified_system.network_probe_transport import (
    ProbeJournal, ProbeTransportBlocked,
)


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'private-owned-leaf'
        self.root.mkdir()
        self.admitted = True
        self.admit = lambda root: self.admitted and root == self.root
        self.journal = ProbeJournal.create(self.root, 'installation-1', admit=self.admit)

    def test_unfinished_operation_blocks_after_reopen_without_elapsed_release(self):
        self.journal.begin('LS7', 'a'*32, 'b'*64)
        reopened = ProbeJournal.open(self.root, 'installation-1', admit=self.admit)
        self.assertEqual(reopened.state('LS7')['status'], 'IN_FLIGHT')
        with self.assertRaisesRegex(ProbeTransportBlocked, 'PROBE_OPERATION_UNRESOLVED'):
            reopened.begin('LS7', 'c'*32, 'd'*64)

    def test_uncertain_cleanup_remains_blocked_across_instances(self):
        self.journal.begin('PC1', 'a'*32, 'b'*64)
        self.journal.finish('PC1', 'a'*32, {'reason':'NO_OWNER_HEADER'}, exit_confirmed=False)
        reopened = ProbeJournal.open(self.root, 'installation-1', admit=self.admit)
        self.assertEqual(reopened.state('PC1')['status'], 'UNCERTAIN')
        with self.assertRaises(ProbeTransportBlocked):
            reopened.begin('PC1', 'c'*32, 'd'*64)

    def test_only_literal_confirmed_exit_releases_the_same_operation(self):
        self.journal.begin('PC2', 'a'*32, 'b'*64)
        with self.assertRaisesRegex(ProbeTransportBlocked, 'PROBE_OPERATION_MISMATCH'):
            self.journal.finish('PC2', 'c'*32, {}, exit_confirmed=True)
        self.assertEqual(self.journal.state('PC2')['status'], 'IN_FLIGHT')
        self.journal.finish('PC2', 'a'*32, {}, exit_confirmed=1)
        self.assertEqual(self.journal.state('PC2')['status'], 'UNCERTAIN')

    def test_confirmed_prior_operation_allows_fresh_nonce_and_generation(self):
        self.journal.begin('PC3', 'a'*32, 'b'*64)
        self.journal.finish('PC3', 'a'*32, {'reason':'CLEAN_EXIT'}, exit_confirmed=True)
        self.journal.begin('PC3', 'c'*32, 'd'*64)
        state = self.journal.state('PC3')
        self.assertEqual((state['generation'], state['nonce'], state['status']), (2,'c'*32,'IN_FLIGHT'))

    def test_repeated_nonce_unknown_host_or_revoked_state_admission_never_mutates(self):
        self.journal.begin('PC4', 'a'*32, 'b'*64)
        self.journal.finish('PC4', 'a'*32, {}, exit_confirmed=True)
        for host, nonce in [('ADMINIT','c'*32), ('pc1','c'*32), ('PC1;whoami','c'*32), ('PC1','a'*32)]:
            with self.subTest(host=host,nonce=nonce), self.assertRaises(ProbeTransportBlocked):
                self.journal.begin(host, nonce, 'd'*64)
        self.admitted = False
        with self.assertRaises(ProbeTransportBlocked):
            self.journal.begin('PC1', 'c'*32, 'd'*64)
        self.admitted = True
        self.assertEqual(self.journal.state('PC1')['generation'], 0)

    def test_nonempty_foreign_leaf_and_wrong_installation_are_never_adopted(self):
        other = Path(self.temp.name)/'foreign'
        other.mkdir(); (other/'keep').write_bytes(b'unchanged')
        with self.assertRaises(ProbeTransportBlocked):
            ProbeJournal.create(other, 'installation-1', admit=lambda root: True)
        self.assertEqual((other/'keep').read_bytes(), b'unchanged')
        with self.assertRaises(ProbeTransportBlocked):
            ProbeJournal.open(self.root, 'other-installation', admit=self.admit)

    def test_changed_db_identity_unknown_schema_or_journal_sidecar_blocks(self):
        db = self.root/'probe-latch.sqlite'
        foreign = self.root/'probe-latch.sqlite-wal'
        foreign.write_bytes(b'not an owned WAL')
        with self.assertRaises(ProbeTransportBlocked): self.journal.state('PC1')
        foreign.unlink()  # Delete only this test's explicit inert fixture.
        with closing(sqlite3.connect(db)) as con:
            con.execute('CREATE TABLE unknown_fixture(value)');con.commit()
        with self.assertRaises(ProbeTransportBlocked): self.journal.state('PC1')

    def test_hardlinked_database_is_rejected_without_writing_target(self):
        db = self.root/'probe-latch.sqlite'
        alias = Path(self.temp.name)/'alias.sqlite'
        os.link(db, alias)
        before = alias.read_bytes()
        with self.assertRaises(ProbeTransportBlocked): self.journal.state('PC1')
        self.assertEqual(alias.read_bytes(), before)

    def test_bounded_receipt_and_foreign_json_do_not_release_intent(self):
        self.journal.begin('LS5', 'a'*32, 'b'*64)
        with self.assertRaises(ProbeTransportBlocked):
            self.journal.finish('LS5', 'a'*32, {'oversized':'x'*20000}, exit_confirmed=True)
        self.assertEqual(self.journal.state('LS5')['status'], 'IN_FLIGHT')

    def test_capacity_reserves_terminal_evidence_before_any_other_launch(self):
        with patch('unified_system.network_probe_transport.MAX_EVENTS',4):
            self.journal.begin('PC1','a'*32,'b'*64)
            self.journal.begin('PC2','c'*32,'d'*64)
            with self.assertRaisesRegex(ProbeTransportBlocked,'PROBE_EVIDENCE_CAPACITY'):
                self.journal.begin('PC3','e'*32,'f'*64)
            self.journal.finish('PC1','a'*32,{},exit_confirmed=True)
            self.journal.finish('PC2','c'*32,{},exit_confirmed=True)

    def test_second_instance_cannot_start_from_a_stale_complete_snapshot(self):
        other=ProbeJournal.open(self.root,'installation-1',admit=self.admit)
        self.journal.begin('PC1','a'*32,'b'*64)
        with self.assertRaisesRegex(ProbeTransportBlocked,'PROBE_OPERATION_UNRESOLVED'):
            other.begin('PC1','c'*32,'d'*64)

    def test_replaced_database_identity_is_not_accepted_even_with_identical_bytes(self):
        db=self.root/'probe-latch.sqlite';raw=db.read_bytes()
        db.rename(self.root/'preserved-original.sqlite')
        db.write_bytes(raw)
        with self.assertRaises(ProbeTransportBlocked):self.journal.state('PC1')

    def test_interrupted_creation_is_left_blocked_without_namespace_deletion(self):
        leaf=Path(self.temp.name)/'interrupted';leaf.mkdir();calls=[]
        def admit(path):calls.append(path);return len(calls)==1
        with self.assertRaises(ProbeTransportBlocked):ProbeJournal.create(leaf,'installation-1',admit=admit)
        self.assertEqual((leaf/'probe-owner.json').read_bytes(),b'{"creating":true}')
        with self.assertRaises(ProbeTransportBlocked):ProbeJournal.open(leaf,'installation-1',admit=lambda root:True)
        with self.assertRaises(ProbeTransportBlocked):ProbeJournal.create(leaf,'installation-1',admit=lambda root:True)


def owner(node,nonce):
    return dict(schema='unified.network-probe-owner.v1',computer=node,nonce=nonce,
        pid=11756,ppid=12048,parent_ppid=10952,created_utc='2026-11-05T15:21:58.6983010Z',
        parent_created_utc='2026-11-05T15:21:58.6622960Z')


class FakeRunner:
    """Modeled authenticated-SSH result; never authenticates a real host."""
    def __init__(self,*,mode='normal'):
        self.calls=[];self.mode=mode
    def run(self,argv,**kwargs):
        from unified_system.network_probe_transport import RunResult
        self.calls.append((argv,kwargs))
        encoded=re.search(r'-EncodedCommand ([A-Za-z0-9+/=]+)',argv[-1])[1]
        script=base64.b64decode(encoded).decode('utf-16le')
        nonce=re.search(r"\$n='([a-f0-9]{32})'",script)[1]
        node=next(value for value in argv if value.startswith('HostKeyAlias=unified-lan-')).split('unified-lan-',1)[1].upper()
        if 'UNIFIED_NP_' in argv[-1]:
            self.header=owner(node,nonce)
            if self.mode=='bad_nonce':self.header['nonce']='0'*32
            if self.mode=='bad_pid':self.header['pid']=True
            if self.mode=='missing_header':return RunResult(0,b'{}\n',b'',False,False,True,True,True,True)
            header=b'UNIFIED_PROBE_OWNER '+json.dumps(self.header).encode()+b'\n'
            if self.mode=='timeout':return RunResult(None,header,b'',True,False,True,True,True,True)
            observation=dict(schema='unified.network-readonly-observation.v1',computer=node,mutations=False,scope='SYNTHETIC_TEST_ONLY')
            if self.mode=='bad_result':observation['computer']='WRONG_HOST'
            result=b'UNIFIED_PROBE_RESULT '+nonce.encode()+b' '+json.dumps(observation).encode()+b'\n'
            return RunResult(0,header+result,b'',False,self.mode=='overflow',self.mode!='local_uncertain',self.mode!='overflow',True,True)
        response=dict(schema='unified.network-probe-cleanup.v1',computer=node,nonce=nonce,
            pid=self.header['pid'],created_utc=self.header['created_utc'],
            owner_exit_confirmed=True,parent_exit_confirmed=True,stop_attempted=False)
        if self.mode=='cleanup_mismatch':response['nonce']='0'*32
        if self.mode=='cleanup_unknown':response['owner_exit_confirmed']=False
        if self.mode=='cleanup_timeout':return RunResult(None,b'',b'',True,False,True,True,True,True)
        return RunResult(0,json.dumps(response).encode()+b'\n',b'',False,False,True,True,True,True)


class TransportTests(unittest.TestCase):
    def setUp(self):
        JournalTests.setUp(self)
        from tests.test_lan_probe_inventory import InventoryFixture
        from unified_system.lan_probe_inventory import LanProbeInventory,_QUARANTINED
        self.lan_fixture=InventoryFixture(Path(self.temp.name)/'private ssh assets')
        self.inventory=LanProbeInventory(self.lan_fixture)
        def release_only_modeled_handles():
            # These tests create NO real SSH process; release only this exact
            # fixture's quarantined read handles before its tempdir cleanup.
            for key,lease in list(_QUARANTINED.items()):
                if lease.owner is self.inventory:lease.stack.close();del _QUARANTINED[key]
        self.addCleanup(release_only_modeled_handles)
    def transport(self,runner):
        from unified_system.network_probe_transport import NetworkProbeTransport
        return NetworkProbeTransport(self.journal,inventory=self.inventory,require_current=lambda:True,runner=runner)

    def test_success_requires_second_channel_exit_evidence(self):
        runner=FakeRunner();result=self.transport(runner).observe('PC1')
        self.assertEqual(result['scope'],'SYNTHETIC_TEST_ONLY')
        self.assertEqual(len(runner.calls),2)
        self.assertEqual(self.journal.state('PC1')['status'],'COMPLETE')
        for argv,kwargs in runner.calls:
            self.assertLessEqual(len(argv[-1]),7000)
            self.assertIn('StrictHostKeyChecking=yes',argv)
            self.assertIn('BatchMode=yes',argv)
            self.assertEqual(kwargs['stdin_mode'],'DEVNULL')

    def test_remote_hosts_closed_before_latch_or_runner(self):
        runner=FakeRunner();transport=self.transport(runner)
        for node in ('ADMINIT','AMINIT','ls7','LS5','PC1 & whoami','PC1.example.invalid'):
            with self.subTest(node=node),self.assertRaises(ProbeTransportBlocked):transport.observe(node)
        self.assertEqual(runner.calls,[])
        self.assertEqual(self.journal.state('PC1')['generation'],0)

    def test_no_header_malformed_nonce_or_bool_pid_is_sticky_uncertain(self):
        from unified_system.network_probe_transport import NetworkProbeTransport
        for index,mode in enumerate(('missing_header','bad_nonce','bad_pid')):
            node=('PC1','PC2','PC3')[index];runner=FakeRunner(mode=mode)
            with self.subTest(mode=mode),self.assertRaises(ProbeTransportBlocked):self.transport(runner).observe(node)
            self.assertEqual(len(runner.calls),1)
            self.assertEqual(self.journal.state(node)['status'],'UNCERTAIN')
            reopened=ProbeJournal.open(self.root,'installation-1',admit=self.admit)
            with self.assertRaises(ProbeTransportBlocked):NetworkProbeTransport(reopened,inventory=self.inventory,require_current=lambda:True,runner=runner).observe(node)
            self.assertEqual(len(runner.calls),1)

    def test_timeout_with_owner_header_runs_only_exact_cleanup_then_reports_failure(self):
        runner=FakeRunner(mode='timeout')
        with self.assertRaisesRegex(ProbeTransportBlocked,'PROBE_DEADLINE'):self.transport(runner).observe('LS7')
        self.assertEqual(len(runner.calls),2)
        self.assertEqual(self.journal.state('LS7')['status'],'COMPLETE')
        encoded=re.search(r'-EncodedCommand ([A-Za-z0-9+/=]+)',runner.calls[1][0][-1])[1]
        script=base64.b64decode(encoded).decode('utf-16le')
        self.assertIn('Stop-Process -InputObject',script)
        for forbidden in ('Stop-Service','Restart-Service','taskkill','/T','Stop-Process -Id'):
            self.assertNotIn(forbidden,script)

    def test_wrong_cleanup_response_unknown_owner_or_local_drain_is_never_complete(self):
        for node,mode in zip(('PC1','PC2','PC3'),('cleanup_mismatch','cleanup_unknown','local_uncertain')):
            with self.subTest(mode=mode),self.assertRaises(ProbeTransportBlocked):self.transport(FakeRunner(mode=mode)).observe(node)
            self.assertEqual(self.journal.state(node)['status'],'UNCERTAIN')

    def test_full_source_admission_must_be_literal_true_before_effect(self):
        from unified_system.network_probe_transport import NetworkProbeTransport
        runner=FakeRunner()
        with self.assertRaises(ProbeTransportBlocked):NetworkProbeTransport(self.journal,inventory=self.inventory,require_current=lambda:1,runner=runner).observe('PC1')
        self.assertEqual(runner.calls,[])
        self.assertEqual(self.journal.state('PC1')['generation'],0)

    def test_revocation_after_durable_intent_still_precedes_any_ssh_effect(self):
        from unified_system.network_probe_transport import NetworkProbeTransport
        current=[True];original=self.journal.begin
        def begin(*args):
            result=original(*args);current[0]=False;return result
        runner=FakeRunner()
        with patch.object(self.journal,'begin',side_effect=begin):
            with self.assertRaisesRegex(ProbeTransportBlocked,'PROBE_SOURCE_ADMISSION_REVOKED'):
                NetworkProbeTransport(self.journal,inventory=self.inventory,require_current=lambda:current[0],runner=runner).observe('PC1')
        self.assertEqual(runner.calls,[])
        self.assertEqual(self.journal.state('PC1')['status'],'COMPLETE')

    def test_revocation_during_probe_still_cleans_but_never_publishes(self):
        from unified_system.network_probe_transport import NetworkProbeTransport
        live=[True]
        class RevokingRunner(FakeRunner):
            def run(self,*args,**kwargs):
                result=super().run(*args,**kwargs)
                if len(self.calls)==1:live[0]=False
                return result
        runner=RevokingRunner()
        with self.assertRaisesRegex(ProbeTransportBlocked,'PROBE_SOURCE_ADMISSION_REVOKED'):
            NetworkProbeTransport(self.journal,inventory=self.inventory,require_current=lambda:live[0],runner=runner).observe('PC1')
        self.assertEqual(len(runner.calls),2)
        self.assertEqual(self.journal.state('PC1')['status'],'COMPLETE')

    def test_inventory_revocation_during_probe_uses_only_held_original_cleanup(self):
        fixture=self.lan_fixture
        class RevokingInventoryRunner(FakeRunner):
            def run(self,*args,**kwargs):
                result=super().run(*args,**kwargs)
                if len(self.calls)==1:fixture.live=False
                return result
        runner=RevokingInventoryRunner()
        with self.assertRaisesRegex(ProbeTransportBlocked,'LAN_OWNER_ADMISSION_REVOKED'):
            self.transport(runner).observe('PC1')
        self.assertEqual(len(runner.calls),2)
        self.assertEqual(runner.calls[0][0][:-1],runner.calls[1][0][:-1])
        self.assertEqual(self.journal.state('PC1')['status'],'COMPLETE')

    def test_last_publication_check_after_durable_completion_rejects_revocation(self):
        from unified_system.network_probe_transport import NetworkProbeTransport
        live=[True];original=self.journal.finish
        def finish(*args,**kwargs):
            result=original(*args,**kwargs);live[0]=False;return result
        runner=FakeRunner()
        with patch.object(self.journal,'finish',side_effect=finish):
            with self.assertRaisesRegex(ProbeTransportBlocked,'PROBE_SOURCE_ADMISSION_REVOKED'):
                NetworkProbeTransport(self.journal,inventory=self.inventory,require_current=lambda:live[0],runner=runner).observe('PC1')
        self.assertEqual(len(runner.calls),2)
        self.assertEqual(self.journal.state('PC1')['status'],'COMPLETE')

    def test_source_revoked_by_last_endpoint_check_precedes_runner_spawn(self):
        from unified_system.network_probe_transport import NetworkProbeTransport
        live=[True];original=self.lan_fixture.admit_lan_endpoint
        def admit(node,descriptor):
            granted=original(node,descriptor)
            if self.journal.state(node)['status']=='IN_FLIGHT':live[0]=False
            return granted
        runner=FakeRunner()
        with patch.object(self.lan_fixture,'admit_lan_endpoint',side_effect=admit):
            with self.assertRaisesRegex(ProbeTransportBlocked,'PROBE_SOURCE_ADMISSION_REVOKED'):
                NetworkProbeTransport(self.journal,inventory=self.inventory,require_current=lambda:live[0],runner=runner).observe('PC1')
        self.assertEqual(runner.calls,[])
        self.assertEqual(self.journal.state('PC1')['status'],'COMPLETE')

    def test_cleanup_ssh_timeout_is_sticky_unknown_not_a_remote_hard_bound(self):
        runner=FakeRunner(mode='cleanup_timeout');transport=self.transport(runner)
        with self.assertRaisesRegex(ProbeTransportBlocked,'PROBE_CLEANUP_UNCERTAIN'):transport.observe('PC1')
        self.assertEqual(self.journal.state('PC1')['status'],'UNCERTAIN')
        with self.assertRaises(ProbeTransportBlocked):transport.observe('PC1')
        self.assertEqual(len(runner.calls),2)

    def test_known_header_output_overflow_is_cleaned_but_never_an_observation(self):
        runner=FakeRunner(mode='overflow')
        with self.assertRaisesRegex(ProbeTransportBlocked,'PROBE_LOCAL_DRAIN_UNCERTAIN'):self.transport(runner).observe('PC1')
        self.assertEqual(len(runner.calls),2)
        self.assertEqual(self.journal.state('PC1')['status'],'UNCERTAIN')

    def test_invalid_observation_is_not_returned_even_after_proven_cleanup(self):
        runner=FakeRunner(mode='bad_result')
        with self.assertRaisesRegex(ProbeTransportBlocked,'PROBE_FRAME_REJECTED'):
            self.transport(runner).observe('PC1')
        self.assertEqual(len(runner.calls),2)
        self.assertEqual(self.journal.state('PC1')['status'],'COMPLETE')

    def test_packed_original_source_roundtrip_and_command_bound(self):
        from unified_system.network_probe_transport import _make_recipe
        raw=(Path(__file__).resolve().parents[1]/'scripts/network_readonly_probe.ps1').read_bytes()
        recipe=_make_recipe('LS7','a'*32,raw)
        packed=re.search(r'set UNIFIED_NP_[a-f0-9]{32}=([A-Za-z0-9+/=]+)&',recipe.command)[1]
        payload=gzip.decompress(base64.b64decode(packed))
        self.assertEqual(payload[recipe.source_offset:recipe.source_offset+recipe.source_length],raw)
        self.assertEqual(hashlib.sha256(payload).hexdigest(),recipe.payload_sha256)
        self.assertLessEqual(len(recipe.command),7000)
        self.assertEqual(recipe.source_sha256,hashlib.sha256(raw).hexdigest())
        self.assertNotIn('[Console]::In',recipe.command)
        with self.assertRaisesRegex(ProbeTransportBlocked,'PROBE_COMMAND_BOUNDS'):
            _make_recipe('LS7','a'*32,base64.b64encode(os.urandom(10000)))


class RunnerTests(unittest.TestCase):
    def fake(self,stdout=b'',running=False):
        class Process:
            def __init__(self):
                self.stdout=io.BytesIO(stdout);self.stderr=io.BytesIO(b'')
                self.returncode=None if running else 0;self.killed=False
            def poll(self):return self.returncode
            def kill(self):self.killed=True;self.returncode=-1
            def wait(self,timeout=None):return self.returncode
        return Process()

    def invoke(self,process,clock=None):
        from unified_system.network_probe_transport import _BoundedRunner
        env=dict(SYSTEMROOT=r'C:\Windows',PROGRAMDATA=r'C:\ProgramData',USERPROFILE=r'C:\Users\Fixture',PATH=r'C:\Windows\System32',BYBIT_API_SECRET='MUST_NOT_FORWARD')
        with patch('unified_system.network_probe_transport.os.name','nt'),patch.dict(os.environ,env),patch('unified_system.network_probe_transport.subprocess.CREATE_NO_WINDOW',0x08000000,create=True),patch('unified_system.network_probe_transport.subprocess.Popen',return_value=process) as spawn:
            if clock:
                with patch('unified_system.network_probe_transport.time.monotonic',side_effect=clock):
                    result=_BoundedRunner().run(['INERT_MODELED_ARGV'],timeout=65,stdout_limit=32,stderr_limit=32,stdin_mode='DEVNULL')
            else:result=_BoundedRunner().run(['INERT_MODELED_ARGV'],timeout=65,stdout_limit=32,stderr_limit=32,stdin_mode='DEVNULL')
            self.assertEqual(spawn.call_args.kwargs['stdin'],subprocess.DEVNULL)
            self.assertNotIn('BYBIT_API_SECRET',spawn.call_args.kwargs['env'])
        return result

    def test_output_overflow_is_bounded_but_retains_header_prefix_for_cleanup(self):
        result=self.invoke(self.fake(b'A'*10000))
        self.assertIs(result.output_limit,True)
        self.assertEqual(result.stdout,b'A'*32)
        self.assertIs(result.local_exit_confirmed,False)
        self.assertIs(result.local_process_exit_confirmed,True)
        self.assertIs(result.stdout_eof,False)
        self.assertIs(result.stderr_eof,True)

    def test_monotonic_deadline_stops_only_retained_local_ssh_process(self):
        process=self.fake(b'OWNER_PREFIX',running=True)
        result=self.invoke(process,clock=[0.,66.])
        self.assertIs(result.timed_out,True)
        self.assertIs(result.local_exit_confirmed,True)
        self.assertTrue(process.killed)
        self.assertEqual(result.stdout,b'OWNER_PREFIX')


@unittest.skipUnless(os.name=='nt','Windows default-shell inert parser model only')
class InertWindowsShellTests(unittest.TestCase):
    def test_actual_cleanup_guard_ast_rejects_each_fingerprint_counterexample(self):
        from unified_system import network_probe_transport as mod
        recipe=mod._make_recipe('LS7','a'*32,b"'INERT_NO_NETWORK'")
        command=mod._cleanup_command(recipe,owner('LS7','a'*32))
        encoded=re.search(r'-EncodedCommand ([A-Za-z0-9+/=]+)',command)[1]
        script=r'''$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';$text=[Text.Encoding]::Unicode.GetString([Convert]::FromBase64String('__ENCODED__'));$tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseInput($text,[ref]$tokens,[ref]$errors);if($errors.Count){throw 'cleanup AST invalid'};$functions=@($ast.FindAll({param($node)$node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -in @('D','M')},$true));if($functions.Count -ne 2){throw 'missing actual guards'};foreach($function in $functions){. ([scriptblock]::Create($function.Extent.Text))};$e='__EXPECTED__';$s=[Security.Cryptography.SHA256]::Create();$v=@(11756,12048,'powershell.exe','2026-11-05T15:21:58.6983010Z','C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe');$results=@{};foreach($case in @('valid','pid','ppid','name','path','created','held_start','exited','argument','multiple_arguments','missing_argument','null_cim','null_handle')){$a=[pscustomobject]@{ProcessId=11756;ParentProcessId=12048;Name='powershell.exe';ExecutablePath=$v[4];CreationDate=[DateTime]::Parse($v[3]);CommandLine='powershell.exe -EncodedCommand __OWNER_ARG__'};$b=[pscustomobject]@{StartTime=$a.CreationDate.AddTicks(2);HasExited=$false};switch($case){'pid'{$a.ProcessId=11757};'ppid'{$a.ParentProcessId=12049};'name'{$a.Name='other.exe'};'path'{$a.ExecutablePath='C:\Other\powershell.exe'};'created'{$a.CreationDate=$a.CreationDate.AddSeconds(1)};'held_start'{$b.StartTime=$b.StartTime.AddTicks(10)};'exited'{$b.HasExited=$true};'argument'{$a.CommandLine='powershell.exe -EncodedCommand QQBBAEEA'};'multiple_arguments'{$a.CommandLine+=' -EncodedCommand QQBBAEEA'};'missing_argument'{$a.CommandLine='powershell.exe'};'null_cim'{$a=$null};'null_handle'{$b=$null}};$results[$case]=[bool](M $a $b $v)};$s.Dispose();$results|ConvertTo-Json -Compress'''
        script=script.replace('__ENCODED__',encoded).replace('__EXPECTED__',recipe.encoded_sha256).replace('__OWNER_ARG__',recipe.encoded)
        result=subprocess.run([r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',mod._encoded(script)],stdin=subprocess.DEVNULL,capture_output=True,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(result.returncode,0,(len(result.stderr),hashlib.sha256(result.stderr).hexdigest()))
        values=json.loads(result.stdout)
        self.assertEqual(len(values),13)
        self.assertIs(values.pop('valid'),True)
        self.assertTrue(all(value is False for value in values.values()))

    def test_both_default_shell_styles_roundtrip_original_inert_utf8_source(self):
        from unified_system import network_probe_transport as mod
        computer=os.environ['COMPUTERNAME']
        self.assertRegex(computer,r'^[A-Za-z0-9_-]{1,80}$')
        # Replace only CIM data in the test's private recipe. No real network
        # observation or remote/helper cleanup is executed by this model.
        cim=r"function Get-CimInstance {param($ClassName,$Filter);[pscustomobject]@{ParentProcessId=12048;CreationDate=[DateTime]::Parse('2026-11-05T15:21:58Z')}};"
        observation=dict(schema='unified.network-readonly-observation.v1',computer=computer,mutations=False,scope='INERT_MODEL_ONLY',text='кириллица')
        raw=("'"+json.dumps(observation,ensure_ascii=False).replace("'","''")+"'").encode('utf-8')
        with patch.object(mod,'REMOTE_NODES',mod.REMOTE_NODES|{computer}),patch.object(mod,'_OWNER_PREFIX',cim+mod._OWNER_PREFIX):
            recipe=mod._make_recipe(computer,'a'*32,raw)
        outer_cmd=r'"C:\Windows\System32\cmd.exe" /d /v:off /s /c "'+recipe.command+'"'
        outer_ps=[r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',mod._encoded('& '+recipe.command)]
        for name,command in (('cmd-default',outer_cmd),('powershell-default',outer_ps)):
            with self.subTest(shell=name):
                result=subprocess.run(command,stdin=subprocess.DEVNULL,capture_output=True,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
                self.assertEqual(result.returncode,0,(name,len(result.stderr),hashlib.sha256(result.stderr).hexdigest()))
                lines=result.stdout.splitlines()
                self.assertEqual(len(lines),2)
                self.assertTrue(lines[0].startswith(b'UNIFIED_PROBE_OWNER '))
                self.assertEqual(json.loads(lines[1].split(b' ',2)[2]),observation)


if __name__ == '__main__': unittest.main()
