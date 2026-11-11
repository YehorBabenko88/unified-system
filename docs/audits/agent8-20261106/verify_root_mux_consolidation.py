"""Primary Git verification of owner consolidation evidence, not an execution receipt."""
import hashlib,io,json,pathlib,subprocess
r=pathlib.Path(__file__).resolve().parents[1];repo=r/'work/unified-audit';out=r/'outputs/phase50';out.mkdir(exist_ok=True);merge='a77a5bdb70ca08acbc2f3a3d806866f0d0cb228e';evidence='38c39092a30be51f8f554bac48f3fad5a87a6c25';component='08d6f01d94feb44a17338be8ef3f8871995c284a';prefix='release/evidence/control-mux-integrated-a77a5bd/'
def git(*a):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a])
def read(pin,path):return git('show',pin+':'+path)
paths=git('diff','--name-only',merge+'^',merge).decode().splitlines();assert len(paths)==32
for p in paths:assert read(merge,p)==read(component,p),p
raw=read(evidence,prefix+'root-result.json');owner=json.loads(raw);(out/'root-result.original.json').write_bytes(raw)
errors=[];verified=[]
for path,digest in owner['evidence_sha256'].items():
 p=subprocess.run(['git','--no-replace-objects','-C',str(repo),'show',evidence+':'+prefix+path],capture_output=True)
 if p.returncode:errors.append(dict(path=path,error='INDEXED_FILE_ABSENT_FROM_COMMIT',expected_sha256=digest));continue
 actual=hashlib.sha256(p.stdout).hexdigest();assert actual==digest,path;verified.append(path)
 if '/' not in path:(out/path).write_bytes(p.stdout)
bound=json.loads(read(evidence,prefix+'source-bound.json'));assert bound['primary']['head']==merge and len(bound['primary']['raw_files'])==872 and bound['grid']['head']=='58cfe0f51bc05bb0ee2ed09368a9b64679358c63' and len(bound['grid']['raw_files'])==672
def verify_map(source_repo,pin,mapping):
 names=list(mapping);stream=io.BytesIO(subprocess.check_output(['git','--no-replace-objects','-C',str(source_repo),'cat-file','--batch'],input=''.join(pin+':'+n+'\n' for n in names).encode()))
 for name in names:
  oid,kind,size=stream.readline().split();assert kind==b'blob';body=stream.read(int(size));assert stream.read(1)==b'\n' and hashlib.sha256(body).hexdigest()==mapping[name],name
verify_map(repo,merge,bound['primary']['raw_files']);verify_map(r/'work/review-grid58cfe',bound['grid']['head'],bound['grid']['raw_files'])
copies=git('ls-tree','-r','--name-only',evidence,'release/evidence/control-mux-phase49/').decode().splitlines();matched=[]
for path in copies:
 name=path.rsplit('/',1)[-1];orig=r/'outputs/phase49'/name
 if orig.is_file():assert read(evidence,path)==orig.read_bytes(),name;matched.append(name)
assert len(matched)==18
real=json.loads(read(evidence,prefix+'real-consul.json'));assert real['owned_processes_stopped'] and len(real['events'])==42 and len(bound['executed_unit_ids'])==18 and len(bound['executed_source_guard_case_ids'])==8 and bound['skips']==[]
report=dict(requirement='ROOT_DRAFT26_MERGE_AND_EVIDENCE_BINDING',repository='unified-system',pr=26,merge_head=merge,merge_tree=git('rev-parse',merge+'^{tree}').decode().strip(),evidence_head=evidence,evidence_tree=git('rev-parse',evidence+'^{tree}').decode().strip(),component_head=component,merged_paths_exact_component_bytes=32,primary_reported_raw_files_matched_git=872,grid_reported_raw_files_matched_git=672,original_A8_phase49_copied_raw_equal=matched,owner_reported_execution=dict(unit=18,real=42,source_guards=8,skips=0,owned_processes_stopped=True),owner_environment='REUSED_A2_ENV_NOT_NEWLY_INDEPENDENTLY_QUALIFIED',A8_execution_on_merged_source='NOT_RUN',owner_evidence_members_hash_verified=len(verified),evidence_index_errors=errors,original_A8_phase49_scope='PRESERVED_NO_TRANSFER_TO_MERGE_OR_DOCS_HEAD',evidence_completeness='FAIL_INDEXED_FILE_MISSING' if errors else 'PASS',severity='P2_EXISTING_F07_EVIDENCE_COMPLETENESS' if errors else 'NONE',qualification='PRIMARY_GIT_SOURCE_AND_OWNER_RECEIPT_CONSISTENCY_ONLY',native_authentication=False,full_windows_matrix=False,physical='BLOCKED',tailscale_removal='BLOCKED',overall='NO_GO')
(out/'independent-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
