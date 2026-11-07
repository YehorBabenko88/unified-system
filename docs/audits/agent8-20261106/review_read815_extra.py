import pathlib,subprocess,os
r=pathlib.Path.cwd();o=r/'outputs/phase89';repo=r/'work/review-read815';grid=r/'work/read815-a8-grid-f19'
s='''import pathlib,sys,json,hashlib,socket,time,copy
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
root=pathlib.Path.cwd();sys.path[:0]=[str(root),str(root/'tests'),str(root/'tests/gateway_runtime')]
import test_manifest_front as mf
import test_query_front as qf
from unified_system.storage.object_store import ObjectStore
actual=ObjectStore.read
results=[]
def manifest_case(mode):
 f=mf.ManifestFrontTests();f.setUp();reads=[];instance=[]
 try:
  if mode=='expiry':
   expiry=(datetime.now(timezone.utc)+timedelta(seconds=3)).replace(microsecond=0);f.profile['clients'][0]['expires_utc']=expiry.strftime('%Y-%m-%dT%H:%M:%SZ')
  front=f.start();original_instance=f.store.read;f.store.read=lambda *a,**k:(instance.append(1),original_instance(*a,**k))[1]
  def read(store,*a,**k):
   raw=actual(store,*a,**k)
   if store is f.store:
    reads.append(a[0])
    if mode=='revoke_during_read':front._manifest_composition.authority.revoke_service(mf.U)
   return raw
  request=copy.deepcopy(f.request)
  if mode=='wrong_view':request['view_id']='22222222-2222-4222-8222-222222222222'
  if mode=='expiry':time.sleep(max(0,(expiry-datetime.now(timezone.utc)).total_seconds())+.1)
  if mode=='audit_corrupt':f.audit.path.write_bytes(b'OWN_A8_SYNTHETIC_AUDIT_CORRUPTION')
  with patch.object(ObjectStore,'read',read):headers,body=f.request_front(front,request)
  code=int(headers.split(b' ')[1]);expected={'positive':200,'wrong_view':403,'expiry':401,'revoke_during_read':503,'audit_corrupt':503}[mode];assert code==expected,(mode,code,body)
  assert len(reads)==(1 if mode in ('positive','revoke_during_read') else 0)
  if mode=='positive':
   events=[e for r in f.audit.read() for e in r['receipt']['events']];assert sum(e['decision']=='READ_CURRENT_CHECK' for e in events)==2
   assert instance==[] # Fixed class read bypasses the instance monkeypatch used by one Root counter test.
  if mode=='audit_corrupt':assert f.audit.path.read_bytes()==b'OWN_A8_SYNTHETIC_AUDIT_CORRUPTION'
  if code!=200:assert 'manifest' not in body and 'rows' not in body
  results.append(dict(case=mode,HTTP_status=code,actual_class_ObjectStore_reads=len(reads),instance_monkeypatch_observed_reads=len(instance),manifest_disclosed=code==200))
 finally:f.doCleanups()
for mode in ['positive','wrong_view','expiry','revoke_during_read','audit_corrupt']:manifest_case(mode)
f=qf.QueryFrontTests();f.setUp();f.addCleanup(f.fixture.doCleanups);reads=[]
try:
 front=f.start();packet=root/'release/evidence/gateway-runtime-contiguous-read-20261107';raw=(packet/'query-request.canonical.json').read_bytes();request=json.loads(raw);assert json.dumps(request,sort_keys=True,separators=(',',':')).encode()==raw
 def read(store,*a,**k):
  out=actual(store,*a,**k)
  if store is f.fixture.store:reads.append(a[0])
  return out
 with patch.object(ObjectStore,'read',read):
  with f.fixture.client_context.wrap_socket(socket.create_connection(front.address,timeout=3),server_hostname='127.0.0.1') as s:
   assert s.getpeercert(binary_form=True)==f.fixture.tls.server_der;s.sendall((f'POST /intelligence/v1/query HTTP/1.1\\r\\nHost: 127.0.0.1:{front.address[1]}\\r\\nContent-Type: application/json\\r\\nContent-Length: {len(raw)}\\r\\n\\r\\n').encode()+raw);chunks=[]
   while data:=s.recv(8192):chunks.append(data)
 wire=b''.join(chunks);headers,body=wire.split(b'\\r\\n\\r\\n',1);assert headers.startswith(b'HTTP/1.1 200 ');response=json.loads(body);owner=json.dumps(response['owner_result'],sort_keys=True,separators=(',',':')).encode();assert len(reads)==6
 assert body==(packet/'gateway-response.json').read_bytes() and owner==(packet/'query-result.canonical.json').read_bytes()
 assert len(response['owner_result']['rows'])==len(response['owner_result']['cells'])==1
 events=[e for r in f.fixture.audit.read() for e in r['receipt']['events']];assert sum(e['decision']=='READ_CURRENT_CHECK' for e in events)==7
 summary=dict(manifest_cases=results,query=dict(actual_fresh_HTTPS_ONEBAR=True,actual_ObjectStore_reads=6,actual_fixed_issuer_checks=7,request_bytes=len(raw),request_sha256=hashlib.sha256(raw).hexdigest(),owner_bytes=len(owner),owner_sha256=hashlib.sha256(owner).hexdigest(),HTTP_body_bytes=len(body),HTTP_body_sha256=hashlib.sha256(body).hexdigest(),archived_owner_result_body_byte_equal=True,provider_coverage=response['owner_result']['provider_coverage'],publication=response['owner_result']['publication'],artifact_published=response['artifact_published']),root_manifest_counter_gap='INSTANCE_READ_PATCH_REPORTS0_EVEN_ACTUAL_POSITIVE_CLASS_READ1',scope='DISPOSABLE_ACTUAL_mTLS_EXPECTED_ISSUER_IMMUTABLE_SYNTHETIC_READ_ONLY_NOT_JOB_E2E')
 print(json.dumps(summary,indent=2))
finally:f.doCleanups()
'''
(o/'extra-executed.py').write_text(s,encoding='utf-8');env=os.environ.copy();env['GRID_GATEWAY_SOURCE_ROOT']=str(grid);env['A4_COMPONENT_ROOT']=str(repo);p=subprocess.run([str(r/'work/identity-a8-env/Scripts/python.exe'),'-I','-B','-c',s],cwd=repo,env=env,capture_output=True,timeout=70);(o/'extra.stdout.json').write_bytes(p.stdout);(o/'extra.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr;print(p.stdout.decode())
