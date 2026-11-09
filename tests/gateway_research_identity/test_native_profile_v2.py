"""Actual own mTLS/Consul profile-v2 source; no issued jobs or grants seeded."""
import base64,copy,hashlib,json,uuid,unittest
from test_native_broker import NativeBrokerTests,canonical
from unified_system.gateway_research_identity import ResearchIdentityBroker,ResearchIdentityDenied,ResearchIdentityUnavailable

TARGET_SCHEMA_SHA='faf01152678c5b066145dcafebe92f593a641a54dac84da3ce1e1df94c0fb261'
INPUT_SHA='c548e2ffcd542d5d741682303694b3c6d06507740f158a6e30089b2d5355f648'
PRODUCER='aed8a7c8a952f96803c207d5e90b133969a47f04'
def target_bytes(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')

class NativeProfileV2Tests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):NativeBrokerTests.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls):NativeBrokerTests.tearDownClass.__func__(cls)
    put=NativeBrokerTests.put
    async def asyncSetUp(self):
        await NativeBrokerTests.asyncSetUp(self)
        self.job=str(uuid.uuid4());self.original=str(uuid.uuid4())
        self.target=dict(schema='unified.gateway.target-native-request.v1-review1',request_id=self.original,
            target_kind='MetaAnalyse',target_capability='meta.ohlcv.untouched_levels.v1',target_version='f3c01a23fa5baaeeeb28eb8e9397e72b5ef4d5a1',
            dataset_manifest_id='local-sha256:33d5bf0f918884c8908795b384e0964a48a1351c808800964b8cacf3f83e28b6',dataset_revision='LOCAL_FIXTURE_1',
            experiment_id='fixture.gateway.btc.levels',strategy_version=None,parameters_digest=INPUT_SHA,
            execution_mode='NATIVE_RESEARCH_ADMISSION_REQUEST_NOT_PERMISSION',
            resource_budget=dict(max_input_bytes=16384,max_output_bytes=16384,max_rows=3,max_executions=1),
            quota_owner=self.principal['quota_owner_id'],principal_id=self.actor,authority_generation=self.generation,
            assignment_revision=None,fencing_token=None,idempotency_key='native_original_1',
            result_schema='unified.gateway.native-target-observation.v1-review1',result_artifact_ref=None)
        self.profile['schema']='unified.authority.target-bound-research-profile.v2-review1'
        self.profile['target_binding']=dict(target_request_schema_sha256=TARGET_SCHEMA_SHA,
            target_request_canonical_base64='',target_request_sha256='',request_id=self.original,job_id=self.job,
            idempotency_key=self.target['idempotency_key'],cluster_generation=self.generation,
            actor_principal_id=self.actor,quota_owner_id=self.target['quota_owner'],producer_request_sha256=INPUT_SHA,producer_head=PRODUCER)
        self.rebind_target()
        await self.commission(self.profile)
    def rebind_target(self):
        raw=target_bytes(self.target)
        self.profile['target_binding'].update(target_request_canonical_base64=base64.b64encode(raw).decode(),target_request_sha256=hashlib.sha256(raw).hexdigest())
    async def commission(self,profile):
        await self.broker.close()
        self.profile=copy.deepcopy(profile);self.profile_sha=hashlib.sha256(canonical(self.profile)).hexdigest()
        self.principal['profile_sha256']=self.profile_sha;self.policy_body['profile_sha256']=self.profile_sha
        # Genuine Root bootstrap of profile/principal/policy only. Never seed job,
        # Assignment, hold, lease, command receipt or a fake worker proof.
        await self.put(self.prefix+'profile-registry/'+self.profile_sha,self.profile)
        await self.put(self.prefix+'principals/'+self.actor,self.principal)
        await self.put(self.prefix+'policies/'+self.policy,self.policy_body)
        self.broker=ResearchIdentityBroker(authority=self.authority,generation=self.generation,realm_id=self.realm,
            profile_sha256=self.profile_sha,server_ssl_context=self.tls.server_context,
            server_certificate_der=self.tls.server_der,audit_sink=self.audit)
        self.addAsyncCleanup(self.broker.close)
    def submit(self):
        return dict(schema='unified.gateway.lab-job-submit.v1-review1',operation='SUBMIT_RESEARCH',cluster_id=self.cluster,
            cluster_generation=self.generation,request_id=self.original,job_id=self.job,
            original_actor_principal_id=self.actor,quota_owner_id=self.target['quota_owner'],idempotency_key=self.target['idempotency_key'],
            commissioned_profile_sha256=self.profile_sha,input_request_sha256=INPUT_SHA,producer_head=PRODUCER,resources=self.profile['resources'])
    async def test_00_actual_v2_principal_and_exact_submit_read_capture(self):
        context=await self.broker.open_session(self.tls.accepted,leader=self.leader)
        raw=canonical(self.submit())
        for scope in ('SUBMIT_RESEARCH','READ_RESEARCH'):
            capture=await self.broker.capture_current(context,scope=scope,request_bytes=raw)
            snapshot=ResearchIdentityBroker.require_capture(self.broker,capture,expected_authority=self.authority,scope=scope,request_bytes=raw)
            self.assertEqual(snapshot.actor_id,self.actor)
            self.assertEqual(snapshot.profile_sha256,self.profile_sha)
            self.assertEqual(snapshot.records[1].raw,canonical(self.profile))
            self.assertEqual(snapshot.records[-1].session,snapshot.session_id)
            native=await self.authority._request('GET','/v1/session/info/'+snapshot.session_id)
            self.assertEqual(native[0]['ID'],snapshot.session_id)
        self.assertIsNone(await self.authority._request('GET','/v1/kv/'+self.prefix+'jobs/'+self.job,params={'consistent':''},missing_ok=True))
    async def test_exact_cancel_is_separate_original_bound_identity_capture(self):
        context=await self.broker.open_session(self.tls.accepted,leader=self.leader)
        cancel=dict(schema='unified.gateway.lab-job-cancel.v1-review1',operation='CANCEL_OWN_JOB',cluster_id=self.cluster,
            cluster_generation=self.generation,request_id=str(uuid.uuid4()),job_id=self.job,
            original_actor_principal_id=self.actor,quota_owner_id=self.target['quota_owner'],idempotency_key='cancel_original_1',
            commissioned_profile_sha256=self.profile_sha,original_submit_request_id=self.original,
            original_submit_intent_sha256=hashlib.sha256(canonical(self.submit())).hexdigest())
        capture=await self.broker.capture_current(context,scope='CANCEL_OWN_JOB',request_bytes=canonical(cancel))
        self.assertEqual(self.broker.require_capture(capture,expected_authority=self.authority,scope='CANCEL_OWN_JOB',request_bytes=canonical(cancel)).actor_id,self.actor)
        cancel['original_submit_intent_sha256']='f'*64
        with self.assertRaises(ResearchIdentityDenied):
            await self.broker.capture_current(context,scope='CANCEL_OWN_JOB',request_bytes=canonical(cancel))
    async def test_wrong_lab_original_never_binds_valid_v2_context(self):
        context=await self.broker.open_session(self.tls.accepted,leader=self.leader)
        for field,value in (('job_id',str(uuid.uuid4())),('request_id',str(uuid.uuid4())),('idempotency_key','other_original'),('commissioned_profile_sha256','f'*64),('quota_owner_id','other_quota')):
            bad=self.submit();bad[field]=value
            with self.subTest(field=field),self.assertRaises(ResearchIdentityDenied):
                await self.broker.capture_current(context,scope='SUBMIT_RESEARCH',request_bytes=canonical(bad))
        with self.assertRaises(ResearchIdentityDenied):
            await self.broker.capture_current(context,scope='READ_RESEARCH',request_bytes=b'{"role":"SUBMIT_RESEARCH"}')
    async def test_fully_rebound_float_and_registry_actor_aliases_refuse(self):
        original=copy.deepcopy(self.profile);target=copy.deepcopy(self.target)
        for field,value in (('max_rows',3.0),('max_executions',True)):
            self.profile=copy.deepcopy(original);self.target=copy.deepcopy(target)
            self.target['resource_budget'][field]=value;self.rebind_target();await self.commission(self.profile)
            with self.subTest(field=field),self.assertRaises(ResearchIdentityDenied):
                await self.broker.open_session(self.tls.accepted,leader=self.leader)
        self.profile=copy.deepcopy(original);self.target=copy.deepcopy(target)
        foreign=str(uuid.uuid4());self.target['principal_id']=foreign
        self.profile['target_binding']['actor_principal_id']=foreign;self.rebind_target();await self.commission(self.profile)
        with self.assertRaises(ResearchIdentityDenied):await self.broker.open_session(self.tls.accepted,leader=self.leader)
    async def test_direct_profile_and_dot_key_cannot_be_upgraded(self):
        original=copy.deepcopy(self.profile);target=copy.deepcopy(self.target)
        self.target.update(schema='unified.gateway.target-request.v1',execution_mode='DIRECT_DISPOSABLE_SYNTHETIC')
        self.rebind_target();await self.commission(self.profile)
        with self.assertRaises(ResearchIdentityDenied):await self.broker.open_session(self.tls.accepted,leader=self.leader)
        self.profile=copy.deepcopy(original);self.target=copy.deepcopy(target)
        self.target['idempotency_key']='original.with.dot';self.profile['target_binding']['idempotency_key']=self.target['idempotency_key']
        self.rebind_target();await self.commission(self.profile)
        with self.assertRaises(ResearchIdentityDenied):await self.broker.open_session(self.tls.accepted,leader=self.leader)
    async def test_real_v2_policy_revocation_and_session_loss_refuse(self):
        context=await self.broker.open_session(self.tls.accepted,leader=self.leader);raw=canonical(self.submit())
        capture=await self.broker.capture_current(context,scope='SUBMIT_RESEARCH',request_bytes=raw)
        snapshot=self.broker.require_capture(capture,expected_authority=self.authority,scope='SUBMIT_RESEARCH',request_bytes=raw)
        await self.put(self.prefix+'policies/'+self.policy,dict(self.policy_body,state='REVOKED',revision='2'))
        with self.assertRaises(ResearchIdentityDenied):await self.broker.capture_current(context,scope='SUBMIT_RESEARCH',request_bytes=raw)
        await self.put(self.prefix+'policies/'+self.policy,dict(self.policy_body,revision='3'))
        await self.authority._request('PUT','/v1/session/destroy/'+snapshot.session_id)
        with self.assertRaises(ResearchIdentityDenied):await self.broker.capture_current(context,scope='SUBMIT_RESEARCH',request_bytes=raw)
    async def test_z_real_one_of_three_no_quorum_refuses_v2_capture(self):
        context=await self.broker.open_session(self.tls.accepted,leader=self.leader)
        for process in self.lab.processes[1:]:process.kill();process.wait(timeout=10)
        with self.assertRaises(ResearchIdentityUnavailable):
            await self.broker.capture_current(context,scope='READ_RESEARCH',request_bytes=canonical(self.submit()))

if __name__=='__main__':unittest.main()
