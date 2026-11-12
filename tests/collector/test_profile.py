"""Strict profile admission; no runtime/host/network admission is inferred."""
import copy,hashlib,json,unittest
from unified_system import collector_profile as cp

def fixture():
 return {'schema':'unified.data-only-collector.profile.v1','mode':'SYNTHETIC_OFFLINE','grid_launch_profile':'grid.data-only-collector.v1','context_id':'1'*32,'store_id':'96dce424-a40b-4f25-8500-26738dd278e5','source_manifest_sha256':'a'*64,'instrument_identity':'synthetic-btcusdt-v1','limits':{'frames':4,'frame_bytes':1048576,'raw_bytes':4194304,'duration_seconds':30},'network':{'rest':False,'websocket':False},'features':{'trading':False,'training':False,'math':False,'public_submit':False,'authority_mutation':False},'logging':{'schema':'unified.collector.logging.v1','max_file_bytes':65536,'file_count':3}}

class ProfileTests(unittest.TestCase):
 def parse(self,value):return cp.validate_collector_profile(value,manifest_sha256='a'*64)
 def test_store_identity_is_explicit_canonical_uuid4_not_context_alias(self):
  self.assertEqual(self.parse(fixture()).document['store_id'],fixture()['store_id'])
  for identity in (fixture()['store_id'].upper(),'1'*32,'96dce424-a40b-1f25-8500-26738dd278e5',None):
   value=fixture();value['store_id']=identity
   with self.subTest(identity=identity),self.assertRaises(cp.CollectorProfileRejected):self.parse(value)
 def test_non_builtin_strings_rejected_before_equality_callbacks(self):
  calls=[]
  class Trap(str):
   def __eq__(self,other):calls.append('eq');return True
  for field in ('schema','mode','grid_launch_profile','instrument_identity','source_manifest_sha256'):
   value=fixture();value[field]=Trap('wrong');calls.clear()
   with self.subTest(field=field),self.assertRaises(cp.CollectorProfileRejected):self.parse(value)
   self.assertEqual(calls,[])
  value=fixture();value['logging']['schema']=Trap('wrong');calls.clear()
  with self.assertRaises(cp.CollectorProfileRejected):self.parse(value)
  self.assertEqual(calls,[])
 def test_non_builtin_dictionary_keys_rejected_before_hash_callbacks(self):
  calls=[]
  class Key(str):
   def __hash__(self):calls.append('hash');return super().__hash__()
   def __eq__(self,other):calls.append('eq');return super().__eq__(other)
  for nested in (None,'limits','network','features','logging'):
   value=fixture();target=value if nested is None else value[nested]
   key=next(iter(target));item=target.pop(key);target[Key(key)]=item;calls.clear()
   with self.subTest(nested=nested),self.assertRaises(cp.CollectorProfileRejected):self.parse(value)
   self.assertEqual(calls,[])
 def test_context_identity_matches_logging_contract_without_aliases(self):
  for identity in ('named-context','A'*32,'1'*31,'1'*33):
   value=fixture();value['context_id']=identity
   with self.subTest(identity=identity),self.assertRaises(cp.CollectorProfileRejected):self.parse(value)
 def test_valid_profile_is_immutable_detached_and_not_authority(self):
  value=fixture();profile=self.parse(value);value['limits']['frames']=1
  self.assertEqual(profile.document['limits']['frames'],4)
  snapshot=profile.document;snapshot['network']['rest']=True
  self.assertFalse(profile.document['network']['rest']);self.assertFalse(profile.execution_authority)
  self.assertEqual(profile.sha256,hashlib.sha256(profile.encoded).hexdigest())
 def test_real_provider_permissions_are_rejected(self):
  for key in ('rest','websocket'):
   value=fixture();value['network'][key]=True
   with self.subTest(key=key),self.assertRaises(cp.CollectorProfileRejected):self.parse(value)
 def test_disabled_workloads_cannot_be_enabled(self):
  for key in fixture()['features']:
   value=fixture();value['features'][key]=True
   with self.subTest(key=key),self.assertRaises(cp.CollectorProfileRejected):self.parse(value)
 def test_source_binding_cannot_be_substituted(self):
  value=fixture();value['source_manifest_sha256']='b'*64
  with self.assertRaises(cp.CollectorProfileRejected):self.parse(value)
 def test_unknown_fields_versions_and_live_mode_fail_closed(self):
  for patch in ({'schema':'v2'},{'mode':'LIVE'},{'grid_launch_profile':None},{'instrument_identity':'BTCUSDT'},{'authority':'approved'}):
   value=fixture();value.update(patch)
   with self.subTest(patch=patch),self.assertRaises(cp.CollectorProfileRejected):self.parse(value)
 def test_limits_reject_bool_negative_oversize_and_inconsistent_budget(self):
  for key,bad in (('frames',True),('frames',0),('frames',5),('frame_bytes',1048577),('raw_bytes',4194305),('duration_seconds',121)):
   value=fixture();value['limits'][key]=bad
   with self.subTest(key=key,bad=bad),self.assertRaises(cp.CollectorProfileRejected):self.parse(value)
  value=fixture();value['limits']['raw_bytes']=1
  with self.assertRaises(cp.CollectorProfileRejected):self.parse(value)
 def test_logging_bounds_and_sensitive_fields_rejected(self):
  for patch in ({'file_count':0},{'max_file_bytes':True},{'max_file_bytes':1048577},{'token':'secret'},{'schema':'unknown'}):
   value=fixture();value['logging'].update(patch)
   with self.subTest(patch=patch),self.assertRaises(cp.CollectorProfileRejected):self.parse(value)
 def test_duplicate_json_nonfinite_and_oversize_rejected(self):
  for raw in (b'{"schema":"a","schema":"b"}',b'{"x":NaN}',b'x'*32769,b'\xff'):
   with self.subTest(raw=raw[:20]),self.assertRaises(cp.CollectorProfileRejected):cp.decode_collector_profile(raw,manifest_sha256='a'*64)
 def test_canonical_roundtrip_and_plan_only_are_explicit(self):
  value=fixture();profile=self.parse(value)
  decoded=cp.decode_collector_profile(json.dumps(value).encode(),manifest_sha256='a'*64)
  self.assertEqual(decoded.encoded,profile.encoded)
  plan=cp.collector_plan(profile)
  self.assertEqual(plan['status'],'PLAN_ONLY_NOT_EXECUTION_AUTHORITY');self.assertFalse(plan['provider_sends']);self.assertFalse(plan['installed'])
 def test_direct_dataclass_construction_cannot_skip_plan_validation(self):
  for raw in (b'[]',b'not-json',b'{"source_manifest_sha256":null}'):
   with self.subTest(raw=raw),self.assertRaises(cp.CollectorProfileRejected):cp.collector_plan(cp.CollectorProfile(raw))

if __name__=='__main__':unittest.main()
