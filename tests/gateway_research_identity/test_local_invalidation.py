"""Actual principal sessions; local-only cleanup never grants native retirement."""
import threading,unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch,PropertyMock
import httpx
import test_native_profile_v2 as profile_fixture
from grid.coordination import ConsulSessionAuthority
from unified_system.gateway_research_identity import ResearchIdentityBroker,ResearchIdentityDenied,ResearchIdentityUnavailable,ResearchPrincipalContext

class Trap(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.requests+=1;self.send_response(403);self.send_header('Content-Length','0');self.end_headers()
    do_PUT=do_GET
    def log_message(self,*args):pass

class LocalInvalidationTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):profile_fixture.NativeProfileV2Tests.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls):profile_fixture.NativeProfileV2Tests.tearDownClass.__func__(cls)
    put=profile_fixture.NativeProfileV2Tests.put
    commission=profile_fixture.NativeProfileV2Tests.commission
    rebind_target=profile_fixture.NativeProfileV2Tests.rebind_target
    submit=profile_fixture.NativeProfileV2Tests.submit
    async def asyncSetUp(self):await profile_fixture.NativeProfileV2Tests.asyncSetUp(self)
    async def source(self):
        context=await self.broker.open_session(self.tls.accepted,leader=self.leader)
        raw=profile_fixture.canonical(self.submit())
        capture=await self.broker.capture_current(context,scope='READ_RESEARCH',request_bytes=raw)
        snapshot=ResearchIdentityBroker.require_capture(self.broker,capture,expected_authority=self.authority,scope='READ_RESEARCH',request_bytes=raw)
        return context,raw,capture,snapshot
    async def test_actual_local_only_never_touches_lost_transport_peer_clock_or_config(self):
        context,raw,capture,snapshot=await self.source()
        safe=ConsulSessionAuthority(self.authority.config);self.addAsyncCleanup(safe.close)
        server=ThreadingHTTPServer(('127.0.0.1',0),Trap);server.daemon_threads=True;server.requests=0
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        unknown=httpx.AsyncClient(proxy='http://127.0.0.1:'+str(server.server_port),trust_env=False,follow_redirects=False)
        original_client=self.authority.client;self.authority.client=unknown
        try:
            with patch.object(self.authority,'_request',side_effect=AssertionError('NO_NATIVE_RPC')), \
                 patch.object(type(self.authority),'config',new_callable=PropertyMock,create=True,side_effect=AssertionError('NO_CONFIG_ACCESS')), \
                 patch.object(self.broker,'_clock',side_effect=AssertionError('NO_CLOCK_ACCESS')), \
                 patch.object(self.broker,'_peer',side_effect=AssertionError('NO_PEER_ACCESS')):
                self.assertIsNone(ResearchIdentityBroker.invalidate_context_local_only(self.broker,context))
                self.assertIsNone(ResearchIdentityBroker.invalidate_context_local_only(self.broker,context))
            self.assertEqual(server.requests,0)
        finally:
            self.authority.client=original_client
            await unknown.aclose();server.shutdown();server.server_close();thread.join(2);self.assertFalse(thread.is_alive())
        with self.assertRaises(ResearchIdentityDenied):
            ResearchIdentityBroker.require_capture(self.broker,capture,expected_authority=self.authority,scope='READ_RESEARCH',request_bytes=raw)
        with self.assertRaises(ResearchIdentityDenied):await self.broker.capture_current(context,scope='READ_RESEARCH',request_bytes=raw)
        # Separately admitted safe fixture client observes actual server state;
        # local latch did NOT retire/destroy the native principal session.
        actual=await safe._request('GET','/v1/session/info/'+snapshot.session_id)
        self.assertEqual(actual[0]['ID'],snapshot.session_id)
        self.assertIn(snapshot.session_id,self.broker._sessions)
    async def test_foreign_inventory_refused_and_actual_audit_failure_keeps_latch(self):
        first,raw,first_capture,_=await self.source()
        second,_,second_capture,second_snapshot=await self.source()
        before=set(self.broker._invalid)
        foreign=object.__new__(ResearchPrincipalContext)  # UNISSUED lookalike, not proof.
        with self.assertRaises(ResearchIdentityDenied):ResearchIdentityBroker.invalidate_context_local_only(self.broker,foreign)
        self.assertEqual(set(self.broker._invalid),before)
        while len(self.audit._events)<self.audit._max:self.audit._append(dict(schema='untrusted.audit-capacity-test-data.v1'))
        with self.assertRaises(ResearchIdentityUnavailable):ResearchIdentityBroker.invalidate_context_local_only(self.broker,second)
        self.assertIn(second_snapshot.session_id,self.broker._invalid)
        self.assertIn(second_snapshot.session_id,self.broker._sessions)
        self.assertIsNone(ResearchIdentityBroker.invalidate_context_local_only(self.broker,second))
        with self.assertRaises(ResearchIdentityDenied):
            ResearchIdentityBroker.require_capture(self.broker,second_capture,expected_authority=self.authority,scope='READ_RESEARCH',request_bytes=raw)
        ResearchIdentityBroker.require_capture(self.broker,first_capture,expected_authority=self.authority,scope='READ_RESEARCH',request_bytes=raw)
    async def test_actual_inflight_capture_rechecks_latch_after_unmodified_native_read(self):
        context,raw,_,snapshot=await self.source();observed=[]
        target='/v1/kv/'+self.prefix+'principal-sessions/'+snapshot.session_id+'/lock'
        async def latch_after_actual_read(response):
            if response.request.method=='GET' and response.request.url.path==target and not observed:
                await response.aread()  # Observe the REAL unmodified response, no fake proof.
                ResearchIdentityBroker.invalidate_context_local_only(self.broker,context);observed.append('LATCHED')
        self.authority.client.event_hooks['response'].append(latch_after_actual_read)
        try:
            with self.assertRaises(ResearchIdentityDenied):await self.broker.capture_current(context,scope='READ_RESEARCH',request_bytes=raw)
        finally:self.authority.client.event_hooks['response'].remove(latch_after_actual_read)
        self.assertEqual(observed,['LATCHED'])
        actual=await self.authority._request('GET','/v1/session/info/'+snapshot.session_id)
        self.assertEqual(actual[0]['ID'],snapshot.session_id)

if __name__=='__main__':unittest.main()
