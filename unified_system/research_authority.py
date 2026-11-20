"""Root-owned authenticated negative research observation; never job permission.

Minimal extraction from Grid295 c9ffdaa authority_assignment_v1.py. No general
assignment/registration authority, worker, provider, store or native issuer.
"""
import base64,hashlib,json,re,uuid
from dataclasses import dataclass
from urllib.parse import quote
import httpx
from .authority_codec import canonical,measure_native_plan
from .consul_authority import ConsulSessionAuthority

class ResearchAuthorityUnavailable(RuntimeError):pass

def _uuid(value):
    if type(value) is not str:raise ValueError('UUID')
    try:valid=str(uuid.UUID(value,version=4))==value
    except ValueError:valid=False
    if not valid:raise ValueError('UUID')
    return value

@dataclass(frozen=True)
class CapturedRecord:
    key: str
    index: int
    raw: bytes|None
    session: str=''

def _decode(raw):
    def pairs(items):
        value={}
        for key,item in items:
            if key in value:raise ValueError('DUPLICATE_KEY')
            value[key]=item
        return value
    def number(_):raise ValueError('NUMBER_NOT_ALLOWED')
    if type(raw) is not bytes or not 0<len(raw)<=16384:raise ValueError('RECORD_CAP')
    depth=0;quoted=False;escaped=False
    for char in raw:
        if quoted:
            if escaped:escaped=False
            elif char==92:escaped=True
            elif char==34:quoted=False
        elif char==34:quoted=True
        elif char in (91,123):
            depth+=1
            if depth>12:raise ValueError('RECORD_DEPTH')
        elif char in (93,125):
            depth-=1
            if depth<0:raise ValueError('RECORD_JSON')
    value=json.loads(raw.decode('ascii'),object_pairs_hook=pairs,parse_int=number,parse_float=number,parse_constant=number)
    if type(value) is not dict or canonical(value)!=raw:raise ValueError('RECORD_CANONICAL')
    return value

class _ConsulSnapshot:
    def __init__(self,authority,generation):
        self.authority=authority;self.generation=_uuid(generation)
    async def _read_snapshot(self,keys):
        """Private one-Txn consistent facts, NOT identity/admission/closure proof.

        Public owners must derive their exact key set and check current rights.
        Missing at this snapshot is not proof an original never committed.
        """
        namespace=getattr(getattr(self.authority,'config',None),'namespace','')+'/'
        if (type(keys) is not tuple or not 1<=len(keys)<=64
                or any(type(k) is not str or not 1<=len(k)<=1024 or not k.startswith(namespace)
                       or re.fullmatch(r'[A-Za-z0-9_-]+(?:/[A-Za-z0-9_.:-]+)*',k) is None
                       or any(part in ('.','..') for part in k.split('/')) for k in keys)
                or len(set(keys))!=len(keys)):
            raise ValueError('SNAPSHOT_KEY_INVENTORY')
        if (type(self.authority) is not ConsulSessionAuthority or not self.authority._owns_client
                or type(self.authority.client) is not httpx.AsyncClient
                or type(self.authority.client._transport) is not httpx.AsyncHTTPTransport):
            raise ResearchAuthorityUnavailable('ACTUAL_CONSUL_SNAPSHOT_SOURCE_REQUIRED')
        result=await self._transaction([{'KV':dict(Verb='get-or-empty',Key=k)} for k in keys],read_only=True)
        if result.get('KnownLeader') is not True or result.get('ResultsFilteredByACLs') is not False:
            raise ResearchAuthorityUnavailable('CONSISTENT_UNFILTERED_SNAPSHOT_UNAVAILABLE')
        records=[]
        try:
            for key,item in zip(keys,result['Results'],strict=True):
                if set(item)!={'KV'} or type(item['KV']) is not dict:raise ValueError('SNAPSHOT_ROW')
                row=item['KV'];index=row['ModifyIndex'];created=row['CreateIndex']
                if (row.get('Key')!=key or type(index) is not int or not 0<=index<2**63
                        or type(created) is not int or not 0<=created<=index):raise ValueError('SNAPSHOT_INDEX')
                session=row.get('Session','')
                if type(session) is not str:raise ValueError('SNAPSHOT_SESSION')
                if session and str(uuid.UUID(session))!=session:raise ValueError('SNAPSHOT_SESSION')
                if index==0:
                    if created!=0 or row.get('Value') is not None or session:raise ValueError('SNAPSHOT_ABSENCE')
                    raw=None
                else:
                    if created==0 or type(row.get('Value')) is not str:raise ValueError('SNAPSHOT_VALUE')
                    raw=base64.b64decode(row['Value'],validate=True);_decode(raw)
                records.append(CapturedRecord(key,index,raw,session))
        except (ValueError,TypeError,KeyError,UnicodeError) as exc:
            raise ResearchAuthorityUnavailable('NATIVE_SNAPSHOT_ENCODING') from exc
        return tuple(records)
    async def _transaction(self,operations,*,read_only=False):
        measure_native_plan(operations) # actual64op/32768encoded limit, not proof.
        result=await self.authority._request('PUT','/v1/txn',json=operations,**({'params':{'consistent':''}} if read_only else {}))
        if (type(result) is not dict or result.get('Errors') or type(result.get('Results')) is not list
                or len(result['Results'])!=len(operations) or any(type(item) is not dict for item in result['Results'])):
            raise ResearchAuthorityUnavailable('NATIVE_TRANSACTION_OUTCOME_UNKNOWN')
        return result

