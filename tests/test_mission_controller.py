"""Development context durability, never physical qualification."""
import copy
from contextlib import closing
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace

from unified_system.contracts import ContractError, canonical, seal
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
        self.root = Path(self.tmp.name).resolve()
        self.path = self.root/"mission.db"
        self.controller = MissionController.create(self.path)

    def put(self, value=None):
        return self.controller.put(value or task(), expected_sequence=self.controller.projection()["sequence"])

    def test_owned_temp_alias_is_resolved_before_guarded_journal_creation(self):
        parent=Path(self.tmp.name).resolve()/"owned canonical fixture parent";parent.mkdir()
        (parent/"walk").mkdir();alias=parent/"walk"/".."
        if os.name=="nt":
            import ctypes
            function=ctypes.WinDLL("kernel32",use_last_error=True).GetShortPathNameW
            function.argtypes=[ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_uint];function.restype=ctypes.c_uint
            buffer=ctypes.create_unicode_buffer(32768)
            length=function(str(parent),buffer,len(buffer))
            if 0<length<len(buffer) and "~" in buffer.value: alias=Path(buffer.value)
        self.assertNotEqual(str(alias),str(alias.resolve()))
        fixture=type(self)("test_duplicate_is_idempotent")
        self.addCleanup(fixture.doCleanups)
        # Only the owned TemporaryDirectory spelling is modeled. The actual
        # journal, canonicalization and unchanged production guards remain real.
        with patch.object(tempfile,"TemporaryDirectory",return_value=SimpleNamespace(name=str(alias),cleanup=lambda:None)):
            fixture.setUp()
        self.assertEqual(str(fixture.path.parent),str(parent.resolve()))
        fixture.put()
        self.assertEqual(MissionController.open(fixture.path).projection()["sequence"],2)
        with self.assertRaises(ContractError): MissionController.create(alias/"untrusted-raw.db")

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
        path=self.root/"legacy.db";journal=Journal(path);journal.initialize();journal.append("OBSERVING",dict(legacy=True))
        before=path.read_bytes()
        with self.assertRaises(ContractError): MissionController.create(path)
        with self.assertRaises(ContractError): MissionController.open(path)
        self.assertEqual(before,path.read_bytes())

    def test_unknown_schema_refused(self):
        path=self.root/"future.db";journal=Journal(path);journal.initialize();journal.append("OBSERVING",dict(kind="development-mission",schema_version=3,max_bytes=16*1024*1024,max_records=1024))
        with self.assertRaises(ContractError): MissionController.open(path)

    def test_crash_before_append_keeps_last_commit(self):
        self.put(); before=self.controller.projection()
        changed=task();changed["next_actions"]=["uncommitted"]
        # Caller dies before invoking put: only committed receipt is recoverable.
        self.assertEqual(MissionController.open(self.path).projection(),before)

    def test_truncated_database_rejected(self):
        path=self.root/"broken.db";path.write_bytes(b"not sqlite")
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
        path=self.root/"bool.db";journal=Journal(path);journal.initialize()
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

    def test_sparse_file_rejected_before_journal_materialization(self):
        with self.path.open("r+b") as stream: stream.truncate(17*1024*1024)
        with patch.object(Journal,"read",side_effect=AssertionError("unbounded read")):
            with self.assertRaises(ContractError): MissionController.open(self.path)

    def test_relative_path_refused_without_creation(self):
        with self.assertRaises(ContractError): MissionController.create(Path("relative-mission.db"))

    def test_hardlink_refused_without_writing(self):
        alias=self.root/"alias.db";os.link(self.path,alias)
        before=self.path.read_bytes()
        with self.assertRaises(ContractError): MissionController.open(alias)
        with self.assertRaises(ContractError): self.put()
        self.assertEqual(before,self.path.read_bytes())

    def test_legacy_version_one_refused_without_rewrite(self):
        path=self.root/"v1.db";journal=Journal(path);journal.initialize()
        journal.append("OBSERVING",dict(kind="development-mission",schema_version=1))
        before=path.read_bytes()
        with self.assertRaises(ContractError): MissionController.open(path)
        self.assertEqual(before,path.read_bytes())

    def test_persisted_record_capacity_refuses_append(self):
        path=self.root/"small.db";controller=MissionController.create(path,max_records=2)
        controller.put(task(),expected_sequence=1)
        before=path.read_bytes()
        with self.assertRaises(ContractError): controller.put(task("task-2"),expected_sequence=2)
        self.assertEqual(before,path.read_bytes())
        reopened=MissionController.open(path)
        with self.assertRaises(ContractError): reopened.put(task("task-2"),expected_sequence=2)

    def test_oversized_receipt_rejected_before_journal_materialization(self):
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("UPDATE transitions SET receipt=? WHERE sequence=1",("x"*70000,));db.commit()
        with patch.object(Journal,"read",side_effect=AssertionError("unbounded read")):
            with self.assertRaises(ContractError): MissionController.open(self.path)

    def test_invalid_capacity_refused_before_reservation(self):
        for limits in (dict(max_bytes=True),dict(max_bytes=1023),dict(max_bytes=65*1024*1024),dict(max_records=True),dict(max_records=1),dict(max_records=100001)):
            path=self.root/"invalid.db"
            with self.subTest(limits=limits),self.assertRaises(ContractError): MissionController.create(path,**limits)
            self.assertFalse(path.exists())

    def test_legacy_wal_sidecar_refused_before_create(self):
        path=self.root/"orphan.db";sidecar=Path(str(path)+"-wal");sidecar.write_bytes(b"foreign")
        with self.assertRaises(ContractError): MissionController.create(path)
        self.assertFalse(path.exists());self.assertEqual(sidecar.read_bytes(),b"foreign")

    def test_wal_sidecar_refused_before_read(self):
        Path(str(self.path)+"-wal").write_bytes(b"foreign")
        with patch.object(Journal,"read",side_effect=AssertionError("unbounded read")):
            with self.assertRaises(ContractError): MissionController.open(self.path)

    def test_conservative_byte_reserve_before_append(self):
        path=self.root/"bytes.db";controller=MissionController.create(path,max_bytes=1024*1024)
        with path.open("r+b") as stream: stream.truncate(1024*1024-32768)
        before=path.read_bytes()
        with self.assertRaises(ContractError): controller.put(task(),expected_sequence=1)
        self.assertEqual(before,path.read_bytes())

    def test_foreign_schema_refused_before_read(self):
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("CREATE TABLE foreign_data (secret TEXT)");db.commit()
        with patch.object(Journal,"read",side_effect=AssertionError("unbounded read")):
            with self.assertRaises(ContractError): MissionController.open(self.path)

    def test_maximum_task_dag_replays_and_cycle_revision_refused(self):
        path=self.root/"dag.db";controller=MissionController.create(path,max_records=1030)
        marker=Journal(path).read()[0];previous=seal(marker);rows=[]
        # Maximum supported identities and dependency fan-in, without recursive
        # graph traversal or repeated revalidation of the complete prior DAG.
        for index in range(1024):
            value=task("task-"+str(index),["task-"+str(n) for n in range(max(0,index-128),index)])
            receipt=dict(kind="development-task",schema_version=1,task=value)
            body=dict(sequence=index+2,state="OBSERVING",receipt=receipt,previous_hash=previous)
            digest=seal(body);rows.append((index+2,"OBSERVING",canonical(receipt).decode(),previous,digest));previous=digest
        with closing(sqlite3.connect(path)) as db:
            db.executemany("INSERT INTO transitions VALUES (?,?,?,?,?)",rows);db.commit()
        reopened=MissionController.open(path)
        self.assertEqual(len(reopened.projection()["tasks"]),1024)
        with self.assertRaises(ContractError): reopened.put(task("overflow"),expected_sequence=1025)
        with self.assertRaises(ContractError): reopened.put(task("task-0",["task-1023"]),expected_sequence=1025)

    def test_directory_symlink_or_junction_refused(self):
        target=self.root/"real";target.mkdir()
        MissionController.create(target/"mission.db")
        alias=self.root/"alias"
        try:
            alias.symlink_to(target,target_is_directory=True)
        except OSError:
            self.assertEqual(sys.platform,"win32")
            result=subprocess.run(["cmd.exe","/d","/c","mklink","/J",str(alias),str(target)],capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
        with self.assertRaises(ContractError): MissionController.open(alias/"mission.db")

    def test_persisted_bounds_are_recovered_and_closed(self):
        marker=Journal(self.path).read()[0]["receipt"]
        self.assertEqual(marker,dict(kind="development-mission",schema_version=2,max_bytes=16*1024*1024,max_records=1024))
        path=self.root/"bad-marker.db";journal=Journal(path);journal.initialize()
        journal.append("OBSERVING",dict(marker,max_records=True))
        with patch.object(Journal,"read",side_effect=AssertionError("unbounded read")):
            with self.assertRaises(ContractError): MissionController.open(path)




def continuation_metadata():
    return dict(source_head="b"*40, source_tree="c"*40, status="IN_PROGRESS",
                last_verified_result=None, evidence=[], retry_budget=dict(max_retries=2,retries_used=0),
                next_executable_step=dict(step_id="review",description="Review source evidence"),
                blocking_condition=None, required_authorization=["Root review"])


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name).resolve()/"context.db"
        self.controller=MissionController.create(self.path)
        self.controller.put(task(),expected_sequence=1)

    def checkpoint(self,metadata=None):
        return self.controller.checkpoint_continuation("task-1",metadata or continuation_metadata(),
                    expected_sequence=self.controller.projection()["sequence"])

    def test_continuation_reopen_detached_and_no_authority(self):
        original=self.controller.projection()
        result=self.checkpoint();self.assertFalse(result["continuations"]["task-1"]["stale"])
        result["continuations"].clear()
        reopened=MissionController.open(self.path)
        self.assertEqual(reopened.continuation_projection()["continuations"]["task-1"]["metadata"],continuation_metadata())
        self.assertEqual(set(reopened.projection()),set(original))
        for key in ("native_authority","runtime_admission","physical_execution_authorization","trading_authority","grants_node_operations"):
            self.assertIs(reopened.continuation_projection()[key],False)
        self.assertEqual(reopened.continuation_projection()["public_submit"],"DENY")

    def test_any_task_drift_stales_without_rewriting_history(self):
        self.checkpoint();before=Journal(self.path).read()
        changed=task();changed["next_actions"]=["different"]
        self.controller.put(changed,expected_sequence=3)
        self.assertTrue(self.controller.continuation_projection()["continuations"]["task-1"]["stale"])
        self.assertEqual(Journal(self.path).read()[:3],before)
        self.assertFalse(self.checkpoint()["continuations"]["task-1"]["stale"])

    def test_retry_budget_never_resets_even_after_stale_and_reopen(self):
        metadata=continuation_metadata();metadata["retry_budget"]["retries_used"]=1
        self.checkpoint(metadata)
        changed=task();changed["blockers"]=["blocked"];self.controller.put(changed,expected_sequence=3)
        self.controller=MissionController.open(self.path)
        with self.assertRaises(ContractError):self.checkpoint()
        metadata["retry_budget"]["max_retries"]=3
        with self.assertRaises(ContractError):self.checkpoint(metadata)

    def test_closed_types_sha_bounds_and_unknown_task(self):
        for mutate in (lambda m:m.update(extra=True),lambda m:m.update(source_tree="c"*40+"\n"),
                       lambda m:m["retry_budget"].update(max_retries=True),
                       lambda m:m["retry_budget"].update(retries_used=3),
                       lambda m:m.update(required_authorization=["x"*2049])):
            metadata=continuation_metadata();mutate(metadata)
            with self.assertRaises(ContractError):self.checkpoint(metadata)
        with self.assertRaises(ContractError):
            self.controller.checkpoint_continuation("missing",continuation_metadata(),expected_sequence=2)
        self.assertEqual(self.controller.projection()["sequence"],2)

    def test_stale_cas_duplicate_and_full_receipt_capacity(self):
        self.checkpoint();self.checkpoint();self.assertEqual(self.controller.projection()["sequence"],3)
        with self.assertRaises(ContractError):
            self.controller.checkpoint_continuation("task-1",continuation_metadata(),expected_sequence=2)
        metadata=continuation_metadata();metadata["required_authorization"]=["x"*2048]*128
        with self.assertRaises(ContractError):self.checkpoint(metadata)

    def test_unknown_receipt_version_and_invalid_binding_reject_reopen(self):
        Journal(self.path).append("OBSERVING",dict(kind="development-continuation",schema_version=2,
            task_id="task-1",task_snapshot_sha256="0"*64,metadata=continuation_metadata()),expected_sequence=2)
        with self.assertRaises(ContractError):MissionController.open(self.path)

    def test_result_scope_and_evidence_remain_observations(self):
        metadata=continuation_metadata()
        metadata["last_verified_result"]=dict(status="PASS",scope="SOURCE_ONLY",summary="Reviewed",source_head="d"*40,source_tree="e"*40)
        metadata["evidence"]=[dict(reference="local receipt",sha256="f"*64)]
        metadata["status"]="COMPLETE"
        result=self.checkpoint(metadata)
        self.assertEqual(result["continuations"]["task-1"]["metadata"],metadata)
        self.assertIs(result["physical_execution_authorization"],False)
        metadata["last_verified_result"]["authority"]=True
        with self.assertRaises(ContractError):self.checkpoint(metadata)

    def test_continuation_persisted_record_capacity(self):
        path=self.path.parent/"limited.db"
        limited=MissionController.create(path,max_records=2)
        limited.put(task(),expected_sequence=1)
        with self.assertRaises(ContractError):
            limited.checkpoint_continuation("task-1",continuation_metadata(),expected_sequence=2)
        self.assertEqual(len(Journal(path).read()),2)

    def test_unknown_continuation_version_rejected(self):
        import hashlib
        Journal(self.path).append("OBSERVING",dict(kind="development-continuation",schema_version=3,
            task_id="task-1",task_snapshot_sha256=hashlib.sha256(canonical(task())).hexdigest(),
            metadata=continuation_metadata()),expected_sequence=2)
        with self.assertRaises(ContractError):MissionController.open(self.path)

    def test_aba_task_drift_stays_stale_until_explicit_checkpoint(self):
        metadata=continuation_metadata();metadata["retry_budget"]["retries_used"]=1
        self.checkpoint(metadata)
        changed=task();changed["blockers"]=["intermediate drift"]
        self.controller.put(changed,expected_sequence=3)
        self.controller.put(task(),expected_sequence=4)
        self.controller=MissionController.open(self.path)
        self.assertTrue(self.controller.continuation_projection()["continuations"]["task-1"]["stale"])
        self.checkpoint(metadata)
        self.assertEqual(self.controller.projection()["sequence"],6)
        self.assertFalse(MissionController.open(self.path).continuation_projection()["continuations"]["task-1"]["stale"])
        lower=continuation_metadata()
        with self.assertRaises(ContractError):self.checkpoint(lower)
        metadata["retry_budget"]["max_retries"]=3
        with self.assertRaises(ContractError):self.checkpoint(metadata)

if __name__ == "__main__": unittest.main()
