import copy,hashlib,json,shutil,tempfile
from pathlib import Path
import unittest
from unified_system.integration_registry import RegistryRejected,decode,verify_identity,verify_ownership

ROOT=Path(__file__).resolve().parents[1]/'coordination'

class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.manifest=json.loads((ROOT/'integration-manifest.v1.json').read_text(encoding='utf-8'))
        self.pin=hashlib.sha256((ROOT/'integration-manifest.v1.json').read_bytes()).hexdigest()
        self.candidate={'schema':'unified.integration-candidate.v1','mode':'LAB_SIMULATION','contracts_sha256':self.manifest['contracts_sha256'],'modules':{k:{p:v[p] for p in ('head','tree')}for k,v in self.manifest['modules'].items()}}
    def test_matching_identity_never_authorizes_runtime_or_trading(self):
        actual=verify_identity(ROOT,self.candidate,expected_manifest_sha256=self.pin)
        self.assertEqual(actual['runtime_admission'],'BLOCKED');self.assertFalse(actual['deployment_authorized']);self.assertFalse(actual['trading_authorized'])
    def test_mixed_missing_extra_head_tree_and_contract_versions_rejected(self):
        variants=[]
        for field in ('head','tree'):
            value=copy.deepcopy(self.candidate);value['modules']['math'][field]='0'*40;variants.append(value)
        value=copy.deepcopy(self.candidate);del value['modules']['math'];variants.append(value)
        value=copy.deepcopy(self.candidate);value['modules']['ADMINIT']={'head':'0'*40,'tree':'0'*40};variants.append(value)
        value=copy.deepcopy(self.candidate);value['contracts_sha256']='0'*64;variants.append(value)
        for value in variants:
            with self.subTest(value=value),self.assertRaises(RegistryRejected):verify_identity(ROOT,value,expected_manifest_sha256=self.pin)
    def test_external_manifest_pin_cannot_be_replaced_by_candidate_claim(self):
        with self.assertRaises(RegistryRejected):verify_identity(ROOT,self.candidate,expected_manifest_sha256='0'*64)
        self.candidate['approved']=True
        with self.assertRaises(RegistryRejected):verify_identity(ROOT,self.candidate,expected_manifest_sha256=self.pin)
    def test_real_trading_and_json_duplicate_claims_denied(self):
        self.candidate['mode']='LIVE'
        with self.assertRaises(RegistryRejected):verify_identity(ROOT,self.candidate,expected_manifest_sha256=self.pin)
        for raw in (b'{"approved":false,"approved":true}',b'{"revision":NaN}'):
            with self.assertRaises(RegistryRejected):decode(raw)
    def test_eight_scopes_isolated_and_conflicting_reservations_denied(self):
        owners=json.loads((ROOT/'ownership.v1.json').read_text(encoding='utf-8'));self.assertTrue(verify_ownership(owners))
        owners['agents'][1]['allowed_files'].append(owners['agents'][0]['allowed_files'][0])
        with self.assertRaises(RegistryRejected):verify_ownership(owners)
    def test_shared_worktree_denied(self):
        owners=json.loads((ROOT/'ownership.v1.json').read_text(encoding='utf-8'));owners['agents'][4]['worktree']=owners['agents'][0]['worktree']
        with self.assertRaises(RegistryRejected):verify_ownership(owners)
    def test_agent_cannot_reserve_common_contract_or_activation_files(self):
        owners=json.loads((ROOT/'ownership.v1.json').read_text(encoding='utf-8'))
        owners['agents'][4]['allowed_files'].append('unified_system/service_bootstrap.py')
        with self.assertRaises(RegistryRejected):verify_ownership(owners)
    def test_rehashed_candidate_cannot_hide_changed_contract_or_gate_bytes(self):
        with tempfile.TemporaryDirectory(prefix='registry-test-owned-') as temporary:
            target=Path(temporary)
            for source in ROOT.glob('*.json'):shutil.copyfile(source,target/source.name)
            (target/'mandatory-gates.v1.json').write_text('{"go":"GO"}')
            with self.assertRaises(RegistryRejected):verify_identity(target,self.candidate,expected_manifest_sha256=self.pin)
    def test_windows_path_aliases_and_case_collisions_rejected(self):
        for path in ('UNIFIED_SYSTEM/LAN_TRANSPORT.PY','unified_system/../unified_system/contracts.py','unified_system\\contracts.py'):
            owners=json.loads((ROOT/'ownership.v1.json').read_text(encoding='utf-8'))
            owners['agents'][1]['allowed_files'].append(path)
            with self.subTest(path=path),self.assertRaises(RegistryRejected):verify_ownership(owners)
    def test_unsafe_repository_path_spelling_rejected(self):
        for path in ('/unified_system/x.py','C:/x.py','unified_system//x.py','./unified_system/x.py','unified_system/x.py.','unified_system/CON.py','unified_system/x.py:stream'):
            owners=json.loads((ROOT/'ownership.v1.json').read_text(encoding='utf-8'));owners['agents'][1]['allowed_files'].append(path)
            with self.subTest(path=path),self.assertRaises(RegistryRejected):verify_ownership(owners)

class AcceptanceTests(unittest.TestCase):
    def test_package_integrity_never_grants_execution(self):
        from unified_system.integration_registry import verify_acceptance_package
        package=ROOT.parent/'acceptance/20261106'
        pin=hashlib.sha256((package/'package-index.json').read_bytes()).hexdigest()
        result=verify_acceptance_package(package,expected_index_sha256=pin)
        self.assertFalse(result['physical_authorized']);self.assertEqual(result['go'],'NO-GO')
    def test_modified_member_and_wrong_external_pin_rejected(self):
        from unified_system.integration_registry import verify_acceptance_package
        source=ROOT.parent/'acceptance/20261106'
        pin=hashlib.sha256((source/'package-index.json').read_bytes()).hexdigest()
        with self.assertRaises(RegistryRejected):verify_acceptance_package(source,expected_index_sha256='0'*64)
        with tempfile.TemporaryDirectory(prefix='acceptance-owned-test-') as temporary:
            target=Path(temporary)/'package';shutil.copytree(source,target)
            (target/'rollback-plan.md').write_bytes(b'changed')
            with self.assertRaises(RegistryRejected):verify_acceptance_package(target,expected_index_sha256=pin)
    def test_additional_allocation_cannot_claim_another_scope(self):
        owners=json.loads((ROOT/'ownership.v1.json').read_bytes())
        duplicate=dict(owners['agents'][0]);duplicate['branch']='test-unique';duplicate['worktree']='C:/test-owned-unique'
        owners['agents'][6]['additional_allocations']=[duplicate]
        with self.assertRaises(RegistryRejected):verify_ownership(owners)

if __name__=='__main__':unittest.main()
