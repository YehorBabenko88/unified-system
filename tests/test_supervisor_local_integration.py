"""Cross-component local specification; no native or physical qualification."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tests.test_lab_release import fixture as capsule_fixture
from tests.test_mission_controller import task as development_task
from tests.test_node_task_journal import operation, scoped_journal
from unified_system import ci_queue_controller as queue
from unified_system import lab_release
from unified_system.mission_controller import MissionController
from unified_system.node_supervisor_v2 import NodeSupervisorV2
from unified_system.node_task_journal import NodeJournalError, NodeOperation
from unified_system.supervisor_deployment import DeploymentBlocked, DeploymentControllerAdapter


FIXTURES=Path(__file__).resolve().parents[1]/"release/evidence/supervisor-local-integration-fixtures"
RAW_SHA256={
    "run":"24670c428528cea08c791fe31e3a7561bff78dd058006f20bdab8c2da09e03ec",
    "jobs":"a9447f5db6237d4811da9275202963c4dc043728188f35175787adf2f026fa6f",
}


class LocalIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        self.mission=MissionController.create(self.root/"development.db")
        self.journal=scoped_journal(self.root/"node.db")
        self.supervisor=NodeSupervisorV2(self.journal,node_id="node1",node_incarnation="inc1",cluster_id="cluster1")
        self.capsule=self.root/"capsule";self.capsule.mkdir()
        self.manifest=capsule_fixture(self.capsule)
        raw=lab_release.canonical(self.manifest);(self.capsule/"lab-release.json").write_bytes(raw)
        self.pin=hashlib.sha256(raw).hexdigest()
        self.deployment=DeploymentControllerAdapter(self.capsule,self.pin)

    @staticmethod
    def node():
        return dict(node_id="PC1",incarnation_id="12345678-1234-4234-8234-123456789abc",os_edition="HOME",role="WORKER",inventory_sha256="a"*64)

    def save(self,value):
        self.mission.put(value,expected_sequence=self.mission.projection()["sequence"])
        return MissionController.open(self.root/"development.db").projection()

    def test_development_receipts_cannot_parse_or_submit_as_node_operations(self):
        self.save(development_task())
        value=self.mission.projection()["tasks"]["task-1"]
        for attempted in (value,dict(operation(),**value)):
            with self.subTest(fields=sorted(attempted)),self.assertRaises(NodeJournalError): NodeOperation.parse(attempted)
            with self.assertRaises(NodeJournalError): self.supervisor.submit(attempted)
        self.assertEqual(self.journal.snapshot(),[])
        self.assertFalse(self.journal.path.exists())
        self.assertFalse(self.mission.projection()["grants_node_operations"])

    def test_archived_math_queue_reopens_unassigned_consumed_without_api(self):
        records={}
        for name,digest in RAW_SHA256.items():
            raw=(FIXTURES/("math-"+name+"-42352374979.json")).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),digest)
            records[name]=json.loads(raw)
        self.assertEqual(records["jobs"]["total_count"],1)
        job=records["jobs"]["jobs"][0]
        self.assertEqual(job["steps"],[]);self.assertEqual(job["runner_id"],0)
        pin=queue.Pin(*queue.PROTECTED)
        controller=queue.Controller.create(self.root/"math.db",pin,limit=2)
        # Ingest archived bytes only: no HTTP client, fetch, rerun or callback.
        captured=json.dumps(dict(run=records["run"],job=job,artifacts=[])).encode()
        receipt=controller.observe(captured,now=100)
        self.assertEqual(receipt["state"],"QUEUED")
        self.assertEqual(receipt["runner_assignment"],0)
        self.assertEqual(receipt["runner_assignment_state"],"UNASSIGNED")
        self.assertEqual(receipt["authorization_state"],"CONSUMED")
        reopened=queue.Controller.open(self.root/"math.db",pin)
        self.assertEqual(reopened.history(),[receipt])
        value=development_task();value["blockers"]=["Archived Math job has no runner assignment"]
        value["ci"]=[dict(workflow_id=str(pin.workflow_id),run_id=pin.run_id,attempt=pin.attempt,job_id=pin.job_id,source_sha=pin.source_sha,state=receipt["state"],artifact_references=[],authorization_state=receipt["authorization_state"])]
        projection=self.save(value)
        self.assertEqual(projection["tasks"]["task-1"]["ci"][0]["state"],"QUEUED")
        self.assertEqual(projection["tasks"]["task-1"]["axes"]["physical"],"UNKNOWN")
        self.assertFalse(projection["native_authority"])

    def test_report_status_completes_only_local_receipts_and_preserves_unknowns(self):
        self.supervisor.submit(operation())
        result=self.supervisor.run_readonly("task1")
        self.assertEqual(result["state"],"COMPLETED")
        self.assertEqual(result["receipt"]["code"],"LOCAL_RECEIPTS_ONLY")
        self.assertFalse(result["receipt"]["effects_authorized"])
        for axis in ("authority","source","freshness"): self.assertEqual(result["receipt"][axis],"UNKNOWN")
        self.assertEqual(result["receipt"]["physical_acceptance"],"NOT_RUN")
        self.assertEqual(scoped_journal(self.root/"node.db").get("task1"),result)
        plan=self.deployment.rollout([self.node()])
        self.assertEqual(plan["steps"][0]["local_health"],"UNKNOWN")
        self.assertEqual(plan["steps"][0]["authority_freshness"],"UNKNOWN")
        self.assertEqual(plan["steps"][0]["windows_qualification"],"HOME_NOT_RUN")

    def test_request_drain_blocks_despite_development_pass_and_approval_reference(self):
        value=development_task();value["axes"]={key:"PASS" for key in value["axes"]}
        value["approvals"]=[dict(reference="claimed-approval",approved=True)]
        projection=self.save(value)
        self.assertFalse(projection["native_authority"])
        self.supervisor.submit(operation(operation_type="REQUEST_DRAIN",approval_reference="claimed-approval"))
        result=self.supervisor.run_readonly("task1")
        self.assertEqual(result["state"],"BLOCKED")
        self.assertEqual(result["receipt"]["code"],"PLAN_ONLY_NATIVE_AUTHORITY_UNAVAILABLE")
        self.assertFalse(result["receipt"]["effects_authorized"])
        self.assertEqual(scoped_journal(self.root/"node.db").get("task1"),result)

    def test_verified_capsule_and_inactive_install_plan_never_create_target_or_rollback(self):
        report=lab_release.verify_capsule(self.capsule,self.pin)
        self.assertEqual(report["source_provenance"],"PINNED_METADATA_ONLY_VERIFY_SOURCES_BEFORE_EXECUTION")
        install=self.root/"install";state=self.root/"state"
        preparation=self.deployment.prepare_install(self.node(),install_root=install,state_root=state,installation_id="install1",operation_id="prepare1")
        self.assertEqual(preparation["transaction_plan"]["schema"],"unified.installation-transaction.v1")
        self.assertEqual(preparation["transaction_plan"]["activation"],"BLOCKED")
        self.assertEqual(preparation["mode"],"PLAN_ONLY");self.assertFalse(preparation["effects_authorized"])
        previous=dict(release_id="previous",manifest_sha256="b"*64,backup_sha256="c"*64)
        rollout=self.deployment.rollout([self.node()],previous_release=previous)
        self.assertEqual(rollout["rollback_readiness"],"REFERENCE_ONLY_NOT_VERIFIED")
        self.assertFalse(rollout["rollback_authorized"])
        with self.assertRaises(DeploymentBlocked): self.deployment.execute(preparation)
        self.assertFalse(install.exists());self.assertFalse(state.exists())

    def test_source_ci_and_development_pass_cannot_promote_trust_or_deployment(self):
        pin=queue.Pin("YehorBabenko88/unified-system",1,2,1,"a"*40,3)
        controller=queue.Controller.create(self.root/"ordinary-ci.db",pin)
        run=dict(id=2,workflow_id=1,run_attempt=1,head_sha=pin.source_sha,repository={"full_name":pin.repository},status="completed",conclusion="success")
        job=dict(id=3,run_id=2,run_attempt=1,head_sha=pin.source_sha,status="completed",conclusion="success",runner_id=1)
        receipt=controller.observe(json.dumps(dict(run=run,job=job,artifacts=[])).encode(),now=100)
        self.assertEqual(receipt["state"],"SUCCESS")
        value=development_task();value["axes"]={key:"PASS" for key in value["axes"]}
        value["ci"]=[dict(workflow_id="1",run_id=2,attempt=1,job_id=3,source_sha=pin.source_sha,state="SUCCESS",artifact_references=[],authorization_state="UNKNOWN")]
        projection=self.save(value)
        self.assertFalse(projection["grants_node_operations"]);self.assertFalse(projection["native_authority"])
        plan=self.deployment.rollout([self.node()])
        self.assertEqual(plan["mode"],"PLAN_ONLY");self.assertFalse(plan["effects_authorized"])
        self.assertFalse(plan["trading_authorized"]);self.assertFalse(plan["development_task_conversion"])
        self.assertEqual(plan["physical_acceptance"],"NOT_RUN")
        with self.assertRaises(DeploymentBlocked): self.deployment.execute(plan)
        report=lab_release.verify_capsule(self.capsule,self.pin)
        self.assertEqual(report["mode"],"LAB_SIMULATION")
        self.assertEqual(report["publisher_trust"],"NOT_REQUIRED_FOR_LAB")
        changed=copy.deepcopy(self.manifest);changed["mode"]="TRUSTED_RELEASE"
        raw=lab_release.canonical(changed);(self.capsule/"lab-release.json").write_bytes(raw)
        with self.assertRaises(ValueError): lab_release.verify_capsule(self.capsule,hashlib.sha256(raw).hexdigest())


if __name__=="__main__": unittest.main()
