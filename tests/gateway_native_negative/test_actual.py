"""Actual loopback mTLS/Consul composition; never an admitted research job."""
import hashlib
import asyncio
import json
from datetime import datetime,timedelta,timezone
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
        self.original_bytes=fixture.canonical(self.submit())

    async def test_closed_owned_client_rejected_before_constructor_auth(self):
        from unified_system.gateway_native_negative import DisposableNativeNegativeGateway,NativeNegativeDenied
        from grid.coordination import ConsulSessionAuthority
        extra=ConsulSessionAuthority(self.authority.config)
        broker=ResearchIdentityBroker(authority=extra,generation=self.generation,realm_id=self.realm,
            profile_sha256=self.profile_sha,server_ssl_context=self.tls.server_context,
            server_certificate_der=self.tls.server_der,audit_sink=self.audit)
        try:
            await extra.close()
            with self.assertRaises(NativeNegativeDenied):
                DisposableNativeNegativeGateway(extra,self.generation,broker=broker)
            self.assertEqual(self.session_responses,[])
        finally:
            await broker.close();await extra.close()

    async def test_replaced_client_rejected_before_call_auth(self):
        import httpx
        from unified_system.gateway_native_negative import DisposableNativeNegativeGateway,NativeNegativeDenied
        gateway=DisposableNativeNegativeGateway(self.authority,self.generation,broker=self.broker)
        original=self.authority.client
        replacement=httpx.AsyncClient(trust_env=False,follow_redirects=False)
        try:
            self.authority.client=replacement
            with self.assertRaises(NativeNegativeDenied):
                await gateway.submit(self.original_bytes,accepted_tls=self.tls.accepted,leader=self.leader)
            self.assertEqual(self.session_responses,[])
        finally:
            self.authority.client=original;await replacement.aclose()

    async def test_closed_captured_client_rejected_before_call_auth(self):
        from unified_system.gateway_native_negative import DisposableNativeNegativeGateway,NativeNegativeDenied
        gateway=DisposableNativeNegativeGateway(self.authority,self.generation,broker=self.broker)
        await self.authority.client.aclose()
        with self.assertRaises(NativeNegativeDenied):
            await gateway.submit(self.original_bytes,accepted_tls=self.tls.accepted,leader=self.leader)
        self.assertEqual(self.session_responses,[])

    async def test_actual_mtls_submit_denied_and_own_context_invalidated(self):
        from unified_system.gateway_native_negative import DisposableNativeNegativeGateway
        gateway=DisposableNativeNegativeGateway(self.authority,self.generation,broker=self.broker)
        result=await gateway.submit(self.original_bytes,accepted_tls=self.tls.accepted,leader=self.leader)
        self.assertIs(type(result),ResearchAdmissionResult)
        self.assertEqual((result.outcome,result.reason,result.commit_status),
            ('DENIED','NATIVE_WORKER_RESOURCE_API_UNQUALIFIED','NOT_ATTEMPTED'))
        self.assertIs(result.effect_permitted,False)
        self.assertEqual(result.original_intent_sha256,hashlib.sha256(self.original_bytes).hexdigest())
        self.assertEqual(len(self.broker._contexts),1)
        context=next(iter(self.broker._contexts))
        with self.assertRaises(ResearchIdentityDenied):
            await ResearchIdentityBroker.capture_current(self.broker,context,scope='READ_RESEARCH',request_bytes=self.original_bytes)
        self.assertEqual(len(self.session_responses),1)
        sid=__import__('json').loads(self.session_responses[0]['raw'])['ID']
        self.assertEqual(await self.authority._request('GET','/v1/session/info/'+sid),[])
        self.assertIsNone(await self.authority._request('GET','/v1/kv/'+self.prefix+'jobs/'+self.job,params={'consistent':''},missing_ok=True))

    async def test_actual_same_original_twice_stays_denied_without_job(self):
        from unified_system.gateway_native_negative import DisposableNativeNegativeGateway
        gateway=DisposableNativeNegativeGateway(self.authority,self.generation,broker=self.broker)
        first=await gateway.submit(self.original_bytes,accepted_tls=self.tls.accepted,leader=self.leader)
        second=await gateway.submit(self.original_bytes,accepted_tls=self.tls.accepted,leader=self.leader)
        self.assertEqual(first,second)
        ids=[json.loads(row['raw'])['ID'] for row in self.session_responses]
        self.assertEqual(len(ids),len(set(ids)));self.assertEqual(len(ids),2)
        for sid in ids:self.assertEqual(await self.authority._request('GET','/v1/session/info/'+sid),[])
        self.assertIsNone(await self.authority._request('GET','/v1/kv/'+self.prefix+'jobs/'+self.job,params={'consistent':''},missing_ok=True))

    async def test_actual_lookup_absence_remains_unknown(self):
        from unified_system.gateway_native_negative import DisposableNativeNegativeGateway
        gateway=DisposableNativeNegativeGateway(self.authority,self.generation,broker=self.broker)
        value=await gateway.lookup(self.original_bytes,accepted_tls=self.tls.accepted,leader=self.leader)
        self.assertEqual((value.outcome,value.reason),('UNKNOWN','JOB_RECONCILIATION_API_UNQUALIFIED'))
        self.assertEqual(value.commit_status,'NOT_ATTEMPTED');self.assertIs(value.effect_permitted,False)

    async def test_input_and_fake_socket_reject_before_authentication(self):
        from unified_system.gateway_native_negative import DisposableNativeNegativeGateway,NativeNegativeDenied
        gateway=DisposableNativeNegativeGateway(self.authority,self.generation,broker=self.broker)
        class FalseSocket:
            def __getattr__(self,name):raise AssertionError('fake socket accessed')
        for raw,sock in [(b'',self.tls.accepted),(b'x'*16385,self.tls.accepted),({},self.tls.accepted),(self.original_bytes,FalseSocket())]:
            with self.subTest(kind=type(raw).__name__,socket=type(sock).__name__),self.assertRaises(NativeNegativeDenied):
                await gateway.submit(raw,accepted_tls=sock,leader=self.leader)
        class OperationClaim:
            def __eq__(self,other):raise AssertionError('operation equality claim executed')
        with self.assertRaises(NativeNegativeDenied):
            await gateway._call(self.original_bytes,accepted_tls=self.tls.accepted,leader=self.leader,operation=OperationClaim())
        self.assertEqual(self.session_responses,[])

    async def test_actual_revoked_and_expired_policy_are_errors_not_gate_data(self):
        from unified_system.gateway_native_negative import DisposableNativeNegativeGateway
        gateway=DisposableNativeNegativeGateway(self.authority,self.generation,broker=self.broker)
        await self.put(self.prefix+'policies/'+self.policy,dict(self.policy_body,state='REVOKED',revision='2'))
        with self.assertRaises(ResearchIdentityDenied):await gateway.submit(self.original_bytes,accepted_tls=self.tls.accepted,leader=self.leader)
        past=(datetime.now(timezone.utc)-timedelta(seconds=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
        await self.put(self.prefix+'policies/'+self.policy,dict(self.policy_body,expires_utc=past,revision='3'))
        with self.assertRaises(ResearchIdentityDenied):await gateway.lookup(self.original_bytes,accepted_tls=self.tls.accepted,leader=self.leader)
        self.assertEqual(self.session_responses,[])

    async def test_actual_destroyed_leader_is_not_resource_denial(self):
        from unified_system.gateway_native_negative import DisposableNativeNegativeGateway
        gateway=DisposableNativeNegativeGateway(self.authority,self.generation,broker=self.broker)
        await self.authority._request('PUT','/v1/session/destroy/'+self.leader.session_id)
        with self.assertRaises(ResearchIdentityDenied):await gateway.submit(self.original_bytes,accepted_tls=self.tls.accepted,leader=self.leader)
        self.assertEqual(self.session_responses,[])

    async def test_actual_inflight_call_rejects_second_instead_of_queueing(self):
        from unified_system.gateway_native_negative import DisposableNativeNegativeGateway,NativeNegativeDenied
        gateway=DisposableNativeNegativeGateway(self.authority,self.generation,broker=self.broker)
        reached=asyncio.Event();release=asyncio.Event()
        async def hold_real_response(response):
            if response.request.url.path=='/v1/session/create':
                await response.aread();reached.set();await release.wait()
        self.authority.client.event_hooks['response'].append(hold_real_response)
        task=asyncio.create_task(gateway.submit(self.original_bytes,accepted_tls=self.tls.accepted,leader=self.leader))
        try:
            await asyncio.wait_for(reached.wait(),4)
            with self.assertRaises(NativeNegativeDenied):await gateway.lookup(self.original_bytes,accepted_tls=self.tls.accepted,leader=self.leader)
        finally:release.set()
        result=await asyncio.wait_for(task,10)
        self.assertEqual(result.outcome,'DENIED');self.assertEqual(len(self.session_responses),1)


    async def test_actual_task_cancellation_locally_invalidates_without_result(self):
        from unified_system.gateway_native_negative import DisposableNativeNegativeGateway
        gateway=DisposableNativeNegativeGateway(self.authority,self.generation,broker=self.broker)
        reached=asyncio.Event();release=asyncio.Event()
        async def hold_native_read(response):
            if response.request.url.path=='/v1/txn':
                request=json.loads(response.request.content)
                if type(request) is list and len(request)==7 and all(item.get('KV',{}).get('Verb')=='get-or-empty' for item in request):
                    await response.aread();reached.set();await release.wait()
        self.authority.client.event_hooks['response'].append(hold_native_read)
        task=asyncio.create_task(gateway.submit(self.original_bytes,accepted_tls=self.tls.accepted,leader=self.leader))
        try:
            await asyncio.wait_for(reached.wait(),5)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):await task
        finally:
            release.set()
            if not task.done():task.cancel()
        self.assertFalse(gateway._busy)
        self.assertEqual(len(self.broker._contexts),1)
        context=next(iter(self.broker._contexts))
        with self.assertRaises(ResearchIdentityDenied):
            await ResearchIdentityBroker.capture_current(self.broker,context,scope='READ_RESEARCH',request_bytes=self.original_bytes)
        sid=json.loads(self.session_responses[0]['raw'])['ID']
        self.assertEqual(await self.authority._request('GET','/v1/session/info/'+sid),[])
        self.assertIsNone(await self.authority._request('GET','/v1/kv/'+self.prefix+'jobs/'+self.job,params={'consistent':''},missing_ok=True))

    async def test_closed_actual_tls_socket_cannot_authenticate(self):
        from unified_system.gateway_native_negative import DisposableNativeNegativeGateway,NativeNegativeDenied
        gateway=DisposableNativeNegativeGateway(self.authority,self.generation,broker=self.broker)
        self.tls.accepted.close()
        with self.assertRaises(NativeNegativeDenied):await gateway.submit(self.original_bytes,accepted_tls=self.tls.accepted,leader=self.leader)
        self.assertEqual(self.session_responses,[])

    async def test_rebound_authority_config_rejected_before_authentication(self):
        from dataclasses import replace
        from unified_system.gateway_native_negative import DisposableNativeNegativeGateway,NativeNegativeDenied
        gateway=DisposableNativeNegativeGateway(self.authority,self.generation,broker=self.broker)
        original=self.authority.config
        try:
            self.authority.config=replace(original,request_timeout=4)
            with self.assertRaises(NativeNegativeDenied):
                await gateway.submit(self.original_bytes,accepted_tls=self.tls.accepted,leader=self.leader)
            self.assertEqual(self.session_responses,[])
        finally:self.authority.config=original

    async def test_z_actual_quorum_loss_cleanup_preserves_original_error(self):
        from unified_system.gateway_native_negative import DisposableNativeNegativeGateway
        from unified_system.gateway_research_identity import ResearchIdentityUnavailable
        gateway=DisposableNativeNegativeGateway(self.authority,self.generation,broker=self.broker)
        injected=[]
        async def cut_only_own_quorum(request):
            if not injected and request.url.path.startswith('/v1/session/destroy/'):
                injected.append(True)
                for process in self.lab.processes[1:]:process.kill();process.wait(timeout=10)
        self.authority.client.event_hooks['request'].append(cut_only_own_quorum)
        with self.assertRaises(ValueError) as caught:
            await gateway.submit(b'{}',accepted_tls=self.tls.accepted,leader=self.leader)
        self.assertTrue(injected)
        self.assertIn('NATIVE_NEGATIVE_CONTEXT_INVALIDATION_UNKNOWN',getattr(caught.exception,'__notes__',[]))
        self.assertEqual(len(self.broker._contexts),1)
        context=next(iter(self.broker._contexts))
        with self.assertRaises(ResearchIdentityDenied):
            await ResearchIdentityBroker.capture_current(self.broker,context,scope='READ_RESEARCH',request_bytes=self.original_bytes)
        with self.assertRaises(ResearchIdentityUnavailable):
            await gateway.submit(self.original_bytes,accepted_tls=self.tls.accepted,leader=self.leader)
