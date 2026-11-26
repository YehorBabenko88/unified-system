"""Owner-only durable LAB cursor reconciliation for C's existing PostgreSQL fence.

This is CLOSED 1m candle custody, not a raw tick/book cursor, nor an
additional market-data writer, Consul grant, exchange client,
service, idempotent insert API, or production startup authorization.
"""
import re

from .lab_simulation_admission import LabAdmissionRejected, need
from .lab_pg_fence import _sha, revalidate_lab_fence, fenced_lab_witness

_STREAM = re.compile(r"[A-Za-z0-9][A-Za-z0-9_:/.-]{0,127}\Z")
_SYMBOL = re.compile(r"[A-Z0-9_.:-]{2,40}\Z")
_RESOURCE = "grid-market-data-primary"


def _integer(value, code, *, allow_zero=False):
    need(type(value) is int and (0 <= value if allow_zero else 0 < value)
         and value < 2**63, code)
    return value


def _record(symbol, start_ms, fingerprint, content_id):
    need(type(symbol) is str and _SYMBOL.fullmatch(symbol) is not None,
         "LAB_CURSOR_SYMBOL_INVALID")
    _integer(start_ms, "LAB_CURSOR_START_INVALID", allow_zero=True)
    return symbol, start_ms, _sha(fingerprint), _sha(content_id)


def _stream(stream_id):
    need(type(stream_id) is str and _STREAM.fullmatch(stream_id) is not None,
         "LAB_CURSOR_STREAM_INVALID")
    return stream_id


def _verified_scope(pg, identity, generation, backend_pid):
    # Revalidate C/E-owned type and one live PostgreSQL backend before every
    # read or CAS. Its result is diagnostic, never Root/Consul authorization.
    receipt = revalidate_lab_fence(
        pg, identity=identity, generation=generation, backend_pid=backend_pid)
    need(receipt["db_backend_observed"] is True
         and receipt["db_fence_current_at_read"] is True
         and receipt["native_writer_admitted"] is False
         and receipt["execution_authority"] is False,
         "LAB_CURSOR_FENCE_UNVERIFIED")
    return receipt


def _condition(receipt):
    # Every interpolated component has already been type/range/regex or UUID4
    # checked by C revalidation. The authoritative second check is in SQL.
    return (
        "f.resource_id='grid-market-data-primary' AND f.active IS TRUE"
        f" AND f.owner='{receipt['owner']}'"
        f" AND f.namespace='{receipt['namespace']}'"
        f" AND f.generation={receipt['generation']}"
        f" AND f.token={receipt['token']}"
        f" AND f.session_id='{receipt['session_id']}'::uuid"
        f" AND f.instance_id='{receipt['instance_id']}'::uuid"
        f" AND f.node_incarnation_id='{receipt['node_incarnation_id']}'::uuid"
        f" AND f.source_sha256='{receipt['source_sha256']}'"
        f" AND f.schema_sha256='{receipt['schema_sha256']}'"
        f" AND f.backend_pid={receipt['backend_pid']}"
        " AND a.pid=f.backend_pid AND a.backend_start=f.backend_start"
        " AND a.usename='lab_writer' AND a.datname=current_database()"
        " AND a.backend_type='client backend'"
    )


