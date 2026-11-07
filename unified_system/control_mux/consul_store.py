"""Control admission on existing Grid authority; no election or local authority.
First executable slice: OPERATOR OPEN and current-authorized reconciliation.
NODE delegation, streams, close containment and subscriptions are not admitted.
"""
import base64
from dataclasses import dataclass
import hashlib
import json
import uuid
from urllib.parse import quote
from .codec import PROFILE_SHA,decode,encode,validate
from .commands import prepare_open, PreparedCommand

class AuthorityUncertain(Exception):
    pass

@dataclass(frozen=True)
class Outcome:
    kind: str
    status: int | None = None
    body: bytes = b''
    receipt_index: int = 0

@dataclass(frozen=True)
class _Record:
    index: int
    raw: bytes | None


def _check(key,index):
    return {'KV':dict(Verb='check-index',Key=key,Index=index)} if index else {'KV':dict(Verb='check-not-exists',Key=key)}
def _cas(key,index,raw):
    if type(raw) is not bytes or len(raw)>32768:raise ValueError('RECORD_CAP')
    return {'KV':dict(Verb='cas',Key=key,Index=index,Value=base64.b64encode(raw).decode('ascii'))}

def _uuid(value):
    if type(value) is not str or str(uuid.UUID(value,version=4))!=value:raise ValueError('UUID')
    return value

