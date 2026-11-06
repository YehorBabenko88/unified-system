"""Independent exact-Git package integrity and ownership-scope review."""
import argparse,hashlib,json,pathlib,subprocess
p=argparse.ArgumentParser();p.add_argument('--head',default='c7307afba57aa28548e483e02c3a2f390b5056e1');p.add_argument('--index',default='81e4dd6e8d32643bdeb5cb760d6be4db2aa51370fe2bfca7b182a9f76dcaf234');p.add_argument('--members',type=int,default=30);p.add_argument('--output',default='preparation-review.json');args=p.parse_args()
ROOT=pathlib.Path(__file__).resolve().parents[1];repo=ROOT/'work/coordination-review';sha=args.head;prefix='acceptance/20261106/';expected=args.index
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
def blob(path):return git('show',sha+':'+path)
index_raw=blob(prefix+'package-index.json');assert hashlib.sha256(index_raw).hexdigest()==expected
index=json.loads(index_raw);assert len(index['files'])==args.members
verified={name:hashlib.sha256(blob(prefix+name)).hexdigest()==digest for name,digest in index['files'].items()};assert all(verified.values())
approval=json.loads(blob(prefix+'approval-status.json'));release=json.loads(blob(prefix+'release-manifest.json'))
for document in (approval,release):
    assert document['runtime_admission']=='BLOCKED' and document['installable'] is False and document['go']=='NO-GO'
    assert document['physical_fault_injection']=='NOT_AUTHORIZED' and document['production_deployment']=='NOT_AUTHORIZED' and document['tailscale_removal']=='BLOCKED'
baseline=json.loads(blob(prefix+'integration-baseline.json'));assert baseline['modules']==release['source_modules']
pins={}
for name,pin in baseline['modules'].items():
    evidence=ROOT/'outputs/evidence'/(name+'-'+pin['head']+'.json')
    original=json.loads(evidence.read_text())
    assert original['commit']['sha']==pin['head'] and original['commit']['commit']['tree']['sha']==pin['tree']
    pins[name]={'head':pin['head'],'tree':pin['tree'],'pr':pin['pr'],'prior_original_api_pin_match':True}
ownership=json.loads(blob(prefix+'ownership-registry.json'))
assert blob(prefix+'ownership-registry.json')==blob('coordination/ownership.v1.json')
ns={'__name__':'exact_preparation_registry'};exec(compile(blob('unified_system/integration_registry.py'),'exact_git_registry','exec'),ns)
assert ns['verify_ownership'](ownership)
result=ns['verify_acceptance_package'](repo/prefix,expected_index_sha256=expected)
assert result['runtime_admission']=='BLOCKED' and result['go']=='NO-GO' and result['physical_authorized'] is False
scope_gaps={}
for agent_id,repo_name,pr in [('A7','math',112),('A7','strattester',71),('A7','meta_analyse',77),('A5','unified-system',24)]:
    agent=next(a for a in ownership['agents'] if a['agent_id']==agent_id)
    allocation=next(a for a in [agent,*agent.get('additional_allocations',[])] if a['repository']==repo_name)
    changed=json.loads((ROOT/'outputs/phase4'/(repo_name+'-files.json')).read_text()) if agent_id=='A7' else None
    if changed is None:
        r=ROOT/'work/review5-scheduler';paths=subprocess.check_output(['git','-C',str(r),'diff','--name-only',allocation['base_head'],'787c862568eb47177c21393338e743ec01b5f45f'],text=True).splitlines()
    else:paths=[r['filename'] for r in changed]
    scope_gaps[repo_name+'#'+str(pr)]=[p for p in paths if p not in allocation['allowed_files'] and not any(p.startswith(pre) for pre in allocation['allowed_new_path_prefixes'])]
own=next(a for a in ownership['agents'] if a['agent_id']=='A8');assert own['worktree'].replace('\\','/').casefold()==str(ROOT/'work/unified-audit').replace('\\','/').casefold()
nodes=json.loads(blob(prefix+'node-inventory.json'));assert {n['node_id'] for n in nodes['nodes']}=={'LS5','PC1','PC2','PC3','PC4','LS7'}
assert all(n['runtime_mutual_auth']=='NOT_QUALIFIED' and n['capacity']=='NOT_ADMITTED' for n in nodes['nodes'])
boundary='proposals/5cc8e6a3557a9d71b6d1ccdf9939be49133deee9219b19029ffd4cf3d3bfa278.json'
assert hashlib.sha256(blob(prefix+boundary)).hexdigest()=='5cc8e6a3557a9d71b6d1ccdf9939be49133deee9219b19029ffd4cf3d3bfa278'
agent6=next(a for a in ownership['agents'] if a['agent_id']=='A6')
pending6=[]
if agent6.get('draft_pr')!=69:pending6.append('draft_pr should be69')
if not {'A3','A4'}<=set(agent6.get('dependencies',[])):pending6.append('dependencies should include A3/A4')
report={'head':sha,'tree':git('rev-parse',sha+'^{tree}').decode().strip(),'index_sha256':expected,'members_verified':verified,
 'package_integrity_result':result,'six_source_pins':pins,'ownership_revision':ownership['revision'],
 'ownership_sha256':hashlib.sha256(blob(prefix+'ownership-registry.json')).hexdigest(),
 'A8_scope_and_actual_path':'ACK_A8_SCOPE_ONLY','changed_files_not_in_published_ownership':scope_gaps,
 'known_A6_metadata_pending':pending6,
 'node_inventory':'CANDIDATES_DECLARED_NOT_AUTHENTICATED_OR_CAPACITY_ADMITTED',
 'release_manifest':'PRESENT_PREPARATION_ONLY_NOT_APPROVED_OR_INSTALLABLE','contract_endpoint_ACK':'PENDING',
 'mandatory_case_workflow_platform_attempt_skip_mapping':'PENDING_A8_REVIEW','physical':'BLOCKED','tailscale_removal':'BLOCKED','overall':'NO-GO'}
(ROOT/'outputs/phase6'/args.output).write_text(json.dumps(report,indent=2));print(json.dumps({'members':len(verified),'integrity':result,'scope_gaps':scope_gaps,'A6_pending':pending6,'A8_ACK':'SCOPE_ONLY'}))
