"""SOURCE PREPARATION ONLY: ten controlled-backend actual-code unit cases.

NOT RUN/NOT NATIVE PROOF. Runtime imports occur only inside harness setup.
Root/A8 must admit exact source/dependency origins and a bounded outer runner.
The backend fabricates UNIT DATA only; no HTTP, Consul or real grants result.
Asyncio may allocate an internal self-pipe/socketpair. No global zero-socket claim.
"""
import asyncio
import base64
import copy
from contextlib import AsyncExitStack
from datetime import datetime, timedelta, timezone
from functools import wraps
import hashlib
import ipaddress
import json
import ssl
from types import SimpleNamespace
import unittest
from unittest.mock import patch


CLUSTER = '00000000-0000-4000-8000-000000000001'
GENERATION = '00000000-0000-4000-8000-000000000002'
REALM = '00000000-0000-4000-8000-000000000003'
ACTOR = '00000000-0000-4000-8000-000000000004'
POLICY = '00000000-0000-4000-8000-000000000005'
SERVICE = '00000000-0000-4000-8000-000000000006'
REQUEST = '00000000-0000-4000-8000-000000000007'
JOB = '00000000-0000-4000-8000-000000000008'
OTHER_GENERATION = '00000000-0000-4000-8000-000000000009'
FINGERPRINT = 'a' * 64
INPUT_SHA = 'c548e2ffcd542d5d741682303694b3c6d06507740f158a6e30089b2d5355f648'
PRODUCER = 'aed8a7c8a952f96803c207d5e90b133969a47f04'
TARGET_SCHEMA = 'faf01152678c5b066145dcafebe92f593a641a54dac84da3ce1e1df94c0fb261'
START = datetime(2026, 11, 10, 12, tzinfo=timezone.utc)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('ascii')


def _expiry(seconds=300):
    return (START + timedelta(seconds=seconds)).strftime('%Y-%m-%dT%H:%M:%SZ')


def _runtime_imports():
    # Admission is external: this function MUST NOT be called in SOURCE-only review.
    import httpx
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
    from grid import authority_assignment_v1 as assignment
    from grid import coordination
    from unified_system import gateway_research_identity as broker
    from unified_system.gateway_identity import GatewayAuditSink
    return SimpleNamespace(httpx=httpx, x509=x509, hashes=hashes, serialization=serialization,
                           ec=ec, eku=ExtendedKeyUsageOID, names=NameOID,
                           assignment=assignment, coordination=coordination,
                           broker=broker, audit=GatewayAuditSink)


def _public_ssl_context(runtime):
    """Ephemeral in-memory test CA/server; no personal keys/files/handshake.

    Crypto CPU/RNG/DSO and ssl context allocation are real local effects.
    This is constructor input, NOT a qualified peer or production trust source.
    """
    x509 = runtime.x509
    ca_key = runtime.ec.generate_private_key(runtime.ec.SECP256R1())
    ca_name = x509.Name([x509.NameAttribute(runtime.names.COMMON_NAME, 'MOCK-UNIT-CA')])
    ca = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name)
          .public_key(ca_key.public_key()).serial_number(1)
          .not_valid_before(START - timedelta(seconds=60))
          .not_valid_after(START + timedelta(seconds=600))
          .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
          .sign(ca_key, runtime.hashes.SHA256()))
    server_key = runtime.ec.generate_private_key(runtime.ec.SECP256R1())
    server_name = x509.Name([x509.NameAttribute(runtime.names.COMMON_NAME, 'MOCK-UNIT-SERVER')])
    server = (x509.CertificateBuilder().subject_name(server_name).issuer_name(ca_name)
              .public_key(server_key.public_key()).serial_number(2)
              .not_valid_before(START - timedelta(seconds=60))
              .not_valid_after(START + timedelta(seconds=600))
              .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
              .add_extension(x509.ExtendedKeyUsage([runtime.eku.SERVER_AUTH]), critical=False)
              .add_extension(x509.SubjectAlternativeName([
                  x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]), critical=False)
              .sign(ca_key, runtime.hashes.SHA256()))
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_verify_locations(cadata=ca.public_bytes(runtime.serialization.Encoding.PEM).decode('ascii'))
    return context, server.public_bytes(runtime.serialization.Encoding.DER)


