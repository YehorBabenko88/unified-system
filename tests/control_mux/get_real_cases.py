"""Real HTTP/existing Grid/Consul reads; native causes explicitly synthetic.
No actual Windows identity, session expiry, containment or admission is claimed.
"""
import asyncio,base64,hashlib,json,uuid
from contextlib import asynccontextmanager
from dataclasses import replace
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
import urllib.request,urllib.error
from grid.coordination import CoordinationLost
from unified_system.control_mux.codec import encode,decode,validate
from unified_system.control_mux.commands import RawRequest,NativeAdmissionError,NativeAdmissionProvider
from unified_system.control_mux.consul_store import MuxAuthority,AuthorityUncertain
from unified_system.control_mux.http_api import ControlMuxRuntime

class SyntheticReadProvider:
    def __init__(self,context,sid='S-1-5-21-123',luid='0000000000000001'):
        self.context=context;self.sid=sid;self.luid=luid;self.errors={};self.wrong_returns={}
    def check(self,name):
        if name in self.errors:raise self.errors[name]
    def resolve(self,request,operation):
        self.check('resolve')
        if 'resolve' in self.wrong_returns:return self.wrong_returns['resolve']
        if request.native_connection is not self.context.native_handle or operation!='GET_COMMAND':raise NativeAdmissionError('UNAUTHENTICATED')
        return self.context
    def revalidate(self,context,operation):
        self.check('revalidate')
        if 'revalidate' in self.wrong_returns:return self.wrong_returns['revalidate']
        if context is not self.context or operation!='GET_COMMAND':raise NativeAdmissionError('UNAUTHENTICATED')
        return context
    def identity_binding(self,context):
        self.check('identity_binding')
        return self.wrong_returns.get('identity_binding',context.native_handle)
    def verify_records(self,context,records):
        self.check('verify_records')
        if 'verify_records' in self.wrong_returns:return self.wrong_returns['verify_records']
        assert records['principal']['sid']==self.sid and records['session']['native_logon_id']==self.luid
        assert context.quota_owner_id==context.native_handle.principal_id

@asynccontextmanager
async def actual_http(runtime_box,binding_box):
    loop=asyncio.get_running_loop()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            size=int(self.headers.get('Content-Length','0'))
            if not 0<=size<=16384:self.send_error(413);return
            raw=RawRequest('GET',self.path,tuple((k.encode('ascii'),v.encode('ascii')) for k,v in self.headers.raw_items()),self.rfile.read(size),binding_box[0])
            result=asyncio.run_coroutine_threadsafe(runtime_box[0].handle(raw),loop).result(timeout=20)
            self.send_response(result.status)
            for key,value in result.headers:self.send_header(key,value)
            self.end_headers();self.wfile.write(result.body)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    async def get(original,query=None,headers=None):
        query=query or str(uuid.uuid4())
        def send():
            req=urllib.request.Request('http://127.0.0.1:'+str(server.server_port)+'/control/v3/commands/'+original,method='GET',headers={'X-Request-ID':query,**(headers or {})})
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
            try:
                with opener.open(req,timeout=20) as response:return response.status,response.read(16385),query
            except urllib.error.HTTPError as error:return error.code,error.read(16385),query
        return await asyncio.to_thread(send)
    try:yield get
    finally:
        await asyncio.to_thread(server.shutdown);server.server_close();thread.join(timeout=3)
        assert not thread.is_alive(),'OWNED_GET_HTTP_THREAD_NOT_STOPPED'

def error(response,status,code,reason=None):
    observed,raw,query=response;assert observed==status,(observed,raw)
    value=validate('error_v3',decode(raw));assert value['code']==code and value['request_id']==query,(value,query)
    if reason is not None:assert value['reason']==reason,value
    assert 'command_digest' not in value and 'receipt' not in value
    return value