def install_lab_checkpoint(pg):
    """Owner-only LAB table, never a second INSERT permission for Grid."""
    pg._verify_owned()
    need(pg.started, "LAB_PG_NOT_STARTED")
    pg._verify_postmaster()
    # C's existing guarded function, not this module, remains sole authority
    # to INSERT immutable market provenance.
    witness = fenced_lab_witness(pg)
    need(witness["direct_writer_insert"] is False
         and witness["writer_exec"] is True
         and witness["reader_exec"] is False
         and witness["fence_owner"] == "lab_owner"
         and witness["function_owner"] == "lab_owner"
         and witness["function_security_definer"] is True
         and witness["function_search_path_pinned"] is True,
         "LAB_CURSOR_BASE_CUSTODY_NOT_VERIFIED")
    pg.sql(r"""
    BEGIN;
    CREATE TABLE public.lab_stream_checkpoint (
      stream_id text PRIMARY KEY
         CHECK(stream_id ~ '^[A-Za-z0-9][A-Za-z0-9_:/.-]{0,127}$'),
      symbol text NOT NULL CHECK(symbol ~ '^[A-Z0-9_.:-]{2,40}$'),
      cursor_value bigint NOT NULL CHECK(cursor_value>=0),
      source_start_ms bigint NOT NULL CHECK(source_start_ms>=0),
      fingerprint text NOT NULL CHECK(fingerprint ~ '^[0-9a-f]{64}$'),
      content_id text NOT NULL CHECK(content_id ~ '^[0-9a-f]{64}$'),
      owner text NOT NULL,
      namespace text NOT NULL,
      generation bigint NOT NULL CHECK(generation>0),
      token bigint NOT NULL CHECK(token>0),
      updated_at timestamptz NOT NULL DEFAULT pg_catalog.clock_timestamp()
    );
    REVOKE ALL ON TABLE public.lab_stream_checkpoint
        FROM PUBLIC,lab_writer,lab_reader;
    CREATE TABLE public.lab_stream_pending (
      stream_id text PRIMARY KEY
         CHECK(stream_id ~ '^[A-Za-z0-9][A-Za-z0-9_:/.-]{0,127}$'),
      symbol text NOT NULL CHECK(symbol ~ '^[A-Z0-9_.:-]{2,40}$'),
      start_ms bigint NOT NULL CHECK(start_ms>=0 AND start_ms%60000=0),
      fingerprint text NOT NULL CHECK(fingerprint ~ '^[0-9a-f]{64}$'),
      content_id text NOT NULL CHECK(content_id ~ '^[0-9a-f]{64}$'),
      owner text NOT NULL,
      namespace text NOT NULL,
      generation bigint NOT NULL CHECK(generation>0),
      token bigint NOT NULL CHECK(token>0),
      source_sha256 text NOT NULL CHECK(source_sha256 ~ '^[0-9a-f]{64}$'),
      schema_sha256 text NOT NULL CHECK(schema_sha256 ~ '^[0-9a-f]{64}$'),
      created_at timestamptz NOT NULL DEFAULT pg_catalog.clock_timestamp()
    );
    REVOKE ALL ON TABLE public.lab_stream_pending
        FROM PUBLIC,lab_writer,lab_reader;
    COMMIT;
    """)
    for table in ("lab_stream_checkpoint", "lab_stream_pending"):
        for role in ("lab_writer", "lab_reader"):
            for action in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                need(pg.sql(
                    f"SELECT has_table_privilege('{role}',"
                    f"'public.{table}','{action}')") == "f",
                    "LAB_CURSOR_PUBLIC_PERMISSION_BYPASS")
    return pg


