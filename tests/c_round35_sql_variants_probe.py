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
        # IMPORTANT: original revalidate_lab_fence() must use the existing
        # independently connected C owner. It cannot use the test transaction:
        # otherwise the uncommitted active=false is already visible during
        # preflight, and the snapshot-race test never reaches the original
        # source query whose own fence witness we are qualifying.
        if "relevant_pending AS (" not in statement:
            return self.original_pg.sql(statement, **kwargs)
        self.queries.append(statement)
        # ONLY the full, original verify_existing_lab_checkpoint SQL is run
        # on the injected connection. This sees transaction-local competing
        # provenance / inactive fence while the independent owner preflight
        # sees the last COMMITTED PostgreSQL state.
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

        # A *real* second immutable provenance row for the SAME minute
        # must invalidate an otherwise matching checkpoint. The conflicting
        # row is deliberately never committed: original production immutability
        # prohibits later deletion, and the single C native test must leave
        # the positive pending-clear fixture intact for the original assertions.
        # PostgreSQL enforces this against the actual original C schema/DDL,
        # not J's simplified fixture or a mocked SELECT result.
        competing_fp, competing_cid = "9" * 64, "8" * 64
        with connection.cursor() as cursor:
            cursor.execute("BEGIN")
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO public.provenance_minutes("
                    "fingerprint,content_id,symbol,start_ms,record)"
                    " VALUES (%s,%s,%s,%s,%s::jsonb)",
                    (competing_fp, competing_cid, "BTCUSDT", start_ms,
                     '{"dataset_fingerprint":"' + competing_fp + '"}'))
            raw = _NativeRawSql(test.pg, connection)
            outcome = "NOT_EXECUTED"
            try:
                observed = current.verify_existing_lab_checkpoint(raw, **kwargs)
                test.assertEqual(observed["state"], "UNRESOLVED")
                test.assertIs(observed["execution_authority"], False)
                outcome = "CONFLICTING_MINUTE_UNRESOLVED"
            finally:
                for statement in raw.queries:
                    print("C35_NATIVE_PG18_CONFLICT "
                          f"source={CURRENT_BLOB} "
                          f"sql_sha256={hashlib.sha256(statement.encode('utf-8')).hexdigest()} "
                          f"chars={len(statement)} outcome={outcome}", flush=True)
            test.assertEqual(len(raw.queries), 1)
        finally:
            # Even on a test assertion/SQL exception, do not persist
            # synthetic competing provenance or remove immutable real rows.
            with connection.cursor() as cursor:
                cursor.execute("ROLLBACK")

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM public.provenance_minutes"
                " WHERE fingerprint=%s AND content_id=%s"
                " AND symbol=%s AND start_ms=%s",
                (competing_fp, competing_cid, "BTCUSDT", start_ms))
            test.assertEqual(cursor.fetchone()[0], 0,
                             "C35_CONFLICT_ROW_SURVIVED_ROLLBACK")
        raw = _NativeRawSql(test.pg, connection)
        restored = current.verify_existing_lab_checkpoint(raw, **kwargs)
        test.assertEqual(restored["state"], "EXACT_ALREADY_ACKNOWLEDGED",
                         "C35_ORIGINAL_CHECKPOINT_NOT_RESTORED")

        # The preliminary owner/backend revalidation runs in the original
        # guarded API, but SQL must *independently* enforce the fence at the
        # actual read snapshot. Flip only this disposable owner's fence in
        # an uncommitted transaction. Its separate revalidation connection
        # still sees the previous committed active fence, while the final
        # SQL on THIS connection must see our inactive row and DENY.
        # This verifies no stale preflight receipt becomes a writer permit.
        from unified_system.lab_simulation_admission import LabAdmissionRejected
        with connection.cursor() as cursor:
            cursor.execute("BEGIN")
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE public.lab_writer_fence SET active=false"
                    " WHERE resource_id=%s AND active IS TRUE"
                    " AND generation=%s AND token=%s RETURNING active",
                    ("grid-market-data-primary", 1, identity.token))
                test.assertEqual(cursor.fetchone(), (False,),
                                 "C35_DISPOSABLE_FENCE_TOGGLE_UNVERIFIED")
            raw = _NativeRawSql(test.pg, connection)
            outcome = "NOT_EXECUTED"
            try:
                with test.assertRaisesRegex(
                        LabAdmissionRejected, "LAB_CURSOR_STALE_OWNER"):
                    current.verify_existing_lab_checkpoint(raw, **kwargs)
                outcome = "UNCOMMITTED_INACTIVE_FENCE_DENIED"
            finally:
                for statement in raw.queries:
                    print("C35_NATIVE_PG18_FENCE_NEGATIVE "
                          f"source={CURRENT_BLOB} "
                          f"sql_sha256={hashlib.sha256(statement.encode('utf-8')).hexdigest()} "
                          f"chars={len(statement)} outcome={outcome}", flush=True)
            test.assertEqual(len(raw.queries), 1,
                             "C35_FENCE_NEGATIVE_SQL_NOT_EXECUTED")
        finally:
            # Do not persist a disabled fence or alter another original
            # recovery test. A failed native assertion still attempts
            # rollback, and the test fails if the connection cannot recover.
            with connection.cursor() as cursor:
                cursor.execute("ROLLBACK")

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT active FROM public.lab_writer_fence"
                " WHERE resource_id=%s AND generation=%s AND token=%s",
                ("grid-market-data-primary", 1, identity.token))
            test.assertEqual(cursor.fetchone(), (True,),
                             "C35_DISPOSABLE_FENCE_ROLLBACK_FAILED")
        raw = _NativeRawSql(test.pg, connection)
        restored = current.verify_existing_lab_checkpoint(raw, **kwargs)
        test.assertEqual(restored["state"], "EXACT_ALREADY_ACKNOWLEDGED",
                         "C35_FENCE_ROLLBACK_NOT_RESTORED")
