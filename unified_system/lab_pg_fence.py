"""LAB-only PostgreSQL resource-side fence for the canonical market-data writer.

This is NOT a native Root/Consul admission implementation. A trusted LAB
supervisor must independently prove prior-process quiescence before claiming.
No user databases, external PostgreSQL instance or trading endpoints.
"""
import re
import uuid

from .lab_simulation_admission import LabAdmissionRejected, need

_SHA64 = re.compile(r"[0-9a-f]{64}\Z")
_RESOURCE = "grid-market-data-primary"
_SIGNATURE = ("bigint,bigint,uuid,uuid,uuid,text,text,"
              "text,text,text,bigint,jsonb")

def _id(value):
    need(type(value) is str, "LAB_FENCE_ID_INVALID")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise LabAdmissionRejected("LAB_FENCE_ID_INVALID") from exc
    need(str(parsed) == value and parsed.version == 4, "LAB_FENCE_ID_INVALID")
    return value

def _sha(value):
    need(type(value) is str and _SHA64.fullmatch(value) is not None,
         "LAB_FENCE_SHA_INVALID")
    return value

def install_lab_fence(pg):
    """One atomic owner-only install: base INSERT is revoked before function grant."""
    pg._verify_owned()
    need(pg.started, "LAB_PG_NOT_STARTED")
    pg._verify_postmaster()
    pg.sql(r"""
    BEGIN;
    LOCK TABLE public.provenance_minutes IN ACCESS EXCLUSIVE MODE;
    CREATE TABLE public.lab_writer_fence (
      resource_id text PRIMARY KEY CHECK(resource_id='grid-market-data-primary'),
      generation bigint NOT NULL CHECK(generation>0),
      token bigint NOT NULL CHECK(token>0),
      session_id uuid NOT NULL,
      instance_id uuid NOT NULL,
      node_incarnation_id uuid NOT NULL,
      source_sha256 text NOT NULL CHECK(source_sha256 ~ '^[0-9a-f]{64}$'),
      schema_sha256 text NOT NULL CHECK(schema_sha256 ~ '^[0-9a-f]{64}$'),
      backend_pid integer NOT NULL CHECK(backend_pid>0),
      backend_start timestamptz NOT NULL,
      active boolean NOT NULL
    );
    REVOKE ALL ON TABLE public.lab_writer_fence FROM PUBLIC, lab_writer, lab_reader;
    REVOKE INSERT ON TABLE public.provenance_minutes FROM lab_writer;
    CREATE FUNCTION public.lab_fenced_insert(
       p_generation bigint,p_token bigint,p_session uuid,p_instance uuid,
       p_node uuid,p_source text,p_schema text,p_fingerprint text,
       p_content_id text,p_symbol text,p_start_ms bigint,p_record jsonb)
    RETURNS void LANGUAGE plpgsql SECURITY DEFINER
    SET search_path = pg_catalog AS $fence$
    DECLARE live public.lab_writer_fence%ROWTYPE;
    DECLARE actual_backend_start timestamptz;
    BEGIN
      IF session_user <> 'lab_writer' THEN
        RAISE EXCEPTION 'LAB_FENCE_CALLER_DENIED';
      END IF;
      SELECT backend_start INTO actual_backend_start
      FROM pg_catalog.pg_stat_activity
      WHERE pid=pg_catalog.pg_backend_pid() AND usename=session_user;
      SELECT * INTO live FROM public.lab_writer_fence
        WHERE resource_id='grid-market-data-primary' FOR UPDATE;
      IF NOT FOUND OR live.active IS NOT TRUE
         OR live.generation IS DISTINCT FROM p_generation
         OR live.token IS DISTINCT FROM p_token
         OR live.session_id IS DISTINCT FROM p_session
         OR live.instance_id IS DISTINCT FROM p_instance
         OR live.node_incarnation_id IS DISTINCT FROM p_node
         OR live.source_sha256 IS DISTINCT FROM p_source
         OR live.schema_sha256 IS DISTINCT FROM p_schema
         OR live.backend_pid IS DISTINCT FROM pg_catalog.pg_backend_pid()
         OR live.backend_start IS DISTINCT FROM actual_backend_start
         OR actual_backend_start IS NULL THEN
        RAISE EXCEPTION 'LAB_FENCE_STALE_OR_FOREIGN_WRITER';
      END IF;
      INSERT INTO public.provenance_minutes(
         fingerprint,content_id,symbol,start_ms,record)
      VALUES(p_fingerprint,p_content_id,p_symbol,p_start_ms,p_record);
    END $fence$;
    REVOKE ALL ON FUNCTION public.lab_fenced_insert(
       bigint,bigint,uuid,uuid,uuid,text,text,text,text,text,bigint,jsonb)
       FROM PUBLIC;
    GRANT EXECUTE ON FUNCTION public.lab_fenced_insert(
       bigint,bigint,uuid,uuid,uuid,text,text,text,text,text,bigint,jsonb)
       TO lab_writer;
    COMMIT;
    """)
    need(pg.sql("SELECT has_table_privilege('lab_writer',"
                "'public.provenance_minutes','INSERT')") == "f",
         "LAB_FENCE_DIRECT_INSERT_BYPASS")
    return pg