class _MemoryBackend:
    """Closed in-memory response protocol; never delegates to any transport."""
    def __init__(self, coordination):
        self.coordination = coordination
        self.rows = {}
        self.sessions = set()
        self.calls = []
        self.index = 100
        self.session_number = 0
        self.bad_snapshot = None
        self.pause = False
        self.arrived = asyncio.Event()
        self.release = asyncio.Event()
        self.interleave = None
        self.before_write = None

    def put(self, key, value, session=''):
        self.index += 1
        previous = self.rows.get(key)
        self.rows[key] = dict(Key=key, CreateIndex=previous['CreateIndex'] if previous else self.index,
                              ModifyIndex=self.index, Value=base64.b64encode(_canonical(value)).decode(),
                              Session=session)

    def body(self, key):
        return json.loads(base64.b64decode(self.rows[key]['Value'], validate=True))

    def missing(self, key):
        return dict(Key=key, CreateIndex=0, ModifyIndex=0, Value=None, Session='')

    async def _hold(self):
        if self.pause:
            self.arrived.set()
            await self.release.wait()

    async def request(self, method, path, *, missing_ok=False, **kwargs):
        if len(self.calls) >= 256:
            raise AssertionError('MOCK_REQUEST_BUDGET')
        self.calls.append((method, path, copy.deepcopy(kwargs)))
        if method == 'GET' and path.startswith('/v1/kv/'):
            if kwargs.get('params') != {'consistent': ''}:
                raise AssertionError('MOCK_CONSISTENT_GET_REQUIRED')
            key = path[len('/v1/kv/'):]
            row = copy.deepcopy(self.rows.get(key))
            # OLD sequential broker reads principal before this writer transition.
            if self.interleave is not None and '/principals/' in key:
                change, self.interleave = self.interleave, None
                change()
            if '/principal-sessions/' in key:
                await self._hold()
            if row is None and not missing_ok:
                raise AssertionError('MOCK_UNEXPECTED_MISSING_KEY')
            return None if row is None else [row]
        if method == 'PUT' and path == '/v1/session/create':
            self.session_number += 1
            session = '10000000-0000-4000-8000-' + format(self.session_number, '012x')
            self.sessions.add(session)
            return {'ID': session}
        if method == 'PUT' and path.startswith('/v1/session/destroy/'):
            session = path.rsplit('/', 1)[1]
            self.sessions.discard(session)
            for row in self.rows.values():
                if row['Session'] == session:
                    self.index += 1
                    row.update(Session='', ModifyIndex=self.index)
            return True
        if method == 'PUT' and path.startswith('/v1/kv/'):
            key = path[len('/v1/kv/'):]
            session = kwargs.get('params', {}).get('acquire')
            if session not in self.sessions:
                raise AssertionError('MOCK_KV_ACQUIRE_ONLY')
            self.put(key, json.loads(kwargs['content']), session)
            return True
        if method == 'PUT' and path == '/v1/txn':
            ops = kwargs.get('json')
            if type(ops) is not list or not 1 <= len(ops) <= 64:
                raise AssertionError('MOCK_TRANSACTION_PLAN')
            if all(set(op) == {'KV'} and op['KV'].get('Verb') == 'get-or-empty' for op in ops):
                if kwargs.get('params') != {'consistent': ''}:
                    raise AssertionError('MOCK_CONSISTENT_TXN_REQUIRED')
                if self.interleave is not None:
                    change, self.interleave = self.interleave, None
                    change()
                # Materialize all rows at ONE memory cut, before any await.
                result = dict(Results=[{'KV': copy.deepcopy(self.rows.get(op['KV']['Key'],
                                  self.missing(op['KV']['Key'])))} for op in ops],
                              Errors=[], KnownLeader=True, ResultsFilteredByACLs=False)
                await self._hold()
                if self.bad_snapshot is not None:
                    return self.bad_snapshot(copy.deepcopy(result))
                return result
            if self.before_write is not None:
                change, self.before_write = self.before_write, None
                change()
            return self._write_transaction(ops)
        raise AssertionError('MOCK_UNEXPECTED_OPERATION_NO_FALLBACK')

    def _write_transaction(self, ops):
        # Only the existing open-session operation subset; fake atomic DATA.
        pending = copy.deepcopy(self.rows)
        results = []
        for item in ops:
            op = item['KV']
            key, verb = op['Key'], op['Verb']
            row = pending.get(key)
            accepted = ((verb == 'check-index' and row is not None and row['ModifyIndex'] == op['Index'])
                        or (verb == 'check-session' and row is not None and row['Session'] == op['Session'])
                        or (verb == 'check-not-exists' and row is None))
            if verb == 'lock':
                accepted = row is None and op['Session'] in self.sessions
                if accepted:
                    self.index += 1
                    row = dict(Key=key, CreateIndex=self.index, ModifyIndex=self.index,
                               Value=op['Value'], Session=op['Session'])
                    pending[key] = row
            if not accepted:
                raise self.coordination.CoordinationLost('MOCK_TRANSACTION_FENCE_REJECTED')
            if row is not None:
                results.append({'KV': copy.deepcopy(row)})
        self.rows = pending
        return {'Results': results, 'Errors': []}


