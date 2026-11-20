"""Inert SQL capture only; no PostgreSQL/client/native effects or admission."""
import hashlib,tempfile,unittest
from pathlib import Path
from unified_system import service_postgres as pg
ASSET='sources/market_data/market_data/capture_schema.sql'
RAW=(Path(__file__).parent/'fixtures/capture-schema-b5ca636.sql').read_bytes()
class Boundary(pg.WindowsPostgresBoundary):
 def __init__(self,root):
  super().__init__();self.calls=[];self.sql=[];self.manifest={'files':{ASSET:{'sha256':hashlib.sha256(RAW).hexdigest(),'bytes':len(RAW)}}};self.root=root
 def _permit(self,plan,action):self.calls.append(action)
 def _sql(self,plan,server,sql,**kwargs):self.sql.append((sql,kwargs));return b''
class CaptureSchemaProvisioningTests(unittest.TestCase):
 def setup(self,folder):
  root=Path(folder);p=root/ASSET;p.parent.mkdir(parents=True);p.write_bytes(RAW)
  return Boundary(root),{'service_plan':{'code':str(root)},'user':'unified_lab_test'},p
 def test_declared_data_asset_creates_only_fresh_public_tables_in_transaction(self):
  with tempfile.TemporaryDirectory() as f:
   b,p,path=self.setup(f);b.provision_capture_schema(p,object())
   self.assertEqual(b.calls,['PROVISION_CAPTURE_SCHEMA_NATIVE']);self.assertEqual(len(b.sql),1)
   sql,kw=b.sql[0];self.assertTrue(sql.startswith('BEGIN;'));self.assertTrue(sql.rstrip().endswith('COMMIT;'))
   self.assertEqual(sql.count('CREATE TABLE public.'),3);self.assertNotIn('IF NOT EXISTS',sql)
   self.assertEqual(kw,{'user':p['user'],'provision':True});self.assertEqual(path.read_bytes(),RAW)
 def test_missing_asset_pin_refused_before_sql(self):
  with tempfile.TemporaryDirectory() as f:
   b,p,path=self.setup(f);b.manifest['files'].clear()
   with self.assertRaises(pg.PostgresBlocked):b.provision_capture_schema(p,object())
   self.assertEqual(b.sql,[])
 def test_changed_source_bytes_refused_before_sql(self):
  with tempfile.TemporaryDirectory() as f:
   b,p,path=self.setup(f);path.write_bytes(RAW+b'-- drift')
   with self.assertRaises(pg.PostgresBlocked):b.provision_capture_schema(p,object())
   self.assertEqual(b.sql,[])
 def test_wrong_declared_size_refused_before_sql(self):
  with tempfile.TemporaryDirectory() as f:
   b,p,path=self.setup(f);b.manifest['files'][ASSET]['bytes']+=1
   with self.assertRaises(pg.PostgresBlocked):b.provision_capture_schema(p,object())
   self.assertEqual(b.sql,[])
 def test_source_refusal_does_not_delete_or_rewrite_asset(self):
  with tempfile.TemporaryDirectory() as f:
   b,p,path=self.setup(f);foreign=RAW.replace(b'market_data_capture_v2',b'foreign_capture');path.write_bytes(foreign)
   b.manifest['files'][ASSET]={'sha256':hashlib.sha256(foreign).hexdigest(),'bytes':len(foreign)}
   with self.assertRaises(pg.PostgresBlocked):b.provision_capture_schema(p,object())
   self.assertEqual(b.sql,[]);self.assertEqual(path.read_bytes(),foreign)
 def test_missing_owner_permission_precedes_asset_and_sql(self):
  with tempfile.TemporaryDirectory() as f:
   b,p,path=self.setup(f)
   def refuse(*args):raise pg.PostgresBlocked('POSTGRES_OWNER_PHASE_REJECTED')
   b._permit=refuse;path.unlink()
   with self.assertRaises(pg.PostgresBlocked):b.provision_capture_schema(p,object())
   self.assertEqual(b.sql,[])
 def test_sql_failure_is_not_retried_or_source_rewritten(self):
  with tempfile.TemporaryDirectory() as f:
   b,p,path=self.setup(f);calls=[]
   def failed(*args,**kwargs):calls.append(args);raise pg.PostgresBlocked('POSTGRES_NOT_READY')
   b._sql=failed
   with self.assertRaises(pg.PostgresBlocked):b.provision_capture_schema(p,object())
   self.assertEqual(len(calls),1);self.assertEqual(path.read_bytes(),RAW)
