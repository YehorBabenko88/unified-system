"""Development context durability, never physical qualification."""
import copy
from contextlib import closing
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from pathlib import Path

from unified_system.contracts import ContractError
from unified_system.journal import Journal
from unified_system.mission_controller import MissionController


def task(name="task-1", dependencies=None):
    return dict(schema_version=1, task_id=name, mission_id="master", requirements=["retain context"],
                owner="agent", repository="owner/repo", pr_reference="owner/repo#1", base_sha="a"*40,
                allowed_files=["src/a.py"], dependencies=dependencies or [], acceptance_tests=["test_a"],
                evidence_requirements=["CI"], completion_criteria=["review"], next_actions=["test"],
                blockers=[], approvals=[], evidence=[], ci=[],
                axes=dict(source="UNKNOWN", tested="UNKNOWN", integrated="UNKNOWN", windows="UNKNOWN", physical="UNKNOWN"))


class MissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/"mission.db"
        self.controller = MissionController.create(self.path)

    def put(self, value=None):
        return self.controller.put(value or task(), expected_sequence=self.controller.projection()["sequence"])

    def test_reopen_preserves_receipts(self):
        self.put()
        first = Journal(self.path).read()
        value = task(); value["blockers"] = ["review pending"]
        self.put(value)
        reopened = MissionController.open(self.path)
        self.assertEqual(reopened.projection()["tasks"]["task-1"], value)
        self.assertEqual(Journal(self.path).read()[:len(first)], first)

    def test_duplicate_is_idempotent(self):
        self.put(); n = self.controller.projection()["sequence"]
        self.put()
        self.assertEqual(n, self.controller.projection()["sequence"])

    def test_concurrent_stale_writer_rejected(self):
        other = MissionController.open(self.path)
        self.put()
        with self.assertRaises(ContractError):
            other.put(task("task-2"), expected_sequence=1)

    def test_base_identity_collision_rejected(self):
        self.put(); value=task(); value["base_sha"]="b"*40
        with self.assertRaises(ContractError): self.put(value)

    def test_owner_and_scope_identity_immutable(self):
        self.put()
        for key, value in (("owner","other"),("allowed_files",["other.py"]),("repository","other/repo"),("mission_id","other")):
            changed=task(); changed[key]=value
            with self.subTest(key=key), self.assertRaises(ContractError): self.put(changed)

    def test_unknown_dependency_rejected(self):
        with self.assertRaises(ContractError): self.put(task(dependencies=["missing"]))

    def test_cycle_rejected(self):
        self.put(); self.put(task("task-2",["task-1"]))
        changed=task(dependencies=["task-2"])
        with self.assertRaises(ContractError): self.put(changed)

    def test_closed_fields_and_canonical_ids(self):
        for key,value in (("operation_type","INSTALL"),("task_id","bad\n"),("base_sha","a"*40+"\n"),("schema_version",True)):
            changed=task();changed[key]=value
            with self.subTest(key=key), self.assertRaises(ContractError): self.put(changed)

    def test_bounds_and_safe_paths(self):
        for key,value in (("requirements",["x"]*129),("owner","x"*129),("allowed_files",["../secret"]),("next_actions",["x"*2049])):
            changed=task();changed[key]=value
            with self.subTest(key=key), self.assertRaises(ContractError): self.put(changed)

    def test_fake_ci_success_never_physical_approval(self):
        changed=task(); changed["ci"]=[dict(workflow_id="ci",run_id=1,attempt=1,job_id=2,source_sha="b"*40,state="SUCCESS",artifact_references=["artifact"],authorization_state="UNKNOWN")]
        changed["approvals"]=[dict(reference="claimed",approved=True)]
        self.put(changed)
        projection=self.controller.projection()
        self.assertFalse(projection["grants_node_operations"])
        self.assertFalse(projection["native_authority"])
        self.assertEqual(projection["tasks"]["task-1"]["axes"]["physical"],"UNKNOWN")
        changed["axes"]["physical"]="READY"
        with self.assertRaises(ContractError): self.put(changed)

    def test_evidence_and_ci_are_typed_and_bounded(self):
        for key,value in (("evidence",[dict(reference="log",sha256="bad")]),("approvals",[dict(reference="x",approved=1)]),("ci",[dict(run_id=True)])):
            changed=task();changed[key]=value
            with self.subTest(key=key), self.assertRaises(ContractError): self.put(changed)

    def test_projection_is_copy(self):
        self.put(); snapshot=self.controller.projection();snapshot["tasks"].clear()
        self.assertIn("task-1",self.controller.projection()["tasks"])

    def test_corruption_rejected_without_repair(self):
        self.put()
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("UPDATE transitions SET receipt='{}' WHERE sequence=2")
            db.commit()
        before=self.path.read_bytes()
        with self.assertRaises(ContractError): MissionController.open(self.path)
        self.assertEqual(before,self.path.read_bytes())

    def test_arbitrary_existing_database_not_adopted(self):
        path=Path(self.tmp.name)/"legacy.db";journal=Journal(path);journal.initialize();journal.append("OBSERVING",dict(legacy=True))
        before=path.read_bytes()
        with self.assertRaises(ContractError): MissionController.create(path)
        with self.assertRaises(ContractError): MissionController.open(path)
        self.assertEqual(before,path.read_bytes())

    def test_unknown_schema_refused(self):
        path=Path(self.tmp.name)/"future.db";journal=Journal(path);journal.initialize();journal.append("OBSERVING",dict(kind="development-mission",schema_version=2))
        with self.assertRaises(ContractError): MissionController.open(path)

    def test_crash_before_append_keeps_last_commit(self):
        self.put(); before=self.controller.projection()
        changed=task();changed["next_actions"]=["uncommitted"]
        # Caller dies before invoking put: only committed receipt is recoverable.
        self.assertEqual(MissionController.open(self.path).projection(),before)

    def test_truncated_database_rejected(self):
        path=Path(self.tmp.name)/"broken.db";path.write_bytes(b"not sqlite")
        with self.assertRaises(ContractError): MissionController.open(path)

    def test_actual_process_exit_after_commit_reopens(self):
        root=Path(__file__).resolve().parents[1]
        script="import os,sys;sys.path.insert(0,sys.argv[1]);sys.path.insert(0,sys.argv[1]+'/tests');from test_mission_controller import task;from unified_system.mission_controller import MissionController;c=MissionController.open(sys.argv[2]);c.put(task(),expected_sequence=1);os._exit(23)"
        result=subprocess.run([sys.executable,"-I","-S","-B","-c",script,str(root),str(self.path)],capture_output=True,timeout=15)
        self.assertEqual(result.returncode,23,result.stderr)
        self.assertEqual(MissionController.open(self.path).projection()["tasks"]["task-1"],task())

    def test_unknown_receipt_rejected_even_with_valid_chain(self):
        Journal(self.path).append("OBSERVING",dict(kind="future",schema_version=1,task=task()),expected_sequence=1)
        with self.assertRaises(ContractError): MissionController.open(self.path)

    def test_boolean_marker_version_rejected(self):
        path=Path(self.tmp.name)/"bool.db";journal=Journal(path);journal.initialize()
        journal.append("OBSERVING",dict(kind="development-mission",schema_version=True))
        with self.assertRaises(ContractError): MissionController.open(path)

    def test_same_task_updates_keep_failed_ci_history(self):
        changed=task();changed["ci"]=[dict(workflow_id="ci",run_id=1,attempt=1,job_id=2,source_sha="a"*40,state="FAILURE",artifact_references=[],authorization_state="CONSUMED")]
        self.put(changed)
        self.put(task())
        self.assertEqual(Journal(self.path).read()[1]["receipt"]["task"]["ci"][0]["state"],"FAILURE")

    def test_record_bytes_bounded(self):
        changed=task();changed["requirements"]=["x"*2048]*33
        with self.assertRaises(ContractError): self.put(changed)

    def test_simultaneous_writers_have_one_commit(self):
        barrier=Barrier(2)
        def write(name):
            controller=MissionController.open(self.path)
            barrier.wait(timeout=5)
            try:
                controller.put(task(name),expected_sequence=1)
                return "committed"
            except ContractError:
                return "stale"
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(write,("task-a","task-b")))
        self.assertEqual(sorted(results),["committed","stale"])
        self.assertEqual(len(MissionController.open(self.path).projection()["tasks"]),1)

    def test_process_dies_during_uncommitted_transaction(self):
        self.put();before=self.controller.projection()
        script="import os,sqlite3,sys;db=sqlite3.connect(sys.argv[1]);db.execute('BEGIN IMMEDIATE');db.execute(\"INSERT INTO transitions VALUES (3,'OBSERVING','{}','uncommitted','uncommitted')\");os._exit(24)"
        result=subprocess.run([sys.executable,"-I","-S","-B","-c",script,str(self.path)],capture_output=True,timeout=15)
        self.assertEqual(result.returncode,24,result.stderr)
        self.assertEqual(MissionController.open(self.path).projection(),before)
        self.put(task("task-2"))
        self.assertEqual(self.controller.projection()["sequence"],3)

    def test_replay_rejects_semantic_identity_collision(self):
        self.put();changed=task();changed["base_sha"]="b"*40
        Journal(self.path).append("OBSERVING",dict(kind="development-task",schema_version=1,task=changed),expected_sequence=2)
        with self.assertRaises(ContractError): MissionController.open(self.path)


if __name__ == "__main__": unittest.main()
