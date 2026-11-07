"""Actual HTTPS -> fixed Grid reader -> ObjectStore under real A2 mTLS caps."""
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_manifest_front as fixtures
from unified_system.gateway_runtime_composition import commission_disposable_query_front


class QueryFrontTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.ManifestFrontTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.request=json.loads((fixtures.FIXTURE/'actual-query.request.canonical.json').read_bytes())
        self.source=os.environ.get('GRID_GATEWAY_SOURCE_ROOT',
            'C:/Users/LS-5/Documents/Codex/2026-11-06/codex-agent-3-bybit-historical-live/work/grid-gateway-query')
        for name in ('data-schema','segment-index','rows','coverage','dependencies'):
            self.fixture.store.put((fixtures.FIXTURE/(name+'.canonical.json')).read_bytes())
        q=self.request
        self.binding=dict(schema='unified.gateway.read-binding.v1-review2',dataset_id=q['dataset_id'],
            dataset_revision=q['dataset_revision'],manifest_sha256=q['knowledge_cut']['manifest_sha256'],
            schema_sha256=q['data_schema_sha256'],consumer_id=q['consumer_context']['consumer_id'],view_id=q['consumer_context']['view_id'])
        self.fixture.profile['clients'][0]['grants']=[dict(tool_name='unified.query_market_data',binding=self.binding,owned_store=self.fixture.store)]

    def start(self):
        f=self.fixture
        front=commission_disposable_query_front(server_ssl_context=f.tls.server_context,
            profile=f.profile,pinned_owned_store=f.store,audit_journal=f.audit,
            commissioning_client_context=f.client_context,query_source_root=self.source)
        self.addCleanup(front.close);return front

    def get(self,front,request):
        raw=json.dumps(request,sort_keys=True,separators=(',',':')).encode()
        with self.fixture.client_context.wrap_socket(socket.create_connection(front.address,timeout=3),server_hostname='127.0.0.1') as s:
            self.assertEqual(s.getpeercert(binary_form=True),self.fixture.tls.server_der)
            s.sendall((f'POST /intelligence/v1/query HTTP/1.1\r\nHost: 127.0.0.1:{front.address[1]}\r\nContent-Type: application/json\r\nContent-Length: {len(raw)}\r\n\r\n').encode()+raw)
            output=bytearray()
            while part:=s.recv(8192):output.extend(part)
        h,b=bytes(output).split(b'\r\n\r\n',1);return h,json.loads(b)

    def test_real_authenticated_bounded_query_digest_gaps_and_audit(self):
        headers,response=self.get(self.start(),self.request)
        self.assertTrue(headers.startswith(b'HTTP/1.1 200'),response)
        result=response['owner_result'];self.assertEqual(result['status'],'SYNTHETIC_QUERY_RESULT')
        self.assertEqual(len(result['rows']),1);self.assertEqual(result['cells'][1]['disposition'],'GAP')
        self.assertEqual(result['provider_coverage'],'UNKNOWN');self.assertEqual(result['publication'],'UNPROVEN')
        raw=json.dumps(result,sort_keys=True,separators=(',',':')).encode()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),response['owner_result_sha256'])
        self.assertFalse(response['artifact_published'])
        events=[e for r in self.fixture.audit.read() for e in r['receipt']['events']]
        self.assertEqual(sum(e['decision']=='READ_CURRENT_CHECK' for e in events),7)

    def test_actual_principal_wrong_view_rejected_before_any_object_read(self):
        front=self.start();observed=[];read=self.fixture.store.read
        self.fixture.store.read=lambda *a,**kw:(observed.append(1),read(*a,**kw))[1]
        q=json.loads(json.dumps(self.request));q['consumer_context']['view_id']=fixtures.U
        headers,response=self.get(front,q)
        self.assertTrue(headers.startswith(b'HTTP/1.1 403'),response);self.assertEqual(observed,[])
        self.assertNotIn('rows',response)

    def test_chain_valid_but_unregistered_client_fingerprint_is_unauthenticated(self):
        self.fixture.profile['clients'][0]['certificate_sha256']='f'*64
        front=self.start();observed=[];read=self.fixture.store.read
        self.fixture.store.read=lambda *a,**kw:(observed.append(1),read(*a,**kw))[1]
        headers,response=self.get(front,self.request)
        self.assertTrue(headers.startswith(b'HTTP/1.1 401'),response)
        self.assertEqual(observed,[]);self.assertNotIn('rows',response)

    def test_corrupt_owned_audit_blocks_disclosure_without_repair_or_object_read(self):
        front=self.start();observed=[];read=self.fixture.store.read
        self.fixture.store.read=lambda *a,**kw:(observed.append(1),read(*a,**kw))[1]
        corrupt=b'OWN_DISPOSABLE_AUDIT_CORRUPTION'
        self.fixture.audit.path.write_bytes(corrupt)
        headers,response=self.get(front,self.request)
        self.assertTrue(headers.startswith(b'HTTP/1.1 503'),response)
        self.assertEqual(observed,[])
        self.assertEqual(self.fixture.audit.path.read_bytes(),corrupt)

    def test_duplicate_read_and_explicit_front_restart_preserve_result_not_job_grants(self):
        front=self.start();h,first=self.get(front,self.request);self.assertTrue(h.startswith(b'HTTP/1.1 200'),first)
        h,second=self.get(front,self.request);self.assertEqual(first,second)
        front.close();h,third=self.get(self.start(),self.request)
        self.assertTrue(h.startswith(b'HTTP/1.1 200'),third);self.assertEqual(first,third)
        self.assertGreater(len(self.fixture.audit.read()),5)


if __name__=='__main__':unittest.main()
