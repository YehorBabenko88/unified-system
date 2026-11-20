"""Pure canonical native DTO checks; crypto operations and native I/O refuse."""
import base64,copy,hashlib,json,pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(pathlib.Path(__file__).parent)]
from canonical_profile_fixture import bind_profile,target_bytes,TARGET_SCHEMA_SHA
from test_root_authority import inert_crypto_imports
class CanonicalNativeBindingTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.imports=inert_crypto_imports();cls.imports.__enter__()
  from unified_system import gateway_research_identity
  cls.core=gateway_research_identity
 @classmethod
 def tearDownClass(cls):cls.imports.__exit__(None,None,None)
 def setUp(self):
  self.actor='11111111-1111-4111-8111-111111111111';self.generation='22222222-2222-4222-8222-222222222222'
  self.profile={'principal_registry':{'a'*64:self.actor}}
  self.target=bind_profile(self.profile,request_id='33333333-3333-4333-8333-333333333333',job_id='44444444-4444-4444-8444-444444444444',generation=self.generation,actor=self.actor,quota_owner='local-quota')
 def check(self):return self.core._target_binding(self.profile,generation=self.generation,actor=self.actor,quota_owner='local-quota')
 def rebind(self):
  raw=target_bytes(self.target);self.profile['target_binding'].update(target_request_canonical_base64=base64.b64encode(raw).decode('ascii'),target_request_sha256=hashlib.sha256(raw).hexdigest())
 def test_canonical_binding_matches_exact_schema_and_both_sources(self):
  self.assertEqual(self.core._PRODUCER,'a2f63228aeb7436721eaf3fe6251c94ab7e5e087');self.assertEqual(self.core._MATH,'7ed299b6480b2cb683ee91bd162ed9d76e99aa7f')
  self.assertEqual(self.check(),self.profile['target_binding'])
  self.assertEqual(hashlib.sha256((ROOT/'docs/intelligence/canonical-native-profile/request.schema.json').read_bytes()).hexdigest(),TARGET_SCHEMA_SHA)
 def test_every_retired_profile_schema_is_refused(self):
  for schema in ('unified.authority.research-lab-profile.v1-review1','unified.authority.target-bound-research-profile.v2-review1'):
   self.profile['schema']=schema
   with self.subTest(schema=schema),self.assertRaises(self.core.ResearchIdentityDenied):self.check()
 def test_rebound_retired_targets_and_direct_mode_are_refused(self):
  original=copy.deepcopy(self.target)
  for key,value in (('target_kind','MetaAnalyse'),('target_version','f3c01a23fa5baaeeeb28eb8e9397e72b5ef4d5a1'),('target_capability','meta.ohlcv.untouched_levels.v1'),('schema','unified.gateway.target-native-request.v1-review1'),('execution_mode','DIRECT_DISPOSABLE_SYNTHETIC'),('parameters_digest','0'*64)):
   self.target=copy.deepcopy(original);self.target[key]=value;self.rebind()
   with self.subTest(key=key),self.assertRaises(self.core.ResearchIdentityDenied):self.check()
 def test_math_and_producer_rebinding_cannot_change_fixed_cohort(self):
  original=copy.deepcopy(self.profile)
  for key,values in (('math_head',('f'*40,'de8194f71311a6d7dddb69be9de812030ed1f13f','a5868944bf1bae813403a32b22d329c1da6f8238','e80d622eed7c01b109062b68e750f2b70bcccff7','370972f2eeec18824fecd3ec471f0a514e7dd030','b3cb935aee7d6569d6fd0cfaff70ea9b9e5f0df3','0dcb85e76214453e2e1ff2abdfb8734cde5922b5')),('producer_head',('f'*40,'b99913690ce29ce60e73414cc4d626ca989916ce','75a906d36574bfdc19acd966e79a6c168dc71ad4','042b075dda0fc8cf6bb829d758632cfa989e8e55','221a2562f70558e7753a92499fee1c3f2e706bfb','fc0bed4937ab5dbb039320aae48e49b01b31bb43','742d9681b9b57e0252182e3edf4c1dd90ba19c53'))):
   for value in values:
    self.profile=copy.deepcopy(original);self.profile[key]=value;self.profile['target_binding'][key]=value
    with self.subTest(key=key,value=value),self.assertRaises(self.core.ResearchIdentityDenied):self.check()
 def test_actor_generation_and_quota_join_are_literal(self):
  original=copy.deepcopy(self.target)
  for key,value in (('principal_id',self.generation),('authority_generation',self.actor),('quota_owner','other-quota')):
   self.target=copy.deepcopy(original);self.target[key]=value;self.rebind()
   with self.subTest(key=key),self.assertRaises(self.core.ResearchIdentityDenied):self.check()
 def test_float_bool_and_changed_resource_caps_are_refused(self):
  original=copy.deepcopy(self.target)
  for value in (3.0,True,4):
   self.target=copy.deepcopy(original);self.target['resource_budget']['max_rows']=value;self.rebind()
   with self.subTest(value=value),self.assertRaises(self.core.ResearchIdentityDenied):self.check()
 def test_noncanonical_or_mismatching_target_bytes_are_refused(self):
  self.profile['target_binding']['target_request_sha256']='f'*64
  with self.assertRaises(self.core.ResearchIdentityDenied):self.check()
  raw=json.dumps(self.target,sort_keys=True).encode('ascii');self.profile['target_binding'].update(target_request_canonical_base64=base64.b64encode(raw).decode('ascii'),target_request_sha256=hashlib.sha256(raw).hexdigest())
  with self.assertRaises(self.core.ResearchIdentityDenied):self.check()
 def test_exact_original_submit_and_old_submit_schema_are_distinct(self):
  p=self.profile;p.update(cluster_id='55555555-5555-4555-8555-555555555555',resources={'cpu_millicores':'1000'})
  b=p['target_binding'];submit=dict(schema='unified.gateway.canonical-job-submit.v2',operation='SUBMIT_RESEARCH',cluster_id=p['cluster_id'],cluster_generation=b['cluster_generation'],request_id=b['request_id'],job_id=b['job_id'],original_actor_principal_id=b['actor_principal_id'],quota_owner_id=b['quota_owner_id'],idempotency_key=b['idempotency_key'],commissioned_profile_sha256='a'*64,input_request_sha256=p['input_request_sha256'],producer_head=p['producer_head'],math_head=p['math_head'],resources=p['resources'])
  self.core._profile_request(p,'a'*64,scope='SUBMIT_RESEARCH',raw=self.core.canonical(submit))
  submit['schema']='unified.gateway.lab-job-submit.v1-review1'
  with self.assertRaises(self.core.ResearchIdentityDenied):self.core._profile_request(p,'a'*64,scope='SUBMIT_RESEARCH',raw=self.core.canonical(submit))
 def test_policy_read_path_rejects_retired_or_rebound_profiles_before_identity(self):
  from test_root_authority import complete
  from datetime import datetime,timezone
  p=self.profile;p.update(cluster_id='55555555-5555-4555-8555-555555555555',realm_id='66666666-6666-4666-8666-666666666666',resources={'cpu_millicores':'1000','resident_memory_bytes':'268435456','max_artifact_bytes':'1048576'},expiry_semantics='NATIVE_SESSION_INVALIDATION_NOT_UTC_AT_COMMIT',expires_utc='2026-11-20T12:05:00Z')
  fingerprint='a'*64;service='77777777-7777-4777-8777-777777777777';policy_id='88888888-8888-4888-8888-888888888888'
  wall=datetime(2026,11,20,12,0,tzinfo=timezone.utc).timestamp();original=copy.deepcopy(p)
  for change in ({},{'schema':'unified.authority.research-lab-profile.v1-review1'},{'schema':'unified.authority.target-bound-research-profile.v2-review1'},{'math_head':'f'*40},{'producer_head':'f'*40},{'input_request_sha256':'f'*64},{'foreign':True}):
   current=copy.deepcopy(original);current.update(change);pin=hashlib.sha256(self.core.canonical(current)).hexdigest()
   obj=object.__new__(self.core.ResearchIdentityBroker);obj._namespace='unified/'+p['cluster_id'];obj._prefix=obj._namespace+'/runtime-v2/canonical-research-v3/'+p['realm_id']+'/'
   obj._generation=self.generation;obj._profile_sha=pin;obj._cluster=p['cluster_id'];obj._realm=p['realm_id'];obj._wall=wall;obj._clock=lambda:(wall,wall)
   principal=dict(schema='unified.authority.research-lab-principal.v1-review1',actor_id=self.actor,service_id=service,certificate_sha256=fingerprint,quota_owner_id='local-quota',policy_id=policy_id,profile_sha256=pin,state='ACTIVE')
   policy=dict(schema='unified.authority.research-lab-policy.v1-review1',policy_id=policy_id,actor_id=self.actor,profile_sha256=pin,revision='1',state='ACTIVE',scopes=['READ_RESEARCH','SUBMIT_RESEARCH'],expires_utc=p['expires_utc'])
   records={obj._namespace+'/commands/generation':{'generation':self.generation},obj._prefix+'profile-registry/'+pin:current,obj._prefix+'principals/'+self.actor:principal,obj._prefix+'policies/'+policy_id:policy}
   calls=[]
   async def read(key):
    calls.append(key);return self.core.ResearchNativeRecord(key,1,self.core.canonical(records[key]),'')
   obj._read=read
   if change:
    with self.subTest(change=change),self.assertRaises(self.core.ResearchIdentityDenied):complete(obj._policy(fingerprint,service))
    self.assertEqual(len(calls),2)
   else:
    value=complete(obj._policy(fingerprint,service));self.assertEqual(value[1],principal);self.assertEqual(len(calls),4)
if __name__=='__main__':unittest.main()
