"""Actual loopback mTLS/Consul composition; never an admitted research job."""
import hashlib
import unittest
import test_native_profile_v2 as fixture
from grid.authority_assignment_v1 import ResearchAdmissionResult
from unified_system.gateway_research_identity import ResearchIdentityBroker, ResearchIdentityDenied

class GatewayNegativeTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):fixture.NativeProfileV2Tests.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls):fixture.NativeProfileV2Tests.tearDownClass.__func__(cls)
    put=fixture.NativeProfileV2Tests.put
    commission=fixture.NativeProfileV2Tests.commission
    rebind_target=fixture.NativeProfileV2Tests.rebind_target
    submit=fixture.NativeProfileV2Tests.submit
    async def asyncSetUp(self):
        await fixture.NativeProfileV2Tests.asyncSetUp(self)
        self.original=fixture.canonical(self.submit())

    async def test_actual_mtls_submit_denied_and_own_context_invalidated(self):
        from unified_system.gateway_native_negative import DisposableNativeNegativeGateway
        gateway=DisposableNativeNegativeGateway(self.authority,self.generation,broker=self.broker)
        result=await gateway.submit(self.original,accepted_tls=self.tls.accepted,leader=self.leader)
        self.assertIs(type(result),ResearchAdmissionResult)
        self.assertEqual((result.outcome,result.reason,result.commit_status),
            ('DENIED','NATIVE_WORKER_RESOURCE_API_UNQUALIFIED','NOT_ATTEMPTED'))
        self.assertIs(result.effect_permitted,False)
        self.assertEqual(result.original_intent_sha256,hashlib.sha256(self.original).hexdigest())
        self.assertEqual(len(self.broker._contexts),1)
        context=next(iter(self.broker._contexts))
        with self.assertRaises(ResearchIdentityDenied):
            await ResearchIdentityBroker.capture_current(self.broker,context,scope='READ_RESEARCH',request_bytes=self.original)
        self.assertEqual(len(self.session_responses),1)
        sid=__import__('json').loads(self.session_responses[0]['raw'])['ID']
        self.assertEqual(await self.authority._request('GET','/v1/session/info/'+sid),[])
        self.assertIsNone(await self.authority._request('GET','/v1/kv/'+self.prefix+'jobs/'+self.job,params={'consistent':''},missing_ok=True))
