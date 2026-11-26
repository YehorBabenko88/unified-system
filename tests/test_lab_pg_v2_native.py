"""C Round 5: actual owned PG18 writer fence and Grid v2 -> Terminan HTTP.

This test intentionally uses PostgreSQL connections and canonical Grid SQL
reader WITHOUT stubbing immutable_minutes. Root admission is LAB-only.
No provider authenticity, complete exchange history or trading permissions.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid
from http.server import ThreadingHTTPServer
from pathlib import Path

from unified_system.lab_pg_fence import (
    install_lab_fence, claim_lab_fence, revoke_lab_fence, fence_identity,
    fenced_lab_witness, revalidate_lab_fence)
from unified_system.lab_postgres import LabPostgres
from unified_system.lab_simulation_admission import LabAdmissionRejected

_SHA_GRID = "f57781a947af138a2099bebe553b89c3c5ee726e"
_SHA_D = "cf1448f8d30399f8787f69f9abfcb5cf992a4209"
_SHA_MATH = "9e6acbd9e12a91189f57234828e31640983af553"
_OWNER = "unified-system"
_NAMESPACE = "unified/lab"
 

def require_sources():
    specs = (
        ("LAB_GRID_ROOT", "LAB_GRID_SHA", _SHA_GRID, "."),
        ("LAB_D_ROOT", "LAB_D_SHA", _SHA_D, "."),
        ("LAB_MATH_ROOT", "LAB_MATH_SHA", _SHA_MATH, ".."),
    )
    roots = []
    for name, sha_key, expected, git_rel in specs:
        value = os.environ.get(name)
        if not value or os.environ.get(sha_key) != expected:
            raise AssertionError("NATIVE_E2E_SOURCE_PIN_REQUIRED:" + name)
        folder = Path(value)
        actual = subprocess.check_output(
            ["git", "-C", str(folder / git_rel), "rev-parse", "HEAD"],
            text=True).strip()
        if actual != expected:
            raise AssertionError("NATIVE_E2E_SOURCE_SHA_MISMATCH:" + name)
        roots.append(str(folder))
    return roots


def write_row(conn, *, generation, token, ids, fp, content_id,
              source_sha, schema_sha,
              owner=_OWNER, namespace=_NAMESPACE,
              symbol="BTCUSDT", start_ms=60000, record=None):
    sql = """SELECT public.lab_fenced_insert(
       %s::text,%s::text,%s::bigint,%s::bigint,
       %s::uuid,%s::uuid,%s::uuid,
       %s::text,%s::text,%s::text,%s::text,%s::text,
       %s::bigint,%s::jsonb)"""
    with conn.cursor() as cur:
        cur.execute(sql, (owner, namespace, generation, token, *ids, source_sha,
                         schema_sha, fp, content_id, symbol,
                         start_ms, json.dumps(record or {"sample": 1})))
    conn.commit()


class CurrentLabAdmission:
    def __init__(self, source_commit):
        self.current = True
        self.source_commit = source_commit

    def require_current(self):
        if not self.current:
            raise ValueError("LAB_SOURCE_REVOKED")
        return True

    def source_identity(self, module_id):
        if module_id != "market_data":
            raise ValueError("LAB_SOURCE_ID_MISMATCH")
        return {"commit": self.source_commit}


class NativePg18V2Tests(unittest.TestCase):
    def setUp(self):
        bin_dir = os.environ.get("LAB_POSTGRES_BIN")
        if not bin_dir or os.name == "nt" or (
            hasattr(os, "geteuid") and os.geteuid() == 0
        ):
            raise AssertionError("NATIVE_PG18_REQUIRED_NONROOT_LINUX")
        self.grid_root, self.d_root, self.math_root = require_sources()
        from tests.test_lab_postgres import canonical_schema
        import psycopg
        self.psycopg = psycopg
        self.root = Path(tempfile.mkdtemp(prefix="c-native-v2-pg-"))
        self.root.chmod(0o700)
        self.pg = None
        self.writer = None
        self.other = None
        self.server = None
        self.server_thread = None
        self.old_client = None
        self.old_market_dsn = os.environ.get("MARKET_DATA_DSN")
        self.paths_inserted = False
        self.addCleanup(self._cleanup)
        # B must be imported from the *installed one-distribution v2 wheel*.
        # Grid source checkout is used only to verify canonical migration 47.
        sys.path[:0] = [self.math_root, self.d_root]
        self.paths_inserted = True
        import importlib.metadata
        import market_data
        if importlib.metadata.version("market-data") != "0.2.0.dev0":
            raise AssertionError("NATIVE_V2_INSTALLED_WHEEL_REQUIRED")
        if Path(market_data.__file__).resolve().is_relative_to(
                Path(self.grid_root).resolve()):
            raise AssertionError("NATIVE_V2_SOURCE_TREE_SHADOWED_WHEEL")
        # Pin the actual installed SDK bytes, not a fabricated placeholder hash.
        from importlib import import_module
        source_digest = hashlib.sha256()
        for relative, module in (
            ("market_data/provenance.py", "market_data.provenance"),
            ("market_data/history_api.py", "market_data.history_api"),
            ("market_data_v2/qualified_read_contract.py",
             "market_data_v2.qualified_read_contract"),
            ("market_data_v2/read_api.py", "market_data_v2.read_api"),
        ):
            installed = Path(import_module(module).__file__).read_bytes()
            pinned = (Path(self.grid_root) / relative).read_bytes()
            if installed != pinned:
                raise AssertionError("NATIVE_V2_INSTALLED_BYTES_NOT_PINNED:" + relative)
            source_digest.update(relative.encode("ascii") + b"\0" + installed + b"\0")
        self.source_sha = source_digest.hexdigest()
        self.schema_sha = hashlib.sha256(
            (Path(self.grid_root) / "grid/migrations.py").read_bytes()).hexdigest()
        self.pg = LabPostgres(bin_dir, self.root, min_major=18).initialize().start()
        self.pg.provision(canonical_schema())
        self.writer = psycopg.connect(self.pg.dsn("lab_writer"))
        self.other = psycopg.connect(self.pg.dsn("lab_writer"))
        install_lab_fence(self.pg)
        self.assertFalse(fenced_lab_witness(self.pg)["execution_authority"])

    def _cleanup(self):
        try:
            if self.old_client is not None:
                from terminan import data
                data._private_market_data_client = self.old_client
            if self.server is not None:
                self.server.shutdown()
                self.server.server_close()
                self.server_thread.join(timeout=5)
            for c in (self.writer, self.other):
                if c is not None:
                    c.close()
            if self.old_market_dsn is None:
                os.environ.pop("MARKET_DATA_DSN", None)
            else:
                os.environ["MARKET_DATA_DSN"] = self.old_market_dsn
            if self.pg is not None:
                self.pg.stop()
            if hasattr(self, "root"):
                shutil.rmtree(self.root)
        finally:
            if self.paths_inserted:
                del sys.path[:2]

    def identity(self):
        return tuple(str(uuid.uuid4()) for _ in range(3))

    def lease_identity(self, ids, token):
        from unified_system.grid_writer_fence_model import WriterLeaseIdentity
        return WriterLeaseIdentity(
            owner=_OWNER, namespace=_NAMESPACE,
            session_id=ids[0], token=token, instance_id=ids[1],
            node_incarnation_id=ids[2], source_sha256=self.source_sha,
            schema_sha256=self.schema_sha)

    def backend_pid(self, conn):
        with conn.cursor() as cur:
            cur.execute("SELECT pg_backend_pid()")
            return cur.fetchone()[0]

    def claim(self, conn, generation, token, ids, *, quiescent=True):
        return claim_lab_fence(self.pg, owner=_OWNER, namespace=_NAMESPACE,
            generation=generation, token=token,
            session_id=ids[0], instance_id=ids[1],
            node_incarnation_id=ids[2], source_sha256=self.source_sha,
            schema_sha256=self.schema_sha, backend_pid=self.backend_pid(conn),
            previous_quiescence_verified=quiescent)

    def test_two_real_db_backends_fence_stale_writer_and_direct_insert(self):
        import psycopg
        self.assertEqual(fence_identity()["native_admission"], False)
        self.assertEqual(self.pg.sql(
            "SELECT has_table_privilege('lab_writer',"
            "'provenance_minutes','INSERT')"), "f")
        with self.assertRaises(LabAdmissionRejected):
            self.pg.sql(
                "INSERT INTO provenance_minutes(fingerprint,content_id,symbol,"
                "start_ms,record) VALUES ('" + "a"*64 + "','" + "a"*64
                + "','BTCUSDT',0,'{}')", role="lab_writer")
        with self.assertRaisesRegex(LabAdmissionRejected, "QUIESCENCE_REQUIRED"):
            self.claim(self.writer, 1, 100, self.identity(), quiescent=False)
        identities = self.identity()
        self.assertTrue(self.claim(self.writer, 1, 100, identities))
        validated = revalidate_lab_fence(
            self.pg, identity=self.lease_identity(identities, 100),
            generation=1, backend_pid=self.backend_pid(self.writer))
        self.assertTrue(validated["db_backend_observed"])
        self.assertTrue(validated["db_fence_current_at_read"])
        self.assertFalse(validated["native_writer_admitted"])
        self.assertFalse(validated["root_consul_admitted"])
        for wrong in (
            dict(identity=self.lease_identity(identities, 101),generation=1,
                 backend_pid=self.backend_pid(self.writer)),
            dict(identity=self.lease_identity(identities, 100),generation=2,
                 backend_pid=self.backend_pid(self.writer)),
            dict(identity=self.lease_identity(identities, 100),generation=1,
                 backend_pid=self.backend_pid(self.other)),
        ):
            with self.assertRaisesRegex(LabAdmissionRejected,
                                        "LAB_FENCE_REVALIDATION_DENIED"):
                revalidate_lab_fence(self.pg, **wrong)
        with self.assertRaises(LabAdmissionRejected):
            self.claim(self.other, 2, 101, self.identity())
        write_row(self.writer, source_sha=self.source_sha, schema_sha=self.schema_sha, generation=1, token=100, ids=identities,
                  fp="1"*64, content_id="2"*64)
        self.assertEqual(self.pg.sql("SELECT count(*) FROM provenance_minutes"),
                         "1")
        for kwargs in (
            {"owner": "foreign-owner"},
            {"namespace": "foreign/namespace"},
            {"source_sha": "f"*64},
            {"schema_sha": "e"*64},
        ):
            args = dict(source_sha=self.source_sha, schema_sha=self.schema_sha,
                        generation=1, token=100, ids=identities,
                        fp="d"*64, content_id="e"*64)
            args.update(kwargs)
            with self.subTest(rejected=sorted(kwargs)):
                with self.assertRaises(psycopg.Error):
                    write_row(self.writer, **args)
                self.writer.rollback()
        with self.assertRaises(psycopg.Error):
            write_row(self.other, source_sha=self.source_sha, schema_sha=self.schema_sha, generation=1, token=100, ids=identities,
                      fp="3"*64, content_id="4"*64)
        self.other.rollback()
        self.assertTrue(revoke_lab_fence(self.pg, generation=1, token=100))
        with self.assertRaisesRegex(LabAdmissionRejected,
                                    "LAB_FENCE_REVALIDATION_DENIED"):
            revalidate_lab_fence(
                self.pg, identity=self.lease_identity(identities, 100),
                generation=1, backend_pid=self.backend_pid(self.writer))
        with self.assertRaises(psycopg.Error):
            write_row(self.writer, source_sha=self.source_sha, schema_sha=self.schema_sha, generation=1, token=100, ids=identities,
                      fp="5"*64, content_id="6"*64)
        self.writer.rollback()
        # Even an asserted quiescence boolean must NOT override PostgreSQL's
        # independent observation that the prior backend is still connected.
        with self.assertRaisesRegex(LabAdmissionRejected, "LAB_FENCE_CLAIM_DENIED"):
            self.claim(self.other, 2, 101, self.identity(), quiescent=True)
        # Native production additionally requires old OS-process extinction.
        # Closing the old backend is the deliberate LAB quiescence proof here.
        self.writer.close()
        self.writer = None
        with self.assertRaisesRegex(LabAdmissionRejected,
                                    "LAB_FENCE_REVALIDATION_DENIED"):
            revalidate_lab_fence(
                self.pg, identity=self.lease_identity(identities, 100),
                generation=1, backend_pid=validated["backend_pid"])
        identities2 = self.identity()
        self.assertTrue(self.claim(self.other, 2, 101, identities2))
        current = revalidate_lab_fence(
            self.pg, identity=self.lease_identity(identities2, 101),
            generation=2, backend_pid=self.backend_pid(self.other))
        self.assertEqual(current["generation"], 2)
        with self.assertRaises(LabAdmissionRejected):
            self.claim(self.other, 3, 100, self.identity())
        write_row(self.other, source_sha=self.source_sha, schema_sha=self.schema_sha, generation=2, token=101, ids=identities2,
                  fp="7"*64, content_id="8"*64)
        self.assertEqual(self.pg.sql("SELECT count(*) FROM provenance_minutes"),
                         "2")
        guarded = fenced_lab_witness(self.pg)
        self.assertEqual(guarded["schema"], "lab-postgres-fenced-custody.v1")
        self.assertFalse(guarded["direct_writer_insert"])
        self.assertFalse(guarded["trading_authorized"])
        self.pg.sql("GRANT INSERT ON provenance_minutes TO lab_writer")
        with self.assertRaisesRegex(LabAdmissionRejected,
                                     "LAB_FENCE_CUSTODY_NOT_VERIFIED"):
            fenced_lab_witness(self.pg)
        self.pg.sql("REVOKE INSERT ON provenance_minutes FROM lab_writer")
        self.assertEqual(self.pg.sql(
            "SELECT token FROM lab_writer_fence"), "101")
        with self.assertRaises(LabAdmissionRejected):
            self.pg.sql("UPDATE lab_writer_fence SET token=999",
                        role="lab_writer")

    def test_32_real_pg_contenders_same_resource_have_one_winner(self):
        from concurrent.futures import ThreadPoolExecutor
        from queue import Queue
        import threading

        # 32 separate live PostgreSQL backends, no application mutex. They
        # remain alive until the main thread verifies one DB/CAS winner.
        count = 32
        ready = threading.Barrier(count + 1, timeout=45)
        release = threading.Event()
        results = Queue()

        def contender(index):
            with self.psycopg.connect(self.pg.dsn("lab_writer")) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT pg_backend_pid()")
                    pid = cur.fetchone()[0]
                ids = self.identity()
                ready.wait()
                try:
                    try:
                        accepted = claim_lab_fence(
                            self.pg, owner=_OWNER, namespace=_NAMESPACE,
                            generation=1, token=500,
                            session_id=ids[0], instance_id=ids[1],
                            node_incarnation_id=ids[2],
                            source_sha256=self.source_sha,
                            schema_sha256=self.schema_sha,
                            backend_pid=pid,
                            previous_quiescence_verified=True)
                        if accepted:
                            receipt = revalidate_lab_fence(
                                self.pg, identity=self.lease_identity(ids, 500),
                                generation=1, backend_pid=pid)
                            if receipt["db_fence_current_at_read"] is not True:
                                raise AssertionError("DB_WINNER_NOT_CURRENT")
                        results.put((index, accepted))
                    except LabAdmissionRejected:
                        results.put((index, False))
                finally:
                    if not release.wait(90):
                        raise AssertionError("CONTENDER_RELEASE_TIMEOUT")

        with ThreadPoolExecutor(max_workers=count) as pool:
            futures = [pool.submit(contender, i) for i in range(count)]
            try:
                ready.wait()
                outcomes = [results.get(timeout=60) for _ in range(count)]
                winners = [i for i, admitted in outcomes if admitted is True]
                self.assertEqual(len(winners), 1)
                self.assertEqual(self.pg.sql(
                    "SELECT count(*),min(generation),min(token) FROM lab_writer_fence"),
                    "1|1|500")
                self.assertEqual(self.pg.sql(
                    "SELECT has_table_privilege('lab_writer',"
                    "'provenance_minutes','INSERT')"), "f")
                self.assertFalse(fenced_lab_witness(self.pg)["trading_authorized"])
            finally:
                release.set()
                for future in futures:
                    future.result(timeout=90)

    def test_native_crash_recovers_fence_high_water_without_old_writer(self):
        ids = self.identity()
        self.assertTrue(self.claim(self.writer, 1, 200, ids))
        first_pid = self.backend_pid(self.writer)
        first_receipt = revalidate_lab_fence(
            self.pg, identity=self.lease_identity(ids, 200),
            generation=1, backend_pid=first_pid)
        self.assertTrue(first_receipt["db_backend_observed"])
        write_row(self.writer, source_sha=self.source_sha, schema_sha=self.schema_sha, generation=1, token=200, ids=ids,
                  fp="9"*64, content_id="a"*64)
        self.writer.close()
        self.writer = None
        self.other.close()
        self.other = None
        killed_pid = self.pg.crash()
        self.assertFalse(self.pg.started)
        self.pg.start()
        self.assertNotEqual(self.pg.postmaster_pid(), killed_pid)
        with self.assertRaisesRegex(LabAdmissionRejected,
                                    "LAB_FENCE_REVALIDATION_DENIED"):
            revalidate_lab_fence(
                self.pg, identity=self.lease_identity(ids, 200),
                generation=1, backend_pid=first_pid)
        self.assertEqual(self.pg.sql(
            "SELECT generation,token,active FROM lab_writer_fence"), "1|200|t")
        self.assertEqual(self.pg.sql("SELECT count(*) FROM provenance_minutes"),
                         "1")
        # Active state is durable and does not authorize a new generation.
        self.writer = self.psycopg.connect(self.pg.dsn("lab_writer"))
        with self.assertRaisesRegex(LabAdmissionRejected, "LAB_FENCE_CLAIM_DENIED"):
            self.claim(self.writer, 2, 201, self.identity())
        self.assertTrue(revoke_lab_fence(self.pg, generation=1, token=200))
        with self.assertRaisesRegex(LabAdmissionRejected, "LAB_FENCE_CLAIM_DENIED"):
            self.claim(self.writer, 2, 200, self.identity())
        next_ids = self.identity()
        self.assertTrue(self.claim(self.writer, 2, 201, next_ids))
        write_row(self.writer, source_sha=self.source_sha, schema_sha=self.schema_sha, generation=2, token=201, ids=next_ids,
                  fp="b"*64, content_id="c"*64)
        self.assertEqual(self.pg.sql("SELECT count(*) FROM provenance_minutes"),
                         "2")
        self.assertEqual(self.pg.sql("SELECT token FROM lab_writer_fence"),
                         "201")

    def test_real_pg_reader_grid_v2_managed_http_to_terminan_chart(self):
        from market_data.provenance import minute_record, producer, digest, canonical
        from market_data import history_api
        from market_data_v2 import read_api
        from terminan import data
        now = int(time.time()*1000)
        start = (now//60000 - 1)*60000
        row = dict(symbol="BTCUSDT", start_ms=start,
                   source_event_start_ms=start+1,
                   source_event_end_ms=start+59999,
                   source_provenance=producer(
                       "synthetic-owned-lab", "a"*40,
                       "wss://stream.bybit.com/v5/public/linear"),
                   open=2,high=2,low=2,close=2,buy_volume=1,sell_volume=0,
                   delta=1,trade_count=1,poc_price=2,quality_status="GOOD",
                   quality_reasons=[],
                   levels=[dict(price=2,buy_volume=1,sell_volume=0,
                                delta=1,volume=1,buy_count=1,sell_count=0)])
        record = minute_record(row, now, "synthetic-owned-lab")
        self.assertEqual(record["producer"], "market_data")
        identities = self.identity()
        self.claim(self.writer, 1, 100, identities)
        write_row(self.writer, source_sha=self.source_sha, schema_sha=self.schema_sha, generation=1, token=100, ids=identities,
                  fp=record["dataset_fingerprint"], content_id=digest(row),
                  start_ms=start, record=record)
        os.environ["MARKET_DATA_DSN"] = self.pg.dsn("lab_reader")
        # This is the *real* imported canonical PostgreSQL query: never mocked.
        rows = history_api.immutable_minutes("BTCUSDT", 1, 2**63-1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(canonical(rows[0]), canonical(record))
        self.assertEqual(self.pg.sql("SHOW transaction_read_only",
                                     role="lab_reader"), "on")
        # The original custody witness is for the legacy INSERT-only writer.
        # Fenced mode REVOKES that grant; report it separately and never
        # misrepresent the old catalogue witness as a success.
        self.assertEqual(self.pg.sql(
            "SELECT has_table_privilege('lab_writer',"
            "'provenance_minutes','INSERT')"), "f")
        self.assertEqual(self.pg.sql(
            "SELECT has_table_privilege('lab_reader',"
            "'provenance_minutes','SELECT')"), "t")
        admission = CurrentLabAdmission(self.grid_sha())
        token = "c"*64
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), read_api.Handler)
        self.server.daemon_threads = True
        self.server.module_identity = {"instance_token": token}
        self.server.startup_admission = admission
        self.server_thread = threading.Thread(
            target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        self.old_client = data._private_market_data_client
        cap = dict(port=self.server.server_port, token=token,
                   source_commit=self.grid_sha(), release_id="c-owned-lab",
                   epoch="d"*32)
        data._private_market_data_client = data.MarketDataReadClient(
            cap, admission, "c-owned-lab")
        receipt = data.qualified_market_data_chart("BTCUSDT", 1)
        self.assertEqual(receipt["status"], "PARTIAL")
        self.assertEqual(receipt["record_integrity"], "VERIFIED")
        self.assertEqual(receipt["storage_immutability"], "NOT_ATTESTED")
        self.assertFalse(receipt["paper_admitted"])
        self.assertFalse(receipt["trading_authorized"])
        self.assertEqual(len(receipt["rows"]), 1)
        # A revoked Root-test admission must deny the next HTTP receipt.
        admission.current = False
        denied = data.qualified_market_data_chart("BTCUSDT", 1)
        self.assertEqual(denied["status"], "UNAVAILABLE")
        self.assertFalse(denied["execution_authority"])

    def grid_sha(self):
        return _SHA_GRID


if __name__ == "__main__":
    unittest.main()