def read_committed_lab_minute(pg, *, identity, generation, backend_pid,
                              symbol, start_ms, fingerprint, content_id):
    """Exact immutable readback; MISSING and CONFLICT remain unacknowledged.

    This is a LAB-only diagnostic. The upstream collector MUST pause on any
    unknown outcome and reconcile under freshly validated Root/C authority.
    """
    receipt = _verified_scope(pg, identity, generation, backend_pid)
    symbol, start_ms, fingerprint, content_id = _record(
        symbol, start_ms, fingerprint, content_id)
    c = _condition(receipt)
    result = pg.sql(
        "WITH active AS ("
        " SELECT f.resource_id FROM public.lab_writer_fence f"
        " JOIN pg_catalog.pg_stat_activity a ON a.pid=f.backend_pid"
        f" WHERE {c} FOR SHARE OF f)"
        " SELECT CASE"
        " WHEN NOT EXISTS (SELECT 1 FROM active) THEN 'DENIED'"
        " WHEN EXISTS (SELECT 1 FROM public.provenance_minutes p"
        f" WHERE p.fingerprint='{fingerprint}'"
        f" AND p.content_id='{content_id}'"
        f" AND p.symbol='{symbol}' AND p.start_ms={start_ms}"
        f" AND p.record->>'dataset_fingerprint'='{fingerprint}')"
        " AND NOT EXISTS (SELECT 1 FROM public.provenance_minutes p_other"
        f" WHERE p_other.symbol='{symbol}' AND p_other.start_ms={start_ms}"
        f" AND (p_other.fingerprint<>'{fingerprint}'"
        f" OR p_other.content_id<>'{content_id}')) THEN 'MATCH'"
        " WHEN EXISTS (SELECT 1 FROM public.provenance_minutes p"
        f" WHERE p.fingerprint='{fingerprint}'"
        f" OR (p.symbol='{symbol}' AND p.start_ms={start_ms}))"
        " THEN 'CONFLICT' ELSE 'MISSING' END"
    )
    need(result != "DENIED", "LAB_CURSOR_STALE_OWNER")
    need(result in ("MATCH", "CONFLICT", "MISSING"),
         "LAB_CURSOR_RECONCILIATION_INVALID")
    return {"schema":"lab-pg-committed-readback.v1",
            "scope":"ISOLATED_LAB_ONLY",
            "status":result,"resource_id":_RESOURCE,
            "symbol":symbol,"start_ms":start_ms,
            "fingerprint":fingerprint,"content_id":content_id,
            "native_admitted":False,"execution_authority":False,
            "trading_authorized":False,"paper_admitted":False}


def commit_verified_lab_cursor(pg, *, identity, generation, backend_pid,
                                stream_id, cursor, symbol, start_ms,
                                fingerprint, content_id):
    """Owner-only durable monotonic CAS after *exact* committed row readback.

    A closed 1m cursor advances only if its immutable row exists and the
    same E identity and actual PG backend are current while the DB holds the
    fence row lock. It does NOT prove contiguous exchange coverage.
    """
    receipt = _verified_scope(pg, identity, generation, backend_pid)
    stream_id = _stream(stream_id)
    cursor = _integer(cursor, "LAB_CURSOR_NOT_MONOTONIC", allow_zero=True)
    symbol, start_ms, fingerprint, content_id = _record(
        symbol, start_ms, fingerprint, content_id)
    # This C table tracks CLOSED 1m candle start_ms, not a synthetic cursor
    # claiming completeness of tick/book feeds. A later minute may only be
    # acknowledged if contiguous with the last committed 1m checkpoint.
    need(cursor == start_ms and start_ms % 60000 == 0,
         "LAB_CURSOR_CLOSED_MINUTE_REQUIRED")
    c = _condition(receipt)
    result = pg.sql(
        "WITH active AS ("
        " SELECT f.* FROM public.lab_writer_fence f"
        " JOIN pg_catalog.pg_stat_activity a ON a.pid=f.backend_pid"
        f" WHERE {c} FOR UPDATE OF f),"
        " committed AS ("
        " SELECT p.fingerprint,p.content_id FROM public.provenance_minutes p"
        f" WHERE p.fingerprint='{fingerprint}'"
        f" AND p.content_id='{content_id}'"
        f" AND p.symbol='{symbol}' AND p.start_ms={start_ms}"
        f" AND p.record->>'dataset_fingerprint'='{fingerprint}'"
        " AND NOT EXISTS (SELECT 1 FROM public.provenance_minutes p_other"
        f" WHERE p_other.symbol='{symbol}' AND p_other.start_ms={start_ms}"
        f" AND (p_other.fingerprint<>'{fingerprint}'"
        f" OR p_other.content_id<>'{content_id}'))"
        "), acknowledged AS ("
        " INSERT INTO public.lab_stream_checkpoint("
        "stream_id,symbol,cursor_value,source_start_ms,fingerprint,content_id,"
        "owner,namespace,generation,token)"
        f" SELECT '{stream_id}','{symbol}',{cursor},{start_ms},"
        "p.fingerprint,p.content_id,"
        "f.owner,f.namespace,f.generation,f.token"
        " FROM active f CROSS JOIN committed p"
        # PostgreSQL INSERT..SELECT..ON CONFLICT parser needs an explicit
        # SELECT predicate to disambiguate ON from a JOIN clause.
        " WHERE true"
        " ON CONFLICT(stream_id) DO UPDATE SET"
        " cursor_value=EXCLUDED.cursor_value,"
        " source_start_ms=EXCLUDED.source_start_ms,"
        " fingerprint=EXCLUDED.fingerprint,content_id=EXCLUDED.content_id,"
        " generation=EXCLUDED.generation,token=EXCLUDED.token,"
        " updated_at=pg_catalog.clock_timestamp()"
        " WHERE public.lab_stream_checkpoint.owner=EXCLUDED.owner"
        " AND public.lab_stream_checkpoint.namespace=EXCLUDED.namespace"
        " AND public.lab_stream_checkpoint.symbol=EXCLUDED.symbol"
        " AND public.lab_stream_checkpoint.cursor_value+60000=EXCLUDED.cursor_value"
        " AND public.lab_stream_checkpoint.generation<=EXCLUDED.generation"
        " AND public.lab_stream_checkpoint.token<=EXCLUDED.token"
        " RETURNING cursor_value)"
        " SELECT cursor_value FROM acknowledged"
    )
    need(result == str(cursor), "LAB_CURSOR_CAS_OR_READBACK_DENIED")
    return {"schema":"lab-pg-durable-cursor.v1",
            "scope":"ISOLATED_LAB_ONLY", "stream_id":stream_id,
            "cursor":cursor,"generation":generation,"token":identity.token,
            "fingerprint":fingerprint,"content_id":content_id,
            "committed_record_verified":True,
            "contiguous_source_coverage_attested":False,
            "native_admitted":False,"execution_authority":False,
            "trading_authorized":False,"paper_admitted":False}


