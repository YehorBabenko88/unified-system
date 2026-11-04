"""No local SCM/ACL lane: pure guards, fake HTTPS streams and workflow scope."""
import hashlib
from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch
from urllib.request import Request

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('ci_stopped_service', ROOT/'scripts/ci_stopped_service_acceptance.py')
lane = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lane)


class Response(io.BytesIO):
    def __init__(self, raw, url, length=None):
        super().__init__(raw)
        self.url = url
        self.headers = {} if length is None else {'Content-Length': str(length)}
    def geturl(self):
        return self.url


class HostedStoppedServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.env = dict(GITHUB_ACTIONS='true', RUNNER_ENVIRONMENT='github-hosted', RUNNER_OS='Windows', RUNNER_TEMP=str(self.root))
        self.target = self.root/'fresh-run'
        self.python = self.root/'inert-python.exe'
        self.python.write_bytes(b'INERT_UNIT_INTERPRETER_NEVER_EXECUTED')

    def reviewed_entry(self):
        raw=subprocess.check_output(['git','-C',str(ROOT),'cat-file','blob','HEAD:unified_system/service_entry.py'],timeout=10)
        self.assertEqual(len(raw),lane.BLOCKED_ENTRY_BYTES)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),lane.service.BLOCKED_ENTRY_SHA256)
        return raw

    def test_only_hosted_windows_fresh_descendant_is_admitted_without_effects(self):
        self.assertEqual(lane.admit_context(self.target, self.env, 'win32', 'fv-az123-456')['root'], self.target)
        for field, value in [('GITHUB_ACTIONS','false'), ('RUNNER_ENVIRONMENT','self-hosted'), ('RUNNER_OS','Linux'), ('RUNNER_TEMP','')]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                lane.admit_context(self.target, dict(self.env, **{field:value}), 'win32', 'fv-az123-456')
        for target in (self.root, self.root.parent/'outside'):
            with self.assertRaises(ValueError):lane.admit_context(target, self.env, 'win32', 'fv-az123-456')
        self.target.mkdir()
        with self.assertRaises(ValueError):lane.admit_context(self.target, self.env, 'win32', 'fv-az123-456')
        self.assertEqual(list(self.target.iterdir()), [])

    def test_all_office_and_adminit_variants_reject_os_name(self):
        for host in ('LS5','LS-5','ls_7','PC1','PC-2','pc_3','PC4-office','ADMINIT','ADMINIT-JQ1IQSV','admin-it.domain','DESKTOP-ADMINIT','backup_PC1','OfficeLS5Backup'):
            with self.subTest(host=host), self.assertRaises(ValueError):
                lane.admit_context(self.target, self.env, 'win32', host)
        self.assertFalse(self.target.exists())

    def test_entry_uses_os_name_and_rejects_before_network_or_acl(self):
        with patch.dict(lane.os.environ, dict(self.env, COMPUTERNAME='fv-az123-456')):
            with patch.object(lane.sys, 'platform', 'win32'), patch.object(lane.service, 'current_computer_name', return_value='LS-5') as actual:
                with patch.object(lane, 'execute_lane', side_effect=AssertionError('effects forbidden')) as execute,redirect_stdout(io.StringIO()):
                    self.assertEqual(lane.main(['--root',str(self.target),'--expected-sha','a'*40]), 1)
                    actual.assert_called_once();execute.assert_not_called()
        self.assertFalse(self.target.exists())

    def artifact(self, raw=b'PINNED_PUBLIC_ARCHIVE'):
        return dict(url='https://www.nssm.cc/ci/fixed.zip', max_bytes=64, expected_bytes=None,
                    sha256=hashlib.sha256(raw).hexdigest(), filename='fixed.zip')

    def test_download_requires_pinned_bytes_and_exclusive_destination(self):
        raw=b'PINNED_PUBLIC_ARCHIVE';item=self.artifact(raw);target=self.root/'archive.zip'
        class Opener:
            def open(self, request, timeout):
                self.timeout=timeout
                return Response(raw,item['url'],len(raw))
        opener=Opener();receipt=lane.download_archive(item,target,opener=opener)
        self.assertEqual(target.read_bytes(),raw);self.assertEqual(receipt['sha256'],item['sha256'])
        self.assertGreater(opener.timeout,0)
        with self.assertRaises((ValueError,FileExistsError)):lane.download_archive(item,target,opener=opener)

    def test_download_rejects_size_hash_and_cross_host_final_response(self):
        variants=[(b'x'*65,'https://www.nssm.cc/ci/fixed.zip',None),
                  (b'BAD','https://www.nssm.cc/ci/fixed.zip',None),
                  (b'PINNED_PUBLIC_ARCHIVE','https://other.example/fixed.zip',None),
                  (b'PINNED_PUBLIC_ARCHIVE','https://www.nssm.cc/ci/fixed.zip',100)]
        for index,(raw,url,length) in enumerate(variants):
            class Opener:
                def open(self, request, timeout):return Response(raw,url,length)
            with self.subTest(index=index),self.assertRaises(ValueError):
                lane.download_archive(self.artifact(),self.root/('bad'+str(index)),opener=Opener())

    def test_redirects_require_https_same_host_no_credentials_and_bounded_hops(self):
        for url in ('http://www.nssm.cc/fixed.zip','https://other.example/fixed.zip',
                    'https://user:secret@www.nssm.cc/fixed.zip','https://www.nssm.cc:8443/fixed.zip'):
            with self.subTest(url=url),self.assertRaises(ValueError):
                lane.SameHostRedirect('www.nssm.cc').redirect_request(Request('https://www.nssm.cc/old'),None,302,'',{},url)
        handler=lane.SameHostRedirect('www.nssm.cc')
        for index in range(3):
            self.assertIsNotNone(handler.redirect_request(Request('https://www.nssm.cc/old'),None,302,'',{},'https://www.nssm.cc/new'+str(index)))
        with self.assertRaises(ValueError):
            handler.redirect_request(Request('https://www.nssm.cc/old'),None,302,'',{},'https://www.nssm.cc/fourth')

    def test_phase_guard_requires_exact_action_and_plan_digest(self):
        guard=lane.PhaseGuard();guard.admit('a'*64,{'BEGIN','STAGE'})
        self.assertTrue(guard('BEGIN','a'*64))
        self.assertFalse(guard('START','a'*64));self.assertFalse(guard('BEGIN','b'*64))

    def test_artifact_ownership_output_is_confined_to_runner_command_file(self):
        command=self.root/'output';command.write_text('')
        with patch.dict(lane.os.environ,{'GITHUB_OUTPUT':str(command)}):
            lane.publish_owned_reports({'temporary':self.root})
        self.assertEqual(command.read_text(),'report_root_owned=true\n')
        before=command.read_bytes()
        with patch.dict(lane.os.environ,{'GITHUB_OUTPUT':str(command)}),self.assertRaises(ValueError):
            lane.publish_owned_reports({'temporary':self.root/'different-scope'})
        self.assertEqual(command.read_bytes(),before)

    @unittest.skipUnless(__import__('sys').platform == 'win32', 'Windows short-name path fixture')
    def test_inert_orchestration_accepts_canonical_fake_tools_under_short_temp_alias(self):
        import ctypes
        parent=self.root/'long-private-short-name-control'
        parent.mkdir()
        buffer=ctypes.create_unicode_buffer(32768)
        get_short=ctypes.WinDLL('kernel32',use_last_error=True).GetShortPathNameW
        get_short.argtypes=[ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_uint32]
        get_short.restype=ctypes.c_uint32
        count=get_short(str(parent),buffer,len(buffer))
        self.assertGreater(count,0);self.assertLess(count,len(buffer))
        if Path(buffer.value) == parent:
            self.skipTest('This volume does not provide a distinct short-name alias')
        self.assertEqual(Path(buffer.value).resolve(),parent)
        with patch.object(tempfile,'tempdir',buffer.value):
            self.test_inert_orchestration_dry_run_uses_fakes_only_and_preserves_state()
            # The shared service/uninstall fixture must also canonicalize its
            # own newly-created root, before the unchanged inventory guard.
            from tests.test_installation_service import ServiceResourceTests
            result=unittest.TestResult()
            ServiceResourceTests('test_registered_command_uses_only_reviewed_blocked_entry').run(result)
            self.assertTrue(result.wasSuccessful(),str(result.errors)+str(result.failures))

    def test_inert_orchestration_dry_run_uses_fakes_only_and_preserves_state(self):
        from tests.test_installation_service import FakeWindows
        from tests.test_installation_uninstall import FakeRemoval
        payload=b'INERT_TEST_ONLY_NSSM';pin=hashlib.sha256(payload).hexdigest()
        class CanonicalFakeWindows(FakeWindows):
            def native_tools(self):
                # Hosted Windows TEMP may use an 8.3 alias; fixture plans must
                # already satisfy the production canonical-path boundary.
                return {name:dict(tool,path=str(Path(tool['path']).resolve()))
                        for name,tool in super().native_tools().items()}
        backend=CanonicalFakeWindows()
        class PrivateRoot:
            def __init__(self, root):self.root=root;root.mkdir()
            def _owned(self):return self.root
        def download(artifact, target):
            target.write_bytes(b'INERT_TEST_ARCHIVE');return {'sha256':'a'*64}
        identity=dict(head='a'*40,tree='b'*40,checkout='INERT_UNIT_FIXTURE')
        entry=self.reviewed_entry()
        captured=io.StringIO()
        with patch.dict(lane.os.environ,self.env),patch.object(lane.sys,'platform','win32'),patch.object(lane.sys,'executable',str(self.python)):
            with patch.object(lane.service,'current_computer_name',return_value='TEST-PC'),patch.object(lane,'source_identity',return_value=identity):
                with patch.object(lane.FreshCodeRoot,'create',side_effect=PrivateRoot),patch.object(lane,'download_archive',side_effect=download):
                    with patch.object(lane.builder,'nssm_payload',return_value=(payload,{'scope':'INERT_UNIT_FIXTURE'})),patch.object(lane.builder,'NSSM_MEMBER_SHA256',pin),patch.object(lane.service,'NSSM_PIN',pin):
                        with patch.object(lane.service,'WindowsServiceBoundary',return_value=backend),patch.object(lane,'WindowsRemovalBoundary',return_value=FakeRemoval(backend)),patch.object(lane,'read_tool_versions',return_value={'scope':'INERT_UNIT_FIXTURE'}),patch.object(lane,'entry_blob',return_value=(entry,{'origin':'INERT_UNIT_FIXTURE'})),patch.object(lane,'publish_owned_reports'),redirect_stdout(captured):
                            result=lane.main(['--root',str(self.target),'--expected-sha','a'*40])
        facts=None
        if result != 0:
            facts={'stdout':captured.getvalue()[:4096]}
            report_path=self.target/'reports/report.json'
            if report_path.is_file():
                failed=__import__('json').loads(report_path.read_text())
                facts.update({key:failed.get(key) for key in ('failure_stage','error_code')})
                facts['phase_tail']=[call['action'] for call in failed.get('phase_calls',[])[-4:]]
            for label,path in [('temporary',self.root),('code',self.target/'stopped-resource/code')]:
                try:
                    stat=path.stat();facts[label]={'device':stat.st_dev,'inode':stat.st_ino,'links':stat.st_nlink}
                except OSError:facts[label]={'present':False}
        self.assertEqual(result,0,__import__('json').dumps(facts,sort_keys=True) if facts is not None else captured.getvalue()[:4096])
        report=__import__('json').loads((self.target/'reports/report.json').read_text())
        self.assertEqual(report['source_proof'],'NOT_EVALUATED');self.assertEqual(report['activation'],'BLOCKED')
        self.assertEqual(report['service_start'],'NOT_RUN');self.assertFalse(report['installation_closure'])
        self.assertEqual(report['capsule_leaves']['runtime/python/python.exe']['sha256'],hashlib.sha256(self.python.read_bytes()).hexdigest())
        self.assertIsNone(backend.service)
        self.assertEqual((self.target/'stopped-resource/state/preserved-fixture.bin').read_bytes(),b'SYNTHETIC_TEST_INPUT_PRESERVE_STATE')
        self.assertFalse((self.target/'stopped-resource/code').exists())

    def test_crlf_operator_file_does_not_replace_exact_lf_git_blob(self):
        entry=self.reviewed_entry()
        self.assertEqual(len(entry),lane.BLOCKED_ENTRY_BYTES)
        operator=self.root/'operator';source=operator/'unified_system';source.mkdir(parents=True)
        (source/'service_entry.py').write_bytes(entry.replace(b'\n',b'\r\n'))
        (source/'owned_python.py').write_bytes(b'INERT_BOOTSTRAP')
        payload=b'INERT_NSSM';pin=hashlib.sha256(payload).hexdigest()
        with patch.object(lane,'REPO',operator),patch.object(lane,'source_identity',return_value={'head':'a'*40}),patch.object(lane.shutil,'which',return_value='git'),patch.object(lane.sys,'executable',str(self.python)):
            with patch.object(lane.subprocess,'check_output',side_effect=[b'448\n',entry]) as git:
                with patch.object(lane.builder,'NSSM_MEMBER_SHA256',pin),patch.object(lane.service,'NSSM_PIN',pin):
                    manifest_pin,leaves,origin=lane.make_capsule(self.target,payload,'a'*40)
        staged=self.target/'sources/unified-system/unified_system/service_entry.py'
        self.assertEqual(staged.read_bytes(),entry)
        self.assertEqual((self.target/'runtime/python/python.exe').read_bytes(),self.python.read_bytes())
        self.assertEqual((source/'service_entry.py').read_bytes(),entry.replace(b'\n',b'\r\n'))
        self.assertEqual(origin['origin'],'EXACT_HEAD_GIT_BLOB')
        self.assertEqual(origin['sha256'],lane.service.BLOCKED_ENTRY_SHA256)
        self.assertEqual(git.call_args_list[-1].args[0],['git','-C',str(operator),'cat-file','blob','a'*40+':unified_system/service_entry.py'])
        manifest=lane.lab_release.verify_capsule(self.target,manifest_pin)['manifest']
        self.assertEqual(manifest['dependencies'][0]['version'],lane.platform.python_version())

    def test_git_blob_wrong_size_or_pin_is_rejected_without_normalization(self):
        entry=self.reviewed_entry()
        for outputs in ([b'449\n'],[b'448\n',b'x'*448],[str(len(entry.replace(b'\n',b'\r\n'))).encode()+b'\n']):
            with patch.object(lane,'source_identity',return_value={'head':'a'*40}),patch.object(lane.shutil,'which',return_value='git'),patch.object(lane.subprocess,'check_output',side_effect=outputs):
                with self.assertRaises(ValueError):lane.entry_blob('a'*40)

    def test_workflow_scopes_disposable_matrix_and_report_artifact(self):
        text=(ROOT/'.github/workflows/lab-stopped-service.yml').read_text()
        self.assertIn('os: [windows-2022, windows-2025]',text)
        self.assertIn('timeout-minutes: 15',text)
        self.assertIn('persist-credentials: false',text)
        self.assertIn('github.event.pull_request.head.sha || github.sha',text)
        self.assertIn('github.event_name',text)
        self.assertIn('path: ${{ runner.temp }}/${{ env.CI_STOPPED_NAME }}/reports/',text)
        job_env=text.split('    env:\n',1)[1].split('    steps:',1)[0]
        self.assertNotIn('runner.',job_env)
        self.assertIn('always()',text)
        self.assertIn("steps.acceptance.outputs.report_root_owned == 'true'",text)
        self.assertNotIn('include-hidden-files: true',text)


if __name__=='__main__':unittest.main()
