"""Round 7: real owned PostgreSQL 18 + B canonical SQL writer + D chart.

Only synthetic market-source input and a plainly labeled LAB admission stub.
There is no native Root/Consul grant, live collector, trading or external DB.
No SQL reader monkeypatch. Reuses E's exact WriterLeaseIdentity class.
"""
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid
from http.server import ThreadingHTTPServer

from unified_system.lab_postgres import LabPostgres
from unified_system.lab_pg_fence import (
    install_lab_fence, claim_lab_fence, revoke_lab_fence,
    revalidate_lab_fence, fenced_lab_witness,
)
from unified_system.lab_simulation_admission import LabAdmissionRejected

B_SHA="3265d441717f2bc01b82e759b5d8df06cb516fa4"
B_JOURNAL_BLOB="3bfc4daad0eea65982e3c7c92610d9660afe0e71"
D_SHA="05fef5e9527ae02149017b586d311da8870baf25"
MATH_SHA="9e6acbd9e12a91189f57234828e31640983af553"
E_SHA="2c993d873cc53a784a64ff525465770bb5bb4a39"
E_MODEL_BLOB="71c74a2c0d8c1c0120412124ef1d12d53b691581"
B_ADAPTER_BLOB="8b93466a79fa234468a3cdc44106bd5e153e81c4"
DIGEST_MODULES=(
    ("market_data/provenance.py","market_data.provenance"),
    ("market_data/history_api.py","market_data.history_api"),
    ("market_data_v2/qualified_read_contract.py",
     "market_data_v2.qualified_read_contract"),
    ("market_data_v2/read_api.py","market_data_v2.read_api"),
)


def exact_repo(env_root, env_sha, expected, *, repo_root=None):
    path=Path(os.environ[env_root]).resolve(strict=True)
    if os.environ[env_sha]!=expected:
        raise AssertionError("ROUND7_PIN_ENV_MISMATCH:"+env_sha)
    checkout=(path/repo_root) if repo_root else path
    actual=subprocess.check_output(
        ["git","-C",str(checkout),"rev-parse","HEAD"],text=True).strip()
    if actual!=expected:
        raise AssertionError("ROUND7_SOURCE_HEAD_MISMATCH:"+env_root)
    return path


def git_blob(path):
    return subprocess.check_output(
        ["git","hash-object","--",str(path)],text=True).strip()


class TestOnlyLabAdmission:
    """FOR SYNTHETIC ISOLATED PG TESTS ONLY; fully forgeable, not Root authority."""
    lab_only=True
    trusted_root_authority=True

    def __init__(self):
        self.current=True

    def require_current(self):
        return self.current is True


class TestOnlySourceAdmission:
    def __init__(self, sha):
        self.sha=sha
        self.current=True

    def require_current(self):
        if not self.current:
            raise ValueError("ROUND7_LAB_SOURCE_REVOKED")
        return True

    def source_identity(self, name):
        if name!="market_data":
            raise ValueError("ROUND7_WRONG_SOURCE")
        return {"commit":self.sha}


