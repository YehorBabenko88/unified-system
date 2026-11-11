"""Extra actual native-rejection cause and absent-write assertions, no source edit."""
import hashlib,importlib.util,json,pathlib,sys,types
r=pathlib.Path(__file__).resolve().parents[1];root=r/'work/review-mux-08d6f01';grid=r/'work/review-grid58cfe';out=r/'outputs/phase49';head='08d6f01d94feb44a17338be8ef3f8871995c284a'
spec=importlib.util.spec_from_file_location('a8_guard',root/'tests/control_mux/source_runner.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
before=g.source_receipt(root,head);gbefore=g.source_receipt(grid,'58cfe0f51bc05bb0ee2ed09368a9b64679358c63');sys.path[:0]=[str(root),str(grid),str(root/'tests/control_mux')]
path=root/'tests/control_mux/record_negatives.py';raw=path.read_bytes();text=raw.decode();old='''                    except AuthorityUncertain:
                        native_rejected=True;raise''';new='''                    except AuthorityUncertain as a8_exc:
                        from grid.coordination import CoordinationLost
                        assert isinstance(a8_exc.__cause__,CoordinationLost),('NOT_NATIVE_CONSUL_409',type(a8_exc.__cause__).__name__)
                        assert str(a8_exc.__cause__)=='Consul fencing transaction rejected'
                        race_evidence[-1]['actual_grid_cause']=type(a8_exc.__cause__).__name__
                        race_evidence[-1]['native_rejection_evidence']='HTTP409_INFERRED_FROM_ACTUAL_GRID_CAUSE'
                        race_evidence[-1]['attempted_native_ops']=ops
                        native_rejected=True;raise'''
assert text.count(old)==1;text=text.replace(old,new)
old="                if window=='PREPARE':assert index is None,'REVOKED_PREPARATION_PERSISTED'"
new="""                if window=='PREPARE':
                    assert index is None,'REVOKED_PREPARATION_PERSISTED'
                    assert await read(store.prefix+'commands/'+command.key_sha256) is None,'REVOKED_PREPARE_COMMAND_PERSISTED'"""
assert text.count(old)==1;text=text.replace(old,new)
old="                    assert await read(store.prefix+'receipts/'+index['receipt_ref']) is None,'REVOKED_FINAL_RECEIPT_WRITTEN'"
new=old+"\n                    assert await read(store.prefix+'responses/'+index['receipt_ref']) is None,'REVOKED_FINAL_RESPONSE_WRITTEN'\n                    assert len(holds['entries'])<=14 and sum(int(e['bytes']) for e in holds['entries'])<=131072"
assert text.count(old)==1;text=text.replace(old,new)
m=types.ModuleType('record_negatives');m.__file__=str(path);sys.modules[m.__name__]=m;exec(compile(text,str(path)+'<a8-extra-native-assertions>','exec'),m.__dict__)
script=root/'tests/control_mux/test_real_consul.py';sys.argv=[str(script),'--binary',str(r/'work/consul-bin/extracted/consul.exe'),'--scratch',str(r/'work/mux8-a8-native-extra-data'),'--grid-source',str(grid),'--output',str(out/'native-rejection-supplement.json')]
exec(compile(script.read_bytes(),str(script),'exec'),dict(__name__='__main__',__file__=str(script)))
assert before==g.source_receipt(root,head) and gbefore==g.source_receipt(grid,'58cfe0f51bc05bb0ee2ed09368a9b64679358c63')
a=json.loads((out/'native-rejection-supplement.json').read_bytes());assert a['owned_processes_stopped'] and len(a['events'])==42 and len(a['identity_race_fencing'])==8
for row in a['identity_race_fencing']:assert row['changed_index']>row['checked_index'] and hashlib.sha256(json.dumps(row['attempted_native_ops'],separators=(',',':')).encode()).hexdigest()==row['native_transaction_sha256']
(out/'native-supplement-source-verification.json').write_text(json.dumps(dict(head=head,original_negative_module_sha256=hashlib.sha256(raw).hexdigest(),derived_in_memory_sha256=hashlib.sha256(text.encode()).hexdigest(),raw_before_after_equal=True,primary_raw_files=len(before['raw_files']),grid_raw_files=len(gbefore['raw_files']),original_events_repeated_not_additional_unique=42,enhanced_identity_windows=8,native_authentication=False,physical='BLOCKED'),indent=2),encoding='utf-8')
