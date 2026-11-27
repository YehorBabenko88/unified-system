"""Unified-owned Consul session transport; never resource-side fencing.

Extracted from Grid295 c9ffdaa coordination.py; no Grid factories or aliases.
"""
import asyncio
import base64
from dataclasses import dataclass, field
import json
import math
import re
import ssl
import time
from urllib.parse import quote, urlsplit

import httpx

from .grid_writer_fence_model import _consul_session_id


class CoordinationUnavailable(RuntimeError):
    pass


class CoordinationLost(CoordinationUnavailable):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


@dataclass(frozen=True)
class ConsulConfig:
    endpoints: tuple[str, ...]
    namespace: str
    acl_token: str = field(default='', repr=False)
    ca_bundle: str | None = None
    client_certificate: str | None = None
    client_key: str | None = field(default=None, repr=False)
    isolated_lab: bool = False
    ttl_seconds: int = 15
    request_timeout: float = 2.0

    def __post_init__(self):
        if (type(self.endpoints) is not tuple or not 1 <= len(self.endpoints) <= 5
                or len(set(self.endpoints)) != len(self.endpoints)):
            raise ValueError('one to five distinct Consul endpoints required')
        if (type(self.namespace) is not str or len(self.namespace) > 200
                or not re.fullmatch(r'[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*', self.namespace)):
            raise ValueError('explicit coordination namespace required')
        if type(self.isolated_lab) is not bool:
            raise ValueError('isolated_lab must be explicit boolean')
        for endpoint in self.endpoints:
            p = urlsplit(endpoint)
            if (p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password
                    or p.path not in ('', '/') or p.query or p.fragment):
                raise ValueError('ordinary HTTP(S) Consul endpoint required')
            if not self.isolated_lab and p.scheme != 'https':
                raise ValueError('production Consul requires HTTPS')
        if not self.isolated_lab and not all((self.acl_token, self.ca_bundle, self.client_certificate, self.client_key)):
            raise ValueError('production Consul requires ACL token, trusted CA and mutual TLS certificate/key')
        if type(self.ttl_seconds) is not int or not 10 <= self.ttl_seconds <= 3600:
            raise ValueError('Consul TTL must be between 10 and 3600 seconds')
        if (type(self.request_timeout) not in (int, float) or not math.isfinite(self.request_timeout)
                or not 0 < self.request_timeout < self.ttl_seconds / 3):
            raise ValueError('request deadline must be positive and below a third of session TTL')


@dataclass(frozen=True)
class ConsulLease:
    owner: str
    session_id: str
    token: int


