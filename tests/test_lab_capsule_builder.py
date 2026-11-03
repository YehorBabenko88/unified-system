import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('lab_capsule_builder',ROOT/'scripts/prepare_lab_capsule.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

class BuilderTests(unittest.TestCase):
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
