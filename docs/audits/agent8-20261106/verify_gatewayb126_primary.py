import pathlib,subprocess,json,hashlib,io
r=pathlib.Path.cwd();repo=r/'work/review-gatewayb126';o=r/'outputs/phase80';head='b1261c560922ac6fc255d79809759d7d06035f0a';pub='e2fa604a6b39852db1075efc2ced07b8120801a2'
def g(*a,data=None):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a],input=data)
assert g('rev-parse',head+'^{tree}').decode().strip()=='9a8174b3b9470bdbcf969ab8ed4f284edcce8c92';assert g('rev-parse',pub+'^{tree}').decode().strip()=='0aa4032eef595f1dfb7dfc87513af8ea1d05d0a2'
changes=g('diff','--name-status','55ebd47934a5bc521120deea7ce9e0d48cf1935d',head).decode().splitlines();assert len(changes)==8 and all(x.startswith('A\t') for x in changes);paths=[x.split('\t')[1] for x in changes]
for p in paths:assert g('show',head+':'+p)==g('show',pub+':'+p)
prefix='release/evidence/intelligence-gateway-20261107/';raw=g('show',pub+':'+prefix+'index.json');(o/'owner-index.original.json').write_bytes(raw);index=json.loads(raw)
for name,facts in index['raw_files'].items():
 b=g('show',pub+':'+prefix+name);assert len(b)==facts['bytes'] and hashlib.sha256(b).hexdigest()==facts['sha256'];(o/('owner-'+name)).write_bytes(b)
rows=[]
for row in g('ls-tree','-rz',head).split(b'\0'):
 if row:
  meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();assert kind==b'blob';rows.append((name.decode(),oid.decode()))
s=io.BytesIO(g('cat-file','--batch',data=''.join(oid+'\n' for _,oid in rows).encode()))
for name,oid in rows:
 actual,kind,size=s.readline().split();b=s.read(int(size));assert s.read(1)==b'\n' and actual.decode()==oid and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==oid and (repo/name).read_bytes()==b
(o/'primary-verification.json').write_text(json.dumps(dict(tested_head=head,tested_tree='9a8174b3b9470bdbcf969ab8ed4f284edcce8c92',evidence_head=pub,evidence_tree='0aa4032eef595f1dfb7dfc87513af8ea1d05d0a2',eight_NEW_paths=changes,all_eight_source_paths_raw_equal_at_publication=True,primary_objects_recomputed=len(rows),owner_index_members_verified=len(index['raw_files']),owner_driver_byte_equal_actualworkflow=(o/'owner-executed-exact-workflow.py').read_bytes()==(o/'executed-workflow.py').read_bytes(),publication_full_matrix_execution='NOT_RUN_NO_TRANSFER'),indent=2),encoding='utf-8');print('1378primary blobs/eight source paths/five indexed owner members verified')
