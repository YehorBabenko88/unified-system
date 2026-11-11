"""A8 isolated real primitives. Missing integration/native/physical gates stay closed."""
import argparse,base64,hashlib,http.client,ipaddress,json,os,pathlib,socket,subprocess,sys,time,uuid
ROOT=pathlib.Path(__file__).resolve().parents[1]
REQUIRED=('MODEL-CONTRACTS','CODE-INVENTORY','CODE-SOURCE','CODE-CLEANUP','ENDPOINT-CONSUL','ENDPOINT-MTLS','ENDPOINT-HTTP-CLOSED','ENDPOINT-INTEGRATED','WINDOWS-CI','PHYSICAL-CLUSTER')
def decide(rows):
 if set(rows)!=set(REQUIRED):raise ValueError('MANDATORY_CASE_INVENTORY_MISMATCH')
 for name,row in rows.items():
  if row['status'] not in ('PASS','FAIL','BLOCKED','NOT_RUN'):raise ValueError('INVALID_STATUS')
  if name.startswith('ENDPOINT-') and row['status']=='PASS' and row.get('evidence_class')!='REAL_PROCESS':raise ValueError('MOCK_IS_NOT_ENDPOINT_EVIDENCE')
 return 'GO' if all(row['status']=='PASS' for row in rows.values()) else 'NO_GO'
def git(repo,*args):return subprocess.check_output(['git','--no-replace-objects','-c','core.fsmonitor=false','-C',str(repo),*args])
def identity(repo,sha):
 if git(repo,'rev-parse','HEAD').decode().strip()!=sha:raise ValueError('EXACT_HEAD_MISMATCH')
 rows={}
 for item in filter(None,git(repo,'ls-tree','-rz',sha).split(b'\0')):
  meta,name=item.split(b'\t',1);mode,kind,oid=meta.split();path=repo/name.decode()
  if mode not in (b'100644',b'100755') or kind!=b'blob':raise ValueError('NONREGULAR_GIT_INPUT')
  for ancestor in (path,*path.parents):
   if ancestor==repo.parent:break
   stat=ancestor.lstat()
   if ancestor.is_symlink() or getattr(stat,'st_file_attributes',0)&1024:raise ValueError('REPARSE_INPUT')
  raw=path.read_bytes()
  if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=oid.decode():raise ValueError('RAW_BLOB_MISMATCH:'+name.decode())
  rows[name.decode()]=hashlib.sha256(raw).hexdigest()
 return dict(head=sha,tree=git(repo,'rev-parse',sha+'^{tree}').decode().strip(),files=rows)
def request(port,method,path,body=None):
 conn=http.client.HTTPConnection('127.0.0.1',port,timeout=2)
 try:
  conn.request(method,path,body=body);response=conn.getresponse();data=response.read(1024*1024)
  if response.status!=200:raise RuntimeError('LOCAL_CONSUL_HTTP_'+str(response.status))
  return json.loads(data)
 finally:conn.close()
def ports(count):
 socks=[]
 try:
  for _ in range(count):s=socket.socket();s.bind(('127.0.0.1',0));socks.append(s)
  return [s.getsockname()[1] for s in socks]
 finally:
  for s in socks:s.close()
