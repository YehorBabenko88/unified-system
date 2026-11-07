"""Real TLS principal -> actual scoped immutable manifest bytes, no job grant."""
import hashlib
import json
from pathlib import Path
import socket
import ssl
import sys
import tempfile
import unittest
from datetime import datetime,timedelta,timezone

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import test_gateway_identity as identity_fixture
from unified_system.gateway_runtime_composition import commission_disposable_manifest_front
from unified_system.storage.object_store import ObjectStore
from unified_system.journal import Journal


U='11111111-1111-4111-8111-111111111111'
FIXTURE=Path(__file__).resolve().parents[2]/'release/evidence/gateway-runtime-synthetic-profile-review1'


class ManifestFrontTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='gateway-front-read-');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.tls=identity_fixture.TLSFixture();self.addCleanup(self.tls.close)
        self.store=ObjectStore.create(self.root/'objects',store_id=U)
        self.manifest=(FIXTURE/'manifest.canonical.json').read_bytes();self.sha=hashlib.sha256(self.manifest).hexdigest()
        self.store.put(self.manifest)
        self.request=dict(schema='unified.storage.gateway-manifest-request.v1-review2',request_id=U,
            dataset_id='00000000-0000-4000-8000-000000000002',dataset_revision='7',manifest_revision='1',
            manifest_sha256=self.sha,manifest_schema_sha256='a599b399cb8809ad72a2ecdb778a4e7e419f88a6cadcf2da20489cf93d12fd10',consumer_id=U,view_id=U)
        self.binding=dict(schema='unified.gateway.read-binding.v1-review2',dataset_id=self.request['dataset_id'],
            dataset_revision='7',manifest_sha256=self.sha,schema_sha256=self.request['manifest_schema_sha256'],consumer_id=U,view_id=U)
        self.profile=dict(schema='unified.gateway.disposable-identity.v1-review1',realm_id=U,
            server_certificate_der=self.tls.server_der,clients=[dict(certificate_sha256=hashlib.sha256(self.tls.client_der).hexdigest(),
            service_id=U,delegated_user_id=U,quota_owner_id='test-quota',uri=identity_fixture.URI,
            expires_utc=(datetime.now(timezone.utc)+timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            grants=[dict(tool_name='unified.get_dataset_manifest',binding=self.binding,owned_store=self.store)])])
        self.audit=Journal(self.root/'audit.db');self.audit.initialize()
        self.client_context=ssl.create_default_context(cafile=str(Path(self.tls.temp.name)/'ca.pem'))
        self.client_context.load_cert_chain(str(Path(self.tls.temp.name)/'client.pem'),str(Path(self.tls.temp.name)/'client.key'))

    def start(self):
        front=commission_disposable_manifest_front(server_ssl_context=self.tls.server_context,
            profile=self.profile,pinned_owned_store=self.store,audit_journal=self.audit,
            commissioning_client_context=self.client_context)
        self.addCleanup(front.close);return front

    def request_front(self,front,value):
        body=json.dumps(value,sort_keys=True,separators=(',',':')).encode()
        with self.client_context.wrap_socket(socket.create_connection(front.address,timeout=3),server_hostname='127.0.0.1') as s:
            self.assertEqual(s.getpeercert(binary_form=True),self.tls.server_der)
            s.sendall((f'POST /intelligence/v1/manifest HTTP/1.1\r\nHost: 127.0.0.1:{front.address[1]}\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n').encode()+body)
            chunks=[]
            while part:=s.recv(8192):chunks.append(part)
        header,raw=b''.join(chunks).split(b'\r\n\r\n',1)
        return header,json.loads(raw)

    def test_actual_mtls_scoped_manifest_and_durable_audit(self):
        front=self.start();headers,result=self.request_front(front,self.request)
        self.assertTrue(headers.startswith(b'HTTP/1.1 200'))
        self.assertEqual(result['status'],'SYNTHETIC_MANIFEST_DISCLOSED')
        self.assertIn(self.sha,json.dumps(result))
        self.assertGreater(len(self.audit.read()),0)
        self.assertNotIn('BEGIN PRIVATE KEY',json.dumps(self.audit.read()))

    def test_actual_principal_wrong_view_denied_without_object_read(self):
        front=self.start();called=[];original=self.store.read
        self.store.read=lambda *args,**kwargs:(called.append(1),original(*args,**kwargs))[1]
        value=dict(self.request,view_id='22222222-2222-4222-8222-222222222222')
        headers,result=self.request_front(front,value)
        self.assertTrue(headers.startswith(b'HTTP/1.1 403'));self.assertEqual(called,[])
        self.assertNotIn(self.sha,json.dumps(result))

    def test_invalid_server_leaf_profile_refused_at_commission(self):
        other=identity_fixture.TLSFixture();self.addCleanup(other.close)
        self.profile['server_certificate_der']=other.server_der
        # Use only a valid alternate public certificate; its temporary own fixture
        # is explicitly closed, and no caller-controlled cert/URL can activate IO.
        with self.assertRaisesRegex(RuntimeError,'COMMISSIONING_PROFILE_UNAVAILABLE'):
            self.start()


if __name__=='__main__':unittest.main()
