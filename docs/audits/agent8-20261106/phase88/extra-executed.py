import pathlib,sys,importlib.util,json,os,hashlib
repo=pathlib.Path.cwd();spec=importlib.util.spec_from_file_location('a8_research_adapter',repo/'strattester/research/gateway_adapter.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
raw=(repo/'docs/gateway/research/evidence/btc-v1/request.json').read_bytes();original=(repo/'docs/gateway/research/evidence/btc-v1/meta-result.json').read_bytes();descriptor=(repo/'docs/gateway/research/evidence/btc-v1/descriptor.json').read_bytes();meta=sys.argv[1]
reads=[]
def audit(event,args):
 if event in ('socket.connect','socket.bind','subprocess.Popen','os.system'):raise AssertionError('FORBIDDEN_EFFECT:'+event)
 if event=='open':
  path,mode,flags=args
  if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):raise AssertionError('FILE_WRITE')
  reads.append(str(path))
sys.addaudithook(audit)
try:m.execute_synthetic_research(raw,meta_source_root=meta,cancel_check=lambda:True);raise AssertionError('PRECANCELLED_RESULT')
except m.GatewayResearchCancelled:pass
assert not reads
calls=[]
class ForeignAwaitable:
 def __await__(self):calls.append('await');yield
 def close(self):calls.append('close')
 def cancel(self):calls.append('cancel')
a=ForeignAwaitable()
try:m.execute_synthetic_research(raw,meta_source_root=meta,cancel_check=lambda:a);raise AssertionError('AWAITABLE_ACCEPTED')
except m.GatewayResearchError as e:assert e.code=='INVALID_CANCEL_CHECK'
assert calls==[]
finalized=[]
class Pause:
 def __await__(self):yield 'OWN_SUSPENDED'
async def foreign():
 try:await Pause()
 finally:finalized.append('ACTUAL_OWNER_DISPOSED')
c=foreign();c.send(None)
try:
 try:m.execute_synthetic_research(raw,meta_source_root=meta,cancel_check=lambda:c);raise AssertionError('COROUTINE_ACCEPTED')
 except m.GatewayResearchError as e:assert e.code=='INVALID_CANCEL_CHECK'
 assert finalized==[]
finally:c.close()
assert finalized==['ACTUAL_OWNER_DISPOSED']
count=[0]
def cancel_after_calculation():count[0]+=1;return count[0]==3
try:m.execute_synthetic_research(raw,meta_source_root=meta,cancel_check=cancel_after_calculation);raise AssertionError('POSTCALC_RESULT_RETURNED')
except m.GatewayResearchCancelled:pass
assert not any(n.startswith('_stratt_gateway_meta_') for n in sys.modules)
value=m.execute_synthetic_research(raw,meta_source_root=meta,cancel_check=lambda:False);assert value['artifact_bytes']==original and m._canonical(value['descriptor'])==descriptor
levels=json.loads(value['artifact_bytes'])['levels'];assert [(x['kind'],x['price'],x['source_start_ms']) for x in levels]==[('low','8',0),('low','9',60000),('high','12',120000),('low','10',120000)]
d=value['descriptor'];assert all(v is None for k,v in d['financial'].items() if k not in ('status','calculation_basis'));assert d['provenance']['dataset_revision']=='UNAVAILABLE_A4_BINDING_PENDING' and d['production_runtime_admission']=='BLOCKED';assert not any(n.startswith('_stratt_gateway_meta_') for n in sys.modules)
print(json.dumps(dict(scope='ACTUAL_PINNED_PURE_META_SYNTHETIC_ONLY',precancel_before_any_source_read=True,foreign_await_close_cancel_calls=calls,foreign_coroutine_disposed_only_by_creator=True,cancel_after_actual_calculation_discards_output=True,unique_namespace_cleanup=True,original_artifact_sha256=hashlib.sha256(original).hexdigest(),original_descriptor_sha256=hashlib.sha256(descriptor).hexdigest(),hand_expected_four_levels_equal=True,finance_null_profile_none=True,write_network_process_tripwire='NO_CALLS',source_revision_or_dataset_authenticity='NOT_PROVEN',publication='NONE',shared_job_runtime='NOT_RUN'),indent=2))
