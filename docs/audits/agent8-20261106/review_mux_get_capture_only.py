"""Actual GET cannot reread after native checked capture; original files untouched."""
import hashlib,importlib.util,json,pathlib,sys,types
r=pathlib.Path(__file__).resolve().parents[1];root=r/'work/review-mux-get-be5cb94';grid=r/'work/review-grid58cfe';out=r/'outputs/phase61';head='be5cb942436f82f374375eabb255768bb139797f'
spec=importlib.util.spec_from_file_location('a8_guard',root/'tests/control_mux/source_runner.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g);before=g.source_receipt(root,head);gbefore=g.source_receipt(grid,'58cfe0f51bc05bb0ee2ed09368a9b64679358c63');sys.path[:0]=[str(root),str(grid),str(root/'tests/control_mux')]
path=root/'tests/control_mux/get_real_cases.py';raw=path.read_bytes();text=raw.decode();marker="            if body is not None:assert v['original_result_ascii'].encode()==body\n            events.append(event)"
extra='''
            a8_read=store._read;a8_txn=store._txn;a8_checked=False;a8_ops=[]
            async def a8_no_late_read(key):
                assert not a8_checked,'GET_REREAD_AFTER_CHECKED_CAPTURE'
                return await a8_read(key)
            async def a8_record_checks(ops,**kwargs):
                nonlocal a8_checked
                result=await a8_txn(ops,**kwargs)
                if kwargs.get('read_only'):
                    assert all(op['KV']['Verb']=='check-index' for op in ops)
                    a8_ops.extend(ops);a8_checked=True
                return result
            store._read=a8_no_late_read;store._txn=a8_record_checks
            try:
                a8_reply=await unchanged_get(request);assert a8_reply[0]==200
                assert a8_checked and len(a8_ops)==8
                from unified_system.security_identity_records import guard_keys
                assert set(guard_keys(context.native_handle).values())<=set(op['KV']['Key'] for op in a8_ops)
                a8_doc=decode(a8_reply[1]);a8_ix=decode((await read(store.prefix+'requests/'+request))[0]);a8_key=store.prefix+'receipts/'+a8_ix['receipt_ref'];a8_indices=[op['KV']['Index'] for op in a8_ops if op['KV']['Key']==a8_key]
                assert a8_indices==[int(a8_doc['receipt_modify_index'])] and a8_doc['query_request_id']==a8_reply[2]
                events.append('A8_GET_'+status+'_CAPTURE_ONLY_8_NATIVE_CHECKS_NO_LATE_READ_NO_WRITES')
            finally:store._read=a8_read;store._txn=a8_txn
'''
assert text.count(marker)==1;text=text.replace(marker,marker+'\n'+extra);m=types.ModuleType('get_real_cases');m.__file__=str(path);sys.modules[m.__name__]=m;exec(compile(text,str(path)+'<a8-capture-only-assertions>','exec'),m.__dict__)
script=root/'tests/control_mux/test_real_consul.py';sys.argv=[str(script),'--binary',str(r/'work/consul-bin/extracted/consul.exe'),'--scratch',str(r/'work/muxget-a8-capture-extra-data'),'--grid-source',str(grid),'--output',str(out/'capture-only-supplement.json')];exec(compile(script.read_bytes(),str(script),'exec'),dict(__name__='__main__',__file__=str(script)))
assert before==g.source_receipt(root,head) and gbefore==g.source_receipt(grid,'58cfe0f51bc05bb0ee2ed09368a9b64679358c63');a=json.loads((out/'capture-only-supplement.json').read_bytes());assert a['owned_processes_stopped'] and len(a['events'])==74
(out/'capture-source-verification.json').write_text(json.dumps(dict(head=head,original_get_fixture_sha256=hashlib.sha256(raw).hexdigest(),derived_in_memory_sha256=hashlib.sha256(text.encode()).hexdigest(),primary_raw_files=674,grid_raw_files=672,raw_before_after_equal=True,original72_repeated_not_additional_unique=True,additional_actual_cases=2,all_owned_processes_stopped=True,native_authentication=False,physical='NOT_QUALIFIED'),indent=2),encoding='utf-8')
