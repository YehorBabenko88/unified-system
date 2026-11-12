"""Closed disposable PG protocol renderer. No IO/native initialization at import.

All bytes containing credentials are PRIVATE. Only hashes/counts are reportable.
This module neither grants a native lease nor implements database adapters.
"""
from dataclasses import dataclass,field
import hashlib
from .pg_qualification import command_for,SQL_NAMES

MIGRATION_SHA='9f9c25f36a86c68e05e3f486cf61eed622fdeeb65ef0da27c8d489ad00ebb65e'
READBACK_SHA='48e2af3f0667c3ac25c115d1ace8a197cd2a2b9707d9ff6e540629dc0aee350c'

def require(value):
    if value is not True:raise ValueError('PG_PROTOCOL_DENIED')

def hexvalue(value,n):
    require(type(value) is str and len(value)==n and all(c in '0123456789abcdef' for c in value));return value

def digest(raw):return hashlib.sha256(raw).hexdigest()

def encoded(text):return text.encode('ascii')

def marker(role):return encoded("\nSELECT 'PG_PROTOCOL_V1_"+role.upper()+"';\n")

@dataclass(frozen=True)
class Protocol:
    scripts:tuple=field(repr=False)
    secrets:tuple=field(repr=False)
    context_id:str
    binding_sha256:str
    def script(self,name):
        require(name in SQL_NAMES);return dict(self.scripts)[name]
    def sql_pins(self):return tuple((n,digest(raw),len(raw)) for n,raw in self.scripts)
    def private_files(self):return tuple(('sql/'+n+'.sql',raw,n=='bootstrap') for n,raw in self.scripts)+self.secrets
    def public_manifest(self):return {'scope':'DISPOSABLE_SQL_PROTOCOL_NOT_AUTHORITY','sql_pins':tuple((n,'PRIVATE_REDACTED' if n=='bootstrap' else sha,size) for n,sha,size in self.sql_pins()),'context_id':self.context_id,'binding_sha256':self.binding_sha256,'production_qualified':False}