GUARD='''import sys,ipaddress
def guard(event,args):
 if event in ('socket.connect','socket.bind') and (not isinstance(args[1],tuple) or not ipaddress.ip_address(args[1][0]).is_loopback):raise RuntimeError('NONLOOPBACK_DENIED')
sys.addaudithook(guard)
'''
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true');parser.add_argument('--output',type=pathlib.Path,default=ROOT/'outputs/phase33');args=parser.parse_args()
 if not args.execute:parser.error('Use --execute only within already authorized isolated acceptance scope')
 out=args.output.resolve();out.mkdir(exist_ok=False,parents=True);scratch=ROOT/'work'/('phased-lab-'+uuid.uuid4().hex);scratch.mkdir()
 rows={name:dict(status='NOT_RUN',evidence_class='NONE') for name in REQUIRED};handles=[];processes=[];source={};current='CODE-SOURCE';error=None
 def row(name,status,actual,evidence_class='REAL_PROCESS',**extra):
  rows[name]=dict(status=status,evidence_class=evidence_class,actual=actual,environment='OWNED_WINDOWS_LOOPBACK_ONLY',**extra)
 def child(label,repo,code):
  env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')};env.update(PYTHONDONTWRITEBYTECODE='1',TEMP=str(scratch),TMP=str(scratch))
  boot=GUARD+'sys.path.insert(0,'+repr(str(repo))+')\n'+code
  p=subprocess.run([sys.executable,'-I','-B','-c',boot],cwd=repo,env=env,capture_output=True,timeout=45)
  (out/(label+'.stdout.log')).write_bytes(p.stdout);(out/(label+'.stderr.log')).write_bytes(p.stderr)
  if p.returncode:raise RuntimeError(label+'_FAILED_EXIT_'+str(p.returncode))
 try:
  bindings=[('lan',ROOT/'work/review-stage1-lan','1541af3b0e99fdb671f59c205696faab40e283e4'),('control',ROOT/'work/review-stage1-control','7a0365bd0161ec619019157cf04672b513c495c6')]
  for label,repo,sha in bindings:source[label]=identity(repo,sha)
  binary=ROOT/'work/consul-bin/extracted/consul.exe';digest=hashlib.sha256(binary.read_bytes()).hexdigest()
  if digest!='41762ef5b98c8dd9b6852df6cfbceed37e7f0acc5760856be33100f1092475e1':raise ValueError('CONSUL_BINARY_MISMATCH')
  (out/'source-before.json').write_text(json.dumps(source,indent=2))
  row('CODE-SOURCE','PASS','Exact component HEAD/tree/primary raw blobs and Consul binary bound',evidence_class='RAW_SOURCE_CHECK',consul_sha256=digest,harness_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest())
  row('CODE-INVENTORY','PASS','Mandatory case inventory explicitly closed; no functional model claim',evidence_class='REPORTER_INVENTORY_ONLY')
  current='ENDPOINT-CONSUL';portlist=ports(12);nodes=[]
  for i in range(3):
   rpc,lan,wan,http=portlist[4*i:4*i+4];folder=scratch/('consul-'+str(i));folder.mkdir()
   config=dict(server=True,bootstrap_expect=3,datacenter='a8-phased',node_name='a8-phased-'+str(i),data_dir=str(folder/'data'),bind_addr='127.0.0.1',advertise_addr='127.0.0.1',client_addr='127.0.0.1',retry_join=['127.0.0.1:'+str(portlist[j*4+1]) for j in range(3) if j!=i],ports=dict(server=rpc,serf_lan=lan,serf_wan=wan,http=http,https=-1,dns=-1,grpc=-1,grpc_tls=-1),disable_update_check=True,disable_remote_exec=True,enable_script_checks=False,log_level='warn',performance=dict(raft_multiplier=1),raft_logstore=dict(backend='boltdb'),connect=dict(enabled=False))
   path=folder/'config.json';path.write_text(json.dumps(config));log=(out/('consul-'+str(i)+'.log')).open('wb');handles.append(log)
   env=dict(os.environ,CHECKPOINT_DISABLE='1');process=subprocess.Popen([str(binary),'agent','-config-file',str(path)],stdout=log,stderr=subprocess.STDOUT,env=env,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));processes.append(process);nodes.append(http)
  deadline=time.monotonic()+45;last=''
  while True:
   try:
    if any(p.poll() is not None for p in processes):raise RuntimeError('OWNED_CONSUL_EXITED')
    for port in nodes:
     voters=request(port,'GET','/v1/operator/raft/configuration?consistent')['Servers']
     assert len(voters)==3 and sum(x['Leader'] for x in voters)==1 and all(x['Voter'] for x in voters)
    break
   except (OSError,ValueError,AssertionError,RuntimeError) as exc:
    last=type(exc).__name__
    if time.monotonic()>deadline:raise RuntimeError('CONSUL_READY_TIMEOUT_'+last)
    time.sleep(.2)
  key='/v1/kv/a8-phased/'+uuid.uuid4().hex;body=json.dumps(dict(test='synthetic',nonce=uuid.uuid4().hex),sort_keys=True).encode()
  assert request(nodes[0],'PUT',key+'?cas=0',body) is True
  assert request(nodes[1],'PUT',key+'?cas=0',b'counterfeit') is False
  evidence=[]
  for port in nodes:
   value=request(port,'GET',key+'?consistent')[0];assert base64.b64decode(value['Value'])==body;evidence.append(dict(port=port,modify_index=value['ModifyIndex'],value_sha256=hashlib.sha256(body).hexdigest()))
  (out/'consul-consistent-cas.json').write_text(json.dumps(dict(voters=voters,reads=evidence),indent=2));row(current,'PASS','3 actual persistent voters,1 leader; successful CAS, duplicate CAS refused, consistent bytes on3 HTTP endpoints',qualification='REAL_CONSUL_COMPONENT_NOT_CONTROL_MUX_AUTH',consul_acl_tls='NOT_ENABLED_LOOPBACK_TEST_ONLY')
  current='ENDPOINT-MTLS';repo=bindings[0][1]
  child('mtls',repo,"import unittest\nnames=['tests.test_lan_transport.TLSIsolationTests.test_real_mtls_payload_credit_classes_and_actual_byte_accounting','tests.test_lan_transport.TLSIsolationTests.test_fingerprint_and_wrong_uri_cert_rejected','tests.test_lan_transport.TLSIsolationTests.test_wrong_eku_and_expired_cert_rejected']\nr=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names));assert r.wasSuccessful() and r.testsRun==3 and not r.skipped\n")
  row(current,'PASS','3 selected actual loopback TLS tests; payload/credit/accounting and pin/SAN/EKU/expiry rejection',qualification='REAL_LAN_TRANSPORT_COMPONENT_ONLY_NOT_CONSUL_BRIDGE')
  current='ENDPOINT-HTTP-CLOSED';repo=bindings[1][1]
  child('http-closed',repo,"from tests.control_v3.fixture_server import fixture_server\nfrom unified_system.control_v3_boundary import ControlV3App,ROOT\nfrom urllib.request import Request,urlopen\nfrom urllib.error import HTTPError\nimport json\nwith fixture_server(ControlV3App()) as url:\n try:urlopen(Request(url+ROOT+'snapshot?scope=CONTROL&dataset_id=~&source_id=~&partition_id=~',headers={'Authorization':'Bearer forged'}),timeout=2)\n except HTTPError as e:\n  body=json.loads(e.read());assert e.code==503 and body['code']=='AUTHENTICATION_UNAVAILABLE' and body['native_admission'] is False and 'resources' not in body;print(json.dumps(body))\n else:raise AssertionError('default boundary opened')\n")
  row(current,'PASS','Actual HTTP503 from default app with forged Authorization; no synthetic success provider',qualification='CLOSED_HTTP_ENDPOINT_ONLY_NOT_AUTHENTICATED_READ')
  for label,repo,sha in bindings:
   if source[label]!=identity(repo,sha):raise ValueError('SOURCE_CHANGED_AFTER_EXECUTION')
  (out/'source-after.json').write_text(json.dumps(source,indent=2))
 except BaseException as exc:
  error=type(exc).__name__+':'+str(exc)[:300];row(current,'FAIL',error)
 finally:
  for process in processes:
   if process.poll() is None:process.kill()
   process.wait(timeout=10)
  for handle in handles:handle.close()
  stopped=all(p.poll() is not None for p in processes);row('CODE-CLEANUP','PASS' if stopped else 'FAIL','Only owned Popen handles stopped',pids=[p.pid for p in processes],all_owned_stopped=stopped)
  row('ENDPOINT-INTEGRATED','BLOCKED','No published admitted real ConsulMux+LAN+mTLS+HTTP bridge exact pin; primitives do not establish integrated endpoint',evidence_class='MISSING_REAL_ADAPTER')
  row('MODEL-CONTRACTS','NOT_RUN','No fresh Review4 model suite executed in this primitive preparation lane',evidence_class='NOT_EVALUATED')
  row('WINDOWS-CI','BLOCKED','Local Windows execution does not qualify mandatory hosted Windows matrix',evidence_class='NO_HOSTED_ARTIFACT')
  row('PHYSICAL-CLUSTER','BLOCKED','Office fault injection/provider/native provisioning prohibited',evidence_class='NOT_AUTHORIZED')
  result=dict(schema='agent8.phased-isolated-acceptance.v1',cases=rows,phase_status=dict(MODEL='NOT_RUN',CODE='PASS' if not error and stopped else 'FAIL',ENDPOINT='BLOCKED',WINDOWS='BLOCKED',PHYSICAL='BLOCKED'),mandatory_inventory=list(REQUIRED),skip_inventory=[],case_count=len(rows),overall=decide(rows),error=error,review4_design_pin='360c5cdc9dae88416d69f8765f3dff5ab8828945',source=source,qualification='SEPARATE_REAL_PRIMITIVES_NOT_INTEGRATED_ENDPOINT_PASS',tailscale_removal='BLOCKED',physical='BLOCKED',production='NOT_AUTHORIZED',python=sys.version)
  (out/'phased-acceptance.json').write_text(json.dumps(result,indent=2))
  index={p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()};(out/'artifact-sha256.json').write_text(json.dumps(index,indent=2));print(json.dumps(dict(overall=result['overall'],error=error,all_owned_stopped=stopped,cases={name:row['status'] for name,row in rows.items()})))
 return 1 if error else 0
if __name__=='__main__':raise SystemExit(main())
