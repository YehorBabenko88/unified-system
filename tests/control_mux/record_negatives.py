"""Actual isolated Consul record faults; never a malicious-authority/auth claim."""
import base64,hashlib,json,uuid
from unified_system.control_mux.codec import encode,decode
from unified_system.control_mux.commands import prepare_close
from unified_system.control_mux.consul_store import AuthorityUncertain

async def run_record_negatives(store,authority,context,lease,close_command,draining,parent,identity_records):
    events=[];race_evidence=[]
    async def read(key):
        rows=await authority._request('GET','/v1/kv/'+key,params={'consistent':''},missing_ok=True)
        return base64.b64decode(rows[0]['Value']) if rows else None
    async def put(key,value):
        if value is None:await authority._request('DELETE','/v1/kv/'+key)
        else:await authority._request('PUT','/v1/kv/'+key,content=value)
    ix=decode(await read(store.prefix+'requests/'+close_command.request_id))
    keys=store._keys(close_command.request_id,close_command.key_sha256,ix['receipt_ref'])
    originals={key:await read(key) for key in keys}
    ledger_key=store.prefix+'owners/'+context.quota_owner_id+'/connections'
    ledger=await read(ledger_key)
    cmd=decode(originals[keys[1]]);receipt=decode(originals[keys[2]])
    result=decode(originals[keys[3]])
    faults=[]
    faults.append(('MISSING_RESPONSE_REJECTED_WITH_DEBT_RETAINED',{keys[3]:None}))
    faults.append(('RESPONSE_HASH_MISMATCH_REJECTED_WITH_DEBT_RETAINED',{keys[3]:encode(dict(result,connection_epoch='2'))}))
    faults.append(('RECEIPT_LINK_MISMATCH_REJECTED_WITH_DEBT_RETAINED',{keys[2]:encode(dict(receipt,request_id=str(uuid.uuid4())))}))
    faults.append(('PENDING_WITH_TERMINAL_EVIDENCE_REJECTED_WITH_DEBT_RETAINED',{keys[1]:encode(dict(cmd,state='PENDING',result_sha256=None))}))
    faults.append(('NONEMPTY_204_REJECTED_WITH_DEBT_RETAINED',{keys[2]:encode(dict(receipt,http_status='204',result_schema_sha256=None))}))
    changed=encode(dict(result,connection_id=str(uuid.uuid4())));digest=hashlib.sha256(changed).hexdigest()
    faults.append(('HASH_CONSISTENT_WRONG_CLOSE_TARGET_REJECTED',{keys[3]:changed,keys[1]:encode(dict(cmd,result_sha256=digest)),keys[2]:encode(dict(receipt,canonical_response_sha256=digest))}))
    for event,changes in faults:
        try:
            for key,value in changes.items():await put(key,value)
            observed=await store.reconcile(context,close_command.request_id)
            assert observed.kind=='UNAVAILABLE',(event,observed)
            assert await read(ledger_key)==ledger,'FAULT_RELEASED_OR_CHANGED_DEBT'
        finally:
            for key in changes:await put(key,originals[key])
        restored=await store.reconcile(context,close_command.request_id)
        assert restored.kind=='COMMITTED' and restored.status==202 and restored.body==draining.body
        # Fixture restores bytes with native writes, so receipt ModifyIndex may advance.
        events.append(event)
    for kind,(identity_key,active_record) in identity_records.items():
        for window in ('PREPARE','FINAL'):
            request=str(uuid.uuid4());command=prepare_close(context,b'',request,'identity-race-'+kind+'-'+window,parent['connection_id'],parent['connection_epoch'])
            native_txn=store._txn;injected=False;native_rejected=False
            async def revoke_before_native(ops,**kwargs):
                nonlocal injected,native_rejected
                match=any(op['KV']['Verb']=='cas' and (op['KV']['Key']==store.prefix+'requests/'+request if window=='PREPARE' else '/receipts/' in op['KV']['Key']) for op in ops)
                if match and not injected:
                    injected=True
                    matching=[op['KV'] for op in ops if op['KV']['Verb']=='check-index' and op['KV']['Key']==identity_key]
                    assert len(matching)==1,'IDENTITY_NATIVE_INDEX_GUARD_ABSENT'
                    await put(identity_key,encode(dict(decode(active_record),state='REVOKED')))
                    changed=await authority._request('GET','/v1/kv/'+identity_key,params={'consistent':''})
                    assert changed[0]['ModifyIndex']>matching[0]['Index']
                    race_evidence.append(dict(kind=kind,window=window,checked_index=matching[0]['Index'],changed_index=changed[0]['ModifyIndex'],native_transaction_sha256=hashlib.sha256(json.dumps(ops,separators=(',',':')).encode()).hexdigest()))
                    try:return await native_txn(ops,**kwargs)
                    except AuthorityUncertain:
                        native_rejected=True;raise
                return await native_txn(ops,**kwargs)
            store._txn=revoke_before_native
            try:
                outcome=await store.close_connection(lease,context,command)
                assert injected and native_rejected and outcome.kind=='UNAVAILABLE',(kind,window,outcome)
                assert await read(ledger_key)==ledger,'RACE_CHANGED_PARENT_DEBT'
                index=await read(store.prefix+'requests/'+request)
                if window=='PREPARE':assert index is None,'REVOKED_PREPARATION_PERSISTED'
                else:
                    assert index is not None
                    index=decode(index);pending=decode(await read(store.prefix+'commands/'+command.key_sha256))
                    assert pending['state']=='PENDING' and pending['result_sha256'] is None
                    assert pending['original_preimage']==decode(command.preimage) and pending['original_body_ascii']==''
                    holds=decode(await read(store.prefix+'owners/'+context.quota_owner_id+'/pending-mutations'))
                    held=[x for x in holds['entries'] if x['request_id']==request]
                    assert len(held)==1 and held[0]['command_digest']==command.digest and held[0]['command_key_sha256']==command.key_sha256
                    assert held[0]['bytes']==str(len(command.body)+len(command.preimage))
                    assert await read(store.prefix+'receipts/'+index['receipt_ref']) is None,'REVOKED_FINAL_RECEIPT_WRITTEN'
            finally:
                store._txn=native_txn
                await put(identity_key,active_record)
            events.append('CURRENT_'+kind.upper()+'_REVOCATION_'+window+'_NATIVE_TXN_REJECTED')
    return dict(events=events,identity_races=race_evidence)
