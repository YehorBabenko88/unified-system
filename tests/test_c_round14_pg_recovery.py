"""C ROUND14: separate native PostgreSQL18 recovery fault lane.

Only a new, isolated, marker-owned non-5432 disposable cluster is touched.
The test's Root quiescence flag is NOT trusted production authorization.
"""
import os
import subprocess
import sys
import shutil
import tempfile
import unittest
from pathlib import Path

from unified_system.lab_postgres import LabPostgres
from unified_system.lab_pg_fence import (
    install_lab_fence, claim_lab_fence, observe_old_lab_backend)
from unified_system.lab_pg_checkpoint import (
    install_lab_checkpoint, read_lab_pending)
from unified_system.lab_pg_recovery import (recover_exclusive_lab_cluster,
                                            contain_exclusive_lab_cluster)
from unified_system.lab_simulation_admission import LabAdmissionRejected


class NativeCRecoveryTests(unittest.TestCase):
    def setUp(self):
        if (not os.environ.get("LAB_POSTGRES_BIN")
                or os.name == "nt"
                or hasattr(os, "geteuid") and os.geteuid() == 0):
            raise AssertionError("C_ROUND14_NATIVE_NONROOT_PG18_REQUIRED")
        import psycopg
        import uuid
        from tests.test_lab_postgres import canonical_schema
        self.psycopg = psycopg
        self.root = Path(tempfile.mkdtemp(prefix="c-round14-recovery-"))
        self.root.chmod(0o700)
        self.pg = None
        self.writer = None
        self.old = None
        self.addCleanup(self.cleanup)
        self.pg = LabPostgres(os.environ["LAB_POSTGRES_BIN"], self.root,
                              min_major=18).initialize().start()
        self.assertEqual(self.pg.major, 18)
        self.assertNotEqual(self.pg.port, 5432)
        self.pg.provision(canonical_schema())
        install_lab_fence(self.pg)
        install_lab_checkpoint(self.pg)
        self.writer = self.psycopg.connect(
            self.pg.dsn("lab_writer"), autocommit=True)
        self.ids = tuple(str(uuid.uuid4()) for _ in range(3))
        self.source = "a" * 64
        self.schema = "b" * 64
        with self.writer.cursor() as cursor:
            cursor.execute("SELECT pg_backend_pid()")
            pid = cursor.fetchone()[0]
        start = self.pg.sql(
            "SELECT backend_start FROM pg_catalog.pg_stat_activity "
            f"WHERE pid={pid} AND usename='lab_writer'")
        self.old = dict(owner="unified-system", namespace="unified/lab",
                        generation=1, token=100, backend_pid=pid,
                        backend_start=start)
        self.assertTrue(claim_lab_fence(
            self.pg, owner=self.old["owner"],
            namespace=self.old["namespace"], generation=1, token=100,
            session_id=self.ids[0], instance_id=self.ids[1],
            node_incarnation_id=self.ids[2], source_sha256=self.source,
            schema_sha256=self.schema, backend_pid=pid,
            previous_quiescence_verified=True))

    def cleanup(self):
        if self.writer is not None:
            try:
                self.writer.close()
            except Exception:
                pass
        if self.pg is not None:
            self.pg.stop()
        if hasattr(self, "root") and (self.pg is None or not self.pg.started):
            shutil.rmtree(self.root)

    def _recover(self, **overrides):
        options = dict(old=self.old, streams=(), quiesced=True, max_seconds=120)
        options.update(overrides)
        return recover_exclusive_lab_cluster(self.pg, **options)

    def test_nonmutating_invalid_arguments_denied(self):
        for modified in (
            dict(quiesced=False), dict(max_seconds=1),
            dict(streams=("bad'stream",)),
        ):
            with self.subTest(modified=modified):
                with self.assertRaises(LabAdmissionRejected):
                    self._recover(**modified)
                self.assertEqual(observe_old_lab_backend(self.pg, **self.old),
                                 "STILL_ALIVE")
                self.assertTrue(self.pg.started)

    def test_reject_foreign_pg_type_before_method_dispatch(self):
        class MaliciousPg:
            def __getattribute__(self, name):
                raise AssertionError("FOREIGN_PG_METHOD_CALLED:" + name)
        with self.assertRaisesRegex(LabAdmissionRejected,
                                    "LAB_RECOVERY_PG_TYPE_INVALID"):
            recover_exclusive_lab_cluster(
                MaliciousPg(), old=self.old,
                quiesced=True, max_seconds=180)

    def test_kernel_lock_survives_stop_only_and_recovery(self):
        # A separate interpreter tries to lock the SAME inode, without
        # inheriting the owner's C descriptor. This is a kernel test.
        contained=contain_exclusive_lab_cluster(
            self.pg,old=dict(self.old),quiesced=True,max_seconds=120)
        self.assertEqual(contained["state"],"UNKNOWN")
        path=self.root/".lab-postgres-recovery.lock"
        self.assertTrue(path.is_file())
        code=(
            "import os,sys,fcntl\n"
            "fd=os.open(sys.argv[1],os.O_RDWR)\n"
            "try:\n"
            " fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)\n"
            "except BlockingIOError:\n"
            " sys.exit(77)\n"
            "sys.exit(0)\n"
        )
        outsider=subprocess.run(
            [sys.executable,"-B","-c",code,str(path)],
            capture_output=True,text=True,timeout=10,check=False)
        self.assertEqual(outsider.returncode,77,outsider.stderr)
        receipt=self._recover()
        self.assertFalse(receipt["native_admitted"])
        again=subprocess.run(
            [sys.executable,"-B","-c",code,str(path)],
            capture_output=True,text=True,timeout=10,check=False)
        self.assertEqual(again.returncode,77,again.stderr)

    def test_external_process_lock_denies_c_before_any_stop(self):
        # This process owns the ORIGINAL disposable PG, but an independent
        # LAB child already holds C's exact OS locking region. Recovery
        # must NEVER race the other OS-level owner or signal postmaster.
        from unified_system.lab_pg_recovery import _acquire_cluster_os_lock
        fd=_acquire_cluster_os_lock(self.pg)
        os.close(fd)
        path=self.root/".lab-postgres-recovery.lock"
        code=(
            "import fcntl,os,sys\n"
            "fd=os.open(sys.argv[1],os.O_RDWR)\n"
            "fcntl.flock(fd,fcntl.LOCK_EX)\n"
            "print('C_NATIVE_LOCK_HELD',flush=True)\n"
            "sys.stdin.readline()\n"
        )
        child=subprocess.Popen(
            [sys.executable,"-B","-c",code,str(path)],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,text=True)
        try:
            import select
            ready, _, _ = select.select([child.stdout], [], [], 10)
            self.assertTrue(ready, "C_NATIVE_LOCK_CHILD_START_TIMEOUT")
            self.assertEqual(child.stdout.readline().strip(),
                             "C_NATIVE_LOCK_HELD")
            with self.assertRaisesRegex(
                    LabAdmissionRejected,
                    "LAB_RECOVERY_CROSS_PROCESS_LOCK_BUSY"):
                self._recover()
            self.assertTrue(self.pg.started)
            self.assertEqual(observe_old_lab_backend(
                self.pg,**self.old),"STILL_ALIVE")
        finally:
            if child.poll() is None:
                try:
                    child.stdin.write("end\n")
                    child.stdin.flush()
                    child.wait(timeout=15)
                except (BrokenPipeError, subprocess.TimeoutExpired):
                    # The test may stop only the disposable child it created.
                    child.kill()
                    child.wait(timeout=10)
            child.stdin.close()
            child.stdout.close()
            child.stderr.close()
        receipt=self._recover()
        self.assertFalse(receipt["native_admitted"])

    def test_e_stop_only_then_resume_without_duplicate_stop(self):
        # Future E executor delegates to C's ONE serialized stop-only entry.
        stream = "bybit:BTCUSDT:1m"
        contained=contain_exclusive_lab_cluster(
            self.pg,old=self.old,quiesced=True,max_seconds=120)
        self.assertFalse(self.pg.started)
        self.assertEqual(contained["state"],"UNKNOWN")
        self.assertFalse(contained["old_backend_extinct"])
        receipt=self._recover(streams=(stream,))
        self.assertFalse(receipt["native_admitted"])
        self.assertFalse(receipt["durable_fence_active"])
        self.assertEqual(self.pg.sql(
            "SELECT generation,token,active FROM public.lab_writer_fence"),
            "1|100|f")

    def test_concurrent_containment_and_restart_denied(self):
        from threading import Event,Thread
        entered,release=Event(),Event()
        original=self.pg.stop
        errors=[]
        results=[]
        def blocking_stop(*args,**kwargs):
            entered.set()
            if not release.wait(10):
                raise RuntimeError("LAB_STOP_WORKER_NOT_RELEASED")
            return original(*args,**kwargs)
        def worker():
            try:
                results.append(contain_exclusive_lab_cluster(
                    self.pg,old=self.old,quiesced=True,max_seconds=120))
            except BaseException as error:
                errors.append(error)
        self.pg.stop=blocking_stop
        thread=Thread(target=worker,daemon=True)
        thread.start()
        try:
            self.assertTrue(entered.wait(5))
            with self.assertRaisesRegex(
                    LabAdmissionRejected,"LAB_RECOVERY_REENTRY_OR_POISONED"):
                self._recover()
        finally:
            release.set()
            thread.join(90)
            self.pg.stop=original
        self.assertFalse(thread.is_alive())
        self.assertFalse(errors)
        self.assertEqual(results[0]["state"],"UNKNOWN")
        self.assertFalse(self._recover()["native_admitted"])

    def test_timed_out_stop_poison_blocks_any_restart(self):
        from subprocess import TimeoutExpired
        original=self.pg.stop
        def fake_timeout(*args,**kwargs):
            raise TimeoutExpired(cmd="test-only-owned-pg-stop",timeout=1)
        self.pg.stop=fake_timeout
        try:
            with self.assertRaises(TimeoutExpired):
                contain_exclusive_lab_cluster(
                    self.pg,old=self.old,quiesced=True,max_seconds=120)
        finally:
            self.pg.stop=original
        with self.assertRaisesRegex(LabAdmissionRejected,
                                    "LAB_RECOVERY_REENTRY_OR_POISONED"):
            self._recover()

    def test_recovery_reentry_denied_after_successful_attempt(self):
        self._recover()
        with self.assertRaisesRegex(LabAdmissionRejected,
                                    "LAB_RECOVERY_REENTRY_OR_POISONED"):
            self._recover()

    def test_recovery_wrong_identity_poisoned_and_no_restart(self):
        bad = dict(self.old, token=999)
        with self.assertRaises(LabAdmissionRejected):
            self._recover(old=bad)
        with self.assertRaisesRegex(LabAdmissionRejected,
                                    "LAB_RECOVERY_REENTRY_OR_POISONED"):
            self._recover()

    def test_unknown_commit_conflicting_immutable_row_stays_unverified(self):
        stream="bybit:BTCUSDT:1m"
        symbol="BTCUSDT"
        start_ms=120000
        expected_fp="c"*64
        expected_cid="d"*64
        observed_fp="e"*64
        observed_cid="f"*64
        self.pg.sql(
            "INSERT INTO public.lab_stream_pending("
            "stream_id,symbol,start_ms,fingerprint,content_id,"
            "owner,namespace,generation,token,source_sha256,schema_sha256)"
            f" VALUES ('{stream}','{symbol}',{start_ms},"
            f"'{expected_fp}','{expected_cid}',"
            "'unified-system','unified/lab',1,100,"
            f"'{self.source}','{self.schema}')")
        # Deliberately injected conflicting synthetic LAB row. This is
        # NOT a second Grid writer and does not attest exchange authenticity.
        self.pg.sql(
            "INSERT INTO public.provenance_minutes("
            "fingerprint,content_id,symbol,start_ms,record)"
            f" VALUES ('{observed_fp}','{observed_cid}',"
            f"'{symbol}',{start_ms},"
            f"'{{\"dataset_fingerprint\":\"{observed_fp}\"}}'::jsonb)")
        receipt=self._recover(streams=(stream,))
        outcome=receipt["stream_snapshots"][stream]["immutable_outcome"]
        self.assertEqual(outcome,"CONFLICT")
        self.assertFalse(receipt["native_admitted"])
        self.assertFalse(receipt["trading_authorized"])
        self.assertEqual(self.pg.sql(
            "SELECT generation,token,active FROM public.lab_writer_fence"),
            "1|100|f")

    def test_raw_stopped_postmaster_without_c_witness_denied(self):
        # A foreign/manual stop is not a protected C STOPPED_UNVERIFIED state.
        self.pg.stop()
        self.assertFalse(self.pg.started)
        with self.assertRaisesRegex(LabAdmissionRejected,
                                    "LAB_RECOVERY_STOPPED_WITHOUT_C_EVIDENCE"):
            self._recover()
        self.assertFalse(self.pg.started)

    def test_stopped_old_identity_mutation_denied_before_restart(self):
        contained=contain_exclusive_lab_cluster(
            self.pg,old=dict(self.old),quiesced=True,max_seconds=120)
        self.assertEqual(contained["state"],"UNKNOWN")
        self.assertFalse(self.pg.started)
        forged=dict(self.old, token=self.old["token"]+1)
        with self.assertRaisesRegex(LabAdmissionRejected,
                                    "LAB_RECOVERY_STOPPED_OWNER_MISMATCH"):
            self._recover(old=forged)
        self.assertFalse(self.pg.started)

    def test_different_python_object_same_data_root_denied(self):
        # Demonstrate exact type checking alone does not prove single
        # physical PostgreSQL ownership. No new LabPostgres constructor
        # is invoked (a new legitimate constructor rejects old marker).
        contained=contain_exclusive_lab_cluster(
            self.pg,old=dict(self.old),quiesced=True,max_seconds=120)
        self.assertEqual(contained["state"],"UNKNOWN")
        mirror=object.__new__(LabPostgres)
        mirror.__dict__.update(self.pg.__dict__)
        self.assertIsNot(mirror,self.pg)
        self.assertEqual(mirror.root,self.pg.root)
        with self.assertRaisesRegex(LabAdmissionRejected,
                                    "LAB_RECOVERY_STOPPED_OWNER_MISMATCH"):
            recover_exclusive_lab_cluster(
                mirror,old=dict(self.old),streams=(),quiesced=True,
                max_seconds=120)
        self.assertFalse(self.pg.started)

    def test_unavailable_retained_a_handle_denies_without_stop(self):
        from unittest.mock import patch
        from unified_system import runtime_process
        with patch.object(runtime_process, "RetainedOsProcessWait",
                          side_effect=ValueError("test-only missing OS handle")):
            with self.assertRaisesRegex(
                    LabAdmissionRejected,
                    "LAB_RECOVERY_RETAINED_HANDLE_UNKNOWN"):
                self._recover()
        # The old backend stays alive and no new generation can start.
        self.assertTrue(self.pg.started)
        self.assertEqual(observe_old_lab_backend(self.pg,**self.old),
                         "STILL_ALIVE")
        with self.assertRaises(LabAdmissionRejected):
            self._recover()

    def test_c_backend_start_exact_fence_binding_and_revocation(self):
        from datetime import datetime
        from unified_system.grid_writer_fence_model import WriterLeaseIdentity
        from unified_system.lab_pg_fence import revalidate_lab_fence
        identity=WriterLeaseIdentity(
            owner="unified-system",namespace="unified/lab",
            session_id=self.ids[0],token=100,
            instance_id=self.ids[1],node_incarnation_id=self.ids[2],
            source_sha256=self.source,schema_sha256=self.schema)
        receipt=revalidate_lab_fence(
            self.pg,identity=identity,generation=1,
            backend_pid=self.old["backend_pid"])
        self.assertFalse(receipt["native_writer_admitted"])
        self.assertFalse(receipt["root_consul_admitted"])
        self.assertEqual(
            datetime.fromisoformat(receipt["backend_start"]),
            datetime.fromisoformat(
                self.old["backend_start"].replace(" ","T")))
        self.assertEqual(receipt["backend_pid"],self.old["backend_pid"])
        self._recover()
        with self.assertRaises(LabAdmissionRejected):
            revalidate_lab_fence(
                self.pg,identity=identity,generation=1,
                backend_pid=self.old["backend_pid"])

    def test_native_process_crash_wal_replay_with_immutable_pending_checkpoint(self):
        from unittest.mock import patch
        stream="bybit:BTCUSDT:1m"
        symbol="BTCUSDT"
        ms=240000
        fp="a"*64
        cid="b"*64
        # Synthetic dedicated LAB fixture only, inserted by PG owner for
        # storage durability. NOT an authorized second market-data writer.
        self.pg.sql(
            "INSERT INTO public.provenance_minutes("
            "fingerprint,content_id,symbol,start_ms,record)"
            f" VALUES ('{fp}','{cid}','{symbol}',{ms},"
            f"'{{\"dataset_fingerprint\":\"{fp}\"}}'::jsonb)")
        self.pg.sql(
            "INSERT INTO public.lab_stream_pending("
            "stream_id,symbol,start_ms,fingerprint,content_id,"
            "owner,namespace,generation,token,source_sha256,schema_sha256)"
            f" VALUES ('{stream}','{symbol}',{ms},'{fp}','{cid}',"
            "'unified-system','unified/lab',1,100,"
            f"'{self.source}','{self.schema}')")
        self.pg.sql(
            "INSERT INTO public.lab_stream_checkpoint("
            "stream_id,symbol,cursor_value,source_start_ms,"
            "fingerprint,content_id,owner,namespace,generation,token)"
            f" VALUES ('{stream}','{symbol}',{ms},{ms},"
            f"'{fp}','{cid}','unified-system','unified/lab',1,100)")
        self.assertEqual(read_lab_pending(
            self.pg,stream_id=stream)["content_id"],cid)
        with patch.dict(os.environ,{"LAB_C_PG18_PROCESS_CRASH_TEST":"1"}):
            contained=contain_exclusive_lab_cluster(
                self.pg,old=dict(self.old),quiesced=True,
                max_seconds=180,fault="PROCESS_CRASH_TEST")
            self.assertEqual(contained["state"],"UNKNOWN")
            self.assertFalse(contained["old_backend_extinct"])
            self.assertFalse(self.pg.started)
            recovered=self._recover(streams=(stream,),max_seconds=250)
        self.assertEqual(recovered["wal_recovery"],
                         "LAB_PROCESS_CRASH_WAL_REPLAY_LOG_VERIFIED")
        self.assertFalse(recovered["native_admitted"])
        snap=recovered["stream_snapshots"][stream]
        self.assertEqual(snap["immutable_outcome"],"MATCH")
        self.assertEqual(snap["pending"]["fingerprint"],fp)
        self.assertEqual(snap["pending"]["content_id"],cid)
        self.assertEqual(snap["checkpoint"]["fingerprint"],fp)
        self.assertEqual(snap["checkpoint"]["content_id"],cid)
        self.assertEqual(snap["checkpoint"]["start_ms"],ms)
        self.assertEqual(self.pg.sql(
            "SELECT generation,token,active FROM public.lab_writer_fence"),
            "1|100|f")
        self.assertEqual(self.pg.sql(
            f"SELECT count(*) FROM public.provenance_minutes"
            f" WHERE symbol='{symbol}' AND start_ms={ms}"),"1")

    def test_cluster_stop_restart_durable_highwater_pending_and_cas(self):
        import uuid
        # A durable pending marker must remain unresolved after cluster
        # restart and old fence revocation; no blind writer retry.
        stream = "bybit:BTCUSDT:1m"
        symbol, start_ms = "BTCUSDT", 60000
        fp, cid = "c"*64, "d"*64
        self.pg.sql(
            "INSERT INTO public.lab_stream_pending("
            "stream_id,symbol,start_ms,fingerprint,content_id,"
            "owner,namespace,generation,token,source_sha256,schema_sha256)"
            f" VALUES ('{stream}','{symbol}',{start_ms},'{fp}','{cid}',"
            "'unified-system','unified/lab',1,100,"
            f"'{self.source}','{self.schema}')")
        self.assertEqual(read_lab_pending(self.pg, stream_id=stream)["fingerprint"], fp)
        receipt=self._recover(streams=(stream,))
        self.assertEqual(receipt["schema"], "c-isolated-pg18-recovery-diagnostic.v2")
        self.assertEqual(receipt["wal_recovery"],"CLEAN_SHUTDOWN_ONLY")
        self.assertEqual(receipt["old_backend_pid"], self.old["backend_pid"])
        self.assertIs(receipt["native_admitted"],False)
        self.assertIs(receipt["trading_authorized"],False)
        self.assertEqual(receipt["stream_snapshots"][stream]["pending"]["fingerprint"], fp)
        self.assertEqual(receipt["stream_snapshots"][stream]["immutable_outcome"],"MISSING")
        self.assertIsNone(receipt["stream_snapshots"][stream]["checkpoint"])
        self.assertEqual(self.pg.sql(
            "SELECT generation,token,active FROM public.lab_writer_fence"),
            "1|100|f")
        with self.assertRaises(LabAdmissionRejected):
            self._recover(streams=(stream,))
        new=self.psycopg.connect(self.pg.dsn("lab_writer"),autocommit=True)
        self.addCleanup(new.close)
        with new.cursor() as cur:
            cur.execute("SELECT pg_backend_pid()")
            new_backend=cur.fetchone()[0]
        with self.assertRaises(LabAdmissionRejected):
            claim_lab_fence(
                self.pg, owner="unified-system",namespace="unified/lab",
                generation=2,token=100,session_id=str(uuid.uuid4()),
                instance_id=str(uuid.uuid4()),
                node_incarnation_id=str(uuid.uuid4()),
                source_sha256=self.source,schema_sha256=self.schema,
                backend_pid=new_backend,previous_quiescence_verified=True)
        self.assertTrue(claim_lab_fence(
            self.pg,owner="unified-system",namespace="unified/lab",
            generation=2,token=101,session_id=str(uuid.uuid4()),
            instance_id=str(uuid.uuid4()),
            node_incarnation_id=str(uuid.uuid4()),
            source_sha256=self.source,schema_sha256=self.schema,
            backend_pid=new_backend,previous_quiescence_verified=True))
        self.assertEqual(self.pg.sql(
            "SELECT generation,token,active FROM public.lab_writer_fence"),
            "2|101|t")


if __name__=="__main__":
    unittest.main()
