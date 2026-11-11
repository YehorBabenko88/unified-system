"""Publication/provenance checks only; no owner tests, probes or runtime code executed."""
import collections,hashlib,io,json,pathlib,subprocess,tomllib
r=pathlib.Path(__file__).resolve().parents[1];unified=r/'work/unified-audit';out=r/'outputs/phase65';out.mkdir(exist_ok=True);head='92b8328a65520b86e63f8052b2429422334c98b9';prefix='release/master-mission/20261107/'
repos={'unified-system':unified,'bybit-cluster-grid':r/'work/review-grid265','strattester':r/'work/review7-strattester','math':r/'work/review7-math-917','meta_analyse':r/'work/review7-meta_analyse','Terminan':r/'work/terminan-isolated'}
def git(repo,*a):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a])
def read(name):return git(unified,'show',head+':'+prefix+name)
index_raw=read('evidence-index.json');index=json.loads(index_raw);names=git(unified,'ls-tree','-r','--name-only',head,prefix).decode().splitlines();assert len(names)==31 and {prefix+x['path'] for x in index['files']}==set(names)-{prefix+'evidence-index.json'} and len(index['files'])==30
for entry in index['files']:
 raw=read(entry['path']);assert len(raw)==entry['bytes'] and hashlib.sha256(raw).hexdigest()==entry['sha256']
artifacts=[x['path'] for x in index['files'] if x['path'].endswith('.md') and x['path'][0] in 'ABCDEFG'];assert len(artifacts)==7
matrix=json.loads(read('scientific-capability-gap-matrix.json'));catalog=json.loads(read('six-source-catalog.json'));status=json.loads(read('MASTER-STATUS.json'));blockers=json.loads(read('integration-blockers.json'));assert matrix['classification']=='AUDIT_SNAPSHOT_NOT_INSTALLABLE' and len(blockers['items'])==8 and {x['id'] for x in blockers['items']}==set('ABCDEFGH') and status['GO_NO_GO']=='NO_GO'
owner_specs=[('Agent 3','agent3-scientific-capability-sourcefacts-7a19.json','rows',r.parent/'codex-agent-3-bybit-historical-live/outputs/scientific-capability-audit/agent3-scientific-capability-sourcefacts-7a19.json'),('Agent 6','SCIENTIFIC-CAPABILITY-AUDIT-10E07EF.json','capabilities',r.parent/'codex-agent-6-distributed-terminan-control/outputs/terminan-sync-v1/SCIENTIFIC-CAPABILITY-AUDIT-10E07EF.json'),('Agent 7','agent7-scientific-reuse-audit-20261107.json','capabilities',r.parent/'codex-agent-7-distributed-research-math/outputs/agent7-scientific-reuse-audit-20261107.json')]
counts={}
for owner,name,key,local in owner_specs:
 raw=read(name);assert raw==local.read_bytes();original=json.loads(raw)[key];copied=[row['detail'] for row in matrix['rows'] if row['owner']==owner];canonical=lambda values:collections.Counter(json.dumps(v,sort_keys=True) for v in values);assert canonical(original)==canonical(copied);counts[owner]=len(original)
assert counts=={'Agent 3':18,'Agent 6':22,'Agent 7':48} and len(matrix['rows'])==88
for row in matrix['rows']:
 field={'Agent 3':'implementation_status','Agent 6':'implementation','Agent 7':'status'}[row['owner']];assert row['status']==row['detail'][field]
checks=matrix['raw_git_source_checks'];assert len(checks)==len({(x['repo'],x['head'],x['path']) for x in checks})==130
for name in repos:
 group=[x for x in checks if x['repo']==name]
 if not group:continue
 stream=io.BytesIO(subprocess.check_output(['git','--no-replace-objects','-C',str(repos[name]),'cat-file','--batch'],input=''.join(x['head']+':'+x['path']+'\n' for x in group).encode()))
 for item in group:
  oid,kind,size=stream.readline().split();body=stream.read(int(size));assert stream.read(1)==b'\n' and kind==b'blob' and oid.decode()==item['blob'] and hashlib.sha256(body).hexdigest()==item['sha256']
for name,item in catalog.items():
 repo=repos[name];assert git(repo,'rev-parse',item['head']+'^{tree}').decode().strip()==item['tree'];assert len(git(repo,'ls-tree','-r','--name-only',item['head']).decode().splitlines())==item['source_file_count']
 for path,fact in item['project_manifest_facts'].items():
  raw=git(repo,'show',item['head']+':'+path);assert len(raw)==fact['bytes'] and hashlib.sha256(raw).hexdigest()==fact['sha256']
 assert not item['integrated_full_runtime'] and not item['physical_verified']
