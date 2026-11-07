"""Real own-loopback TLS transport; no authenticated resource disclosure yet."""
import json
import socket
import ssl
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import test_lan_transport as certificates
from unified_system.gateway_runtime_composition import DisposableGatewayFront


class FrontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pki=certificates.TLSIsolationTests
        cls.pki.setUpClass();cls.addClassCleanup(cls.pki.tearDownClass)

    def setUp(self):
        c=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        c.minimum_version=ssl.TLSVersion.TLSv1_2;c.verify_mode=ssl.CERT_REQUIRED
        c.load_verify_locations(str(self.pki.root/'ca.pem'))
        c.load_cert_chain(str(self.pki.root/'LS5.pem'),str(self.pki.root/'LS5.key'))
        self.front=DisposableGatewayFront(server_ssl_context=c)
        self.front.start();self.addCleanup(self.front.close)

    def connection(self,*,cert=True):
        c=ssl.create_default_context(cafile=str(self.pki.root/'ca.pem'));c.check_hostname=False
        if cert:c.load_cert_chain(str(self.pki.root/'PC1.pem'),str(self.pki.root/'PC1.key'))
        raw=socket.create_connection(self.front.address,timeout=3)
        return c.wrap_socket(raw,server_hostname='localhost')

    def request(self,path='/intelligence/v1/capabilities',*,method='GET',extra=b''):
        with self.connection() as s:
            s.sendall(method.encode()+b' '+path.encode()+b' HTTP/1.1\r\nHost: '+
                      ('127.0.0.1:'+str(self.front.address[1])).encode()+b'\r\n'+extra+b'\r\n')
            chunks=[]
            while part:=s.recv(8192):chunks.append(part)
        return b''.join(chunks)

    def test_actual_tls_catalog_not_identity_or_registered_tools(self):
        raw=self.request();headers,body=raw.split(b'\r\n\r\n',1)
        self.assertTrue(headers.startswith(b'HTTP/1.1 200'))
        v=json.loads(body);self.assertEqual(len(v['tools']),34)
        self.assertFalse(v['runtime_available']);self.assertFalse(v['authentication_available'])
        self.assertIn(b'Connection: close',headers)

    def test_tls_peer_without_certificate_cannot_read_catalog(self):
        with self.assertRaises((ssl.SSLError,ConnectionError,OSError)):
            with self.connection(cert=False) as s:
                s.sendall(b'GET /intelligence/v1/capabilities HTTP/1.1\r\n\r\n')
                data=s.recv(1024)
                if not data:raise ConnectionError('TLS denied')
                self.fail('Uncertified peer received response')

    def test_protected_route_ignores_forged_role_and_does_not_read_body(self):
        raw=self.request('/intelligence/v1/query',method='POST',extra=b'Authorization: ADMIN\r\nContent-Length: 10000\r\n')
        self.assertTrue(raw.startswith(b'HTTP/1.1 503'))
        self.assertEqual(json.loads(raw.split(b'\r\n\r\n',1)[1])['code'],'CLIENT_ADMISSION_UNAVAILABLE')
        self.assertNotIn(b'ADMIN',raw)

    def test_duplicate_headers_transfer_encoding_and_wrong_host_refused(self):
        for extra in (b'X-Role: a\r\nX-Role: b\r\n',b'Transfer-Encoding: chunked\r\n',b'Host: attacker\r\n'):
            with self.subTest(extra=extra):self.assertTrue(self.request(extra=extra).startswith(b'HTTP/1.1 400'))

    def test_invalid_path_query_and_unbounded_headers_refused(self):
        for path in ('/intelligence/v1/capabilities?admin=true','/../capabilities','/%2e/capabilities'):
            self.assertTrue(self.request(path).startswith(b'HTTP/1.1 400'))
        self.assertTrue(self.request(extra=b'X-Padding: '+b'x'*8200+b'\r\n').startswith(b'HTTP/1.1 400'))

    def test_head_no_body_unknown_path_and_body_on_catalog(self):
        self.assertEqual(self.request(method='HEAD').split(b'\r\n\r\n',1)[1],b'')
        self.assertTrue(self.request('/intelligence/v1/not-real').startswith(b'HTTP/1.1 404'))
        self.assertTrue(self.request(extra=b'Content-Length: 1\r\n').startswith(b'HTTP/1.1 400'))

    def test_head_errors_never_emit_response_body(self):
        for path,extra in (('/intelligence/v1/capabilities',b'Host: attacker\r\n'),
                           ('/intelligence/v1/capabilities?bad=true',b'')):
            response=self.request(path,method='HEAD',extra=extra)
            self.assertTrue(response.startswith(b'HTTP/1.1 400'))
            self.assertEqual(response.split(b'\r\n\r\n',1)[1],b'')

    def test_owned_shutdown_has_no_remaining_workers_or_restart(self):
        self.request();self.front.close();self.front.close()
        self.assertFalse(self.front.is_alive())
        with self.assertRaises(RuntimeError):self.front.start()

    def test_unverified_context_rejected_before_bind(self):
        c=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        with self.assertRaises(ValueError):DisposableGatewayFront(server_ssl_context=c)


if __name__=='__main__':unittest.main()
