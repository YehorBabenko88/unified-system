"""Executable plan boundary tests: actual capsule bytes, no installation actuator."""
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
import uuid
from tests.test_lab_release import fixture
from unified_system import lab_release
from unified_system.supervisor_deployment import DeploymentControllerAdapter, DeploymentBlocked

class DeploymentPlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.capsule=self.root/'capsule';self.capsule.mkdir()
        self.manifest=fixture(self.capsule);raw=lab_release.canonical(self.manifest)
        (self.capsule/'lab-release.json').write_bytes(raw);self.pin=hashlib.sha256(raw).hexdigest()
        self.adapter=DeploymentControllerAdapter(self.capsule,self.pin)
    def node(self,name='LS5'):
        return dict(node_id=name,incarnation_id=str(uuid.uuid4()),os_edition='HOME' if name in ('PC1','LS7') else 'PRO',role='COORDINATOR' if name in ('LS5','PC4','PC3') else 'WORKER',inventory_sha256='a'*64)
    def test_actual_capsule_bytes_and_sequential_rollout_reuse(self):
        plan=self.adapter.rollout([self.node(n) for n in ('LS7','PC2','PC3','LS5','PC1','PC4')])
        self.assertEqual([s['node']['node_id'] for s in plan['steps']],['LS5','PC4','PC3','PC2','PC1','LS7'])
        self.assertEqual(plan['manifest_sha256'],self.pin)
        self.assertEqual(len(plan['source_pins']),6);self.assertEqual(plan['max_concurrent_nodes'],1)
        self.assertEqual(plan['mode'],'PLAN_ONLY');self.assertFalse(plan['effects_authorized'])
        self.assertTrue(all(s['authority_freshness']=='UNKNOWN' for s in plan['steps']))
    def test_original_input_not_mutated_and_edition_qualification_separate(self):
        nodes=[self.node('PC1')];before=copy.deepcopy(nodes);plan=self.adapter.rollout(nodes)
        self.assertEqual(nodes,before);self.assertEqual(plan['steps'][0]['windows_qualification'],'HOME_NOT_RUN')
        self.assertEqual(plan['steps'][0]['local_health'],'UNKNOWN')
    def test_wrong_membership_role_duplicates_and_injected_health_reject(self):
        for nodes in ([self.node('ADMINIT')],[dict(self.node('PC1'),role='COORDINATOR')],[self.node(),self.node()],[dict(self.node(),local_health='HEALTHY')]):
            with self.subTest(nodes=nodes),self.assertRaises(DeploymentBlocked):self.adapter.rollout(nodes)
    def test_metadata_drift_is_blocker_never_upgrade_or_success(self):
        plan=self.adapter.rollout([dict(self.node('PC1'),os_edition='PRO')])
        self.assertIn('EDITION_DRIFT',plan['steps'][0]['blockers'])
        self.assertEqual(plan['steps'][0]['windows_qualification'],'NOT_RUN_EDITION_DRIFT')
    def test_empty_oversized_or_noncanonical_nodes_refused(self):
        for nodes in ([],[self.node()]*7,[dict(self.node(),incarnation_id='x')],[dict(self.node(),inventory_sha256='a'*64+'\n')]):
            with self.subTest(nodes=nodes),self.assertRaises(DeploymentBlocked):self.adapter.rollout(nodes)
    def test_capsule_tamper_after_constructor_refuses_before_preparation(self):
        (self.capsule/'runtime.json').write_bytes(b'tampered')
        with self.assertRaises(ValueError):self.adapter.prepare_install(self.node(),install_root=self.root/'install',state_root=self.root/'state',installation_id='i1',operation_id='op1')
        self.assertFalse((self.root/'install').exists());self.assertFalse((self.root/'state').exists())
    def test_prepare_reuses_existing_inactive_transaction_plan_without_writes(self):
        plan=self.adapter.prepare_install(self.node(),install_root=self.root/'install',state_root=self.root/'state',installation_id='i1',operation_id='op1')
        self.assertEqual(plan['transaction_plan']['schema'],'unified.installation-transaction.v1')
        self.assertEqual(plan['transaction_plan']['activation'],'BLOCKED');self.assertEqual(plan['mode'],'PLAN_ONLY')
        self.assertFalse((self.root/'install').exists());self.assertFalse((self.root/'state').exists())
        self.assertFalse(plan['effects_authorized'])
    def test_overlapping_roots_fail_existing_transaction_validation(self):
        with self.assertRaises(ValueError):self.adapter.prepare_install(self.node(),install_root=self.root/'same',state_root=self.root/'same',installation_id='i1',operation_id='op1')
        self.assertFalse((self.root/'same').exists())
    def test_rollback_reference_is_not_backup_or_rollback_verification(self):
        ref=dict(release_id='previous',manifest_sha256='b'*64,backup_sha256='c'*64)
        plan=self.adapter.rollout([self.node()],previous_release=ref)
        self.assertEqual(plan['rollback_readiness'],'REFERENCE_ONLY_NOT_VERIFIED')
        self.assertFalse(plan['rollback_authorized']);self.assertEqual(plan['previous_release'],ref)
    def test_development_task_cannot_be_cast_to_node_or_service_operation(self):
        with self.assertRaises(DeploymentBlocked):self.adapter.rollout([{'task_id':'dev','repository':'unified-system','base_sha':'a'*40}])
        with self.assertRaises(DeploymentBlocked):self.adapter.service_prototype({'mode':'DEVELOPMENT'},'a'*64)
    def test_no_execution_or_shell_authority_from_plans(self):
        plan=self.adapter.rollout([self.node()])
        with self.assertRaises(DeploymentBlocked):self.adapter.execute(plan)
        with self.assertRaises(TypeError):self.adapter.rollout([self.node()],shell='powershell')
        self.assertEqual(plan['installed_release'],'NOT_OBSERVED')
    def test_returned_plan_mutation_does_not_change_adapter(self):
        a=self.adapter.rollout([self.node()]);a['source_pins'].clear()
        b=self.adapter.rollout([self.node()]);self.assertEqual(len(b['source_pins']),6)


class ServicePrototypeTests(unittest.TestCase):
    def setUp(self):
        from tests.test_installation_service import ServiceResourceTests
        self.context=ServiceResourceTests('test_entry_denies_missing_protected_grant_or_token_and_ignores_caller_flags')
        self.context.setUp();self.addCleanup(self.context.doCleanups)
        self.adapter=DeploymentControllerAdapter(self.context.source,self.context.pin)
    def plan(self,node_id,role):
        from unified_system.installation_service import service_plan
        return service_plan(self.context.source,self.context.pin,self.context.root/'service','install',node_id,role,self.context.backend)
    def test_existing_service_plan_reused_without_registration_or_activation(self):
        plan=self.plan('LS5','CONTROL');result=self.adapter.service_prototype(plan,plan['plan_sha256'])
        self.assertEqual(result['mode'],'PLAN_ONLY');self.assertEqual(result['service_state'],'NOT_OBSERVED')
        self.assertFalse(result['effects_authorized']);self.assertEqual(self.context.backend.calls,[])
        self.assertFalse((self.context.root/'service').exists())
    def test_home_worker_cannot_receive_control_service_plan(self):
        plan=self.plan('PC1','CONTROL')
        with self.assertRaises(DeploymentBlocked):self.adapter.service_prototype(plan,plan['plan_sha256'])

if __name__=='__main__':unittest.main()
