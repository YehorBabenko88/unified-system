"""LAB-only PostgreSQL resource-side fence for the canonical market-data writer.

This is NOT a native Root/Consul admission implementation. A trusted LAB
supervisor must independently prove prior-process quiescence before claiming.
No user databases, external PostgreSQL instance or trading endpoints.
"""
import re
import uuid
import datetime

from .lab_simulation_admission import LabAdmissionRejected, need

_SHA64 = re.compile(r"[0-9a-f]{64}\Z")
_RESOURCE = "grid-market-data-primary"
_OWNER_PATTERN = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
_NAMESPACE_PATTERN = re.compile(r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*\Z")

def _id(value, *, consul_session=False):
    need(type(value) is str, "LAB_FENCE_ID_INVALID")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise LabAdmissionRejected("LAB_FENCE_ID_INVALID") from exc
    # A Consul session identifier is an opaque server-issued UUID-shaped
    # value, not an application UUID4/5 identity. Do not infer lease
    # authority from its version or variant. Keep exact canonical bytes for
    # PostgreSQL uuid binding, and prove the actual lease independently.
    # Instance and node incarnation identities remain strict RFC4122 UUID4.
    if consul_session:
        need(str(parsed) == value, "LAB_FENCE_ID_INVALID")
    else:
        need(str(parsed) == value and parsed.variant == uuid.RFC_4122
             and parsed.version == 4, "LAB_FENCE_ID_INVALID")
    return value

def _scope(owner, namespace):
    need(type(owner) is str and _OWNER_PATTERN.fullmatch(owner) is not None,
         "LAB_FENCE_OWNER_INVALID")
    need(type(namespace) is str and len(namespace) <= 200
         and _NAMESPACE_PATTERN.fullmatch(namespace) is not None,
         "LAB_FENCE_NAMESPACE_INVALID")
    return owner, namespace

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
      owner text NOT NULL,
      namespace text NOT NULL,
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
       p_owner text,p_namespace text,p_generation bigint,p_token bigint,p_session uuid,p_instance uuid,
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
         OR live.owner IS DISTINCT FROM p_owner
         OR live.namespace IS DISTINCT FROM p_namespace
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
       text,text,bigint,bigint,uuid,uuid,uuid,text,text,text,text,text,bigint,jsonb)
       FROM PUBLIC;
    GRANT EXECUTE ON FUNCTION public.lab_fenced_insert(
       text,text,bigint,bigint,uuid,uuid,uuid,text,text,text,text,text,bigint,jsonb)
       TO lab_writer;
    COMMIT;
    """)
    need(pg.sql("SELECT has_table_privilege('lab_writer',"
                "'public.provenance_minutes','INSERT')") == "f",
         "LAB_FENCE_DIRECT_INSERT_BYPASS")
    return pg

def claim_lab_fence(pg, *, owner, namespace, generation, token,
                    session_id, instance_id,
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
    owner, namespace = _scope(owner, namespace)
    ids = (_id(session_id, consul_session=True), _id(instance_id),
           _id(node_incarnation_id))
    sha1, sha2 = _sha(source_sha256), _sha(schema_sha256)
    # A claimed PID must be an existing lab_writer DB connection. A current
    # backend_start is stored by PostgreSQL, not asserted in any client JSON.
    sql = (
        "INSERT INTO public.lab_writer_fence("
        "resource_id,owner,namespace,generation,token,session_id,instance_id,"
        "node_incarnation_id,source_sha256,schema_sha256,"
        "backend_pid,backend_start,active)"
        " SELECT 'grid-market-data-primary',"
        f"'{owner}','{namespace}',{generation},{token},'{ids[0]}'::uuid,'{ids[1]}'::uuid,"
        f"'{ids[2]}'::uuid,'{sha1}','{sha2}',pid,backend_start,true"
        " FROM pg_catalog.pg_stat_activity"
        f" WHERE pid={backend_pid} AND usename='lab_writer'"
        " ON CONFLICT(resource_id) DO UPDATE SET"
        " owner=EXCLUDED.owner,namespace=EXCLUDED.namespace,"
        " generation=EXCLUDED.generation,token=EXCLUDED.token,"
        " session_id=EXCLUDED.session_id,instance_id=EXCLUDED.instance_id,"
        " node_incarnation_id=EXCLUDED.node_incarnation_id,"
        " source_sha256=EXCLUDED.source_sha256,"
        " schema_sha256=EXCLUDED.schema_sha256,"
        " backend_pid=EXCLUDED.backend_pid,"
        " backend_start=EXCLUDED.backend_start,active=true"
        " WHERE public.lab_writer_fence.active=false"
        " AND EXCLUDED.owner=public.lab_writer_fence.owner"
        " AND EXCLUDED.namespace=public.lab_writer_fence.namespace"
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

def revoke_lab_fence(pg, *, owner, namespace, generation, token,
                     backend_pid, backend_start, timeout=120):
    """Revoke ONE exact original LAB backend fence with durable SQL readback.

    Caller-supplied generation/token alone MUST fail closed (TypeError).
    PostgreSQL row revocation is not process/backend extinction, Consul lease
    expiry, Root admission, or an assertion that no old COMMIT ever occurred.
    Unknown UPDATE outcome is resolved only by an independent exact readback.
    """
    pg._verify_owned()
    need(pg.started, "LAB_PG_NOT_STARTED")
    pg._verify_postmaster()
    owner, namespace = _scope(owner, namespace)
    need(type(generation) is int and 0 < generation < 2**63
         and type(token) is int and 0 < token < 2**63,
         "LAB_FENCE_TOKEN_INVALID")
    need(type(backend_pid) is int and 0 < backend_pid < 2**31,
         "LAB_FENCE_BACKEND_INVALID")
    need(type(backend_start) is str and len(backend_start) <= 64,
         "LAB_FENCE_BACKEND_START_INVALID")
    need(type(timeout) in (int, float) and 1 <= timeout <= 120,
         "LAB_FENCE_REVOKE_TIMEOUT_INVALID")
    try:
        old_start = datetime.datetime.fromisoformat(
            backend_start.replace("Z", "+00:00").replace(" ", "T"))
    except (ValueError, OverflowError) as exc:
        raise LabAdmissionRejected("LAB_FENCE_BACKEND_START_INVALID") from exc
    need(old_start.tzinfo is not None, "LAB_FENCE_BACKEND_START_INVALID")
    where = (
        " WHERE resource_id='grid-market-data-primary'"
        f" AND owner='{owner}' AND namespace='{namespace}'"
        f" AND generation={generation} AND token={token}"
        f" AND backend_pid={backend_pid}"
        f" AND backend_start='{old_start.isoformat()}'::timestamptz"
    )
    try:
        pg.sql("UPDATE public.lab_writer_fence SET active=false"
               + where + " AND active=true RETURNING generation",
               timeout=timeout)
    except Exception:
        # Could be a lock timeout, network failure, or unknown COMMIT.
        # Nothing is acknowledged until a new owner-only SQL connection
        # independently proves the exact durable identity is inactive.
        pass
    result = pg.sql(
        "SELECT CASE WHEN active=false THEN 'REVOKED_EXACT'"
        " ELSE 'UNKNOWN' END FROM public.lab_writer_fence" + where,
        timeout=timeout)
    need(result == "REVOKED_EXACT", "LAB_FENCE_REVOKE_UNVERIFIED")
    return True


def fence_identity():
    """Immutable fixture identity; caller still needs independent Root authority."""
    return {"resource_id": _RESOURCE, "schema": "lab-postgres-writer-fence.v1",
            "owner_namespace_required": True,
            "scope": "ISOLATED_LAB_ONLY", "execution_authority": False,
            "trading_authorized": False, "native_admission": False}

def fenced_lab_witness(pg, *, timeout=120):
    """Independent owner catalogue check for opt-in fenced LAB, not production."""
    import json
    pg._verify_owned()
    need(pg.started, "LAB_PG_NOT_STARTED")
    pg._verify_postmaster()
    result = pg.sql("""
       SELECT json_build_object(
           'schema','lab-postgres-fenced-custody.v1',
           'scope','ISOLATED_LAB_ONLY',
           'direct_writer_insert',
              has_table_privilege('lab_writer','public.provenance_minutes','INSERT'),
           'writer_exec',
              has_function_privilege('lab_writer',
                'public.lab_fenced_insert(text,text,bigint,bigint,uuid,uuid,uuid,text,text,text,text,text,bigint,jsonb)',
                'EXECUTE'),
           'reader_exec',
              has_function_privilege('lab_reader',
                'public.lab_fenced_insert(text,text,bigint,bigint,uuid,uuid,uuid,text,text,text,text,text,bigint,jsonb)',
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
         'public.lab_fenced_insert(text,text,bigint,bigint,uuid,uuid,uuid,text,text,text,text,text,bigint,jsonb)'::regprocedure
    """, timeout=timeout)
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

def revalidate_lab_fence(pg, *, identity, generation, backend_pid):
    """Private Root-side read-only revalidation; NEVER an admission grant.

    Exact E WriterLeaseIdentity input is data, NOT independent Consul truth.
    A caller also needs a trusted Root process/lease binding before acting.
    The owner re-reads the current PG18 backend, matching its startup time,
    after every promotion/revoke/restart. No public endpoints or secrets.
    """
    pg._verify_owned()
    need(pg.started, "LAB_PG_NOT_STARTED")
    pg._verify_postmaster()
    need(type(generation) is int and 0 < generation < 2**63
         and type(backend_pid) is int and 0 < backend_pid < 2**31,
         "LAB_FENCE_REVALIDATION_ARGUMENTS")
    # Fail closed on unexpected shape; no duck-typed caller JSON as authority.
    from .grid_writer_fence_model import WriterLeaseIdentity
    need(type(identity) is WriterLeaseIdentity, "LAB_FENCE_IDENTITY_REQUIRED")
    owner, namespace = _scope(identity.owner, identity.namespace)
    sess = _id(identity.session_id, consul_session=True)
    inst = _id(identity.instance_id)
    node = _id(identity.node_incarnation_id)
    source = _sha(identity.source_sha256)
    schema = _sha(identity.schema_sha256)
    token = identity.token
    need(type(token) is int and 0 < token < 2**63,
         "LAB_FENCE_TOKEN_INVALID")
    # This query MUST re-read the original fenced row and active backend in
    # one DB snapshot. Return no user secret, DSN or bearer material.
    query = (
        "SELECT CASE WHEN"
        " f.resource_id='grid-market-data-primary'"
        " AND f.active IS TRUE"
        f" AND f.owner='{owner}' AND f.namespace='{namespace}'"
        f" AND f.generation={generation} AND f.token={token}"
        f" AND f.session_id='{sess}'::uuid"
        f" AND f.instance_id='{inst}'::uuid"
        f" AND f.node_incarnation_id='{node}'::uuid"
        f" AND f.source_sha256='{source}'"
        f" AND f.schema_sha256='{schema}'"
        f" AND f.backend_pid={backend_pid}"
        " AND s.pid=f.backend_pid"
        " AND s.backend_start=f.backend_start"
        " AND s.usename='lab_writer'"
        " AND s.datname=current_database()"
        " AND s.backend_type='client backend'"
        " THEN f.backend_start::text ELSE 'DENIED' END"
        " FROM public.lab_writer_fence f"
        " LEFT JOIN pg_catalog.pg_stat_activity s ON s.pid=f.backend_pid"
        " WHERE f.resource_id='grid-market-data-primary'"
    )
    result = pg.sql(query)
    need(result not in ("", "DENIED"), "LAB_FENCE_REVALIDATION_DENIED")
    # The backend_start comes from the EXACT matching C fence + live
    # pg_stat_activity in the SAME SQL snapshot. Still NOT Root authority.
    from datetime import datetime
    try:
        parsed = datetime.fromisoformat(result.replace(" ", "T"))
    except (TypeError, ValueError) as exc:
        raise LabAdmissionRejected("LAB_FENCE_BACKEND_START_INVALID") from exc
    need(parsed.tzinfo is not None, "LAB_FENCE_BACKEND_START_INVALID")
    receipt = {
        "schema": "lab-postgres-fence-revalidation.v1",
        "scope": "ISOLATED_LAB_ONLY",
        "resource_id": _RESOURCE,
        "generation": generation,
        "token": token,
        "backend_pid": backend_pid,
        "backend_start": parsed.isoformat(),
        "owner": owner,
        "namespace": namespace,
        "session_id": sess,
        "instance_id": inst,
        "node_incarnation_id": node,
        "source_sha256": source,
        "schema_sha256": schema,
        "db_backend_observed": True,
        "db_fence_current_at_read": True,
        "root_consul_admitted": False,
        "host_old_process_quiescence_attested": False,
        "native_writer_admitted": False,
        "execution_authority": False,
        "trading_authorized": False,
        "paper_admitted": False,
    }
    return receipt


def observe_old_lab_backend(pg, *, owner, namespace, generation, token,
                            backend_pid, backend_start, timeout=120):
    """Read-only old-backend observation; not a transferable Root grant.

    A missing/mismatched row, inaccessible PostgreSQL, or any ambiguous
    identity is UNKNOWN. The exact old backend start comes from the durable
    fence and must match the trusted caller's expected value.
    """
    import datetime
    pg._verify_owned()
    need(pg.started, "LAB_PG_NOT_STARTED")
    pg._verify_postmaster()
    owner, namespace = _scope(owner, namespace)
    need(type(generation) is int and 0 < generation < 2**63
         and type(token) is int and 0 < token < 2**63,
         "LAB_BACKEND_FENCE_ARGUMENTS")
    need(type(backend_pid) is int and 0 < backend_pid < 2**31,
         "LAB_BACKEND_PID_INVALID")
    need(type(backend_start) is str and len(backend_start) <= 64,
         "LAB_BACKEND_START_INVALID")
    try:
        started = datetime.datetime.fromisoformat(backend_start.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LabAdmissionRejected("LAB_BACKEND_START_INVALID") from exc
    need(started.tzinfo is not None, "LAB_BACKEND_START_INVALID")
    query = (
        "SELECT CASE WHEN "
        f"f.owner='{owner}' AND f.namespace='{namespace}'"
        f" AND f.generation={generation} AND f.token={token}"
        f" AND f.backend_pid={backend_pid}"
        f" AND f.backend_start='{started.isoformat()}'::timestamptz"
        " THEN CASE WHEN EXISTS ("
        " SELECT 1 FROM pg_catalog.pg_stat_activity a"
        " WHERE a.pid=f.backend_pid AND a.backend_start=f.backend_start"
        " AND a.datname=current_database() AND a.usename='lab_writer'"
        " AND a.backend_type='client backend') THEN 'STILL_ALIVE'"
        " WHEN EXISTS (SELECT 1 FROM pg_catalog.pg_stat_activity a"
        " WHERE a.pid=f.backend_pid) THEN 'UNKNOWN'"
        " ELSE 'EXTINCT' END"
        " ELSE 'UNKNOWN' END"
        " FROM public.lab_writer_fence f"
        " WHERE f.resource_id='grid-market-data-primary'"
    )
    try:
        state = pg.sql(query, timeout=timeout)
    except Exception:
        return "UNKNOWN"
    return state if state in ("EXTINCT", "STILL_ALIVE") else "UNKNOWN"


def terminate_old_lab_backend(pg, *, owner, namespace, generation, token,
                              backend_pid, backend_start):
    """Conservative LAB-only backend stop; NOT a transferable Root proof.

    This helper deliberately DOES NOT terminate a PID. PostgreSQL exposes
    pg_terminate_backend(pid), not an atomic pid+backend_start CAS, so an
    in-statement pg_stat_activity join still has a PID-reuse TOCTOU race.
    Until Root can hold an OS/backend-incarnation-stable actuator, only
    observe old state. In particular do not return EXTINCT on a racing probe.
    """
    state = observe_old_lab_backend(
        pg, owner=owner, namespace=namespace, generation=generation,
        token=token, backend_pid=backend_pid, backend_start=backend_start)
    return "UNKNOWN" if state == "STILL_ALIVE" else state
