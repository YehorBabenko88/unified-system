"""Documentary integrity/gate-boundary review only; no application tests."""
import datetime,gzip,hashlib,io,json,pathlib,subprocess,tarfile
root=pathlib.Path(__file__).resolve().parents[1];repo=root/'work/review-integration-56f';out=root/'outputs/phase20';out.mkdir(exist_ok=True)
head='d88f4f7ab0b69f48840c38c8ade2fab40e243bd9';previous='084ef2ec3b42131b12af44103f2d21845bf1c0f7'
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
def blob(path):return git('show',head+':'+path)
def obj(path):return json.loads(blob(path))
manifest=obj('release/integration-manifest.json');regraw=blob('release/ownership-registry.json');reg=json.loads(regraw);regsha=hashlib.sha256(regraw).hexdigest();assert reg['revision']==7 and regsha==manifest['ownership_registry_sha256']=='2fda0830e1f5618cadfec40ec868964bd89a8e31815e76d028d18e4ad181a0d4'
agents={a['agent_id']:a for a in reg['agents']};assert all(a['ack']=='PENDING' for a in reg['agents'])
assert agents['A8']['allowed_new_path_prefixes']==['docs/audits/agent8-20261106/'] and agents['A8']['allowed_files']==[]
for aid in ('A1','A3','A4'):assert 'WAITING_EXPLICIT_OWNER_DESIGN_APPROVAL' in agents[aid]['full_feature_implementation']
design=manifest['contract_design_decisions']['authority_event_ordered_v3'];proposal=blob(design['proposal_path']);assert hashlib.sha256(proposal).hexdigest()==design['proposal_sha256']
approval_raw=blob(design['root_approval_path']);assert hashlib.sha256(approval_raw).hexdigest()==design['root_approval_sha256'];approval=json.loads(approval_raw);assert approval['proposal_sha256']==design['proposal_sha256']
peers=[];folder='release/contracts/authority-event-ordered-v3/'
for aid,item in approval['peer_acks'].items():
 raw=blob(folder+item['path']);assert hashlib.sha256(raw).hexdigest()==item['sha256']
 assert design['proposal_sha256'] in raw.decode();peers.append({'agent':aid,'path':item['path'],'sha256':item['sha256'],'scope':item['scope']})
assert len(peers)==6 and approval['runtime_admission']==approval['physical_admission']=='BLOCKED' and approval['old_gates_opened'] is False
assert design['old_profile_changed'] is False and design['wire_and_runtime_acceptance']=='BLOCKED'
inert=obj('release/contracts/inert-bootstrap-v2/ROOT-SCOPED-ACK.json');assert hashlib.sha256(blob('release/contracts/inert-bootstrap-v2/PROPOSAL.json')).hexdigest()==inert['proposal_sha256']
assert inert['physical_authorization']=='NONE_FROM_THIS_ACK' and inert['qualification']=='NOT_IMPLEMENTED_NOT_TESTED_NOT_INSTALLABLE'
assert inert['operational_transition'].startswith('BLOCKED_')
for key in ('main_merge_authorized','physical_fault_injection_authorized','tailscale_removal_authorized'):assert manifest[key] is False
assert manifest['go']=='NO-GO' and manifest['runtime_admission']=='BLOCKED' and manifest['status']=='PROVISIONAL_NOT_INSTALLABLE'
plan=obj('release/physical-deployment-plan.json');assert plan['status']=='BLOCKED_NOT_EXECUTABLE' and all(s['status']=='BLOCKED_NOT_RUN' for s in plan['stages'])
snapshotraw=blob('release/ci-all-open-heads.json');snapshot=json.loads(snapshotraw);summary=obj('release/ci-metadata-summary.json')
assert hashlib.sha256(snapshotraw).hexdigest()==manifest['metadata_snapshot_coverage']['sha256']==summary['source_index_sha256']
assert len(snapshot['heads'])==summary['heads']==manifest['metadata_snapshot_coverage']['heads']==444
archive=blob('release/evidence/all-open-ci-20261106.tar.gz');verified=0
with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
 for key,item in snapshot['heads'].items():
  compressed=tar.extractfile(item['evidence_file']).read();assert hashlib.sha256(compressed).hexdigest()==item['compressed_sha256']
  raw=gzip.decompress(compressed);assert hashlib.sha256(raw).hexdigest()==item['raw_sha256'];json.loads(raw);verified+=1
trace=obj('release/authority-requirement-trace.json');assert trace['literal_clock_requirement_conclusion'].startswith('NOT_FOUND_IN_THIS_ATTACHMENT_SCOPE')
log=obj('release/evidence/full-suite-network-receipt.json')
for stream in ('stdout','stderr'):assert hashlib.sha256(blob('release/evidence/full-suite-network.'+stream+'.log')).hexdigest()==log[stream+'_sha256']
source_pin=manifest['modules']['unified-system'];assert source_pin['tree']==git('rev-parse',source_pin['head']+'^{tree}').decode().strip()
changes=git('diff','--name-only',previous,head).decode().splitlines();unreviewed=[p for p in changes if p.startswith(('unified_system/','tests/','scripts/network_'))]
assert unreviewed
result={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'head':head,'tree':git('rev-parse',head+'^{tree}').decode().strip(),'scope':'DOCUMENTARY_HASH_AND_GATE_BOUNDARIES_ONLY_NO_SOURCE_RUNTIME_REVIEW','ownership_revision':7,'ownership_sha256':regsha,'A8_ACK':'FRESH_OWN_AUDIT_PREFIX_ONLY_NO_GLOBAL_CONTRACT_OR_ACK_TRANSFER','new_profile_proposal_sha256':design['proposal_sha256'],'root_design_approval_sha256':design['root_approval_sha256'],'peer_ack_hashes_verified':peers,'semantic_design_approval':'ROOT_DOCUMENTED_NEW_PROFILE_ONLY_NOT_HUMAN_FULL_FEATURE_APPROVAL_OR_RUNTIME_PROOF','inert_bootstrap_proposal_sha256':inert['proposal_sha256'],'inert_scope':'DESIGN_BOUNDARY_ONLY_NO_INSTALL_PERMISSION','metadata_heads_original_archived_hashes_verified':verified,'metadata_qualification':'NOT_MANDATORY_CASE_ATTEMPT_LOG_ARTIFACT_OR_RUNTIME_ACCEPTANCE','original_new_full_suite_receipt_hashes':'VERIFIED_OWNER_EVIDENCE_NOT_REEXECUTED_OR_ACCEPTED_AS_FULL_PASS','unreviewed_added_source_test_paths':unreviewed,'source_56f_acceptance_transfer':False,'owner_requirement_trace':'BOUNDED_DECLARED_SCOPE_ONLY_ORIGINAL_ATTACHMENTS_NOT_REACQUIRED_BY_A8_NO_LITERAL_REQUIREMENT_INFERRED','closed_gate_promotions_identified_in_reviewed_documents':False,'runtime':'BLOCKED','installable':False,'physical':'BLOCKED','tailscale_removal':'BLOCKED','overall':'NO_GO'}
(out/'design-checkpoint-review.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