class _Harness:
    async def __aenter__(self):
        self.stack = AsyncExitStack()
        await self.stack.__aenter__()
        try:
            self.runtime = _runtime_imports()
            self.wall = START.timestamp()
            self.mono = 100.0
            self.peer_service = SERVICE
            self.peer_ok = True
            self.stack.enter_context(patch.object(self.runtime.broker, '_utc', lambda: self.wall))
            # Replace module binding, NOT stdlib time.monotonic or asyncio clock.
            self.stack.enter_context(patch.object(self.runtime.broker, 'time',
                                                 SimpleNamespace(monotonic=lambda: self.mono)))
            async def forbidden_http(*args, **kwargs):
                raise AssertionError('REAL_HTTP_FORBIDDEN_IN_MOCK_UNIT')
            self.stack.enter_context(patch.object(self.runtime.httpx.AsyncClient, 'request', forbidden_http))
            self.stack.enter_context(patch.object(self.runtime.httpx.AsyncHTTPTransport,
                                                 'handle_async_request', forbidden_http))
            config = self.runtime.coordination.ConsulConfig(('http://127.0.0.1:1',),
                     'unified/' + CLUSTER, isolated_lab=True, acl_token='MOCK_BACKEND_ONLY',
                     ttl_seconds=15, request_timeout=2)
            self.authority = self.runtime.coordination.ConsulSessionAuthority(config, clock=lambda: self.mono)
            self.stack.push_async_callback(self.authority.close)
            self.backend = _MemoryBackend(self.runtime.coordination)
            self.stack.enter_context(patch.object(self.authority, '_request', self.backend.request))
            self.ssl_context, self.server_der = _public_ssl_context(self.runtime)
            self.namespace = config.namespace
            self.prefix = self.namespace + '/runtime-v1/research-lab-v1/' + REALM + '/'
            self.target = dict(schema='unified.gateway.target-native-request.v1-review1', request_id=REQUEST,
                target_kind='MetaAnalyse', target_capability='meta.ohlcv.untouched_levels.v1',
                target_version='f3c01a23fa5baaeeeb28eb8e9397e72b5ef4d5a1',
                dataset_manifest_id='local-sha256:33d5bf0f918884c8908795b384e0964a48a1351c808800964b8cacf3f83e28b6',
                dataset_revision='LOCAL_FIXTURE_1', experiment_id='fixture.gateway.btc.levels',
                strategy_version=None, parameters_digest=INPUT_SHA,
                execution_mode='NATIVE_RESEARCH_ADMISSION_REQUEST_NOT_PERMISSION',
                resource_budget=dict(max_input_bytes=16384, max_output_bytes=16384, max_rows=3, max_executions=1),
                quota_owner='mock_quota', principal_id=ACTOR, authority_generation=GENERATION,
                assignment_revision=None, fencing_token=None, idempotency_key='mock_original',
                result_schema='unified.gateway.native-target-observation.v1-review1', result_artifact_ref=None)
            target_raw = _canonical(self.target)
            self.profile = dict(schema='unified.authority.target-bound-research-profile.v2-review1',
                cluster_id=CLUSTER, realm_id=REALM, principal_registry={FINGERPRINT: ACTOR},
                input_request_sha256=INPUT_SHA, producer_head=PRODUCER,
                resources=dict(cpu_millicores='1000', resident_memory_bytes='268435456', max_artifact_bytes='1048576'),
                expiry_semantics='NATIVE_SESSION_INVALIDATION_NOT_UTC_AT_COMMIT', expires_utc=_expiry(),
                target_binding=dict(target_request_schema_sha256=TARGET_SCHEMA,
                    target_request_canonical_base64=base64.b64encode(target_raw).decode(),
                    target_request_sha256=hashlib.sha256(target_raw).hexdigest(), request_id=REQUEST,
                    job_id=JOB, idempotency_key='mock_original', cluster_generation=GENERATION,
                    actor_principal_id=ACTOR, quota_owner_id='mock_quota',
                    producer_request_sha256=INPUT_SHA, producer_head=PRODUCER))
            self.profile_sha = hashlib.sha256(_canonical(self.profile)).hexdigest()
            self.principal = dict(schema='unified.authority.research-lab-principal.v1-review1',
                actor_id=ACTOR, service_id=SERVICE, certificate_sha256=FINGERPRINT, quota_owner_id='mock_quota',
                policy_id=POLICY, profile_sha256=self.profile_sha, state='ACTIVE')
            self.policy = dict(schema='unified.authority.research-lab-policy.v1-review1', policy_id=POLICY,
                actor_id=ACTOR, profile_sha256=self.profile_sha, revision='1', state='ACTIVE',
                scopes=['CANCEL_OWN_JOB', 'READ_RESEARCH', 'SUBMIT_RESEARCH'], expires_utc=_expiry())
            self.backend.put(self.namespace + '/commands/generation', {'generation': GENERATION})
            self.backend.put(self.prefix + 'profile-registry/' + self.profile_sha, self.profile)
            self.backend.put(self.prefix + 'principals/' + ACTOR, self.principal)
            self.backend.put(self.prefix + 'policies/' + POLICY, self.policy)
            self.broker = self.make_broker()
            self.stack.push_async_callback(self.broker.close)
            self.backend.calls.clear()
            return self
        except BaseException:
            await self.stack.aclose()
            raise

    def make_broker(self):
        broker = self.runtime.broker.ResearchIdentityBroker(authority=self.authority, generation=GENERATION,
                 realm_id=REALM, profile_sha256=self.profile_sha, server_ssl_context=self.ssl_context,
                 server_certificate_der=self.server_der, audit_sink=self.runtime.audit(max_events=100))
        def modeled_peer(sock):
            if not self.peer_ok:
                raise self.runtime.broker.ResearchIdentityDenied('MOCK_PEER_LOSS')
            return FINGERPRINT, self.peer_service, START.timestamp() + 600
        self.stack.enter_context(patch.object(broker, '_peer', modeled_peer))
        return broker

    @property
    def original(self):
        return _canonical(dict(schema='unified.gateway.lab-job-submit.v1-review1', operation='SUBMIT_RESEARCH',
            cluster_id=CLUSTER, cluster_generation=GENERATION, request_id=REQUEST, job_id=JOB,
            original_actor_principal_id=ACTOR, quota_owner_id='mock_quota', idempotency_key='mock_original',
            commissioned_profile_sha256=self.profile_sha, input_request_sha256=INPUT_SHA,
            producer_head=PRODUCER, resources=self.profile['resources']))

    async def open(self):
        self.leader = await self.authority.acquire('mock-source-unit')
        if self.leader is None:
            raise AssertionError('MOCK_LEADER_SETUP_FAILED')
        # Actual broker is the only object constructing its context/capture.
        self.context = await self.broker.open_session(object(), leader=self.leader)
        self.backend.calls.clear()
        return self.context

    async def capture(self):
        return await self.broker.capture_current(self.context, scope='READ_RESEARCH', request_bytes=self.original)

    def require(self, capture, **changes):
        kwargs = dict(expected_authority=self.authority, scope='READ_RESEARCH', request_bytes=self.original)
        kwargs.update(changes)
        return self.broker.require_capture(capture, **kwargs)

    def expected_keys(self):
        session = self.broker._contexts[self.context][3]
        return (self.namespace + '/commands/generation', self.prefix + 'profile-registry/' + self.profile_sha,
                self.prefix + 'principals/' + ACTOR, self.prefix + 'policies/' + POLICY,
                self.prefix + 'principal-sessions/' + session + '/lock')

    def change_identity(self):
        self.backend.put(self.namespace + '/commands/generation', {'generation': OTHER_GENERATION})
        self.backend.put(self.prefix + 'principals/' + ACTOR, dict(self.principal, state='REVOKED'))
        self.backend.put(self.prefix + 'policies/' + POLICY, dict(self.policy, revision='2'))

    async def __aexit__(self, *args):
        # Release paused tasks before close; no orphan intentionally retained.
        self.backend.release.set()
        await self.stack.aclose()


