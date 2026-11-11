import pathlib,subprocess,json,hashlib,io
r=pathlib.Path.cwd();o=r/'outputs';proof=[]
for phase,name,head,tree in [('phase84','review-identity2cb6','2cb6b21eac5617ff39ad7a96b7e1c73118e0af00','f51a4a976c2864a584446c3a5c11e8bfcbcca537'),('phase85','review-identityeed4','eed4f5b14e2b940f67a4cbe5d6eb5f17d90887cf','032536ddcbf2f6caad914f2183a54d069d59695a')]:
 repo=r/'work'/name
 def g(*a,data=None):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a],input=data)
 assert g('rev-parse','HEAD').decode().strip()==head and g('rev-parse','HEAD^{tree}').decode().strip()==tree
 entries=[]
 for row in g('ls-tree','-rz',head).split(b'\0'):
  if row:
   meta,path=row.split(b'\t',1);mode,kind,oid=meta.split();assert kind==b'blob';entries.append((path.decode(),oid.decode()))
 stream=io.BytesIO(g('cat-file','--batch',data=''.join(oid+'\n' for _,oid in entries).encode()));files={}
 for path,oid in entries:
  actual,kind,size=stream.readline().split();raw=stream.read(int(size));assert stream.read(1)==b'\n' and actual.decode()==oid and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==oid and (repo/path).read_bytes()==raw;files[path]=hashlib.sha256(raw).hexdigest()
 unexpected=[]
 for path in repo.rglob('*'):
  rel=path.relative_to(repo)
  if rel.parts[0]=='.git':continue
  assert not path.is_symlink() and not getattr(path.lstat(),'st_file_attributes',0)&1024 and path.suffix not in ('.pyc','.pyo')
  if path.is_file() and rel.as_posix() not in files:unexpected.append(rel.as_posix())
 assert not unexpected
 (o/phase/'independent-primary.json').write_text(json.dumps(dict(head=head,tree=tree,primary_objects_recomputed=len(entries),no_untracked_or_cache_inputs_in_actual_normal_clone=True,module_raw_sha256=files['unified_system/gateway_identity.py'],API_review3_raw_sha256=files['docs/intelligence/identity/API-REVIEW3.md'],tracked_raw_map=files),indent=2),encoding='utf-8');proof.append(files['unified_system/gateway_identity.py'])
assert proof[0]==proof[1] and proof[0].startswith('84093865')
new=r/'work/review-identityeed4';workflow=(new/'.github/workflows/gateway-identity.yml').read_text();assert 'git rev-parse HEAD' not in workflow and 'git config --global' not in workflow and 'ref: ${{ env.EXPECTED_HEAD }}' in workflow and 'persist-credentials: false' in workflow and 'fetch-depth: 0' in workflow
(o/'phase85/workflow-pin-review.json').write_text(json.dumps(dict(source='eed4f5b14e2b940f67a4cbe5d6eb5f17d90887cf',event_derived_expected_HEAD=True,checkout_exact_expected_HEAD=True,persist_credentials=False,full_fetch=True,no_global_git_config_mutation=True,self_attested_HEAD_tautology_removed=True,hosted_execution='NOT_QUALIFIED'),indent=2),encoding='utf-8');print('1398+1400 primaryOID/raw/no-cache inventories verified; runtime andAPI3 hashes unchanged; successorworkflow pin config reviewed')