@dataclass(frozen=True)
class ResearchAdmissionResult:
    """NEGATIVE_PATH observation DATA, never a receipt or execution capability."""
    outcome: str
    reason: str
    original_intent_sha256: str
    commit_status: str='NOT_ATTEMPTED'
    effect_permitted: bool=False

class ResearchLabAuthority:
    """Internal authenticated negative path over the Unified-owned Consul authority.

    No job writes, queue, second broker, resource proof or positive permission.
    Existing committed jobs are deliberately UNKNOWN until a qualified resolver
    checks their full original/receipt/assignment/phase dependencies.
    """
    def __init__(self,authority,generation,*,broker):
        from unified_system.gateway_research_identity import ResearchIdentityBroker
        if (type(authority) is not ConsulSessionAuthority or type(broker) is not ResearchIdentityBroker
                or broker._authority is not authority or broker._generation!=generation):
            raise TypeError('ACTUAL_SAME_AUTHORITY_RESEARCH_BROKER_REQUIRED')
        self._native=_ConsulSnapshot(authority,generation)
        self._broker=broker

    async def _observe(self,original,*,context,scope,leader=None):
        from unified_system.gateway_research_identity import ResearchIdentityBroker
        command=_decode(original)
        fields={'schema','operation','cluster_id','cluster_generation','request_id','job_id',
                'original_actor_principal_id','quota_owner_id','idempotency_key',
                'commissioned_profile_sha256','input_request_sha256','producer_head','math_head','resources'}
        if (set(command)!=fields or command['schema']!='unified.gateway.canonical-job-submit.v2'
                or command['operation']!='SUBMIT_RESEARCH'):
            raise ValueError('EXACT_CANONICAL_ORIGINAL_REQUIRED')
        authority=self._native.authority
        if scope=='SUBMIT_RESEARCH' and not await authority.validate(leader):
            raise ResearchAuthorityUnavailable('CURRENT_AUTHORITY_LEASE_REQUIRED')
        capture=await ResearchIdentityBroker.capture_current(self._broker,context,scope=scope,request_bytes=original)
        identity=ResearchIdentityBroker.require_capture(self._broker,capture,expected_authority=authority,scope=scope,request_bytes=original)
        profile=_decode(identity.records[1].raw)
        if (profile.get('schema')!='unified.authority.canonical-research-profile.v3'
                or profile.get('cluster_id')!=command['cluster_id']
                or command['cluster_generation']!=self._native.generation
                or identity.actor_id!=command['original_actor_principal_id']
                or identity.quota_owner_id!=command['quota_owner_id']
                or identity.profile_sha256!=command['commissioned_profile_sha256']):
            raise ResearchAuthorityUnavailable('CURRENT_TARGET_BOUND_PROFILE_REQUIRED')
        realm=_uuid(profile['realm_id']);job=_uuid(command['job_id'])
        namespace=authority.config.namespace
        if namespace!='unified/'+_uuid(command['cluster_id']):raise ValueError('CLUSTER_BINDING')
        job_key=namespace+'/runtime-v2/canonical-research-v3/'+realm+'/jobs/'+job
        keys=tuple(r.key for r in identity.records)
        generation_key=namespace+'/commands/generation'
        if generation_key not in keys:raise ResearchAuthorityUnavailable('CURRENT_GENERATION_SOURCE_REQUIRED')
        rows=await self._native._read_snapshot(keys+(authority.key,job_key))
        for current,prior in zip(rows,identity.records):
            if (current.key,current.index,current.raw,current.session)!=(prior.key,prior.index,prior.raw,prior.session):
                raise ResearchAuthorityUnavailable('CURRENT_IDENTITY_SNAPSHOT_CHANGED')
        if _decode(rows[keys.index(generation_key)].raw)!={'generation':self._native.generation}:
            raise ResearchAuthorityUnavailable('GENERATION_NOT_CURRENT')
        if scope=='SUBMIT_RESEARCH':
            lock=rows[-2]
            if lock.index!=leader.token or lock.session!=leader.session_id or not await authority.validate(leader):
                raise ResearchAuthorityUnavailable('CURRENT_AUTHORITY_LEASE_REQUIRED')
        # Recheck the actual fixed issuer, exact original and local peer/expiry
        # after all awaits; this does not establish Raft commit-time UTC.
        ResearchIdentityBroker.require_capture(self._broker,capture,expected_authority=authority,scope=scope,request_bytes=original)
        return rows[-1]

    async def submit(self,original_request_bytes,*,context,leader,owned_attempt=None):
        job=await self._observe(original_request_bytes,context=context,scope='SUBMIT_RESEARCH',leader=leader)
        # No caller-supplied attempt/boolean/method shape can bypass this gate.
        reason='JOB_RECONCILIATION_API_UNQUALIFIED' if job.index else 'NATIVE_WORKER_RESOURCE_API_UNQUALIFIED'
        return ResearchAdmissionResult('UNKNOWN' if job.index else 'DENIED',reason,hashlib.sha256(original_request_bytes).hexdigest())

    async def lookup(self,original_request_bytes,*,context):
        await self._observe(original_request_bytes,context=context,scope='READ_RESEARCH')
        # Snapshot absence is not never-committed evidence. Do not manufacture a
        # NOT_FOUND receipt or expose arbitrary native job record payloads.
        return ResearchAdmissionResult('UNKNOWN','JOB_RECONCILIATION_API_UNQUALIFIED',hashlib.sha256(original_request_bytes).hexdigest())

