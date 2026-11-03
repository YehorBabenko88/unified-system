"""Synthetic capsule/archive and mocked CONTROL fixtures; no real enrollment."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def builder():
    spec=importlib.util.spec_from_file_location('owned_worker_builder',ROOT/'scripts/prepare_worker_capsule.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def synthetic_source(root):
    from tests.test_lab_release import fixture
    from unified_system.lab_release import canonical
    m=fixture(root)
    # Preserve an intentional Git-like empty namespace in the exact closure.
    empty=root/'sources/grid/empty';empty.mkdir();m['directories']=sorted([*m['directories'],'sources/grid/empty'])
    raw=canonical(m);(root/'lab-release.json').write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


class WorkerArchiveTests(unittest.TestCase):
    def test_exact_archive_roundtrip_keeps_empty_directories_without_payload_imports(self):
        b=builder()
        with tempfile.TemporaryDirectory(prefix='worker-builder-') as directory:
            parent=Path(directory).resolve();source=parent/'source';source.mkdir();pin=synthetic_source(source)
            archive=parent/'capsule.zip'
            # Mocked source proof is explicit: this test qualifies ZIP closure only.
            with patch.object(b,'prove_sources',return_value=None):receipt=b.export_archive(source,archive,pin)
            manifest=b.check_archive(archive,receipt['archive_sha256'],pin)
            self.assertIn('sources/grid/empty',manifest['directories'])
            target=parent/'expanded';target.mkdir();b.extract_verified(archive,target,manifest,pin,receipt['archive_sha256'])
            from unified_system.lab_release import verify_capsule
            self.assertEqual(verify_capsule(target,pin)['manifest'],manifest)
            self.assertEqual(list((target/'sources/grid/empty').iterdir()),[])
    def test_failed_source_proof_precedes_archive_creation(self):
        b=builder()
        with tempfile.TemporaryDirectory(prefix='worker-builder-') as directory:
            parent=Path(directory).resolve();source=parent/'source';source.mkdir();pin=synthetic_source(source);archive=parent/'capsule.zip'
            with patch.object(b,'prove_sources',side_effect=ValueError('SYNTHETIC_SOURCE_DENIED')):
                with self.assertRaises(ValueError):b.export_archive(source,archive,pin)
            self.assertFalse(archive.exists())
    def test_extra_duplicate_link_and_traversal_members_reject(self):
        b=builder()
        with tempfile.TemporaryDirectory(prefix='worker-builder-') as directory:
            parent=Path(directory).resolve();source=parent/'source';source.mkdir();pin=synthetic_source(source)
            honest=parent/'honest.zip'
            with patch.object(b,'prove_sources',return_value=None):b.export_archive(source,honest,pin)
            for index,(name,mode) in enumerate([('foreign.py',0o100600),('../escape',0o100600),('lab-release.json',0o100600),('link',0o120777)]):
                with self.subTest(name=name):
                    bad=parent/('bad'+str(index)+'.zip');bad.write_bytes(honest.read_bytes())
                    import warnings
                    with warnings.catch_warnings():
                        warnings.simplefilter('ignore',UserWarning)
                        with zipfile.ZipFile(bad,'a') as z:
                            member=zipfile.ZipInfo(name);member.create_system=3;member.external_attr=mode<<16
                            z.writestr(member,b'not executable')
                    with self.assertRaises(ValueError):b.check_archive(bad,hashlib.sha256(bad.read_bytes()).hexdigest(),pin)
            with self.assertRaises(ValueError):b.check_archive(honest,'0'*64,pin)
    def test_device_alias_paths_are_rejected_before_open_or_creation(self):
        b=builder()
        with tempfile.TemporaryDirectory(prefix='worker-builder-') as directory:
            root=Path(directory).resolve()
            for name in ('NUL','CON','AUX','COM1','LPT1','NUL.txt'):
                with self.subTest(name=name),self.assertRaises(ValueError):b.safe(root/name)

    def test_worker_targets_require_observed_logical_or_exact_mapped_hostname(self):
        b=builder()
        for logical,host in [('PC1','Easy'),('PC2','Leitstelle1'),('PC3','LS03e'),('PC4','LS4'),('LS7','LS-07')]:
            with patch.object(b.socket,'gethostname',return_value=host):b.check_worker_host(logical)
        for logical,host in [('PC1','LS5'),('LS5','LS5'),('ADMINIT','ADMINIT'),('PC1','arbitrary')]:
            with self.subTest(logical=logical,host=host),patch.object(b.socket,'gethostname',return_value=host):
                with self.assertRaises(ValueError):b.check_worker_host(logical)
    def test_private_stdin_json_is_exact_bounded_and_never_accepts_database_credentials(self):
        b=builder();valid={'enrollment_token':'T'*43}
        self.assertEqual(b.read_private(io.BytesIO(json.dumps(valid).encode())),valid)
        for raw in [b'X'*4097,b'{"enrollment_token":"a","enrollment_token":"b"}',json.dumps({**valid,'PGPASSWORD':'forbidden'}).encode(),json.dumps({**valid,'grid_shared_token':'a'*64}).encode()]:
            with self.assertRaises(ValueError):b.read_private(io.BytesIO(raw))


class MockedControlTests(unittest.TestCase):
    """Loopback HTTP is a labeled mock, never an actual CONTROL receipt."""
    def exchange(self,response,*,drip=False):
        b=builder();listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);port=listener.getsockname()[1];received=[]
        def server():
            try:
                connection,_=listener.accept()
                with connection:
                    received.append(connection.recv(4096))
                    if drip:
                        for byte in response:
                            try:connection.sendall(bytes([byte]));time.sleep(.02)
                            except OSError:break
                    else:connection.sendall(response)
            finally:listener.close()
        task=threading.Thread(target=server,daemon=True);task.start()
        began=time.monotonic()
        try:return b.enroll(port,'PC1','T'*43,timeout=.25 if drip else 2),received
        finally:task.join(2);self.assertLess(time.monotonic()-began,3)
    def test_accepts_exact_pilot_enrollment_and_sends_only_enrollment_payload(self):
        raw=json.dumps(dict(node_id='PC1',credential='C'*64,install_mode='PILOT')).encode()
        response=b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: '+str(len(raw)).encode()+b'\r\n\r\n'+raw
        result,requests=self.exchange(response)
        self.assertEqual(result,'C'*64);self.assertIn(b'POST /enroll HTTP/1.1',requests[0]);self.assertNotIn(b'grid_shared_token',requests[0])
    def test_redirect_wrong_role_duplicate_lengths_and_oversized_response_reject(self):
        for header,body in [(b'HTTP/1.1 302 Found\r\nContent-Length: 0',b''),(b'HTTP/1.1 200 OK\r\nContent-Length: 5000',b''),(b'HTTP/1.1 200 OK\r\nContent-Length: 0\r\nContent-Length: 0',b'')]:
            with self.assertRaises(ValueError):self.exchange(header+b'\r\n\r\n'+body)
        raw=json.dumps(dict(node_id='PC1',credential='C'*64,install_mode='NORMAL')).encode()
        with self.assertRaises(ValueError):self.exchange(b'HTTP/1.1 200 OK\r\nContent-Length: '+str(len(raw)).encode()+b'\r\n\r\n'+raw)
    def test_absolute_deadline_rejects_dripping_response(self):
        with self.assertRaises(ValueError):self.exchange(b'HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n',drip=True)

class WorkerTransformTests(unittest.TestCase):
    def test_rebases_all_program_paths_and_removes_control_database_role(self):
        b=builder()
        with tempfile.TemporaryDirectory(prefix='worker-builder-') as directory:
            parent=Path(directory).resolve();old=parent/'old';state=parent/'old-state';target=parent/'new';newstate=parent/'new-state'
            ports=dict(zip(sorted(b.MODULES),range(26000,26006)))
            config={'node_id':'LS5','state_root':str(state),'snapshot_path':str(state/'public/runtime.json'),'programs':{}}
            for name in b.MODULES-{'unified-system'}:
                args=[str(old/'python.exe'),'-I','-S','-B',str(old/'sources/unified-system/unified_system/owned_python.py'),'--source-root',str(old/'sources'/name)]
                if name=='grid':args+=['--dependency-root',str(old/'sources/grid')]
                args+=['--module','uvicorn' if name=='grid' else 'example','--','--port','20000']
                config['programs'][name]={'argv':args,'cwd':str(old/'sources'/name),'health_url':'http://127.0.0.1:20000/internal/v2/module/health','env':{'UNIFIED_SOURCE_ROOT':str(old/'sources/unified-system')}}
            config['programs']['grid']['env']['POSTGRES_DSN']='postgresql://unified_lab_old@127.0.0.1:55459/unified_lab_old'
            result=b.worker_config(config,node_id='PC1',old_root=old,new_root=target,new_state=newstate,ports=ports,coordinator_port=29000,auth_path=newstate/'private/grid-auth.json',auth_sha256='a'*64)
            env=result['programs']['grid']['env'];self.assertEqual(env['ROLE'],'worker');self.assertNotIn('POSTGRES_DSN',env);self.assertNotIn('PGPASSWORD',env)
            self.assertIn('grid.owned_worker_service',result['programs']['grid']['argv']);self.assertNotIn(str(old),json.dumps(result))
            self.assertIn('POSTGRES_DSN',config['programs']['grid']['env'])
            config['programs']['math']['env']['POSTGRES_DSN']='postgresql://unexpected'
            with self.assertRaises(ValueError):b.worker_config(config,node_id='PC1',old_root=old,new_root=target,new_state=newstate,ports=ports,coordinator_port=29000,auth_path=newstate/'private/grid-auth.json',auth_sha256='a'*64)

    def test_invalid_archive_precedes_code_state_creation_and_private_stdin(self):
        b=builder()
        with tempfile.TemporaryDirectory(prefix='worker-builder-') as directory:
            parent=Path(directory).resolve();archive=parent/'bad.zip';archive.write_bytes(b'not a capsule');target=parent/'code';state=parent/'state'
            class PrivateNeverRead:
                def read(self,*args):raise AssertionError('secret read before admission')
            with patch.object(b.socket,'gethostname',return_value='Easy'):
                with self.assertRaises(ValueError):b.prepare_worker(archive,'0'*64,'a'*64,target,state,'PC1',dict(zip(sorted(b.MODULES),range(26000,26006))),29000,PrivateNeverRead())
            self.assertFalse(target.exists());self.assertFalse(state.exists())

class OperatorClosureTests(unittest.TestCase):
    def test_raw_operator_sources_ignore_poisoned_bytecode_and_changed_helper_rejects(self):
        import py_compile
        import subprocess
        import shutil
        with tempfile.TemporaryDirectory(prefix='worker-builder-') as directory:
            parent=Path(directory).resolve();operator=parent/'operator';operator.mkdir();files={}
            paths=[*ROOT.joinpath('unified_system').rglob('*.py'),ROOT/'integration/source_guard.py',ROOT/'scripts/prepare_worker_capsule.py']
            for source in paths:
                relative=source.relative_to(ROOT).as_posix();dest=operator/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
                files[relative]=hashlib.sha256(dest.read_bytes()).hexdigest()
            lock=parent/'operator-lock.json';lock.write_text(json.dumps(dict(schema='unified.worker-operator.v1',files=files,source_manifest_sha256s=['a'*64])))
            pin=hashlib.sha256(lock.read_bytes()).hexdigest()
            honest=operator/'unified_system/__init__.py';poison=parent/'poison.py';raw=b'raise RuntimeError("POISON_BYTECODE_EXECUTED")\n'
            self.assertLessEqual(len(raw),honest.stat().st_size);poison.write_bytes(raw.ljust(honest.stat().st_size,b' '))
            os.utime(poison,ns=(honest.stat().st_atime_ns,honest.stat().st_mtime_ns))
            cache=Path(importlib.util.cache_from_source(str(honest)));cache.parent.mkdir();py_compile.compile(str(poison),cfile=str(cache),dfile=str(honest),doraise=True)
            command='''import sys,runpy,pathlib
root=pathlib.Path(sys.argv[1]);ns=runpy.run_path(str(root/'scripts/prepare_worker_capsule.py'),run_name='owned_operator_test')
try:
 allowed=ns['admit_operator'](root,pathlib.Path(sys.argv[2]),sys.argv[3])
 assert allowed==frozenset({'a'*64})
 import unified_system.lab_release,unified_system.lab_runtime,unified_system.lab_capsule_acl,integration.source_guard
 print('SOURCE_ONLY_OPERATOR_OK')
except ValueError:
 print('PIN_DENIED');raise SystemExit(7)
'''
            args=[sys.executable,'-I','-S','-B','-c',command,str(operator),str(lock),pin]
            result=subprocess.run(args,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stdout.strip(),'SOURCE_ONLY_OPERATOR_OK')
            valid_policy=json.loads(lock.read_text())
            for pins in ([],['a'*64,'a'*64],['b'*64,'a'*64],['A'*64],['a'*63],['a'*64]*17):
                policy={**valid_policy,'source_manifest_sha256s':pins};lock.write_text(json.dumps(policy))
                bad_pin=hashlib.sha256(lock.read_bytes()).hexdigest()
                result=subprocess.run([*args[:-1],bad_pin],capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,7,result.stderr);self.assertEqual(result.stdout.strip(),'PIN_DENIED')
            for alias in ('unified_system//__init__.py','unified_system/../__init__.py','unified_system/__INIT__.py'):
                policy={**valid_policy,'files':{**files,alias:files['unified_system/__init__.py']}};lock.write_text(json.dumps(policy))
                bad_pin=hashlib.sha256(lock.read_bytes()).hexdigest()
                result=subprocess.run([*args[:-1],bad_pin],capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,7,result.stderr)
            lock.write_text(json.dumps(valid_policy));pin=hashlib.sha256(lock.read_bytes()).hexdigest();args[-1]=pin
            honest.write_bytes(b'raise RuntimeError("UNPINNED_SOURCE_EXECUTED")\n')
            result=subprocess.run(args,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,7,result.stderr);self.assertEqual(result.stdout.strip(),'PIN_DENIED')


@unittest.skipUnless(os.name=='nt','Native Windows worker ACL pipeline')
class NativeMockedWorkerPipelineTests(unittest.TestCase):
    def test_mocked_control_worker_capsule_is_rebased_private_and_sealed(self):
        """Synthetic sources plus mock CONTROL; proves staging only, no readiness."""
        from unified_system import lab_release,lab_runtime
        from tests.test_lab_release import fixture
        from tests.test_lab_capsule_acl import ps
        spec=importlib.util.spec_from_file_location('owned_control_fixture_builder',ROOT/'scripts/prepare_lab_capsule.py')
        control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
        b=builder()
        with tempfile.TemporaryDirectory(prefix='worker-builder-') as directory:
            parent=Path(directory).resolve();source=parent/'source';source.mkdir();m=fixture(source)
            for name,raw in [('sources/unified-system/unified_system/owned_python.py',b'# Synthetic; never executed\n'),('sources/math/src/math-engine-server.mjs',b'// Synthetic; never executed\n')]:
                p=source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);m['files'][name]=dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
            for name in m['sources']:m['sources'][name]['dependencies']={d:'1.0.0' for d in control.GRAPH[name]}
            snapshots={name:{'runtime_files':{'inert.txt':{'raw_sha256':m['files']['sources/'+name+'/inert.txt']['sha256']}}} for name in m['sources']}
            tool=source/'tools/git.exe';config=control.runtime_config(source,parent/'source-state',m['sources'],snapshots,tool,tool,tool,'lab-1',(parent/'source-state/private/grid-auth.json','a'*64),55459)
            raw=lab_release.canonical(config);(source/'runtime.json').write_bytes(raw);m['files']['runtime.json']=dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
            m['directories']=sorted(p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_dir())
            raw=lab_release.canonical(m);(source/'lab-release.json').write_bytes(raw);pin=hashlib.sha256(raw).hexdigest();archive=parent/'source.zip'
            with patch.object(b,'prove_sources',return_value=None):export=b.export_archive(source,archive,pin)
            target=parent/'code';state=parent/'state';ports=dict(zip(sorted(b.MODULES),range(26000,26006)))
            with patch.object(b.socket,'gethostname',return_value='Easy'),patch.object(b,'prove_sources',return_value=None),patch.object(b,'enroll',return_value='C'*64) as forbidden:
                with self.assertRaises(ValueError):b.prepare_worker(archive,export['archive_sha256'],pin,parent/'rejected-code',parent/'rejected-state','PC1',ports,29000,io.BytesIO(json.dumps(dict(enrollment_token='T'*43,grid_shared_token='a'*64)).encode()))
                forbidden.assert_not_called()

            listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);port=listener.getsockname()[1]
            while port in ports.values():ports={k:v+10 for k,v in ports.items()}
            def mock_control():
                try:
                    connection,_=listener.accept()
                    with connection:
                        connection.recv(4096)
                        body=json.dumps(dict(node_id='PC1',credential='C'*64,install_mode='PILOT')).encode()
                        connection.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: '+str(len(body)).encode()+b'\r\n\r\n'+body)
                finally:listener.close()
            task=threading.Thread(target=mock_control,daemon=True);task.start()
            try:
                with patch.object(b.socket,'gethostname',return_value='Easy'),patch.object(b,'prove_sources',return_value=None):
                    result=b.prepare_worker(archive,export['archive_sha256'],pin,target,state,'PC1',ports,port,io.BytesIO(json.dumps(dict(enrollment_token='T'*43)).encode()))
                final=lab_release.verify_capsule(target,result['manifest_sha256'])['manifest']
                public=json.loads((target/'runtime.json').read_bytes());lab_runtime.validate_config(public,final,target,hostname='PC1')
                self.assertEqual(final['sources'],m['sources']);self.assertEqual(final['directories'],m['directories'])
                auth=json.loads((state/'private/grid-auth.json').read_bytes());self.assertEqual(auth['role'],'WORKER');self.assertEqual(auth['schema'],'unified.lab.grid-auth.v3');self.assertIsNone(auth['postgres_password']);self.assertIsNone(auth['grid_shared_token'])
                self.assertEqual(auth['node_credential'],'C'*64);self.assertNotIn('POSTGRES_DSN',public['programs']['grid']['env']);self.assertNotIn('GRID_SHARED_TOKEN',public['programs']['grid']['env']);self.assertNotIn('PGPASSWORD',public['programs']['grid']['env'])
                self.assertNotIn('enrollment_token',(state/'private/grid-auth.json').read_text())
                with self.assertRaises(PermissionError):(target/'accidental.pyc').write_bytes(b'blocked')
                (state/'own.log').write_text('writable');self.assertEqual(result['runtime_readiness'],'NOT_TESTED')
            finally:
                listener.close();task.join(2)
                if target.exists():
                    # Only this test's own fresh absolute code root is unsealed.
                    self.assertEqual(target.parent,parent);self.assertTrue(parent.name.startswith('worker-builder-'))
                    self.assertEqual(target.resolve(),target);self.assertFalse(target.is_symlink())
                    literal="'"+str(target).replace("'","''")+"'"
                    cleanup=ps("$ErrorActionPreference='Stop';$p="+literal+";$a=Get-Acl -LiteralPath $p;$a.SetAccessRuleProtection($true,$false);foreach($r in @($a.GetAccessRules($true,$false,[Security.Principal.SecurityIdentifier]))){$a.RemoveAccessRuleSpecific($r)};$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User;$a.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($sid,'FullControl','ContainerInherit,ObjectInherit','None','Allow'));(Get-Item -LiteralPath $p).SetAccessControl($a)")
                    self.assertEqual(cleanup.returncode,0,cleanup.stderr)


class ExternalSourcePolicyTests(unittest.TestCase):
    def test_only_admitted_operator_policy_source_pins_reach_prepare(self):
        b=builder()
        with tempfile.TemporaryDirectory(prefix='worker-builder-') as directory:
            parent=Path(directory).resolve()
            common=['--operator-root',str(parent),'--operator-lock',str(parent/'lock.json'),'--operator-lock-sha256','f'*64,
                'prepare','--archive',str(parent/'source.zip'),'--archive-sha256','c'*64,'--target',str(parent/'code'),
                '--state',str(parent/'state'),'--node','PC1','--ports-json','{}','--coordinator-port','29000','--enroll']
            for pin,expected in [('b'*64,False),('a'*64,True)]:
                with patch.object(b,'admit_operator',return_value=frozenset({'a'*64})),patch.object(b,'prepare_worker',return_value={'scope':'MOCK_ROUTING_ONLY'}) as prepare,patch.object(b.sys,'stdout',io.StringIO()):
                    result=b.main([*common,'--source-manifest-sha256',pin])
                    self.assertEqual(result,0 if expected else 1);self.assertEqual(prepare.called,expected)
            self.assertFalse((parent/'code').exists());self.assertFalse((parent/'state').exists())
