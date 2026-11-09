"""Actual disposable mTLS + Consul principal session; never a job/worker grant.

Root owns certificate/key load+client pin, real ACL provisioning and source capsule.
No READ capability upgrade, standalone ledger, source callback or human identity.
"""
import asyncio
import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
import ssl
import time
import uuid
from urllib.parse import quote
from cryptography import x509
from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes
from cryptography.x509.oid import ExtendedKeyUsageOID
import httpx
from .gateway_identity import GatewayAuditSink, GatewayIdentityUnavailable

try:
    from grid.coordination import ConsulSessionAuthority, CoordinationUnavailable
    from grid.authority_runtime_v1 import canonical, measure_native_plan
except ImportError:
    ConsulSessionAuthority = None

SCOPES=frozenset(('SUBMIT_RESEARCH','READ_RESEARCH','CANCEL_OWN_JOB'))
_PROFILE_V2='unified.authority.target-bound-research-profile.v2-review1'
_TARGET_SCHEMA_SHA='faf01152678c5b066145dcafebe92f593a641a54dac84da3ce1e1df94c0fb261'
_INPUT_SHA='c548e2ffcd542d5d741682303694b3c6d06507740f158a6e30089b2d5355f648'
_PRODUCER='aed8a7c8a952f96803c207d5e90b133969a47f04'

class ResearchIdentityDenied(RuntimeError): pass
class ResearchIdentityUnavailable(RuntimeError): pass

def _require(value):
    if not value: raise ResearchIdentityDenied('RESEARCH_IDENTITY_DENIED')
def _uuid(value):
    _require(type(value) is str and re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}',value) is not None)
def _native_session(value):
    # Consul session IDs are canonical UUID strings, not guaranteed UUIDv4.
    _require(type(value) is str and re.fullmatch(r'[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}',value) is not None)
    _require(str(uuid.UUID(value))==value)
def _sha(value):
    _require(type(value) is str and re.fullmatch(r'[0-9a-f]{64}',value) is not None)
def _id(value):
    _require(type(value) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}',value) is not None)
