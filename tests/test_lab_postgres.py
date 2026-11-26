"""C2: temporary PostgreSQL lifecycle, roles, duplicates, crash recovery, cleanup.

Runs when LAB_POSTGRES_BIN names a PostgreSQL bin directory and the process is
not root. Product minimum is 18; LAB_POSTGRES_MIN_MAJOR may lower it for local
development only (CI uses PostgreSQL 18).
"""
import os
import json
import time
import copy
import shutil
import sys
import subprocess
import socket
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
        pg = getattr(self, 'pg', None)
        if pg is not None:
            try:
                pg.stop()
            except BaseException:
                # The test must fail rather than delete an unverified cluster.
                raise
        shutil.rmtree(self.root)

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
        # Writer cannot read data, create tables or temporary objects.
        with self.assertRaises(LabAdmissionRejected):
            pg.sql('SELECT count(*) FROM provenance_minutes', role='lab_writer')
        with self.assertRaises(LabAdmissionRejected):
            pg.sql('CREATE TEMP TABLE writer_temp(x int)', role='lab_writer')
        with self.assertRaises(LabAdmissionRejected):
            pg.sql('SET default_transaction_read_only=off; CREATE TEMP TABLE reader_temp(x int)',
                   role='lab_reader')
        # Owner-created future tables must not silently become readable.
        pg.sql('CREATE TABLE lab_private_owner_only(x int)')
        with self.assertRaises(LabAdmissionRejected):
            pg.sql('SELECT * FROM lab_private_owner_only', role='lab_reader')
        witness = pg.provenance_storage_witness()
        self.assertEqual(witness['witness_schema'], 'lab-postgres-custody.v1')
        self.assertEqual(witness['storage_immutability'], 'ROLE_AND_TRIGGER_GUARDED_LAB_ONLY')
        self.assertEqual(witness['immutable_trigger_count'], 1)
        self.assertFalse(witness['writer_can_select'])
        self.assertFalse(witness['writer_can_update'])
        self.assertFalse(witness['writer_can_delete'])
        self.assertFalse(witness['reader_can_insert'])
        self.assertFalse(witness['execution_authority'])
        self.assertFalse(witness['trading_authorized'])
        # An altered grant or disabled immutability trigger invalidates the
        # witness even when a previously observed record still hashes correctly.
        pg.sql('GRANT SELECT ON provenance_minutes TO lab_writer')
        with self.assertRaisesRegex(LabAdmissionRejected, 'LAB_PG_CUSTODY_NOT_VERIFIED'):
            pg.provenance_storage_witness()
        pg.sql('REVOKE SELECT ON provenance_minutes FROM lab_writer')
        pg.sql('ALTER TABLE provenance_minutes DISABLE TRIGGER provenance_minutes_immutable')
        with self.assertRaisesRegex(LabAdmissionRejected, 'LAB_PG_CUSTODY_NOT_VERIFIED'):
            pg.provenance_storage_witness()
        pg.sql('ALTER TABLE provenance_minutes ENABLE TRIGGER provenance_minutes_immutable')
        self.assertEqual(pg.provenance_storage_witness()['immutable_trigger_count'], 1)
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

    @unittest.skipUnless(os.environ.get('LAB_GRID_ROOT') and os.environ.get('LAB_MATH_ROOT'),
                         'needs pinned Grid and Math source trees')
    def test_canonical_provenance_readback_and_refusal(self):
        """Synthetic Grid → Math integrity → PG18 → Grid reader, no exchange claim."""
        grid_root = os.environ['LAB_GRID_ROOT']
        math_root = os.environ['LAB_MATH_ROOT']
        expected = os.environ['LAB_MATH_SHA']
        actual = subprocess.check_output(['git', '-C', str(Path(math_root).parent),
                                          'rev-parse', 'HEAD'], text=True).strip()
        self.assertEqual(actual, expected, 'LAB_MATH_SHA_MISMATCH')
        sys.path[:0] = [grid_root, math_root]
        try:
            from market_data.provenance import minute_record, producer, digest, canonical
            from market_data.provenance_gateway import read_snapshot
            start = (int(time.time() * 1000) // 60000 - 1) * 60000
            row = dict(symbol='BTCUSDT', start_ms=start,
                       source_event_start_ms=start + 1, source_event_end_ms=start + 59999,
                       source_provenance=producer('lab-fixture', 'a' * 40,
                           'wss://stream.bybit.com/v5/public/linear'),
                       open=1, high=2, low=1, close=2, buy_volume=1,
                       sell_volume=0, delta=1, trade_count=1, poc_price=2,
                       quality_status='GOOD', quality_reasons=[],
                       levels=[dict(price=2, buy_volume=1, sell_volume=0,
                                    delta=1, volume=1, buy_count=1, sell_count=0)])
            record = minute_record(row, int(time.time() * 1000), 'lab-fixture')
            self.assertEqual(record['status'], 'PARTIAL')
            self.assertFalse(record['coverage']['exchange_completeness_attested'])
            self.assertEqual(digest({k: v for k, v in record.items()
                                     if k != 'dataset_fingerprint'}), record['dataset_fingerprint'])
            self.pg = pg = LabPostgres(BIN, self.root, min_major=MIN).initialize().start()
            pg.provision(canonical_schema())
            witness = pg.provenance_storage_witness()
            self.assertEqual(witness['storage_immutability'],
                             'ROLE_AND_TRIGGER_GUARDED_LAB_ONLY')
            self.assertFalse(witness['execution_authority'])

            def persist(symbol, payload, content_id):
                body = canonical(payload).decode('ascii').replace("'", "''")
                pg.sql("INSERT INTO provenance_minutes(fingerprint,content_id,symbol,start_ms,record)"
                       " VALUES ('" + payload['dataset_fingerprint'] + "','" + content_id +
                       "','" + symbol + "'," + str(start) + ",'" + body + "'::jsonb)",
                       role='lab_writer')

            persist('BTCUSDT', record, digest(row))
            raw = pg.sql("SELECT record::text FROM provenance_minutes "
                         "WHERE symbol='BTCUSDT'", role='lab_reader')
            self.assertEqual(json.loads(raw), record)
            previous = os.environ.get('MARKET_DATA_PROVENANCE_READ')
            os.environ['MARKET_DATA_PROVENANCE_READ'] = '1'
            try:
                def reader(symbol, limit, before_ms):
                    result = pg.sql("SELECT record::text FROM provenance_minutes WHERE symbol='" +
                                    symbol + "' AND start_ms<" + str(before_ms) +
                                    " ORDER BY start_ms DESC LIMIT " + str(limit),
                                    role='lab_reader')
                    return [json.loads(line) for line in result.splitlines() if line]
                good = read_snapshot({}, 'BTCUSDT', 10, None, reader)
                self.assertEqual(good['status'], 'PARTIAL')
                self.assertEqual(good['reason'], 'EXCHANGE_COMPLETENESS_UNATTESTED')
                self.assertFalse(good['execution_authority'])
                self.assertTrue(good['immutable'])
                # A structurally valid JSONB row with forged digest must be
                # rejected by the consumer even though PostgreSQL stores it.
                bad = copy.deepcopy(record)
                bad['symbol'] = 'ETHUSDT'
                bad['dataset_fingerprint'] = 'c' * 64
                persist('ETHUSDT', bad, 'b' * 64)
                rejected = read_snapshot({}, 'ETHUSDT', 10, None, reader)
                self.assertEqual(rejected['reason'], 'SNAPSHOT_INTEGRITY_FAILED')
                self.assertNotIn('rows', rejected)
            finally:
                if previous is None:
                    os.environ.pop('MARKET_DATA_PROVENANCE_READ', None)
                else:
                    os.environ['MARKET_DATA_PROVENANCE_READ'] = previous
        finally:
            del sys.path[:2]

    def test_canonical_grid_producer_retained_without_relabel(self):
        """On pinned Grid+Math, persist original producer bytes via lab writer.

        Do not silently convert legacy bybit-cluster-grid records to the
        canonical market_data producer. This test proves custody of an exact
        source-generated canonical record, not provider authenticity.
        """
        grid_root = os.environ.get('LAB_GRID_ROOT')
        math_root = os.environ.get('LAB_MATH_ROOT')
        if not (grid_root and math_root):
            self.fail('canonical producer requires both pinned source trees')
        sys.path[:0] = [grid_root, math_root]
        try:
            from market_data.provenance import minute_record, producer, digest, canonical
            import uuid
            start = (int(time.time() * 1000) // 60000 - 1) * 60000
            row = dict(symbol='BTCUSDT', start_ms=start,
                source_event_start_ms=start + 1,
                source_event_end_ms=start + 59999,
                source_provenance=producer('lab-fixture', 'a' * 40,
                    'wss://stream.bybit.com/v5/public/linear'),
                open=1, high=2, low=1, close=2, buy_volume=1,
                sell_volume=0, delta=1, trade_count=1, poc_price=2,
                quality_status='GOOD', quality_reasons=[],
                levels=[dict(price=2, buy_volume=1, sell_volume=0, delta=1,
                             volume=1, buy_count=1, sell_count=0)])
            record = minute_record(row, int(time.time() * 1000), 'lab-fixture')
            self.assertEqual(record['producer'], 'market_data')
            self.assertFalse(record['execution_authority'])
            self.pg = pg = LabPostgres(BIN, self.root, min_major=MIN).initialize().start()
            pg.provision(canonical_schema())
            fingerprint = record['dataset_fingerprint']
            content_id = digest(row)
            blob = canonical(record).decode('ascii').replace("'", "''")
            pg.sql("INSERT INTO provenance_minutes"
                   "(fingerprint, content_id, symbol, start_ms, record) VALUES "
                   f"('{fingerprint}', '{content_id}', 'BTCUSDT', {start},"
                   f" '{blob}'::jsonb)", role='lab_writer')
            result = json.loads(pg.sql(
                "SELECT record::text FROM provenance_minutes WHERE fingerprint='"
                + fingerprint + "'", role='lab_reader'))
            self.assertEqual(result['producer'], 'market_data')
            self.assertEqual(result['dataset_fingerprint'], fingerprint)
            self.assertEqual(canonical(result), canonical(record))
            witness = pg.provenance_storage_witness()
            self.assertFalse(witness['execution_authority'])
            self.assertEqual(witness['scope'], 'ISOLATED_LAB_ONLY')
        finally:
            del sys.path[:2]

    def test_occupied_port_and_reserved_5432_fail_closed(self):
        self.pg = pg = LabPostgres(BIN, self.root, min_major=MIN).initialize()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as blocker:
            blocker.bind(('127.0.0.1', pg.port))
            blocker.listen(1)
            with self.assertRaisesRegex(LabAdmissionRejected, 'LAB_PG_START_FAILED'):
                pg.start()
            self.assertFalse(pg.started)
            self.assertEqual(blocker.getsockname()[1], pg.port)
        pg.port = 5432
        with self.assertRaisesRegex(LabAdmissionRejected, 'LAB_PG_PORT_REJECTED'):
            pg.start()

    @unittest.skipIf(os.name == 'nt', 'symlink creation requires privilege on Windows')
    def test_symlink_root_rejected(self):
        self.pg = None
        link = self.root.parent / (self.root.name + '-linked')
        try:
            os.symlink(self.root, link)
            with self.assertRaisesRegex(LabAdmissionRejected, 'ROOT_UNOWNED'):
                LabPostgres(BIN, link, min_major=MIN)
        finally:
            link.unlink(missing_ok=True)

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
