import ast,copy,json,unittest
from pathlib import Path
from unified_system.staging import build_staging_plan,source_lock_digest
ROOT=Path(__file__).resolve().parents[1]
def lock():return json.loads((ROOT/'docs/windows-staging-sources.json').read_text())
def node(i,modules=None,intent='PRESENT'):return dict(id='logical-slot-'+str(i),modules=['unified','terminan'] if modules is None else modules,intent=intent)
def prior(n):return dict(id=n['id'],modules=n['modules'],source_lock_sha256=source_lock_digest(lock()))
class StagingTests(unittest.TestCase):
 def test_counts_immutability_no_authority_or_physical_facts(self):
  for count in (0,1,5,6,7,10,64):
   source=lock();nodes=[node(i) for i in range(count)];before=copy.deepcopy((source,nodes));p=build_staging_plan(source,nodes)
   self.assertEqual(len(p['nodes']),count);self.assertEqual(before,(source,nodes))
   for k,v in dict(mode='PLAN_ONLY',admission='BLOCKED',physical='NOT_RUN',production='NO_GO',execution_authorized=False,mutations_performed=False,trading_authorized=False).items():self.assertEqual(p[k],v)
   for row in p['nodes']:
    self.assertEqual(row['action'],'ADD');self.assertEqual(row['host_identity'],'UNVERIFIED');self.assertTrue(all(c['status']=='UNVERIFIED' and c['probe']=='NOT_RUN' for c in row['checks']))
 def test_incremental_add_drain_retire_no_fleet_reinstall(self):
  old=[prior(node(i)) for i in range(6)];p=build_staging_plan(lock(),[node(i) for i in range(5)]+[node(6)],old);rows={n['logical_id']:n for n in p['nodes']}
  self.assertTrue(all(rows[node(i)['id']]['action']=='KEEP' and rows[node(i)['id']]['operations']==[] for i in range(5)))
  self.assertEqual(rows[node(6)['id']]['action'],'ADD');self.assertEqual(rows[node(5)['id']]['action'],'RETIRE')
  for intent in ('DRAIN','RETIRE'):
   row=build_staging_plan(lock(),[node(0,intent=intent)],[old[0]])['nodes'][0]
   self.assertEqual(row['action'],intent);self.assertIn('REVIEW_LEASE_EXPIRY_FENCING_CHECKPOINT',row['operations'])
 def test_changes_are_only_update_proposals(self):
  old=prior(node(0));old['source_lock_sha256']='f'*64
  self.assertEqual(build_staging_plan(lock(),[node(0)],[old])['nodes'][0]['action'],'UPDATE')
  self.assertIn('REVIEW_LEASE_EXPIRY_FENCING_CHECKPOINT',build_staging_plan(lock(),[node(0)],[old])['nodes'][0]['operations'])
  self.assertEqual(build_staging_plan(lock(),[node(0,['math'])],[prior(node(0))])['nodes'][0]['action'],'UPDATE')
 def test_unknown_secret_command_and_authority_fields_rejected(self):
  for key in ('command','executor','ssh_private_key','password','operator_approved','identity_verified','execution_authorized','observations'):
   n=node(0);n[key]='untrusted'
   with self.subTest(key=key),self.assertRaises(ValueError):build_staging_plan(lock(),[n])
  for where in ('root','source','pin'):
   s=lock();target=s if where=='root' else s['sources'] if where=='source' else s['sources']['math'];target['command']='x'
   with self.subTest(where=where),self.assertRaises(ValueError):build_staging_plan(s,[])
 def test_source_roster_types_and_bounds(self):
  for s in (None,{},dict(lock(),schema='v2')):
   with self.assertRaises(ValueError):build_staging_plan(s,[])
  for key,bad in [('commit','latest'),('tree',True)]:
   s=lock();s['sources']['math'][key]=bad
   with self.assertRaises(ValueError):build_staging_plan(s,[])
  for nodes in ([node(i) for i in range(65)],[node(0),dict(node(0),id='LOGICAL-SLOT-0')],[dict(node(0),id='host;exec')],[node(0,['math','math'])],[node(0,['unknown'])],[node(0,intent=True)],[node(0,intent='RETIRE')]):
   with self.assertRaises(ValueError):build_staging_plan(lock(),nodes)
  with self.assertRaises(ValueError):build_staging_plan(lock(),[],[dict(prior(node(0)),source_lock_sha256='fake')])
 def test_disjoint_rosters_bounded_no_predecessor_trust(self):
  p=build_staging_plan(lock(),[node(i) for i in range(64)],[prior(node(i+64)) for i in range(64)])
  self.assertEqual(len(p['nodes']),128);self.assertEqual(p['admission'],'BLOCKED')
 def test_no_io_or_execution(self):
  for n in ast.walk(ast.parse((ROOT/'unified_system/staging.py').read_text())):
   if isinstance(n,ast.Import):self.assertTrue(all(x.name in {'hashlib','json','re'} for x in n.names))
   self.assertNotIsInstance(n,ast.ImportFrom)
   if isinstance(n,ast.Call) and isinstance(n.func,ast.Name):self.assertNotIn(n.func.id,('open','eval','exec','compile','__import__','input'))

 def test_module_removal_update_requires_drain_before_closure_and_approval(self):
  old=prior(node(0,['unified','grid']));row=build_staging_plan(lock(),[node(0,['unified'])],[old])['nodes'][0]
  self.assertEqual(row['action'],'UPDATE')
  for review in ('REVIEW_DRAIN','REVIEW_LEASE_EXPIRY_FENCING_CHECKPOINT','REVIEW_IDENTITY_REVOCATION_AND_RETENTION'):
   self.assertIn(review,row['operations']);self.assertLess(row['operations'].index(review),row['operations'].index('REVIEW_SOURCE_AND_PACKAGE_CLOSURE'))
  self.assertEqual(row['operations'][-1],'REQUEST_SEPARATE_PHYSICAL_APPROVAL')
