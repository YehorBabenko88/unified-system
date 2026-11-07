"""Additional actual private Consul assertions; immutable product files untouched."""
import hashlib,importlib.util,json,pathlib,sys
r=pathlib.Path(__file__).resolve().parents[1];root=r/'work/review-mux-5fd0ccb';grid=r/'work/review-grid58cfe';out=r/'outputs/phase48';head='5fd0ccbd28c79fb5ff040ecb1030462ac4baef35'
spec=importlib.util.spec_from_file_location('a8_source_runner',root/'tests/control_mux/source_runner.py');guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
before=guard.source_receipt(root,head);gbefore=guard.source_receipt(grid,'58cfe0f51bc05bb0ee2ed09368a9b64679358c63')
sys.path.insert(0,str(root/'tests/control_mux'))
script=root/'tests/control_mux/test_real_consul.py';raw=script.read_bytes();marker="                report['events'].append('ACTUAL_SUBSCRIBE_CONTROL_SLOT_AND_IMMUTABLE_REPLAY')"
extra='''
                a8_meta=decode((await store._read(store.prefix+'subscriptions/'+sub['subscription_id'])).raw)
                a8_snapshot=decode((await store._read(store.prefix+'snapshots/'+sub['snapshot_id'])).raw)
                a8_subledger=decode((await store._read(store.prefix+'owners/'+context.quota_owner_id+'/subscriptions')).raw)
                assert a8_meta['state']=='WAIT_SOURCE' and a8_snapshot['state']=='WAIT_SOURCE'
                assert next(e for e in a8_subledger['entries'] if e['subscription_id']==sub['subscription_id'])['state']=='WAIT_SOURCE'
                assert all(a8_snapshot[k] is None for k in ('body_sha256','cursor','view_ref'))
                report['events'].append('A8_ACTUAL_WAIT_SOURCE_LEDGER_METADATA_SNAPSHOT_NO_LIVE')
                a8_before=await authority._request('GET','/v1/kv/'+store.prefix,params={'consistent':'','recurse':''})
                a8_req=str(uuid.uuid4());a8_body=encode(dict(schema='unified.control.subscription-open.v3',request_id=a8_req,kind='DATASET',selector=dict(kind='DATASET',dataset_id=str(uuid.uuid4()),source_id=None,partition_id=None),expected_connection_epoch=opened['connection_epoch']))
                a8_cmd=prepare_subscribe(context,a8_body,a8_req,'a8-dataset-denied',opened['connection_id'],opened['connection_epoch'])
                a8_denied=await store.subscribe(lease,context,a8_cmd)
                assert a8_denied.kind=='UNAVAILABLE'
                assert a8_before==await authority._request('GET','/v1/kv/'+store.prefix,params={'consistent':'','recurse':''})
                report['events'].append('A8_ACTUAL_DATASET_UNAVAILABLE_WHOLE_PRIVATE_NAMESPACE_UNCHANGED')
'''
text=raw.decode();assert text.count(marker)==1;text=text.replace(marker,marker+'\n'+extra)
sys.argv=[str(script),'--binary',str(r/'work/consul-bin/extracted/consul.exe'),'--scratch',str(r/'work/mux5-a8-supplement-data'),'--grid-source',str(grid),'--output',str(out/'actual-supplement.json')]
exec(compile(text,str(script)+'<a8-extra-assertions>','exec'),dict(__name__='__main__',__file__=str(script)))
assert before==guard.source_receipt(root,head) and gbefore==guard.source_receipt(grid,'58cfe0f51bc05bb0ee2ed09368a9b64679358c63')
a=json.loads((out/'actual-supplement.json').read_bytes());assert a['result']=='PASS' and a['owned_processes_stopped'] and len(a['events'])==30
(out/'supplement-source-verification.json').write_text(json.dumps(dict(head=head,original_test_script_sha256=hashlib.sha256(raw).hexdigest(),derived_in_memory_script_sha256=hashlib.sha256(text.encode()).hexdigest(),primary_raw_files=len(before['raw_files']),grid_raw_files=len(gbefore['raw_files']),raw_before_after_equal=True,additional_actual_cases=2,scope='REAL_CONSUL_SYNTHETIC_IDENTITY_METADATA_ONLY',native_authentication=False,physical='BLOCKED'),indent=2),encoding='utf-8')