def _fields(value,names): _require(type(value) is dict and set(value)==set(names.split()))
def _utc(): return datetime.now(timezone.utc).timestamp()
def _expiry(value):
    _require(type(value) is str and re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z',value) is not None)
    return datetime.strptime(value,'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp()
def _decode(raw):
    _require(type(raw) is bytes and 0<len(raw)<=16384)
    def pairs(items):
        result={}
        for key,value in items:
            _require(key not in result);result[key]=value
        return result
    def number(_): raise ValueError('NATIVE_METADATA_NUMBER')
    value=json.loads(raw.decode('ascii'),object_pairs_hook=pairs,parse_int=number,parse_float=number,parse_constant=number)
    _require(type(value) is dict and canonical(value)==raw)
    return value

def _lab_id(value):
    _require(type(value) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,128}',value) is not None)

def _decode_target(raw):
    """Separate target codec retains numeric input caps; never native C3 coercion."""
    _require(type(raw) is bytes and 0<len(raw)<=16384)
    depth=0;quoted=False;escaped=False
    for char in raw:
        if quoted:
            if escaped:escaped=False
            elif char==92:escaped=True
            elif char==34:quoted=False
        elif char==34:quoted=True
        elif char in (91,123):
            depth+=1;_require(depth<=12)
        elif char in (93,125):
            depth-=1;_require(depth>=0)
    _require(depth==0 and not quoted)
    def pairs(items):
        result={}
        for key,value in items:
            _require(key not in result);result[key]=value
        return result
    def constant(_):raise ValueError('TARGET_NONFINITE_NUMBER')
    value=json.loads(raw.decode('ascii'),object_pairs_hook=pairs,parse_constant=constant)
    _require(type(value) is dict and json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')==raw)
    return value

def _target_binding(profile,*,generation,actor,quota_owner):
    """Data joins for actual commissioned profile, not resource/job qualification."""
    binding=profile['target_binding']
    _fields(binding,'target_request_schema_sha256 target_request_canonical_base64 target_request_sha256 request_id job_id idempotency_key cluster_generation actor_principal_id quota_owner_id producer_request_sha256 producer_head')
    _require(binding['target_request_schema_sha256']==_TARGET_SCHEMA_SHA)
    _sha(binding['target_request_sha256'])
    encoded=binding['target_request_canonical_base64']
    _require(type(encoded) is str and 0<len(encoded)<=21848)
    raw=base64.b64decode(encoded,validate=True)
    _require(base64.b64encode(raw).decode('ascii')==encoded and hashlib.sha256(raw).hexdigest()==binding['target_request_sha256'])
    target=_decode_target(raw)
    _fields(target,'schema request_id target_kind target_capability target_version dataset_manifest_id dataset_revision experiment_id strategy_version parameters_digest execution_mode resource_budget quota_owner principal_id authority_generation assignment_revision fencing_token idempotency_key result_schema result_artifact_ref')
    expected=dict(schema='unified.gateway.target-native-request.v1-review1',target_kind='MetaAnalyse',
        target_capability='meta.ohlcv.untouched_levels.v1',target_version='f3c01a23fa5baaeeeb28eb8e9397e72b5ef4d5a1',
        dataset_manifest_id='local-sha256:33d5bf0f918884c8908795b384e0964a48a1351c808800964b8cacf3f83e28b6',
        dataset_revision='LOCAL_FIXTURE_1',experiment_id='fixture.gateway.btc.levels',strategy_version=None,
        parameters_digest=_INPUT_SHA,execution_mode='NATIVE_RESEARCH_ADMISSION_REQUEST_NOT_PERMISSION',
        assignment_revision=None,fencing_token=None,result_schema='unified.gateway.native-target-observation.v1-review1',result_artifact_ref=None)
    for key,value in expected.items():
        _require(type(target[key]) is type(value) and target[key]==value)
    caps=target['resource_budget'];_fields(caps,'max_input_bytes max_output_bytes max_rows max_executions')
    for key,value in dict(max_input_bytes=16384,max_output_bytes=16384,max_rows=3,max_executions=1).items():
        _require(type(caps[key]) is int and caps[key]==value)
    for key in ('request_id','job_id','cluster_generation','actor_principal_id'):_uuid(binding[key])
    _lab_id(binding['idempotency_key']);_lab_id(binding['quota_owner_id'])
    _require(binding['cluster_generation']==generation==target['authority_generation'])
    _require(binding['actor_principal_id']==actor==target['principal_id'])
    _require(binding['quota_owner_id']==quota_owner==target['quota_owner'])
    _require(binding['request_id']==target['request_id'] and binding['idempotency_key']==target['idempotency_key'])
    _require(binding['producer_request_sha256']==profile['input_request_sha256']==_INPUT_SHA)
    _require(binding['producer_head']==profile['producer_head']==_PRODUCER)
    _require(len(profile['principal_registry'])==1)
    return binding

def _profile_request(profile,profile_sha,*,scope,raw):
    """Bind current identity capture to the ONE original; never issue a job."""
    b=profile['target_binding']
    submit=dict(schema='unified.gateway.lab-job-submit.v1-review1',operation='SUBMIT_RESEARCH',
        cluster_id=profile['cluster_id'],cluster_generation=b['cluster_generation'],request_id=b['request_id'],
        job_id=b['job_id'],original_actor_principal_id=b['actor_principal_id'],quota_owner_id=b['quota_owner_id'],
        idempotency_key=b['idempotency_key'],commissioned_profile_sha256=profile_sha,
        input_request_sha256=profile['input_request_sha256'],producer_head=profile['producer_head'],resources=profile['resources'])
    if scope in ('SUBMIT_RESEARCH','READ_RESEARCH'):
        _require(raw==canonical(submit))
        return
    cancel=_decode(raw)
    _fields(cancel,'schema operation cluster_id cluster_generation request_id job_id original_actor_principal_id quota_owner_id idempotency_key commissioned_profile_sha256 original_submit_request_id original_submit_intent_sha256')
    _uuid(cancel['request_id']);_lab_id(cancel['idempotency_key'])
    _require(cancel['request_id']!=b['request_id'])
    expected=dict(schema='unified.gateway.lab-job-cancel.v1-review1',operation='CANCEL_OWN_JOB',
        cluster_id=profile['cluster_id'],cluster_generation=b['cluster_generation'],job_id=b['job_id'],
        original_actor_principal_id=b['actor_principal_id'],quota_owner_id=b['quota_owner_id'],
        commissioned_profile_sha256=profile_sha,original_submit_request_id=b['request_id'],
        original_submit_intent_sha256=hashlib.sha256(canonical(submit)).hexdigest())
    for key,value in expected.items():_require(cancel[key]==value)
def _leaf(cert,eku,uri=None):
    _require(not cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca)
    _require(list(cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value)==[eku])
    names=list(cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value)
    if uri is None:
        _require(len(names)==1 and type(names[0]) is x509.IPAddress and str(names[0].value)=='127.0.0.1')
    else:
        _require(len(names)==1 and type(names[0]) is x509.UniformResourceIdentifier and names[0].value==uri)

@dataclass(frozen=True)
class ResearchNativeRecord:
    key: str
    index: int
    raw: bytes
    session: str

@dataclass(frozen=True)
class ResearchIdentitySnapshot:
    actor_id: str
    service_id: str
    quota_owner_id: str
    session_id: str
    policy_id: str
    profile_sha256: str
    records: tuple

class ResearchPrincipalContext:
    __slots__=()
    def __new__(cls): raise TypeError('BROKER_ONLY_CONTEXT')
    def __copy__(self): raise TypeError('CONTEXT_NOT_COPYABLE')
    def __deepcopy__(self,memo): raise TypeError('CONTEXT_NOT_COPYABLE')
    def __reduce__(self): raise TypeError('CONTEXT_NOT_SERIALIZABLE')
class ResearchIdentityCapture(ResearchPrincipalContext):
    __slots__=()

class ResearchIdentityBroker:
    def __init__(self,*,authority,generation,realm_id,profile_sha256,server_ssl_context,server_certificate_der,audit_sink):
        if (ConsulSessionAuthority is None or type(authority) is not ConsulSessionAuthority
                or not authority._owns_client or type(authority.client) is not httpx.AsyncClient
                or type(authority.client._transport) is not httpx.AsyncHTTPTransport
                or not authority.config.isolated_lab or not authority.config.acl_token
                or type(audit_sink) is not GatewayAuditSink):
            raise ResearchIdentityUnavailable('QUALIFIED_DISPOSABLE_SOURCE_UNAVAILABLE')
        self._authority=authority;self._audit=audit_sink
        self._contexts={};self._captures={};self._sessions=set();self._invalid=set()
        self._operations_lock=asyncio.Lock()
        self._wall=_utc();self._mono=time.monotonic();self._last_wall=self._wall;self._last_mono=self._mono
        self._poisoned=False;self._closed=False
        try:
            _uuid(generation);_uuid(realm_id);_sha(profile_sha256)
            namespace=authority.config.namespace
            _require(namespace.startswith('unified/'));_uuid(namespace[8:])
            self._cluster=namespace[8:];self._namespace=namespace;self._generation=generation
            self._realm=realm_id;self._profile_sha=profile_sha256
            self._prefix=namespace+'/runtime-v1/research-lab-v1/'+realm_id+'/'
            _require(type(server_ssl_context) is ssl.SSLContext and server_ssl_context.protocol==ssl.PROTOCOL_TLS_SERVER)
            _require(server_ssl_context.verify_mode==ssl.CERT_REQUIRED and server_ssl_context.minimum_version>=ssl.TLSVersion.TLSv1_2)
            self._ssl=server_ssl_context
            cas=server_ssl_context.get_ca_certs(binary_form=True);_require(len(cas)==1)
            self._ca=x509.load_der_x509_certificate(cas[0])
            _require(type(server_certificate_der) is bytes)
            server=x509.load_der_x509_certificate(server_certificate_der)
            server.verify_directly_issued_by(self._ca);_leaf(server,ExtendedKeyUsageOID.SERVER_AUTH)
            self._server_expiry=server.not_valid_after_utc.timestamp()
            _require(server.not_valid_before_utc.timestamp()<=self._wall<self._server_expiry)
        except (ResearchIdentityDenied,ValueError,TypeError,x509.ExtensionNotFound,InvalidSignature,UnsupportedAlgorithm) as exc:
            raise ResearchIdentityUnavailable('DISPOSABLE_COMMISSIONING_UNAVAILABLE') from exc
    def _clock(self):
        wall,mono=_utc(),time.monotonic()
        if (self._closed or self._poisoned or wall<self._last_wall or mono<self._last_mono
                or wall-self._wall<mono-self._mono-1):
            self._poisoned=True
            raise ResearchIdentityUnavailable('CLOCK_OR_SOURCE_UNAVAILABLE')
        self._last_wall,self._last_mono=wall,mono
        return wall,mono
    def _emit(self,decision):
        try:
            self._audit._append(dict(schema='unified.gateway.research-identity-audit.v1',realm_id=self._realm,decision=decision))
        except GatewayIdentityUnavailable:
            raise ResearchIdentityUnavailable('AUDIT_SOURCE_UNAVAILABLE') from None
    def _peer(self,sock):
        wall,_=self._clock()
        _require(type(sock) is ssl.SSLSocket and sock.context is self._ssl and sock.server_side and sock.fileno()>=0)
        raw=sock.getpeercert(binary_form=True);_require(type(raw) is bytes)
        cert=x509.load_der_x509_certificate(raw);cert.verify_directly_issued_by(self._ca)
        names=list(cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value)
        _require(len(names)==1 and type(names[0]) is x509.UniformResourceIdentifier)
        uri=names[0].value;prefix='urn:unified:test:research-service:'
        _require(uri.startswith(prefix));service=uri[len(prefix):];_uuid(service)
        _leaf(cert,ExtendedKeyUsageOID.CLIENT_AUTH,uri)
        expiry=min(cert.not_valid_after_utc.timestamp(),self._server_expiry)
        _require(cert.not_valid_before_utc.timestamp()<=wall<expiry)
        return hashlib.sha256(raw).hexdigest(),service,expiry
    async def _read(self,key):
        try:
            rows=await self._authority._request('GET','/v1/kv/'+quote(key,safe='/'),params={'consistent':''},missing_ok=True)
        except CoordinationUnavailable:
            raise ResearchIdentityUnavailable('NATIVE_IDENTITY_SOURCE_UNAVAILABLE') from None
        if type(rows) is not list or len(rows)!=1: raise ResearchIdentityUnavailable('NATIVE_IDENTITY_RECORD_UNAVAILABLE')
        row=rows[0]
        _require(type(row) is dict and row.get('Key')==key and type(row.get('ModifyIndex')) is int and 0<row['ModifyIndex']<2**63)
        value=base64.b64decode(row['Value'],validate=True);_decode(value)
        session=row.get('Session','');_require(type(session) is str)
        return ResearchNativeRecord(key,row['ModifyIndex'],value,session)
    async def _policy(self,fingerprint,service):
        generation=await self._read(self._namespace+'/commands/generation')
        _require(_decode(generation.raw)=={'generation':self._generation})
        profile=await self._read(self._prefix+'profile-registry/'+self._profile_sha)
        _require(hashlib.sha256(profile.raw).hexdigest()==self._profile_sha)
        p=_decode(profile.raw)
        profile_fields='schema cluster_id realm_id principal_registry input_request_sha256 producer_head resources expiry_semantics expires_utc'
        v2=p.get('schema')==_PROFILE_V2
        _fields(p,profile_fields+(' target_binding' if v2 else ''))
        _require(p['schema'] in ('unified.authority.research-lab-profile.v1-review1',_PROFILE_V2) and p['cluster_id']==self._cluster and p['realm_id']==self._realm)
        _require(p['expiry_semantics']=='NATIVE_SESSION_INVALIDATION_NOT_UTC_AT_COMMIT')
        _require(type(p['principal_registry']) is dict and 1<=len(p['principal_registry'])<=32)
        for key,value in p['principal_registry'].items(): _sha(key);_uuid(value)
        _require(p['input_request_sha256']=='c548e2ffcd542d5d741682303694b3c6d06507740f158a6e30089b2d5355f648')
        _require(p['producer_head']=='aed8a7c8a952f96803c207d5e90b133969a47f04')
        _require(p['resources']=={'cpu_millicores':'1000','resident_memory_bytes':'268435456','max_artifact_bytes':'1048576'})
        actor=p['principal_registry'].get(fingerprint);_require(actor is not None)
        principal=await self._read(self._prefix+'principals/'+actor);a=_decode(principal.raw)
        _fields(a,'schema actor_id service_id certificate_sha256 quota_owner_id policy_id profile_sha256 state')
        _require(a['schema']=='unified.authority.research-lab-principal.v1-review1' and a['actor_id']==actor
                 and a['service_id']==service and a['certificate_sha256']==fingerprint and a['profile_sha256']==self._profile_sha and a['state']=='ACTIVE')
        _id(a['quota_owner_id']);_uuid(a['policy_id'])
        if v2:_target_binding(p,generation=self._generation,actor=actor,quota_owner=a['quota_owner_id'])
        policy=await self._read(self._prefix+'policies/'+a['policy_id']);r=_decode(policy.raw)
        _fields(r,'schema policy_id actor_id profile_sha256 revision state scopes expires_utc')
        _require(r['schema']=='unified.authority.research-lab-policy.v1-review1' and r['policy_id']==a['policy_id']
                 and r['actor_id']==actor and r['profile_sha256']==self._profile_sha and r['state']=='ACTIVE')
        revision=r['revision'];_require(type(revision) is str and re.fullmatch('[1-9][0-9]{0,18}',revision) is not None and int(revision)<2**63)
        scopes=r['scopes'];_require(type(scopes) is list and 1<=len(scopes)<=3 and all(type(s) is str and s in SCOPES for s in scopes) and scopes==sorted(set(scopes)))
        expiry=min(_expiry(p['expires_utc']),_expiry(r['expires_utc']))
        wall,_=self._clock();_require(wall<expiry<=self._wall+900)
        return (generation,profile,principal,policy),a,r,expiry
    @staticmethod
    def _check(record): return {'KV':dict(Verb='check-index',Key=record.key,Index=record.index)}
    async def open_session(self,server_ssl_socket,*,leader):
        try:
            async with self._operations_lock:
                return await self._open_session(server_ssl_socket,leader=leader)
        except (ResearchIdentityDenied,ResearchIdentityUnavailable): raise
        except Exception:
            raise ResearchIdentityUnavailable('PRINCIPAL_SESSION_OUTCOME_UNKNOWN') from None
    async def _open_session(self,server_ssl_socket,*,leader):
        if len(self._contexts)>=128 or len(self._sessions)>=128: raise ResearchIdentityUnavailable('CONTEXT_CAPACITY')
        session_id=None
        try:
            fingerprint,service,cert_expiry=self._peer(server_ssl_socket)
            records,a,r,policy_expiry=await self._policy(fingerprint,service)
            _require(await self._authority.validate(leader))
            self._emit('PRINCIPAL_SESSION_BEGIN')
            started=time.monotonic()
            created=await self._authority._request('PUT','/v1/session/create',json={
                'Name':'research-principal-'+a['actor_id'],'TTL':'10s','Behavior':'release','LockDelay':'0s','NodeChecks':[]})
            session_id=created['ID'];_native_session(session_id);self._sessions.add(session_id)
            key=self._prefix+'principal-sessions/'+session_id+'/lock'
            body=dict(schema='unified.authority.research-lab-principal-session.v1-review1',actor_id=a['actor_id'],
                service_id=service,certificate_sha256=fingerprint,session_id=session_id,policy_id=a['policy_id'],
                profile_sha256=self._profile_sha,quota_owner_id=a['quota_owner_id'])
            operations=[self._check(record) for record in records]+[
                {'KV':dict(Verb='check-index',Key=self._authority.key,Index=leader.token)},
                {'KV':dict(Verb='check-session',Key=self._authority.key,Session=leader.session_id)},
                {'KV':dict(Verb='check-not-exists',Key=key)},
                {'KV':dict(Verb='lock',Key=key,Session=session_id,Value=base64.b64encode(canonical(body)).decode('ascii'))}]
            measure_native_plan(operations)
            result=await self._authority._request('PUT','/v1/txn',json=operations)
            _require(type(result) is dict and not result.get('Errors') and type(result.get('Results')) is list)
            lock=await self._read(key);_require(lock.session==session_id and lock.raw==canonical(body))
            fingerprint2,service2,cert_expiry2=self._peer(server_ssl_socket)
            _require((fingerprint,service)==(fingerprint2,service2))
            expiry=min(cert_expiry,cert_expiry2,policy_expiry)
            wall,mono=self._clock()
            deadline=min(started+9,mono+expiry-wall)
            _require(wall<expiry and mono<deadline)
            self._emit('PRINCIPAL_SESSION_CONFIRMED')
            context=object.__new__(ResearchPrincipalContext)
            self._contexts[context]=(server_ssl_socket,fingerprint,service,session_id,deadline,a['actor_id'],a['policy_id'],a['quota_owner_id'],expiry)
            return context
        except BaseException:
            if session_id:
                self._invalid.add(session_id)
                try:
                    destroyed=await self._authority._request('PUT','/v1/session/destroy/'+session_id)
                    if destroyed is True:
                        self._sessions.discard(session_id);self._invalid.discard(session_id)
                except Exception: pass
            raise
    def _context(self,context):
        _require(type(context) is ResearchPrincipalContext and context in self._contexts)
        state=self._contexts[context];wall,mono=self._clock()
        _require(state[3] not in self._invalid and mono<state[4] and wall<state[8])
        fingerprint,service,_=self._peer(state[0]);_require((fingerprint,service)==(state[1],state[2]))
        return state
    async def capture_current(self,context,*,scope,request_bytes):
        try:
            async with self._operations_lock:
                return await self._capture_current(context,scope=scope,request_bytes=request_bytes)
        except (ResearchIdentityDenied,ResearchIdentityUnavailable): raise
        except Exception:
            raise ResearchIdentityUnavailable('CURRENT_IDENTITY_UNAVAILABLE') from None
    async def _capture_current(self,context,*,scope,request_bytes):
        _require(type(scope) is str and scope in SCOPES and type(request_bytes) is bytes and 0<len(request_bytes)<=16384)
        if len(self._captures)>=256: raise ResearchIdentityUnavailable('CAPTURE_CAPACITY')
        state=self._context(context)
        records,a,r,policy_expiry=await self._policy(state[1],state[2]);_require(scope in r['scopes'])
        profile=_decode(records[1].raw)
        if profile['schema']==_PROFILE_V2:_profile_request(profile,self._profile_sha,scope=scope,raw=request_bytes)
        _require((a['actor_id'],a['policy_id'],a['quota_owner_id'])==(state[5],state[6],state[7]))
        lock=await self._read(self._prefix+'principal-sessions/'+state[3]+'/lock')
        expected=dict(schema='unified.authority.research-lab-principal-session.v1-review1',actor_id=state[5],
            service_id=state[2],certificate_sha256=state[1],session_id=state[3],policy_id=state[6],profile_sha256=self._profile_sha,quota_owner_id=state[7])
        _require(lock.session==state[3] and lock.raw==canonical(expected))
        self._context(context);self._emit('CURRENT_RESEARCH_IDENTITY')
        wall,mono=self._clock();expiry=min(state[8],policy_expiry)
        deadline=min(state[4],mono+expiry-wall)
        _require(wall<expiry and mono<deadline)
        snapshot=ResearchIdentitySnapshot(state[5],state[2],state[7],state[3],state[6],self._profile_sha,records+(lock,))
        capture=object.__new__(ResearchIdentityCapture)
        self._captures[capture]=(context,scope,hashlib.sha256(request_bytes).digest(),snapshot,expiry,deadline)
        return capture
    def require_capture(self,capture,*,expected_authority,scope,request_bytes):
        _require(type(self) is ResearchIdentityBroker and self._authority is expected_authority)
        _require(type(scope) is str and scope in SCOPES and type(request_bytes) is bytes and 0<len(request_bytes)<=16384)
        _require(type(capture) is ResearchIdentityCapture and capture in self._captures)
        context,original_scope,digest,snapshot,expiry,deadline=self._captures[capture]
        self._context(context)
        wall,mono=self._clock();_require(wall<expiry and mono<deadline)
        _require(type(request_bytes) is bytes and scope==original_scope and hashlib.sha256(request_bytes).digest()==digest)
        return snapshot
    async def invalidate_context(self,context):
        _require(type(context) is ResearchPrincipalContext and context in self._contexts)
        session=self._contexts[context][3];self._invalid.add(session)
        try:
            self._emit('PRINCIPAL_SESSION_INVALIDATED')
        finally:
            # Audit backpressure cannot prevent best-effort native invalidation.
            try: await self._authority._request('PUT','/v1/session/destroy/'+session)
            except CoordinationUnavailable:
                raise ResearchIdentityUnavailable('NATIVE_INVALIDATION_UNKNOWN') from None
    async def close(self):
        # Latch before waiting: in-flight operations must fail their final check.
        self._closed=True
        async with self._operations_lock:
            self._invalid.update(self._sessions)
            for session in tuple(self._sessions):
                try:
                    destroyed=await self._authority._request('PUT','/v1/session/destroy/'+session)
                    if destroyed is True: self._sessions.discard(session)
                except Exception: pass
