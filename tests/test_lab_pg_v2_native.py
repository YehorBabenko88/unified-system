"""C Round 5: actual owned PG18 writer fence and Grid v2 -> Terminan HTTP.

This test intentionally uses PostgreSQL connections and canonical Grid SQL
reader WITHOUT stubbing immutable_minutes. Root admission is LAB-only.
No provider authenticity, complete exchange history or trading permissions.
"""
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
    install_lab_fence, claim_lab_fence, revoke_lab_fence, fence_identity)
from unified_system.lab_postgres import LabPostgres
from unified_system.lab_simulation_admission import LabAdmissionRejected

_SHA_GRID = "f57781a947af138a2099bebe553b89c3c5ee726e"
_SHA_D = "cf1448f8d30399f8787f69f9abfcb5cf992a4209"
_SHA_MATH = "9e6acbd9e12a91189f57234828e31640983af553"
_SOURCE_SHA = "a" * 64
_SCHEMA_SHA = "b" * 64


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
              symbol="BTCUSDT", start_ms=60000, record=None):
    sql = """SELECT public.lab_fenced_insert(
       %s::bigint,%s::bigint,%s::uuid,%s::uuid,%s::uuid,
       %s::text,%s::text,%s::text,%s::text,%s::text,
       %s::bigint,%s::jsonb)"""
    with conn.cursor() as cur:
        cur.execute(sql, (generation, token, *ids, _SOURCE_SHA,
                         _SCHEMA_SHA, fp, content_id, symbol,
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
        # B must be imported from the *installed one-distribution v2 wheel*.
        # Grid source checkout is used only to verify canonical migration 47.
        sys.path[:0] = [self.math_root, self.d_root]
        import importlib.metadata
        import market_data
        if importlib.metadata.version("market-data") != "0.2.0.dev0":
            raise AssertionError("NATIVE_V2_INSTALLED_WHEEL_REQUIRED")
        if Path(market_data.__file__).resolve().is_relative_to(
                Path(self.grid_root).resolve()):
            raise AssertionError("NATIVE_V2_SOURCE_TREE_SHADOWED_WHEEL")
        from tests.test_lab_postgres import canonical_schema
        self.pg = LabPostgres(bin_dir, self.root, min_major=18).initialize().start()
        self.pg.provision(canonical_schema())
        self.writer = psycopg.connect(self.pg.dsn("lab_writer"))
        self.other = psycopg.connect(self.pg.dsn("lab_writer"))
        install_lab_fence(self.pg)

    def tearDown(self):
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
            if hasattr(self, "grid_root"):
                del sys.path[:2]

    def identity(self):
        return tuple(str(uuid.uuid4()) for _ in range(3))

    def backend_pid(self, conn):
        with conn.cursor() as cur:
            cur.execute("SELECT pg_backend_pid()")
            return cur.fetchone()[0]

    def claim(self, conn, generation, token, ids, *, quiescent=True):
        return claim_lab_fence(self.pg, generation=generation, token=token,
            session_id=ids[0], instance_id=ids[1],
            node_incarnation_id=ids[2], source_sha256=_SOURCE_SHA,
            schema_sha256=_SCHEMA_SHA, backend_pid=self.backend_pid(conn),
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
        with self.assertRaises(LabAdmissionRejected):
            self.claim(self.other, 2, 101, self.identity())
        write_row(self.writer, generation=1, token=100, ids=identities,
                  fp="1"*64, content_id="2"*64)
        self.assertEqual(self.pg.sql("SELECT count(*) FROM provenance_minutes"),
                         "1")
        with self.assertRaises(psycopg.Error):
            write_row(self.other, generation=1, token=100, ids=identities,
                      fp="3"*64, content_id="4"*64)
        self.other.rollback()
        self.assertTrue(revoke_lab_fence(self.pg, generation=1, token=100))
        with self.assertRaises(psycopg.Error):
            write_row(self.writer, generation=1, token=100, ids=identities,
                      fp="5"*64, content_id="6"*64)
        self.writer.rollback()
        # Native production still requires owner-verified old-process death.
        # Closing the old writer is the deliberate LAB quiescence proof here.
        self.writer.close()
        self.writer = None
        identities2 = self.identity()
        self.assertTrue(self.claim(self.other, 2, 101, identities2))
        with self.assertRaises(LabAdmissionRejected):
            self.claim(self.other, 3, 100, self.identity())
        write_row(self.other, generation=2, token=101, ids=identities2,
                  fp="7"*64, content_id="8"*64)
        self.assertEqual(self.pg.sql("SELECT count(*) FROM provenance_minutes"),
                         "2")
        self.assertEqual(self.pg.sql(
            "SELECT token FROM lab_writer_fence"), "101")
        with self.assertRaises(LabAdmissionRejected):
            self.pg.sql("UPDATE lab_writer_fence SET token=999",
                        role="lab_writer")

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
        write_row(self.writer, generation=1, token=100, ids=identities,
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
