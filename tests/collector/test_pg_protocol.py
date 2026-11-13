"""Pure SQL protocol controls: actual renderer, no PostgreSQL/process/SQL fixture."""
import unittest
from tools.collector import pg_protocol as p
MIGRATION=b"-- SOURCE ONLY. Execute only in a newly authorized isolated PostgreSQL database.\n-- Fail on namespace reuse. This projection grants no publication authority.\nBEGIN;\nCREATE SCHEMA collector_metadata_v1;\nCREATE TABLE collector_metadata_v1.instrument (\n    instrument_id text PRIMARY KEY CHECK (length(instrument_id) BETWEEN 1 AND 256),\n    identity_kind text NOT NULL CHECK (identity_kind IN ('SYNTHETIC', 'UNKNOWN')),\n    identity_contract_sha256 text CHECK (identity_contract_sha256 ~ '^[0-9a-f]{64}$')\n);\nCREATE TABLE collector_metadata_v1.context (\n    context_id text PRIMARY KEY CHECK (context_id ~ '^[0-9a-f]{32}$'),\n    instrument_id text NOT NULL REFERENCES collector_metadata_v1.instrument(instrument_id),\n    binding_sha256 text NOT NULL CHECK (binding_sha256 ~ '^[0-9a-f]{64}$'),\n    store_id uuid NOT NULL,\n    custody text NOT NULL CHECK (custody = 'LOCAL_UNATTESTED'),\n    lifecycle_state text NOT NULL CHECK (lifecycle_state IN ('ACTIVE','STOPPED','UNKNOWN','TERMINAL')),\n    UNIQUE (context_id, binding_sha256)\n);\nCREATE TABLE collector_metadata_v1.observation_ref (\n    context_id text NOT NULL REFERENCES collector_metadata_v1.context(context_id),\n    observation_sha256 text NOT NULL CHECK (observation_sha256 ~ '^[0-9a-f]{64}$'),\n    raw_journal_digest text NOT NULL CHECK (raw_journal_digest ~ '^[0-9a-f]{64}$'),\n    payload_sha256 text CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),\n    payload_byte_count integer NOT NULL CHECK (payload_byte_count BETWEEN 0 AND 1048576),\n    observation_kind text NOT NULL CHECK (observation_kind IN ('OPAQUE','SYNTHETIC','GAP')),\n    continuity text NOT NULL CHECK (continuity = 'UNKNOWN'),\n    PRIMARY KEY (context_id, observation_sha256),\n    UNIQUE (context_id, observation_sha256, raw_journal_digest),\n    CHECK (payload_sha256 IS NOT NULL OR payload_byte_count = 0)\n);\nCREATE TABLE collector_metadata_v1.local_checkpoint (\n    context_id text PRIMARY KEY,\n    observation_sha256 text NOT NULL,\n    raw_journal_digest text NOT NULL,\n    local_lifecycle_sequence integer NOT NULL CHECK (local_lifecycle_sequence BETWEEN 1 AND 128),\n    native_outcome text NOT NULL CHECK (native_outcome = 'UNKNOWN'),\n    publication_confirmed boolean NOT NULL CHECK (publication_confirmed = false),\n    FOREIGN KEY (context_id, observation_sha256, raw_journal_digest)\n        REFERENCES collector_metadata_v1.observation_ref\n            (context_id, observation_sha256, raw_journal_digest)\n);\nCREATE TABLE collector_metadata_v1.retention_hold (\n    context_id text NOT NULL REFERENCES collector_metadata_v1.context(context_id),\n    hold_id text NOT NULL CHECK (length(hold_id) BETWEEN 1 AND 256),\n    reason text NOT NULL CHECK (length(reason) BETWEEN 1 AND 1024),\n    PRIMARY KEY (context_id, hold_id)\n);\nCOMMIT;\n"
READBACK=b'-- SOURCE ONLY. Bind $1=context_id and $2=binding_sha256; read-only projection.\nBEGIN READ ONLY;\nSELECT c.context_id, c.instrument_id, c.binding_sha256, c.store_id,\n       c.custody, c.lifecycle_state, i.identity_kind, i.identity_contract_sha256,\n       p.observation_sha256, p.raw_journal_digest, p.local_lifecycle_sequence,\n       p.native_outcome, p.publication_confirmed\nFROM collector_metadata_v1.context AS c\nJOIN collector_metadata_v1.instrument AS i USING (instrument_id)\nLEFT JOIN collector_metadata_v1.local_checkpoint AS p USING (context_id)\nWHERE c.context_id = $1 AND c.binding_sha256 = $2;\nSELECT observation_sha256, raw_journal_digest, payload_sha256,\n       payload_byte_count, observation_kind, continuity\nFROM collector_metadata_v1.observation_ref\nWHERE context_id = $1 AND EXISTS (\n    SELECT 1 FROM collector_metadata_v1.context\n    WHERE context_id = $1 AND binding_sha256 = $2)\nORDER BY observation_sha256\nLIMIT 17;\nSELECT hold_id, reason FROM collector_metadata_v1.retention_hold\nWHERE context_id = $1 AND EXISTS (\n    SELECT 1 FROM collector_metadata_v1.context\n    WHERE context_id = $1 AND binding_sha256 = $2)\nORDER BY hold_id LIMIT 129;\nCOMMIT;\n'
class ProtocolTests(unittest.TestCase):
    def test_bootstrap_immutable_superuser_locked_and_verified_in_same_session(self):
        raw=self.render().script('bootstrap')
        self.assertNotIn(b'ALTER ROLE unified_bootstrap_collector_c0c2 NOSUPERUSER',raw)
        lock=b'ALTER ROLE unified_bootstrap_collector_c0c2 NOLOGIN PASSWORD NULL;'
        self.assertIn(lock,raw);self.assertIn(b'FROM pg_authid',raw)
        self.assertIn(b'rolsuper AND NOT rolcanlogin AND rolpassword IS NULL',raw)
        self.assertIn(b'count(*)',raw);self.assertLess(raw.index(lock),raw.index(b'FROM pg_authid'))
        self.assertLess(raw.index(b'FROM pg_authid'),raw.index(b'PG_PROTOCOL_V1_BOOTSTRAP'))
    def test_app_checks_exact_session_and_no_bootstrap_membership_or_set_role(self):
        raw=self.render().script('verify')
        self.assertIn(b"session_user <> 'unified_lab_collector_app'",raw)
        self.assertIn(b'NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole',raw)
        self.assertIn(b'NOT rolreplication AND NOT rolbypassrls',raw)
        self.assertIn(b"pg_has_role(current_user,'unified_bootstrap_collector_c0c2','MEMBER')",raw)
        self.assertIn(b"pg_has_role(current_user,'unified_bootstrap_collector_c0c2','SET')",raw)
        self.assertIn(b'BOOTSTRAP_MEMBERSHIP',raw);self.assertIn(b'BOOTSTRAP_LOCK',raw)
    def test_bootstrap_unretired_session_prevents_any_app_command(self):
        v=self.render();fake=Custodian(v);fake.bootstrap_session_retired=lambda:False
        with self.assertRaises(ValueError):p.run_protocol(fake,v,Writer())
        self.assertEqual(fake.events,['initdb','start','ready','bootstrap','close'])
    def render(self,**kw):
        args=dict(migration=MIGRATION,readback=READBACK,context_id='a'*32,binding_sha256='b'*64,admin_password='c'*64,app_password='d'*64);args.update(kw);return p.render_protocol(**args)
    def test_exact_four_roles_and_pins(self):
        v=self.render();self.assertEqual(tuple(n for n,_ in v.scripts),('bootstrap','migrate','verify','readback'));self.assertEqual(len(v.sql_pins()),4)
    def test_pinned_migration_retained_byte_exact(self):self.assertIn(MIGRATION,self.render().script('migrate'))
    def test_real_prepare_execute_parameters_not_text_substitution(self):
        s=self.render().script('readback');self.assertEqual(s.count(b'PREPARE '),3);self.assertEqual(s.count(b'\nEXECUTE collector_read_'),6);self.assertIn(b'$1',s);self.assertIn(b'$2',s)
    def test_each_actual_readback_select_has_exact_correct_and_mismatch_row_assertions(self):
        raw=self.render().script('readback');self.assertEqual(raw.count(b'FOR counted_row IN EXECUTE '),6)
        for i in range(3):
            self.assertIn(('READBACK_CORRECT_'+str(i)+'_ROWS').encode(),raw);self.assertIn(('READBACK_MISMATCH_'+str(i)+'_ROWS').encode(),raw)
        for select in [x.strip() for x in READBACK.partition(b'\n')[2].split(b';') if x.strip()][1:4]:self.assertEqual(raw.count(select),3)
        self.assertEqual(raw.count(b'IF row_count <> 1 THEN'),3);self.assertEqual(raw.count(b'IF row_count <> 0 THEN'),3)
        self.assertLess(raw.rfind(b'END $read_count_'),raw.index(b'PG_PROTOCOL_V1_READBACK'))
    def test_source_pin_changes_rejected(self):
        for name in ('migration','readback'):
            with self.subTest(name=name),self.assertRaises(ValueError):self.render(**{name:(MIGRATION if name=='migration' else READBACK)+b' '})
    def test_injection_and_bool_rejected(self):
        for name,value in (('context_id',"a';--"),('binding_sha256',True),('admin_password',"x';SQL"),('app_password','d'*63)):
            with self.subTest(name=name),self.assertRaises(ValueError):self.render(**{name:value})
    def test_credentials_private_not_repr_or_public_manifest(self):
        v=self.render();self.assertNotIn('c'*64,repr(v));self.assertNotIn('d'*64,repr(v));self.assertNotIn('c'*64,str(v.public_manifest()));self.assertIn(b'd'*64,v.script('bootstrap'))
    def test_public_bootstrap_digest_redacted_internal_pin_retained(self):
        v=self.render();secret_hash=p.digest(v.script('bootstrap'));self.assertNotIn(secret_hash,str(v.public_manifest()));self.assertEqual(v.sql_pins()[0][1],secret_hash);self.assertNotIn(secret_hash,str(p.run_protocol(Custodian(v),v,Writer())))
    def test_credentials_must_differ(self):
        with self.assertRaises(ValueError):self.render(app_password='c'*64)
    def test_no_drop_service_or_port_fallback(self):
        v=self.render();self.assertNotIn(b'DROP ',b' '.join(s for _,s in v.scripts));self.assertNotIn(b'55432',b' '.join(s for _,s,_ in v.private_files()))
    def test_exact_fixed_orchestration(self):
        v=self.render();fake=Custodian(v);writer=Writer();r=p.run_protocol(fake,v,writer)
        self.assertEqual(fake.events,['initdb','start','ready','bootstrap','migrate','verify','readback','stop','start','ready','readback','stop','close']);self.assertTrue(r['sql_assertions_observed']);self.assertFalse(r['production_qualified']);self.assertEqual(len(writer.files),6)
    def test_failure_always_closes_no_retry(self):
        v=self.render();fake=Custodian(v,'verify')
        with self.assertRaises(RuntimeError):p.run_protocol(fake,v,Writer())
        self.assertEqual(fake.events[-1],'close');self.assertEqual(fake.events.count('start'),1)
    def test_missing_marker_denies(self):
        v=self.render();fake=Custodian(v,'marker')
        with self.assertRaises(ValueError):p.run_protocol(fake,v,Writer())
        self.assertEqual(fake.events[-1],'close')
    def test_wrong_custodian_sql_pins_denies_before_write(self):
        v=self.render();fake=Custodian(v);fake.plan.sql_pins=();writer=Writer()
        with self.assertRaises(ValueError):p.run_protocol(fake,v,writer)
        self.assertEqual(writer.files,[]);self.assertEqual(fake.events,[])
class Writer:
    def __init__(self):self.files=[]
    def __call__(self,path,raw,secret):self.files.append((path,raw,secret))
class Plan:
    def __init__(self,v):self.sql_pins=v.sql_pins();self.root=r'C:\INERT\UnifiedCollectorTest\pg-attempt1'
class Custodian:
    def __init__(self,v,fault=None):self.plan=Plan(v);self.events=[];self.fault=fault;self.output=b''
    def run(self,c):
        name=c.sql_name if c.role=='psql' else c.role;self.events.append(name)
        if name==self.fault:raise RuntimeError('INERT_PHASE_FAILURE')
        if c.role=='psql' and self.fault!='marker':self.output+=('PG_PROTOCOL_V1_'+name.upper()+'\n').encode()
    def start_server(self):self.events.append('start')
    def wait_server_ready(self):self.events.append('ready')
    def bootstrap_session_retired(self):return True
    def close(self):self.events.append('close');return dict(transport_ok=True,protocol_complete=True)
    def private_output(self):return self.output,b''