def read_lab_cursor(pg, *, stream_id):
    """Read-only owner-side WAL cursor state; never bearer or permission."""
    pg._verify_owned()
    need(pg.started, "LAB_PG_NOT_STARTED")
    pg._verify_postmaster()
    stream_id = _stream(stream_id)
    result = pg.sql(
        "WITH state AS ("
        " SELECT c.cursor_value,"
        " (p.fingerprint IS NOT NULL) AS matched"
        " FROM public.lab_stream_checkpoint c"
        " LEFT JOIN public.provenance_minutes p"
        " ON p.fingerprint=c.fingerprint AND p.content_id=c.content_id"
        " AND p.symbol=c.symbol AND p.start_ms=c.source_start_ms"
        " AND p.record->>'dataset_fingerprint'=c.fingerprint"
        " AND NOT EXISTS (SELECT 1 FROM public.provenance_minutes p_other"
        " WHERE p_other.symbol=c.symbol"
        " AND p_other.start_ms=c.source_start_ms"
        " AND (p_other.fingerprint<>c.fingerprint"
        " OR p_other.content_id<>c.content_id))"
        f" WHERE c.stream_id='{stream_id}')"
        " SELECT COALESCE((SELECT CASE WHEN matched"
        " THEN cursor_value::text ELSE 'CORRUPT' END FROM state),'ABSENT')"
    )
    need(result != "CORRUPT", "LAB_CURSOR_DURABLE_RECORD_CORRUPT")
    if result == "ABSENT":
        return None
    try:
        value = int(result)
    except (TypeError, ValueError) as exc:
        raise LabAdmissionRejected("LAB_CURSOR_STATE_INVALID") from exc
    return _integer(value, "LAB_CURSOR_STATE_INVALID", allow_zero=True)


