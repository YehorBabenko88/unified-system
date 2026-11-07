import pathlib,subprocess,os,json
r=pathlib.Path.cwd();repo=r/'work/review-broker53-c02';o=r/'outputs/phase98';grid=r/'work/broker53-a8-grid40'
s='''import sys,unittest,asyncio,copy,base64,uuid,json
from datetime import datetime,timedelta,timezone
sys.path[:0]=['.','tests/gateway_research_identity']
import test_native_broker as f
from unified_system.gateway_research_identity import ResearchIdentityBroker,ResearchIdentityDenied
class A8Extra(f.NativeBrokerTests):
 async def test_a8_elapsed_expiry_and_opaque_source(self):
  expiry=datetime.now(timezone.utc)+timedelta(seconds=3)
  await self.put(self.prefix+'policies/'+self.policy,dict(self.policy_body,expires_utc=expiry.strftime('%Y-%m-%dT%H:%M:%SZ')))
  context=await self.broker.open_session(self.tls.accepted,leader=self.leader)
  capture=await self.broker.capture_current(context,scope='SUBMIT_RESEARCH',request_bytes=b'A8-original')
  snapshot=self.broker.require_capture(capture,expected_authority=self.authority,scope='SUBMIT_RESEARCH',request_bytes=b'A8-original')
  other=ResearchIdentityBroker(authority=self.authority,generation=self.generation,realm_id=self.realm,profile_sha256=self.profile_sha,server_ssl_context=self.tls.server_context,server_certificate_der=self.tls.server_der,audit_sink=self.audit);self.addAsyncCleanup(other.close)
  with self.assertRaises(ResearchIdentityDenied):ResearchIdentityBroker.require_capture(other,capture,expected_authority=self.authority,scope='SUBMIT_RESEARCH',request_bytes=b'A8-original')
  with self.assertRaises(ResearchIdentityDenied):self.broker.require_capture(capture,expected_authority=self.authority,scope='READ_RESEARCH',request_bytes=b'A8-original')
  with self.assertRaises(TypeError):copy.copy(context)
  await asyncio.sleep(max(0,(expiry.replace(microsecond=0)-datetime.now(timezone.utc)).total_seconds())+.15)
  with self.assertRaises(ResearchIdentityDenied):self.broker.require_capture(capture,expected_authority=self.authority,scope='SUBMIT_RESEARCH',request_bytes=b'A8-original')
  print(json.dumps(dict(case='ACTUAL_ELAPSED_EXPIRY_AND_SOURCE_IDENTITY',clock_patch=False,other_same_authority_broker_denied=True,wrong_scope_denied=True,context_copy_denied=True,elapsed_expiry_denied=True)))
 async def test_a8_native_destroy_blocks_target_cas(self):
  context=await self.broker.open_session(self.tls.accepted,leader=self.leader)
  capture=await self.broker.capture_current(context,scope='SUBMIT_RESEARCH',request_bytes=b'A8-original')
  snapshot=self.broker.require_capture(capture,expected_authority=self.authority,scope='SUBMIT_RESEARCH',request_bytes=b'A8-original')
  await self.authority._request('PUT','/v1/session/destroy/'+snapshot.session_id)
  # Local capture is evidence, not an execution permit/current native read.
  self.broker.require_capture(capture,expected_authority=self.authority,scope='SUBMIT_RESEARCH',request_bytes=b'A8-original')
  target=self.prefix+'identity-native-probes/'+str(uuid.uuid4());ops=[{'KV':dict(Verb='check-index',Key=x.key,Index=x.index)} for x in snapshot.records]
  ops += [{'KV':dict(Verb='check-session',Key=snapshot.records[-1].key,Session=snapshot.session_id)},{'KV':dict(Verb='cas',Key=target,Index=0,Value=base64.b64encode(f.canonical({'schema':'A8_UNTRUSTED_NEGATIVE_PROBE'})).decode())}]
  with self.assertRaises(f.CoordinationLost):await self.authority._request('PUT','/v1/txn',json=ops)
  self.assertIsNone(await self.authority._request('GET','/v1/kv/'+target,params={'consistent':''},missing_ok=True))
  print(json.dumps(dict(case='REAL_NATIVE_DESTROY_TARGET_CAS_DENIED',local_capture_is_evidence_not_permission=True,target_write_absent=True)))
suite=unittest.TestSuite(A8Extra(name) for name in ['test_a8_elapsed_expiry_and_opaque_source','test_a8_native_destroy_blocks_target_cas']);result=unittest.TextTestRunner(verbosity=2).run(suite);assert result.testsRun==2 and result.wasSuccessful() and not result.skipped
'''
(o/'extra-executed.py').write_text(s);env=os.environ.copy();env.update(A2_RESEARCH_GRID_SOURCE=str(grid),A2_RESEARCH_CONSUL_BINARY=str(r/'work/consul-bin/extracted/consul.exe'),PYTHONDONTWRITEBYTECODE='1');p=subprocess.run([str(r/'work/broker53-a8-env/Scripts/python.exe'),'-I','-B','-c',s],cwd=repo,env=env,capture_output=True,timeout=90);(o/'extra.stdout.jsonl').write_bytes(p.stdout);(o/'extra.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr;print(p.stdout.decode())
