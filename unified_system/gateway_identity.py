"""Disposable actual mTLS service authentication; no native/production admission.

Root owns listener, loaded certificate/key proof, commissioning and audit draining.
READ_DATA handles are instance/session/request/resource/store bound local objects.
No distributed fence, Windows identity, mutation or reusable remote credential.
"""
import copy
import hashlib
import json
import re
import ssl
import threading
import time
from datetime import datetime, timezone
from cryptography import x509
from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes
from cryptography.x509.oid import ExtendedKeyUsageOID

class GatewayIdentityDenied(RuntimeError):
    pass

class GatewayIdentityUnavailable(RuntimeError):
    pass

def _deny(ok):
    if not ok:
        raise GatewayIdentityDenied('GATEWAY_READ_DENIED')

def _uuid(value):
    _deny(type(value) is str and re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}', value) is not None)

def _sha(value):
    _deny(type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None)

def _binding(value):
    _deny(type(value) is dict and set(value) == {'schema', 'dataset_id', 'dataset_revision',
          'manifest_sha256', 'schema_sha256', 'consumer_id', 'view_id'})
    _deny(value['schema'] == 'unified.gateway.read-binding.v1-review2')
    for name in ('dataset_id', 'consumer_id', 'view_id'):
        _uuid(value[name])
    for name in ('manifest_sha256', 'schema_sha256'):
        _sha(value[name])
    rev = value['dataset_revision']
    _deny(type(rev) is str and re.fullmatch(r'[1-9][0-9]{0,18}', rev) is not None and int(rev) <= 2**63-1)
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode('ascii')

def _utc():
    return datetime.now(timezone.utc).timestamp()