assert status['SIX_REPOSITORY_HEADS']==catalog
canonical_before=git(unified,'show',status['INTEGRATION_AUDIT_BASE']+':release/integration-manifest.json');canonical_after=git(unified,'show',head+':release/integration-manifest.json');assert canonical_before==canonical_after and json.loads(canonical_after)['status']=='PROVISIONAL_NOT_INSTALLABLE'
node=json.loads(read('six-node-stage0.json'));assert len(node['results'])==node['observed_nodes']==6 and {x['node'] for x in node['results']}=={'LS5','PC1','PC2','PC3','PC4','LS7'} and all(x['process_exit_code']==0 for x in node['results']);assert not node['configuration_mutations'] and not node['adminit_contacted'] and not node['installation_authorized'] and node['runtime_readiness']=='NOT_QUALIFIED'
ci=json.loads(read('ci-snapshot.json'));assert len(ci)==4
for item in ci:
 actual=json.loads(read('run-'+str(item['id'])+'.json'));assert actual['head_sha']==item['head_sha'] and actual['run_attempt']==item['attempt']==1 and actual['status']==item['status']=='queued' and actual['conclusion'] is item['conclusion'] is None
math=next(x for x in ci if x['repo']=='math');assert math['id']==42352374979 and math['head_sha']=='2446d04624469e34aa96ed766be7a4887d6d654c' and status['AGENT7_AUTHORIZATION_STATUS']=='CONSUMED; no retry authorized'
probe=json.loads(read('math-existing-helper-overflow-repro.json'));assert probe['head']==catalog['math']['head'] and hashlib.sha256(git(repos['math'],'show',probe['head']+':'+probe['file'])).hexdigest()==probe['source_sha256'] and not probe['native_execution'] and not probe['source_mutations']
directive=read('owner-directive.txt');trailing=sum(line.endswith(b'  ') for line in directive.splitlines());assert trailing>0
for name in ['evidence-index.json','MASTER-STATUS.json','integration-blockers.json']:(out/('root-'+name)).write_bytes(read(name))
report=dict(requirement='MASTER_SEVEN_ARTIFACT_PUBLICATION_PROVENANCE_STATUS',repository='unified-system',pr=26,head=head,tree=git(unified,'rev-parse',head+'^{tree}').decode().strip(),selected_members=30,index_additional=1,artifacts=artifacts,owner_original_rows=counts,owner_rows_preserved=88,owner_raw_files_equal=True,raw_Git_blob_OID_SHA_checks=130,six_catalog_HEAD_tree_counts_manifests_verified=True,canonical_provisional_manifest_bytes_unchanged=True,stage0='SIX_OWNER_READ_ONLY_RECORDS_NOT_INDEPENDENT_HOST_REACQUISITION_OR_ACCEPTANCE',integration_gate_groups=8,confirmed_new_P0_defects='NOT_INFERRED_FROM_GATE_GROUPS',archived_run_snapshots='FOUR_QUEUED_ATTEMPT1_NOT_CURRENT_OR_TERMINAL_PASS',Math='917_HELPER_SOURCE_BOUND_OWNER_REPRO_NOT_2446_NATIVE_DIAGNOSTIC',Grid267_268='SEPARATE_NOT_CANONICAL_BASELINE_UPDATES_5S_GAP_OPEN',directive_sha256=hashlib.sha256(directive).hexdigest(),directive_lines_with_trailing_markdown_spaces=trailing,directive_bytes='VERIFIED_AS_INDEXED_NO_NORMALIZATION_NOT_REPUBLISHED_HERE',owner_implementation_scientific_status='ATTRIBUTED_NOT_INDEPENDENTLY_EXECUTED_SEMANTIC_88_ROW_ACK',audit_actions='READ_ONLY_GIT_AND_LOCAL_EVIDENCE_NO_TEST_OR_OFFICE_PROVIDER_NATIVE_EXECUTION',status='PASS_PUBLICATION_SOURCE_PROVENANCE_AND_BOUNDED_STATUS_CONSISTENCY',overall='NO_GO_RELEASE_PHYSICAL_NATIVE_ADMISSION')
(out/'independent-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
