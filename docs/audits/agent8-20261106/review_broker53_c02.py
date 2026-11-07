import pathlib,subprocess,os,hashlib,json,io
r=pathlib.Path.cwd();o=r/'outputs/phase98';repo=r/'work/review-broker53-c02';grid=r/'work/broker53-a8-grid40';head='c02b110a8939674adc676cb203e0d71ffab800d0'
def inventory(path):
 def g(*a,data=None):return subprocess.check_output(['git','--no-replace-objects','-C',str(path),*a],input=data)
 rows=[]
 for row in g('ls-tree','-rz','HEAD').split(b'\0'):
  if row:
   meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();assert kind==b'blob';rows.append((name.decode(),oid.decode()))
 s=io.BytesIO(g('cat-file','--batch',data=''.join(oid+'\n' for _,oid in rows).encode()));rawmap={}
 for name,oid in rows:
  actual,kind,size=s.readline().split();b=s.read(int(size));assert s.read(1)==b'\n' and actual.decode()==oid and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==oid and (path/name).read_bytes()==b;rawmap[name]=hashlib.sha256(b).hexdigest()
 for p in path.rglob('*'):
  rel=p.relative_to(path)
  if rel.parts[0]!='.git' and p.is_file():assert rel.as_posix() in rawmap
 return rawmap
before=inventory(repo);gbefore=inventory(grid);assert len(before)==1511 and len(gbefore)==695 and before['unified_system/gateway_research_identity.py']=='81ca69e9de3789c21beb96176efc2e4c60106e240f96562017bbd5cc3b89d961';binary=r/'work/consul-bin/extracted/consul.exe';assert hashlib.sha256(binary.read_bytes()).hexdigest()=='41762ef5b98c8dd9b6852df6cfbceed37e7f0acc5760856be33100f1092475e1'
env={k:v for k,v in os.environ.items() if not k.upper().startswith('GIT_')};env.update(A2_RESEARCH_CONSUL_BINARY=str(binary),A2_RESEARCH_EVIDENCE_OUT=str(o/'own-native-evidence'),PYTHONDONTWRITEBYTECODE='1')
p=subprocess.run([str(r/'work/broker53-a8-env/Scripts/python.exe'),'-I','-B',str(repo/'docs/intelligence/research-identity/run_qualification.py'),'--expected-head',head,'--grid-source',str(grid)],cwd=repo,env=env,capture_output=True,timeout=180);(o/'own15.stdout.log').write_bytes(p.stdout);(o/'own15.stderr.log').write_bytes(p.stderr);assert inventory(repo)==before and inventory(grid)==gbefore;assert p.returncode==0,p.stderr.decode(errors='replace')[-2000:];print(p.stdout.decode())
(o/'primary-verification.json').write_text(json.dumps(dict(head=head,tree=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD^{tree}']).decode().strip(),tests=15,skips=0,Unified_primary_raw_prepost=1511,Grid_primary_raw_prepost=695,Unified_source_raw=before,Grid_source_raw=gbefore,actual_own_TLS_Consul=True,scope='ISOLATED_PRINCIPAL_SESSION_NOT_JOB_OR_WORKER'),indent=2))