class MuxAuthority:
    def __init__(self,authority,generation,*,admission=None):
        # authority is the existing qualified Grid ConsulSessionAuthority supplied
        # by trusted composition, not a caller-selected endpoint or KV gateway.
        self.authority=authority;self.generation=_uuid(generation);self.admission=admission
        self.prefix=authority.config.namespace+'/control-v3/'
        self.generation_key=authority.config.namespace+'/commands/generation'

    async def _read(self,key):
        try:rows=await self.authority._request('GET','/v1/kv/'+quote(key,safe='/'),params={'consistent':''},missing_ok=True)
        except Exception as exc:raise AuthorityUncertain() from exc
        if rows is None:return _Record(0,None)
        if type(rows) is not list or len(rows)!=1:raise ValueError('AMBIGUOUS_RECORD')
        row=rows[0]
        if type(row) is not dict or row.get('Key')!=key or type(row.get('ModifyIndex')) is not int or not 0<row['ModifyIndex']<2**63:
            raise ValueError('INVALID_NATIVE_RECORD')
        raw=base64.b64decode(row['Value'],validate=True)
        if len(raw)>32768:raise ValueError('RECORD_CAP')
        return _Record(row['ModifyIndex'],raw)

    async def _txn(self,ops,*,read_only=False):
        if not 0<len(ops)<=64:raise ValueError('TXN_OPERATION_CAP')
        if len(json.dumps(ops,separators=(',',':')).encode())>32768:raise ValueError('TXN_BYTE_CAP')
        try:result=await self.authority._request('PUT','/v1/txn',json=ops,**({'params':{'consistent':''}} if read_only else {}))
        except Exception as exc:raise AuthorityUncertain() from exc
        if type(result) is not dict or result.get('Errors'):raise ValueError('INVALID_TXN_RESULT')

    async def _identity(self,context,operation):
        if self.admission is None:raise ValueError('NATIVE_PROVIDER_UNAVAILABLE')
        from unified_system.security_identity_records import guard_keys,decode_guard_records
        current=self.admission.revalidate(context,operation)
        if current!=context:raise ValueError('NATIVE_CONTEXT_CHANGED')
        binding=self.admission.identity_binding(current)
        if (binding.cluster_id,binding.principal_id,binding.session_id)!=(context.cluster_id,context.actor_principal_id,context.actor_session_id):
            raise ValueError('NATIVE_BINDING_MISMATCH')
        if context.role!='OPERATOR_CONTROL' or context.quota_owner_id!=binding.principal_id:
            raise ValueError('QUOTA_OWNER_NOT_NATIVE_PRINCIPAL')
        if self.authority.config.namespace!='unified/'+binding.cluster_id:raise ValueError('AUTHORITY_CLUSTER_MISMATCH')
        keys=guard_keys(binding);records={};checks=[]
        for kind,key in keys.items():
            record=await self._read(key)
            if not record.index:raise ValueError('MISSING_IDENTITY_RECORD')
            records[kind]=record.raw;checks.append(_check(key,record.index))
        parsed=decode_guard_records(binding,records)
        if (parsed['policy']['role']!=context.role or operation not in parsed['policy']['permissions']
                or parsed['enrollment']['revision']!=context.enrollment_revision):raise ValueError('POLICY_MISMATCH')
        self.admission.verify_records(current,parsed)
        return checks

    async def _fence(self,leader,context):
        checks=await self._identity(context,'OPEN_CONNECTION')
        if not await self.authority.validate(leader):raise ValueError('LEADER_NOT_CURRENT')
        generation=await self._read(self.generation_key)
        if decode(generation.raw)!={'generation':self.generation}:raise ValueError('GENERATION_MISMATCH')
        return checks+[_check(self.generation_key,generation.index),
            {'KV':dict(Verb='check-session',Key=self.authority.key,Session=leader.session_id)},
            _check(self.authority.key,leader.token)]

    def _keys(self,request,keyhash,receipt):
        return (self.prefix+'requests/'+request,self.prefix+'commands/'+keyhash,
                self.prefix+'receipts/'+receipt,self.prefix+'responses/'+receipt)

    async def _observe(self,context,request,checks):
        indexkey=self.prefix+'requests/'+_uuid(request)
        index=await self._read(indexkey)
        if not index.index:
            await self._txn(checks+[_check(indexkey,0)],read_only=True)
            return Outcome('UNKNOWN')
        ix=validate('request_index',decode(index.raw))
        if ix['request_id']!=request or ix['cluster_id']!=context.cluster_id or ix['profile_schema_sha256']!=PROFILE_SHA:raise ValueError('INDEX_BINDING')
        if ix['quota_owner_id']!=context.quota_owner_id or ix['original_actor_principal_id']!=context.actor_principal_id:
            return Outcome('FORBIDDEN')
        keys=self._keys(request,ix['command_key_sha256'],ix['receipt_ref'])
        command,receipt,response=[await self._read(k) for k in keys[1:]]
        await self._txn(checks+[_check(k,r.index) for k,r in zip(keys,(index,command,receipt,response))],read_only=True)
        if not command.index:raise ValueError('MISSING_COMMAND')
        cmd=validate('stored_command',decode(command.raw));pre=validate('command_preimage',cmd['original_preimage'])
        if any(cmd[k]!=ix[k] for k in ('command_digest','command_key_sha256','request_id','receipt_ref')):raise ValueError('COMMAND_LINK')
        if any(pre[k]!=ix[k] for k in ('request_id','quota_owner_id','original_actor_principal_id','original_actor_session_id','profile_schema_sha256')):raise ValueError('PREIMAGE_LINK')
        if hashlib.sha256(encode(pre)).hexdigest()!=ix['command_digest']:raise ValueError('COMMAND_HASH')
        body=cmd['original_body_ascii'].encode('ascii')
        if hashlib.sha256(body).hexdigest()!=pre['canonical_body_sha256']:raise ValueError('BODY_HASH')
        key=dict(namespace_schema='unified.control.command-key.v3',cluster_id=context.cluster_id,quota_owner_id=ix['quota_owner_id'],original_actor_principal_id=ix['original_actor_principal_id'],idempotency_key=pre['idempotency_key'])
        if hashlib.sha256(encode(key)).hexdigest()!=ix['command_key_sha256']:raise ValueError('KEY_HASH')
        # Only this implemented operation may produce a successful result here.
        original=validate('open_request',decode(body))
        if (pre['operation']!='OPEN_CONNECTION' or pre['http_method']!='POST' or pre['canonical_path']!='/control/v3/connections'
                or any(pre[k] is not None for k in ('connection_id','subscription_id','snapshot_id','expected_connection_epoch','expected_subscription_epoch'))
                or original['request_id']!=request):raise ValueError('OPERATION_MISMATCH')
        if cmd['state']=='PENDING':
            if receipt.index or response.index or cmd['result_sha256'] is not None:raise ValueError('PENDING_CONTRADICTION')
            return Outcome('UNKNOWN')
        if cmd['state']!='COMPLETED' or not receipt.index or not response.index:raise ValueError('TERMINAL_EVIDENCE_MISSING')
        rc=validate('stored_receipt',decode(receipt.raw));result=validate('opened',decode(response.raw))
        if any(rc[k]!=ix[k] for k in ('receipt_ref','request_id','command_digest','command_key_sha256')):raise ValueError('RECEIPT_LINK')
        digest=hashlib.sha256(response.raw).hexdigest()
        if rc['http_status']!='201' or rc['result_schema_sha256']!=PROFILE_SHA or rc['canonical_response_sha256']!=digest or cmd['result_sha256']!=digest:raise ValueError('RECEIPT_RESULT')
        if (result['request_id']!=request or result['command_digest']!=ix['command_digest'] or result['quota_owner_ref']!=ix['quota_owner_id']
                or result['profile_schema_sha256']!=PROFILE_SHA or result['admitted_role']!=original['role']):raise ValueError('OPENED_BINDING')
        return Outcome('COMMITTED',201,response.raw,receipt.index)

    async def reconcile(self,context,request):
        try:return await self._observe(context,request,await self._identity(context,'GET_COMMAND'))
        except AuthorityUncertain:return Outcome('UNKNOWN')
        except Exception:return Outcome('UNAVAILABLE')

    async def _ledger(self,context):
        ledgerkey=self.prefix+'owners/'+context.quota_owner_id+'/connections'
        ledgerrecord=await self._read(ledgerkey)
        ledger=decode(ledgerrecord.raw) if ledgerrecord.index else dict(schema='unified.control.connection-ledger.v1',revision='0',connections=[])
        if set(ledger)!={'schema','revision','connections'} or ledger['schema']!='unified.control.connection-ledger.v1' or type(ledger['connections']) is not list or len(ledger['connections'])>2:raise ValueError('LEDGER_INVALID')
        revision=ledger['revision']
        if type(revision) is not str or not revision.isascii() or not revision.isdecimal() or str(int(revision))!=revision or not 0<=int(revision)<2**63-1:raise ValueError('REVISION_EXHAUSTED')
        for entry in ledger['connections']:
            if type(entry) is not dict or set(entry)!={'connection_id','connection_epoch','request_id','role','state'}:raise ValueError('LEDGER_ENTRY')
            _uuid(entry['connection_id']);_uuid(entry['request_id'])
            if entry['connection_epoch']!='1' or entry['role']!='OPERATOR_CONTROL' or entry['state'] not in ('PENDING','OPEN'):raise ValueError('LEDGER_ENTRY')
        if len({e['connection_id'] for e in ledger['connections']})!=len(ledger['connections']) or len({e['request_id'] for e in ledger['connections']})!=len(ledger['connections']):raise ValueError('LEDGER_DUPLICATE')
        return ledgerkey,ledgerrecord,ledger

    async def open(self,leader,context,command):
        if type(command) is not PreparedCommand:return Outcome('UNAVAILABLE')
        try:
            verified=prepare_open(context,command.body,command.request_id,decode(command.preimage)['idempotency_key'])
            if command!=verified:return Outcome('UNAVAILABLE')
        except Exception:return Outcome('UNAVAILABLE')
        try:
            # Reserved node slots need the separate qualified human-service delegation.
            if context.role!='OPERATOR_CONTROL':return Outcome('UNAVAILABLE')
            checks=await self._fence(leader,context)
            indexkey=self.prefix+'requests/'+command.request_id;commandkey=self.prefix+'commands/'+command.key_sha256
            index=await self._read(indexkey);stored=await self._read(commandkey)
            if index.index or stored.index:
                await self._txn(checks+[_check(indexkey,index.index),_check(commandkey,stored.index)],read_only=True)
                if not index.index or not stored.index:return Outcome('CONFLICT')
                ix=validate('request_index',decode(index.raw));cmd=validate('stored_command',decode(stored.raw))
                if ix['command_digest']!=command.digest or ix['command_key_sha256']!=command.key_sha256 or cmd['command_digest']!=command.digest or cmd['request_id']!=command.request_id:
                    return Outcome('CONFLICT')
                observed=await self._observe(context,command.request_id,checks)
                if observed.kind!='UNKNOWN':return observed
            else:
                ledgerkey,ledgerrecord,ledger=await self._ledger(context)
                if len(ledger['connections'])>=2:
                    await self._txn(checks+[_check(ledgerkey,ledgerrecord.index),_check(indexkey,0),_check(commandkey,0)],read_only=True)
                    return Outcome('UNAVAILABLE')
                reserved=dict(ledger,revision=str(int(ledger['revision'])+1),connections=ledger['connections']+[
                    dict(connection_id=str(uuid.uuid4()),connection_epoch='1',request_id=command.request_id,role=context.role,state='PENDING')])
                receipt=str(uuid.uuid4());pre=decode(command.preimage)
                ix=dict(schema='unified.control.request-index.v3',cluster_id=context.cluster_id,request_id=command.request_id,profile_schema_sha256=PROFILE_SHA,
                    quota_owner_id=context.quota_owner_id,original_actor_principal_id=context.actor_principal_id,original_actor_session_id=context.actor_session_id,
                    command_key_sha256=command.key_sha256,command_digest=command.digest,receipt_ref=receipt)
                cmd=dict(schema='unified.control.stored-command.v3',command_key_sha256=command.key_sha256,command_digest=command.digest,request_id=command.request_id,
                    receipt_ref=receipt,original_preimage=pre,original_body_ascii=command.body.decode('ascii'),state='PENDING',result_sha256=None)
                await self._txn(checks+[_cas(indexkey,0,encode(validate('request_index',ix))),_cas(commandkey,0,encode(validate('stored_command',cmd))),_cas(ledgerkey,ledgerrecord.index,encode(reserved))])
            # Re-read the durable original, never reconstruct a different intent after UNKNOWN.
            checks=await self._fence(leader,context);stored=await self._read(commandkey)
            if not stored.index:raise ValueError('LOST_PREPARED_COMMAND')
            cmd=validate('stored_command',decode(stored.raw))
            if cmd['state']!='PENDING':return await self._observe(context,command.request_id,checks)
            if cmd['command_digest']!=command.digest or cmd['original_body_ascii'].encode()!=command.body:raise ValueError('INTENT_MISMATCH')
            ledgerkey,ledgerrecord,ledger=await self._ledger(context)
            held=[entry for entry in ledger['connections'] if entry['request_id']==command.request_id]
            if len(held)!=1 or held[0]['state']!='PENDING':raise ValueError('PREPARATION_HOLD_MISSING')
            connection=held[0]['connection_id']
            opened=dict(schema='unified.control.connection-opened.v3',status='OPENED',request_id=command.request_id,command_digest=command.digest,
                connection_id=connection,connection_epoch='1',admitted_role=context.role,quota_owner_ref=context.quota_owner_id,profile_schema_sha256=PROFILE_SHA,
                csrf_policy_ref=context.csrf_policy_ref,initial_mux_cursor=str(uuid.uuid4()),initial_mux_sequence='0')
            result=encode(validate('opened',opened));digest=hashlib.sha256(result).hexdigest()
            receipt=cmd['receipt_ref'];keys=self._keys(command.request_id,command.key_sha256,receipt)
            rc=dict(schema='unified.control.stored-receipt.v3',receipt_ref=receipt,request_id=command.request_id,command_key_sha256=command.key_sha256,
                command_digest=command.digest,http_status='201',result_schema_sha256=PROFILE_SHA,canonical_response_sha256=digest)
            cmd=dict(cmd,state='COMPLETED',result_sha256=digest)
            ledger=dict(ledger,revision=str(int(ledger['revision'])+1),connections=[dict(entry,state='OPEN') if entry['request_id']==command.request_id else entry for entry in ledger['connections']])
            originalindex=await self._read(indexkey)
            if not originalindex.index or validate('request_index',decode(originalindex.raw))!=ix:raise ValueError('INDEX_CHANGED')
            await self._txn(checks+[_check(indexkey,originalindex.index),_cas(commandkey,stored.index,encode(cmd)),_cas(keys[2],0,encode(validate('stored_receipt',rc))),_cas(keys[3],0,result),_cas(ledgerkey,ledgerrecord.index,encode(ledger))])
            return await self._observe(context,command.request_id,await self._identity(context,'GET_COMMAND'))
        except Exception:
            # A timeout/409 is not rejection. Only original evidence may resolve it.
            result=await self.reconcile(context,command.request_id)
            if result.kind=='COMMITTED' and decode(result.body)['command_digest']!=command.digest:return Outcome('UNAVAILABLE')
            return result