class ConsulSessionAuthority:
    def __init__(self, config: ConsulConfig, *, client=None, clock=time.monotonic):
        self.config = config
        self.key = config.namespace + '/leader'
        self.clock = clock
        self._sessions = {}
        self._deadlines = {}
        self._owns_client = client is None
        self._closed = False
        if client is not None and not config.isolated_lab:
            raise ValueError('injected HTTP transports are restricted to isolated lab configuration')
        if client is None:
            context = ssl.create_default_context()
            if config.ca_bundle:
                context.load_verify_locations(cafile=config.ca_bundle)
            if config.client_certificate:
                context.load_cert_chain(config.client_certificate, config.client_key)
            client = httpx.AsyncClient(verify=context, follow_redirects=False, trust_env=False)
        self.client = client

    async def close(self):
        # Closing the authority always revokes local grants, even when the
        # HTTP transport was injected and is owned by another caller.
        # Do not silently destroy Consul sessions: original SQL/OS shutdown
        # may still be UNKNOWN and needs independent Root reconciliation.
        self._closed = True
        for session in self._deadlines:
            self._deadlines[session] = 0
        if self._owns_client:
            await self.client.aclose()

    async def _request(self, method, path, *, missing_ok=False, **kwargs):
        headers = {'X-Consul-Token': self.config.acl_token} if self.config.acl_token else {}
        async def attempt():
            # Writes deliberately target one endpoint (no uncertain replay),
            # so retain the full request deadline. Divide only GET failover
            # budgets among the configured independent read endpoints.
            budget = (self.config.request_timeout if method != 'GET'
                      else self.config.request_timeout / len(self.config.endpoints))
            for endpoint in self.config.endpoints:
                try:
                    response = await asyncio.wait_for(
                        self.client.request(method, endpoint.rstrip('/') + path,
                            headers=headers, timeout=budget, **kwargs), timeout=budget)
                except (httpx.HTTPError, asyncio.TimeoutError):
                    # A timed-out PUT may have committed before the reply was
                    # lost. Never replay a mutation on another endpoint:
                    # session/create, renew, destroy and /txn are all
                    # deliberately single-attempt under ambiguous failure.
                    if method != 'GET':
                        raise CoordinationUnavailable(
                            'Consul mutation outcome unknown') from None
                    continue
                if response.status_code >= 500:
                    # Even a server-side error can follow an applied write.
                    # Keep GET quorum failover, but never retry mutations.
                    if method != 'GET':
                        raise CoordinationUnavailable(
                            'Consul mutation outcome unknown')
                    continue
                if response.status_code == 404 and missing_ok:
                    return None
                if response.status_code == 409:
                    raise CoordinationLost('Consul fencing transaction rejected')
                if response.status_code != 200 or len(response.content) > 65536:
                    raise CoordinationUnavailable('Consul request denied or invalid response')
                try:
                    return response.json()
                except (ValueError, TypeError):
                    raise CoordinationUnavailable('Consul returned invalid JSON') from None
            raise CoordinationUnavailable('Consul quorum endpoint unavailable')
        try:
            return await asyncio.wait_for(attempt(), timeout=self.config.request_timeout)
        except asyncio.TimeoutError:
            raise CoordinationUnavailable('Consul request deadline exceeded') from None

    async def _read_lock(self):
        rows = await self._request('GET', '/v1/kv/' + quote(self.key, safe='/'),
                                   params={'consistent': ''}, missing_ok=True)
        if rows is None:
            return None
        if type(rows) is not list or len(rows) != 1 or type(rows[0]) is not dict:
            raise CoordinationUnavailable('Consul lock record invalid')
        return rows[0]

    def _matches(self, row, lease):
        try:
            return (row is not None and row.get('Key') == self.key
                    and row['Session'] == lease.session_id
                    and type(row['ModifyIndex']) is int and row['ModifyIndex'] == lease.token
                    and json.loads(base64.b64decode(row['Value'], validate=True)) ==
                        {'owner': lease.owner, 'session_id': lease.session_id, 'namespace': self.config.namespace})
        except (ValueError, TypeError, KeyError):
            return False

    async def acquire(self, owner):
        if self._closed:
            raise CoordinationUnavailable('Consul authority already closed')
        if type(owner) is not str or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', owner):
            raise ValueError('stable owner identifier required')
        started = self.clock()
        created = await self._request('PUT', '/v1/session/create', json={
            'Name': 'unified-control-' + owner, 'TTL': str(self.config.ttl_seconds) + 's',
            'Behavior': 'release', 'LockDelay': '0s', 'NodeChecks': []})
        # Session ID is an opaque value supplied by Consul, not an RFC4122
        # UUID4/UUID5 credential. Never normalize or mint a replacement.
        # The acquired KV lock + exact local lease is the authority witness.
        session = created.get('ID') if type(created) is dict else None
        if not _consul_session_id(session):
            raise CoordinationUnavailable('Consul session identity invalid')
        destroy_attempted = False
        try:
            if self._closed:
                raise CoordinationLost('Consul authority closed during acquisition')
            value = canonical({'owner': owner, 'session_id': session, 'namespace': self.config.namespace})
            won = await self._request('PUT', '/v1/kv/' + quote(self.key, safe='/'),
                                      params={'acquire': session}, content=value)
            if won is not True:
                # A failed KV acquire must clean up only once; if destroy
                # replied false or its reply was lost, retrying from the
                # exception handler would replay an unknown mutation.
                destroy_attempted = True
                destroyed = await self._request(
                    'PUT', '/v1/session/destroy/' + session)
                if destroyed is not True:
                    raise CoordinationLost('Consul unacquired session destroy unconfirmed')
                return None
            row = await self._read_lock()
            token = row.get('ModifyIndex') if row else None
            if type(token) is not int or not 0 < token < (1 << 63):
                raise CoordinationLost('Consul fencing token invalid')
            lease = ConsulLease(owner, session, token)
            if (self._closed or not self._matches(row, lease)
                    or self.clock() >= started + self.config.ttl_seconds - 1):
                raise CoordinationLost('Consul acquisition no longer current')
            self._sessions[session] = lease
            self._deadlines[session] = started + self.config.ttl_seconds - 1
            return lease
        except BaseException:
            if not destroy_attempted:
                destroy_attempted = True
                try:
                    # Best-effort single attempt; failure remains UNKNOWN and
                    # never authorizes another Root lease or writer claim.
                    await self._request('PUT', '/v1/session/destroy/' + session)
                except CoordinationUnavailable:
                    pass
            raise

    async def validate(self, lease):
        # A copied caller-built dataclass can equal the original lease by
        # value. Only the exact object issued by this authority is local proof.
        if (self._closed or type(lease) is not ConsulLease
                or self._sessions.get(lease.session_id) is not lease):
            return False
        deadline = self._deadlines.get(lease.session_id, 0)
        if self.clock() >= deadline:
            return False
        try:
            row = await self._read_lock()
            return (self.clock() < deadline
                    and self._deadlines.get(lease.session_id, 0) >= deadline
                    and self._sessions.get(lease.session_id) is lease
                    and self._matches(row, lease))
        except CoordinationUnavailable:
            return False

    async def renew(self, lease):
        if (self._closed or
                self._sessions.get(getattr(lease, 'session_id', None)) is not lease):
            return False
        started = self.clock()
        if started >= self._deadlines[lease.session_id]:
            return False
        try:
            result = await self._request('PUT', '/v1/session/renew/' + lease.session_id)
            # A malformed session-renew reply is an unknown result, not an
            # exception that leaves the old local renewal deadline active.
            # Session ID must match exactly; a forged JSON scalar or row
            # cannot extend or retain this Root owner's lease authority.
            if (type(result) is not list or len(result) != 1
                    or type(result[0]) is not dict
                    or result[0].get('ID') != lease.session_id
                    or not await self.validate(lease)):
                self._deadlines[lease.session_id] = 0
                return False
            self._deadlines[lease.session_id] = started + self.config.ttl_seconds - 1
            return True
        except CoordinationUnavailable:
            self._deadlines[lease.session_id] = 0
            return False
        except BaseException:
            # asyncio.CancelledError is BaseException (not Exception).
            # A renew request can have reached Consul before task shutdown.
            # Never retain a locally trusted deadline after such ambiguity.
            self._deadlines[lease.session_id] = 0
            raise

    async def release(self, lease):
        if self._sessions.get(getattr(lease, 'session_id', None)) is not lease:
            return
        # Never allow a stale local lease to validate while destruction is
        # in flight or its outcome remains unknown.
        self._deadlines[lease.session_id] = 0
        # Destroying our own session releases the persistent KV lock. Never
        # delete the key: its Raft ModifyIndex remains the resource fence.
        # Consul may return HTTP 200 with JSON false, or the reply can be
        # lost after commit. Preserve the exact session identity for explicit
        # idempotent cleanup/reconciliation until success is confirmed.
        destroyed = await self._request(
            'PUT', '/v1/session/destroy/' + lease.session_id)
        if destroyed is not True:
            raise CoordinationLost('Consul session destroy unconfirmed')
        self._sessions.pop(lease.session_id, None)

    def _state_key(self, name):
        if type(name) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', name):
            raise ValueError('bounded control record name required')
        return self.config.namespace + '/state/' + name

    async def write_control(self, lease, name, payload):
        if not await self.validate(lease):
            raise CoordinationLost('current quorum-backed lease required')
        value = canonical({'owner': lease.owner, 'token': lease.token, 'session_id': lease.session_id, 'payload': payload})
        if len(value) > 32768:
            raise ValueError('control record exceeds byte budget')
        operations = [
            {'KV': {'Verb': 'check-session', 'Key': self.key, 'Session': lease.session_id}},
            {'KV': {'Verb': 'check-index', 'Key': self.key, 'Index': lease.token}},
            {'KV': {'Verb': 'set', 'Key': self._state_key(name), 'Value': base64.b64encode(value).decode()}},
        ]
        # A lost /txn reply may conceal a committed state mutation. Block
        # further writes by this original local lease until external Root/C
        # reconciliation; the caller must not replay or mint a new owner.
        try:
            result = await self._request('PUT', '/v1/txn', json=operations)
        except BaseException:
            # Includes asyncio cancellation during the original network
            # mutation; the server may have committed without an ACK.
            # Quarantine the exact old lease, propagate cancellation, and
            # never blindly replay the transaction.
            self._deadlines[lease.session_id] = 0
            raise
        # HTTP 200 without transaction Results is not a verifiable commit.
        # A successful set operation returns its KV key and ModifyIndex;
        # check-session/check-index are still enforced by Consul atomically.
        # Never treat {}, a malformed Errors field, or an unrelated KV row as
        # confirmation of the original owner-controlled state write.
        target = self._state_key(name)
        if (type(result) is not dict
                or result.get('Errors') not in (None, [])
                or type(result.get('Results')) is not list
                or not any(
                    type(entry) is dict
                    and type(entry.get('KV')) is dict
                    and entry['KV'].get('Key') == target
                    and type(entry['KV'].get('ModifyIndex')) is int
                    and entry['KV']['ModifyIndex'] > 0
                    for entry in result['Results']
                )):
            self._deadlines[lease.session_id] = 0
            raise CoordinationLost('Consul fencing transaction unconfirmed')
        # A syntactically successful Consul write may finish only after the
        # original local lease deadline (or after a concurrent release).
        # No caller may interpret that old write as current Root authority.
        # Re-read the original lease and consistent leader KV *after* the
        # network transaction, rejecting both timeout and changed owner.
        try:
            still_current = await self.validate(lease)
        except BaseException:
            # Even post-transaction read cancellation leaves the preceding
            # mutation outcome uncertain to its caller.
            self._deadlines[lease.session_id] = 0
            raise
        if not still_current:
            self._deadlines[lease.session_id] = 0
            raise CoordinationLost('Consul lease lost after control transaction')

    async def read_control(self, name):
        # Historical control data is readable, but is never a Root lease or
        # a substitute for current leader/session/SQL fencing authority.
        if self._closed:
            raise CoordinationUnavailable('Consul authority already closed')
        target = self._state_key(name)
        rows = await self._request('GET', '/v1/kv/' + quote(target, safe='/'),
                                   params={'consistent': ''}, missing_ok=True)
        if rows is None:
            return None
        if type(rows) is not list or len(rows) != 1 or type(rows[0]) is not dict:
            raise CoordinationUnavailable('control record invalid')
        row = rows[0]
        try:
            if (row.get('Key') != target
                    or type(row.get('ModifyIndex')) is not int
                    or not 0 < row['ModifyIndex'] < (1 << 63)
                    or type(row.get('Value')) is not str):
                raise ValueError('control metadata invalid')
            raw = base64.b64decode(row['Value'], validate=True)
            if len(raw) > 32768:
                raise ValueError('control data exceeds byte budget')
            record = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(
                ValueError('non-finite control data')))
            if (type(record) is not dict
                    or set(record) != {'owner', 'token', 'session_id', 'payload'}
                    or type(record['owner']) is not str
                    or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', record['owner'])
                    or type(record['token']) is not int
                    or not 0 < record['token'] < (1 << 63)
                    or not _consul_session_id(record['session_id'])):
                raise ValueError('control identity invalid')
            # A concurrent authority.close() can complete while this
            # consistent GET is in flight. Never return data from a closed
            # authority even if the original Consul response was valid.
            if self._closed:
                raise CoordinationUnavailable('Consul authority already closed')
            return record
        except (KeyError, TypeError, ValueError, IndexError):
            raise CoordinationUnavailable('control record invalid') from None
