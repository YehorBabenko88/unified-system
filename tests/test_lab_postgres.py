"""C2: temporary PostgreSQL lifecycle, roles, duplicates, crash recovery, cleanup.

Runs when LAB_POSTGRES_BIN names a PostgreSQL bin directory and the process is
not root. Product minimum is 18; LAB_POSTGRES_MIN_MAJOR may lower it for local
development only (CI uses PostgreSQL 18).
"""
import os
import shutil
import sys
import subprocess
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from unified_system.lab_postgres import LabPostgres
from unified_system.lab_simulation_admission import LabAdmissionRejected

BIN = os.environ.get('LAB_POSTGRES_BIN')
MIN = int(os.environ.get('LAB_POSTGRES_MIN_MAJOR', '18'))
ROOT_USER = hasattr(os, 'geteuid') and os.geteuid() == 0

# Byte-equivalent of Grid migration 47 (source_owned_immutable_minutes).
SCHEMA = [
    """CREATE TABLE IF NOT EXISTS provenance_minutes(
fingerprint text PRIMARY KEY CHECK(fingerprint ~ '^[0-9a-f]{64}$'),
content_id text NOT NULL UNIQUE CHECK(content_id ~ '^[0-9a-f]{64}$'),
symbol text NOT NULL,start_ms bigint NOT NULL,record jsonb NOT NULL,
created_at timestamptz NOT NULL DEFAULT clock_timestamp())""",
    "CREATE INDEX IF NOT EXISTS provenance_minutes_page ON provenance_minutes(symbol,start_ms,fingerprint)",
    """CREATE FUNCTION reject_provenance_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'immutable provenance record'; END $$""",
    """CREATE TRIGGER provenance_minutes_immutable BEFORE UPDATE OR DELETE ON provenance_minutes
FOR EACH ROW EXECUTE FUNCTION reject_provenance_mutation()""",
]


def canonical_schema():
    """Load migration 47 from the exact pinned Grid source tree, not a copy."""
    root = os.environ.get('LAB_GRID_ROOT')
    if not root:
        return SCHEMA  # standalone unit fixture, not canonical E2E evidence
    expected = os.environ.get('LAB_GRID_SHA')
    if not expected or len(expected) != 40:
        raise AssertionError('LAB_GRID_SHA_REQUIRED')
    actual = subprocess.check_output(['git', '-C', root, 'rev-parse', 'HEAD'],
                                     text=True).strip()
    if actual != expected:
        raise AssertionError('LAB_GRID_SHA_MISMATCH')
    need_path = Path(root) / 'grid' / 'migrations.py'
    if not need_path.is_file(): raise AssertionError('LAB_GRID_MIGRATIONS_MISSING')
    # Execute only the pinned source file with its canonical package imports.
    sys.path.insert(0, root)
    try:
        from grid.migrations import MIGRATIONS
        selected = [(name, sqls) for version, name, sqls in MIGRATIONS if version == 47]
    finally:
        sys.path.remove(root)
    if len(selected) != 1 or selected[0][0] != 'source_owned_immutable_minutes':
        raise AssertionError('LAB_GRID_MIGRATION_47_CHANGED')
    sqls = selected[0][1]
    if not isinstance(sqls, list) or not sqls:
        raise AssertionError('LAB_GRID_MIGRATION_47_INVALID')
    return sqls


def insert(i):
    f = format(i, '064x')
    return ("INSERT INTO provenance_minutes(fingerprint,content_id,symbol,start_ms,record) VALUES "
            f"('{f}','{f}','BTCUSDT',{i * 60000},'{{\"i\":{i}}}') ON CONFLICT DO NOTHING")


