"""C ROUND14: separate native PostgreSQL18 recovery fault lane.

Only a new, isolated, marker-owned non-5432 disposable cluster is touched.
The test's Root quiescence flag is NOT trusted production authorization.
"""
import os
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
            thread.join(15)
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
        self.assertEqual(receipt["old_backend_pid"], self.old["backend_pid"])
        self.assertIs(receipt["native_admitted"],False)
        self.assertIs(receipt["trading_authorized"],False)
        self.assertEqual(receipt["stream_snapshots"][stream]["pending"]["fingerprint"], fp)
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
