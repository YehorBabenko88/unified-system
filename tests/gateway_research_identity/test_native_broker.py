"""Real disposable mTLS/ACL/three-voter principal sessions; NO job grants."""
raise RuntimeError('NATIVE_QUALIFICATION_PREREQUISITES_LOCKED')
import asyncio,base64,copy,hashlib,json,os,sys,tempfile,types,unittest,uuid
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
from jsonschema import Draft202012Validator
import subprocess

GRID=Path(os.environ.get('A2_RESEARCH_GRID_SOURCE','C:/Users/LS-5/Documents/Codex/2026-11-06/codex-agent-2-high-availability-distributed/work/grid-assignment-native-20261107'))
sys.path.insert(0,str(GRID))
from grid.coordination import ConsulConfig,ConsulSessionAuthority,CoordinationLost
from grid.authority_runtime_v1 import canonical
from unified_system.gateway_identity import GatewayAuditSink
from unified_system.gateway_research_identity import ResearchIdentityBroker,ResearchIdentityDenied,ResearchIdentityUnavailable
from consul_lab import ConsulLab

ROOT=Path(__file__).resolve().parents[2]
fixture_raw=subprocess.check_output(['git','--no-replace-objects','-C',str(ROOT),'show',
    'f155126a95e80139b1b9679c1870ffd66c29360e:tests/test_gateway_identity.py'])
assert hashlib.sha256(fixture_raw).hexdigest()=='b26fe114c778a8b8a95bc3de822dd7c7a4f57dd12277e9fdcbc96cfb5bc4199f'
fixture=types.ModuleType('a2_pinned_tls_fixture');sys.modules[fixture.__name__]=fixture
exec(compile(fixture_raw,'<pinned-TLSFixture>','exec'),fixture.__dict__)

class NativeBrokerTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='a2-native-principal-')
        cls.lab=ConsulLab(os.environ.get('A2_RESEARCH_CONSUL_BINARY',
            'C:/Users/LS-5/Documents/Codex/2026-11-06/codex-agent-8-independent-security-ci/work/consul-bin/extracted/consul.exe'),Path(cls.temp.name)/'consul')
        try: cls.lab.__enter__()
        except BaseException: cls.temp.cleanup();raise
    @classmethod
    def tearDownClass(cls):
        cls.lab.__exit__(None,None,None);cls.temp.cleanup()
    async def asyncSetUp(self):
        self.cluster=str(uuid.uuid4());self.generation=str(uuid.uuid4());self.realm=str(uuid.uuid4())
        self.actor=str(uuid.uuid4());self.policy=str(uuid.uuid4());self.service=str(uuid.uuid4())
        self.tls=fixture.TLSFixture(client_uri='urn:unified:test:research-service:'+self.service)
        self.addCleanup(self.tls.close)
        self.authority=ConsulSessionAuthority(ConsulConfig(tuple(self.lab.nodes),'unified/'+self.cluster,
            isolated_lab=True,acl_token=self.lab.token,ttl_seconds=15,request_timeout=2))
        self.addAsyncCleanup(self.authority.close)
        self.leader=await self.authority.acquire('research-source')
        self.assertIsNotNone(self.leader)
        self.session_responses=[]
        async def observe(response):
            if response.request.url.path=='/v1/session/create':
                raw=await response.aread()
                self.session_responses.append(dict(status=response.status_code,raw=raw.decode('ascii')))
        self.authority.client.event_hooks['response'].append(observe)  # observes REAL transport, no mock response
        self.prefix=self.authority.config.namespace+'/runtime-v1/research-lab-v1/'+self.realm+'/'
        self.fingerprint=hashlib.sha256(self.tls.client_der).hexdigest()
        expiry=(datetime.now(timezone.utc)+timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%SZ')
        self.profile=dict(schema='unified.authority.research-lab-profile.v1-review1',cluster_id=self.cluster,
            realm_id=self.realm,principal_registry={self.fingerprint:self.actor},
            input_request_sha256='c548e2ffcd542d5d741682303694b3c6d06507740f158a6e30089b2d5355f648',
            producer_head='aed8a7c8a952f96803c207d5e90b133969a47f04',
            resources=dict(cpu_millicores='1000',resident_memory_bytes='268435456',max_artifact_bytes='1048576'),
            expiry_semantics='NATIVE_SESSION_INVALIDATION_NOT_UTC_AT_COMMIT',expires_utc=expiry)
        self.profile_sha=hashlib.sha256(canonical(self.profile)).hexdigest()
        self.principal=dict(schema='unified.authority.research-lab-principal.v1-review1',actor_id=self.actor,
            service_id=self.service,certificate_sha256=self.fingerprint,quota_owner_id='lab-quota',policy_id=self.policy,
            profile_sha256=self.profile_sha,state='ACTIVE')
        self.policy_body=dict(schema='unified.authority.research-lab-policy.v1-review1',policy_id=self.policy,
            actor_id=self.actor,profile_sha256=self.profile_sha,revision='1',state='ACTIVE',
            scopes=['CANCEL_OWN_JOB','READ_RESEARCH','SUBMIT_RESEARCH'],expires_utc=expiry)
        # Genuine Root commissioning only. NO Assignment/hold/job/receipt seeded.
        await self.put(self.authority.config.namespace+'/commands/generation',{'generation':self.generation})
        for key,value in (('profile-registry/'+self.profile_sha,self.profile),('principals/'+self.actor,self.principal),
                          ('policies/'+self.policy,self.policy_body)):
            await self.put(self.prefix+key,value)
        self.audit=GatewayAuditSink(max_events=100)
        self.broker=ResearchIdentityBroker(authority=self.authority,generation=self.generation,realm_id=self.realm,
            profile_sha256=self.profile_sha,server_ssl_context=self.tls.server_context,
            server_certificate_der=self.tls.server_der,audit_sink=self.audit)
        self.addAsyncCleanup(self.broker.close)
    async def put(self,key,value):
        result=await self.authority._request('PUT','/v1/kv/'+key,content=canonical(value));self.assertIs(result,True)
    async def test_actual_mtls_native_session_and_sealed_capture(self):
        context=await self.broker.open_session(self.tls.accepted,leader=self.leader)
        capture=await self.broker.capture_current(context,scope='SUBMIT_RESEARCH',request_bytes=b'original-intent')
        snapshot=ResearchIdentityBroker.require_capture(self.broker,capture,expected_authority=self.authority,
            scope='SUBMIT_RESEARCH',request_bytes=b'original-intent')
        self.assertEqual(snapshot.actor_id,self.actor)
        class ScopeEqualityClaim:
            def __eq__(self,other):return True
        with self.assertRaises(ResearchIdentityDenied):
            self.broker.require_capture(capture,expected_authority=self.authority,
                scope=ScopeEqualityClaim(),request_bytes=b'original-intent')
        with self.assertRaises(ResearchIdentityDenied):
            self.broker.require_capture(capture,expected_authority=self.authority,
                scope='SUBMIT_RESEARCH',request_bytes=b'x'*16385)
        lock=snapshot.records[-1]
        schema_dir=ROOT/'docs/intelligence/research-identity'
        for name,record in zip(('profile','principal','policy','principal_session'),snapshot.records[1:],strict=True):
            schema=json.loads((schema_dir/(name+'.schema.json')).read_bytes())
            Draft202012Validator.check_schema(schema)
            Draft202012Validator(schema).validate(json.loads(record.raw))
        self.assertEqual(lock.session,snapshot.session_id);self.assertGreater(lock.index,0)
        native=await self.authority._request('GET','/v1/session/info/'+snapshot.session_id)
        self.assertEqual(native[0]['ID'],snapshot.session_id)
        self.assertIs(self.tls.client.getpeercert(binary_form=True)==self.tls.server_der,True)
        with self.assertRaises(ResearchIdentityDenied):
            ResearchIdentityBroker.require_capture(self.broker,capture,expected_authority=object(),
                scope='SUBMIT_RESEARCH',request_bytes=b'original-intent')
        with self.assertRaises(ResearchIdentityDenied):
            ResearchIdentityBroker.require_capture(self.broker,capture,expected_authority=self.authority,
                scope='SUBMIT_RESEARCH',request_bytes=b'changed-intent')
        evidence=os.environ.get('A2_RESEARCH_EVIDENCE_OUT')
        if evidence:
            folder=Path(evidence).resolve();folder.mkdir(parents=True,exist_ok=True)
            created=next(row for row in self.session_responses if json.loads(row['raw'])['ID']==snapshot.session_id)
            report=dict(scope='ACTUAL_MTLS_CONSUL_PRINCIPAL_SESSION_ONLY_NO_JOB_GRANT',
                session_create_response=created,session_info=native,
                native_lock=dict(key=lock.key,modify_index=lock.index,session=lock.session,raw_value=lock.raw.decode('ascii')),
                source_session_id=snapshot.session_id,canonical_roundtrip=str(uuid.UUID(snapshot.session_id)),
                uuid_version_bits=uuid.UUID(snapshot.session_id).version,
                exact_join=json.loads(created['raw'])['ID']==snapshot.session_id==lock.session==json.loads(lock.raw)['session_id'],
                client_observed_loaded_server_der=self.tls.client.getpeercert(binary_form=True)==self.tls.server_der,
                binary_sha256=hashlib.sha256(self.lab.binary.read_bytes()).hexdigest(),
                binary_version=subprocess.check_output([str(self.lab.binary),'version']).decode().splitlines()[0],
                acl='DEFAULT_DENY_REAL_CLIENT_403_CHECK_SEPARATE',native_human=False)
            (folder/'actual-native-session.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    async def test_actual_native_policy_revocation_and_session_invalidation(self):
        context=await self.broker.open_session(self.tls.accepted,leader=self.leader)
        await self.put(self.prefix+'policies/'+self.policy,dict(self.policy_body,state='REVOKED',revision='2'))
        with self.assertRaises(ResearchIdentityDenied):
            await self.broker.capture_current(context,scope='SUBMIT_RESEARCH',request_bytes=b'original')
        await self.put(self.prefix+'policies/'+self.policy,dict(self.policy_body,revision='3'))
        capture=await self.broker.capture_current(context,scope='SUBMIT_RESEARCH',request_bytes=b'original')
        snapshot=self.broker.require_capture(capture,expected_authority=self.authority,scope='SUBMIT_RESEARCH',request_bytes=b'original')
        await self.authority._request('PUT','/v1/session/destroy/'+snapshot.session_id)
        with self.assertRaises(ResearchIdentityDenied):
            await self.broker.capture_current(context,scope='SUBMIT_RESEARCH',request_bytes=b'original')
    async def test_forward_utc_jump_expires_real_issued_capture(self):
        expiry=datetime.now(timezone.utc)+timedelta(seconds=30)
        await self.put(self.prefix+'policies/'+self.policy,dict(self.policy_body,expires_utc=expiry.strftime('%Y-%m-%dT%H:%M:%SZ')))
        context=await self.broker.open_session(self.tls.accepted,leader=self.leader)
        capture=await self.broker.capture_current(context,scope='SUBMIT_RESEARCH',request_bytes=b'clock')
        with patch('unified_system.gateway_research_identity._utc',return_value=expiry.timestamp()+1):
            with self.assertRaises(ResearchIdentityDenied):
                self.broker.require_capture(capture,expected_authority=self.authority,scope='SUBMIT_RESEARCH',request_bytes=b'clock')
    async def test_shortened_native_policy_expiry_bounds_new_capture(self):
        context=await self.broker.open_session(self.tls.accepted,leader=self.leader)
        expiry=datetime.now(timezone.utc)+timedelta(seconds=30)
        await self.put(self.prefix+'policies/'+self.policy,dict(self.policy_body,revision='2',expires_utc=expiry.strftime('%Y-%m-%dT%H:%M:%SZ')))
        capture=await self.broker.capture_current(context,scope='SUBMIT_RESEARCH',request_bytes=b'shortened')
        with patch('unified_system.gateway_research_identity._utc',return_value=expiry.timestamp()+1):
            with self.assertRaises(ResearchIdentityDenied):
                self.broker.require_capture(capture,expected_authority=self.authority,scope='SUBMIT_RESEARCH',request_bytes=b'shortened')
    async def test_acl_default_deny_client_cannot_write_policy(self):
        status,_=self.lab.request(self.lab.nodes[0],'PUT','/v1/kv/'+self.prefix+'policies/'+self.policy,
                                  canonical(dict(self.policy_body,state='ACTIVE')),authenticated=False)
        self.assertEqual(status,403)
    async def test_close_during_actual_native_create_retires_owned_session(self):
        arrived=asyncio.Event();release=asyncio.Event();created=[]
        async def pause_actual_response(response):
            if response.request.url.path=='/v1/session/create':
                raw=await response.aread();created.append(json.loads(raw)['ID'])
                arrived.set();await release.wait()
        self.authority.client.event_hooks['response'].append(pause_actual_response)
        opening=asyncio.create_task(self.broker.open_session(self.tls.accepted,leader=self.leader))
        closing=None
        try:
            await asyncio.wait_for(arrived.wait(),3)
            closing=asyncio.create_task(self.broker.close())
            await asyncio.sleep(0)  # let close latch before resuming the real response
            release.set()
            with self.assertRaises(ResearchIdentityUnavailable):await opening
            await closing
            self.assertEqual(len(created),1)
            for session in created:
                self.assertEqual(await self.authority._request('GET','/v1/session/info/'+session),[])
            self.assertEqual(self.broker._sessions,set())
        finally:
            release.set()
            await asyncio.gather(opening,*([closing] if closing else []),return_exceptions=True)
            self.authority.client.event_hooks['response'].remove(pause_actual_response)
    async def test_read_scope_cannot_be_upgraded_by_request(self):
        await self.put(self.prefix+'policies/'+self.policy,dict(self.policy_body,scopes=['READ_RESEARCH']))
        context=await self.broker.open_session(self.tls.accepted,leader=self.leader)
        with self.assertRaises(ResearchIdentityDenied):
            await self.broker.capture_current(context,scope='SUBMIT_RESEARCH',request_bytes=b'{"role":"admin"}')
    async def test_invalidate_latches_and_stale_capture_is_no_permission(self):
        context=await self.broker.open_session(self.tls.accepted,leader=self.leader)
        capture=await self.broker.capture_current(context,scope='SUBMIT_RESEARCH',request_bytes=b'original')
        await self.broker.invalidate_context(context)
        with self.assertRaises(ResearchIdentityDenied):
            self.broker.require_capture(capture,expected_authority=self.authority,scope='SUBMIT_RESEARCH',request_bytes=b'original')
    async def test_stale_policy_capture_fails_actual_native_cas(self):
        context=await self.broker.open_session(self.tls.accepted,leader=self.leader)
        capture=await self.broker.capture_current(context,scope='SUBMIT_RESEARCH',request_bytes=b'original')
        snapshot=self.broker.require_capture(capture,expected_authority=self.authority,scope='SUBMIT_RESEARCH',request_bytes=b'original')
        await self.put(self.prefix+'policies/'+self.policy,dict(self.policy_body,state='REVOKED',revision='2'))
        probe=self.prefix+'identity-native-probes/'+str(uuid.uuid4())
        ops=[{'KV':dict(Verb='check-index',Key=r.key,Index=r.index)} for r in snapshot.records]
        ops+=[{'KV':dict(Verb='check-session',Key=snapshot.records[-1].key,Session=snapshot.session_id)},
              {'KV':dict(Verb='cas',Key=probe,Index=0,Value=base64.b64encode(canonical({'schema':'untrusted.identity-policy-probe.v1'})).decode())}]
        with self.assertRaises(CoordinationLost): await self.authority._request('PUT','/v1/txn',json=ops)
        self.assertIsNone(await self.authority._request('GET','/v1/kv/'+probe,params={'consistent':''},missing_ok=True))
    async def test_real_foreign_native_session_cannot_rebind_issued_context(self):
        context=await self.broker.open_session(self.tls.accepted,leader=self.leader)
        capture=await self.broker.capture_current(context,scope='SUBMIT_RESEARCH',request_bytes=b'original')
        snapshot=self.broker.require_capture(capture,expected_authority=self.authority,scope='SUBMIT_RESEARCH',request_bytes=b'original')
        lock=snapshot.records[-1]
        other=await self.authority._request('PUT','/v1/session/create',json={
            'Name':'foreign-negative-only','TTL':'10s','Behavior':'release','LockDelay':'0s','NodeChecks':[]})
        try:
            await self.authority._request('PUT','/v1/session/destroy/'+snapshot.session_id)
            self.assertIs(await self.authority._request('PUT','/v1/kv/'+lock.key,
                params={'acquire':other['ID']},content=lock.raw),True)
            with self.assertRaises(ResearchIdentityDenied):
                await self.broker.capture_current(context,scope='SUBMIT_RESEARCH',request_bytes=b'original')
        finally: await self.authority._request('PUT','/v1/session/destroy/'+other['ID'])
    async def test_audit_full_invalidation_still_destroys_own_native_session(self):
        context=await self.broker.open_session(self.tls.accepted,leader=self.leader)
        capture=await self.broker.capture_current(context,scope='SUBMIT_RESEARCH',request_bytes=b'original')
        snapshot=self.broker.require_capture(capture,expected_authority=self.authority,scope='SUBMIT_RESEARCH',request_bytes=b'original')
        self.audit._max=len(self.audit._events)
        with self.assertRaises(ResearchIdentityUnavailable): await self.broker.invalidate_context(context)
        self.audit.drain()
        # Consul1.22.2 session/info returns an empty JSON list after destroy.
        self.assertEqual(await self.authority._request('GET','/v1/session/info/'+snapshot.session_id,missing_ok=True),[])
        self.assertEqual((await self.broker._read(snapshot.records[-1].key)).session,'')
        with self.assertRaises(ResearchIdentityDenied):
            self.broker.require_capture(capture,expected_authority=self.authority,scope='SUBMIT_RESEARCH',request_bytes=b'original')
    async def test_z_real_one_of_three_no_quorum_is_unavailable(self):
        context=await self.broker.open_session(self.tls.accepted,leader=self.leader)
        for p in self.lab.processes[1:]:
            if p.poll() is None: p.kill()
            p.wait(timeout=10)
        with self.assertRaises(ResearchIdentityUnavailable):
            await self.broker.capture_current(context,scope='SUBMIT_RESEARCH',request_bytes=b'original')

if __name__=='__main__': unittest.main()
