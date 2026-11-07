import pathlib,subprocess,json,hashlib,io
r=pathlib.Path.cwd();o=r/'outputs/phase72';proof=[]
for folder in ['review-assignment40e9','review-mux-get-be5cb94']:
 repo=r/'work'/folder
 def g(*args,data=None):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*args],input=data)
 rows=[]
 for row in g('ls-tree','-rz','HEAD').split(b'\0'):
  if row:
   meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();assert kind==b'blob';rows.append((name.decode(),oid.decode()))
 stream=io.BytesIO(g('cat-file','--batch',data=''.join(oid+'\n' for _,oid in rows).encode()))
 for name,oid in rows:
  actual,kind,size=stream.readline().split();raw=stream.read(int(size));assert stream.read(1)==b'\n' and actual.decode()==oid and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==oid and (repo/name).read_bytes()==raw
 proof.append(dict(clone=folder,head=g('rev-parse','HEAD').decode().strip(),tree=g('rev-parse','HEAD^{tree}').decode().strip(),primary_objects_recomputed=len(rows)))
repo=r/'work/review-assignment40e9';schema=repo/'docs/coordination/assignment-v1/runtime-actor-policy-review2.schema.json';digest=hashlib.sha256(schema.read_bytes()).hexdigest();assert digest=='fa0c069c30ba498443f0af5e1624f94e9cea25cf2cd9e76bb8e5f6a5a7ba324f'
changes=subprocess.check_output(['git','-C',str(repo),'diff','--name-status','be6335a2e8cfac9483213a6a215bc29e32808b0c','HEAD']).decode().splitlines();assert len(changes)==11 and all(row.startswith('A\t') for row in changes)
(o/'independent-primary-verification.json').write_text(json.dumps(dict(primary_sources=proof,policy_review2_sha256=digest,all_eleven_paths_new=changes,binary_sha256=hashlib.sha256((r/'work/consul-bin/extracted/consul.exe').read_bytes()).hexdigest(),dependency_environment='OWN_PREVIOUSLY_PINNED_MUX_ENV_NOT_NEW_NATIVE_QUALIFICATION',guard_fixtures_retained_outside_publication='work/assignment40e9-a8-guard-fixtures'),indent=2),encoding='utf-8')
ci=json.loads((o/'ci.original.json').read_text());print([{k:x.get(k) for k in ['id','status','conclusion','run_attempt']} for x in ci['workflow_runs']])
