"""Pure generator freshness/data joins; no native broker or issued authority."""
import hashlib,importlib.util,json,pathlib,tempfile,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
GEN=ROOT/'docs/intelligence/research-identity/build_record_schemas.py'
SUPPORT=('integration/four_owner/cohort.json','docs/intelligence/canonical-native-profile/request.schema.json','release/integration/native-negative-v2/manifest.json','unified_system/gateway_research_identity.py')
def api():
 spec=importlib.util.spec_from_file_location('inert_record_generator',GEN);module=importlib.util.module_from_spec(spec)
 with patch.object(pathlib.Path,'write_bytes',side_effect=AssertionError('IMPORT_SOURCE_WRITE')),patch.object(pathlib.Path,'write_text',side_effect=AssertionError('IMPORT_SOURCE_WRITE')):
  spec.loader.exec_module(module)
 return module
def profile():
 path=ROOT/'tests/gateway_research_identity/canonical_profile_fixture.py';spec=importlib.util.spec_from_file_location('inert_profile_data',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 value={'principal_registry':{'a'*64:'11111111-1111-4111-8111-111111111111'}}
 module.bind_profile(value,request_id='33333333-3333-4333-8333-333333333333',job_id='44444444-4444-4444-8444-444444444444',generation='22222222-2222-4222-8222-222222222222',actor='11111111-1111-4111-8111-111111111111',quota_owner='local-quota')
 value.update(cluster_id='55555555-5555-4555-8555-555555555555',realm_id='66666666-6666-4666-8666-666666666666',resources={'cpu_millicores':'1000','resident_memory_bytes':'268435456','max_artifact_bytes':'1048576'},expiry_semantics='NATIVE_SESSION_INVALIDATION_NOT_UTC_AT_COMMIT',expires_utc='2026-11-20T12:05:00Z')
 return value
def copy_support(root):
 for rel in SUPPORT:
  p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/rel).read_bytes())
class ResearchRecordSchemaTests(unittest.TestCase):
 def test_import_is_pure_without_source_writes(self):self.assertTrue(callable(api().render_records))
 def test_checked_in_records_and_hash_manifest_match_current_inputs(self):
  expected=api().render_records(ROOT)
  for name,raw in expected.items():self.assertEqual(json.loads(raw),json.loads((GEN.parent/name).read_bytes()))
  manifest=json.loads(api().render_manifest(expected))
  self.assertEqual(manifest,json.loads((GEN.parent/'RECORD-MANIFEST.json').read_bytes()))
 def test_actual_canonical_profile_literal_joins(self):
  schema=json.loads((GEN.parent/'profile.schema.json').read_bytes());value=profile();props=schema['properties'];nested=props['target_binding']['properties']
  for key in ('schema','input_request_sha256','producer_head','math_head'):self.assertEqual(props[key]['const'],value[key])
  for key in ('target_request_schema_sha256','producer_request_sha256','producer_head','math_head'):self.assertEqual(nested[key]['const'],value['target_binding'][key])
 def test_retired_source_and_schema_literals_are_not_constraints(self):
  value=json.loads(api().render_records(ROOT)['profile.schema.json']);props=value['properties'];nested=props['target_binding']['properties']
  for old in ('de8194f71311a6d7dddb69be9de812030ed1f13f','b3cb935aee7d6569d6fd0cfaff70ea9b9e5f0df3'):self.assertNotEqual(props['math_head']['const'],old);self.assertNotEqual(nested['math_head']['const'],old)
  for old in ('b99913690ce29ce60e73414cc4d626ca989916ce','fc0bed4937ab5dbb039320aae48e49b01b31bb43'):self.assertNotEqual(props['producer_head']['const'],old);self.assertNotEqual(nested['producer_head']['const'],old)
  self.assertNotEqual(nested['target_request_schema_sha256']['const'],'342187bea8ace00b409f04a0fb739757184b5bb933741b597a83ed08a765ce4d')
 def test_cohort_drift_is_refused_before_generating_records(self):
  with tempfile.TemporaryDirectory() as directory:
   root=pathlib.Path(directory);copy_support(root);path=root/SUPPORT[0];cohort=json.loads(path.read_bytes());cohort['sources']['math']['commit']='a'*40;path.write_text(json.dumps(cohort))
   with self.assertRaises(ValueError):api().render_records(root)
 def test_coherent_future_revisions_are_derived_not_hardcoded(self):
  with tempfile.TemporaryDirectory() as directory:
   root=pathlib.Path(directory);copy_support(root)
   cp=root/SUPPORT[0];cohort=json.loads(cp.read_bytes());old_math=cohort['sources']['math']['commit'];old_term=cohort['sources']['terminan']['commit'];cohort['sources']['math']['commit']='a'*40;cohort['sources']['terminan']['commit']='b'*40;cp.write_text(json.dumps(cohort))
   sp=root/SUPPORT[1];old_schema=hashlib.sha256(sp.read_bytes()).hexdigest();schema=json.loads(sp.read_bytes());schema['properties']['target_version']['const']='b'*40;sp.write_text(json.dumps(schema,sort_keys=True));new_schema=hashlib.sha256(sp.read_bytes()).hexdigest()
   bp=root/SUPPORT[3];bp.write_text(bp.read_text().replace(old_math,'a'*40).replace(old_term,'b'*40).replace(old_schema,new_schema))
   mp=root/SUPPORT[2];manifest=json.loads(mp.read_bytes());binding=manifest['canonical_native_binding'];binding.update(math_head='a'*40,terminan_head='b'*40,target_schema_sha256=new_schema);manifest['root_modules_sha256']['unified_system/gateway_research_identity.py']=hashlib.sha256(bp.read_bytes()).hexdigest();mp.write_text(json.dumps(manifest))
   result=json.loads(api().render_records(root)['profile.schema.json'])['properties'];self.assertEqual(result['math_head']['const'],'a'*40);self.assertEqual(result['producer_head']['const'],'b'*40);self.assertEqual(result['target_binding']['properties']['target_request_schema_sha256']['const'],new_schema)
if __name__=='__main__':unittest.main()