def verify_existing_lab_checkpoint(pg, *, identity, generation, backend_pid,
                                   stream_id, symbol, start_ms,
                                   fingerprint, content_id):
    """Read-only LAB reconciliation after an ambiguous checkpoint response.

    This NEVER executes INSERT/UPDATE, advances a cursor or admits a writer.
    It proves both current C fence/back-end and the exact existing confirmed
    record before a B caller may request conditional pending clear.
    """
    receipt=_verified_scope(pg,identity,generation,backend_pid)
    stream_id=_stream(stream_id)
    symbol,start_ms,fingerprint,content_id=_record(
        symbol,start_ms,fingerprint,content_id)
    c=_condition(receipt)
    result=pg.sql(
        "WITH active AS ("
        " SELECT f.resource_id FROM public.lab_writer_fence f"
        " JOIN pg_catalog.pg_stat_activity a ON a.pid=f.backend_pid"
        f" WHERE {c} FOR SHARE OF f),"
        " checkpoint AS ("
        " SELECT k.stream_id FROM public.lab_stream_checkpoint k"
        " JOIN public.provenance_minutes p"
        " ON p.fingerprint=k.fingerprint AND p.content_id=k.content_id"
        " AND p.symbol=k.symbol AND p.start_ms=k.source_start_ms"
        " AND p.record->>'dataset_fingerprint'=k.fingerprint"
        f" WHERE k.stream_id='{stream_id}'"
        f" AND k.symbol='{symbol}'"
        f" AND k.cursor_value={start_ms}"
        f" AND k.source_start_ms={start_ms}"
        f" AND k.fingerprint='{fingerprint}'"
        f" AND k.content_id='{content_id}'"
        " AND k.owner=(SELECT f.owner FROM public.lab_writer_fence f"
        " WHERE f.resource_id='grid-market-data-primary')"
        " AND k.namespace=(SELECT f.namespace FROM public.lab_writer_fence f"
        " WHERE f.resource_id='grid-market-data-primary')"
        " AND k.generation<=(SELECT f.generation"
        " FROM public.lab_writer_fence f"
        " WHERE f.resource_id='grid-market-data-primary')"
        " AND k.token<=(SELECT f.token FROM public.lab_writer_fence f"
        " WHERE f.resource_id='grid-market-data-primary')"
        " AND NOT EXISTS (SELECT 1 FROM public.provenance_minutes p_other"
        " WHERE p_other.symbol=k.symbol"
        " AND p_other.start_ms=k.source_start_ms"
        " AND (p_other.fingerprint<>k.fingerprint"
        " OR p_other.content_id<>k.content_id))),"
        " relevant_pending AS ("
        " SELECT q.stream_id FROM public.lab_stream_pending q"
        f" WHERE q.stream_id='{stream_id}'"
        f" AND q.symbol='{symbol}'"
        f" AND q.start_ms={start_ms}"
        f" AND q.fingerprint='{fingerprint}'"
        f" AND q.content_id='{content_id}'"
        " AND q.owner=(SELECT f.owner FROM public.lab_writer_fence f"
        " WHERE f.resource_id='grid-market-data-primary')"
        " AND q.namespace=(SELECT f.namespace FROM public.lab_writer_fence f"
        " WHERE f.resource_id='grid-market-data-primary')"
        " AND q.source_sha256=(SELECT f.source_sha256"
        " FROM public.lab_writer_fence f"
        " WHERE f.resource_id='grid-market-data-primary')"
        " AND q.schema_sha256=(SELECT f.schema_sha256"
        " FROM public.lab_writer_fence f"
        " WHERE f.resource_id='grid-market-data-primary')"
        " AND q.generation<=(SELECT f.generation"
        " FROM public.lab_writer_fence f"
        " WHERE f.resource_id='grid-market-data-primary')"
        " AND q.token<=(SELECT f.token FROM public.lab_writer_fence f"
        " WHERE f.resource_id='grid-market-data-primary'))"
        " SELECT CASE"
        " WHEN NOT EXISTS (SELECT 1 FROM active) THEN 'DENIED'"
        " WHEN EXISTS (SELECT 1 FROM checkpoint)"
        " AND EXISTS (SELECT 1 FROM relevant_pending)"
        " THEN 'EXACT_ALREADY_ACKNOWLEDGED'"
        " ELSE 'UNRESOLVED' END"
    )
    need(result!="DENIED","LAB_CURSOR_STALE_OWNER")
    need(result in ("EXACT_ALREADY_ACKNOWLEDGED","UNRESOLVED"),
         "LAB_CURSOR_EXISTING_ACK_INVALID")
    return {
        "schema":"lab-pg-exact-checkpoint-reconciliation.v1",
        "scope":"ISOLATED_LAB_ONLY",
        "state":result,
        "stream_id":stream_id,
        "symbol":symbol,
        "start_ms":start_ms,
        "fingerprint":fingerprint,
        "content_id":content_id,
        "native_admitted":False,
        "execution_authority":False,
        "trading_authorized":False,
        "paper_admitted":False,
    }