def claim_lab_fence(pg, *, generation, token, session_id, instance_id,
                    node_incarnation_id, source_sha256, schema_sha256,
                    backend_pid, previous_quiescence_verified=False):
    """LAB CAS, not production authority. Backend identity comes from PG itself."""
    pg._verify_owned()
    need(pg.started, "LAB_PG_NOT_STARTED")
    pg._verify_postmaster()
    need(previous_quiescence_verified is True, "LAB_FENCE_QUIESCENCE_REQUIRED")
    need(type(generation) is int and 0 < generation < 2**63
         and type(token) is int and 0 < token < 2**63,
         "LAB_FENCE_TOKEN_INVALID")
    need(type(backend_pid) is int and 0 < backend_pid < 2**31,
         "LAB_FENCE_BACKEND_INVALID")
    ids = tuple(map(_id, (session_id, instance_id, node_incarnation_id)))
    sha1, sha2 = _sha(source_sha256), _sha(schema_sha256)
    # A claimed PID must be an existing lab_writer DB connection. A current
    # backend_start is stored by PostgreSQL, not asserted in any client JSON.
    sql = (
        "INSERT INTO public.lab_writer_fence("
        "resource_id,generation,token,session_id,instance_id,"
        "node_incarnation_id,source_sha256,schema_sha256,"
        "backend_pid,backend_start,active)"
        " SELECT 'grid-market-data-primary',"
        f"{generation},{token},'{ids[0]}'::uuid,'{ids[1]}'::uuid,"
        f"'{ids[2]}'::uuid,'{sha1}','{sha2}',pid,backend_start,true"
        " FROM pg_catalog.pg_stat_activity"
        f" WHERE pid={backend_pid} AND usename='lab_writer'"
        " ON CONFLICT(resource_id) DO UPDATE SET"
        " generation=EXCLUDED.generation,token=EXCLUDED.token,"
        " session_id=EXCLUDED.session_id,instance_id=EXCLUDED.instance_id,"
        " node_incarnation_id=EXCLUDED.node_incarnation_id,"
        " source_sha256=EXCLUDED.source_sha256,"
        " schema_sha256=EXCLUDED.schema_sha256,"
        " backend_pid=EXCLUDED.backend_pid,"
        " backend_start=EXCLUDED.backend_start,active=true"
        " WHERE public.lab_writer_fence.active=false"
        " AND EXCLUDED.token>public.lab_writer_fence.token"
        " AND EXCLUDED.generation>public.lab_writer_fence.generation"
        # A caller-controlled quiescence flag is NOT enough: postgres
        # independently verifies the original backend instance is extinct.
        " AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_stat_activity a"
        " WHERE a.pid=public.lab_writer_fence.backend_pid"
        " AND a.backend_start=public.lab_writer_fence.backend_start)"
        " RETURNING generation"
    )
    need(pg.sql(sql) == str(generation), "LAB_FENCE_CLAIM_DENIED")
    return True

