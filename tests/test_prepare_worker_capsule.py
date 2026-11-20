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
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def builder():
    spec=importlib.util.spec_from_file_location('owned_worker_builder',ROOT/'scripts/prepare_worker_capsule.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


class WorkerInspectTests(unittest.TestCase):
    def fixture(self,parent):
        root=parent/'code';root.mkdir();files={}
        for name in ('sources/unified_system/unified_system/package_preflight.py','sources/unified_system/integration/source_guard.py'):
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(name.encode())
            files[name]=dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)
        config=dict(node_id='PC1',release_id='test',programs={n:dict(env={}) for n in ('market_data','math','terminan')})
        manifest=dict(files=files,sources={'unified_system':{'root':'sources/unified_system'}})
        return root,config,{'manifest':manifest}
    def test_inspection_never_starts_process_or_creates_credentials(self):
        b=builder()
        with tempfile.TemporaryDirectory() as tmp:
            root,config,report=self.fixture(Path(tmp).resolve());before=sorted(str(p) for p in root.rglob('*'))
            with patch('unified_system.lab_runtime.prepare',return_value=(config,report)),patch.object(b,'check_worker_host'),patch('subprocess.Popen',side_effect=AssertionError('NO CHILD')):
                self.assertEqual(b.inspect_worker(root,'a'*64)['result'],'WORKER_SOURCE_VERIFIED_NOT_STARTED')
            self.assertEqual(before,sorted(str(p) for p in root.rglob('*')))
    def test_changed_bootstrap_and_secret_bearing_program_are_refused(self):
        b=builder()
        with tempfile.TemporaryDirectory() as tmp:
            root,config,report=self.fixture(Path(tmp).resolve())
            with patch('unified_system.lab_runtime.prepare',return_value=(config,report)),patch.object(b,'check_worker_host'):
                config['programs']['market_data']['env']['MARKET_DATA_DSN']='forbidden'
                with self.assertRaises(ValueError):b.inspect_worker(root,'a'*64)
                config['programs']['market_data']['env'].clear();(root/'sources/unified_system/unified_system/package_preflight.py').write_bytes(b'changed')
                with self.assertRaises(ValueError):b.inspect_worker(root,'a'*64)
    def test_retired_enrollment_and_execution_apis_are_absent(self):
        b=builder()
        for name in ('read_private','enroll','run_worker'):self.assertFalse(hasattr(b,name))
        with patch.object(b,'admit_operator',side_effect=AssertionError('NO ADMISSION')):
            with self.assertRaises(SystemExit):b.main(['--operator-root','x','--operator-lock','y','--operator-lock-sha256','a'*64,'run'])


def synthetic_source(root):
    from tests.test_lab_release import fixture
    from unified_system.lab_release import canonical
    m=fixture(root)
    # Preserve an intentional Git-like empty namespace in the exact closure.
    empty=root/'sources/market_data/empty';empty.mkdir();m['directories']=sorted([*m['directories'],'sources/market_data/empty'])
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
            self.assertIn('sources/market_data/empty',manifest['directories'])
            target=parent/'expanded';target.mkdir();b.extract_verified(archive,target,manifest,pin,receipt['archive_sha256'])
            from unified_system.lab_release import verify_capsule
            self.assertEqual(verify_capsule(target,pin)['manifest'],manifest)
            self.assertEqual(list((target/'sources/market_data/empty').iterdir()),[])
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





class WorkerTransformTests(unittest.TestCase):
    def context(self):
        from tests.test_runtime_profile import RuntimeProfileTests
        case=RuntimeProfileTests();case.setUp();self.addCleanup(case.doCleanups);return case
    def test_rebases_canonical_programs_and_removes_database_access(self):
        case=self.context();b=builder();before=json.dumps(case.config,sort_keys=True)
        ports=dict(zip(sorted(b.MODULES),range(26000,26004)))
        result=b.worker_config(case.config,node_id='PC1',old_root=case.base,new_root=case.root/'worker',new_state=case.root/'worker-state',ports=ports)
        self.assertEqual(set(result['programs']),{'market_data','math','terminan'})
        self.assertNotIn('MARKET_DATA_DSN',result['programs']['market_data']['env']);self.assertNotIn(str(case.base),json.dumps(result))
        self.assertEqual(json.dumps(case.config,sort_keys=True),before)
        with self.assertRaises(TypeError):b.worker_config(case.config,node_id='PC1',old_root=case.base,new_root=case.root/'x',new_state=case.root/'y',ports=ports,auth_path='retired')
    def test_invalid_archive_precedes_any_code_or_state_creation(self):
        b=builder()
        with tempfile.TemporaryDirectory() as tmp:
            parent=Path(tmp).resolve();archive=parent/'bad.zip';archive.write_bytes(b'not a capsule');target=parent/'code';state=parent/'state'
            with patch.object(b.socket,'gethostname',return_value='Easy'):
                with self.assertRaises(ValueError):b.prepare_worker(archive,'0'*64,'a'*64,target,state,'PC1',dict(zip(sorted(b.MODULES),range(26000,26004))))
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


