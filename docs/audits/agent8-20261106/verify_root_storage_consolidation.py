"""Primary Git/receipt consistency only; no merged runtime qualification."""
import hashlib,io,json,pathlib,subprocess
r=pathlib.Path(__file__).resolve().parents[1];repo=r/'work/unified-audit';out=r/'outputs/phase56';out.mkdir(exist_ok=True);head='32f6b1996d7e810e1ecc84025e850ef62c28802f';merge='9d6857a26842b1c4ce6375a69cef4cdba832b7b1';component='cd0286dee5fc41cb7a35b0b6ac431a7ebfc25dfb';prefix='release/evidence/storage-integrated-9d6857a/'
def git(*a):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a])
def read(pin,path):return git('show',pin+':'+path)
raw=read(head,prefix+'publication-binding.json');b=json.loads(raw);(out/'publication-binding.original.json').write_bytes(raw);assert b['integration_head']==merge and b['component_head']==component and len(b['component_files_unchanged'])==7
for path,digest in b['component_files_unchanged'].items():assert read(merge,path)==read(component,path) and hashlib.sha256(read(merge,path)).hexdigest()==digest
for name,digest in b['published_evidence_sha256'].items():
 raw=read(head,prefix+name);assert hashlib.sha256(raw).hexdigest()==digest;(out/name).write_bytes(raw)
s=json.loads((out/'source-bound.json').read_bytes());assert s['integration_head']==merge and len(s['raw_primary_files'])==944;names=list(s['raw_primary_files']);stream=io.BytesIO(subprocess.check_output(['git','--no-replace-objects','-C',str(repo),'cat-file','--batch'],input=''.join(merge+':'+n+'\n' for n in names).encode()))
for name in names:
 oid,kind,size=stream.readline().split();assert kind==b'blob';body=stream.read(int(size));assert stream.read(1)==b'\n' and hashlib.sha256(body).hexdigest()==s['raw_primary_files'][name],name
copies=[]
for path in git('ls-tree','-r','--name-only',head,'release/evidence/storage-a8-phase54/').decode().splitlines():
 name=path.rsplit('/',1)[-1];orig=r/'outputs/phase54'/name
 if orig.is_file():assert read(head,path)==orig.read_bytes();copies.append(name)
assert len(copies)==7
tests=json.loads((out/'tests.stdout.json').read_bytes());assert tests['head']==merge and tests['passed'] and tests['tests_run']==43 and tests['skips']==0 and not tests['dirty'];assert b['tests']==43 and b['skips']==0 and not b['pilot_rollback_qualified'] and not b['native_admission'] and not b['physical_admission']
report=dict(requirement='ROOT_STORAGE_MERGE_EVIDENCE_BINDING',repository='unified-system',pr=26,merge_head=merge,merge_tree=git('rev-parse',merge+'^{tree}').decode().strip(),publication_head=head,publication_tree=git('rev-parse',head+'^{tree}').decode().strip(),component_head=component,component_paths_raw_equal=7,owner_raw_manifest_matched_primary_Git=944,publication_members_hash_matched=3,original_A8_phase54_copies_raw_equal=copies,owner_execution=dict(cases=43,skips=0),A8_merged_execution='NOT_RUN',owner_interpreter='REUSED_READ_ONLY_A2_ENV_NOT_NEWLY_INDEPENDENTLY_QUALIFIED',status='PASS_PRIMARY_SOURCE_RECEIPT_CONSISTENCY_ONLY',fullsuite_hosted_matrix='NOT_EVALUATED_NOT_TRANSFERRED',media_namespace_crash_durability=False,dataset_authority=False,pilot_rollback_qualified=False,native_physical_admission=False,overall='NO_GO_BROADER_ACCEPTANCE')
(out/'independent-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
