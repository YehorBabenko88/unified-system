import pathlib,subprocess,json,hashlib,io
r=pathlib.Path.cwd();o=r/'outputs/phase89';root=r/'work/review-read815';pub='3fc412d548e2be9853f84b8306f0f852e04cf43e';head='815fd51d3bbba0b2ec4b87af8a085dd36bf46cf1';grid=r/'work/read815-a8-grid-f19'
def g(repo,*a,data=None):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a],input=data)
assert g(root,'rev-parse','HEAD^{tree}').decode().strip()=='d25d762a8f9ac712c518862e63b494baec98cb10'
entries=[]
for row in g(root,'ls-tree','-rz','HEAD').split(b'\0'):
 if row:
  meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();assert kind==b'blob';entries.append((name.decode(),oid.decode()))
s=io.BytesIO(g(root,'cat-file','--batch',data=''.join(oid+'\n' for _,oid in entries).encode()));rawmap={}
for name,oid in entries:
 actual,kind,size=s.readline().split();b=s.read(int(size));assert s.read(1)==b'\n' and actual.decode()==oid and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==oid and (root/name).read_bytes()==b;rawmap[name]=hashlib.sha256(b).hexdigest()
assert len(entries)==1513
contract=json.loads((root/'coordination/gateway-runtime-contracts.v1.json').read_bytes());assert rawmap['unified_system/gateway_identity.py']==contract['identity']['runtime_sha256'] and rawmap['docs/intelligence/identity/API-REVIEW3.md']==contract['identity']['local_abi_sha256'] and rawmap['unified_system/storage/gateway_disclosure.py']==contract['manifest']['module_sha256'] and rawmap['docs/intelligence/storage-disclosure/manifest-request.schema.json']==contract['manifest']['request_schema_sha256']
assert g(grid,'rev-parse','HEAD').decode().strip()==contract['query']['head'];query=g(grid,'show',contract['query']['head']+':grid/gateway_query.py');assert hashlib.sha256(query).hexdigest()==contract['query']['module_sha256'] and (grid/'grid/gateway_query.py').read_bytes()==query
# Public selected publication index only: original logs remain attribution-owner, not independent rerun evidence.
prefix='release/evidence/gateway-runtime-read-815fd51/';idx=g(root,'show',pub+':'+prefix+'index.json');(o/'owner-read-index.original.json').write_bytes(idx);d=json.loads(idx)
for name,facts in d['files'].items():
 b=g(root,'show',pub+':'+prefix+name);assert len(b)==facts['bytes'] and hashlib.sha256(b).hexdigest()==facts['sha256'];(o/('owner-'+name)).write_bytes(b)
old_to_new=g(root,'diff','f155126a95e80139b1b9679c1870ffd66c29360e',head,'--','unified_system/gateway_runtime_composition.py').decode();(o/'docstring-only-delta.original.diff').write_text(old_to_new,encoding='utf-8')
import ast
old=g(root,'show','f155126a95e80139b1b9679c1870ffd66c29360e:unified_system/gateway_runtime_composition.py');new=g(root,'show',head+':unified_system/gateway_runtime_composition.py');a,b=ast.parse(old),ast.parse(new);a.body=a.body[1:];b.body=b.body[1:];assert ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)
changes=g(root,'diff','--name-only',head,pub).decode().splitlines();assert all(x.startswith('release/') or x=='coordination/gateway-runtime-contracts.v1.json' for x in changes)
packet='release/evidence/gateway-runtime-contiguous-read-20261107/';receipt=json.loads(g(root,'show',pub+':'+packet+'receipt.json'));verified=[]
for name,facts in receipt['files'].items():
 b=g(root,'show',pub+':'+packet+name);assert len(b)==facts['bytes'] and hashlib.sha256(b).hexdigest()==facts['sha256'];verified.append(dict(name=name,**facts))
(o/'primary-verification.json').write_text(json.dumps(dict(source_head=head,source_tree='d25d762a8f9ac712c518862e63b494baec98cb10',primary_raw_objects_recomputed=1513,component_contract_hashes_matched=True,query_head=contract['query']['head'],query_tree=g(grid,'rev-parse','HEAD^{tree}').decode().strip(),query_module_sha256=hashlib.sha256(query).hexdigest(),single_canonical_identity_and_ObjectStore=True,contract_record_names_historical_source_f155_not_relabelled=True,f155_to815_runtime_AST_equal_except_docstring=True,publication_head=pub,publication_tree=g(root,'rev-parse',pub+'^{tree}').decode().strip(),publication_delta_release_and_contract_metadata_only=changes,owner815_index_members_verified=2,original_contiguous_capture_five_files_verified=verified,source_raw_sha256=rawmap),indent=2),encoding='utf-8');print('1513primaryOid/componentpins/2owner815members/5ONEBARcapturefilesverified; f155->815ASTdocstringonly')
