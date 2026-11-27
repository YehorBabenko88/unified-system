"""Native Windows pg_ctl regression; isolated LAB, never Root admission.

The A-owned observer is loaded from a separately pinned checkout, just as in
the original C recovery workflow. No alternate process or SQL owner is used.
"""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid

from unified_system.lab_postgres import LabPostgres
from unified_system.lab_pg_fence import install_lab_fence, claim_lab_fence
from unified_system.lab_pg_recovery import (
    contain_exclusive_lab_cluster, _dispose_native_pg18_fixture)


@unittest.skipUnless(os.name == "nt" and os.environ.get("LAB_POSTGRES_BIN")
                     and os.environ.get("LAB_A_RUNTIME_ROOT")
                     and os.environ.get("LAB_A_RUNTIME_SHA")
                     and os.environ.get("LAB_C_PG18_NATIVE_TEST") == "1",
                     "requires native Windows PG18 and pinned A observer")
class WindowsPostgresOptionsTests(unittest.TestCase):
    def test_pg_ctl_starts_without_literal_single_quote_socket_directory(self):
        source = Path(os.environ["LAB_A_RUNTIME_ROOT"])
        actual = subprocess.check_output(
            ["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
        self.assertEqual(actual, os.environ["LAB_A_RUNTIME_SHA"])
        name = "unified_system.runtime_process"
        previous = sys.modules.get(name)
        spec = importlib.util.spec_from_file_location(
            name, source / "unified_system" / "runtime_process.py")
        observer = importlib.util.module_from_spec(spec)
        sys.modules[name] = observer
        spec.loader.exec_module(observer)
        root = Path(tempfile.mkdtemp(prefix="c-round14-recovery-windows-"))
        pg = None
        writer = None
        old = None
        try:
            pg = LabPostgres(os.environ["LAB_POSTGRES_BIN"], root, min_major=18)
            pg.initialize().start()
            self.assertEqual(pg.sql("SHOW server_version", database="postgres").split(".")[0], "18")
            self.assertEqual(pg.sql("SHOW unix_socket_directories", database="postgres"), "")
            self.assertEqual(pg.sql("SHOW listen_addresses", database="postgres"), "127.0.0.1")
            self.assertNotEqual(pg.port, 5432)
            from tests.test_lab_postgres import canonical_schema
            pg.provision(canonical_schema())
            install_lab_fence(pg)
            import psycopg
            writer = psycopg.connect(pg.dsn("lab_writer"), autocommit=True)
            pid = writer.info.backend_pid
            ids = tuple(str(uuid.uuid4()) for _ in range(3))
            claim_lab_fence(pg, owner="unified-system", namespace="unified/lab",
                           generation=1, token=100, session_id=ids[0],
                           instance_id=ids[1], node_incarnation_id=ids[2],
                           source_sha256="a" * 64, schema_sha256="b" * 64,
                           backend_pid=pid, previous_quiescence_verified=True)
            old = dict(owner="unified-system", namespace="unified/lab",
                       generation=1, token=100, backend_pid=pid,
                       backend_start=pg.sql(
                           "SELECT backend_start FROM pg_stat_activity "
                           f"WHERE pid={pid}"))
            result = contain_exclusive_lab_cluster(pg, old=old, quiesced=True)
            self.assertFalse(pg.started)
            self.assertFalse(result["native_admitted"])
        finally:
            try:
                if pg is not None and pg.log.exists():
                    destination = os.environ.get("LAB_PG_LOG_COPY")
                    if destination:
                        shutil.copyfile(pg.log, destination)
                if pg is not None:
                    if pg.started is False and pg._owned_pid is None:
                        # The original owner still verifies postmaster
                        # executable/start/PID-file identity on this path.
                        pg.stop()
                    # Startup failure is deliberately quarantined by C when
                    # its initial outcome is unknown; never bypass that gate.
                    _dispose_native_pg18_fixture(pg)
                if writer is not None:
                    writer.close()
                shutil.rmtree(root)
            finally:
                if previous is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = previous


if __name__ == "__main__":
    unittest.main()
