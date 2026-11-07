import pathlib,subprocess,json,hashlib,io
r=pathlib.Path.cwd();repo=r/'work/review-tlsfront37b3';o=r/'outputs/phase83';head='37b3b029cd6b5a273ea5e7ea04eee8485347de31';pub='4493a53593e65910f67da57bd43057b3416bbe7d'
def g(*a,data=None):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a],input=data)
assert g('rev-parse','HEAD^{tree}').decode().strip()=='ab65b14c34b41158079a2c0c96e4edf6b627e158';changes=g('diff','--name-status','HEAD^','HEAD').decode().splitlines();assert len(changes)==4 and all(row.startswith('A\t') for row in changes)
for row in changes:
 p=row.split('\t')[1];assert g('show',head+':'+p)==g('show',pub+':'+p)
prefix='release/evidence/gateway-runtime-front-20261107/';raw=g('show',pub+':'+prefix+'index.json');(o/'owner-index.original.json').write_bytes(raw);idx=json.loads(raw)
for name,facts in idx['raw_files'].items():
 raw=g('show',pub+':'+prefix+name);assert len(raw)==facts['bytes'] and hashlib.sha256(raw).hexdigest()==facts['sha256'];(o/('owner-'+name)).write_bytes(raw)
entries=[]
for row in g('ls-tree','-rz',head).split(b'\0'):
 if row:
  meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();assert kind==b'blob';entries.append((name.decode(),oid.decode()))
s=io.BytesIO(g('cat-file','--batch',data=''.join(oid+'\n' for _,oid in entries).encode()))
for name,oid in entries:
 actual,kind,size=s.readline().split();raw=s.read(int(size));assert s.read(1)==b'\n' and actual.decode()==oid and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==oid and (repo/name).read_bytes()==raw
(o/'primary-verification.json').write_text(json.dumps(dict(head=head,tree='ab65b14c34b41158079a2c0c96e4edf6b627e158',parent=g('rev-parse','HEAD^').decode().strip(),four_NEW_paths=changes,publication_head=pub,publication_tree=g('rev-parse',pub+'^{tree}').decode().strip(),four_source_paths_raw_equal_at_publication=True,primary_raw_blob_objects_recomputed=len(entries),indexed_owner_raw_members_verified=7,owner_driver_equals_committed_workflow=(o/'owner-executed-workflow.py').read_bytes()==(o/'executed-workflow.py').read_bytes(),publication_HEAD_full_execution='NOT_RUN_NO_TRANSFER'),indent=2),encoding='utf-8');ci=json.loads((o/'ci.original.json').read_text());print(json.dumps(dict(primary_files=len(entries),index_members=7,CI=[{k:x.get(k) for k in ['id','status','conclusion','run_attempt']} for x in ci['workflow_runs']])))
