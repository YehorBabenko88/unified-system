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
from .codec import PROFILE_SHA,decode,encode,validate,matrix
from .reconciliation import build_document,require_fit
from .commands import prepare_open, prepare_close, prepare_subscribe, prepare_ack, validate_original, PreparedCommand, NativeAdmissionError, native_admission_kind, AdmittedContext

class _ReadNativeDenial(Exception):
    def __init__(self,kind):self.kind=kind


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

    async def _identity(self,context,operation,*,read_disclosure=False):
        if self.admission is None:raise ValueError('NATIVE_PROVIDER_UNAVAILABLE')
        from unified_system.security_identity_records import guard_keys,decode_guard_records
        def native_call(name,*args):
            if not read_disclosure:return getattr(self.admission,name)(*args)
            try:return getattr(self.admission,name)(*args)
            except NativeAdmissionError as exc:raise _ReadNativeDenial(native_admission_kind(exc)) from None
            except Exception:raise _ReadNativeDenial('UNAVAILABLE') from None
        current=native_call('revalidate',context,operation)
        if (read_disclosure and type(current) is not AdmittedContext) or current!=context:raise ValueError('NATIVE_CONTEXT_CHANGED')
        binding=native_call('identity_binding',current)
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
        if read_disclosure:
            # Verify actual current native session before classifying a valid
            # session's missing read permission. Other identity mismatches deny.
            if native_call('verify_records',current,parsed) is not None:raise ValueError('NATIVE_VERIFIER_CONTRACT')
            if parsed['policy']['role']!=context.role or parsed['enrollment']['revision']!=context.enrollment_revision:raise ValueError('POLICY_MISMATCH')
            if operation not in parsed['policy']['permissions']:raise _ReadNativeDenial('FORBIDDEN')
        else:
            if (parsed['policy']['role']!=context.role or operation not in parsed['policy']['permissions']
                    or parsed['enrollment']['revision']!=context.enrollment_revision):raise ValueError('POLICY_MISMATCH')
            if self.admission.verify_records(current,parsed) is not None:raise ValueError('NATIVE_VERIFIER_CONTRACT')
        return checks

    async def _fence(self,leader,context,operation='OPEN_CONNECTION'):
        checks=await self._identity(context,operation)
        if not await self.authority.validate(leader):raise ValueError('LEADER_NOT_CURRENT')
        generation=await self._read(self.generation_key)
        if decode(generation.raw)!={'generation':self.generation}:raise ValueError('GENERATION_MISMATCH')
        return checks+[_check(self.generation_key,generation.index),
            {'KV':dict(Verb='check-session',Key=self.authority.key,Session=leader.session_id)},
            _check(self.authority.key,leader.token)]

    def _keys(self,request,keyhash,receipt):
        return (self.prefix+'requests/'+request,self.prefix+'commands/'+keyhash,
                self.prefix+'receipts/'+receipt,self.prefix+'responses/'+receipt)

    async def _observe(self,context,request,checks,*,query_request_id=None):
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
        original=validate_original(pre,body)
        if cmd['state']=='PENDING':
            if receipt.index or response.index or cmd['result_sha256'] is not None:raise ValueError('PENDING_CONTRADICTION')
            return Outcome('UNKNOWN')
        if not receipt.index or not response.index:raise ValueError('TERMINAL_EVIDENCE_MISSING')
        rc=validate('stored_receipt',decode(receipt.raw))
        if any(rc[k]!=ix[k] for k in ('receipt_ref','request_id','command_digest','command_key_sha256')):raise ValueError('RECEIPT_LINK')
        digest=hashlib.sha256(response.raw).hexdigest();status=rc['http_status']
        if rc['canonical_response_sha256']!=digest or cmd['result_sha256']!=digest:raise ValueError('RECEIPT_RESULT')
        def definitive(status):
            if query_request_id is None:return Outcome('COMMITTED',status,response.raw,receipt.index)
            document=build_document(context.cluster_id,query_request_id,pre,body,rc,response.raw,receipt.index)
            return Outcome('COMMITTED',200,document,receipt.index)

        if cmd['state']=='DEFINITIVE_REJECTED':
            result=validate('error_v3',decode(response.raw))
            if rc['result_schema_sha256']!=PROFILE_SHA or result['request_id']!=request or result['code'] not in matrix['definitive_rejected']['status_to_codes'].get(status,[]):raise ValueError('REJECTED_MATRIX')
            return definitive(int(status))
        rule=matrix['operations'][pre['operation']]
        if cmd['state']!='COMPLETED' or status not in rule['completed']:raise ValueError('OPERATION_RESULT_MATRIX')
        if status=='204':
            if rule['completed'][status]!='EMPTY' or response.raw!=b'' or rc['result_schema_sha256'] is not None:raise ValueError('EMPTY_204')
            return definitive(204)
        if rc['result_schema_sha256']!=PROFILE_SHA:raise ValueError('RESULT_PROFILE')
        result=validate(rule['completed'][status],decode(response.raw))
        if result['request_id']!=request or result['command_digest']!=ix['command_digest']:raise ValueError('RESULT_LINK')
        if pre['operation']=='OPEN_CONNECTION':
            if result['quota_owner_ref']!=ix['quota_owner_id'] or result['profile_schema_sha256']!=PROFILE_SHA or result['admitted_role']!=original['role']:raise ValueError('OPENED_BINDING')
        else:
            if result['connection_id']!=pre['connection_id'] or result['connection_epoch']!=pre['expected_connection_epoch']:raise ValueError('CONNECTION_RESULT_BINDING')
            if rule['completed'][status]=='draining' and (result['subscription_id'],result['subscription_epoch'])!=(pre['subscription_id'],pre['expected_subscription_epoch']):raise ValueError('DRAINING_BINDING')
        return definitive(int(status))

    async def reconcile(self,context,request):
        try:return await self._observe(context,request,await self._identity(context,'GET_COMMAND'))
        except AuthorityUncertain:return Outcome('UNKNOWN')
        except Exception:return Outcome('UNAVAILABLE')

    async def reconcile_document(self,context,request,query_request_id):
        """Current GET_COMMAND disclosure; no leader or new command is acquired."""
        try:
            _uuid(request);_uuid(query_request_id)
            if request==query_request_id:return Outcome('AMBIGUOUS')
            checks=await self._identity(context,'GET_COMMAND',read_disclosure=True)
        except _ReadNativeDenial as exc:return Outcome(exc.kind)
        except AuthorityUncertain:return Outcome('UNKNOWN')
        except Exception:return Outcome('UNAVAILABLE')
        try:
            observed=await self._observe(context,request,checks,query_request_id=query_request_id)
            if observed.kind=='UNKNOWN':return Outcome('UNRESOLVED')
            if observed.kind=='FORBIDDEN':return Outcome('DISCLOSURE_DENIED')
            return observed
        except AuthorityUncertain:return Outcome('UNKNOWN')
        except Exception:return Outcome('AMBIGUOUS')

    async def _ledger(self,context):
        ledgerkey=self.prefix+'owners/'+context.quota_owner_id+'/connections'
        ledgerrecord=await self._read(ledgerkey)
        ledger=decode(ledgerrecord.raw) if ledgerrecord.index else dict(schema='unified.control.connection-ledger.hold-only.v2',revision='0',connections=[])
        if set(ledger)!={'schema','revision','connections'} or ledger['schema']!='unified.control.connection-ledger.hold-only.v2' or type(ledger['connections']) is not list or len(ledger['connections'])>2:raise ValueError('LEDGER_INVALID')
        revision=ledger['revision']
        if type(revision) is not str or not revision.isascii() or not revision.isdecimal() or str(int(revision))!=revision or not 0<=int(revision)<2**63-1:raise ValueError('REVISION_EXHAUSTED')
        for entry in ledger['connections']:
            if type(entry) is not dict or set(entry)!={'connection_id','connection_epoch','request_id','role','state','generation'}:raise ValueError('LEDGER_ENTRY')
            _uuid(entry['connection_id']);_uuid(entry['request_id']);_uuid(entry['generation'])
            if entry['connection_epoch']!='1' or entry['role']!='OPERATOR_CONTROL' or entry['state'] not in ('PENDING','OPEN','DRAINING'):raise ValueError('LEDGER_ENTRY')
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
                    dict(connection_id=str(uuid.uuid4()),connection_epoch='1',request_id=command.request_id,role=context.role,state='PENDING',generation=self.generation)])
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
            if len(held)!=1 or held[0]['state']!='PENDING' or held[0]['generation']!=self.generation:raise ValueError('PREPARATION_HOLD_MISSING')
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
            require_fit(context.cluster_id,cmd['original_preimage'],command.body,rc,result)
            originalindex=await self._read(indexkey)
            if not originalindex.index or validate('request_index',decode(originalindex.raw))!=ix:raise ValueError('INDEX_CHANGED')
            await self._txn(checks+[_check(indexkey,originalindex.index),_cas(commandkey,stored.index,encode(cmd)),_cas(keys[2],0,encode(validate('stored_receipt',rc))),_cas(keys[3],0,result),_cas(ledgerkey,ledgerrecord.index,encode(ledger))])
            return await self._observe(context,command.request_id,await self._identity(context,'GET_COMMAND'))
        except Exception:
            # A timeout/409 is not rejection. Only original evidence may resolve it.
            result=await self.reconcile(context,command.request_id)
            if result.kind=='COMMITTED' and decode(result.body)['command_digest']!=command.digest:return Outcome('UNAVAILABLE')
            return result


    async def _close_target(self,context,pre,checks):
        ledgerkey,record,ledger=await self._ledger(context)
        found=[entry for entry in ledger['connections'] if entry['connection_id']==pre['connection_id']]
        if len(found)!=1 or found[0]['connection_epoch']!=pre['expected_connection_epoch']:
            await self._txn(checks+[_check(ledgerkey,record.index)],read_only=True)
            return Outcome('CONFLICT')
        entry=found[0]
        if entry['generation']!=self.generation:return Outcome('UNAVAILABLE')
        if entry['state'] not in ('OPEN','DRAINING'):return Outcome('UNAVAILABLE')
        indexkey=self.prefix+'requests/'+entry['request_id'];index=await self._read(indexkey)
        if not index.index:raise ValueError('PARENT_INDEX_MISSING')
        ix=validate('request_index',decode(index.raw));commandkey=self.prefix+'commands/'+ix['command_key_sha256'];parent=await self._read(commandkey)
        if not parent.index:raise ValueError('PARENT_COMMAND_MISSING')
        command=validate('stored_command',decode(parent.raw));original=command['original_preimage']
        if (original['operation']!='OPEN_CONNECTION' or original['original_actor_principal_id']!=context.actor_principal_id
                or original['original_actor_session_id']!=context.actor_session_id or original['quota_owner_id']!=context.quota_owner_id):return Outcome('FORBIDDEN')
        extra=checks+[_check(ledgerkey,record.index),_check(indexkey,index.index),_check(commandkey,parent.index)]
        observed=await self._observe(context,entry['request_id'],extra)
        if observed.kind!='COMMITTED' or observed.status!=201:raise ValueError('PARENT_UNVERIFIED')
        opened=decode(observed.body)
        if (opened['connection_id'],opened['connection_epoch'])!=(entry['connection_id'],entry['connection_epoch']):raise ValueError('PARENT_RESULT_MISMATCH')
        return ledgerkey,record,ledger,extra

    async def _pending_mutations(self,context):
        key=self.prefix+'owners/'+context.quota_owner_id+'/pending-mutations';record=await self._read(key)
        value=decode(record.raw) if record.index else dict(schema='unified.control.pending-mutations.v1',revision='0',entries=[])
        if type(value) is not dict or set(value)!={'schema','revision','entries'} or value['schema']!='unified.control.pending-mutations.v1':raise ValueError('PENDING_LEDGER')
        revision=value['revision']
        if type(revision) is not str or not revision.isascii() or not revision.isdecimal() or str(int(revision))!=revision or not 0<=int(revision)<2**63-1 or (record.index and revision=='0'):raise ValueError('PENDING_REVISION')
        entries=value['entries']
        if type(entries) is not list or len(entries)>14:raise ValueError('PENDING_CAP')
        total=0;seen=set()
        for entry in entries:
            if type(entry) is not dict or set(entry)!={'request_id','command_digest','command_key_sha256','bytes'}:raise ValueError('PENDING_ENTRY')
            _uuid(entry['request_id'])
            if entry['request_id'] in seen:raise ValueError('PENDING_DUPLICATE')
            seen.add(entry['request_id'])
            for name in ('command_digest','command_key_sha256'):
                if type(entry[name]) is not str or len(entry[name])!=64 or any(c not in '0123456789abcdef' for c in entry[name]):raise ValueError('PENDING_HASH')
            size=entry['bytes']
            if type(size) is not str or not size.isascii() or not size.isdecimal() or str(int(size))!=size or not 0<int(size)<=32768:raise ValueError('PENDING_BYTES')
            total+=int(size)
        if total>131072:raise ValueError('PENDING_BYTE_CAP')
        return key,record,value,total

    async def close_connection(self,leader,context,command):
        return await self._close_command(leader,context,command,'CLOSE_CONNECTION')

    async def close_subscription(self,leader,context,command):
        return await self._close_command(leader,context,command,'CLOSE_SUBSCRIPTION')

    async def _historical_command(self,context,command,checks):
        """Current-authorized immutable history, never target reactivation."""
        indexkey=self.prefix+'requests/'+command.request_id;commandkey=self.prefix+'commands/'+command.key_sha256
        index=await self._read(indexkey);stored=await self._read(commandkey)
        if not index.index and not stored.index:return None
        await self._txn(checks+[_check(indexkey,index.index),_check(commandkey,stored.index)],read_only=True)
        if index.index:
            ix=validate('request_index',decode(index.raw))
            if ix['command_digest']!=command.digest or ix['command_key_sha256']!=command.key_sha256:return Outcome('CONFLICT')
        if stored.index:
            cmd=validate('stored_command',decode(stored.raw))
            if cmd['command_digest']!=command.digest or cmd['request_id']!=command.request_id:return Outcome('CONFLICT')
        if not index.index or not stored.index:return Outcome('UNAVAILABLE')
        observed=await self._observe(context,command.request_id,checks)
        return None if observed.kind=='UNKNOWN' else observed

    async def _close_command(self,leader,context,command,operation):
        """Commit DRAINING only. No qualified containment manager => no204/release.

        Current slice retains all old connection/byte obligations. It cannot
        cancel jobs or turn a historical receipt into a new slot permission.
        """
        if type(command) is not PreparedCommand:return Outcome('UNAVAILABLE')
        try:
            pre=decode(command.preimage)
            verified=prepare_close(context,command.body,command.request_id,pre['idempotency_key'],pre['connection_id'],pre['expected_connection_epoch'],pre['subscription_id'],pre['expected_subscription_epoch'])
            if command!=verified or pre['operation']!=operation:return Outcome('UNAVAILABLE')
        except Exception:return Outcome('UNAVAILABLE')
        try:
            checks=await self._fence(leader,context,operation)
            history=await self._historical_command(context,command,checks)
            if history is not None:return history
            target=await self._close_target(context,pre,checks)
            if isinstance(target,Outcome):return target
            closing=await self._closing_subscriptions(context,pre,target[3])
            if isinstance(closing,Outcome):return closing
            target=(*target[:3],target[3]+closing[0])
            indexkey=self.prefix+'requests/'+command.request_id;commandkey=self.prefix+'commands/'+command.key_sha256
            index=await self._read(indexkey);stored=await self._read(commandkey)
            if index.index or stored.index:
                await self._txn(checks+[_check(indexkey,index.index),_check(commandkey,stored.index)],read_only=True)
                if index.index:
                    ix=validate('request_index',decode(index.raw))
                    if ix['command_digest']!=command.digest or ix['command_key_sha256']!=command.key_sha256:return Outcome('CONFLICT')
                if not index.index or not stored.index:return Outcome('UNAVAILABLE')
                cmd=validate('stored_command',decode(stored.raw))
                if cmd['command_digest']!=command.digest or cmd['request_id']!=command.request_id:return Outcome('CONFLICT')
                observed=await self._observe(context,command.request_id,checks)
                if observed.kind!='UNKNOWN':return observed
            else:
                pendingkey,pendingrecord,pending,total=await self._pending_mutations(context)
                size=len(command.body)+len(command.preimage)
                if len(pending['entries'])>=14 or total+size>131072:return Outcome('UNAVAILABLE')
                receipt=str(uuid.uuid4())
                ix=dict(schema='unified.control.request-index.v3',cluster_id=context.cluster_id,request_id=command.request_id,profile_schema_sha256=PROFILE_SHA,
                    quota_owner_id=context.quota_owner_id,original_actor_principal_id=context.actor_principal_id,original_actor_session_id=context.actor_session_id,
                    command_key_sha256=command.key_sha256,command_digest=command.digest,receipt_ref=receipt)
                cmd=dict(schema='unified.control.stored-command.v3',command_key_sha256=command.key_sha256,command_digest=command.digest,request_id=command.request_id,
                    receipt_ref=receipt,original_preimage=pre,original_body_ascii='',state='PENDING',result_sha256=None)
                hold=dict(request_id=command.request_id,command_digest=command.digest,command_key_sha256=command.key_sha256,bytes=str(size))
                updated=dict(pending,revision=str(int(pending['revision'])+1),entries=pending['entries']+[hold])
                await self._txn(target[3]+[_cas(indexkey,0,encode(validate('request_index',ix))),_cas(commandkey,0,encode(validate('stored_command',cmd))),_cas(pendingkey,pendingrecord.index,encode(updated))])
            checks=await self._fence(leader,context,operation)
            target=await self._close_target(context,pre,checks)
            if isinstance(target,Outcome):return target
            closing=await self._closing_subscriptions(context,pre,target[3])
            if isinstance(closing,Outcome):return closing
            ledgerkey,ledgerrecord,ledger,checks=target
            checks=checks+closing[0]
            stored=await self._read(commandkey);index=await self._read(indexkey)
            if not stored.index or not index.index:raise ValueError('ORIGINAL_MISSING')
            cmd=validate('stored_command',decode(stored.raw))
            if cmd['state']!='PENDING':return await self._observe(context,command.request_id,checks)
            if cmd['command_digest']!=command.digest or cmd['original_preimage']!=pre or cmd['original_body_ascii']!='' or validate('request_index',decode(index.raw))!=ix:raise ValueError('ORIGINAL_CHANGED')
            pendingkey,pendingrecord,pending,total=await self._pending_mutations(context)
            held=[x for x in pending['entries'] if x['request_id']==command.request_id]
            if len(held)!=1 or held[0]['command_digest']!=command.digest or held[0]['command_key_sha256']!=command.key_sha256:raise ValueError('PENDING_HOLD_MISSING')
            result=encode(validate('draining',dict(schema='unified.control.draining.v3',status='DRAINING',request_id=command.request_id,command_digest=command.digest,
                connection_id=pre['connection_id'],connection_epoch=pre['expected_connection_epoch'],subscription_id=pre['subscription_id'],subscription_epoch=pre['expected_subscription_epoch'])))
            digest=hashlib.sha256(result).hexdigest();keys=self._keys(command.request_id,command.key_sha256,cmd['receipt_ref'])
            receipt=dict(schema='unified.control.stored-receipt.v3',receipt_ref=cmd['receipt_ref'],request_id=command.request_id,command_key_sha256=command.key_sha256,
                command_digest=command.digest,http_status='202',result_schema_sha256=PROFILE_SHA,canonical_response_sha256=digest)
            updated_ledger=dict(ledger,revision=str(int(ledger['revision'])+1),connections=[dict(x,state='DRAINING') if operation=='CLOSE_CONNECTION' and x['connection_id']==pre['connection_id'] else x for x in ledger['connections']])
            updated_pending=dict(pending,revision=str(int(pending['revision'])+1),entries=[x for x in pending['entries'] if x['request_id']!=command.request_id])
            require_fit(context.cluster_id,pre,command.body,receipt,result)
            await self._txn(checks+[_check(indexkey,index.index),_cas(commandkey,stored.index,encode(dict(cmd,state='COMPLETED',result_sha256=digest))),
                _cas(keys[2],0,encode(validate('stored_receipt',receipt))),_cas(keys[3],0,result),_cas(ledgerkey,ledgerrecord.index,encode(updated_ledger)),_cas(pendingkey,pendingrecord.index,encode(updated_pending))]+closing[1])
            return await self._observe(context,command.request_id,await self._identity(context,'GET_COMMAND'))
        except Exception:
            result=await self.reconcile(context,command.request_id)
            if result.kind=='COMMITTED' and decode(result.body)['command_digest']!=command.digest:return Outcome('UNAVAILABLE')
            return result


    async def _subscriptions(self,context):
        key=self.prefix+'owners/'+context.quota_owner_id+'/subscriptions';record=await self._read(key)
        value=decode(record.raw) if record.index else dict(schema='unified.control.subscriptions.hold-only.v2',revision='0',epoch_counter='0',entries=[])
        if type(value) is not dict or set(value)!={'schema','revision','epoch_counter','entries'} or value['schema']!='unified.control.subscriptions.hold-only.v2':raise ValueError('SUBSCRIPTION_LEDGER')
        for name in ('revision','epoch_counter'):
            v=value[name]
            if type(v) is not str or not v.isascii() or not v.isdecimal() or str(int(v))!=v or not 0<=int(v)<2**63-1 or (record.index and v=='0'):raise ValueError('SUBSCRIPTION_COUNTER')
        if type(value['entries']) is not list or len(value['entries'])>3:raise ValueError('SUBSCRIPTION_CAP')
        seen=set();controls=set();datasets=0
        required={'subscription_id','subscription_epoch','connection_id','connection_epoch','kind','snapshot_id','delivery_session_id','state','request_id','command_key_sha256'}
        for e in value['entries']:
            if type(e) is not dict or set(e)!=required:raise ValueError('SUBSCRIPTION_ENTRY')
            for name in ('subscription_id','connection_id','snapshot_id','delivery_session_id','request_id'):_uuid(e[name])
            for name in ('subscription_epoch','connection_epoch'):
                v=e[name]
                if type(v) is not str or not v.isascii() or not v.isdecimal() or str(int(v))!=v or not 0<int(v)<2**63:raise ValueError('SUBSCRIPTION_EPOCH')
            if e['subscription_id'] in seen or int(e['subscription_epoch'])>int(value['epoch_counter']):raise ValueError('SUBSCRIPTION_DUPLICATE')
            seen.add(e['subscription_id'])
            if e['state'] not in ('PENDING','WAIT_SOURCE','DRAINING') or e['kind'] not in ('CONTROL','DATASET'):raise ValueError('SUBSCRIPTION_STATE')
            if e['kind']=='CONTROL':
                if e['connection_id'] in controls:raise ValueError('CONTROL_SLOT_DUPLICATE')
                controls.add(e['connection_id'])
            else:datasets+=1
            if type(e['command_key_sha256']) is not str or len(e['command_key_sha256'])!=64 or any(c not in '0123456789abcdef' for c in e['command_key_sha256']):raise ValueError('SUBSCRIPTION_COMMAND_KEY')
        if datasets>1:raise ValueError('DATASET_SLOT_DUPLICATE')
        return key,record,value

    async def subscribe(self,leader,context,command):
        """Reserve CONTROL metadata only; snapshot data/READY/LIVE remain closed."""
        if type(command) is not PreparedCommand:return Outcome('UNAVAILABLE')
        try:
            pre=decode(command.preimage);body=validate_original(pre,command.body)
            verified=prepare_subscribe(context,command.body,command.request_id,pre['idempotency_key'],pre['connection_id'],pre['expected_connection_epoch'])
            if command!=verified or pre['operation']!='OPEN_SUBSCRIPTION':return Outcome('UNAVAILABLE')
            # Dataset source/view authorization has no admitted implementation yet.
            if body['kind']!='CONTROL':return Outcome('UNAVAILABLE')
            checks=await self._fence(leader,context,'OPEN_SUBSCRIPTION')
            history=await self._historical_command(context,command,checks)
            if history is not None:return history
            target=await self._close_target(context,pre,checks)
            if isinstance(target,Outcome):return target
            parent=next(e for e in target[2]['connections'] if e['connection_id']==pre['connection_id'])
            if parent['state']!='OPEN':return Outcome('UNAVAILABLE')
            indexkey=self.prefix+'requests/'+command.request_id;commandkey=self.prefix+'commands/'+command.key_sha256
            index=await self._read(indexkey);stored=await self._read(commandkey)
            if index.index or stored.index:
                await self._txn(checks+[_check(indexkey,index.index),_check(commandkey,stored.index)],read_only=True)
                if index.index:
                    ix=validate('request_index',decode(index.raw))
                    if ix['command_digest']!=command.digest or ix['command_key_sha256']!=command.key_sha256:return Outcome('CONFLICT')
                if not index.index or not stored.index:return Outcome('UNAVAILABLE')
                cmd=validate('stored_command',decode(stored.raw))
                if cmd['command_digest']!=command.digest or cmd['request_id']!=command.request_id:return Outcome('CONFLICT')
                observed=await self._observe(context,command.request_id,checks)
                if observed.kind!='UNKNOWN':return observed
            else:
                subkey,subrecord,subs=await self._subscriptions(context)
                if any(e['connection_id']==pre['connection_id'] and e['kind']=='CONTROL' for e in subs['entries']):
                    await self._txn(target[3]+[_check(subkey,subrecord.index)],read_only=True)
                    return Outcome('UNAVAILABLE')
                pendingkey,pendingrecord,pending,total=await self._pending_mutations(context);size=len(command.body)+len(command.preimage)
                if len(pending['entries'])>=14 or total+size>131072:return Outcome('UNAVAILABLE')
                receipt=str(uuid.uuid4());entry=dict(subscription_id=str(uuid.uuid4()),subscription_epoch=str(int(subs['epoch_counter'])+1),
                    connection_id=pre['connection_id'],connection_epoch=pre['expected_connection_epoch'],kind=body['kind'],snapshot_id=str(uuid.uuid4()),
                    delivery_session_id=str(uuid.uuid4()),state='PENDING',request_id=command.request_id,command_key_sha256=command.key_sha256)
                ix=dict(schema='unified.control.request-index.v3',cluster_id=context.cluster_id,request_id=command.request_id,profile_schema_sha256=PROFILE_SHA,
                    quota_owner_id=context.quota_owner_id,original_actor_principal_id=context.actor_principal_id,original_actor_session_id=context.actor_session_id,
                    command_key_sha256=command.key_sha256,command_digest=command.digest,receipt_ref=receipt)
                cmd=dict(schema='unified.control.stored-command.v3',command_key_sha256=command.key_sha256,command_digest=command.digest,request_id=command.request_id,
                    receipt_ref=receipt,original_preimage=pre,original_body_ascii=command.body.decode(),state='PENDING',result_sha256=None)
                hold=dict(request_id=command.request_id,command_digest=command.digest,command_key_sha256=command.key_sha256,bytes=str(size))
                updated_pending=dict(pending,revision=str(int(pending['revision'])+1),entries=pending['entries']+[hold])
                updated_subs=dict(subs,revision=str(int(subs['revision'])+1),epoch_counter=entry['subscription_epoch'],entries=subs['entries']+[entry])
                await self._txn(target[3]+[_cas(indexkey,0,encode(validate('request_index',ix))),_cas(commandkey,0,encode(validate('stored_command',cmd))),
                    _cas(pendingkey,pendingrecord.index,encode(updated_pending)),_cas(subkey,subrecord.index,encode(updated_subs))])
            checks=await self._fence(leader,context,'OPEN_SUBSCRIPTION');target=await self._close_target(context,pre,checks)
            if isinstance(target,Outcome):return target
            if next(e for e in target[2]['connections'] if e['connection_id']==pre['connection_id'])['state']!='OPEN':return Outcome('UNAVAILABLE')
            subkey,subrecord,subs=await self._subscriptions(context);held=[e for e in subs['entries'] if e['request_id']==command.request_id]
            if len(held)!=1 or held[0]['command_key_sha256']!=command.key_sha256:raise ValueError('SUBSCRIPTION_HOLD_MISSING')
            entry=held[0]
            if entry['state']!='PENDING':return Outcome('UNKNOWN')
            stored=await self._read(commandkey);index=await self._read(indexkey)
            if not stored.index or not index.index:raise ValueError('ORIGINAL_MISSING')
            cmd=validate('stored_command',decode(stored.raw))
            if cmd['state']!='PENDING':return await self._observe(context,command.request_id,checks)
            if cmd['command_digest']!=command.digest or cmd['original_preimage']!=pre or cmd['original_body_ascii'].encode()!=command.body or validate('request_index',decode(index.raw))!=ix:raise ValueError('ORIGINAL_CHANGED')
            pendingkey,pendingrecord,pending,total=await self._pending_mutations(context)
            holds=[x for x in pending['entries'] if x['request_id']==command.request_id]
            if len(holds)!=1 or holds[0]['command_digest']!=command.digest:raise ValueError('PENDING_HOLD_MISSING')
            result=encode(validate('subscribed',dict(schema='unified.control.subscribed.v3',status='SUBSCRIBED',request_id=command.request_id,command_digest=command.digest,
                **{k:entry[k] for k in ('connection_id','connection_epoch','subscription_id','subscription_epoch','delivery_session_id','snapshot_id')})))
            digest=hashlib.sha256(result).hexdigest();keys=self._keys(command.request_id,command.key_sha256,cmd['receipt_ref'])
            receipt=dict(schema='unified.control.stored-receipt.v3',receipt_ref=cmd['receipt_ref'],request_id=command.request_id,command_key_sha256=command.key_sha256,
                command_digest=command.digest,http_status='201',result_schema_sha256=PROFILE_SHA,canonical_response_sha256=digest)
            metadata=dict(schema='unified.control.subscription.hold-only.v2',**entry,selector=body['selector'],owner_id=context.quota_owner_id,
                actor_id=context.actor_principal_id,actor_session_id=context.actor_session_id,generation=self.generation,revision='1')
            metadata['state']='WAIT_SOURCE'
            snapshot=dict(schema='unified.control.snapshot-intent.hold-only.v2',snapshot_id=entry['snapshot_id'],subscription_id=entry['subscription_id'],subscription_epoch=entry['subscription_epoch'],
                connection_id=entry['connection_id'],connection_epoch=entry['connection_epoch'],delivery_session_id=entry['delivery_session_id'],generation=self.generation,state='WAIT_SOURCE',body_sha256=None,cursor=None,view_ref=None)
            updated_subs=dict(subs,revision=str(int(subs['revision'])+1),entries=[dict(e,state='WAIT_SOURCE') if e['subscription_id']==entry['subscription_id'] else e for e in subs['entries']])
            updated_pending=dict(pending,revision=str(int(pending['revision'])+1),entries=[x for x in pending['entries'] if x['request_id']!=command.request_id])
            require_fit(context.cluster_id,pre,command.body,receipt,result)
            await self._txn(target[3]+[_check(indexkey,index.index),_cas(commandkey,stored.index,encode(dict(cmd,state='COMPLETED',result_sha256=digest))),
                _cas(keys[2],0,encode(validate('stored_receipt',receipt))),_cas(keys[3],0,result),_cas(subkey,subrecord.index,encode(updated_subs)),_cas(pendingkey,pendingrecord.index,encode(updated_pending)),
                _cas(self.prefix+'subscriptions/'+entry['subscription_id'],0,encode(metadata)),_cas(self.prefix+'snapshots/'+entry['snapshot_id'],0,encode(snapshot))])
            return await self._observe(context,command.request_id,await self._identity(context,'GET_COMMAND'))
        except Exception:
            result=await self.reconcile(context,command.request_id)
            if result.kind=='COMMITTED' and decode(result.body)['command_digest']!=command.digest:return Outcome('UNAVAILABLE')
            return result

    async def ack_snapshot(self,leader,context,command):
        """No admitted snapshot/barrier producer exists: never emit ACK204/LIVE."""
        if type(command) is not PreparedCommand:return Outcome('UNAVAILABLE')
        try:
            pre=decode(command.preimage);validate_original(pre,command.body)
            verified=prepare_ack(context,command.body,command.request_id,pre['idempotency_key'],pre['connection_id'],pre['subscription_id'],pre['expected_connection_epoch'],pre['expected_subscription_epoch'])
            if command!=verified:return Outcome('UNAVAILABLE')
            checks=await self._fence(leader,context,'ACK_SNAPSHOT')
            target=await self._close_target(context,pre,checks)
            if isinstance(target,Outcome):return target
            # Current native auth/epoch checked, but no source is qualified to
            # establish READY; hashes/claims cannot substitute. No intent writes.
            return Outcome('UNAVAILABLE')
        except AuthorityUncertain:return Outcome('UNKNOWN')
        except Exception:return Outcome('UNAVAILABLE')


    async def _closing_subscriptions(self,context,pre,checks):
        key,record,subs=await self._subscriptions(context)
        targets=[e for e in subs['entries'] if e['connection_id']==pre['connection_id'] and e['connection_epoch']==pre['expected_connection_epoch']]
        if pre['subscription_id'] is not None:
            targets=[e for e in targets if e['subscription_id']==pre['subscription_id'] and e['subscription_epoch']==pre['expected_subscription_epoch']]
            if len(targets)!=1:
                await self._txn(checks+[_check(key,record.index)],read_only=True)
                return Outcome('CONFLICT')
        more=[_check(key,record.index)];writes=[];ids={e['subscription_id'] for e in targets}
        if record.index and targets:
            updated=dict(subs,revision=str(int(subs['revision'])+1),entries=[dict(e,state='DRAINING') if e['subscription_id'] in ids else e for e in subs['entries']])
            writes.append(_cas(key,record.index,encode(updated)))
        for entry in targets:
            metakey=self.prefix+'subscriptions/'+entry['subscription_id'];meta=await self._read(metakey)
            snapshotkey=self.prefix+'snapshots/'+entry['snapshot_id'];snapshot=await self._read(snapshotkey)
            more.extend([_check(metakey,meta.index),_check(snapshotkey,snapshot.index)])
            if not meta.index:
                if entry['state'] not in ('PENDING','DRAINING') or snapshot.index:raise ValueError('MISSING_SUBSCRIPTION_METADATA')
                continue  # Unknown preparation debt is retained; never a release.
            value=decode(meta.raw)
            expected={'schema',*entry,'selector','owner_id','actor_id','actor_session_id','generation','revision'}
            if type(value) is not dict or set(value)!=expected or value['schema']!='unified.control.subscription.hold-only.v2':raise ValueError('SUBSCRIPTION_METADATA')
            if any(value[k]!=v for k,v in entry.items()) or value['owner_id']!=context.quota_owner_id or value['actor_id']!=context.actor_principal_id or value['actor_session_id']!=context.actor_session_id or value['generation']!=self.generation:raise ValueError('SUBSCRIPTION_BINDING')
            validate('scope',value['selector'])
            revision=value['revision']
            if type(revision) is not str or not revision.isascii() or not revision.isdecimal() or str(int(revision))!=revision or not 0<int(revision)<2**63-1:raise ValueError('SUBSCRIPTION_REVISION')
            writes.append(_cas(metakey,meta.index,encode(dict(value,state='DRAINING',revision=str(int(revision)+1)))))
            if not snapshot.index:raise ValueError('SNAPSHOT_INTENT_MISSING')
            snap=decode(snapshot.raw)
            expected_snapshot={'schema','snapshot_id','subscription_id','subscription_epoch','connection_id','connection_epoch','delivery_session_id','generation','state','body_sha256','cursor','view_ref'}
            if type(snap) is not dict or set(snap)!=expected_snapshot or snap['schema']!='unified.control.snapshot-intent.hold-only.v2':raise ValueError('SNAPSHOT_INTENT')
            if any(snap[k]!=entry[k] for k in ('snapshot_id','subscription_id','subscription_epoch','connection_id','connection_epoch','delivery_session_id')) or snap['generation']!=self.generation:raise ValueError('SNAPSHOT_BINDING')
            if snap['state'] not in ('WAIT_SOURCE','RETIRED') or any(snap[k] is not None for k in ('body_sha256','cursor','view_ref')):raise ValueError('UNQUALIFIED_SNAPSHOT_STATE')
            writes.append(_cas(snapshotkey,snapshot.index,encode(dict(snap,state='RETIRED'))))
        return more,writes


    async def subscription_connection(self,context,subscription_id,operation):
        """Resolve fixed native binding for preparation, never a permission token."""
        try:
            if operation not in ('ACK_SNAPSHOT','CLOSE_SUBSCRIPTION'):return Outcome('UNAVAILABLE')
            checks=await self._identity(context,operation);_uuid(subscription_id)
            key,record,subs=await self._subscriptions(context)
            found=[e for e in subs['entries'] if e['subscription_id']==subscription_id]
            await self._txn(checks+[_check(key,record.index)],read_only=True)
            if len(found)!=1:return Outcome('CONFLICT')
            e=found[0]
            return e['connection_id'],e['connection_epoch'],e['subscription_epoch']
        except AuthorityUncertain:return Outcome('UNKNOWN')
        except Exception:return Outcome('UNAVAILABLE')