def prepared_worker_fixture(test,*,native=False):
    from tests.test_runtime_profile import RuntimeProfileTests
    from unified_system import lab_release,lab_runtime
    case=RuntimeProfileTests();case.setUp();test.addCleanup(case.doCleanups);b=builder();pin=case.pin;archive=case.root/'source.zip'
    with patch.object(b,'prove_sources',return_value=None):receipt=b.export_archive(case.base,archive,pin)
    target=case.root/'worker';state=case.root/'worker-state';ports=dict(zip(sorted(b.MODULES),range(26000,26004)));sealed=[]
    class InertRoot:
        def __init__(self,path):self.path=path
        @classmethod
        def create(cls,path):path.mkdir();return cls(path)
        def seal(self,pin):sealed.append(pin)
    from contextlib import nullcontext
    boundary=nullcontext() if native else patch('unified_system.lab_capsule_acl.FreshCodeRoot',InertRoot)
    with boundary,patch.object(b.socket,'gethostname',return_value='Easy'),patch.object(b,'prove_sources',return_value=None):
        result=b.prepare_worker(archive,receipt['archive_sha256'],pin,target,state,'PC1',ports)
    final=lab_release.verify_capsule(target,result['manifest_sha256'])['manifest'];config=json.loads((target/'runtime.json').read_bytes())
    lab_runtime.validate_config(config,final,target,hostname='Easy')
    test.assertEqual(final['sources'],case.manifest['sources']);test.assertFalse((state/'private').exists())
    test.assertNotIn('MARKET_DATA_DSN',config['programs']['market_data']['env']);test.assertEqual(result['runtime_readiness'],'NOT_TESTED')
    return case,target,state,result,sealed

class InertWorkerPipelineTests(unittest.TestCase):
    def test_full_prepare_stages_four_sources_without_credentials_or_processes(self):
        with patch('subprocess.Popen',side_effect=AssertionError('NO CHILD')),patch('socket.socket',side_effect=AssertionError('NO NETWORK')):
            case,target,state,result,sealed=prepared_worker_fixture(self)
        self.assertEqual(sealed,[result['manifest_sha256']]);self.assertEqual(result['result'],'PREPARED_READ_ONLY_WORKER')

@unittest.skipUnless(sys.platform=='win32','Windows NTFS ACL acceptance')
class NativeWorkerAclTests(unittest.TestCase):
    def test_prepared_worker_code_is_immutable_but_state_is_writable(self):
        from tests.test_lab_capsule_acl import ps
        case=target=None
        try:
            case,target,state,result,_=prepared_worker_fixture(self,native=True)
            with self.assertRaises(PermissionError):(target/'accidental.pyc').write_bytes(b'blocked')
            (state/'own.log').write_text('writable')
        finally:
            if target is not None and target.exists():
                self.assertEqual(target.parent,case.root);self.assertEqual(target.resolve(),target);self.assertFalse(target.is_symlink())
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
                '--state',str(parent/'state'),'--node','PC1','--ports-json','{}','--materialize']
            for pin,expected in [('b'*64,False),('a'*64,True)]:
                with patch.object(b,'admit_operator',return_value=frozenset({'a'*64})),patch.object(b,'prepare_worker',return_value={'scope':'MOCK_ROUTING_ONLY'}) as prepare,patch.object(b.sys,'stdout',io.StringIO()):
                    result=b.main([*common,'--source-manifest-sha256',pin])
                    self.assertEqual(result,0 if expected else 1);self.assertEqual(prepare.called,expected)
            self.assertFalse((parent/'code').exists());self.assertFalse((parent/'state').exists())