def render_protocol(*,migration,readback,context_id,binding_sha256,admin_password,app_password):
    # Bound buffers and exact upstream bytes before ANY decode/SQL decomposition.
    for raw,pin in ((migration,MIGRATION_SHA),(readback,READBACK_SHA)):
        require(type(raw) is bytes and 0<len(raw)<=65536 and digest(raw)==pin)
    cid=hexvalue(context_id,32);binding=hexvalue(binding_sha256,64)
    admin=hexvalue(admin_password,64);app=hexvalue(app_password,64);require(admin!=app)
    mismatch=('0' if binding!='0'*64 else '1')*64
    bootstrap=encoded("""\\set ON_ERROR_STOP on
SET password_encryption='scram-sha-256';
CREATE ROLE unified_lab_collector_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD '"""+app+"""';
CREATE DATABASE unified_lab_collector_c0c2 OWNER unified_lab_collector_app TEMPLATE template0 ENCODING 'UTF8';
REVOKE ALL ON DATABASE unified_lab_collector_c0c2 FROM PUBLIC;
REVOKE CONNECT ON DATABASE postgres FROM PUBLIC;
REVOKE CONNECT ON DATABASE template1 FROM PUBLIC;
GRANT CONNECT,TEMPORARY ON DATABASE unified_lab_collector_c0c2 TO unified_lab_collector_app;
ALTER ROLE unified_lab_collector_app SET statement_timeout='5s';
ALTER ROLE unified_lab_collector_app SET lock_timeout='1s';
ALTER ROLE unified_lab_collector_app SET idle_in_transaction_session_timeout='2s';
ALTER ROLE unified_bootstrap_collector_c0c2 NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
""")+marker('bootstrap')
    # Bootstrap is necessarily the initial initdb superuser, then demoted after
    # provisioning. No permanent service role or existing account is adopted.
    migration_script=migration+marker('migrate')
    payload=digest(b'hello');obs=digest(b'qualification-observation');journal=digest(b'qualification-journal')
    fixture=f"""BEGIN;
INSERT INTO collector_metadata_v1.instrument VALUES ('SYNTHETIC:PG:V1','SYNTHETIC',NULL);
INSERT INTO collector_metadata_v1.context VALUES ('{cid}','SYNTHETIC:PG:V1','{binding}','00000000-0000-4000-8000-000000000001','LOCAL_UNATTESTED','ACTIVE');
INSERT INTO collector_metadata_v1.observation_ref VALUES ('{cid}','{obs}','{journal}','{payload}',5,'SYNTHETIC','UNKNOWN');
INSERT INTO collector_metadata_v1.local_checkpoint VALUES ('{cid}','{obs}','{journal}',1,'UNKNOWN',false);
INSERT INTO collector_metadata_v1.retention_hold VALUES ('{cid}','qualification-retain','SYNTHETIC_ONLY');
COMMIT;
"""
    checks=f"""DO $assert$
BEGIN
 IF current_user <> 'unified_lab_collector_app' OR current_database() <> 'unified_lab_collector_c0c2' THEN RAISE EXCEPTION 'ROLE_OR_DATABASE'; END IF;
 IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname IN ('unified_lab_collector_app','unified_bootstrap_collector_c0c2') AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls)) THEN RAISE EXCEPTION 'ROLE_PRIVILEGES'; END IF;
 IF NOT EXISTS (SELECT 1 FROM pg_namespace n JOIN pg_roles r ON n.nspowner=r.oid WHERE n.nspname='collector_metadata_v1' AND r.rolname=current_user) THEN RAISE EXCEPTION 'SCHEMA_OWNER'; END IF;
 IF has_database_privilege(current_user,'postgres','CONNECT') OR has_database_privilege(current_user,'template1','CONNECT') THEN RAISE EXCEPTION 'DATABASE_ISOLATION'; END IF;
 IF (SELECT count(*) FROM collector_metadata_v1.instrument) <> 1 OR NOT EXISTS (SELECT 1 FROM collector_metadata_v1.instrument WHERE instrument_id='SYNTHETIC:PG:V1' AND identity_kind='SYNTHETIC' AND identity_contract_sha256 IS NULL) THEN RAISE EXCEPTION 'INSTRUMENT'; END IF;
 IF (SELECT count(*) FROM collector_metadata_v1.context) <> 1 OR NOT EXISTS (SELECT 1 FROM collector_metadata_v1.context WHERE context_id='{cid}' AND binding_sha256='{binding}' AND instrument_id='SYNTHETIC:PG:V1' AND store_id='00000000-0000-4000-8000-000000000001'::uuid AND custody='LOCAL_UNATTESTED' AND lifecycle_state='ACTIVE') THEN RAISE EXCEPTION 'CONTEXT'; END IF;
 IF (SELECT count(*) FROM collector_metadata_v1.observation_ref) <> 1 OR NOT EXISTS (SELECT 1 FROM collector_metadata_v1.observation_ref WHERE context_id='{cid}' AND observation_sha256='{obs}' AND raw_journal_digest='{journal}' AND payload_sha256='{payload}' AND payload_byte_count=5 AND observation_kind='SYNTHETIC' AND continuity='UNKNOWN') THEN RAISE EXCEPTION 'OBSERVATION'; END IF;
 IF (SELECT count(*) FROM collector_metadata_v1.local_checkpoint) <> 1 OR NOT EXISTS (SELECT 1 FROM collector_metadata_v1.local_checkpoint WHERE context_id='{cid}' AND observation_sha256='{obs}' AND raw_journal_digest='{journal}' AND local_lifecycle_sequence=1 AND native_outcome='UNKNOWN' AND publication_confirmed=false) THEN RAISE EXCEPTION 'CHECKPOINT'; END IF;
 IF (SELECT count(*) FROM collector_metadata_v1.retention_hold) <> 1 OR NOT EXISTS (SELECT 1 FROM collector_metadata_v1.retention_hold WHERE context_id='{cid}' AND hold_id='qualification-retain' AND reason='SYNTHETIC_ONLY') THEN RAISE EXCEPTION 'RETENTION'; END IF;
 IF EXISTS (SELECT 1 FROM collector_metadata_v1.context WHERE context_id='{cid}' AND binding_sha256='{mismatch}') THEN RAISE EXCEPTION 'WRONG_BINDING'; END IF;
END $assert$;
"""
    negative=f"""DO $negative$
BEGIN
 BEGIN
  CREATE SCHEMA collector_metadata_v1;
  RAISE EXCEPTION 'NAMESPACE_REUSE_ACCEPTED';
 EXCEPTION WHEN duplicate_schema THEN NULL;
 END;
 BEGIN
  INSERT INTO collector_metadata_v1.instrument VALUES ('BAD:IDENTITY','PROVIDER',NULL);
  RAISE EXCEPTION 'BAD_IDENTITY_ACCEPTED';
 EXCEPTION WHEN check_violation THEN NULL;
 END;
 BEGIN
  INSERT INTO collector_metadata_v1.instrument VALUES ('BAD:HASH','UNKNOWN','not-a-sha');
  RAISE EXCEPTION 'BAD_HASH_ACCEPTED';
 EXCEPTION WHEN check_violation THEN NULL;
 END;
 BEGIN
  UPDATE collector_metadata_v1.context SET lifecycle_state='COMMITTED' WHERE context_id='{cid}';
  RAISE EXCEPTION 'BAD_STATE_ACCEPTED';
 EXCEPTION WHEN check_violation THEN NULL;
 END;
 BEGIN
  UPDATE collector_metadata_v1.local_checkpoint SET raw_journal_digest=repeat('0',64) WHERE context_id='{cid}';
  RAISE EXCEPTION 'BAD_FOREIGN_KEY_ACCEPTED';
 EXCEPTION WHEN foreign_key_violation THEN NULL;
 END;
 BEGIN
  UPDATE collector_metadata_v1.local_checkpoint SET publication_confirmed=true WHERE context_id='{cid}';
  RAISE EXCEPTION 'AUTHORITY_ACCEPTED';
 EXCEPTION WHEN check_violation THEN NULL;
 END;
END $negative$;
BEGIN;
INSERT INTO collector_metadata_v1.retention_hold VALUES ('{cid}','must-rollback','SYNTHETIC_ONLY');
ROLLBACK;
"""
    verify=encoded(fixture+negative+checks)+marker('verify')
    # Decomposition is ONLY for these exact SHA-bound upstream bytes, not an SQL
    # parser or arbitrary substitution. PostgreSQL binds $1/$2 with PREPARE.
    header,sep,body=readback.partition(b'\n')
    require(sep==b'\n' and header.rstrip(b'\r')==b'-- SOURCE ONLY. Bind $1=context_id and $2=binding_sha256; read-only projection.')
    chunks=[x.strip() for x in body.split(b';') if x.strip()]
    require(len(chunks)==5 and chunks[0].endswith(b'BEGIN READ ONLY') and chunks[-1]==b'COMMIT' and all(x.startswith(b'SELECT ') for x in chunks[1:4]))
    query=b'BEGIN READ ONLY;\n'+encoded(checks)
    for i,select in enumerate(chunks[1:4]):
        query+=encoded(f'PREPARE collector_read_{i}(text,text) AS ')+select+b';\n'
        query+=encoded(f"EXECUTE collector_read_{i}('{cid}','{binding}');\nEXECUTE collector_read_{i}('{cid}','{mismatch}');\n")
    query+=b'COMMIT;\n'+marker('readback')
    scripts=(('bootstrap',bootstrap),('migrate',migration_script),('verify',verify),('readback',query))
    require(tuple(n for n,_ in scripts)==SQL_NAMES and all(len(raw)<=65536 for _,raw in scripts))
    pgpass=encoded('127.0.0.1:55483:postgres:unified_bootstrap_collector_c0c2:'+admin+'\n127.0.0.1:55483:unified_lab_collector_c0c2:unified_lab_collector_app:'+app+'\n')
    return Protocol(scripts,(('secrets/bootstrap-password',encoded(admin+'\n'),True),('secrets/pgpass.conf',pgpass,True)),cid,binding)