def read_lab_checkpoint(pg, *, stream_id):
    """Owner diagnostic: confirmed cursor plus immutable source identity."""
    stream_id=_stream(stream_id)
    cursor=read_lab_cursor(pg,stream_id=stream_id)
    if cursor is None:
        return None
    result=pg.sql(
        "SELECT symbol,source_start_ms,fingerprint,content_id"
        " FROM public.lab_stream_checkpoint"
        f" WHERE stream_id='{stream_id}' AND cursor_value={cursor}"
    )
    fields=result.split("|")
    need(len(fields)==4, "LAB_CURSOR_METADATA_CORRUPT")
    symbol,ms,fp,cid=fields
    _record(symbol,int(ms),fp,cid)
    need(int(ms)==cursor, "LAB_CURSOR_METADATA_CORRUPT")
    return {"symbol":symbol,"start_ms":cursor,
            "fingerprint":fp,"content_id":cid,
            "scope":"ISOLATED_LAB_ONLY","native_admitted":False}


def read_lab_pending(pg, *, stream_id):
    """Owner diagnostic: durable unresolved minute survives process/WAL crash."""
    pg._verify_owned()
    need(pg.started,"LAB_PG_NOT_STARTED")
    pg._verify_postmaster()
    stream_id=_stream(stream_id)
    result=pg.sql(
        "SELECT symbol,start_ms,fingerprint,content_id,"
        "generation,token,source_sha256,schema_sha256"
        " FROM public.lab_stream_pending"
        f" WHERE stream_id='{stream_id}'"
    )
    if result=="":
        return None
    fields=result.split("|")
    need(len(fields)==8,"LAB_PENDING_STATE_CORRUPT")
    symbol,ms,fp,cid,gen,tok,source,schema=fields
    symbol,ms,fp,cid=_record(symbol,int(ms),fp,cid)
    return {"schema":"lab-pg-pending-minute.v1","scope":"ISOLATED_LAB_ONLY",
            "symbol":symbol,"start_ms":ms,"fingerprint":fp,
            "content_id":cid,"generation":_integer(int(gen),"LAB_PENDING_GENERATION"),
            "token":_integer(int(tok),"LAB_PENDING_TOKEN"),
            "source_sha256":_sha(source),"schema_sha256":_sha(schema),
            "native_admitted":False,"execution_authority":False,
            "trading_authorized":False}


