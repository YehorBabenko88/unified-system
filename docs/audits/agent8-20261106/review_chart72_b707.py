import pathlib,subprocess,json,os,hashlib,io
r=pathlib.Path.cwd();repo=r/'work/review-chart72-b707';o=r/'outputs/phase92';o.mkdir(exist_ok=True);head='b70725220eed43e371a3c08f1c87fcabd984a45d'
subprocess.run(['git','clone','--no-hardlinks','--no-checkout',str(r/'work/terminan-isolated'),str(repo)],check=True,capture_output=True);subprocess.run(['git','-c','core.autocrlf=false','-c','core.eol=lf','-C',str(repo),'checkout','--detach',head],check=True,capture_output=True)
def g(*a,data=None):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a],input=data)
rows=[]
for line in g('ls-tree','-rz','HEAD').split(b'\0'):
 if line:
  meta,name=line.split(b'\t',1);mode,kind,oid=meta.split();assert kind==b'blob';rows.append((name.decode(),oid.decode()))
s=io.BytesIO(g('cat-file','--batch',data=''.join(oid+'\n' for _,oid in rows).encode()));rawmap={}
for name,oid in rows:
 actual,kind,size=s.readline().split();b=s.read(int(size));assert s.read(1)==b'\n' and actual.decode()==oid and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==oid and (repo/name).read_bytes()==b;rawmap[name]=hashlib.sha256(b).hexdigest()
assert len(rawmap)==371
workflow=(repo/'.github/workflows/gateway-artifacts.yml').read_bytes();(o/'workflow.original.yml').write_bytes(workflow);code='\n'.join(x[10:] if x.startswith('          ') else x for x in workflow.decode().split("$taskCode = @'\n",1)[1].split("          '@",1)[0].splitlines());bootstrap=r/'work/chart72-bootstrap.cjs';bootstrap.write_text(code);(o/'bootstrap-executed.cjs').write_text(code)
env={k:v for k,v in os.environ.items() if not k.upper().startswith('GIT_')};env.update(GITHUB_WORKSPACE=str(repo),EXPECTED_HEAD=head,GATEWAY_EVIDENCE=str(o/'a8-qualified'))
assert not any(env.get(k) for k in ['NODE_OPTIONS','NODE_PATH','NODE_COMPILE_CACHE','NODE_V8_COVERAGE'])
p=subprocess.run(['node','--no-addons',str(bootstrap)],cwd=repo,env=env,capture_output=True,timeout=45);(o/'qualification.stdout.log').write_bytes(p.stdout);(o/'qualification.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr
receipt=json.loads((o/'a8-qualified/source-receipt.json').read_text());assert receipt['tests']==41 and receipt['result']=='PASS' and receipt['before']==receipt['after'];assert {e['path']:e['sha256'] for e in receipt['before']}==rawmap
packet=repo/'tests/gateway_artifacts/query-v2-1610';m=json.loads((packet/'MANIFEST.json').read_bytes());pins=[]
for name,facts in m['files'].items():
 p=packet/pathlib.Path(name).name;b=p.read_bytes();assert len(b)==facts['bytes'] and hashlib.sha256(b).hexdigest()==facts['sha256'];pins.append(name)
for name in ['upstream-request.json','upstream-result.json','request.json','descriptor.json','meta-result.json']:
 assert (packet/name).read_bytes()==(r/'work/review-query76-6e58/docs/gateway/research/evidence/query-v2-onebar'/name).read_bytes()
result=dict(head=head,tree=g('rev-parse','HEAD^{tree}').decode().strip(),node=receipt['node'],workflow_pinned_node='22.14.0_NOT_EXECUTED_BY_A8',tests=41,skips=0,raw_prepost=371,packet_schema_members=len(pins),five_packet_files='BYTE_IDENTICAL_STRATT76_6e58_RETAINED5b',source_raw=rawmap)
(o/'primary-verification.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='source_raw'}))
