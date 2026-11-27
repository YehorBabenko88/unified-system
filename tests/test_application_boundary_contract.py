"""Pure AST DTO validation only; no installer/import/prepare/native execution."""
import ast,copy,json,pathlib,types,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class ApplicationBoundaryContractTests(unittest.TestCase):
 def setUp(self):
  self.raw=(ROOT/'unified_system/installation_transaction.py').read_bytes();self.tree=ast.parse(self.raw);body=[]
  for n in self.tree.body:
   if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('SCHEMA','PLAN_KEYS') for t in n.targets):body.append(n)
   if isinstance(n,ast.FunctionDef) and n.name in ('need','validate_plan'):body.append(n)
  def digest(value,length=64):
   if type(value) is not str or len(value)!=length or any(c not in '0123456789abcdef' for c in value):raise ValueError('DIGEST')
  ns={'canonical':lambda v:json.dumps(v,sort_keys=True,separators=(',',':')).encode('ascii'),'copy':copy,'identifier':lambda v:None,'root':pathlib.PurePosixPath,'lab_release':types.SimpleNamespace(digest=digest,MODULE_IDS=frozenset(('unified_system','market_data','math','terminan')))}
  exec(compile(ast.Module(body=body,type_ignores=[]),'<actual-closed-plan-validator>','exec'),ns);self.validate=ns['validate_plan']
 def plan(self):
  return dict(schema='unified.installation-transaction.v2',installation_id='install1',node_id='node1',operation_id='op1',role='CONTROL',manifest_sha256='1'*64,capsule_root='/capsule',install_root='/install',state_root='/state',release_id='release1',sources={k:dict(commit='2'*40,tree='3'*40) for k in ('unified_system','market_data','math','terminan')},source_proof='NOT_EVALUATED',activation='BLOCKED',application_boundary='EXISTING_EPHEMERAL_GUARD_UNCHANGED',service_boundary='BLOCKED_NSSM_CLOSURE_SCOPED_ACL_GIT_IDENTITY_PENDING',capacity_gate='NOT_EVALUATED',capsule_source_provenance='PINNED_METADATA_ONLY_VERIFY_SOURCES_BEFORE_EXECUTION')
 def test_v2_exact_application_boundary_detaches_the_literal_dto(self):
  p=self.plan();got=self.validate(p);self.assertEqual(got,p);self.assertIsNot(got,p);p['sources']['math']['commit']='f'*40;self.assertNotEqual(got,p)
 def test_v1_schema_and_old_key_have_no_compatibility_path(self):
  p=self.plan()
  for change in ('v1','oldkey','both'):
   q=copy.deepcopy(p)
   if change=='v1':q['schema']='unified.installation-transaction.v1'
   if change in ('oldkey','both'):
    q['grid_boundary']=q['application_boundary']
    if change=='oldkey':del q['application_boundary']
   with self.assertRaises(ValueError):self.validate(q)
 def test_missing_extra_or_foreign_boundary_value_refuses(self):
  p=self.plan()
  for change in ('missing','extra','value'):
   q=copy.deepcopy(p)
   if change=='missing':del q['application_boundary']
   elif change=='extra':q['root_boundary']='EXISTING_EPHEMERAL_GUARD_UNCHANGED'
   else:q['application_boundary']='AUTHORIZED'
   with self.assertRaises(ValueError):self.validate(q)
 def test_all_non_authorizing_flags_and_service_boundary_stay_closed(self):
  p=self.plan()
  for key in ('source_proof','activation','service_boundary','capacity_gate','capsule_source_provenance'):
   q=copy.deepcopy(p);q[key]='GRANTED'
   with self.assertRaises(ValueError):self.validate(q)
 def test_four_owner_sources_no_legacy_alias_or_extra_fields(self):
  for key in ('grid','meta_analyse','strattester'):
   q=self.plan();q['sources'][key]=q['sources'].pop('market_data')
   with self.assertRaises(ValueError):self.validate(q)
  q=self.plan();q['sources']['math']['authority']=True
  with self.assertRaises(ValueError):self.validate(q)
 def test_paths_remain_distinct_and_non_overlapping_in_the_pure_model(self):
  for key,value in (('state_root','/install'),('state_root','/install/state'),('install_root','/capsule/nested')):
   q=self.plan();q[key]=value
   with self.assertRaises(ValueError):self.validate(q)
 def test_factory_ast_uses_only_the_new_field_without_execution(self):
  f=next(n for n in self.tree.body if isinstance(n,ast.FunctionDef) and n.name=='source_plan');keys=[k.arg for n in ast.walk(f) if isinstance(n,ast.Call) for k in n.keywords]
  self.assertIn('application_boundary',keys);self.assertNotIn('grid_boundary',keys)
 def test_rollback_ast_keeps_all_bytes_and_grants_no_effects(self):
  cls=next(n for n in self.tree.body if isinstance(n,ast.ClassDef) and n.name=='InstallationTransaction');rollback=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='rollback');text=ast.unparse(rollback)
  self.assertIn('ROLLED_BACK_RETAINED',text);self.assertNotIn('unlink',text);self.assertNotIn('rmdir',text)