def _case_budget(method):
    @wraps(method)
    async def bounded(self):
        await asyncio.wait_for(method(self), timeout=5)
    return bounded


class ControlledBackendBrokerUnitTests(unittest.IsolatedAsyncioTestCase):
    """MOCK_BACKEND_UNIT_ONLY: no native acceptance or actual peer proof."""
    async def asyncSetUp(self):
        self.stack = AsyncExitStack()
        await self.stack.__aenter__()
        self.addAsyncCleanup(self.stack.aclose)
        self.h = await self.stack.enter_async_context(_Harness())

    @_case_budget
    async def test_mock_backend_same_authority_constructor_creates_no_native_call(self):
        h = self.h
        self.assertEqual(h.backend.calls, [])
        source = getattr(h.broker, '_identity_snapshot_source', None)
        self.assertIs(type(source), h.runtime.assignment.AssignmentAuthority)
        self.assertIs(source.authority, h.authority)
        self.assertEqual(source.generation, GENERATION)
        self.assertIsNone(source.native_provider)
        self.assertEqual(source.prefix, h.namespace + '/runtime-v1/')
        self.assertEqual(h.backend.sessions, set())
        self.assertEqual(h.broker._contexts, {})

    @_case_budget
    async def test_mock_backend_stable_read_uses_one_five_key_snapshot_and_preserves_order(self):
        h = self.h
        await h.open()
        capture = await h.capture()
        snapshot = h.require(capture)
        self.assertEqual(tuple(row.key for row in snapshot.records), h.expected_keys())
        self.assertEqual(len({row.index for row in snapshot.records}), 5)
        self.assertEqual(tuple(row.raw for row in snapshot.records), tuple(
            base64.b64decode(h.backend.rows[key]['Value'], validate=True) for key in h.expected_keys()))
        self.assertEqual(len(h.backend.calls), 1)
        method, path, options = h.backend.calls[0]
        self.assertEqual((method, path), ('PUT', '/v1/txn'))
        self.assertEqual(options['params'], {'consistent': ''})
        self.assertEqual(options['json'], [{'KV': {'Verb': 'get-or-empty', 'Key': key}}
                                         for key in h.expected_keys()])

    @_case_budget
    async def test_mock_backend_generation_or_principal_policy_interleaving_cannot_issue_mixed_capture(self):
        h = self.h
        await h.open()
        h.backend.interleave = h.change_identity
        before = len(h.broker._captures)
        with self.assertRaises(h.runtime.broker.ResearchIdentityDenied):
            await h.capture()
        self.assertEqual(len(h.broker._captures), before)

    @_case_budget
    async def test_mock_backend_snapshot_inventory_acl_and_transport_fail_closed(self):
        h = self.h
        await h.open()
        def missing(result):
            result['Results'][0]['KV'] = h.backend.missing(h.expected_keys()[0])
            return result
        def reorder(result):
            result['Results'][0], result['Results'][1] = result['Results'][1], result['Results'][0]
            return result
        def duplicate(result):
            result['Results'][1] = copy.deepcopy(result['Results'][0])
            return result
        def invalid_index(result):
            result['Results'][0]['KV']['ModifyIndex'] = True
            return result
        def invalid_base64(result):
            result['Results'][0]['KV']['Value'] = '!'
            return result
        def unavailable(result):
            raise h.runtime.coordination.CoordinationUnavailable('MOCK_NO_QUORUM')
        cases = (('missing', missing), ('order', reorder), ('duplicate', duplicate),
                 ('bool_index', invalid_index), ('base64', invalid_base64), ('transport', unavailable),
                 ('acl', lambda r: dict(r, ResultsFilteredByACLs=True)),
                 ('leader', lambda r: dict(r, KnownLeader=False)),
                 ('short', lambda r: dict(r, Results=r['Results'][:-1])),
                 ('extra', lambda r: dict(r, Results=r['Results'] + r['Results'][:1])))
        for name, mutate in cases:
            with self.subTest(case=name):
                h.backend.bad_snapshot = mutate
                before = len(h.broker._captures)
                with self.assertRaises(h.runtime.broker.ResearchIdentityUnavailable) as caught:
                    await h.capture()
                expected = 'NATIVE_IDENTITY_RECORD_UNAVAILABLE' if name == 'missing' else 'NATIVE_IDENTITY_SOURCE_UNAVAILABLE'
                self.assertEqual(str(caught.exception), expected)
                self.assertEqual(len(h.broker._captures), before)

    @_case_budget
    async def test_mock_backend_context_loss_during_snapshot_prevents_capture(self):
        for loss in ('invalidate', 'closed', 'peer', 'expiry'):
            with self.subTest(loss=loss):
                async with _Harness() as h:
                    await h.open()
                    h.backend.pause = True
                    task = asyncio.create_task(h.capture())
                    try:
                        await asyncio.wait_for(h.backend.arrived.wait(), 1)
                        if loss == 'invalidate':
                            h.broker.invalidate_context_local_only(h.context)
                        elif loss == 'closed':
                            h.broker._closed = True  # Equivalent existing close latch, no retirement here.
                        elif loss == 'peer':
                            h.peer_ok = False
                        else:
                            h.wall += 301
                            h.mono += 301
                        h.backend.release.set()
                        with self.assertRaises((h.runtime.broker.ResearchIdentityDenied,
                                                h.runtime.broker.ResearchIdentityUnavailable)):
                            await task
                        self.assertEqual(h.broker._captures, {})
                    finally:
                        h.backend.release.set()
                        if not task.done():
                            task.cancel()
                        await asyncio.gather(task, return_exceptions=True)

    @_case_budget
    async def test_mock_backend_cancelled_snapshot_propagates_without_capture_or_retry(self):
        h = self.h
        await h.open()
        h.backend.pause = True
        task = asyncio.create_task(h.capture())
        try:
            await asyncio.wait_for(h.backend.arrived.wait(), 1)
            count = len(h.backend.calls)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertEqual(len(h.backend.calls), count)
            self.assertEqual(h.broker._captures, {})
            self.assertFalse(any(path.startswith('/v1/session/') for _, path, _ in h.backend.calls))
        finally:
            h.backend.release.set()
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    @_case_budget
    async def test_mock_backend_policy_decoder_keeps_original_schema_target_scope_and_expiry_rejections(self):
        h = self.h
        await h.open()
        principal_key = h.prefix + 'principals/' + ACTOR
        policy_key = h.prefix + 'policies/' + POLICY
        cases = (('principal', principal_key, dict(h.principal, state='REVOKED')),
                 ('policy', policy_key, dict(h.policy, state='REVOKED')),
                 ('revision', policy_key, dict(h.policy, revision='0')),
                 ('scope', policy_key, dict(h.policy, scopes=['SUBMIT_RESEARCH'])),
                 ('expiry', policy_key, dict(h.policy, expires_utc=_expiry(-1))),
                 ('profile_hash', h.prefix + 'profile-registry/' + h.profile_sha,
                  dict(h.profile, input_request_sha256='f' * 64)))
        baseline = copy.deepcopy(h.backend.rows)
        for name, key, body in cases:
            with self.subTest(case=name):
                h.backend.rows = copy.deepcopy(baseline)
                h.backend.put(key, body)
                with self.assertRaises(h.runtime.broker.ResearchIdentityDenied):
                    await h.capture()
        h.backend.rows = baseline
        with self.assertRaises(h.runtime.broker.ResearchIdentityDenied):
            await h.broker.capture_current(h.context, scope='READ_RESEARCH', request_bytes=b'{"role":"admin"}')
        # Fully rebound v2 target with wrong numeric type: normal new broker/open,
        # never a forged context and never a real job or target execution.
        changed = copy.deepcopy(h.target)
        changed['resource_budget']['max_rows'] = True
        raw = _canonical(changed)
        bad_profile = copy.deepcopy(h.profile)
        bad_profile['target_binding'].update(target_request_canonical_base64=base64.b64encode(raw).decode(),
                                            target_request_sha256=hashlib.sha256(raw).hexdigest())
        h.profile = bad_profile
        h.profile_sha = hashlib.sha256(_canonical(bad_profile)).hexdigest()
        h.backend.put(h.prefix + 'profile-registry/' + h.profile_sha, bad_profile)
        h.backend.put(principal_key, dict(h.principal, profile_sha256=h.profile_sha))
        h.backend.put(policy_key, dict(h.policy, profile_sha256=h.profile_sha))
        bad_broker = h.make_broker()
        h.stack.push_async_callback(bad_broker.close)
        with self.assertRaises(h.runtime.broker.ResearchIdentityDenied):
            await bad_broker.open_session(object(), leader=h.leader)

    @_case_budget
    async def test_mock_backend_open_session_retains_atomic_record_and_leader_fences(self):
        h = self.h
        await h.open()
        # Read original modeled write plan from another normally issued context.
        h.backend.calls.clear()
        await h.broker.open_session(object(), leader=h.leader)
        plan = next(options['json'] for method, path, options in h.backend.calls
                    if method == 'PUT' and path == '/v1/txn')
        self.assertEqual([op['KV']['Verb'] for op in plan],
                         ['check-index'] * 5 + ['check-session', 'check-not-exists', 'lock'])
        self.assertEqual([op['KV']['Key'] for op in plan[:4]], list(h.expected_keys()[:4]))
        self.assertEqual(plan[4]['KV'], dict(Verb='check-index', Key=h.authority.key, Index=h.leader.token))
        self.assertEqual(plan[5]['KV'], dict(Verb='check-session', Key=h.authority.key, Session=h.leader.session_id))
        before = len(h.broker._contexts)
        sessions = set(h.backend.sessions)
        h.backend.before_write = lambda: h.backend.put(h.namespace + '/commands/generation',
                                                       {'generation': OTHER_GENERATION})
        with self.assertRaises(h.runtime.broker.ResearchIdentityUnavailable):
            await h.broker.open_session(object(), leader=h.leader)
        self.assertEqual(len(h.broker._contexts), before)
        self.assertEqual(h.backend.sessions, sessions)

    @_case_budget
    async def test_mock_backend_existing_reobserve_guard_remains_required(self):
        h = self.h
        await h.open()
        consumer = h.runtime.assignment.ResearchLabAuthority(h.authority, GENERATION, broker=h.broker)
        original_reader = consumer._native._read_snapshot
        async def change_before_reobserve(keys):
            h.change_identity()
            return await original_reader(keys)
        with patch.object(consumer._native, '_read_snapshot', change_before_reobserve):
            with self.assertRaises(h.runtime.assignment.AssignmentUnavailable) as caught:
                await consumer._observe(h.original, context=h.context, scope='READ_RESEARCH')
        self.assertEqual(str(caught.exception), 'CURRENT_IDENTITY_SNAPSHOT_CHANGED')

    @_case_budget
    async def test_mock_backend_cached_capture_is_historical_until_explicit_reobserve(self):
        h = self.h
        await h.open()
        captured = await h.capture()
        prior = h.require(captured)
        h.backend.put(h.prefix + 'policies/' + POLICY, dict(h.policy, state='REVOKED', revision='2'))
        h.backend.calls.clear()
        self.assertIs(h.require(captured), prior)
        self.assertEqual(h.backend.calls, [])
        with self.assertRaises(h.runtime.broker.ResearchIdentityDenied):
            await h.capture()


