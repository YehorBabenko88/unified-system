"""Explicit real-Consul runner; not auto-discovered unit test or native auth."""
from dataclasses import replace
import argparse,asyncio,base64,hashlib,importlib.util,json,subprocess,sys,types,uuid
from pathlib import Path

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--binary',required=True);parser.add_argument('--scratch',required=True);parser.add_argument('--grid-source',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    sys.path.insert(0,str(root))
    raw=subprocess.check_output(['git','--no-replace-objects','show','cc286bce5e51e3670bd8a6cdfd3b663307268703:unified_system/security_identity_records.py'],cwd=root)
    module=types.ModuleType('unified_system.security_identity_records');sys.modules[module.__name__]=module;exec(compile(raw,'<pinned-root-identity-seam>','exec'),module.__dict__)
    sys.path.insert(0,str(Path(args.grid_source).resolve()))
    from grid.coordination import ConsulConfig,ConsulSessionAuthority
    from unified_system.control_mux.consul_store import MuxAuthority,AuthorityUncertain
    from unified_system.control_mux.commands import AdmittedContext,prepare_open
    from unified_system.control_mux.codec import encode,decode
    from consul_lab import ConsulLab
    report={'scope':'REAL_CONSUL_PRODUCT_OPEN_SYNTHETIC_NATIVE_PROVIDER_ONLY','production':'NO_GO','native_authentication':False,'events':[],'root_identity_source_sha256':hashlib.sha256(raw).hexdigest()}
    with ConsulLab(args.binary,args.scratch) as lab:
        async def run():
            ids=[str(uuid.uuid4()) for _ in range(8)];cluster,actor,session,enrollment,policy,node,owner,generation=ids
            binding=module.IdentityBinding(cluster,actor,session,enrollment,policy,node)
            context=AdmittedContext(cluster,actor,session,owner,'OPERATOR_CONTROL','fixture-policy','1',frozenset({'OPEN_CONNECTION','GET_COMMAND'}),binding)
            class SyntheticNativeFixture:
                def revalidate(self,c,operation):
                    if c is not context or operation not in c.permissions:raise ValueError('FIXTURE_DENIED')
                    return c
                def identity_binding(self,c):return c.native_handle
                def verify_records(self,c,records):
                    assert c.quota_owner_id==c.native_handle.principal_id
                    assert records['principal']['sid']=='S-1-5-21-123'
                    assert records['session']['native_logon_id']=='0000000000000001'
            authority=ConsulSessionAuthority(ConsulConfig(endpoints=tuple(lab.nodes),namespace='unified/'+cluster,isolated_lab=True,ttl_seconds=15,request_timeout=2))
            try:
                records={}
                for kind in ('principal','session','enrollment','policy'):
                    record=dict(schema='unified.security.identity-record.v1',kind=kind,cluster_id=cluster,principal_id=actor,state='ACTIVE',revision='1')
                    if kind=='principal':record.update(node_id=node,sid='S-1-5-21-123')
                    if kind=='session':record.update(session_id=session,enrollment_id=enrollment,policy_id=policy,native_logon_id='0000000000000001')
                    if kind=='enrollment':record.update(enrollment_id=enrollment,node_id=node)
                    if kind=='policy':record.update(policy_id=policy,role='OPERATOR_CONTROL',permissions=['GET_COMMAND','OPEN_CONNECTION'])
                    records[kind]=encode(record)
                for kind,key in module.guard_keys(binding).items():
                    await authority._request('PUT','/v1/kv/'+key,content=records[kind])
                await authority._request('PUT','/v1/kv/'+authority.config.namespace+'/commands/generation',content=encode({'generation':generation}))
                lease=await authority.acquire('mux-fixture');assert lease is not None
                store=MuxAuthority(authority,generation,admission=SyntheticNativeFixture())
                request=str(uuid.uuid4());body=encode(dict(schema='unified.control.connection-open.v3',request_id=request,app_instance_id=str(uuid.uuid4()),role='OPERATOR_CONTROL',enrollment_revision='1'))
                command=prepare_open(context,body,request,'open-1')
                bad_owner=await store.open(lease,context,command)
                assert bad_owner.kind=='UNAVAILABLE','ARBITRARY_QUOTA_OWNER_ACCEPTED'
                assert await authority._request('GET','/v1/kv/'+store.prefix+'requests/'+request,params={'consistent':''},missing_ok=True) is None
                context=replace(context,quota_owner_id=actor)
                command=prepare_open(context,body,request,'open-1')
                report['events'].append('ARBITRARY_OWNER_REJECTED_BEFORE_PREPARE')
                native_txn=store._txn
                dropped_final=False
                async def drop_final(ops,**kwargs):
                    nonlocal dropped_final
                    await native_txn(ops,**kwargs)
                    if not dropped_final and any(op['KV']['Verb']=='cas' and '/receipts/' in op['KV']['Key'] for op in ops):
                        dropped_final=True;raise AuthorityUncertain('FIXTURE_DROP_ACTUAL_COMMIT_RESPONSE')
                store._txn=drop_final
                result=await store.open(lease,context,command)
                store._txn=native_txn
                assert dropped_final
                report['events'].append('LOST_FINAL_COMMIT_RESPONSE_RECONCILED_ACTUAL_RECEIPT')
                assert result.kind=='COMMITTED' and result.status==201 and result.receipt_index>0,result
                assert decode(result.body)['request_id']==request
                retry=await store.open(lease,context,command);assert retry==result
                history=await store.reconcile(context,request);assert history==result
                report['events'].append('OPEN_ACTUAL_ATOMIC_RECEIPT_IDEMPOTENT_RECONCILE')
                # Duplicate UUID under different immutable body/key must never allocate again.
                body2=decode(body);body2['app_instance_id']=str(uuid.uuid4())
                conflict=await store.open(lease,context,prepare_open(context,encode(body2),request,'open-other'))
                assert conflict.kind=='CONFLICT',conflict
                report['events'].append('GLOBAL_REQUEST_UUID_CONFLICT')
                second_request=str(uuid.uuid4());second_body=decode(body);second_body['request_id']=second_request
                second_command=prepare_open(context,encode(second_body),second_request,'open-2')
                dropped_prepare=False
                async def drop_prepare(ops,**kwargs):
                    nonlocal dropped_prepare
                    await native_txn(ops,**kwargs)
                    if not dropped_prepare and any(op['KV']['Verb']=='cas' and '/requests/' in op['KV']['Key'] for op in ops):
                        dropped_prepare=True;raise AuthorityUncertain('FIXTURE_DROP_ACTUAL_PREPARE_RESPONSE')
                store._txn=drop_prepare
                pending=await store.open(lease,context,second_command)
                store._txn=native_txn
                assert dropped_prepare and pending.kind=='UNKNOWN',pending
                assert (await store.reconcile(context,second_request)).kind=='UNKNOWN'
                # Reconstruct product adapter; actual durable original and held slot survive.
                store=MuxAuthority(authority,generation,admission=SyntheticNativeFixture())
                assert (await store.open(lease,context,second_command)).kind=='COMMITTED'
                report['events'].append('LOST_PREPARE_RESPONSE_PENDING_HOLD_AND_ADAPTER_RESTART_RESUME')
                for _ in range(3):
                    overflow=str(uuid.uuid4());overflow_body=dict(second_body,request_id=overflow)
                    denied=await store.open(lease,context,prepare_open(context,encode(overflow_body),overflow,'overflow-'+overflow))
                    assert denied.kind=='UNAVAILABLE',denied
                    rows=await authority._request('GET','/v1/kv/'+store.prefix+'requests/'+overflow,params={'consistent':''},missing_ok=True)
                    assert rows is None,'CAPACITY_DENIAL_PERSISTED_UNBOUNDED_INTENT'
                report['events'].append('CAPACITY_PREPARATION_ATOMIC_BOUND_NO_DURABLE_OVERFLOW')
                # Revoke real identity record; same original historical request is not permission.
                revoked=decode(records['policy']);revoked['state']='REVOKED'
                await authority._request('PUT','/v1/kv/'+module.guard_keys(binding)['policy'],content=encode(revoked))
                denied=await store.reconcile(context,request);assert denied.kind=='UNAVAILABLE',denied
                report['events'].append('CURRENT_REVOKED_IDENTITY_REJECTED')
                await authority._request('PUT','/v1/kv/'+module.guard_keys(binding)['policy'],content=records['policy'])
                await authority.release(lease)
                stale_request=str(uuid.uuid4());stale_body=dict(second_body,request_id=stale_request)
                stale=await store.open(lease,context,prepare_open(context,encode(stale_body),stale_request,'stale'))
                assert stale.kind=='UNKNOWN',stale
                assert await authority._request('GET','/v1/kv/'+store.prefix+'requests/'+stale_request,params={'consistent':''},missing_ok=True) is None
                report['events'].append('DESTROYED_LEADER_SESSION_NEW_INTENT_DENIED')
                # Kill ONLY two owned isolated test-process handles, leaving one without quorum.
                for proc in lab.processes[:2]:proc.kill();proc.wait(timeout=10)
                noquorum=await store.reconcile(context,request)
                assert noquorum.kind=='UNKNOWN',noquorum
                report['events'].append('ONE_OF_THREE_NO_QUORUM_NO_SUCCESS')
            finally:await authority.close()
        asyncio.run(run())
    report['owned_processes_stopped']=all(p.poll() is not None for p in lab.processes);report['result']='PASS'
    Path(args.output).write_bytes((json.dumps(report,indent=2)+'\n').encode());print(json.dumps(report))
if __name__=='__main__':main()
