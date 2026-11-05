import copy,hashlib,json,unittest
from unified_system.release_manifest import canonical,validate_manifest,parse_manifest
from unified_system.module_catalog import MODULE_IDS


def fixture():
    modules={name:dict(version='1.0.0',commit='a'*40,tree='b'*40,api_major=1,
        dependencies={},artifact=dict(path='modules/'+name+'.zip',sha256='c'*64,bytes=100),
        provenance=dict(repository='owner/'+name,run_id='123',attempt=1,workflow_sha='a'*40)) for name in MODULE_IDS}
    return dict(schema='unified.release.v3',release_id='release-1',sequence=1,
        publisher_sha256='d'*64,modules=modules,execution_authority=False,trading_authorized=False)


class ManifestTests(unittest.TestCase):
    def test_closed_six_module_manifest_roundtrip_is_not_signature_authority(self):
        m=fixture();self.assertEqual(validate_manifest(m,expected_publisher='d'*64),m)
        self.assertEqual(parse_manifest(canonical(m),expected_publisher='d'*64),m)
    def test_missing_alias_and_extra_module_fail(self):
        for replacement in (None,'UNIFIED','other'):
            m=fixture();m['modules'].pop('meta_analyse')
            if replacement:m['modules'][replacement]=fixture()['modules']['meta_analyse']
            with self.assertRaises(ValueError):validate_manifest(m,expected_publisher='d'*64)
    def test_untrusted_publisher_downgrade_wrong_provenance_and_units(self):
        for key,value in [('publisher_sha256','e'*64),('schema','unified.release.v2'),('sequence',True),('execution_authority',True)]:
            m=fixture();m[key]=value
            with self.assertRaises(ValueError):validate_manifest(m,expected_publisher='d'*64)
        m=fixture();m['modules']['grid']['provenance']['workflow_sha']='e'*40
        with self.assertRaises(ValueError):validate_manifest(m,expected_publisher='d'*64)
    def test_dependency_closure_cycles_and_casefold_paths_rejected(self):
        m=fixture();m['modules']['math']['dependencies']={'grid':'9.0.0'}
        with self.assertRaises(ValueError):validate_manifest(m,expected_publisher='d'*64)
        m=fixture();m['modules']['math']['dependencies']={'grid':'1.0.0'};m['modules']['grid']['dependencies']={'math':'1.0.0'}
        with self.assertRaises(ValueError):validate_manifest(m,expected_publisher='d'*64)
        m=fixture();m['modules']['math']['artifact']['path']='../bad.zip'
        with self.assertRaises(ValueError):validate_manifest(m,expected_publisher='d'*64)
    def test_duplicate_json_unknown_fields_and_noncanonical_bytes_rejected(self):
        m=fixture();raw=canonical(m)
        for bad in (raw.replace(b'{',b'{"sequence":0,',1),raw+b' ',b'{"x":NaN}'):
            with self.assertRaises(ValueError):parse_manifest(bad,expected_publisher='d'*64)
        m['trust']='CI_SUCCESS'
        with self.assertRaises(ValueError):validate_manifest(m,expected_publisher='d'*64)

    def test_release_module_versions_are_accepted_by_runtime_contract(self):
        from unified_system.runtime import ModuleSpec,_valid
        for version in ('1.0.0','1.2.3-rc.1','1.2.3+build.7'):
            m=fixture()
            for module in m['modules'].values():module['version']=version
            validate_manifest(m,expected_publisher='d'*64)
            for name,module in m['modules'].items():_valid(ModuleSpec(name,module['version']))
        for version in ('r1','latest','release-2','1.2'):
            m=fixture();m['modules']['grid']['version']=version
            with self.assertRaises(ValueError):validate_manifest(m,expected_publisher='d'*64)

    def test_actual_source_bundle_builder_preserves_exact_git_head(self):
        import pathlib,tempfile,subprocess,shutil,zipfile
        from unified_system.release_manifest import build_module_capsule
        with tempfile.TemporaryDirectory(prefix='mission3-builder-') as temp:
            root=pathlib.Path(temp);repo=root/'source';repo.mkdir()
            git=lambda *args:subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.PIPE).decode().strip()
            git('init');(repo/'hello.txt').write_bytes(b'owned source\n');git('add','.')
            git('-c','user.name=Lab','-c','user.email=lab@example.invalid','commit','-m','source')
            descriptor=dict(commit=git('rev-parse','HEAD'),tree=git('rev-parse','HEAD^{tree}'))
            executable=pathlib.Path(shutil.which('git')).resolve();pin=hashlib.sha256(executable.read_bytes()).hexdigest()
            output=root/'module.zip';facts=build_module_capsule(repo,descriptor,output,git_executable=executable,git_sha256=pin)
            self.assertEqual(facts['sha256'],hashlib.sha256(output.read_bytes()).hexdigest())
            import time
            time.sleep(2.05)  # ZIP timestamps otherwise change for identical source.
            second=root/'repeat.zip'
            again=build_module_capsule(repo,descriptor,second,git_executable=executable,git_sha256=pin)
            self.assertEqual(facts,again,'same source/toolchain must reproduce capsule bytes')
            self.assertEqual(output.read_bytes(),second.read_bytes())
            with zipfile.ZipFile(output) as archive:self.assertEqual(archive.namelist(),['source.bundle'])
            self.assertEqual(git('status','--porcelain'),'')
            with self.assertRaises(ValueError):build_module_capsule(repo,dict(descriptor,tree='f'*40),root/'bad.zip',git_executable=executable,git_sha256=pin)