async def run_get_cases(authority,generation,context,original,close_request,close_body,subscribe_request,pending_request,identity_module,records):
    events=[];races=[]
    provider=SyntheticReadProvider(context);store=MuxAuthority(authority,generation,admission=provider)
    runtime=ControlMuxRuntime(store=store,admission=provider) # No leader provider.
    box=[runtime];binding=[context.native_handle]
    async def read(key):
        rows=await authority._request('GET','/v1/kv/'+key,params={'consistent':''},missing_ok=True)
        return (base64.b64decode(rows[0]['Value']),rows[0]['ModifyIndex']) if rows else (None,0)
    async def put(key,raw):
        if raw is None:await authority._request('DELETE','/v1/kv/'+key)
        else:await authority._request('PUT','/v1/kv/'+key,content=raw)
    async def snapshot():return await authority._request('GET','/v1/kv/'+store.prefix,params={'consistent':'','recurse':''},missing_ok=True)
    async with actual_http(box,binding) as get:
        async def unchanged_get(original,**kwargs):
            before=await snapshot();reply=await get(original,**kwargs);assert await snapshot()==before,'GET_CHANGED_PRIVATE_KV_OR_DEBT'
            return reply
        for request,status,body,event in [(original,'201',None,'GET200_ORIGINAL201_CAPTURED_NATIVE_INDEX'),(close_request,'202',close_body,'GET200_ORIGINAL202_IMMUTABLE_BYTES_NO_LEADER')]:
            reply=await unchanged_get(request);assert reply[0]==200,reply
            v=decode(reply[1]);assert v['query_request_id']==reply[2] and v['request_id']==request and v['receipt']['http_status']==status
            ix=decode((await read(store.prefix+'requests/'+request))[0]);raw,index=await read(store.prefix+'receipts/'+ix['receipt_ref'])
            assert v['receipt']==decode(raw) and v['receipt_modify_index']==str(index)
            if body is not None:assert v['original_result_ascii'].encode()==body
            events.append(event)
        ledger_key=store.prefix+'owners/'+context.quota_owner_id+'/connections';ledger_raw,_=await read(ledger_key)
        closed=decode(ledger_raw);closed['connections'][0]['state']='CLOSED'
        try:
            # Fault-injected current state ONLY, not qualified containment/release.
            await put(ledger_key,encode(closed));reply=await unchanged_get(close_request)
            assert reply[0]==200 and decode(reply[1])['receipt']['http_status']=='202' and decode(reply[1])['original_result_ascii'].encode()==close_body
        finally:await put(ledger_key,ledger_raw)
        events.append('GET200_ORIGINAL202_UNCHANGED_UNDER_FAULT_INJECTED_CURRENT_CLOSED')
        error(await unchanged_get(str(uuid.uuid4())),503,'ADMISSION_UNAVAILABLE','NONE');events.append('GET503_CLEAN_MISSING_NONE_NO_WRITES')
        error(await unchanged_get(pending_request),503,'ADMISSION_UNAVAILABLE','NONE');events.append('GET503_PENDING_NONE_NO_WRITES')
        reply=await unchanged_get(original,query=original);assert reply[0]==400 and decode(reply[1])['request_id'] is None
        events.append('GET400_QUERY_ORIGINAL_ALIAS_NO_WRITES')
        box[0]=ControlMuxRuntime()
        error(await unchanged_get(original),503,'AUTHENTICATION_UNAVAILABLE','PROVIDER_UNAVAILABLE');box[0]=runtime
        events.append('GET503_MISSING_PROVIDER_CURRENT_QUERY_NO_WRITES')
        for stage in ('resolve','revalidate','identity_binding','verify_records'):
            for kind,status,code in [('UNAUTHENTICATED',401,'UNAUTHENTICATED'),('SESSION_EXPIRED',401,'SESSION_EXPIRED'),('FORBIDDEN',403,'FORBIDDEN'),('UNAVAILABLE',503,None)]:
                provider.errors[stage]=NativeAdmissionError(kind)
                reply=await unchanged_get(original)
                if code is None:
                    assert reply[0]==503 and decode(reply[1])['request_id']==reply[2],reply
                else:error(reply,status,code)
                provider.errors.clear()
            events.append('GET_SYNTHETIC_TYPED_NATIVE_'+stage.upper()+'_ALL4_CAUSES_NO_DISCLOSURE')
        class SubclassDenial(NativeAdmissionError):pass
        malformed=NativeAdmissionError('SESSION_EXPIRED');malformed.kind={'client':'SESSION_EXPIRED'}
        foreign=RuntimeError('SESSION_EXPIRED');foreign.kind='SESSION_EXPIRED'
        for stage in ('resolve','revalidate','identity_binding','verify_records'):
            for denial in (SubclassDenial('SESSION_EXPIRED'),malformed,foreign):
                provider.errors[stage]=denial;reply=await unchanged_get(original)
                assert reply[0]==503 and decode(reply[1])['request_id']==reply[2] and 'receipt' not in decode(reply[1]),reply
                provider.errors.clear()
        events.append('GET503_NONEXACT_OR_MALFORMED_NATIVE_ERRORS_ALL4_BOUNDARIES')
        for stage in ('resolve','revalidate','identity_binding','verify_records'):
            provider.wrong_returns[stage]=False;reply=await unchanged_get(original)
            assert reply[0]==503 and decode(reply[1])['request_id']==reply[2],reply
            provider.wrong_returns.clear()
        events.append('GET503_WRONG_NATIVE_RETURN_TYPES_ALL4_BOUNDARIES')
        class InheritedVerifier(SyntheticReadProvider):verify_records=NativeAdmissionProvider.verify_records
        inherited=InheritedVerifier(context)
        box[0]=ControlMuxRuntime(store=MuxAuthority(authority,generation,admission=inherited),admission=inherited)
        reply=await unchanged_get(original);assert reply[0]==503 and decode(reply[1])['request_id']==reply[2],reply
        box[0]=runtime;events.append('GET503_INHERITED_NATIVE_VERIFIER_STUB_NOT_ADMISSION')
        native_txn=store._txn
        async def typed_storage_failure(ops,**kwargs):
            await native_txn(ops,**kwargs)
            raise NativeAdmissionError('SESSION_EXPIRED') # Explicit post-read storage fault, not native provider.
        store._txn=typed_storage_failure
        try:error(await unchanged_get(original),503,'ADMISSION_UNAVAILABLE','RECEIPT_AMBIGUOUS')
        finally:store._txn=native_txn
        events.append('GET503_TYPED_LOOKING_STORAGE_EXCEPTION_NOT_NATIVE_DENIAL')
        provider.errors['revalidate']=PermissionError('SESSION_EXPIRED')
        reply=await unchanged_get(original);assert reply[0]==503 and decode(reply[1])['request_id']==reply[2];provider.errors.clear()
        events.append('GET503_UNTYPED_NATIVE_ERROR_NOT_PARSED_AS_EXPIRY')
        reply=await unchanged_get(original,headers={'X-Native-Admission-Kind':'SESSION_EXPIRED','X-Actor-ID':str(uuid.uuid4())})
        assert reply[0]==200 and decode(reply[1])['original_preimage']['original_actor_principal_id']==context.actor_principal_id
        events.append('GET_IGNORES_TYPED_LOOKING_CLIENT_IDENTITY_HEADERS')
        policy_key=identity_module.guard_keys(context.native_handle)['policy']
        policy=decode(records['policy']);policy['permissions'].remove('GET_COMMAND')
        try:
            await put(policy_key,encode(policy));error(await unchanged_get(original),403,'FORBIDDEN','ROLE_DENIED')
        finally:await put(policy_key,records['policy'])
        events.append('GET403_ACTUAL_CURRENT_POLICY_WITHOUT_GET_COMMAND')
        try:
            await put(policy_key,encode(dict(decode(records['policy']),state='REVOKED')))
            reply=await unchanged_get(original);assert reply[0]==503 and decode(reply[1])['request_id']==reply[2] and 'receipt' not in decode(reply[1])
        finally:await put(policy_key,records['policy'])
        events.append('GET503_ACTUAL_REVOKED_CURRENT_IDENTITY_RECORD_NO_DISCLOSURE')
        later_binding=replace(context.native_handle,session_id=str(uuid.uuid4()))
        later_context=replace(context,actor_session_id=later_binding.session_id,native_handle=later_binding)
        later_session=decode(records['session']);later_session['session_id']=later_binding.session_id
        await put(identity_module.guard_keys(later_binding)['session'],encode(later_session))
        later_provider=SyntheticReadProvider(later_context)
        box[0]=ControlMuxRuntime(store=MuxAuthority(authority,generation,admission=later_provider),admission=later_provider);binding[0]=later_binding
        reply=await unchanged_get(original);assert reply[0]==200
        assert decode(reply[1])['original_preimage']['original_actor_session_id']==context.actor_session_id!=later_context.actor_session_id
        box[0]=runtime;binding[0]=context.native_handle
        events.append('GET200_LATER_CURRENT_SESSION_PRESERVES_ORIGINAL_ACTOR_SESSION')

        ids=[str(uuid.uuid4()) for _ in range(5)]
        b=identity_module.IdentityBinding(context.cluster_id,ids[0],ids[1],ids[2],ids[3],ids[4])
        other=replace(context,actor_principal_id=b.principal_id,actor_session_id=b.session_id,quota_owner_id=b.principal_id,native_handle=b)
        for kind,key in identity_module.guard_keys(b).items():
            record=decode(records[kind])
            for field in b.__dataclass_fields__:
                if field in record:record[field]=getattr(b,field)
            if kind=='principal':record['sid']='S-1-5-21-456'
            if kind=='session':record['native_logon_id']='0000000000000002'
            await put(key,encode(record))
        other_provider=SyntheticReadProvider(other,'S-1-5-21-456','0000000000000002')
        box[0]=ControlMuxRuntime(store=MuxAuthority(authority,generation,admission=other_provider),admission=other_provider);binding[0]=b
        error(await unchanged_get(original),403,'FORBIDDEN','NONE');box[0]=runtime;binding[0]=context.native_handle
        events.append('GET403_ACTUAL_OTHER_OWNER_GUARDS_REDACTED_NO_ROLE_ALIAS')
        original_index=decode((await read(store.prefix+'requests/'+original))[0]);receipt_key=store.prefix+'receipts/'+original_index['receipt_ref']
        for key,kind in ((policy_key,'IDENTITY'),(receipt_key,'RECEIPT')):
            native_txn=store._txn;injected=False;rejected=False
            async def change_before_read_txn(ops,**kwargs):
                nonlocal injected,rejected
                matching=[op['KV'] for op in ops if op['KV']['Verb']=='check-index' and op['KV']['Key']==key]
                if kwargs.get('read_only') and matching and not injected:
                    injected=True;assert all(op['KV']['Verb'].startswith('check-') for op in ops),'GET_WRITE_OPERATION'
                    raw,index=await read(key);assert matching[0]['Index']==index
                    if kind=='IDENTITY':
                        next_policy=decode(raw);next_policy['revision']=str(int(next_policy['revision'])+1);await put(key,encode(next_policy))
                    else:
                        # A same-value Consul PUT is a no-op. Recreate the same
                        # receipt bytes as an explicit fault, never a real commit.
                        await put(key,None);await put(key,raw)
                    _,changed=await read(key);assert changed>index
                    races.append(dict(kind=kind,checked_index=index,changed_index=changed,native_transaction_sha256=hashlib.sha256(json.dumps(ops,separators=(',',':')).encode()).hexdigest()))
                    try:return await native_txn(ops,**kwargs)
                    except AuthorityUncertain as exc:
                        assert type(exc.__cause__) is CoordinationLost,'NOT_ACTUAL_NATIVE_409'
                        races[-1]['native_rejection']='PINNED_GRID_COORDINATION_LOST_HTTP409';rejected=True;raise
                return await native_txn(ops,**kwargs)
            store._txn=change_before_read_txn
            try:
                reply=await get(original);error(reply,503,'ADMISSION_UNAVAILABLE','PROVIDER_UNAVAILABLE')
                assert injected and rejected
            finally:store._txn=native_txn
            reply=await unchanged_get(original);assert reply[0]==200
            _,index=await read(receipt_key);assert decode(reply[1])['receipt_modify_index']==str(index)
            events.append('GET503_'+kind+'_INDEX_RACE_ACTUAL_NATIVE_REJECTION')
        for request,field,event in [(original,'request_id','GET503_HASH_CONSISTENT_ORIGINAL_BODY_UUID_MISMATCH'),(subscribe_request,'expected_connection_epoch','GET503_HASH_CONSISTENT_ORIGINAL_BODY_EPOCH_MISMATCH'),(original,'profile','GET503_HASH_CONSISTENT_ORIGINAL_PROFILE_MISMATCH')]:
            ixkey=store.prefix+'requests/'+request;ix=decode((await read(ixkey))[0]);keys=store._keys(request,ix['command_key_sha256'],ix['receipt_ref'])
            saved={key:(await read(key))[0] for key in keys};cmd=decode(saved[keys[1]]);receipt=decode(saved[keys[2]]);result=decode(saved[keys[3]])
            pre=cmd['original_preimage'];body=decode(cmd['original_body_ascii'].encode())
            if field=='profile':pre['profile_schema_sha256']='f'*64
            else:
                body[field]=str(uuid.uuid4()) if field=='request_id' else str(int(body[field])+1)
                cmd['original_body_ascii']=encode(body).decode();pre['canonical_body_sha256']=hashlib.sha256(cmd['original_body_ascii'].encode()).hexdigest()
            digest=hashlib.sha256(encode(pre)).hexdigest();cmd['command_digest']=ix['command_digest']=receipt['command_digest']=result['command_digest']=digest
            response=encode(result);cmd['result_sha256']=receipt['canonical_response_sha256']=hashlib.sha256(response).hexdigest()
            try:
                for key,value in zip(keys,(encode(ix),encode(cmd),encode(receipt),response)):await put(key,value)
                error(await unchanged_get(request),503,'ADMISSION_UNAVAILABLE','RECEIPT_AMBIGUOUS')
            finally:
                for key,raw in saved.items():await put(key,raw)
            events.append(event)
        ix=decode((await read(store.prefix+'requests/'+close_request))[0]);response_key=store.prefix+'responses/'+ix['receipt_ref'];saved,_=await read(response_key)
        try:
            await put(response_key,None);error(await unchanged_get(close_request),503,'ADMISSION_UNAVAILABLE','RECEIPT_AMBIGUOUS')
        finally:await put(response_key,saved)
        events.append('GET503_MISSING_LINKED_TERMINAL_RESPONSE_AMBIGUOUS')
    return dict(events=events,index_races=races,owned_http_thread_stopped=True,native_identity='SYNTHETIC_CAUSE_MAPPING_ONLY')

async def get_after_leader_or_quorum_loss(store,context,original,*,no_quorum=False):
    provider=SyntheticReadProvider(context);read_store=MuxAuthority(store.authority,store.generation,admission=provider)
    box=[ControlMuxRuntime(store=read_store,admission=provider)];binding=[context.native_handle]
    async with actual_http(box,binding) as get:
        response=await get(original)
        if no_quorum:error(response,503,'ADMISSION_UNAVAILABLE','PROVIDER_UNAVAILABLE')
        else:assert response[0]==200 and decode(response[1])['receipt']['http_status']=='201',response
    return 'GET503_ACTUAL_ONE_OF_THREE_NO_QUORUM_NO_HISTORY_SUCCESS' if no_quorum else 'GET200_HISTORY_AFTER_APP_LEADER_RELEASED_NO_LEASE_PROVIDER'
