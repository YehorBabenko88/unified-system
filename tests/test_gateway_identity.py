"""Owned real loopback PKI/TLS tests; synthetic service identities only."""
import copy
import hashlib
import importlib
import ipaddress
import json
import queue
import socket
import ssl
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

U = '11111111-1111-4111-8111-111111111111'
URI = 'urn:unified:test:service:' + U

class TLSFixture:
    def __init__(self, *, client_uri=URI, client_eku=ExtendedKeyUsageOID.CLIENT_AUTH,
                 trusted=True, present=True):
        self.temp = tempfile.TemporaryDirectory(prefix='a2-gateway-pki-')
        self.sockets = []
        self.thread = None
        try:
            now = datetime.now(timezone.utc)
            def cert(name, issuer, issuer_key, *, ca=False, server=False, uri=URI, eku=None):
                key = ec.generate_private_key(ec.SECP256R1())
                subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
                builder = (x509.CertificateBuilder().subject_name(subject)
                    .issuer_name(issuer.subject if issuer else subject).public_key(key.public_key())
                    .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(seconds=10))
                    .not_valid_after(now+timedelta(minutes=10))
                    .add_extension(x509.BasicConstraints(ca=ca, path_length=0 if ca else None), critical=True))
                if not ca:
                    san = x509.IPAddress(ipaddress.ip_address('127.0.0.1')) if server else x509.UniformResourceIdentifier(uri)
                    builder = builder.add_extension(x509.SubjectAlternativeName([san]), critical=False)
                    builder = builder.add_extension(x509.ExtendedKeyUsage([eku]), critical=False)
                return key, builder.sign(issuer_key or key, hashes.SHA256())
            ca_key, ca = cert('a2-disposable-ca', None, None, ca=True)
            server_key, server = cert('server', ca, ca_key, server=True, eku=ExtendedKeyUsageOID.SERVER_AUTH)
            other_key, other_ca = cert('a2-other-ca', None, None, ca=True)
            client_key, client = cert('client', ca if trusted else other_ca,
                                      ca_key if trusted else other_key, uri=client_uri, eku=client_eku)
            self.server_der = server.public_bytes(serialization.Encoding.DER)
            self.client_der = client.public_bytes(serialization.Encoding.DER)
            root = Path(self.temp.name)
            def write(name, value):
                path = root/name
                path.write_bytes(value)
                return str(path)
            ca_path = write('ca.pem', ca.public_bytes(serialization.Encoding.PEM))
            def material(name, key, certificate):
                return (write(name+'.pem', certificate.public_bytes(serialization.Encoding.PEM)),
                        write(name+'.key', key.private_bytes(serialization.Encoding.PEM,
                          serialization.PrivateFormat.PKCS8, serialization.NoEncryption())))
            self.server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self.server_context.minimum_version = ssl.TLSVersion.TLSv1_2
            self.server_context.verify_mode = ssl.CERT_REQUIRED
            self.server_context.load_verify_locations(cafile=ca_path)
            self.server_context.load_cert_chain(*material('server', server_key, server))
            client_context = ssl.create_default_context(cafile=ca_path)
            if present:
                client_context.load_cert_chain(*material('client', client_key, client))
            listener = socket.socket()
            self.sockets.append(listener)
            listener.settimeout(5)
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
            outcome = queue.Queue()
            def accept():
                raw = None
                try:
                    raw, _ = listener.accept()
                    self.sockets.append(raw)
                    raw.settimeout(5)
                    wrapped = self.server_context.wrap_socket(raw, server_side=True)
                    self.sockets.append(wrapped)
                    outcome.put(wrapped)
                except Exception as exc:
                    if raw: raw.close()
                    outcome.put(exc)
            self.thread = threading.Thread(target=accept)
            self.thread.start()
            raw = socket.create_connection(listener.getsockname(), timeout=5)
            self.sockets.append(raw)
            try:
                self.client = client_context.wrap_socket(raw, server_hostname='127.0.0.1')
                self.sockets.append(self.client)
                assert self.client.getpeercert(binary_form=True) == self.server_der  # actual loaded server cert pin
            except ssl.SSLError:
                self.client = None
            self.accepted = outcome.get(timeout=6)
            self.thread.join(6)
            assert not self.thread.is_alive()
        except BaseException:
            self.close()
            raise
    def close(self):
        for item in reversed(self.sockets): item.close()
        if self.thread: self.thread.join(6)
        self.temp.cleanup()

