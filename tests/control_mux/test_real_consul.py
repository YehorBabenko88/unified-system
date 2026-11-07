"""Explicit real-Consul runner; not auto-discovered unit test or native auth."""
from dataclasses import replace
import argparse,asyncio,base64,hashlib,importlib.util,json,subprocess,sys,types,uuid
from pathlib import Path

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--binary',required=True);parser.add_argument('--scratch',required=True);parser.add_argument('--grid-source',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    sys.path.insert(0,str(root))
    raw=subprocess.check_output(['git','--no-replace-objects','show','cc286bce5e51e3670bd8a6cdfd3b663307268703:unified_system/security_identity_records.py'],cwd=root)
    assert hashlib.sha256(raw).hexdigest()=='0d6b413b5654c0ff26c00bbbdcc6a47329e56dd9b8cb1cd838df8896477972cd'
    module=types.ModuleType('unified_system.security_identity_records');sys.modules[module.__name__]=module;exec(compile(raw,'<pinned-root-identity-seam>','exec'),module.__dict__)
    sys.path.insert(0,str(Path(args.grid_source).resolve()))
    from grid.coordination import ConsulConfig,ConsulSessionAuthority,CoordinationLost
    from unified_system.control_mux.consul_store import MuxAuthority,AuthorityUncertain
    from unified_system.control_mux.commands import AdmittedContext,prepare_open,prepare_close,prepare_subscribe,prepare_ack,RawRequest
    from unified_system.control_mux.http_api import ControlMuxRuntime
    from unified_system.control_mux.codec import encode,decode
    from consul_lab import ConsulLab
    report={'scope':'REAL_CONSUL_MUX_METADATA_HOLD_ONLY_SYNTHETIC_NATIVE_PROVIDER_ONLY','production':'NO_GO','native_authentication':False,'events':[],'root_identity_source_sha256':hashlib.sha256(raw).hexdigest()}
    with ConsulLab(args.binary,args.scratch) as lab:
        async def run():
            ids=[str(uuid.uuid4()) for _ in range(8)];cluster,actor,session,enrollment,policy,node,owner,generation=ids
            binding=module.IdentityBinding(cluster,actor,session,enrollment,policy,node)
            context=AdmittedContext(cluster,actor,session,owner,'OPERATOR_CONTROL','fixture-policy','1',frozenset({'OPEN_CONNECTION','GET_COMMAND','CLOSE_CONNECTION','CLOSE_SUBSCRIPTION','OPEN_SUBSCRIPTION','ACK_SNAPSHOT'}),binding)
            class SyntheticNativeFixture:
                return_false=False
                def resolve(self,request,operation):
                    if request.native_connection is not context.native_handle:raise ValueError('FIXTURE_CONNECTION_ONLY')
                    return self.revalidate(context,operation)
                def revalidate(self,c,operation):
                    if c is not context or operation not in c.permissions:raise ValueError('FIXTURE_DENIED')
                    return c
                def identity_binding(self,c):return c.native_handle
                def verify_records(self,c,records):
                    if self.return_false:return False
                    assert c.quota_owner_id==c.native_handle.principal_id
                    assert records['principal']['sid']=='S-1-5-21-123'
                    assert records['session']['native_logon_id']=='0000000000000001'
            authority=ConsulSessionAuthority(ConsulConfig(endpoints=tuple(lab.nodes),namespace='unified/'+cluster,isolated_lab=True,ttl_seconds=60,request_timeout=2))
            try:
                records={}
                for kind in ('principal','session','enrollment','policy'):
                    record=dict(schema='unified.security.identity-record.v1',kind=kind,cluster_id=cluster,principal_id=actor,state='ACTIVE',revision='1')
                    if kind=='principal':record.update(node_id=node,sid='S-1-5-21-123')
                    if kind=='session':record.update(session_id=session,enrollment_id=enrollment,policy_id=policy,native_logon_id='0000000000000001')
                    if kind=='enrollment':record.update(enrollment_id=enrollment,node_id=node)
                    if kind=='policy':record.update(policy_id=policy,role='OPERATOR_CONTROL',permissions=['ACK_SNAPSHOT','CLOSE_CONNECTION','CLOSE_SUBSCRIPTION','GET_COMMAND','OPEN_CONNECTION','OPEN_SUBSCRIPTION'])
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
                store.admission.return_false=True
                refused=await store.open(lease,context,command)
                assert refused.kind=='UNAVAILABLE','NATIVE_VERIFIER_FALSE_IGNORED'
                assert await authority._request('GET','/v1/kv/'+store.prefix+'requests/'+request,params={'consistent':''},missing_ok=True) is None
                store.admission.return_false=False
                report['events'].append('NATIVE_VERIFIER_FALSE_RETURN_DENIED')
                native_txn=store._txn
                dropped_final=False
                async def drop_final(ops,**kwargs):
                    nonlocal dropped_final
                    await native_txn(ops,**kwargs)
                    if not dropped_final and any(op['KV']['Verb']=='cas' and '/receipts/' in op['KV']['Key'] for op in ops):
                        dropped_final=True;raise AuthorityUncertain('FIXTURE_DROP_ACTUAL_COMMIT_RESPONSE')
                store._txn=drop_final
                async def leader_provider():return lease
                runtime=ControlMuxRuntime(store=store,admission=store.admission,leader_provider=leader_provider)
                from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
                from threading import Thread
                import urllib.request
                loop=asyncio.get_running_loop()
                class FixtureHandler(BaseHTTPRequestHandler):
                    def log_message(self,*args):pass
                    def do_POST(self):self.dispatch('POST')
                    def do_DELETE(self):self.dispatch('DELETE')
                    def dispatch(self,method):
                        size=int(self.headers.get('Content-Length','0'))
                        if not 0<=size<=16384:self.send_error(413);return
                        request=RawRequest(method,self.path,tuple((k.encode('ascii'),v.encode('ascii')) for k,v in self.headers.raw_items()),self.rfile.read(size),context.native_handle)
                        response=asyncio.run_coroutine_threadsafe(runtime.handle(request),loop).result(timeout=10)
                        self.send_response(response.status)
                        for k,v in response.headers:self.send_header(k,v)
                        self.end_headers();self.wfile.write(response.body)
                server=ThreadingHTTPServer(('127.0.0.1',0),FixtureHandler);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
                try:
                    def send_http():
                        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
                        request_http=urllib.request.Request('http://127.0.0.1:'+str(server.server_port)+'/control/v3/connections',data=body,method='POST',headers={'Content-Type':'application/json','X-Request-ID':request,'Idempotency-Key':'open-1'})
                        with opener.open(request_http,timeout=10) as response:return response.status,response.read(16385)
                    status,result_body=await asyncio.to_thread(send_http)
                    assert status==201,status
                    assert decode(result_body)['request_id']==request
                    result=await store.reconcile(context,request)
                    assert result.body==result_body
                    report['events'].append('REAL_HTTP_POST_OPEN_TO_REAL_GRID_CONSUL')
                finally:
                    await asyncio.to_thread(server.shutdown);server.server_close();thread.join(timeout=3)
                store._txn=native_txn
                assert dropped_final
                report['events'].append('LOST_FINAL_COMMIT_RESPONSE_RECONCILED_ACTUAL_RECEIPT')
                report['actual_receipt_modify_index']=result.receipt_index
                report['actual_open_response_sha256']=hashlib.sha256(result.body).hexdigest()
                report['actual_original_request_id']=request
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
                raft=(await authority._request('GET','/v1/operator/raft/configuration',params={'consistent':''}))['Servers']
                failed=int(next(v['Node'] for v in raft if v['Leader']).rsplit('-',1)[1])
                lab.stop_node(failed)
                await asyncio.to_thread(lab.wait_quorum)
                original_leader=lease
                await authority.release(original_leader)
                lease=await authority.acquire('mux-fixture-successor-on-two')
                assert lease is not None and lease.token>original_leader.token
                report['leader_handoff']=dict(trigger='EXPLICIT_OWNED_SESSION_INVALIDATION_AFTER_RAFT_LEADER_LOSS',original_index=original_leader.token,successor_index=lease.token)
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
                report['events'].append('TWO_OF_THREE_COMPLETE_OPEN_AFTER_RAFT_LEADER_LOSS')
                lab.start_node(failed);await asyncio.to_thread(lab.wait_quorum)
                report['events'].append('RESTORED_THREE_VOTERS_KEEP_ORIGINAL_RECEIPT')
                ledger_path=store.prefix+'owners/'+context.quota_owner_id+'/connections'
                ledger_before=await authority._request('GET','/v1/kv/'+ledger_path,params={'consistent':''})
                lab.restart_all();await asyncio.to_thread(lab.wait_quorum)
                recovered=await store.reconcile(context,request)
                assert recovered==result,recovered
                assert await authority._request('GET','/v1/kv/'+ledger_path,params={'consistent':''})==ledger_before
                report['events'].append('SIMULTANEOUS_THREE_RESTART_DURABLE_RECEIPT_AND_SLOT_LEDGER')
                # Historical evidence never restores current coordinator permission.
                await authority.release(lease)
                lease=await authority.acquire('mux-fixture-after-owned-restart')
                assert lease is not None and await authority.validate(lease)
                opened=decode(result.body);subscribe_request=str(uuid.uuid4())
                subscribe_body=encode(dict(schema='unified.control.subscription-open.v3',request_id=subscribe_request,kind='CONTROL',selector=dict(kind='CONTROL',dataset_id=None,source_id=None,partition_id=None),expected_connection_epoch=opened['connection_epoch']))
                subscribe_command=prepare_subscribe(context,subscribe_body,subscribe_request,'subscribe-control',opened['connection_id'],opened['connection_epoch'])
                subscribed=await store.subscribe(lease,context,subscribe_command)
                assert subscribed.kind=='COMMITTED' and subscribed.status==201,subscribed
                sub=decode(subscribed.body);assert sub['connection_id']==opened['connection_id']
                assert await store.subscribe(lease,context,subscribe_command)==subscribed
                report['events'].append('ACTUAL_SUBSCRIBE_CONTROL_SLOT_AND_IMMUTABLE_REPLAY')
                duplicate_sub=str(uuid.uuid4());duplicate_body=decode(subscribe_body);duplicate_body['request_id']=duplicate_sub
                duplicate_result=await store.subscribe(lease,context,prepare_subscribe(context,encode(duplicate_body),duplicate_sub,'subscribe-duplicate',opened['connection_id'],opened['connection_epoch']))
                assert duplicate_result.kind=='UNAVAILABLE',duplicate_result
                assert await authority._request('GET','/v1/kv/'+store.prefix+'requests/'+duplicate_sub,params={'consistent':''},missing_ok=True) is None
                report['events'].append('SECOND_CONTROL_SUBSCRIPTION_DENIED_WITHOUT_INTENT')
                ack_request=str(uuid.uuid4());ack_body=encode(dict(schema='unified.control.snapshot-ack.v3',request_id=ack_request,snapshot_id=sub['snapshot_id'],snapshot_body_sha256='a'*64,cursor='not-an-admitted-cursor',expected_subscription_epoch=sub['subscription_epoch']))
                ack_command=prepare_ack(context,ack_body,ack_request,'ack-unready',opened['connection_id'],sub['subscription_id'],opened['connection_epoch'],sub['subscription_epoch'])
                assert (await store.ack_snapshot(lease,context,ack_command)).kind=='UNAVAILABLE'
                assert await authority._request('GET','/v1/kv/'+store.prefix+'requests/'+ack_request,params={'consistent':''},missing_ok=True) is None
                report['events'].append('NO_SNAPSHOT_SOURCE_NO_ACK204_OR_INTENT')
                close_sub_request=str(uuid.uuid4());close_sub_command=prepare_close(context,b'',close_sub_request,'close-sub',opened['connection_id'],opened['connection_epoch'],sub['subscription_id'],sub['subscription_epoch'])
                close_sub=await store.close_subscription(lease,context,close_sub_command)
                assert close_sub.kind=='COMMITTED' and close_sub.status==202,close_sub
                assert decode(close_sub.body)['subscription_id']==sub['subscription_id']
                assert await store.close_subscription(lease,context,close_sub_command)==close_sub
                parent_ledger=await authority._request('GET','/v1/kv/'+ledger_path,params={'consistent':''})
                assert next(e for e in decode(base64.b64decode(parent_ledger[0]['Value']))['connections'] if e['connection_id']==opened['connection_id'])['state']=='OPEN'
                report['events'].append('CLOSE_SUB202_RETAINS_PARENT_AND_SUBSCRIPTION_DEBT')
                pending_parent=decode((await store.reconcile(context,second_request)).body)
                pending_sub_request=str(uuid.uuid4());pending_body=encode(dict(schema='unified.control.subscription-open.v3',request_id=pending_sub_request,kind='CONTROL',selector=dict(kind='CONTROL',dataset_id=None,source_id=None,partition_id=None),expected_connection_epoch=pending_parent['connection_epoch']))
                pending_sub_command=prepare_subscribe(context,pending_body,pending_sub_request,'pending-sub-close-race',pending_parent['connection_id'],pending_parent['connection_epoch'])
                real_sub_txn=store._txn;drop_sub_once=False
                async def drop_sub_prepare(ops,**kwargs):
                    nonlocal drop_sub_once
                    await real_sub_txn(ops,**kwargs)
                    if not drop_sub_once and any(op['KV']['Verb']=='cas' and op['KV']['Key']==store.prefix+'requests/'+pending_sub_request for op in ops):
                        drop_sub_once=True;raise AuthorityUncertain('DROP_ACTUAL_SUB_PREPARE_RESPONSE')
                store._txn=drop_sub_prepare
                pending_sub=await store.subscribe(lease,context,pending_sub_command)
                store._txn=real_sub_txn
                assert drop_sub_once and pending_sub.kind=='UNKNOWN',pending_sub
                sub_ledger_rows=await authority._request('GET','/v1/kv/'+store.prefix+'owners/'+context.quota_owner_id+'/subscriptions',params={'consistent':''})
                pending_entry=next(e for e in decode(base64.b64decode(sub_ledger_rows[0]['Value']))['entries'] if e['request_id']==pending_sub_request)
                close_pending_id=str(uuid.uuid4());close_pending=prepare_close(context,b'',close_pending_id,'close-pending-sub',pending_parent['connection_id'],pending_parent['connection_epoch'],pending_entry['subscription_id'],pending_entry['subscription_epoch'])
                assert (await store.close_subscription(lease,context,close_pending)).status==202
                resumed=await store.subscribe(lease,context,pending_sub_command)
                assert resumed.kind!='COMMITTED','DRAINING_PENDING_SUB_REACTIVATED'
                assert await authority._request('GET','/v1/kv/'+store.prefix+'subscriptions/'+pending_entry['subscription_id'],params={'consistent':''},missing_ok=True) is None
                report['events'].append('CLOSED_PENDING_SUB_CANNOT_REACTIVATE_AFTER_LOST_PREPARE')
                close_request=str(uuid.uuid4())
                close_command=prepare_close(context,b'',close_request,'close-connection',opened['connection_id'],opened['connection_epoch'])
                draining=await store.close_connection(lease,context,close_command)
                assert draining.kind=='COMMITTED' and draining.status==202,draining
                assert decode(draining.body)['status']=='DRAINING'
                assert await store.close_connection(lease,context,close_command)==draining
                assert await store.reconcile(context,close_request)==draining
                ledger_rows=await authority._request('GET','/v1/kv/'+ledger_path,params={'consistent':''})
                current_ledger=decode(base64.b64decode(ledger_rows[0]['Value']))
                assert len(current_ledger['connections'])==2 and next(e for e in current_ledger['connections'] if e['connection_id']==opened['connection_id'])['state']=='DRAINING'
                report['events'].append('ACTUAL_CLOSE202_IMMUTABLE_REPLAY_AND_DEBT_RETAINED')
                historical_sub=await store.subscribe(lease,context,subscribe_command)
                assert historical_sub==subscribed,'HISTORICAL_SUB_RETRY_DEPENDS_ON_PARENT_STATE'
                current_sub=await authority._request('GET','/v1/kv/'+store.prefix+'subscriptions/'+sub['subscription_id'],params={'consistent':''})
                assert decode(base64.b64decode(current_sub[0]['Value']))['state']=='DRAINING'
                report['events'].append('HISTORICAL_SUB201_RETRY_DOES_NOT_REACTIVATE_DRAINING_PARENT')
                runtime=ControlMuxRuntime(store=store,admission=store.admission,leader_provider=leader_provider)
                server=ThreadingHTTPServer(('127.0.0.1',0),FixtureHandler);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
                try:
                    def delete_http():
                        import urllib.error
                        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
                        req=urllib.request.Request('http://127.0.0.1:'+str(server.server_port)+'/control/v3/connections/'+opened['connection_id'],data=None,method='DELETE',headers={'Content-Length':'0','X-Request-ID':close_request,'Idempotency-Key':'close-connection','X-Expected-Connection-Epoch':opened['connection_epoch']})
                        try:
                            with opener.open(req,timeout=10) as response:return response.status,response.read(16385)
                        except urllib.error.HTTPError as error:return error.code,error.read(16385)
                    def extra_http(method,path,data,headers):
                        import urllib.error
                        req=urllib.request.Request('http://127.0.0.1:'+str(server.server_port)+path,data=data,method=method,headers=headers)
                        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
                        try:
                            with opener.open(req,timeout=10) as response:return response.status,response.read(16385)
                        except urllib.error.HTTPError as error:return error.code,error.read(16385)
                    status_sub,body_sub=await asyncio.to_thread(extra_http,'POST','/control/v3/connections/'+opened['connection_id']+'/subscriptions',subscribe_body,{'Content-Type':'application/json','X-Request-ID':subscribe_request,'Idempotency-Key':'subscribe-control','X-Expected-Connection-Epoch':opened['connection_epoch']})
                    assert status_sub==201 and body_sub==subscribed.body,(status_sub,body_sub)
                    report['events'].append('REAL_HTTP_SUB_HISTORY_WITHOUT_REACTIVATION')
                    status_ack,_=await asyncio.to_thread(extra_http,'POST','/control/v3/subscriptions/'+sub['subscription_id']+'/snapshot-acks',ack_body,{'Content-Type':'application/json','X-Request-ID':ack_request,'Idempotency-Key':'ack-unready','X-Expected-Connection-Epoch':opened['connection_epoch'],'X-Expected-Subscription-Epoch':sub['subscription_epoch']})
                    assert status_ack==503,status_ack
                    report['events'].append('REAL_HTTP_ACK_WITHOUT_SOURCE_FAILS_CLOSED')
                    status_close_sub,body_close_sub=await asyncio.to_thread(extra_http,'DELETE','/control/v3/subscriptions/'+sub['subscription_id'],None,{'Content-Length':'0','X-Request-ID':close_sub_request,'Idempotency-Key':'close-sub','X-Expected-Connection-Epoch':opened['connection_epoch'],'X-Expected-Subscription-Epoch':sub['subscription_epoch']})
                    assert status_close_sub==202 and body_close_sub==close_sub.body,(status_close_sub,body_close_sub)
                    report['events'].append('REAL_HTTP_CLOSE_SUB202_REPLAY')
                    status,body_http=await asyncio.to_thread(delete_http)
                    assert status==202 and body_http==draining.body,(status,body_http)
                    report['events'].append('REAL_HTTP_DELETE_REPLAYS_EXACT_DRAINING_RECEIPT')
                finally:
                    await asyncio.to_thread(server.shutdown);server.server_close();thread.join(timeout=3)
                stale_close=str(uuid.uuid4());stale_command=prepare_close(context,b'',stale_close,'close-stale-epoch',opened['connection_id'],str(int(opened['connection_epoch'])+1))
                stale_result=await store.close_connection(lease,context,stale_command)
                assert stale_result.kind=='CONFLICT',stale_result
                assert await authority._request('GET','/v1/kv/'+store.prefix+'requests/'+stale_close,params={'consistent':''},missing_ok=True) is None
                report['events'].append('STALE_CLOSE_EPOCH_NO_INTENT_OR_RELEASE')
                for _ in range(3):
                    overflow=str(uuid.uuid4());overflow_body=dict(second_body,request_id=overflow)
                    denied=await store.open(lease,context,prepare_open(context,encode(overflow_body),overflow,'overflow-'+overflow))
                    assert denied.kind=='UNAVAILABLE',denied
                    rows=await authority._request('GET','/v1/kv/'+store.prefix+'requests/'+overflow,params={'consistent':''},missing_ok=True)
                    assert rows is None,'CAPACITY_DENIAL_PERSISTED_UNBOUNDED_INTENT'
                report['events'].append('CAPACITY_PREPARATION_ATOMIC_BOUND_NO_DURABLE_OVERFLOW')
                old_parent=decode((await store.reconcile(context,second_request)).body)
                next_generation=str(uuid.uuid4())
                await authority._request('PUT','/v1/kv/'+authority.config.namespace+'/commands/generation',content=encode({'generation':next_generation}))
                recovered_store=MuxAuthority(authority,next_generation,admission=SyntheticNativeFixture())
                cross_generation=str(uuid.uuid4());cross_body=encode(dict(schema='unified.control.subscription-open.v3',request_id=cross_generation,kind='CONTROL',selector=dict(kind='CONTROL',dataset_id=None,source_id=None,partition_id=None),expected_connection_epoch=old_parent['connection_epoch']))
                cross_command=prepare_subscribe(context,cross_body,cross_generation,'old-generation-parent',old_parent['connection_id'],old_parent['connection_epoch'])
                cross_checks=await recovered_store._fence(lease,context,'OPEN_SUBSCRIPTION')
                cross_target=await recovered_store._close_target(context,decode(cross_command.preimage),cross_checks)
                assert getattr(cross_target,'kind',None)=='UNAVAILABLE','GENERATION_GUARD_MISSING_BEFORE_QUOTA'
                cross_result=await recovered_store.subscribe(lease,context,cross_command)
                assert cross_result.kind=='UNAVAILABLE','OLD_GENERATION_CONNECTION_REACTIVATED'
                assert await authority._request('GET','/v1/kv/'+store.prefix+'requests/'+cross_generation,params={'consistent':''},missing_ok=True) is None
                report['events'].append('NEW_GENERATION_CANNOT_REACTIVATE_OLD_CONNECTION')
                # Revoke real identity record; same original historical request is not permission.
                revoked=decode(records['policy']);revoked['state']='REVOKED'
                await authority._request('PUT','/v1/kv/'+module.guard_keys(binding)['policy'],content=encode(revoked))
                denied=await store.reconcile(context,request);assert denied.kind=='UNAVAILABLE',denied
                report['events'].append('CURRENT_REVOKED_IDENTITY_REJECTED')
                await authority._request('PUT','/v1/kv/'+module.guard_keys(binding)['policy'],content=records['policy'])
                await authority.release(lease)
                sentinel=store.prefix+'probe-only/stale-leader/'+str(uuid.uuid4())
                native_stale=[{'KV':dict(Verb='check-session',Key=authority.key,Session=lease.session_id)},
                    {'KV':dict(Verb='check-index',Key=authority.key,Index=lease.token)},
                    {'KV':dict(Verb='cas',Key=sentinel,Index=0,Value=base64.b64encode(b'NEVER').decode())}]
                try:await authority._request('PUT','/v1/txn',json=native_stale)
                except CoordinationLost:pass
                else:raise AssertionError('NATIVE_STALE_LEADER_ACCEPTED')
                assert await authority._request('GET','/v1/kv/'+sentinel,params={'consistent':''},missing_ok=True) is None
                report['events'].append('ACTUAL_NATIVE_STALE_LEADER_TRANSACTION_REJECTED')
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
        async def bounded_run():return await asyncio.wait_for(run(),timeout=90)
        asyncio.run(bounded_run())
    report['owned_processes_stopped']=all(p.poll() is not None for p in lab.all_processes);report['result']='PASS'
    Path(args.output).write_bytes((json.dumps(report,indent=2)+'\n').encode());print(json.dumps(report))
if __name__=='__main__':main()
