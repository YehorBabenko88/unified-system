"""Exact primary source and selected receipts, not rerun of merged runtime."""
import hashlib,io,json,pathlib,subprocess
r=pathlib.Path(__file__).resolve().parents[1];repo=r/'work/unified-audit';out=r/'outputs/phase62';out.mkdir(exist_ok=True);head='eb0c6486524c7d7f4d3dc390abebc0107db2c858';merge='f8f29bfd6041acc7b767b2a783f3576867d9bd02';component='be5cb942436f82f374375eabb255768bb139797f';prefix='release/evidence/get-integrated-f8f29bf/'
def git(*a):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a])
def read(path):return git('show',head+':'+path)
raw=read('release/reports/20261107/GET-INTEGRATION-STATUS.json');status=json.loads(raw);assert raw==read(prefix+'publication-binding.json');(out/'root-status.original.json').write_bytes(raw)
assert status['integration_head']==merge and len(status['component_files_unchanged'])==14
for path,digest in status['component_files_unchanged'].items():
 a=git('show',merge+':'+path);assert a==git('show',component+':'+path) and hashlib.sha256(a).hexdigest()==digest
index=[];copy_counts={}
for category,folder,binding in [('root',prefix,status),('A8','release/evidence/get-a8-phase61/',json.loads(read('release/evidence/get-a8-phase61/root-binding.json'))),('A6','release/evidence/get-a6-be5cb94/',json.loads(read('release/evidence/get-a6-be5cb94/root-binding.json')))]:
 copy_counts[category]=0
 for name,digest in binding['published_evidence_sha256'].items():
  body=read(folder+name);assert hashlib.sha256(body).hexdigest()==digest,name
  if category=='A8':assert body==(r/'outputs/phase61'/name).read_bytes()
  if category=='A6':assert body==(r.parent/'codex-agent-6-distributed-terminan-control/outputs/terminan-sync-v1'/name).read_bytes()
  if category=='root':(out/name).write_bytes(body)
  index.append(dict(category=category,path=folder+name,sha256=digest,bytes=len(body)));copy_counts[category]+=1
assert copy_counts==dict(root=6,A8=21,A6=3) and len(index)==30
bound=json.loads((out/'source-bound.json').read_bytes());assert bound['primary']['head']==merge and len(bound['primary']['raw_files'])==1221 and len(bound['grid']['raw_files'])==672
def check(source_repo,pin,mapping):
 names=list(mapping);stream=io.BytesIO(subprocess.check_output(['git','--no-replace-objects','-C',str(source_repo),'cat-file','--batch'],input=''.join(pin+':'+n+'\n' for n in names).encode()))
 for name in names:
  oid,kind,size=stream.readline().split();assert kind==b'blob';body=stream.read(int(size));assert stream.read(1)==b'\n' and hashlib.sha256(body).hexdigest()==mapping[name],name
check(repo,merge,bound['primary']['raw_files']);check(r/'work/review-grid58cfe',bound['grid']['head'],bound['grid']['raw_files'])
own=json.loads((r/'outputs/phase61/source-bound.json').read_bytes());assert bound['executed_unit_ids']==own['executed_unit_ids'] and bound['executed_real_case_ids']==own['executed_real_case_ids'] and bound['skips']==[]
real=json.loads((out/'real-consul.json').read_bytes());assert real['owned_processes_stopped'] and len(real['events'])==72 and bound['supplemental_get_model_cases']==24
assert status['publication_scope'].startswith('Selected top-level') and status['native_identity_provider']=='UNAVAILABLE' and status['default_wsgi']=='503' and not status['physical_admission'] and not status['ready_live_ack204_release']
(out/'verified-selected-members.json').write_text(json.dumps(index,indent=2),encoding='utf-8')
report=dict(requirement='ROOT_GET_MERGE_SOURCE_SELECTED_EVIDENCE_BINDING',repository='unified-system',pr=26,merge_head=merge,merge_tree=git('rev-parse',merge+'^{tree}').decode().strip(),publication_head=head,publication_tree=git('rev-parse',head+'^{tree}').decode().strip(),component_head=component,component_files_raw_equal=14,indexed_selected_members=30,verified_categories=copy_counts,A8_original21_raw_equal=True,A6_scope='SEMANTIC_ERROR_ABI_ONLY_OWNER_EVIDENCE_NOT_OUR_RERUN',primary1221_Grid672_manifest_hashes_matched_Git=True,owner_execution=dict(units=33,actual_groups=72,guards=8,skips=0,model24='SEPARATE_NOT_ACTUAL204',owned_processes_stopped=True),A8_merged_execution='NOT_RUN',environment='OWNER_BORROWED_A2_ENV_NOT_NEWLY_INDEPENDENTLY_QUALIFIED',negative_fixture_dirs='LOCAL_EXPLICITLY_EXCLUDED_NOT_FALSE_FULL_BUNDLE_CLAIM',default503_native_provider_absent=True,status='PASS_SOURCE_AND_SELECTED_EVIDENCE_CONSISTENCY_ONLY',hosted_fullmatrix_native_browser_office_READY_release_physical='NOT_ADMITTED_NOT_TRANSFERRED',overall='NO_GO_BROADER_ACCEPTANCE')
(out/'independent-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