EXPECTED_METHODS = (
    'test_mock_backend_same_authority_constructor_creates_no_native_call',
    'test_mock_backend_stable_read_uses_one_five_key_snapshot_and_preserves_order',
    'test_mock_backend_generation_or_principal_policy_interleaving_cannot_issue_mixed_capture',
    'test_mock_backend_snapshot_inventory_acl_and_transport_fail_closed',
    'test_mock_backend_context_loss_during_snapshot_prevents_capture',
    'test_mock_backend_cancelled_snapshot_propagates_without_capture_or_retry',
    'test_mock_backend_policy_decoder_keeps_original_schema_target_scope_and_expiry_rejections',
    'test_mock_backend_open_session_retains_atomic_record_and_leader_fences',
    'test_mock_backend_existing_reobserve_guard_remains_required',
    'test_mock_backend_cached_capture_is_historical_until_explicit_reobserve',
)


def main():
    """Inner cooperative runner SOURCE; external hard budgets/admission required.

    No subprocess or installer. Does NOT provide process-family/network/memory
    containment, source authentication, or a substitute for Root/A8 admission.
    """
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ControlledBackendBrokerUnitTests)
    expected = {'__main__.ControlledBackendBrokerUnitTests.' + name for name in EXPECTED_METHODS}
    actual = {case.id() for case in suite}
    if suite.countTestCases() != 10 or len(actual) != 10 or actual != expected:
        raise RuntimeError('MOCK_UNIT_EXACT_INVENTORY_REQUIRED')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.skipped:
        raise RuntimeError('MOCK_UNIT_SKIPS_FORBIDDEN')
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
