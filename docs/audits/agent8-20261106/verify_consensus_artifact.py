"""Download and independently inspect original exact-source hosted consensus evidence."""
import hashlib,json,pathlib,subprocess,xml.etree.ElementTree as ET,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1];out=ROOT/'outputs/phase2';repo='YehorBabenko88/bybit-cluster-grid';run=42088042386;artifact=13451546239
sha='71084a336520187d6e260531a2f5d15555ba0e0c';expected='1d4de71e26ffc1c958f31ebfd2f2e46bd6dd3bbd0e0afae4deb058d30cfb27a4'
def api(path):return subprocess.check_output(['gh','api','--allow-escape-sequences','repos/'+repo+'/'+path])
meta=json.loads(api(f'actions/runs/{run}'));jobs=json.loads(api(f'actions/runs/{run}/attempts/1/jobs?per_page=100'))
assert meta['head_sha']==sha and meta['run_attempt']==1 and meta['conclusion']=='success'
assert jobs['total_count']==len(jobs['jobs']) and all(j['conclusion']=='success' for j in jobs['jobs'])
path=out/'hosted-consensus-original.zip'
data=path.read_bytes() if path.exists() else api(f'actions/artifacts/{artifact}/zip');assert hashlib.sha256(data).hexdigest()==expected
path.write_bytes(data)
required={'immutable_image_version_source_checked','persistent_voters_created','commit_and_duplicate','actual_raft_stats','restarted_actual_raft_stats','actual_raft_leader_crash_receipt_survives',
 'successor_commits_stale_owner_denied','two_voter_loss_denies_new_command',
 'all_process_restart_retained_volumes_receipts_recovered',
 'one_two_network_partition_majority_commits_minority_denied',
 'partition_healed_receipts_reconciled_no_forced_failback','actual_persistent_snapshot',
 'linux_persistent_command_scenarios_complete','budget_anchor_initial_commit','budget_anchor_leader_loss_read','budget_anchor_successor_cas_and_stale_denial','budget_anchor_noquorum_unknown',
 'budget_anchor_restart_recovered','budget_anchor_partition_majority_cas_minority_denied','budget_anchor_heal_recovered'}
with zipfile.ZipFile(path) as z:
    names=z.namelist();receipts={n:json.loads(z.read(n)) for n in names if n.endswith('.json')}
    evidence=receipts['qualification-three/evidence.json'];events=evidence['events'];scenarios=[e['scenario'] for e in events]
    assert evidence['result']=='PASS' and required<=set(scenarios)
    for name in required:
        assert scenarios.count(name)==(3 if name in {'actual_raft_stats','restarted_actual_raft_stats'} else 1),(name,scenarios.count(name))
    assert not {'failure','cleanup_failure'}&set(scenarios)
    assert len(evidence['nodes'])==len({n['raft_id'] for n in evidence['nodes']})==3
    source_before=receipts['qualification-source-before.json'];source_after=receipts['qualification-source-after.json']
    assert source_before['head']==source_after['head']==sha and source_before['tree']==source_after['tree']
    actual_tree=subprocess.check_output(['git','-C',str(ROOT/'work/grid-isolated'),'rev-parse',sha+'^{tree}'],text=True).strip()
    assert source_before['tree']==actual_tree
    lock=(ROOT/'work/grid-isolated/lab/consul/requirements-three-linux.lock').read_bytes()
    assert hashlib.sha256(lock).hexdigest()==source_after['fixture_lock_sha256']
    declared={}
    for name,digest in source_after['files'].items():
        assert name in names,name
        declared[name]=hashlib.sha256(z.read(name)).hexdigest()==digest
    assert all(declared.values())
    junit=ET.fromstring(z.read('coordination-tests.xml'));cases=list(junit.iter('testcase'))
    assert len(cases)==96 and all(c.find('skipped') is None and c.find('failure') is None and c.find('error') is None for c in cases)
    expected_cases={tuple(v) for v in source_after['unit_inventory']['expected']}
    assert {(c.get('classname'),c.get('name')) for c in cases}==expected_cases
    local=ET.parse(out/'grid-offline.xml').getroot()
    source_classes={'tests.coordination.test_budget_anchor','tests.coordination.test_coordination_commands','tests.coordination.test_consul_authority'}
    local_ids={(c.get('classname'),c.get('name')) for c in local.iter('testcase') if c.get('classname') in source_classes}
    assert local_ids==expected_cases,('local source collection disagrees',len(local_ids),len(expected_cases))
result={'head':sha,'run':run,'attempt':1,'artifact':artifact,'sha256':expected,'download_digest_match':True,
 'source_before':source_before,'source_after':source_after,'artifact_file_hashes_verified':declared,
 'scenarios':events,'testcases':96,'mandatory_scenario_subset_verified':sorted(required),
 'result':'PASS_ORIGINAL_HOSTED_LINUX_EVIDENCE_REVIEW_ONLY',
 'independent_local_execution':'NOT_RUN_LINUX_DOCKER_UNAVAILABLE','physical':'BLOCKED',
 'native_windows':'NOT_QUALIFIED_BY_LINUX_ARTIFACT','budget_store_integration':evidence['budget_store_integration'],
 'url':f'https://github.com/{repo}/actions/runs/{run}/artifacts/{artifact}'}
(out/'hosted-consensus-review.json').write_text(json.dumps(result,indent=2))
print(json.dumps({'result':result['result'],'digest_match':True,'testcases':96,'scenarios_verified':len(required),'files':names}))