@unittest.skipUnless(BIN and not ROOT_USER, 'needs LAB_POSTGRES_BIN and a non-root user')
class LabPostgresLifecycle(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='unified-lab-pg-'))
        if os.name != 'nt': self.root.chmod(0o700)

    def tearDown(self):
        try:
            self.pg.stop()
        except Exception:
            pass
        shutil.rmtree(self.root, ignore_errors=True)

    def test_full_lifecycle(self):
        self.pg = pg = LabPostgres(BIN, self.root, min_major=MIN).initialize().start().provision(canonical_schema())
        self.assertGreaterEqual(pg.major, MIN)
        self.assertEqual(pg.sql('SHOW listen_addresses'), '127.0.0.1')
        self.assertNotEqual(pg.port, 5432)
        for i in range(1, 11):
            pg.sql(insert(i), role='lab_writer')
        for i in range(1, 11):                                   # duplicate delivery
            pg.sql(insert(i), role='lab_writer')
        self.assertEqual(pg.sql('SELECT count(*), count(DISTINCT fingerprint) FROM provenance_minutes'), '10|10')
        # Reader is read-only; immutability holds even for the writer.
        self.assertEqual(pg.sql('SHOW transaction_read_only', role='lab_reader'), 'on')
        with self.assertRaisesRegex(LabAdmissionRejected, 'read-only'):
            pg.sql(insert(99), role='lab_reader')
        with self.assertRaises(LabAdmissionRejected):
            pg.sql('DROP TABLE provenance_minutes', role='lab_writer')
        with self.assertRaises(LabAdmissionRejected):
            pg.sql('CREATE TABLE unauthorized(x int)', role='lab_writer')
        with self.assertRaises(LabAdmissionRejected):
            pg.sql("UPDATE provenance_minutes SET symbol='X'", role='lab_writer')
        with self.assertRaises(LabAdmissionRejected):
            pg.sql('DELETE FROM provenance_minutes', role='lab_writer')
        # Unconfirmed / malformed rows are rejected by the schema itself.
        with self.assertRaises(LabAdmissionRejected):
            pg.sql("INSERT INTO provenance_minutes(fingerprint,content_id,symbol,start_ms,record) "
                   "VALUES ('nothex','x','BTCUSDT',0,'{}')", role='lab_writer')
        # A forged or unverifiable PID must never be signaled or stopped.
        with mock.patch.object(pg, '_os_process_identity',
                               side_effect=LabAdmissionRejected('LAB_PG_PID_FOREIGN')):
            with self.assertRaisesRegex(LabAdmissionRejected, 'PID_FOREIGN'):
                pg.crash()
            with self.assertRaisesRegex(LabAdmissionRejected, 'PID_FOREIGN'):
                pg.stop()
        self.assertEqual(pg.sql('SELECT count(*) FROM provenance_minutes'), '10')
        # A replaced ownership marker must not grant shutdown authority.
        original_marker = pg._marker.read_text()
        pg._marker.write_text('replaced')
        try:
            with self.assertRaisesRegex(LabAdmissionRejected, 'OWNERSHIP_LOST'):
                pg.stop()
        finally:
            pg._marker.write_text(original_marker)
        self.assertEqual(pg.sql('SELECT count(*) FROM provenance_minutes'), '10')
        # Crash without shutdown checkpoint, then WAL recovery.
        pg.sql(insert(11), role='lab_writer')
        pid = pg.crash()
        self.assertFalse(pg.started)
        pg.start()
        self.assertNotEqual(pg.postmaster_pid(), pid)
        self.assertEqual(pg.sql('SELECT count(*), count(DISTINCT fingerprint) FROM provenance_minutes'), '11|11')
        report = pg.integrity(['provenance_minutes'])
        self.assertEqual(report['provenance_minutes']['rows'], 11)
        self.assertIn('database system was interrupted', pg.log.read_text())
        pg.stop()
        self.assertFalse((pg.data / 'postmaster.pid').exists())

    def test_refuses_old_version_and_foreign_paths(self):
        with self.assertRaisesRegex(LabAdmissionRejected, 'TOO_OLD'):
            LabPostgres(BIN, self.root, min_major=99)
        with self.assertRaisesRegex(LabAdmissionRejected, 'PATH'):
            LabPostgres('relative/bin', self.root)
        pg = LabPostgres(BIN, self.root, min_major=MIN)
        pg.data.mkdir()
        with self.assertRaisesRegex(LabAdmissionRejected, 'DATA_EXISTS'):
            pg.initialize()


if __name__ == '__main__':
    unittest.main()
