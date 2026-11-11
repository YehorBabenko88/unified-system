import pathlib,sys,json,copy
from unittest.mock import patch
sys.path[:0]=[str(pathlib.Path.cwd()),str(pathlib.Path.cwd()/'tests'),str(pathlib.Path.cwd()/'tests/gateway_runtime')]
import test_query_front as qf
from unified_system.storage.object_store import ObjectStore
original=ObjectStore.read;results=[]
for mode in ['wrong_view','unregistered_peer','revoke_after_sixth_read','audit_corrupt_after_sixth_read','injected_source_path']:
 f=qf.QueryFrontTests();f.setUp();reads=[]
 try:
  if mode=='unregistered_peer':f.fixture.profile['clients'][0]['certificate_sha256']='f'*64
  front=f.start();request=copy.deepcopy(f.request)
  if mode=='wrong_view':request['consumer_context']['view_id']='22222222-2222-4222-8222-222222222222'
  if mode=='injected_source_path':request['source_path']='A8_PRIVATE_UNTRUSTED_SOURCE_PATH'
  def read(store,*a,**k):
   raw=original(store,*a,**k)
   if store is f.fixture.store:
    reads.append(a[0])
    if len(reads)==6:
     if mode=='revoke_after_sixth_read':front._manifest_composition.authority.revoke_service(qf.fixtures.U)
     if mode=='audit_corrupt_after_sixth_read':f.fixture.audit.path.write_bytes(b'A8_OWN_AUDIT_CORRUPTION_AFTER_ACTUAL_READS')
   return raw
  with patch.object(ObjectStore,'read',read):headers,response=f.get(front,request)
  code=int(headers.split(b' ')[1]);assert code=={'wrong_view':403,'unregistered_peer':401,'revoke_after_sixth_read':403,'audit_corrupt_after_sixth_read':503,'injected_source_path':400}[mode],(mode,code,response)
  assert len(reads)==(6 if mode in ['revoke_after_sixth_read','audit_corrupt_after_sixth_read'] else 0)
  assert 'owner_result' not in response and 'rows' not in response and 'A8_PRIVATE' not in json.dumps(response)
  if mode=='audit_corrupt_after_sixth_read':assert f.fixture.audit.path.read_bytes()==b'A8_OWN_AUDIT_CORRUPTION_AFTER_ACTUAL_READS'
  results.append(dict(case=mode,status=code,actual_ObjectStore_class_reads=len(reads),owner_output_withheld=True))
 finally:f.doCleanups()
print(json.dumps(dict(scope='OWN_DISPOSABLE_ACTUAL_HTTPS_READ_ONLY',cases=results,no_job_or_publication_or_native_actions=True),indent=2))
