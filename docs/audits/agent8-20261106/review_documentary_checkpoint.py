"""Verify documentary checkpoint from immutable Git objects; no runtime execution."""
import hashlib,io,json,pathlib,re,subprocess,tarfile
ROOT=pathlib.Path(__file__).resolve().parents[1];repo=ROOT/'work/review-integration-56f';out=ROOT/'outputs/phase13';out.mkdir(exist_ok=True)
head='ca9e390203305c8662ddf98fb771ac0bd268ec49';base='56f4215506f3a6efb7404591753facd69204a1ee'
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
def blob(path):return git('show',head+':'+path)
def obj(path):return json.loads(blob(path))
paths=git('diff','--name-only',base,head).decode().splitlines()
assert all(p=='MASTER-MISSION-FINAL-AUDIT.md' or p.startswith('release/') for p in paths)
assert not any(p.endswith(('.py','.yml','.yaml','.lock')) for p in paths)
ownership=blob('release/ownership-registry.json');digest=hashlib.sha256(ownership).hexdigest();assert digest=='2415c81fb4099bad670312df1132cf398e70a11368eebf3c31d435626b349f38'
reg=json.loads(ownership);assert reg['revision']==4 and all(a['ack']=='PENDING' for a in reg['agents'])
agents={a['agent_id']:a for a in reg['agents']}
assert agents['A8']['allowed_files']==[] and agents['A8']['allowed_new_path_prefixes']==['docs/audits/agent8-20261106/']
assert 'tests/platform-coverage.test.mjs' in agents['A7']['allowed_files']
allocation=agents['A2']['additional_allocations'][0];assert allocation['allowed_files']==['tests/test_owned_control_source.py'] and allocation['head']=='a17f1db6b9aa04c105d2e993496026a83849ecfd'
for agent in ('A1','A3','A4'):assert agents[agent]['full_feature_implementation'].startswith('WAITING_EXPLICIT_OWNER_DESIGN_APPROVAL')
manifest=obj('release/integration-manifest.json');assert manifest['ownership_registry_sha256']==digest and manifest['go']=='NO-GO' and manifest['runtime_admission']=='BLOCKED'
for field in ('main_merge_authorized','physical_fault_injection_authorized','tailscale_removal_authorized'):assert manifest[field] is False
assert manifest['modules']['bybit-cluster-grid']['head']==allocation['head'] and manifest['modules']['math']['head']==agents['A7']['head']=='917d99672e37db59835a8ab23b03c99826b12d78'
logs=[]
for name in ('integrated-components','full-suite','windows-fixture-targeted','source-composition','source-composition-focused'):
 receipt=obj('release/evidence/'+name+'-receipt.json')
 for stream in ('stdout','stderr'):assert hashlib.sha256(blob('release/evidence/'+name+'.'+stream+'.log')).hexdigest()==receipt[stream+'_sha256']
 logs.append({'name':name,'head':receipt['head'],'exit_code':receipt['exit_code'],'hashes':'VERIFIED_ORIGINAL_NOT_INDEPENDENT_EXECUTION'})
index=obj('release/evidence/github-original-metadata-index.json');archive=blob('release/evidence/'+index['archive']);assert hashlib.sha256(archive).hexdigest()==index['sha256']
with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
 members=tar.getmembers();assert len({m.name for m in members})==len(members)==len(index['files'])
 for item in index['files']:
  member=tar.getmember(item['name']);assert member.isfile();data=tar.extractfile(member).read();assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256']
guard_index=obj('release/evidence/integration-guard/sha256-index.json')
for name,expected in guard_index.items():assert hashlib.sha256(blob('release/evidence/integration-guard/'+name)).hexdigest()==expected
nodes=obj('release/node-inventory.json');assert {n['node'] for n in nodes['nodes']}=={'LS5','PC1','PC2','PC3','PC4','LS7'}
assert all(n['runtime_account_admission']=='NOT_VERIFIED' and n['installation_readiness']=='BLOCKED_OTHER_GATES' for n in nodes['nodes'])
pc3=next(n for n in nodes['nodes'] if n['node']=='PC3');assert all(not p['Enabled'] for p in pc3['firewall'])
skips=obj('release/skip-inventory.json');assert len(skips['skips'])==skips['count']==14 and all(s['waiver'] is None for s in skips['skips'])
original_log=blob('release/evidence/full-suite.stderr.log').decode();assert all(s['test'] in original_log for s in skips['skips'])
egress=obj('release/egress-observation.json');assert egress['bybit_route_equivalence']=='NOT_PROVEN' and egress['quota_activation']=='NOT_AUTHORIZED_BY_OBSERVATION'
observations=[{'severity':'P2_METADATA','field':'ownership.A8.base_head','recorded':agents['A8']['base_head'],'verified_pr21_base':'b9b03a1ce9f887dbe113fd22d0bda8932f46ef80','required_correction':'Reconcile current allocation base with actual Draft21 base; label historical if intended.'},{'severity':'P2_METADATA','field':'integration-manifest.modules.unified-system.pr','recorded':manifest['modules']['unified-system']['pr'],'current_integration_pr':26,'required_correction':'Separate historical component PR13 from current integration PR26 and bind candidate HEAD/tree to the intended PR.'}]
result={'head':head,'tree':git('rev-parse',head+'^{tree}').decode().strip(),'reviewed_source_base':base,'changed_paths':paths,'app_tests_workflows_unchanged':True,'ownership_revision':4,'ownership_sha256':digest,'ownership_ACK':'A8_OWN_PATH_SCOPE_ONLY_NO_GLOBAL_ACK_NO_PRIOR_TRANSFER','original_log_pairs_verified':logs,'metadata_archive_members_verified':len(index['files']),'guard_evidence_members_verified':len(guard_index),'declared_nodes':6,'physical_or_LAN_acceptance':'NOT_QUALIFIED_ORIGINAL_OWNER_LOCAL_NODE_DATA_NOT_REACQUIRED','PC3_firewall':'DECLARED_OFF_NOT_INDEPENDENTLY_OBSERVED_BY_A8_REQUIRES_OWNER_SECURITY_REVIEW','mandatory_skips_preserved':14,'metadata_observations':observations,'tests_rerun':'NONE_DOCUMENTARY_ONLY','overall':'NO_GO','tailscale_removal':'BLOCKED'}
(out/'documentary-review.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