def _expiry(value):
    _deny(type(value) is str and re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z', value) is not None)
    try:
        return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        raise GatewayIdentityDenied('GATEWAY_READ_DENIED') from None

def _leaf(cert, eku, *, uri=None):
    _deny(cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca is False)
    _deny(list(cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value) == [eku])
    san = list(cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value)
    if uri is not None:
        _deny(len(san) == 1 and type(san[0]) is x509.UniformResourceIdentifier and san[0].value == uri)
    else:
        _deny(len(san) == 1 and type(san[0]) is x509.IPAddress and str(san[0].value) == '127.0.0.1')

class GatewayAuditSink:
    """Bounded local DATA buffer; Root drains to its own sink. No callback."""
    def __init__(self, *, max_events=1024):
        if type(max_events) is not int or not 1 <= max_events <= 4096:
            raise GatewayIdentityUnavailable('AUDIT_CONFIGURATION_UNAVAILABLE')
        self._max = max_events
        self._events = []
        self._lock = threading.Lock()
    def _append(self, event):
        with self._lock:
            if len(self._events) >= self._max:
                raise GatewayIdentityUnavailable('AUDIT_CAPACITY_UNAVAILABLE')
            self._events.append(event)
    def drain(self):
        with self._lock:
            values = tuple(copy.deepcopy(self._events))
            self._events.clear()
            return values

class GatewayClientContext:
    __slots__ = ()
    def __new__(cls):
        raise TypeError('ISSUER_ONLY_CONTEXT')
    def __copy__(self):
        raise TypeError('CONTEXT_NOT_COPYABLE')
    def __deepcopy__(self, memo):
        raise TypeError('CONTEXT_NOT_COPYABLE')
    def __reduce__(self):
        raise TypeError('CONTEXT_NOT_SERIALIZABLE')

class GatewayReadCapability:
    __slots__ = ('_issuer',)
    def __new__(cls):
        raise TypeError('ISSUER_ONLY_READ_CAPABILITY')
    def __copy__(self):
        raise TypeError('CAPABILITY_NOT_COPYABLE')
    def __deepcopy__(self, memo):
        raise TypeError('CAPABILITY_NOT_COPYABLE')
    def __reduce__(self):
        raise TypeError('CAPABILITY_NOT_SERIALIZABLE')
    def check_current(self, *, tool_name, request_bytes, binding, owned_store):
        return self._issuer._check(self, tool_name, request_bytes, binding, owned_store)

class DisposableIdentityAuthority:
    """Trusted fixture owner only. No HTTP endpoint and no public policy writes.

    Actual loaded server cert/key cannot be introspected from SSLContext. Root
    factory MUST prove its load and client-observed exact server DER pin; passing
    profile bytes here is not proof of that prerequisite.
    """
    def __init__(self, *, server_ssl_context, profile, audit_sink):
        if type(audit_sink) is not GatewayAuditSink:
            raise GatewayIdentityUnavailable('AUDIT_SINK_UNAVAILABLE')
        self._audit = audit_sink
        self._lock = threading.RLock()
        self._contexts = {}
        self._caps = {}
        self._revoked = set()
        self._failed_clock = False
        self._wall = _utc()
        self._mono = time.monotonic()
        self._last_wall = self._wall
        self._last_mono = self._mono
        try:
            _deny(type(server_ssl_context) is ssl.SSLContext and server_ssl_context.protocol == ssl.PROTOCOL_TLS_SERVER)
            _deny(server_ssl_context.verify_mode == ssl.CERT_REQUIRED and server_ssl_context.minimum_version >= ssl.TLSVersion.TLSv1_2)
            _deny(type(profile) is dict and set(profile) == {'schema','realm_id','server_certificate_der','clients'})
            _deny(profile['schema'] == 'unified.gateway.disposable-identity.v1-review1')
            _uuid(profile['realm_id'])
            self._realm = profile['realm_id']
            self._ssl = server_ssl_context
            _deny(type(profile['server_certificate_der']) is bytes)
            server = x509.load_der_x509_certificate(profile['server_certificate_der'])
            _leaf(server, ExtendedKeyUsageOID.SERVER_AUTH)
            cas = server_ssl_context.get_ca_certs(binary_form=True)
            _deny(len(cas) == 1)
            self._ca = x509.load_der_x509_certificate(cas[0])
            server.verify_directly_issued_by(self._ca)
            self._server_expiry = server.not_valid_after_utc.timestamp()
            _deny(server.not_valid_before_utc.timestamp() <= self._wall < self._server_expiry)
            _deny(type(profile['clients']) is list and 1 <= len(profile['clients']) <= 32)
            self._clients = {}
            for entry in profile['clients']:
                _deny(type(entry) is dict and set(entry) == {'certificate_sha256','service_id','delegated_user_id','quota_owner_id','uri','expires_utc','grants'})
                _sha(entry['certificate_sha256'])
                _uuid(entry['service_id']); _uuid(entry['delegated_user_id'])
                _deny(type(entry['quota_owner_id']) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}', entry['quota_owner_id']) is not None)
                _deny(entry['uri'] == 'urn:unified:test:service:' + entry['service_id'])
                expiry = _expiry(entry['expires_utc'])
                _deny(self._wall < expiry <= self._wall + 900)
                _deny(type(entry['grants']) is list and 1 <= len(entry['grants']) <= 32)
                grants = []
                for grant in entry['grants']:
                    _deny(type(grant) is dict and set(grant) == {'tool_name','binding','owned_store'})
                    _deny(grant['tool_name'] in ('unified.get_dataset_manifest','unified.query_market_data'))
                    _deny(grant['owned_store'] is not None and type(grant['owned_store']) not in (bool,dict,str,bytes))
                    grants.append((grant['tool_name'], _binding(grant['binding']), grant['owned_store']))
                _deny(entry['certificate_sha256'] not in self._clients)
                self._clients[entry['certificate_sha256']] = dict(fingerprint=entry['certificate_sha256'], service=entry['service_id'], user=entry['delegated_user_id'],
                    quota=entry['quota_owner_id'], uri=entry['uri'], expiry=expiry,
                    deadline=self._mono + min(expiry,self._server_expiry)-self._wall, grants=tuple(grants))
        except (GatewayIdentityDenied, ValueError, TypeError, KeyError, x509.ExtensionNotFound, InvalidSignature, UnsupportedAlgorithm) as exc:
            raise GatewayIdentityUnavailable('COMMISSIONING_PROFILE_UNAVAILABLE') from exc
    def _now(self):
        wall, mono = _utc(), time.monotonic()
        if (self._failed_clock or mono < self._last_mono or wall < self._last_wall
                or wall-self._last_wall < mono-self._last_mono-1.0
                or wall-self._wall < mono-self._mono-1.0):
            self._failed_clock = True
            raise GatewayIdentityUnavailable('CLOCK_UNCERTAIN')
        self._last_wall, self._last_mono = wall, mono
        return wall, mono
    def _emit(self, decision, *, entry=None, tool='', request=b'', binding=b'', target=None):
        self._audit._append(dict(schema='unified.gateway.disposable-audit.v1', realm_id=self._realm,
            decision=decision, reason=decision, target_service_id=target, service_id=entry['service'] if entry else None,
            delegated_user_id=entry['user'] if entry else None, quota_owner_id=entry['quota'] if entry else None,
            tool_name=tool, request_sha256=hashlib.sha256(request).hexdigest() if request else None,
            binding_sha256=hashlib.sha256(binding).hexdigest() if binding else None))
    def _current(self, state):
        wall, mono = self._now()
        entry, sock, expiry, deadline = state
        _deny(entry['service'] not in self._revoked and wall < min(entry['expiry'],expiry,self._server_expiry)
              and mono < min(entry['deadline'],deadline))
        _deny(type(sock) is ssl.SSLSocket and sock.fileno() >= 0 and sock.context is self._ssl and sock.server_side)
        try:
            _deny(hashlib.sha256(sock.getpeercert(binary_form=True)).hexdigest() == entry['fingerprint'])
        except (ValueError, OSError, TypeError):
            raise GatewayIdentityDenied('GATEWAY_READ_DENIED') from None
    def authenticate_connection(self, server_ssl_socket):
        with self._lock:
            self._now()
            if len(self._contexts) >= 128:
                raise GatewayIdentityUnavailable('CONTEXT_CAPACITY_UNAVAILABLE')
            try:
                sock = server_ssl_socket
                _deny(type(sock) is ssl.SSLSocket and sock.context is self._ssl and sock.server_side and sock.fileno() >= 0)
                der = sock.getpeercert(binary_form=True)
                entry = self._clients.get(hashlib.sha256(der).hexdigest())
                _deny(entry is not None)
                cert = x509.load_der_x509_certificate(der)
                cert.verify_directly_issued_by(self._ca)
                _leaf(cert, ExtendedKeyUsageOID.CLIENT_AUTH, uri=entry['uri'])
                _deny(cert.not_valid_before_utc.timestamp() <= _utc())
                cert_expiry = cert.not_valid_after_utc.timestamp()
                state = (entry, sock, cert_expiry, self._mono + cert_expiry-self._wall)
                self._current(state)
                self._emit('AUTHENTICATED_SYNTHETIC_SESSION', entry=entry)
                context = object.__new__(GatewayClientContext)
                self._contexts[context] = state
                return context
            except (GatewayIdentityDenied, ValueError, TypeError, OSError, x509.ExtensionNotFound, InvalidSignature, UnsupportedAlgorithm):
                self._emit('AUTHENTICATION_DENIED')
                raise GatewayIdentityDenied('GATEWAY_READ_DENIED') from None
    def authorize_read(self, context, *, tool_name, request_bytes, binding, owned_store):
        try:
            return self._authorize_read(context, tool_name=tool_name, request_bytes=request_bytes,
                                        binding=binding, owned_store=owned_store)
        except GatewayIdentityDenied:
            self._emit('READ_DENIED')
            raise
    def _authorize_read(self, context, *, tool_name, request_bytes, binding, owned_store):
        with self._lock:
            if len(self._caps) >= 256:
                raise GatewayIdentityUnavailable('READ_CAPACITY_UNAVAILABLE')
            _deny(type(context) is GatewayClientContext and context in self._contexts)
            state = self._contexts[context]
            self._current(state)
            _deny(type(request_bytes) is bytes and 0 < len(request_bytes) <= 32768)
            bound = _binding(binding)
            _deny(type(tool_name) is str and any(tool_name==t and bound==b and owned_store is s for t,b,s in state[0]['grants']))
            self._emit('READ_PERMIT_ISSUED', entry=state[0], tool=tool_name, request=request_bytes, binding=bound)
            cap = object.__new__(GatewayReadCapability)
            cap._issuer = self
            self._caps[cap] = [state,tool_name,hashlib.sha256(request_bytes).digest(),bound,owned_store,0]
            return cap
    def _check(self, cap, tool_name, request_bytes, binding, owned_store):
        try:
            return self._check_read(cap, tool_name, request_bytes, binding, owned_store)
        except GatewayIdentityDenied:
            self._emit('READ_DENIED')
            raise
    def _check_read(self, cap, tool_name, request_bytes, binding, owned_store):
        with self._lock:
            _deny(type(cap) is GatewayReadCapability and cap in self._caps)
            record = self._caps[cap]
            self._current(record[0])
            _deny(type(request_bytes) is bytes and 0 < len(request_bytes) <= 32768)
            bound = _binding(binding)
            _deny(tool_name == record[1] and hashlib.sha256(request_bytes).digest() == record[2]
                  and bound == record[3] and owned_store is record[4]
                  and record[5] < (2 if record[1]=='unified.get_dataset_manifest' else 7))
            self._emit('READ_CURRENT_CHECK', entry=record[0][0], tool=tool_name, request=request_bytes, binding=bound)
            record[5] += 1
            return None
    def revoke_service(self, service_id):
        with self._lock:
            _uuid(service_id)
            # Negative security state must latch even if required audit is full.
            self._revoked.add(service_id)
            self._emit('SERVICE_REVOKED', target=service_id)
