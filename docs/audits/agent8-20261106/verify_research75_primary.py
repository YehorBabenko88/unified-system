import pathlib,subprocess,json,hashlib,io
r=pathlib.Path.cwd();o=r/'outputs/phase88';repo=r/'work/review-research75-aed8';head='aed8a7c8a952f96803c207d5e90b133969a47f04'
def g(*a,data=None,cwd=repo):return subprocess.check_output(['git','--no-replace-objects','-C',str(cwd),*a],input=data)
assert g('rev-parse','HEAD^{tree}').decode().strip()=='eed3a87c6e33f0993424f20b49ab5af93bd09b9a';changes=g('diff','--name-status','072d22214136148b47e82d21fec9e269bd7468ac',head).decode().splitlines();assert len(changes)==21 and all(x.startswith('A\t') for x in changes)
code='strattester/research/gateway_adapter.py';raw=g('show',head+':'+code);assert hashlib.sha256(raw).hexdigest()=='689bd82be39cdc15725fcefbe2cefc248c4feb51c27822f9813558f5587e81dd';assert raw==g('show','f11f393ddc1ce1d45e5ec66839fa98e15ee98496:'+code)
packet=repo/'docs/gateway/research/evidence/btc-v1';manifest=json.loads((packet/'MANIFEST.json').read_bytes());artifactproof=[]
for facts in manifest['files']+manifest['schemas']:
 path=packet/facts['name'] if facts in manifest['files'] else repo/'docs/gateway/research'/facts['name'];b=path.read_bytes();assert len(b)==facts['bytes'] and hashlib.sha256(b).hexdigest()==facts['sha256'];rel=path.relative_to(repo).as_posix();assert b==g('show','f3d2877ac5e7af6f89586fcdb184974b494e46ac:'+rel);artifactproof.append(dict(path=rel,bytes=len(b),sha256=facts['sha256'],original_packet_commit_raw_equal=True))
entries=[]
for row in g('ls-tree','-rz','HEAD').split(b'\0'):
 if row:
  meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();assert kind==b'blob';entries.append((name.decode(),oid.decode()))
stream=io.BytesIO(g('cat-file','--batch',data=''.join(oid+'\n' for _,oid in entries).encode()))
for name,oid in entries:
 actual,kind,size=stream.readline().split();b=stream.read(int(size));assert stream.read(1)==b'\n' and actual.decode()==oid and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==oid and (repo/name).read_bytes()==b
meta=r/'work/research75-a8-temp/gateway-meta-source-f3c';assert g('rev-parse','HEAD',cwd=meta).decode().strip()=='f3c01a23fa5baaeeeb28eb8e9397e72b5ef4d5a1' and g('rev-parse','HEAD^{tree}',cwd=meta).decode().strip()=='c155c935a801fa98b7c78219c9798ce1f1be8848';pins=json.loads((o/'workflow38.original.json').read_bytes())['meta_source_sha256'];mp=[]
for name,pin in pins.items():
 path='src/meta_analyse/'+name;b=g('show','HEAD:'+path,cwd=meta);assert hashlib.sha256(b).hexdigest()==pin and (meta/path).read_bytes()==b;oid=g('rev-parse','HEAD:'+path,cwd=meta).decode().strip();assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==oid;mp.append(dict(path=path,blob_oid=oid,sha256=pin))
(o/'primary-verification.json').write_text(json.dumps(dict(head=head,tree='eed3a87c6e33f0993424f20b49ab5af93bd09b9a',NEW_paths=changes,primary_raw_objects=len(entries),adapter_sha256=hashlib.sha256(raw).hexdigest(),adapter_byte_equal_corrected_f11=True,original_packet_and_schemas=artifactproof,Meta_head='f3c01a23fa5baaeeeb28eb8e9397e72b5ef4d5a1',Meta_tree='c155c935a801fa98b7c78219c9798ce1f1be8848',Meta_actual_three_primary_blobs=mp,whole_Meta_native_qualification=False),indent=2),encoding='utf-8');print('800primaryGitOID/21NEWpaths/7originalpacket-schema entries/3Meta primarypins verified')