def revoke_lab_fence(pg, *, generation, token):
    """Owner-only revocation; high-water persists across restart."""
    pg._verify_owned()
    need(pg.started, "LAB_PG_NOT_STARTED")
    pg._verify_postmaster()
    need(type(generation) is int and generation>0
         and type(token) is int and token>0, "LAB_FENCE_TOKEN_INVALID")
    result = pg.sql(
        "UPDATE public.lab_writer_fence SET active=false"
        f" WHERE resource_id='grid-market-data-primary' AND active=true"
        f" AND generation={generation} AND token={token}"
        " RETURNING generation")
    need(result == str(generation), "LAB_FENCE_REVOKE_DENIED")
    return True

def fence_identity():
    """Immutable fixture identity; caller still needs independent Root authority."""
    return {"resource_id": _RESOURCE, "schema": "lab-postgres-writer-fence.v1",
            "scope": "ISOLATED_LAB_ONLY", "execution_authority": False,
            "trading_authorized": False, "native_admission": False}

def fenced_lab_witness(pg):
    """Independent owner catalogue check for opt-in fenced LAB, not production."""
    import json
    pg._verify_owned()
    need(pg.started, "LAB_PG_NOT_STARTED")
    pg._verify_postmaster()
    definition = ("public.lab_fenced_insert(bigint,bigint,uuid,uuid,uuid,"
                  "text,text,text,text,text,bigint,jsonb)")
    result = pg.sql("""
       SELECT json_build_object(
           'schema','lab-postgres-fenced-custody.v1',
           'scope','ISOLATED_LAB_ONLY',
           'direct_writer_insert',
              has_table_privilege('lab_writer','public.provenance_minutes','INSERT'),
           'writer_exec',
              has_function_privilege('lab_writer',
                'public.lab_fenced_insert(bigint,bigint,uuid,uuid,uuid,text,text,text,text,text,bigint,jsonb)',
                'EXECUTE'),
           'reader_exec',
              has_function_privilege('lab_reader',
                'public.lab_fenced_insert(bigint,bigint,uuid,uuid,uuid,text,text,text,text,text,bigint,jsonb)',
                'EXECUTE'),
           'fence_writer_select',
              has_table_privilege('lab_writer','public.lab_writer_fence','SELECT'),
           'fence_writer_update',
              has_table_privilege('lab_writer','public.lab_writer_fence','UPDATE'),
           'fence_reader_select',
              has_table_privilege('lab_reader','public.lab_writer_fence','SELECT'),
           'function_owner', pg_get_userbyid(p.proowner),
           'function_security_definer', p.prosecdef,
           'function_search_path_pinned', p.proconfig @> ARRAY['search_path=pg_catalog'],
           'fence_owner',
              (SELECT pg_get_userbyid(c.relowner) FROM pg_class c
               WHERE c.oid='public.lab_writer_fence'::regclass),
           'fence_state_count',(SELECT count(*) FROM public.lab_writer_fence)
       )
       FROM pg_proc p
       WHERE p.oid=
         'public.lab_fenced_insert(bigint,bigint,uuid,uuid,uuid,text,text,text,text,text,bigint,jsonb)'::regprocedure
    """)
    try:
        witness = json.loads(result)
    except (TypeError, ValueError) as exc:
        raise LabAdmissionRejected("LAB_FENCE_WITNESS_INVALID") from exc
    need(type(witness) is dict
         and witness.get("schema") == "lab-postgres-fenced-custody.v1"
         and witness.get("scope") == "ISOLATED_LAB_ONLY"
         and witness.get("direct_writer_insert") is False
         and witness.get("writer_exec") is True
         and witness.get("reader_exec") is False
         and witness.get("fence_writer_select") is False
         and witness.get("fence_writer_update") is False
         and witness.get("fence_reader_select") is False
         and witness.get("function_owner") == "lab_owner"
         and witness.get("function_security_definer") is True
         and witness.get("function_search_path_pinned") is True
         and witness.get("fence_owner") == "lab_owner"
         and type(witness.get("fence_state_count")) is int
         and witness["fence_state_count"] <= 1,
         "LAB_FENCE_CUSTODY_NOT_VERIFIED")
    witness["execution_authority"] = False
    witness["trading_authorized"] = False
    witness["source_authenticity"] = "NOT_INDEPENDENTLY_ATTESTED"
    return witness
