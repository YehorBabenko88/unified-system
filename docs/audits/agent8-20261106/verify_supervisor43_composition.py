import pathlib,subprocess,json,hashlib,io
r=pathlib.Path.cwd();repo=r/'work/review-supervisor43';o=r/'outputs/phase78'
def g(*a,data=None):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a],input=data)
assert g('rev-parse','HEAD^{tree}').decode().strip()=='548a4e2243a224ad86073c39bfec465e6e61251f'
changes=g('diff','--name-status','eeb539d6e254769b5d0e7a0f5f3cb629ce673ffe','HEAD').decode().splitlines();assert len(changes)==5 and all(x.startswith('A\t') for x in changes)
pins={'a2265b0d53e3d6ee8814aa28f5c612d537a0f195':['unified_system/node_task_journal.py','unified_system/node_supervisor_v2.py','tests/test_node_task_journal.py','tests/test_node_supervisor_v2.py'],'48e38a2eeea32ddb3836a27871959814843bb6c6':['unified_system/ci_queue_controller.py','tests/test_ci_queue_controller.py'],'d22677736dc862c344a54fe9105d336fa02abe83':['unified_system/mission_controller.py','tests/test_mission_controller.py'],'4cfdc31f63ff32ab251464e89ff1aa6becd471fa':['unified_system/supervisor_deployment.py','tests/test_supervisor_deployment.py']}
proof=[]
for head,paths in pins.items():
 for p in paths:
  raw=g('show','HEAD:'+p);assert raw==g('show',head+':'+p)==g('show','eeb539d6e254769b5d0e7a0f5f3cb629ce673ffe:'+p);proof.append(dict(source=head,path=p,sha256=hashlib.sha256(raw).hexdigest()))
originals=r.parent/'codex-agent-7-distributed-research-math/outputs/math115-observation-240m';fixtures=[]
for name in ['run','jobs']:
 raw=(repo/f'release/evidence/supervisor-local-integration-fixtures/math-{name}-42352374979.json').read_bytes();orig=originals/(name+'.json');assert orig.read_bytes()==raw;fixtures.append(dict(name=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),original_A7_raw_equal=True))
entries=[]
for row in g('ls-tree','-rz','HEAD').split(b'\0'):
 if row:
  meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();assert kind==b'blob';entries.append((name.decode(),oid.decode()))
s=io.BytesIO(g('cat-file','--batch',data=''.join(oid+'\n' for _,oid in entries).encode()))
for name,oid in entries:
 actual,kind,size=s.readline().split();raw=s.read(int(size));assert s.read(1)==b'\n' and actual.decode()==oid and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==oid and (repo/name).read_bytes()==raw
(o/'independent-composition.json').write_text(json.dumps(dict(head=g('rev-parse','HEAD').decode().strip(),tree=g('rev-parse','HEAD^{tree}').decode().strip(),five_new_paths=changes,exact_components=proof,archived_original_fixtures=fixtures,primary_objects_recomputed=len(entries),live_Math_queries='NONE'),indent=2),encoding='utf-8');print(json.dumps(dict(primary_files=len(entries),component_paths=len(proof),raw_A7_originals=2)))