class Round7OwnedPg18Integrated(unittest.TestCase):
    def setUp(self):
        if os.name=="nt" or not hasattr(os,"geteuid") or os.geteuid()==0:
            raise AssertionError("ROUND7_NATIVE_PG18_NONROOT_LINUX_REQUIRED")
        self.bin=os.environ["LAB_POSTGRES_BIN"]
        self.b=exact_repo("LAB_GRID_ROOT","LAB_GRID_SHA",B_SHA)
        self.d=exact_repo("LAB_D_ROOT","LAB_D_SHA",D_SHA)
        self.math=exact_repo("LAB_MATH_ROOT","LAB_MATH_SHA",MATH_SHA,
                             repo_root="..")
        if os.environ["LAB_E_SHA"]!=E_SHA:
            raise AssertionError("ROUND7_E_EXACT_PIN_REQUIRED")
        from unified_system import grid_writer_fence_model as model
        if git_blob(Path(model.__file__))!=E_MODEL_BLOB:
            raise AssertionError("ROUND7_E_WRITER_LEASE_IDENTITY_BLOB_MISMATCH")
        self.WriterLeaseIdentity=model.WriterLeaseIdentity
        if importlib.metadata.version("market-data")!="0.2.0.dev0":
            raise AssertionError("ROUND7_SINGLE_MARKET_WHEEL_REQUIRED")
        adapter_file=self.b/"grid/canonical_lab_fenced_writer.py"
        if git_blob(adapter_file)!=B_ADAPTER_BLOB:
            raise AssertionError("ROUND7_B_ADAPTER_BLOB_MISMATCH")
        # Load just B's pinned adapter by file location. Adding Grid root to
        # sys.path would silently shadow the independently installed SDK wheel.
        spec=importlib.util.spec_from_file_location(
            "_c_round7_exact_grid_writer",adapter_file)
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.CanonicalLabMinuteWriter=module.CanonicalLabMinuteWriter
        self.old_path=sys.path[:]
        sys.path[:0]=[str(self.math),str(self.d)]
        self.old_dsn=os.environ.get("MARKET_DATA_DSN")
        self.pg=None
        self.primary=None
        self.foreign=None
        self.server=None
        self.worker=None
        self.old_client=None
        self.test_clock_ms=int(time.time()*1000)
        self.tmp=Path(tempfile.mkdtemp(prefix="round7-c-owned-pg18-"))
        self.tmp.chmod(0o700)
        self.addCleanup(self.cleanup)
        from importlib import import_module
        hasher=hashlib.sha256()
        for relative,qualified in DIGEST_MODULES:
            installed=Path(import_module(qualified).__file__).read_bytes()
            source=(self.b/relative).read_bytes()
            if installed!=source:
                raise AssertionError("ROUND7_WHEEL_SOURCE_BYTES_MISMATCH:"+relative)
            hasher.update(relative.encode("ascii")+b"\0"+installed+b"\0")
        self.source_sha=hasher.hexdigest()
        self.schema_sha=hashlib.sha256(
            (self.b/"grid/migrations.py").read_bytes()).hexdigest()
        from tests.test_lab_postgres import canonical_schema
        self.pg=LabPostgres(self.bin,self.tmp,min_major=18).initialize().start()
        if self.pg.major!=18 or self.pg.port==5432:
            raise AssertionError("ROUND7_FOREIGN_PG_VERSION_OR_PORT")
        self.pg.provision(canonical_schema())
        install_lab_fence(self.pg)
        from unified_system.lab_pg_checkpoint import install_lab_checkpoint
        install_lab_checkpoint(self.pg)
        self.assertFalse(fenced_lab_witness(self.pg)["direct_writer_insert"])
        import psycopg
        self.psycopg=psycopg
        self.primary=psycopg.connect(
            self.pg.dsn("lab_writer"),autocommit=True)
        self.foreign=psycopg.connect(
            self.pg.dsn("lab_writer"),autocommit=True)
        self.root_admission=TestOnlyLabAdmission()
        self.ids=tuple(str(uuid.uuid4()) for _ in range(3))
        self.identity=self.WriterLeaseIdentity(
            owner="unified-system",namespace="unified/lab",
            session_id=self.ids[0],token=100,instance_id=self.ids[1],
            node_incarnation_id=self.ids[2],
            source_sha256=self.source_sha,schema_sha256=self.schema_sha)

    def cleanup(self):
        try:
            if self.old_client is not None:
                from terminan import data
                data._private_market_data_client=self.old_client
            if self.server is not None:
                self.server.shutdown()
                self.server.server_close()
                self.worker.join(timeout=10)
                if self.worker.is_alive():
                    raise AssertionError("ROUND7_HTTP_SERVER_NOT_STOPPED")
            for conn in (self.primary,self.foreign):
                if conn is not None and not conn.closed:
                    conn.close()
            if self.old_dsn is None:
                os.environ.pop("MARKET_DATA_DSN",None)
            else:
                os.environ["MARKET_DATA_DSN"]=self.old_dsn
            if self.pg is not None:
                self.pg.stop()
            if self.pg is None or not self.pg.started:
                shutil.rmtree(self.tmp)
        finally:
            sys.path[:]=self.old_path

    def pid(self,conn):
        with conn.cursor() as cur:
            cur.execute("SELECT pg_backend_pid()")
            return cur.fetchone()[0]

    def claim(self,conn,*,generation=1,token=100,identity=None):
        item=identity or self.identity
        return claim_lab_fence(
            self.pg,owner=item.owner,namespace=item.namespace,
            generation=generation,token=token,session_id=item.session_id,
            instance_id=item.instance_id,
            node_incarnation_id=item.node_incarnation_id,
            source_sha256=item.source_sha256,
            schema_sha256=item.schema_sha256,backend_pid=self.pid(conn),
            previous_quiescence_verified=True)

    def adapter(self,conn,*,generation=1,token=100,identity=None,
                admission=None):
        i=identity or self.identity
        return self.CanonicalLabMinuteWriter(
            conn,owner=i.owner,namespace=i.namespace,
            generation=generation,token=token,session_id=i.session_id,
            instance_id=i.instance_id,
            node_incarnation_id=i.node_incarnation_id,
            source_sha256=i.source_sha256,schema_sha256=i.schema_sha256,
            native_admission=admission or self.root_admission,
            bound_backend_pid=self.pid(conn))

    def synthetic_minute(self, *, minute_offset=1, close_value=2.0):
        from market_data.provenance import minute_record, producer
        if type(minute_offset) is not int or not 1<=minute_offset<=10:
            raise AssertionError("ROUND9_MINUTE_OFFSET_INVALID")
        now=self.test_clock_ms
        start=(now//60000-minute_offset)*60000
        record=minute_record({
            "symbol":"BTCUSDT","start_ms":start,
            "source_event_start_ms":start+1,
            "source_event_end_ms":start+59000,
            "source_provenance":producer(
                "isolated-round7","a"*40,
                "wss://stream.bybit.com/v5/public/linear"),
            "open":1.0,"high":2.0,"low":1.0,"close":close_value,
            "buy_volume":1.0,"sell_volume":0.0,"delta":1.0,
            "trade_count":1,"poc_price":2.0,"quality_status":"GOOD",
            "quality_reasons":[],"levels":[{
                "price":2.0,"buy_volume":1.0,"sell_volume":0.0,
                "delta":1.0,"volume":1.0,"buy_count":1,
                "sell_count":1-1
            }],
        },now,"isolated-round7")
        if record["producer"]!="market_data" or record["status"]!="PARTIAL":
            raise AssertionError("ROUND7_SOURCE_PRODUCER_NOT_CANONICAL")
        return record

    def test_real_b_adapter_c_sql_d_chart_and_revoke(self):
        from market_data.provenance import digest
        from market_data import history_api
        from market_data_v2 import read_api
        from terminan import data
        self.assertTrue(self.claim(self.primary))
        db_receipt=revalidate_lab_fence(
            self.pg,identity=self.identity,generation=1,
            backend_pid=self.pid(self.primary))
        self.assertTrue(db_receipt["db_backend_observed"])
        self.assertFalse(db_receipt["native_writer_admitted"])
        self.assertFalse(db_receipt["trading_authorized"])
        record=self.synthetic_minute()
        from unified_system.lab_pg_checkpoint import append_lab_pending
        pending=dict(identity=self.identity,generation=1,
                     backend_pid=self.pid(self.primary),
                     stream_id="bybit:BTCUSDT:1m",
                     symbol="BTCUSDT",start_ms=record["start_ms"],
                     fingerprint=record["dataset_fingerprint"],
                     content_id=digest(record))
        append_lab_pending(self.pg,**pending)
        self.assertEqual(read_lab_pending(
            self.pg,stream_id="bybit:BTCUSDT:1m")["fingerprint"],
            record["dataset_fingerprint"])
        result=self.adapter(self.primary).write(record,content_id=digest(record))
        self.assertEqual(result["status"],"LOCAL_COMMIT_RETURNED")
        self.assertFalse(result["trading_authorized"])
        self.assertEqual(self.pg.sql("SELECT count(*) FROM provenance_minutes"),"1")
        from unified_system.lab_pg_checkpoint import (
            read_committed_lab_minute, commit_verified_lab_cursor,
            read_lab_cursor, read_lab_checkpoint,
            append_lab_pending, read_lab_pending,clear_verified_lab_pending)
        original_id=digest(record)
        query=dict(identity=self.identity,generation=1,
                   backend_pid=self.pid(self.primary),
                   symbol="BTCUSDT",start_ms=record["start_ms"],
                   fingerprint=record["dataset_fingerprint"],
                   content_id=original_id)
        committed=read_committed_lab_minute(self.pg,**query)
        self.assertEqual(committed["status"],"MATCH")
        self.assertFalse(committed["native_admitted"])
        conflict=read_committed_lab_minute(
            self.pg,**dict(query,content_id="e"*64))
        self.assertEqual(conflict["status"],"CONFLICT")
        missing=read_committed_lab_minute(
            self.pg,**dict(query,fingerprint="d"*64,
                          symbol="ETHUSDT",content_id="f"*64))
        self.assertEqual(missing["status"],"MISSING")
        checkpoint=dict(query,stream_id="bybit:BTCUSDT:1m",
                        cursor=record["start_ms"])
        saved=commit_verified_lab_cursor(self.pg,**checkpoint)
        self.assertTrue(saved["committed_record_verified"])
        self.assertFalse(saved["contiguous_source_coverage_attested"])
        from unified_system.lab_pg_checkpoint import verify_existing_lab_checkpoint
        exact=verify_existing_lab_checkpoint(self.pg,**query,
                                              stream_id="bybit:BTCUSDT:1m")
        self.assertEqual(exact["state"],"EXACT_ALREADY_ACKNOWLEDGED")
        self.assertEqual(exact["symbol"],"BTCUSDT")
        # Actual B COwnedLabJournal must validate the unmodified C receipt.
        # Import only the exact source-pinned B adapter; no wheel shadowing.
        journal_source=self.b/"grid/c_lab_journal_adapter.py"
        if git_blob(journal_source)!=B_JOURNAL_BLOB:
            raise AssertionError("ROUND11_B_JOURNAL_PIN_MISMATCH")
        import asyncio
        import importlib.util
        import types
        # This package is deliberately *not* in the market-data wheel.
        # Isolate source checkout under a private module prefix.
        if "_c_round11_grid" not in sys.modules:
            package=types.ModuleType("_c_round11_grid")
            package.__path__=[str(self.b/"grid")]
            sys.modules["_c_round11_grid"]=package
        spec=importlib.util.spec_from_file_location(
            "_c_round11_grid.c_lab_journal_adapter",journal_source)
        loaded=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(loaded)
        owner_journal=loaded.COwnedLabJournal(
            c_module=__import__("unified_system.lab_pg_checkpoint",
                                fromlist=["verify_existing_lab_checkpoint"]),
            pg=self.pg,identity=self.identity,generation=1,
            backend_pid=self.pid(self.primary),
            stream_id="bybit:BTCUSDT:1m")
        minute_key=dict(symbol="BTCUSDT",start_ms=record["start_ms"],
                        fingerprint=record["dataset_fingerprint"],
                        content_id=digest(record))
        verified=asyncio.run(owner_journal.exact_existing_checkpoint(minute_key))
        self.assertEqual(verified,exact)
        self.assertFalse(exact["native_admitted"])
        self.assertEqual(verify_existing_lab_checkpoint(
            self.pg,**dict(query,content_id="b"*64),
            stream_id="bybit:BTCUSDT:1m")["state"],"UNRESOLVED")
        self.assertTrue(clear_verified_lab_pending(
            self.pg,identity=self.identity,generation=1,
            backend_pid=self.pid(self.primary),
            stream_id="bybit:BTCUSDT:1m"))
        self.assertIsNone(read_lab_pending(
            self.pg,stream_id="bybit:BTCUSDT:1m"))
        self.assertEqual(read_lab_cursor(self.pg,
                         stream_id="bybit:BTCUSDT:1m"),record["start_ms"])
        checkpoint_record=read_lab_checkpoint(
            self.pg,stream_id="bybit:BTCUSDT:1m")
        self.assertEqual(checkpoint_record["fingerprint"],
                         record["dataset_fingerprint"])
        with self.assertRaises(LabAdmissionRejected):
            commit_verified_lab_cursor(self.pg,**checkpoint)
        with self.assertRaises(LabAdmissionRejected):
            commit_verified_lab_cursor(
                self.pg,**dict(checkpoint,backend_pid=self.pid(self.foreign)))
        with self.assertRaises(LabAdmissionRejected):
            commit_verified_lab_cursor(
                self.pg,**dict(checkpoint,cursor=record["start_ms"]+60000))
        os.environ["MARKET_DATA_DSN"]=self.pg.dsn("lab_reader")
        rows=history_api.immutable_minutes("BTCUSDT",1,2**63-1)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["dataset_fingerprint"],
                         record["dataset_fingerprint"])
        # No DB seam patch: real Grid managed HTTP calls canonical SQL.
        source=TestOnlySourceAdmission(B_SHA)
        bearer="b"*64
        self.server=ThreadingHTTPServer(("127.0.0.1",0),read_api.Handler)
        self.server.daemon_threads=True
        self.server.startup_admission=source
        self.server.module_identity={"instance_token":bearer}
        self.worker=threading.Thread(
            target=self.server.serve_forever,daemon=True)
        self.worker.start()
        self.old_client=data._private_market_data_client
        capability=dict(port=self.server.server_port,token=bearer,
                        source_commit=B_SHA,release_id="isolated-round7",
                        epoch="d"*32)
        data._private_market_data_client=data.MarketDataReadClient(
            capability,source,"isolated-round7")
        chart=data.qualified_market_data_chart("BTCUSDT",1)
        self.assertEqual(chart["status"],"PARTIAL")
        self.assertEqual(len(chart["rows"]),1)
        self.assertFalse(chart["paper_admitted"])
        self.assertFalse(chart["trading_authorized"])
        with self.assertRaises(self.psycopg.Error):
            self.adapter(self.foreign).write(record,content_id="c"*64)
        self.assertTrue(revoke_lab_fence(self.pg,generation=1,token=100))
        with self.assertRaises(LabAdmissionRejected):
            commit_verified_lab_cursor(self.pg,**checkpoint)
        with self.assertRaises(LabAdmissionRejected):
            revalidate_lab_fence(
                self.pg,identity=self.identity,generation=1,
                backend_pid=self.pid(self.primary))
        with self.assertRaises(self.psycopg.Error):
            self.adapter(self.primary).write(record,content_id="d"*64)
        self.assertEqual(self.pg.sql("SELECT count(*) FROM provenance_minutes"),"1")
        source.current=False
        denied=data.qualified_market_data_chart("BTCUSDT",1)
        self.assertEqual(denied["status"],"UNAVAILABLE")
        self.assertFalse(denied["execution_authority"])

    def test_reconnect_after_pg_crash_cannot_reuse_previous_token(self):
        from market_data.provenance import digest
        from market_data import history_api
        from unified_system.lab_pg_checkpoint import (
            append_lab_pending, read_lab_pending, read_lab_cursor,
            read_lab_checkpoint, commit_verified_lab_cursor,
            read_committed_lab_minute, clear_verified_lab_pending)

        self.assertTrue(self.claim(self.primary))
        stream="bybit:BTCUSDT:1m"

        def fields(record):
            return dict(stream_id=stream,cursor=record["start_ms"],
                        symbol="BTCUSDT",start_ms=record["start_ms"],
                        fingerprint=record["dataset_fingerprint"],
                        content_id=digest(record))

        def owner_fields(identity, generation):
            return dict(identity=identity,generation=generation,
                        backend_pid=self.pid(self.primary))

        # The first committed+acknowledged candle checkpoint must survive WAL.
        first=self.synthetic_minute(minute_offset=4)
        before=dict(fields(first))
        before.pop("cursor")
        append_lab_pending(self.pg,**owner_fields(self.identity,1),**before)
        self.adapter(self.primary).write(first,content_id=digest(first))
        commit_verified_lab_cursor(
            self.pg,**owner_fields(self.identity,1),**fields(first))
        clear_verified_lab_pending(
            self.pg,**owner_fields(self.identity,1),stream_id=stream)
        self.assertEqual(read_lab_cursor(self.pg,stream_id=stream),
                         first["start_ms"])

        # This minute commits to the real DB. Its application-level ACK is
        # deliberately discarded before the postmaster crash: a SYNTHETIC
        # unknown-outcome test, not a fault injected at the COMMIT instruction.
        pending=self.synthetic_minute(minute_offset=3)
        pending_fields=dict(fields(pending))
        pending_fields.pop("cursor")
        append_lab_pending(
            self.pg,**owner_fields(self.identity,1),**pending_fields)
        self.adapter(self.primary).write(pending,content_id=digest(pending))
        self.assertEqual(read_lab_pending(
            self.pg,stream_id=stream)["fingerprint"],
            pending["dataset_fingerprint"])
        old_pid=self.pid(self.primary)
        self.primary.close()
        self.primary=None
        self.foreign.close()
        self.foreign=None
        killed=self.pg.crash()
        self.assertFalse(self.pg.started)
        self.pg.start()
        self.assertNotEqual(self.pg.postmaster_pid(),killed)
        with self.assertRaises(LabAdmissionRejected):
            revalidate_lab_fence(self.pg,identity=self.identity,
                                 generation=1,backend_pid=old_pid)
        self.assertEqual(self.pg.sql(
            "SELECT generation,token,active FROM lab_writer_fence"),"1|100|t")
        self.assertEqual(read_lab_cursor(self.pg,stream_id=stream),
                         first["start_ms"])
        self.assertEqual(read_lab_pending(
            self.pg,stream_id=stream)["fingerprint"],
            pending["dataset_fingerprint"])
        self.assertEqual(read_lab_checkpoint(
            self.pg,stream_id=stream)["content_id"],digest(first))

        self.primary=self.psycopg.connect(
            self.pg.dsn("lab_writer"),autocommit=True)
        with self.assertRaises(LabAdmissionRejected):
            self.claim(self.primary,generation=2,token=101)
        # Old token on a freshly connected same-credential backend must lose.
        with self.assertRaises(self.psycopg.Error):
            self.adapter(self.primary,identity=self.identity,
                         generation=1,token=100).write(
                pending,content_id="e"*64)
        self.assertTrue(revoke_lab_fence(self.pg,generation=1,token=100))
        with self.assertRaises(LabAdmissionRejected):
            self.claim(self.primary,generation=2,token=100)
        newer=self.WriterLeaseIdentity(
            owner=self.identity.owner,namespace=self.identity.namespace,
            session_id=str(uuid.uuid4()),token=101,
            instance_id=str(uuid.uuid4()),node_incarnation_id=str(uuid.uuid4()),
            source_sha256=self.source_sha,schema_sha256=self.schema_sha)
        self.assertTrue(self.claim(
            self.primary,generation=2,token=101,identity=newer))
        current=owner_fields(newer,2)
        fresh=revalidate_lab_fence(self.pg,**current)
        self.assertTrue(fresh["db_fence_current_at_read"])
        self.assertFalse(fresh["root_consul_admitted"])

        # Never blind-retry an unknown COMMIT. Exact immutable readback under
        # the NEW C/E fenced owner must prove MATCH before checkpoint/clear.
        restored=read_committed_lab_minute(
            self.pg,**current,**pending_fields)
        self.assertEqual(restored["status"],"MATCH")
        self.assertFalse(restored["native_admitted"])
        commit_verified_lab_cursor(self.pg,**current,**fields(pending))
        from unified_system.lab_pg_checkpoint import verify_existing_lab_checkpoint
        exact=verify_existing_lab_checkpoint(
            self.pg,**current,**pending_fields,stream_id=stream)
        self.assertEqual(exact["state"],"EXACT_ALREADY_ACKNOWLEDGED")
        self.assertFalse(exact["execution_authority"])
        # A lost checkpoint ACK is not a second cursor advance.
        with self.assertRaisesRegex(LabAdmissionRejected,
                                    "LAB_CURSOR_CAS_OR_READBACK_DENIED"):
            commit_verified_lab_cursor(self.pg,**current,**fields(pending))
        clear_verified_lab_pending(self.pg,**current,stream_id=stream)
        self.assertIsNone(read_lab_pending(self.pg,stream_id=stream))
        # Synthetic lost DELETE ACK: PostgreSQL completed the owner-only
        # clear, but its caller retries. Refuse the repeated DELETE; verify
        # checkpoint and absent pending separately before returning READY.
        with self.assertRaisesRegex(LabAdmissionRejected,
                                    "LAB_PENDING_CLEAR_UNVERIFIED"):
            clear_verified_lab_pending(self.pg,**current,stream_id=stream)
        self.assertIsNone(read_lab_pending(self.pg,stream_id=stream))
        self.assertEqual(read_lab_cursor(self.pg,stream_id=stream),
                         pending["start_ms"])
        self.assertEqual(verify_existing_lab_checkpoint(
            self.pg,**current,**pending_fields,stream_id=stream
        )["state"],"UNRESOLVED")
        with self.assertRaises(self.psycopg.Error):
            self.adapter(self.primary,identity=self.identity,
                         generation=1,token=100).write(
                pending,content_id="f"*64)

        os.environ["MARKET_DATA_DSN"]=self.pg.dsn("lab_reader")
        persisted=history_api.immutable_minutes("BTCUSDT",2,2**63-1)
        self.assertEqual(
            {row["dataset_fingerprint"] for row in persisted},
            {first["dataset_fingerprint"],pending["dataset_fingerprint"]})
        self.assertEqual(self.pg.sql(
            "SELECT count(*),count(DISTINCT fingerprint)"
            " FROM provenance_minutes"),"2|2")

        # An out-of-order later minute can exist, but cannot skip a cursor.
        gap=self.synthetic_minute(minute_offset=1)
        self.adapter(self.primary,identity=newer,generation=2,token=101).write(
            gap,content_id=digest(gap))
        gap_fields=fields(gap)
        with self.assertRaisesRegex(LabAdmissionRejected,
                                    "LAB_CURSOR_CAS_OR_READBACK_DENIED"):
            commit_verified_lab_cursor(self.pg,**current,**gap_fields)
        self.assertEqual(read_lab_cursor(self.pg,stream_id=stream),
                         pending["start_ms"])
        middle=self.synthetic_minute(minute_offset=2)
        self.adapter(self.primary,identity=newer,generation=2,token=101).write(
            middle,content_id=digest(middle))
        commit_verified_lab_cursor(self.pg,**current,**fields(middle))
        commit_verified_lab_cursor(self.pg,**current,**gap_fields)
        self.assertEqual(read_lab_cursor(self.pg,stream_id=stream),
                         gap["start_ms"])
        self.assertEqual(self.pg.sql(
            "SELECT count(*),count(DISTINCT fingerprint)"
            " FROM provenance_minutes"),"4|4")

        # Immutable conflicting contents for the SAME minute are quarantined:
        # the ledger cannot falsely certify either of the two fingerprints.
        divergent=self.synthetic_minute(minute_offset=1,close_value=1.5)
        self.assertNotEqual(divergent["dataset_fingerprint"],
                            gap["dataset_fingerprint"])
        self.adapter(self.primary,identity=newer,generation=2,token=101).write(
            divergent,content_id=digest(divergent))
        self.assertEqual(self.pg.sql(
            "SELECT count(*),count(DISTINCT fingerprint)"
            " FROM provenance_minutes"),"5|5")
        disagreement=read_committed_lab_minute(
            self.pg,**current,
            symbol="BTCUSDT",start_ms=gap["start_ms"],
            fingerprint=gap["dataset_fingerprint"],content_id=digest(gap))
        self.assertEqual(disagreement["status"],"CONFLICT")
        with self.assertRaisesRegex(LabAdmissionRejected,
                                    "LAB_CURSOR_DURABLE_RECORD_CORRUPT"):
            read_lab_cursor(self.pg,stream_id=stream)


if __name__=="__main__":
    unittest.main()