def append_lab_pending(pg, *, identity, generation, backend_pid,
                       stream_id, symbol, start_ms, fingerprint, content_id):
    """Owner-only durable pending marker *before* canonical B writer attempt.

    No INSERT into provenance_minutes. Any crash/uncertain commit preserves
    this marker until a new verified owner reconciles immutable source bytes.
    """
    receipt=_verified_scope(pg,identity,generation,backend_pid)
    stream_id=_stream(stream_id)
    symbol,start_ms,fingerprint,content_id=_record(
        symbol,start_ms,fingerprint,content_id)
    need(start_ms%60000==0,"LAB_PENDING_CLOSED_MINUTE_REQUIRED")
    c=_condition(receipt)
    result=pg.sql(
        "WITH active AS ("
        " SELECT f.* FROM public.lab_writer_fence f"
        " JOIN pg_catalog.pg_stat_activity a ON a.pid=f.backend_pid"
        f" WHERE {c} FOR UPDATE OF f),"
        " allowed AS ("
        " SELECT f.* FROM active f"
        " WHERE NOT EXISTS ("
        " SELECT 1 FROM public.lab_stream_checkpoint k"
        f" WHERE k.stream_id='{stream_id}'"
        f" AND (k.symbol<>'{symbol}'"
        f" OR k.cursor_value+60000<>{start_ms}))),"
        " queued AS ("
        " INSERT INTO public.lab_stream_pending("
        "stream_id,symbol,start_ms,fingerprint,content_id,"
        "owner,namespace,generation,token,source_sha256,schema_sha256)"
        f" SELECT '{stream_id}','{symbol}',{start_ms},"
        f"'{fingerprint}','{content_id}',"
        "f.owner,f.namespace,f.generation,f.token,"
        "f.source_sha256,f.schema_sha256 FROM allowed f"
        " WHERE true ON CONFLICT(stream_id) DO NOTHING"
        " RETURNING stream_id)"
        " SELECT stream_id FROM queued"
    )
    need(result==stream_id,"LAB_PENDING_ALREADY_OPEN_OR_STALE")
    return {"schema":"lab-pg-pending-append.v1","scope":"ISOLATED_LAB_ONLY",
            "stream_id":stream_id,"start_ms":start_ms,
            "native_admitted":False,"trading_authorized":False}


def clear_verified_lab_pending(pg, *, identity, generation, backend_pid,
                               stream_id):
    """Only delete a pending marker after matching immutable checkpoint ACK.

    A newly fenced backend can reconcile an old-generation pending marker,
    but a source/schema pin change cannot silently adopt the record.
    """
    receipt=_verified_scope(pg,identity,generation,backend_pid)
    stream_id=_stream(stream_id)
    c=_condition(receipt)
    result=pg.sql(
        "WITH active AS ("
        " SELECT f.* FROM public.lab_writer_fence f"
        " JOIN pg_catalog.pg_stat_activity a ON a.pid=f.backend_pid"
        f" WHERE {c} FOR UPDATE OF f),"
        " cleared AS ("
        " DELETE FROM public.lab_stream_pending p"
        " USING active f,public.lab_stream_checkpoint k"
        f" WHERE p.stream_id='{stream_id}'"
        " AND k.stream_id=p.stream_id"
        " AND k.symbol=p.symbol"
        " AND k.source_start_ms=p.start_ms"
        " AND k.cursor_value=p.start_ms"
        " AND k.fingerprint=p.fingerprint"
        " AND k.content_id=p.content_id"
        " AND p.owner=f.owner AND p.namespace=f.namespace"
        " AND p.source_sha256=f.source_sha256"
        " AND p.schema_sha256=f.schema_sha256"
        " AND p.generation<=f.generation AND p.token<=f.token"
        " AND k.generation<=f.generation AND k.token<=f.token"
        # The conditional DELETE must independently prove the same exact
        # immutable market row and lack of same-minute competing provenance.
        # An earlier readback outside this transaction is not sufficient.
        " AND EXISTS (SELECT 1 FROM public.provenance_minutes recorded"
        " WHERE recorded.symbol=p.symbol AND recorded.start_ms=p.start_ms"
        " AND recorded.fingerprint=p.fingerprint"
        " AND recorded.content_id=p.content_id"
        " AND recorded.record->>'dataset_fingerprint'=p.fingerprint)"
        " AND NOT EXISTS (SELECT 1 FROM public.provenance_minutes other"
        " WHERE other.symbol=p.symbol AND other.start_ms=p.start_ms"
        " AND (other.fingerprint<>p.fingerprint"
        " OR other.content_id<>p.content_id))"
        " RETURNING p.stream_id)"
        " SELECT stream_id FROM cleared"
    )
    need(result==stream_id,"LAB_PENDING_CLEAR_UNVERIFIED")
    return True