def run_protocol(custodian,protocol,writer):
    """No implicit native binding: injected ACTUAL custodian and own-root writer.

    writer(relative_path, raw, secret) must exclusively stage ordinary single-link
    files under the already admitted fresh private root; never public evidence.
    Its concrete binding is an external native lease prerequisite.
    """
    require(type(protocol) is Protocol and tuple(custodian.plan.sql_pins)==protocol.sql_pins())
    try:
        for path,raw,secret in protocol.private_files():writer(path,raw,secret)
        custodian.run(command_for(custodian.plan,'initdb'))
        custodian.start_server();custodian.wait_server_ready()
        for role in SQL_NAMES:custodian.run(command_for(custodian.plan,'psql',role))
        custodian.run(command_for(custodian.plan,'stop'))
        custodian.start_server();custodian.wait_server_ready()
        custodian.run(command_for(custodian.plan,'psql','readback'))
        custodian.run(command_for(custodian.plan,'stop'))
    finally:receipt=custodian.close()
    require(receipt.get('transport_ok') is True and receipt.get('protocol_complete') is True)
    out,err=custodian.private_output();require(type(out) is bytes and type(err) is bytes)
    lines=[x.strip() for x in out.splitlines()]
    require(all(lines.count(b'PG_PROTOCOL_V1_'+n.upper().encode())==(2 if n=='readback' else 1) for n in SQL_NAMES))
    return {'scope':'OWN_DISPOSABLE_SQL_ASSERTIONS_ONLY','sql_assertions_observed':True,'restart_readback_observed':True,'production_qualified':False,'backup_restore_qualified':False,'adapter_qualified':False,'custody':receipt,'sql_pins':protocol.public_manifest()['sql_pins']}
