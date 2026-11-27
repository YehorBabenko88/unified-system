"""ROUND35 C native SQL A/B probe using original pinned source modules only.

Called *inside* the existing 29-case C-owned PG18 lifecycle. This file is not
another PostgreSQL bootstrap, writer, Consul issuer, or admission authority.
"""
import hashlib
import importlib.util
from pathlib import Path

from unified_system import lab_pg_checkpoint as current


LEGACY_BLOB = "cad4ccf970470eb86a487c484cee9be15ea9614d"
CURRENT_BLOB = "076980d9556bf3a685091f16129ef321cb1372be"


def _git_blob_sha(path):
    data = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + bytes((0,)) + data
    ).hexdigest()


class _NativeRawSql:
    """Use original PG-owned cluster and native psycopg, preserving SQLSTATE."""

    def __init__(self, original_pg, connection):
        self.original_pg = original_pg
        self.connection = connection
        self.queries = []

    def __getattr__(self, name):
        return getattr(self.original_pg, name)

    def sql(self, statement, **kwargs):
        if "relevant_pending AS (" in statement:
            self.queries.append(statement)
        with self.connection.cursor() as cursor:
            cursor.execute(statement)
            if cursor.description is None:
                return ""
            row = cursor.fetchone()
            return "" if row is None or row[0] is None else str(row[0])


def exercise_two_pinned_sql_sources(test, *, identity, stream, start_ms,
                                    fingerprint, content_id):
    """Native parse+execute BOTH exact original C/J source variants.

    This is called only while C's legitimate LAB fence/backend and owner-
    inserted checkpoint/pending rows are alive; no synthetic authority is
    manufactured. The negative legacy SQL must fail with PG SQLSTATE 42601;
    the fixed original source must return exact ACK. No mutation is performed.
    """
    root = Path(__file__).resolve().parents[1]
    current_path = root / "unified_system" / "lab_pg_checkpoint.py"
    legacy_path = (root / "upstream" / "c-legacy-checkpoint"
                   / "unified_system" / "lab_pg_checkpoint.py")
    test.assertTrue(legacy_path.is_file(),
                    "C35_PINNED_LEGACY_SOURCE_MISSING")
    test.assertEqual(_git_blob_sha(current_path), CURRENT_BLOB,
                     "C35_CURRENT_SOURCE_BLOB_CHANGED")
    test.assertEqual(_git_blob_sha(legacy_path), LEGACY_BLOB,
                     "C35_LEGACY_SOURCE_BLOB_CHANGED")

    spec = importlib.util.spec_from_file_location(
        "unified_system._c35_original_legacy_checkpoint", legacy_path)
    test.assertIsNotNone(spec)
    test.assertIsNotNone(spec.loader)
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)

    kwargs = dict(identity=identity, generation=1,
                  backend_pid=test.old["backend_pid"],
                  stream_id=stream, symbol="BTCUSDT", start_ms=start_ms,
                  fingerprint=fingerprint, content_id=content_id)
    test.assertEqual(test.pg.major, 18)
    test.assertNotEqual(test.pg.port, 5432)
    # C's public dsn() intentionally refuses lab_owner. The existing
    # disposable fixture has its own owner password, used only over loopback.
    with test.psycopg.connect(host="127.0.0.1", port=test.pg.port,
                              dbname=test.pg.database, user="lab_owner",
                              password=test.pg.passwords["lab_owner"],
                              connect_timeout=5, autocommit=True) as connection:
        for tag, module, expected_blob in (
            ("cad4ccf", legacy, LEGACY_BLOB),
            ("076980d", current, CURRENT_BLOB),
        ):
            raw = _NativeRawSql(test.pg, connection)
            outcome = "NOT_EXECUTED"
            try:
                if tag == "cad4ccf":
                    # A genuine original old-SQL parser failure is an
                    # expected negative result, not a native PASS claim for
                    # the corrected candidate. Preserve the exact SQLSTATE.
                    with test.assertRaises(test.psycopg.errors.SyntaxError) as caught:
                        module.verify_existing_lab_checkpoint(raw, **kwargs)
                    test.assertEqual(caught.exception.sqlstate, "42601")
                    outcome = "EXPECTED_SQLSTATE_42601"
                else:
                    observed = module.verify_existing_lab_checkpoint(raw, **kwargs)
                    test.assertEqual(observed["state"],
                                     "EXACT_ALREADY_ACKNOWLEDGED")
                    test.assertIs(observed["execution_authority"], False)
                    outcome = observed["state"]
            finally:
                # Log the original emitted SQL even if psycopg raises an
                # unexpected SQLSTATE; assertions after finally must not mask
                # the primary database exception.
                for original_sql in raw.queries:
                    digest = hashlib.sha256(original_sql.encode("utf-8")).hexdigest()
                    print("C35_NATIVE_PG18_SQL_VARIANT "
                          f"source={expected_blob} sql_sha256={digest} "
                          f"chars={len(original_sql)} outcome={outcome}", flush=True)
            test.assertEqual(len(raw.queries), 1)
            test.assertIn("FOR SHARE OF f", raw.queries[0])
            test.assertIn("relevant_pending AS (", raw.queries[0])

        # Read-only native negative evidence: a different immutable
        # fingerprint must NOT turn an existing checkpoint into an ACK.
        # It is important that this runs after the positive case while
        # retaining the same actual PostgreSQL fence and backend identity.
        mismatch = dict(kwargs, fingerprint="5" * 64)
        raw = _NativeRawSql(test.pg, connection)
        outcome = "NOT_EXECUTED"
        try:
            observed = current.verify_existing_lab_checkpoint(raw, **mismatch)
            test.assertEqual(observed["state"], "UNRESOLVED")
            test.assertIs(observed["execution_authority"], False)
            outcome = "UNRESOLVED"
        finally:
            for original_sql in raw.queries:
                digest = hashlib.sha256(original_sql.encode("utf-8")).hexdigest()
                print("C35_NATIVE_PG18_NEGATIVE "
                      f"source={CURRENT_BLOB} sql_sha256={digest} "
                      f"chars={len(original_sql)} outcome={outcome}", flush=True)
        test.assertEqual(len(raw.queries), 1)
        test.assertIn("FOR SHARE OF f", raw.queries[0])
