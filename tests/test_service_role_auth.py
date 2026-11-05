"""Role metadata does not authorize startup or loosen private credential shape."""
import hashlib,tempfile,unittest
from pathlib import Path
from unified_system import lab_runtime as lab

class ServiceRoleAuthTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name).resolve();self.path=self.root/'auth.json'
 def read(self,node,base_role,record,**changes):
  raw=lab.lab_release.canonical(record);self.path.write_bytes(raw)
  context=dict(scope='OFFLINE_VALIDATION_ONLY',role=base_role,node_id=node,computer_name='LABHOST',credential_root=str(self.root))
  context.update(changes)
  return lab.read_grid_auth(self.path,hashlib.sha256(raw).hexdigest(),node_id=node,release_id='lab-r1',source_commit='a'*40,role_context=context)
 def record(self,node,role):
  return dict(schema='unified.lab.grid-auth.v3',node_id=node,role=role,release_id='lab-r1',source_commit='a'*40,
   grid_shared_token='c'*64 if role=='CONTROL' else None,node_credential=None if role=='CONTROL' else 'w'*64,postgres_password='d'*64 if role=='CONTROL' else None)
 def test_single_pc_and_control_metadata_read_only_exact_control_secrets(self):
  for role in ('CONTROL','SINGLE_PC'):
   with self.subTest(role=role):
    self.assertEqual(self.read('LAB1',role,self.record('LAB1','CONTROL')),{'GRID_SHARED_TOKEN':'c'*64,'PGPASSWORD':'d'*64})
 def test_worker_metadata_never_admits_fleet_or_database_secrets(self):
  record=self.record('LABW','WORKER')
  self.assertEqual(self.read('LABW','WORKER',record),{'NODE_CREDENTIAL':'w'*64})
  for key,value in (('grid_shared_token','c'*64),('postgres_password','d'*64),('role','CONTROL'),('schema','unified.lab.grid-auth.v2')):
   with self.subTest(key=key),self.assertRaises(ValueError):self.read('LABW','WORKER',{**record,key:value})
 def test_mismatched_context_or_credential_root_is_rejected(self):
  for change in ({'node_id':'OTHER'},{'role':'PRODUCTION'},{'scope':'APPROVED'},{'credential_root':str(self.root/'other')}):
   with self.subTest(change=change),self.assertRaises(ValueError):self.read('LAB1','CONTROL',self.record('LAB1','CONTROL'),**change)
 def test_no_context_still_rejects_nonoffice_node(self):
  raw=lab.lab_release.canonical(self.record('LAB1','CONTROL'));self.path.write_bytes(raw)
  with self.assertRaises(ValueError):lab.read_grid_auth(self.path,hashlib.sha256(raw).hexdigest(),node_id='LAB1',release_id='lab-r1',source_commit='a'*40)

 def test_source_scope_is_exact_per_member_and_never_implicit(self):
  from unittest.mock import patch
  from tests.test_lab_release import fixture
  manifest=fixture(self.root);root=self.root;calls=[]
  class Fence:
   def __init__(self,path,head,**kwargs):
    self.source=next(s for s in manifest['sources'].values() if root/s['root']==path);calls.append((path,kwargs))
   def check(self):return {'tree':self.source['tree'],'runtime_files':{'inert.txt':{'comparison':'RAW_IDENTICAL'}}}
   def git(self,*args):return ('https://github.com/'+self.source['repository']).encode()
  with patch('integration.source_guard.SourceFence',Fence):
   self.assertEqual(set(lab.verify_sources(root,manifest,owner_admitted_root=root)),set(manifest['sources']))
   self.assertTrue(all(kw['owner_admitted_root']==path for path,kw in calls))
   calls.clear();lab.verify_sources(root,manifest)
   self.assertTrue(all('owner_admitted_root' not in kw for _,kw in calls))
  with patch('integration.source_guard.SourceFence') as child:
   for invalid in (root.parent,Path('.'),root/'*'):
    with self.subTest(root=str(invalid)),self.assertRaises(ValueError):lab.verify_sources(root,manifest,owner_admitted_root=invalid)
   child.assert_not_called()
