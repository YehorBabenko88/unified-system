import pathlib,subprocess,json,hashlib,io,os
r=pathlib.Path.cwd();repo=r/'work/review-targetui22e';o=r/'outputs/phase103';o.mkdir(exist_ok=True);head='22e6e7230d2f66fd22dda648a77910579812bd60'
def g(*a,data=None):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a],input=data)
rows=[]
for row in g('ls-tree','-rz','HEAD').split(b'\0'):
 if row:
  meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();assert kind==b'blob';rows.append((name.decode(),oid.decode()))
s=io.BytesIO(g('cat-file','--batch',data=''.join(oid+'\n' for _,oid in rows).encode()));rawmap={}
for name,oid in rows:
 actual,kind,size=s.readline().split();b=s.read(int(size));assert s.read(1)==b'\n' and actual.decode()==oid and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==oid and (repo/name).read_bytes()==b;rawmap[name]=hashlib.sha256(b).hexdigest()
assert len(rawmap)==388
workflow=(repo/'.github/workflows/target-adapter-result.yml').read_bytes();(o/'workflow.original.yml').write_bytes(workflow);code='\n'.join(x[10:] if x.startswith('          ') else x for x in workflow.decode().split("$taskCode = @'\n",1)[1].split("          '@",1)[0].splitlines());bootstrap=r/'work/targetui22e-bootstrap.cjs';bootstrap.write_text(code);(o/'bootstrap-executed.cjs').write_text(code)
env={k:v for k,v in os.environ.items() if not k.upper().startswith('GIT_')};env.update(GITHUB_WORKSPACE=str(repo),EXPECTED_HEAD=head,TARGET_UI_EVIDENCE=str(o/'a8-corrected-qualified'));assert not any(env.get(k) for k in ['NODE_OPTIONS','NODE_PATH','NODE_COMPILE_CACHE','NODE_V8_COVERAGE'])
p=subprocess.run(['node','--no-addons',str(bootstrap)],cwd=repo,env=env,capture_output=True,timeout=45);(o/'corrected-own16.stdout.log').write_bytes(p.stdout);(o/'corrected-own16.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr;d=json.loads((o/'a8-corrected-qualified/source-receipt.json').read_text());assert d['tests']==16 and d['result']=='PASS' and d['before']==d['after'];assert {x['path']:x['sha256'] for x in d['before']}==rawmap
packet=repo/'tests/target_adapter_result/owner-cf7d';pins=json.loads((packet/'SOURCE-PINS.json').read_bytes());rootrepo=r/'work/unified-audit';bindings=[]
for name,sha in pins['files_sha256'].items():
 raw=(packet/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==sha;prefix='docs/intelligence/target-adapter/' if name.endswith(('.md','.schema.json')) else 'docs/intelligence/target-adapter/evidence/source-a84eabb/';primary=subprocess.check_output(['git','--no-replace-objects','-C',str(rootrepo),'show',pins['publication']+':'+prefix+name]);assert raw==primary;bindings.append(dict(name=name,sha256=sha,bytes=len(raw),Root_primary_path=prefix+name))
for name in ['prepared-request.json','direct-result.json','actual-meta-result.json']:assert (packet/name).read_bytes()==(r/'outputs/phase101'/name).read_bytes()
result=dict(head=head,tree=g('rev-parse','HEAD^{tree}').decode().strip(),base='b70725220eed43e371a3c08f1c87fcabd984a45d',new_owned_files=len(g('diff','--name-only','b70725220eed43e371a3c08f1c87fcabd984a45d','HEAD').decode().splitlines()),node=d['node'],pinned_workflow_node='22.14.0_NOT_RUN_BY_A8',tests=16,skips=0,primary_raw_prepost=388,source_raw=rawmap,Root_primary_bindings=bindings,three_packet_files='BYTE_IDENTICAL_PHASE101_ACTUAL_A8_EXECUTION_NOT_EXECUTION_TRANSFER',A8_browser=False,actual_target_invoked_by_renderer=False)
(o/'corrected-primary-verification.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ('source_raw','Root_primary_bindings')}))
