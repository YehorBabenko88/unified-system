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
    install_lab_fence, claim_lab_fence, observe_old_lab_backend,
    revoke_lab_fence)
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
        # Retain the original C-locked object even if initdb fails before
        # initialize() returns. Cleanup must never delete an unverified root.
        self.pg = LabPostgres(os.environ["LAB_POSTGRES_BIN"], self.root,
                              min_major=18)
        self.pg.initialize()
        self.pg.start()
        self.assertEqual(self.pg.major, 18)
        self.assertNotEqual(self.pg.port, 5432)
        self.pg.provision(canonical_schema())
        install_lab_fence(self.pg)
        install_lab_checkpoint(self.pg)
        self.writer = self.psycopg.connect(
            self.pg.dsn("lab_writer"), autocommit=True)
        self.ids = tuple(str(uuid.uuid4()) for _ in range(3))
        # A real Consul 2.1 ID enters the original native C-owned claim
        # during this one focused test; no second lifecycle or owner is made.
        if self._testMethodName == (
                "test_native_consul_210_exact_session_sql_write_revoke_and_denial"):
            self.ids = ("4a91bb79-c488-1086-0664-30ccbc028eda",
                        self.ids[1], self.ids[2])
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
        if self.pg is not None:
            from unified_system import lab_pg_recovery as c
            # An unmodified, still-live fixture has no C state yet.
            # Contain/recover it through the SAME original C owner instead
            # of bypassing the guarded pg.stop() with raw pg_ctl or SIGKILL.
            if self.pg.started and self.old is not None:
                root=c._resource(self.pg)
                if root not in c._STATES:
                    try:
                        self._recover()
                    except LabAdmissionRejected:
                        # Even a denied recovery records POISONED with the
                        # exact original C worker/OS lock for safe teardown.
                        pass
            c._dispose_native_pg18_fixture(self.pg)
        if self.writer is not None:
            self.writer.close()
        if hasattr(self, "root"):
            # Never delete a root until C verified its old kernel process,
            # original lock and loopback listener are extinct.
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

    def test_native_sql_commit_linearizes_before_fence_revoke(self):
        # Actual PostgreSQL18 row lock, not a fake E operation permit.
        # A B-owned write that already holds FOR UPDATE either commits
        # before C owner SQL revoke, or it is rejected by the SQL fence.
        # Remote Consul lease expiry is NOT covered by this SQL-only test.
        import json
        from unified_system.lab_simulation_admission import LabAdmissionRejected
        resource="grid-market-data-primary"
        symbol="BTCUSDT"
        start_ms=900000
        fingerprint="f"*64
        content_id="e"*64
        record=json.dumps({"dataset_fingerprint":fingerprint})
        query=(
            "SELECT public.lab_fenced_insert("
            "%s::text,%s::text,%s::bigint,%s::bigint,"
            "%s::uuid,%s::uuid,%s::uuid,"
            "%s::text,%s::text,%s::text,%s::text,%s::text,"
            "%s::bigint,%s::jsonb)"
        )
        args=(self.old["owner"],self.old["namespace"],1,100,
              *self.ids,self.source,self.schema,
              fingerprint,content_id,symbol,start_ms,record)
        with self.writer.transaction():
            with self.writer.cursor() as cursor:
                cursor.execute(query,args)
            # A new owner SQL session must not observe uncommitted rows.
            self.assertEqual(self.pg.sql(
                "SELECT count(*) FROM public.provenance_minutes "
                f"WHERE symbol='{symbol}' AND start_ms={start_ms}"),"0")
            # Revoke shares the SAME fence row and fails on lock timeout;
            # it cannot slip past the in-flight writer's FOR UPDATE lock.
            # PostgreSQL sets lock_timeout per statement. A single
            # independent owner connection attempts the same row while B's
            # original writer transaction still holds FOR UPDATE.
            # psycopg's transaction failure must roll back ONLY this
            # independent connection, not the original writer transaction.
            with self.psycopg.connect(
                    host="127.0.0.1", port=self.pg.port,
                    dbname=self.pg.database, user="lab_owner",
                    password=self.pg.passwords["lab_owner"],
                    autocommit=True) as revoker:
                with revoker.cursor() as cursor:
                    cursor.execute("SET lock_timeout='300ms'")
                    with self.assertRaisesRegex(
                            self.psycopg.errors.LockNotAvailable,
                            "lock timeout"):
                        cursor.execute(
                            "UPDATE public.lab_writer_fence "
                            "SET active=false "
                            "WHERE resource_id=%s "
                            "AND generation=1 AND token=100 "
                            "RETURNING generation",(resource,))
            self.assertEqual(self.pg.sql(
                "SELECT generation,token,active "
                "FROM public.lab_writer_fence"),
                "1|100|t")
        # Exiting the original writer transaction is the commit boundary.
        self.assertEqual(self.pg.sql(
            "SELECT count(*) FROM public.provenance_minutes "
            f"WHERE symbol='{symbol}' AND start_ms={start_ms}"),"1")
        # A wrong original backend incarnation cannot revoke this writer.
        with self.assertRaisesRegex(
                LabAdmissionRejected, "LAB_FENCE_REVOKE_UNVERIFIED"):
            revoke_lab_fence(
                self.pg, owner=self.old["owner"],
                namespace=self.old["namespace"], generation=1, token=100,
                backend_pid=self.old["backend_pid"] + 1,
                backend_start=self.old["backend_start"])
        self.assertEqual(self.pg.sql(
            "SELECT generation,token,active "
            "FROM public.lab_writer_fence"), "1|100|t")
        # Exact owner API now runs a separate durable inactive readback.
        self.assertTrue(revoke_lab_fence(
            self.pg, owner=self.old["owner"],
            namespace=self.old["namespace"], generation=1, token=100,
            backend_pid=self.old["backend_pid"],
            backend_start=self.old["backend_start"]))
        self.assertEqual(self.pg.sql(
            "SELECT generation,token,active "
            "FROM public.lab_writer_fence"),"1|100|f")
        with self.assertRaisesRegex(self.psycopg.Error,
                                    "LAB_FENCE_STALE_OR_FOREIGN_WRITER"):
            with self.writer.cursor() as cursor:
                cursor.execute(query,(*args[:-5],
                                     "d"*64,"c"*64,symbol,
                                     start_ms+60000,record))
        self.assertEqual(self.pg.sql(
            "SELECT count(*) FROM public.provenance_minutes "
            f"WHERE symbol='{symbol}'"),"1")

    def test_native_consul_210_exact_session_sql_write_revoke_and_denial(self):
        """Native C-owned PostgreSQL 18: real NCS session + 14-arg SQL + revoke.

        No Consul lease is created or claimed here. This only proves the
        resource-side SQL accepts an exact server-observed ID, and an owned
        recovery can durably revoke it after the original backend is extinct.
        """
        import json
        from unified_system.lab_pg_fence import _id

        actual = "4a91bb79-c488-1086-0664-30ccbc028eda"
        self.assertEqual(self.ids[0], actual)
        self.assertEqual(_id(actual, consul_session=True), actual)
        self.assertEqual(self.pg.sql(
            "SELECT session_id::text,active FROM public.lab_writer_fence"),
            actual + "|t")
        params = (self.old["owner"], self.old["namespace"], 1, 100,
                  *self.ids, self.source, self.schema,
                  "1" * 64, "2" * 64, "BTCUSDT", 1200000,
                  json.dumps({"dataset_fingerprint": "1" * 64}))
        sql = ("SELECT public.lab_fenced_insert("
               "%s::text,%s::text,%s::bigint,%s::bigint,"
               "%s::uuid,%s::uuid,%s::uuid,"
               "%s::text,%s::text,%s::text,%s::text,%s::text,"
               "%s::bigint,%s::jsonb)")
        self.assertEqual(len(params), 14)
        with self.writer.cursor() as cur:
            cur.execute(sql, params)
        self.assertEqual(self.pg.sql(
            "SELECT count(*) FROM public.provenance_minutes "
            "WHERE fingerprint='" + "1" * 64 + "'"), "1")
        # The original C stop/recovery lane, not a raw pg.stop/start, proves
        # backend extinction and invokes the canonical exact six-field
        # revoke with independent durable inactive readback.
        receipt = self._recover()
        self.assertFalse(receipt["native_admitted"])
        self.assertFalse(receipt["root_consul_admitted"])
        self.assertFalse(receipt["durable_fence_active"])
        self.assertEqual(self.pg.sql(
            "SELECT session_id::text,generation,token,active "
            "FROM public.lab_writer_fence"), actual + "|1|100|f")
        self.assertEqual(self.pg.sql(
            "SELECT count(*) FROM public.provenance_minutes"), "1")
        # Old session must remain denied even when an unrelated writer
        # reconnects after the native C-controlled recovery.
        with self.psycopg.connect(self.pg.dsn("lab_writer"),
                                  autocommit=True) as stale:
            with self.assertRaises(self.psycopg.Error):
                with stale.cursor() as cur:
                    cur.execute(sql, (*params[:9], "3" * 64, "4" * 64,
                                      "BTCUSDT", 1260000,
                                      json.dumps({"dataset_fingerprint": "3" * 64})))
        self.assertEqual(self.pg.sql(
            "SELECT count(*) FROM public.provenance_minutes"), "1")

    def test_native_consul_session_invalid_shape_fails_without_mutation(self):
        """Reject malformed/noncanonical C SQL sessions before claim."""
        from unified_system.lab_pg_fence import _id
        real = "4a91bb79-c488-1086-0664-30ccbc028eda"
        self.assertEqual(_id(real, consul_session=True), real)
        before = self.pg.sql(
            "SELECT generation,token,session_id,active "
            "FROM public.lab_writer_fence")
        for invalid in (real.upper(), "opaque-not-uuid",
                        "{" + real + "}", real.replace("-", ""),
                        real + " "):
            with self.subTest(invalid=invalid):
                with self.assertRaises(LabAdmissionRejected):
                    claim_lab_fence(
                        self.pg, owner=self.old["owner"],
                        namespace=self.old["namespace"],
                        generation=2, token=101, session_id=invalid,
                        instance_id=self.ids[1],
                        node_incarnation_id=self.ids[2],
                        source_sha256=self.source,
                        schema_sha256=self.schema,
                        backend_pid=self.old["backend_pid"],
                        previous_quiescence_verified=True)
        self.assertEqual(self.pg.sql(
            "SELECT generation,token,session_id,active "
            "FROM public.lab_writer_fence"), before)

    def test_sql_commit_after_simulated_external_lease_loss_is_not_root_proof(self):
        """Native PostgreSQL commit; EXTERNAL lease loss is SIMULATED only.

        An external Consul TTL does not participate in PostgreSQL's SQL
        transaction. Do not treat this experiment as actual Consul expiry or
        wire-level COMMIT reply loss. No Root admission is granted.
        """
        import json
        params = (self.old["owner"], self.old["namespace"], 1, 100,
                  *self.ids, self.source, self.schema,
                  "8" * 64, "9" * 64, "BTCUSDT", 1320000,
                  json.dumps({"dataset_fingerprint": "8" * 64}))
        sql = ("SELECT public.lab_fenced_insert("
               "%s::text,%s::text,%s::bigint,%s::bigint,"
               "%s::uuid,%s::uuid,%s::uuid,"
               "%s::text,%s::text,%s::text,%s::text,%s::text,"
               "%s::bigint,%s::jsonb)")
        with self.writer.transaction():
            with self.writer.cursor() as cur:
                cur.execute(sql, params)
            # The only synthetic step: E's remote Consul lease is considered
            # expired while C's original SQL row is still held FOR UPDATE.
            simulated_consul_lease_current = False
            self.assertFalse(simulated_consul_lease_current)
            self.assertEqual(self.pg.sql(
                "SELECT count(*) FROM public.provenance_minutes "
                "WHERE fingerprint='" + "8" * 64 + "'"), "0")
        # SQL can still COMMIT after this simulated external event. Thus C's
        # row lock is never a substitute for E's independent Root transfer
        # block, backend extinction and durable exact revocation.
        self.assertEqual(self.pg.sql(
            "SELECT count(*) FROM public.provenance_minutes "
            "WHERE fingerprint='" + "8" * 64 + "'"), "1")
        self.assertEqual(self.pg.sql(
            "SELECT generation,token,active FROM public.lab_writer_fence"),
            "1|100|t")
        self.assertFalse(simulated_consul_lease_current)
        self.assertEqual(observe_old_lab_backend(
            self.pg, **self.old), "STILL_ALIVE")

    def test_native_lost_commit_wire_reply_reconciles_exact_pending_after_wal(self):
        """Real PG18 COMMIT with server reply deliberately lost on loopback.

        This deliberately intercepts one TEST-ONLY PostgreSQL connection
        after authentication, not Consul and not a production SQL writer.
        Seeing a committed row does not acknowledge delivery: the pending
        marker survives until a separate authenticated recovery can decide.
        """
        import json
        import select
        import socket
        import threading
        import time
        import uuid
        from unittest.mock import patch

        # Retire the original test backend with C's six-field, durable
        # owner revoke. Do not recycle a live backend PID or its identity.
        original = dict(self.old)
        self.assertTrue(revoke_lab_fence(self.pg, **original))
        self.writer.close()
        self.writer = None
        self.assertEqual(observe_old_lab_backend(self.pg, **original),
                         "EXTINCT")

        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(10)
        stop_relay = threading.Event()
        intercept_commit = threading.Event()
        commit_forwarded = threading.Event()
        reply_discarded = threading.Event()
        expected_backend_shutdown = threading.Event()
        relay_errors = []
        relay_sockets = []

        def relay_once():
            front = back = None
            try:
                front, _ = listener.accept()
                back = socket.create_connection(("127.0.0.1", self.pg.port),
                                                timeout=5)
                relay_sockets.extend((front, back))
                # The fixture is authenticated before issuing COMMIT.
                # Parse PG v3 message frames rather than dropping an arbitrary
                # packet; the SQL text is not authorization.
                client_buffer = b""
                server_buffer = b""
                commit_phase = False
                while not stop_relay.is_set():
                    ready, _, _ = select.select((front, back), (), (), 0.1)
                    for sock in ready:
                        packet = sock.recv(65536)
                        if not packet:
                            return
                        if not intercept_commit.is_set():
                            # Startup packets are length-prefixed with NO type
                            # byte; AUTH can include protocol negotiation.
                            # Relay all pre-armed traffic transparently.
                            if sock is front:
                                back.sendall(packet)
                            else:
                                front.sendall(packet)
                            continue
                        if sock is front:
                            client_buffer += packet
                            while len(client_buffer) >= 5:
                                size = int.from_bytes(client_buffer[1:5], "big")
                                if size < 4 or size > 16 * 1024 * 1024:
                                    raise RuntimeError("LAB_PROXY_CLIENT_FRAME_INVALID")
                                frame_end = 1 + size
                                if len(client_buffer) < frame_end:
                                    break
                                frame = client_buffer[:frame_end]
                                client_buffer = client_buffer[frame_end:]
                                if (frame[:1] == b"Q" and
                                        frame[5:] in (b"COMMIT\x00",
                                                      b"COMMIT;\x00")):
                                    commit_phase = True
                                    back.sendall(frame)
                                    commit_forwarded.set()
                                else:
                                    back.sendall(frame)
                        else:
                            server_buffer += packet
                            while len(server_buffer) >= 5:
                                size = int.from_bytes(server_buffer[1:5], "big")
                                if size < 4 or size > 16 * 1024 * 1024:
                                    raise RuntimeError("LAB_PROXY_SERVER_FRAME_INVALID")
                                frame_end = 1 + size
                                if len(server_buffer) < frame_end:
                                    break
                                frame = server_buffer[:frame_end]
                                server_buffer = server_buffer[frame_end:]
                                if commit_phase:
                                    reply_discarded.set()
                                else:
                                    front.sendall(frame)
            except (OSError, RuntimeError) as exc:
                # A deliberately crashed PG18 backend may reset the
                # transport; only unexpected pre-crash relay errors fail.
                if (not stop_relay.is_set()
                        and not expected_backend_shutdown.is_set()):
                    relay_errors.append(repr(exc))
            finally:
                for sock in (front, back):
                    if sock is not None:
                        try:
                            sock.close()
                        except OSError:
                            pass

        relay_thread = threading.Thread(target=relay_once, daemon=True)
        relay_thread.start()
        commit_thread = None
        try:
            self.writer = self.psycopg.connect(
                host="127.0.0.1",
                port=listener.getsockname()[1],
                dbname=self.pg.database, user="lab_writer",
                password=self.pg.passwords["lab_writer"],
                sslmode="disable", connect_timeout=5)
            with self.writer.cursor() as cur:
                cur.execute("SELECT pg_backend_pid()")
                owned_backend = cur.fetchone()[0]
            self.writer.commit()
            new_ids = tuple(str(uuid.uuid4()) for _ in range(3))
            started = self.pg.sql(
                "SELECT backend_start FROM pg_catalog.pg_stat_activity "
                f"WHERE pid={owned_backend} AND usename='lab_writer'")
            self.assertTrue(started)
            self.assertTrue(claim_lab_fence(
                self.pg, owner=original["owner"],
                namespace=original["namespace"], generation=2, token=101,
                session_id=new_ids[0], instance_id=new_ids[1],
                node_incarnation_id=new_ids[2],
                source_sha256=self.source, schema_sha256=self.schema,
                backend_pid=owned_backend,
                previous_quiescence_verified=True))
            self.old = dict(original, generation=2, token=101,
                            backend_pid=owned_backend, backend_start=started)

            # Durable four-field pending evidence BEFORE the uncertain write.
            stream, symbol, minute = "bybit:BTCUSDT:1m", "BTCUSDT", 1860000
            fingerprint, content_id = "6" * 64, "7" * 64
            self.pg.sql(
                "INSERT INTO public.lab_stream_pending("
                "stream_id,symbol,start_ms,fingerprint,content_id,"
                "owner,namespace,generation,token,source_sha256,schema_sha256)"
                f" VALUES ('{stream}','{symbol}',{minute},"
                f"'{fingerprint}','{content_id}',"
                "'unified-system','unified/lab',2,101,"
                f"'{self.source}','{self.schema}')")
            query = ("SELECT public.lab_fenced_insert("
                     "%s::text,%s::text,%s::bigint,%s::bigint,"
                     "%s::uuid,%s::uuid,%s::uuid,"
                     "%s::text,%s::text,%s::text,%s::text,%s::text,"
                     "%s::bigint,%s::jsonb)")
            args = (original["owner"], original["namespace"], 2, 101,
                    *new_ids, self.source, self.schema,
                    fingerprint, content_id, symbol, minute,
                    json.dumps({"dataset_fingerprint": fingerprint}))
            self.assertEqual(len(args), 14)
            with self.writer.cursor() as cur:
                cur.execute(query, args)
            self.assertEqual(self.pg.sql(
                "SELECT count(*) FROM public.provenance_minutes"
                f" WHERE fingerprint='{fingerprint}'"), "0")

            commit_errors = []
            commit_done = threading.Event()

            def send_commit_without_receiving_reply():
                try:
                    self.writer.commit()
                except Exception as exc:
                    commit_errors.append(type(exc).__name__)
                finally:
                    commit_done.set()

            # All startup/authentication, SQL INSERT and reply traffic
            # has completed. Only the next standalone COMMIT wire message
            # is framed; no raw StartupMessage is treated as a v3 frame.
            intercept_commit.set()
            commit_thread = threading.Thread(
                target=send_commit_without_receiving_reply, daemon=True)
            commit_thread.start()
            deadline = time.monotonic() + 15
            committed = False
            while time.monotonic() < deadline:
                if self.pg.sql(
                    "SELECT count(*) FROM public.provenance_minutes"
                    f" WHERE symbol='{symbol}' AND start_ms={minute}"
                    f" AND fingerprint='{fingerprint}'"
                    f" AND content_id='{content_id}'") == "1":
                    committed = True
                    break
                time.sleep(0.1)
            self.assertTrue(committed, "LAB_COMMIT_NOT_DURABLY_OBSERVED")
            self.assertTrue(commit_forwarded.wait(5),
                            "LAB_COMMIT_FRAME_NOT_FORWARDED")
            self.assertTrue(reply_discarded.wait(5),
                            "LAB_COMMIT_REPLY_DROP_NOT_OBSERVED")
            self.assertFalse(commit_done.is_set(),
                             "LAB_COMMIT_ACK_WAS_NOT_LOST")
            self.assertEqual(observe_old_lab_backend(
                self.pg, **self.old), "STILL_ALIVE")

            # C retains original OS witness, crashes ONLY its disposable PG,
            # restarts through its sole recovery and reads independent WAL.
            expected_backend_shutdown.set()
            with patch.dict(os.environ,
                            {"LAB_C_PG18_PROCESS_CRASH_TEST": "1"}):
                contained = contain_exclusive_lab_cluster(
                    self.pg, old=dict(self.old), quiesced=True,
                    max_seconds=180, fault="PROCESS_CRASH_TEST")
                self.assertEqual(contained["state"], "UNKNOWN")
                recovered = self._recover(
                    streams=(stream,), max_seconds=250)
            commit_thread.join(timeout=10)
            self.assertFalse(commit_thread.is_alive(),
                             "LAB_COMMIT_CLIENT_NOT_DISCONNECTED")
            self.assertTrue(commit_errors,
                            "LAB_LOST_REPLY_SHOULD_NOT_ACKNOWLEDGE_COMMIT")
            self.assertEqual(recovered["wal_recovery"],
                             "LAB_PROCESS_CRASH_WAL_REPLAY_LOG_VERIFIED")
            self.assertFalse(recovered["native_admitted"])
            self.assertFalse(recovered["trading_authorized"])
            snap = recovered["stream_snapshots"][stream]
            self.assertEqual(snap["immutable_outcome"], "MATCH")
            self.assertEqual(snap["pending"]["symbol"], symbol)
            self.assertEqual(snap["pending"]["start_ms"], minute)
            self.assertEqual(snap["pending"]["fingerprint"], fingerprint)
            self.assertEqual(snap["pending"]["content_id"], content_id)
            self.assertIsNone(snap["checkpoint"])
            self.assertEqual(self.pg.sql(
                "SELECT generation,token,active FROM public.lab_writer_fence"),
                "2|101|f")
            self.assertEqual(self.pg.sql(
                "SELECT count(*) FROM public.provenance_minutes"
                f" WHERE symbol='{symbol}' AND start_ms={minute}"), "1")
            self.assertFalse(relay_errors, relay_errors)
        finally:
            stop_relay.set()
            try:
                listener.close()
            except OSError:
                pass
            for sock in relay_sockets:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            relay_thread.join(timeout=5)
            if commit_thread is not None:
                commit_thread.join(timeout=5)

    def test_owner_process_death_releases_advisory_lock_but_not_root_admission(self):
        # A dedicated throw-away child dies AFTER C's original lock and
        # marker, but BEFORE initdb/start. No PostgreSQL process is created.
        # The kernel releases flock on death; the permanent original owner
        # marker must still prevent a second LabPostgres constructor.
        extra=Path(tempfile.mkdtemp(prefix="c-round14-recovery-"))
        extra.chmod(0o700)
        child_source=(
            "import os,sys\n"
            "from unified_system.lab_postgres import LabPostgres\n"
            "from unified_system import lab_pg_recovery as c\n"
            "pg=LabPostgres(sys.argv[1],sys.argv[2],min_major=18)\n"
            "c._claim_initial_lab_cluster(pg)\n"
            "print('C_ORIGINAL_BOOTSTRAP_LOCKED',flush=True)\n"
            "os._exit(19)\n"
        )
        try:
            result=subprocess.run(
                [sys.executable,"-B","-c",child_source,
                 os.environ["LAB_POSTGRES_BIN"],str(extra)],
                capture_output=True,text=True,timeout=25,check=False)
            self.assertEqual(result.returncode,19,result.stderr)
            self.assertIn("C_ORIGINAL_BOOTSTRAP_LOCKED",result.stdout)
            self.assertFalse((extra/"pgdata").exists())
            marker=extra/".lab-postgres-owner"
            self.assertTrue(marker.is_file())
            fd=os.open(extra/".lab-postgres-recovery.lock",os.O_RDWR)
            try:
                import fcntl
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            finally:
                os.close(fd)
            # Freed kernel lock is not reissued physical/Root ownership.
            with self.assertRaisesRegex(LabAdmissionRejected,
                                         "LAB_PG_ROOT_USED"):
                LabPostgres(os.environ["LAB_POSTGRES_BIN"],extra,min_major=18)
        finally:
            # The child has exited, no initdb was invoked and no postmaster
            # exists. Only its own disposable, uninitialized root is removed.
            if not (extra/"pgdata").exists():
                shutil.rmtree(extra)

    def test_initialization_failure_keeps_kernel_lock_until_safe_abort(self):
        # Real native OS file lock, fault injected BEFORE the initdb child is
        # launched. This is not a simulated WAL-replay or power-loss test.
        from unittest.mock import patch
        from unified_system import lab_pg_recovery as c
        extra=Path(tempfile.mkdtemp(prefix="c-round14-recovery-"))
        extra.chmod(0o700)
        original=LabPostgres(os.environ["LAB_POSTGRES_BIN"],extra,min_major=18)
        try:
            with patch.object(Path,"mkdir",
                              side_effect=PermissionError("C_NATIVE_PRE_INITDB_FAULT")):
                with self.assertRaisesRegex(PermissionError,
                                            "C_NATIVE_PRE_INITDB_FAULT"):
                    original.initialize()
            self.assertEqual(original._initdb_phase,"NOT_STARTED")
            locked=extra/".lab-postgres-recovery.lock"
            self.assertTrue(locked.is_file())
            code=(
                "import fcntl,os,sys\n"
                "fd=os.open(sys.argv[1],os.O_RDWR)\n"
                "try:\n"
                " fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)\n"
                "except BlockingIOError:\n"
                " sys.exit(77)\n"
                "sys.exit(0)\n"
            )
            outsider=subprocess.run(
                [sys.executable,"-B","-c",code,str(locked)],
                capture_output=True,text=True,timeout=10,check=False)
            self.assertEqual(outsider.returncode,77,outsider.stderr)
            original._initdb_phase="RUNNING_OR_EXIT_UNKNOWN"
            with self.assertRaisesRegex(
                    LabAdmissionRejected,"LAB_NATIVE_PG_BOOTSTRAP_ABORT_UNKNOWN"):
                c._dispose_native_pg18_fixture(original)
            self.assertTrue(locked.is_file())
            original._initdb_phase="NOT_STARTED"
            self.assertTrue(c._dispose_native_pg18_fixture(original))
        finally:
            # Never remove unknown/actively owned OS resources in cleanup.
            root_key=(*original._root_identity,str(extra.resolve(strict=True)))
            if root_key not in c._BOOTSTRAP_ROOTS and root_key not in c._STATES:
                shutil.rmtree(extra)

    def test_direct_lifecycle_entrypoints_rejected_without_c_lock(self):
        # No caller, even with the LabPostgres instance, may bypass C's
        # original OS-backed resource owner after first startup.
        for operation in (lambda: self.pg.stop(),
                          lambda: self.pg.crash(),
                          lambda: self.pg.start()):
            with self.subTest(operation=operation):
                with self.assertRaises(LabAdmissionRejected):
                    operation()
                self.assertTrue(self.pg.started)
                self.assertEqual(observe_old_lab_backend(
                    self.pg, **self.old), "STILL_ALIVE")

    def test_owner_marker_inode_replacement_denied(self):
        # Exact same nonce at a newly created inode is NOT the original
        # owner marker. Preserve original marker for safe fixture teardown.
        path=self.pg._marker
        prior=self.root/".c-native-original-marker"
        nonce=path.read_text(encoding="ascii")
        os.replace(path,prior)
        try:
            path.write_text(nonce,encoding="ascii")
            path.chmod(0o600)
            with self.assertRaisesRegex(LabAdmissionRejected,
                                         "LAB_PG_OWNERSHIP_LOST"):
                self._recover()
            self.assertTrue(self.pg.started)
        finally:
            path.unlink(missing_ok=True)
            os.replace(prior,path)
        self.assertFalse(self._recover()["native_admitted"])

    def test_lock_inode_replacement_denies_restart(self):
        contained=contain_exclusive_lab_cluster(
            self.pg,old=self.old,quiesced=True,max_seconds=120)
        self.assertEqual(contained["state"],"UNKNOWN")
        path=self.root/".lab-postgres-recovery.lock"
        prior=self.root/".c-native-original-lock"
        payload=path.read_bytes()
        os.replace(path,prior)
        try:
            path.write_bytes(payload)
            path.chmod(0o600)
            with self.assertRaisesRegex(LabAdmissionRejected,
                                         "LAB_RECOVERY_OS_LOCK_LOST"):
                self._recover()
            self.assertFalse(self.pg.started)
        finally:
            path.unlink(missing_ok=True)
            os.replace(prior,path)
        self.assertFalse(self._recover()["native_admitted"])

    def test_same_inode_reopened_fd_denied_even_with_original_nonce(self):
        from unified_system import lab_pg_recovery as c
        contained=contain_exclusive_lab_cluster(
            self.pg,old=self.old,quiesced=True,max_seconds=120)
        self.assertEqual(contained["state"],"UNKNOWN")
        root=c._resource(self.pg)
        state=c._STATES[root]
        original_fd=state.lock_fd
        retained=os.dup(original_fd)
        path=self.root/".lab-postgres-recovery.lock"
        os.close(original_fd)
        replacement=os.open(path,os.O_RDWR)
        try:
            if replacement != original_fd:
                os.dup2(replacement,original_fd,inheritable=False)
            with self.assertRaisesRegex(LabAdmissionRejected,
                      "LAB_RECOVERY_OS_LOCK_DESCRIPTION_CHANGED"):
                self._recover()
            self.assertFalse(self.pg.started)
        finally:
            if replacement != original_fd:
                os.close(replacement)
            # Restore the original open file description, which was kept
            # kernel-locked by both the witness and the temporary duplicate.
            os.dup2(retained,original_fd,inheritable=False)
            os.close(retained)
        self.assertFalse(self._recover()["native_admitted"])

    def test_fork_inherits_fd_but_c_worker_rejected(self):
        if not hasattr(os,"fork"):
            self.fail("C_NATIVE_POSIX_FORK_REQUIRED")
        contain_exclusive_lab_cluster(
            self.pg,old=self.old,quiesced=True,max_seconds=120)
        child=os.fork()
        if child==0:
            try:
                self.pg.start(timeout=10)
            except LabAdmissionRejected:
                os._exit(77)
            except BaseException:
                os._exit(78)
            os._exit(0)
        waited,status=os.waitpid(child,0)
        self.assertEqual(waited,child)
        self.assertTrue(os.WIFEXITED(status))
        self.assertEqual(os.WEXITSTATUS(status),77)
        self.assertFalse(self._recover()["native_admitted"])

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

    def test_external_process_cannot_preempt_original_bootstrap_lock(self):
        # C owns one original OS lock since initdb, not merely once
        # recovery starts. A different Python interpreter cannot preempt it.
        path=self.root/".lab-postgres-recovery.lock"
        self.assertTrue(path.is_file())
        code=(
            "import fcntl,os,sys\n"
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
        self.assertTrue(self.pg.started)
        self.assertEqual(observe_old_lab_backend(
            self.pg,**self.old),"STILL_ALIVE")
        self.assertFalse(self._recover()["native_admitted"])

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
        from threading import Event, Thread
        entered, release = Event(), Event()
        original = self.pg.stop
        contender_errors = []
        contender_returns = []

        def blocking_stop(*args, **kwargs):
            entered.set()
            if not release.wait(10):
                raise RuntimeError("LAB_STOP_WORKER_NOT_RELEASED")
            return original(*args, **kwargs)

        def contender():
            if not entered.wait(5):
                contender_errors.append(
                    RuntimeError("LAB_COMPETITOR_NO_OWNER"))
                release.set()
                return
            try:
                contender_returns.append(self._recover())
            except BaseException as exc:
                contender_errors.append(exc)
            finally:
                # Unblock the ACTUAL C owner after challenger returns;
                # the rejected challenger must not poison original state.
                release.set()

        competing_thread = Thread(target=contender, daemon=True)
        self.pg.stop = blocking_stop
        competing_thread.start()
        try:
            # Original physical C worker stays on the same thread as
            # setUp/tearDown. Only the untrusted contender runs elsewhere.
            result = contain_exclusive_lab_cluster(
                self.pg, old=self.old, quiesced=True, max_seconds=120)
        finally:
            release.set()
            competing_thread.join(timeout=15)
            self.pg.stop = original

        self.assertFalse(competing_thread.is_alive())
        self.assertEqual(contender_returns, [])
        self.assertEqual(len(contender_errors), 1)
        self.assertIsInstance(contender_errors[0], LabAdmissionRejected)
        self.assertIn("LAB_RECOVERY_STOPPED_OWNER_MISMATCH",
                      str(contender_errors[0]))
        self.assertEqual(result["state"], "UNKNOWN")
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
                                    "LAB_RECOVERY_STOPPED_OWNER_MISMATCH"):
            self._recover()

    def test_recovery_reentry_denied_after_successful_attempt(self):
        self._recover()
        with self.assertRaisesRegex(LabAdmissionRejected,
                                    "LAB_RECOVERY_STOPPED_OWNER_MISMATCH"):
            self._recover()

    def test_recovery_wrong_identity_poisoned_and_no_restart(self):
        bad = dict(self.old, token=999)
        with self.assertRaises(LabAdmissionRejected):
            self._recover(old=bad)
        with self.assertRaisesRegex(LabAdmissionRejected,
                                    "LAB_RECOVERY_STOPPED_OWNER_MISMATCH"):
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
        with self.assertRaisesRegex(LabAdmissionRejected,
                                    "LAB_PG_C_OWNED_LIFECYCLE_REQUIRED"):
            self.pg.stop()
        self.assertTrue(self.pg.started)
        # A raw caller cannot stop the original PG owner, so it also cannot
        # manufacture a STOPPED_UNVERIFIED C-recovery receipt.
        self.assertEqual(observe_old_lab_backend(self.pg, **self.old),
                         "STILL_ALIVE")

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
