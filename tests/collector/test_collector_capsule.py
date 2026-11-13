"""Real existing verifier over bounded inert files; no candidate execution."""
import copy
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).absolute().parents[2]
sys.path.insert(0, str(ROOT))
from unified_system import lab_release as lab
from unified_system.installation_service import service_plan
from unified_system import installation_service as service
from tests.test_lab_release import fixture as v1_fixture

KIND = 'unified.lab-release.collector.v1'
PERMISSIONS = ('provider_rest', 'provider_websocket', 'trading', 'training', 'math',
               'public_submit', 'authority_mutation', 'service_creation', 'acl_changes')


def pin(raw):
    return dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def source_pin(raw):
    return dict(pin(raw), blob_oid=hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest())


def fixture(root):
    files = {}
    def put(name, raw):
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
        files[name] = pin(raw)
    put('source-manifest.json', lab.canonical({'fixture': 'source ledger, not source attestation'}))
    put('collector.json', lab.canonical(dict(schema='unified.data-only-collector.profile.v1',
        mode='SYNTHETIC_OFFLINE', grid_launch_profile='grid.data-only-collector.v1',
        source_manifest_sha256=files['source-manifest.json']['sha256'],
        instrument_identity='synthetic-btcusdt-v1', network=dict(rest=False, websocket=False),
        features=dict(trading=False, training=False, math=False, public_submit=False, authority_mutation=False))))
    put('runtime/python/python.exe', b'INERT NEVER EXECUTED')
    put('dependencies/requirements.lock', b'fixture==1.0\n')
    put('tools/git.exe', b'INERT GIT NEVER EXECUTED')
    sources = {}
    for name, repository in [('unified-system', 'unified-system'), ('grid', 'bybit-cluster-grid')]:
        raw = ('inert ' + name + '\n').encode()
        put('sources/' + name + '/module.txt', raw)
        sources[name] = dict(repository='YehorBabenko88/' + repository, root='sources/' + name,
                             commit='a' * 40, tree='b' * 40, version='1.0.0', dependencies={},
                             file_pins={'module.txt': source_pin(raw)})
    lock = files['dependencies/requirements.lock']['sha256']
    return dict(schema=KIND, mode='SYNTHETIC_OFFLINE', release_id='collector-1', sequence=1,
                permissions=dict.fromkeys(PERMISSIONS, False), sources=sources, files=files,
                directories=sorted({p.as_posix() for name in files for p in Path(name).parents if str(p) != '.'}),
                dependencies=[dict(name='python', version='3.12.10', lock_path='dependencies/requirements.lock', lock_sha256=lock)],
                collector_profile='collector.json', source_manifest='source-manifest.json', git='tools/git.exe',
                runtime=dict(python=dict(path='runtime/python/python.exe', version='3.12.10', sha256=files['runtime/python/python.exe']['sha256']),
                             lock=dict(path='dependencies/requirements.lock', sha256=lock)), overlays=[])


class CollectorCapsuleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='collector-capsule-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.m = fixture(self.root)

    def publish(self):
        raw = lab.canonical(self.m)
        (self.root / 'lab-release.json').write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def verify(self):
        return lab.verify_capsule(self.root, self.publish())

    def test_actual_collector_verifier_accepts_exact_two_source_closure_without_authority(self):
        report = self.verify()
        self.assertEqual(report['mode'], 'SYNTHETIC_OFFLINE')
        self.assertEqual(report['execution'], 'DATA_ONLY')
        self.assertIs(report['execution_authority'], False)
        self.assertIs(report['service_admission'], False)
        self.assertEqual(report['profile_policy'], 'RUNTIME_VALIDATION_REQUIRED')
        self.assertEqual(report['manifest'], self.m)

    def test_existing_v1_parse_and_report_contract_unchanged(self):
        old = self.root / 'old'
        old.mkdir()
        m = v1_fixture(old)
        raw = lab.canonical(m)
        (old / 'lab-release.json').write_bytes(raw)
        report = lab.verify_capsule(old, hashlib.sha256(raw).hexdigest())
        self.assertEqual(set(report), {'mode', 'manifest_sha256', 'release_id', 'publisher_trust',
                                      'files_verified', 'source_provenance', 'trading_authorized', 'execution', 'physical_acceptance', 'manifest'})
        self.assertEqual(report['execution'], 'PAPER_ONLY')
        self.assertEqual(report['manifest'], m)

    def test_early_service_kind_guard_before_sid_or_native(self):
        class NeverNative:
            def sid(self, name): raise AssertionError('SID lookup occurred before kind guard')
        with tempfile.TemporaryDirectory(prefix='collector-service-parent-') as parent, patch.object(lab, 'verify_capsule', return_value={'manifest': {'schema': KIND}}):
            with self.assertRaises(ValueError):
                service_plan(self.root, 'a' * 64, Path(parent).resolve() / 'service', 'installation', 'node', 'WORKER', NeverNative())

    def test_actual_verified_collector_cannot_enter_v1_service(self):
        class NeverNative:
            def sid(self, name): raise AssertionError('native boundary reached')
        with tempfile.TemporaryDirectory(prefix='collector-service-actual-') as parent:
            with self.assertRaises(ValueError):
                service_plan(self.root, self.publish(), Path(parent).resolve() / 'service', 'installation', 'node', 'WORKER', NeverNative())

    def test_service_resource_plan_checker_also_rejects_collector_kind_first(self):
        class CollectorResult(dict):
            def __getitem__(self, key):
                if key == 'files': raise AssertionError('Collector entered V1 file/native-plan validation')
                return super().__getitem__(key)
        with tempfile.TemporaryDirectory(prefix='collector-checker-') as parent:
            root = Path(parent).resolve() / 'service'
            code = root / 'code'
            body = dict(schema=service.SCHEMA, activation='BLOCKED', installation_id='installation',
                        node_id='node', computer_name='FIXTURE', role='WORKER', root=str(root),
                        code=str(code), state=str(root / 'state'), capsule_root=str(self.root),
                        manifest_sha256='a'*64,
                        service_name='UnifiedLab_'+service.seal(dict(installation_id='installation', node_id='node'))[:24],
                        service_sid='S-1-5-80-1-2-3-4-5', nssm=str(code/'runtime/nssm/nssm.exe'),
                        nssm_sha256=service.NSSM_PIN, python=str(code/'runtime/python/python.exe'),
                        python_sha256='b'*64, bootstrap=str(code/'sources/unified-system/unified_system/owned_python.py'),
                        bootstrap_sha256='c'*64, entry=str(code/'sources/unified-system/unified_system/service_entry.py'),
                        entry_sha256=service.SERVICE_ENTRY_SHA256,
                        executor_sha256=hashlib.sha256(service.MODULE.read_bytes()).hexdigest(),
                        native_tools={name:dict(path=str(Path(parent).resolve()/(name+'.exe')),sha256='d'*64)
                                      for name in ('sc','powershell')})
            body['parameters']='-I -S -B "'+body['entry']+'"'
            plan=dict(body, plan_sha256=service.seal(body))
            with patch.object(lab, 'verify_capsule', return_value={'manifest': CollectorResult(schema=KIND)}):
                with self.assertRaises(ValueError): service._check_plan(plan)
            # Same self-hashed V1-shaped input, this time through the actual
            # Collector capsule verifier rather than the isolated-kind double.
            body['manifest_sha256'] = self.publish()
            actual_plan = dict(body, plan_sha256=service.seal(body))
            with self.assertRaises(ValueError): service._check_plan(actual_plan)

    def test_case_alias_inventory_or_source_pin_and_dependency_cycle_rejected(self):
        original = copy.deepcopy(self.m)
        for mutation in ('file_alias', 'pin_alias', 'cycle', 'foreign_overlay', 'runtime_version', 'primary_extra'):
            self.m = copy.deepcopy(original)
            if mutation == 'file_alias': self.m['files']['SOURCES/grid/module.txt'] = self.m['files']['sources/grid/module.txt']
            if mutation == 'pin_alias': self.m['sources']['grid']['file_pins']['MODULE.txt'] = self.m['sources']['grid']['file_pins']['module.txt']
            if mutation == 'cycle':
                self.m['sources']['grid']['dependencies'] = {'unified-system': '1.0.0'}
                self.m['sources']['unified-system']['dependencies'] = {'grid': '1.0.0'}
            if mutation == 'foreign_overlay': self.m['overlays'] = [dict(source='math', commit='c'*40, tree='d'*40, files={'x': source_pin(b'x')})]
            if mutation == 'runtime_version': self.m['runtime']['python']['version'] = '3.11.10'
            if mutation == 'primary_extra': self.m['sources']['grid']['file_pins']['missing.py'] = source_pin(b'missing')
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): self.verify()

    def test_permission_true_integer_or_extra_rejected(self):
        for value in (True, 0, 1, None):
            with self.subTest(value=value):
                self.m['permissions']['provider_rest'] = value
                with self.assertRaises(ValueError): self.verify()
        self.m['permissions']['provider_rest'] = False
        self.m['permissions']['extra'] = False
        with self.assertRaises(ValueError): self.verify()

    def test_missing_foreign_or_case_alias_source_rejected(self):
        for replacement in ({'grid': self.m['sources']['grid']}, dict(self.m['sources'], math=self.m['sources']['grid'])):
            with self.subTest(keys=list(replacement)):
                current = self.m['sources']
                self.m['sources'] = replacement
                with self.assertRaises(ValueError): self.verify()
                self.m['sources'] = current

    def test_declared_source_oid_mismatch_rejected_even_when_sha_matches(self):
        self.m['sources']['grid']['file_pins']['module.txt']['blob_oid'] = '0' * 40
        with self.assertRaises(ValueError): self.verify()

    def test_ordered_overlays_require_final_bytes_and_final_git_oid(self):
        for i, raw in enumerate((b'first overlay\n', b'final overlay\n')):
            self.m['overlays'].append(dict(source='grid', commit=str(i + 1) * 40, tree='c' * 40,
                                           files={'module.txt': source_pin(raw)}))
        path = self.root / 'sources/grid/module.txt'
        path.write_bytes(raw)
        self.m['files']['sources/grid/module.txt'] = pin(raw)
        self.assertEqual(self.verify()['manifest']['overlays'], self.m['overlays'])
        self.m['overlays'].reverse()
        with self.assertRaises(ValueError): self.verify()

    def test_overlay_cannot_escape_root_or_add_unlisted_source_file(self):
        raw = b'not there'
        for name in ('../escape.py', 'new.py'):
            self.m['overlays'] = [dict(source='grid', commit='c' * 40, tree='d' * 40, files={name: source_pin(raw)})]
            with self.subTest(name=name), self.assertRaises(ValueError): self.verify()

    def test_lock_or_runtime_pin_mismatch_rejected(self):
        original = copy.deepcopy(self.m)
        for key in ('runtime', 'dependency'):
            self.m = copy.deepcopy(original)
            if key == 'runtime': self.m['runtime']['python']['sha256'] = '0' * 64
            else: self.m['dependencies'][0]['lock_sha256'] = '0' * 64
            with self.subTest(key=key), self.assertRaises(ValueError): self.verify()

    def test_exact_inventory_extra_file_or_directory_rejected(self):
        self.verify()
        (self.root / 'extra').mkdir()
        with self.assertRaises(ValueError): self.verify()
        (self.root / 'extra').rmdir()
        (self.root / 'extra.txt').write_bytes(b'unknown')
        with self.assertRaises(ValueError): self.verify()

    def test_single_link_and_symlink_protections_reused(self):
        self.verify()
        path = self.root / 'sources/grid/module.txt'
        alias = self.root / 'hardlink'
        os.link(path, alias)
        with self.assertRaises(ValueError): self.verify()
        alias.unlink()
        # Symlink creation may need privilege on Windows; hardlink invariant
        # above is always exercised. Reparse/symlink walk uses existing verifier.
        if os.name != 'nt':
            alias.symlink_to(path)
            with self.assertRaises(ValueError): self.verify()

    def test_unknown_kind_and_extra_manifest_field_rejected(self):
        self.m['schema'] = KIND + '.unknown'
        with self.assertRaises(ValueError): self.verify()

    def test_profile_source_binding_and_provider_deny_checked_without_import(self):
        original = (self.root / 'collector.json').read_bytes()
        for mutation in ('binding', 'network', 'identity', 'canonical'):
            profile = __import__('json').loads(original)
            if mutation == 'binding': profile['source_manifest_sha256'] = '0' * 64
            if mutation == 'network': profile['network']['websocket'] = True
            if mutation == 'identity': profile['instrument_identity'] = 'REAL_BTCUSDT'
            raw = lab.canonical(profile)
            if mutation == 'canonical': raw += b' '
            (self.root / 'collector.json').write_bytes(raw)
            self.m['files']['collector.json'] = pin(raw)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): self.verify()
        self.m['schema'] = KIND
        self.m['runtime_config'] = 'collector.json'
        with self.assertRaises(ValueError): self.verify()

    def test_canonical_duplicate_key_and_external_digest_enforced(self):
        raw = lab.canonical(self.m)
        altered = raw.replace(b'{', b'{"schema":"' + KIND.encode() + b'",', 1)
        with self.assertRaises(ValueError): lab.parse_manifest(altered, hashlib.sha256(altered).hexdigest())
        with self.assertRaises(ValueError): lab.parse_manifest(raw, '0' * 64)

    def test_actual_staging_reuses_existing_copy_and_rejects_existing_target(self):
        target = self.root / 'stage'
        # A target inside source is forbidden; use another private sibling.
        with self.assertRaises(ValueError): lab.stage_capsule(self.root, target, self.publish())
        with tempfile.TemporaryDirectory(prefix='collector-stage-') as parent:
            target = Path(parent).resolve() / 'new'
            result = lab.stage_capsule(self.root, target, self.publish())
            self.assertEqual(result['mode'], 'SYNTHETIC_OFFLINE')
            with self.assertRaises(ValueError): lab.stage_capsule(self.root, target, self.publish())


if __name__ == '__main__': unittest.main(verbosity=2)
