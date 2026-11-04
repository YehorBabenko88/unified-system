import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('lab_capsule_builder',ROOT/'scripts/prepare_lab_capsule.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

class BuilderTests(unittest.TestCase):
    def nssm_fixture(self,root,*,member=None,payload=b'INERT_NSSM_TEST_NEVER_EXECUTED'):
        import zipfile,hashlib
        from unified_system import windows_toolchain
        archive=root/'fixture.zip'
        member=builder.NSSM_MEMBER if member is None else member
        with zipfile.ZipFile(archive,'w') as z:z.writestr(member,payload)
        catalog=windows_toolchain.read_catalog()
        artifact=next(x for x in catalog['artifacts'] if x['component']=='nssm')
        artifact['sha256']=hashlib.sha256(archive.read_bytes()).hexdigest();artifact['expected_bytes']=archive.stat().st_size
        return archive,catalog,artifact,hashlib.sha256(payload).hexdigest(),len(payload)
    def test_nssm_offline_fixed_member_vendor_and_capsule_closure(self):
        import hashlib,json
        from unittest.mock import patch
        from unified_system import windows_toolchain,lab_release
        from tests.test_lab_release import fixture
        with tempfile.TemporaryDirectory() as temporary:
            parent=Path(temporary).resolve();archive,catalog,artifact,member_hash,member_size=self.nssm_fixture(parent)
            with patch.object(windows_toolchain,'read_catalog',return_value=catalog),patch.dict(builder.ARCHIVES,{builder.NSSM_FILENAME:artifact['sha256']}),patch.object(builder,'NSSM_MEMBER_SHA256',member_hash),patch.object(builder,'NSSM_MEMBER_BYTES',member_size):
                root=parent/'capsule';root.mkdir();manifest=fixture(root);(root/'runtime').mkdir()
                record=builder.stage_nssm(archive,root/'runtime/nssm')
            self.assertEqual(record['archive']['url'],artifact['url']);self.assertEqual(record['archive']['sha256'],artifact['sha256'])
            self.assertEqual(record['member']['sha256'],member_hash);self.assertEqual(record['native_execution'],'NOT_RUN')
            lock=root/'locks/vendor.json';lock.parent.mkdir();lock.write_bytes(builder.canonical({'nssm':record}))
            manifest['files'],manifest['directories']=builder.inventory(root)
            manifest['dependencies'].append(dict(name='nssm',version=artifact['version'],lock_path='locks/vendor.json'))
            raw=lab_release.canonical(manifest);(root/'lab-release.json').write_bytes(raw);pin=hashlib.sha256(raw).hexdigest()
            admitted=lab_release.verify_capsule(root,pin)
            self.assertEqual(admitted['manifest']['files']['runtime/nssm/nssm.exe']['sha256'],member_hash)
            self.assertEqual(json.loads(lock.read_bytes())['nssm']['member']['path'],builder.NSSM_MEMBER)
            staged=parent/'staged';lab_release.stage_capsule(root,staged,pin)
            self.assertEqual((staged/'runtime/nssm/nssm.exe').read_bytes(),b'INERT_NSSM_TEST_NEVER_EXECUTED')
            # Transport-only synthetic fixture: real closure checks, mocked Git
            # proof because these inert members are explicitly not source repos.
            from tests.test_prepare_worker_capsule import builder as worker_builder
            import zipfile
            worker=worker_builder();exported=parent/'worker.zip'
            with patch.object(worker,'prove_sources',return_value={}):worker.export_archive(root,exported,pin)
            with zipfile.ZipFile(exported) as worker_archive:
                self.assertEqual(worker_archive.read('runtime/nssm/nssm.exe'),b'INERT_NSSM_TEST_NEVER_EXECUTED')
                self.assertEqual(worker_archive.read('locks/vendor.json'),lock.read_bytes())
    def test_nssm_missing_wrong_archive_or_member_fails_before_destination(self):
        from unittest.mock import patch
        from unified_system import windows_toolchain
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();archive,catalog,artifact,member_hash,member_size=self.nssm_fixture(root)
            target=root/'output'
            with self.assertRaises((ValueError,FileNotFoundError)):builder.stage_nssm(root/'missing',target)
            with self.assertRaises(ValueError):builder.stage_nssm(archive,target)
            with patch.object(windows_toolchain,'read_catalog',return_value=catalog),patch.dict(builder.ARCHIVES,{builder.NSSM_FILENAME:artifact['sha256']}),patch.object(builder,'NSSM_MEMBER_BYTES',member_size):
                with self.assertRaises(ValueError):builder.stage_nssm(archive,target)
            self.assertFalse(target.exists())
    def test_nssm_missing_fixed_member_or_alias_and_existing_target_rejected(self):
        from unittest.mock import patch
        from unified_system import windows_toolchain
        for member in ('nssm-2.24-101-g897c7ad/win32/nssm.exe','unexpected/nssm.exe'):
            with self.subTest(member=member),tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary).resolve();archive,catalog,artifact,member_hash,member_size=self.nssm_fixture(root,member=member)
                with patch.object(windows_toolchain,'read_catalog',return_value=catalog),patch.dict(builder.ARCHIVES,{builder.NSSM_FILENAME:artifact['sha256']}),patch.object(builder,'NSSM_MEMBER_SHA256',member_hash),patch.object(builder,'NSSM_MEMBER_BYTES',member_size):
                    with self.assertRaisesRegex(ValueError,'NSSM_MEMBER_MISSING'):builder.stage_nssm(archive,root/'output')
                self.assertFalse((root/'output').exists())
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();archive,catalog,artifact,member_hash,member_size=self.nssm_fixture(root)
            target=root/'output';target.mkdir();(target/'keep').write_bytes(b'foreign')
            with patch.object(windows_toolchain,'read_catalog',return_value=catalog),patch.dict(builder.ARCHIVES,{builder.NSSM_FILENAME:artifact['sha256']}),patch.object(builder,'NSSM_MEMBER_SHA256',member_hash),patch.object(builder,'NSSM_MEMBER_BYTES',member_size):
                with self.assertRaisesRegex(ValueError,'NSSM_NEW_DESTINATION_REQUIRED'):builder.stage_nssm(archive,target)
            self.assertEqual((target/'keep').read_bytes(),b'foreign')

    def test_build_rejects_missing_or_bad_nssm_before_any_acl_or_output(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from unified_system.lab_capsule_acl import FreshCodeRoot
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();cache=root/'cache';cache.mkdir()
            args=SimpleNamespace(output=root/'capsule',state_root=root/'state',node='LS5',release_id='fixture',postgres_port=55459,cache=cache,nssm_archive=None)
            def pinned_other_inputs(path):
                return builder.LOCK_SHA if Path(path).name.endswith('.lock') else builder.ARCHIVES[Path(path).name]
            for invalid in (None,b'BAD_ARCHIVE_TEST_NEVER_EXECUTED'):
                if invalid is not None:(cache/builder.NSSM_FILENAME).write_bytes(invalid)
                with patch.object(builder.socket,'gethostname',return_value='LS5'),patch.object(builder.socket,'socket'),patch.object(builder,'sha',side_effect=pinned_other_inputs),patch.object(FreshCodeRoot,'create') as acl:
                    with self.assertRaises((ValueError,FileNotFoundError)):builder.build(args)
                    acl.assert_not_called()
                self.assertFalse(args.output.exists());self.assertFalse(args.state_root.exists())

    def test_nssm_real_approved_archive_read_only_extract_no_execution(self):
        import hashlib
        archive=Path(r'C:/Users/LS-5/Documents/Codex/2026-11-02/files-pasted-by-the-user-unified/work/release-unblock-20261103/nssm-2.24-101-g897c7ad.zip')
        if not archive.is_file():self.skipTest('Optional already-admitted offline archive unavailable')
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();record=builder.stage_nssm(archive,root/'nssm')
            self.assertEqual(hashlib.sha256((root/'nssm/nssm.exe').read_bytes()).hexdigest(),builder.NSSM_MEMBER_SHA256)
            self.assertEqual(record['archive']['bytes'],415458);self.assertEqual(record['member']['bytes'],368640)

    def test_npm_uses_distinct_new_empty_configuration_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve()
            env=builder.npm_environment({'INERT':'value'},root/'node.exe',root/'git.exe',root/'cache',root)
            user=Path(env['npm_config_userconfig']);global_config=Path(env['npm_config_globalconfig'])
            self.assertNotEqual(user,global_config)
            self.assertEqual(user.read_bytes(),b'');self.assertEqual(global_config.read_bytes(),b'')
            self.assertEqual(env['INERT'],'value')
            with self.assertRaises(FileExistsError):builder.npm_environment({},root/'node.exe',root/'git.exe',root/'cache',root)
    def test_native_probe_uses_admitted_distribution_names_and_versions(self):
        from unified_system.windows_wheels import parse_compiled_lock
        lock=parse_compiled_lock((ROOT/'integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock').read_bytes())
        pinned={n:p['version'] for n,p in lock.items()}
        probe=builder.native_probe(pinned)
        compile(probe,'native-probe','exec')
        self.assertIn("'psycopg': '3.3.6'",probe)
        self.assertIn('psycopg_binary',probe)
        self.assertNotIn('psycopg2',probe)
        self.assertNotIn('scipy',probe)
        del pinned['psycopg-binary']
        with self.assertRaisesRegex(ValueError,'NATIVE_PROBE_LOCK_MISMATCH'):builder.native_probe(pinned)
    def test_generated_runtime_satisfies_real_supervisor_contract(self):
        from unified_system.runtime_cli import validate_config
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();tool=root/'tool.exe';tool.write_bytes(b'inert')
            bootstrap=root/'sources/unified-system/unified_system/owned_python.py';bootstrap.parent.mkdir(parents=True);bootstrap.write_bytes(b'inert')
            sources={n:dict(root='sources/'+n,commit='a'*40,version='1.0.0') for n in builder.NAMES}
            snapshots={n:{'runtime_files':{'entry.py':{'raw_sha256':'b'*64}}} for n in builder.NAMES}
            config=builder.runtime_config(root,root.parent/(root.name+'-state'),sources,snapshots,tool,tool,tool,
                                          'lab-unit',(root.parent/'private-auth.json','c'*64),55459)
            self.assertEqual(validate_config(config,allow_physical=True),config)
            self.assertEqual(config['programs']['terminan']['env']['TERMINAN_LAB_SNAPSHOT'],str(root.parent/(root.name+'-state')/'public/lab-market-paper.json'))
    def test_lexical_parent_alias_rejected_before_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent=Path(temporary).resolve()
            with self.assertRaisesRegex(ValueError,'NONCANONICAL_PATH'):
                builder.destinations(str(parent/'capsule')+'/../alias',parent/'state')
            self.assertEqual(list(parent.iterdir()),[])
    def test_dangling_link_rejected(self):
        import os
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();link=root/'dangling'
            try:os.symlink(root/'missing',link)
            except OSError:self.skipTest('Windows symlink privilege unavailable')
            with self.assertRaisesRegex(ValueError,'LINK_REJECTED'):builder.safe(link)
    @unittest.skipUnless(__import__('os').name=='nt','pinned Windows runtime check')
    def test_pinned_bundled_pip_ignores_poisoned_ambient_site(self):
        import os
        import subprocess
        archive=builder.CACHE/'python.3.12.10.nupkg'
        if not archive.is_file():self.skipTest('Optional pinned Windows archive not provisioned')
        self.assertEqual(builder.sha(archive),builder.ARCHIVES[archive.name])
        member=builder.bundled_pip_member(archive)
        self.assertEqual(member,'tools/Lib/ensurepip/_bundled/pip-25.0.1-py3-none-any.whl')
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();runtime=root/'python'
            builder.extract(archive,runtime,'tools/')
            poison=root/'poison';poison.mkdir();marker=root/'ambient-executed'
            payload='from pathlib import Path; Path('+repr(str(marker))+').write_text("executed"); raise RuntimeError("AMBIENT_CODE_EXECUTED")'
            (poison/'sitecustomize.py').write_text(payload)
            (poison/'pip.py').write_text(payload)
            site=runtime/'Lib/site-packages';site.mkdir(exist_ok=True)
            (site/'poison.pth').write_text('import pathlib; pathlib.Path('+repr(str(marker))+').write_text("pth executed")')
            (site/'sitecustomize.py').write_text(payload)
            script=root/'pip-bootstrap.py';script.write_text(builder.pip_bootstrap())
            env={**builder.environment(),'PYTHONPATH':str(poison),'PYTHONHOME':str(poison),'PYTHONUSERBASE':str(poison)}
            result=subprocess.run([str(runtime/'python.exe'),'-I','-S','-B',str(script),str(runtime/member.removeprefix('tools/')),'--version'],env=env,cwd=poison,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('pip 25.0.1 from',result.stdout)
            self.assertIn('pip-25.0.1-py3-none-any.whl',result.stdout)
            self.assertFalse(marker.exists())
    def test_existing_destination_rejected_without_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent=Path(temporary).resolve();output=parent/'capsule';output.mkdir();marker=output/'keep';marker.write_bytes(b'unchanged')
            with self.assertRaisesRegex(ValueError,'NEW_DESTINATIONS_REQUIRED'):builder.destinations(output,parent/'state')
            self.assertEqual(marker.read_bytes(),b'unchanged');self.assertFalse((parent/'state').exists())
    def test_sibling_namespace_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent=Path(temporary).resolve()
            with self.assertRaisesRegex(ValueError,'SEPARATE_SIBLINGS_REQUIRED'):builder.destinations(parent/'capsule',parent/'capsule/state')
    def test_relative_namespace_rejected(self):
        with self.assertRaisesRegex(ValueError,'ABSOLUTE_LOCAL_PATH_REQUIRED'):builder.safe(Path('relative'))
    def test_inventory_binds_empty_directories(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();(root/'empty').mkdir();(root/'payload').write_bytes(b'abc')
            files,dirs=builder.inventory(root)
            self.assertEqual(dirs,['empty']);self.assertEqual(files['payload']['bytes'],3)
            (root/'.env').write_text('private')
            with self.assertRaisesRegex(ValueError,'ACTIVE_ENV_REJECTED'):builder.inventory(root)
    def test_hardlink_rejected(self):
        import os
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();(root/'first').write_bytes(b'abc');os.link(root/'first',root/'second')
            with self.assertRaises(ValueError):builder.inventory(root)
    def metadata_fixture(self,root,config):
        source=root/'source';source.mkdir();(source/'.git').mkdir()
        (source/'.git/config').write_text(config)
        git=root/'git.exe';git.write_bytes(b'inert tool never executed')
        return source,git
    def test_dirty_source_rejected(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temporary:
            source,git=self.metadata_fixture(Path(temporary).resolve(),'[core]\nfsmonitor = false\n')
            with patch.object(builder,'run',return_value=' M tracked.py') as runner:
                with self.assertRaisesRegex(ValueError,'SOURCE_DIRTY'):builder.require_clean(source,git,{})
                runner.assert_called_once()
    def test_malicious_metadata_rejected_before_git_execution(self):
        from unittest.mock import patch
        for config,reason in [('[core]\nfsmonitor = malicious.exe\n','UNSAFE_FSMONITOR'),
                              ('[include]\npath = malicious.gitconfig\n','CONFIG_INCLUDE_OR_FILTER')]:
            with self.subTest(reason=reason),tempfile.TemporaryDirectory() as temporary:
                source,git=self.metadata_fixture(Path(temporary).resolve(),config)
                with patch.object(builder,'run') as runner:
                    with self.assertRaisesRegex(ValueError,reason):builder.require_clean(source,git,{})
                    runner.assert_not_called()

if __name__=='__main__':unittest.main()