class GatewayIdentityTests(unittest.TestCase):
    def setUp(self):
        self.m = importlib.import_module('unified_system.gateway_identity')
        self.tls = TLSFixture()
        self.addCleanup(self.tls.close)
        self.store = object()
        self.binding = dict(schema='unified.gateway.read-binding.v1-review2', dataset_id=U,
                            dataset_revision='1', manifest_sha256='a'*64, schema_sha256='b'*64,
                            consumer_id=U, view_id=U)
        self.request = b'{"request_id":"synthetic-one"}'
        self.profile = dict(schema='unified.gateway.disposable-identity.v1-review1', realm_id=U,
            server_certificate_der=self.tls.server_der,
            clients=[dict(certificate_sha256=hashlib.sha256(self.tls.client_der).hexdigest(),
                service_id=U, delegated_user_id=U, quota_owner_id='test-quota', uri=URI,
                expires_utc=(datetime.now(timezone.utc)+timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%SZ'),
                grants=[dict(tool_name='unified.get_dataset_manifest', binding=self.binding, owned_store=self.store)])])
        self.audit = self.m.GatewayAuditSink(max_events=100)
        self.auth = self.m.DisposableIdentityAuthority(server_ssl_context=self.tls.server_context,
                                                       profile=self.profile, audit_sink=self.audit)
    def permit(self):
        context = self.auth.authenticate_connection(self.tls.accepted)
        cap = self.auth.authorize_read(context, tool_name='unified.get_dataset_manifest',
                    request_bytes=self.request, binding=self.binding, owned_store=self.store)
        return context, cap
    def check(self, cap, **changes):
        args = dict(tool_name='unified.get_dataset_manifest', request_bytes=self.request,
                    binding=self.binding, owned_store=self.store)
        args.update(changes)
        return cap.check_current(**args)
    def test_actual_tls_read_capability_two_checks_then_replay_denied(self):
        _, cap = self.permit()
        self.assertIsNone(self.check(cap))
        self.assertIsNone(self.check(cap))
        with self.assertRaises(self.m.GatewayIdentityDenied): self.check(cap)
        self.assertGreaterEqual(len(self.audit.drain()), 4)
    def test_claims_and_public_constructor_cannot_authenticate(self):
        for value in (True, {}, None, self.tls.client_der, self.tls.client):
            with self.subTest(value=type(value)):
                with self.assertRaises(self.m.GatewayIdentityDenied): self.auth.authenticate_connection(value)
        with self.assertRaises(TypeError): self.m.GatewayReadCapability()
    def test_wrong_request_tool_store_and_view_deny(self):
        _, cap = self.permit()
        for changes in (dict(request_bytes=b'other'), dict(tool_name='unified.query_market_data'),
                        dict(owned_store=object()), dict(binding=dict(self.binding, view_id='22222222-2222-4222-8222-222222222222'))):
            with self.subTest(changes=tuple(changes)):
                with self.assertRaises(self.m.GatewayIdentityDenied): self.check(cap, **changes)
    def test_revocation_and_closed_actual_connection(self):
        _, cap = self.permit()
        self.auth.revoke_service(U)
        with self.assertRaises(self.m.GatewayIdentityDenied): self.check(cap)
    def test_closed_socket_denies(self):
        _, cap = self.permit()
        self.tls.accepted.close()
        with self.assertRaises(self.m.GatewayIdentityDenied): self.check(cap)
    def test_copy_and_foreign_authority_reject(self):
        context, cap = self.permit()
        with self.assertRaises(TypeError): copy.copy(cap)
        other = self.m.DisposableIdentityAuthority(server_ssl_context=self.tls.server_context,
                                                   profile=self.profile, audit_sink=self.audit)
        with self.assertRaises(self.m.GatewayIdentityDenied):
            other.authorize_read(context, tool_name='unified.get_dataset_manifest', request_bytes=self.request,
                                 binding=self.binding, owned_store=self.store)
    def test_profile_is_copied_and_cannot_change_grant(self):
        _, cap = self.permit()
        self.profile['clients'][0]['grants'][0]['binding']['view_id'] = 'bad'
        self.assertIsNone(self.check(cap, binding=dict(self.binding, view_id=U)))
    def test_missing_audit_blocks(self):
        with self.assertRaises(self.m.GatewayIdentityUnavailable):
            self.m.DisposableIdentityAuthority(server_ssl_context=self.tls.server_context, profile=self.profile, audit_sink=None)
    def test_real_elapsed_registry_expiry_denies(self):
        profile = dict(self.profile, clients=[dict(self.profile['clients'][0],
            expires_utc=(datetime.now(timezone.utc)+timedelta(seconds=2)).strftime('%Y-%m-%dT%H:%M:%SZ'))])
        auth = self.m.DisposableIdentityAuthority(server_ssl_context=self.tls.server_context,
                                                 profile=profile, audit_sink=self.audit)
        context = auth.authenticate_connection(self.tls.accepted)
        cap = auth.authorize_read(context, tool_name='unified.get_dataset_manifest',request_bytes=self.request,
                                  binding=self.binding, owned_store=self.store)
        time.sleep(2.05)
        with self.assertRaises(self.m.GatewayIdentityDenied): self.check(cap)
    def test_clock_rollback_is_permanent_and_monotonic_deadline_independent(self):
        _, cap = self.permit()
        with patch.object(self.m, '_utc', return_value=self.auth._wall-1):
            with self.assertRaises(self.m.GatewayIdentityUnavailable): self.check(cap)
        with self.assertRaises(self.m.GatewayIdentityUnavailable): self.check(cap)
    def test_cumulative_slow_wall_clock_is_not_allowed_to_drift_forever(self):
        # Controlled clock logic, not an OS-clock/native-auth test.
        wall, mono = self.auth._wall, self.auth._mono
        refused = False
        for n in range(1, 8):
            with patch.object(self.m, '_utc', return_value=wall+n*.75), patch.object(self.m.time, 'monotonic', return_value=mono+n):
                try: self.auth._now()
                except self.m.GatewayIdentityUnavailable:
                    refused = True
                    break
        self.assertTrue(refused)
    def test_context_inventory_is_bounded(self):
        refused = False
        for _ in range(129):
            self.audit.drain()  # isolate context bound from the independent audit bound
            try: self.auth.authenticate_connection(self.tls.accepted)
            except self.m.GatewayIdentityUnavailable:
                refused = True
                break
        self.assertTrue(refused)
    def test_audit_full_cannot_issue_or_check(self):
        sink = self.m.GatewayAuditSink(max_events=1)
        auth = self.m.DisposableIdentityAuthority(server_ssl_context=self.tls.server_context,
                                                 profile=self.profile, audit_sink=sink)
        context = auth.authenticate_connection(self.tls.accepted)
        with self.assertRaises(self.m.GatewayIdentityUnavailable):
            auth.authorize_read(context, tool_name='unified.get_dataset_manifest',request_bytes=self.request,
                                binding=self.binding, owned_store=self.store)
        self.assertEqual(len(sink.drain()), 1)
    def test_revocation_latches_even_when_audit_full(self):
        _, cap = self.permit()
        self.audit._max = len(self.audit._events)
        with self.assertRaises(self.m.GatewayIdentityUnavailable): self.auth.revoke_service(U)
        self.audit.drain()
        with self.assertRaises(self.m.GatewayIdentityDenied): self.check(cap)
    def test_denial_and_revocation_target_are_audited(self):
        _, cap = self.permit()
        with self.assertRaises(self.m.GatewayIdentityDenied): self.check(cap, owned_store=object())
        self.auth.revoke_service(U)
        events = self.audit.drain()
        self.assertTrue(any(e['decision']=='READ_DENIED' for e in events))
        self.assertTrue(any(e['decision']=='SERVICE_REVOKED' and e['target_service_id']==U for e in events))
    def test_nonread_commissioning_grant_unavailable(self):
        profile = dict(self.profile, clients=[dict(self.profile['clients'][0], grants=[
            dict(tool_name='unified.submit_backtest', binding=self.binding, owned_store=self.store)])])
        with self.assertRaises(self.m.GatewayIdentityUnavailable):
            self.m.DisposableIdentityAuthority(server_ssl_context=self.tls.server_context, profile=profile, audit_sink=self.audit)
    def test_forged_exact_type_handle_not_in_issuer_inventory(self):
        fake = object.__new__(self.m.GatewayReadCapability)
        fake._issuer = self.auth
        with self.assertRaises(self.m.GatewayIdentityDenied): self.check(fake)
    def test_forged_capability_cannot_delegate_to_method_shaped_none_provider(self):
        class FakeIssuer:
            def _check(self, *args): return None
        fake = object.__new__(self.m.GatewayReadCapability)
        fake._issuer = FakeIssuer()
        with self.assertRaises(self.m.GatewayIdentityDenied): self.check(fake)
    def test_query_has_seven_current_checks_then_eighth_denied(self):
        profile = dict(self.profile, clients=[dict(self.profile['clients'][0], grants=[
            dict(tool_name='unified.query_market_data', binding=self.binding, owned_store=self.store)])])
        auth = self.m.DisposableIdentityAuthority(server_ssl_context=self.tls.server_context, profile=profile, audit_sink=self.audit)
        context = auth.authenticate_connection(self.tls.accepted)
        cap = auth.authorize_read(context, tool_name='unified.query_market_data', request_bytes=self.request,
                                  binding=self.binding, owned_store=self.store)
        for _ in range(7):
            self.assertIsNone(self.check(cap, tool_name='unified.query_market_data'))
        with self.assertRaises(self.m.GatewayIdentityDenied): self.check(cap, tool_name='unified.query_market_data')
    def test_context_exact_original_peer_pin_not_other_registered_entry(self):
        context, _ = self.permit()
        state = self.auth._contexts[context]
        # Controlled corrupted binding control, not an in-process attacker claim.
        corrupted = (dict(state[0], fingerprint='f'*64),) + state[1:]
        with self.assertRaises(self.m.GatewayIdentityDenied): self.auth._current(corrupted)
    def test_wrong_actual_san_denies(self):
        other = TLSFixture(client_uri='urn:wrong')
        self.addCleanup(other.close)
        profile = dict(self.profile, server_certificate_der=other.server_der)
        profile['clients'] = [dict(self.profile['clients'][0], certificate_sha256=hashlib.sha256(other.client_der).hexdigest())]
        auth = self.m.DisposableIdentityAuthority(server_ssl_context=other.server_context, profile=profile, audit_sink=self.audit)
        with self.assertRaises(self.m.GatewayIdentityDenied): auth.authenticate_connection(other.accepted)
    def test_untrusted_ca_and_missing_client_cert_real_handshake_refused(self):
        for kwargs in (dict(trusted=False), dict(present=False), dict(client_eku=ExtendedKeyUsageOID.SERVER_AUTH)):
            with self.subTest(kwargs=kwargs):
                other = TLSFixture(**kwargs)
                try: self.assertIsInstance(other.accepted, ssl.SSLError)
                finally: other.close()

if __name__ == '__main__': unittest.main()
